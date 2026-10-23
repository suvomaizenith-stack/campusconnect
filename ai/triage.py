"""Turn a complaint into a structured analysis. Uses the LLM chain, falls back to keyword rules.

analyse() never raises: an AI failure only changes mode from "ai" to "rules".
"""
import re

import config
from ai import llm
from ai.keywords import category_scores, has_keyword, language_of, out_of_scope_hit, routing_guide

DEFAULT_CATEGORY = "cleanliness"  # best guess when nothing matches; needs_review is set
MISSING_FIELDS = ("description", "landmark", "room")
QUESTIONS = {
    "description": "Could you tell us a bit more about what exactly is wrong?",
    "landmark": "Which building or place is this in?",
    "room": "Which room, washroom or area exactly (for example room number or 'near the stairs')?",
}
URGENT_WORDS = ("urgent", "emergency", "immediately", "everyone", "all students", "dangerous", "unsafe")
_ROOM_RE = re.compile(r"\b(?:room|lab|hall|cabin|class(?:room)?)\s*(?:no\.?\s*)?([A-Za-z]?\d{1,4}[A-Za-z]?)\b", re.I)
_NUM_RE = re.compile(r"\b(\d{2,4})\b")

SYSTEM_PROMPT = (
    "You triage campus complaints for a university. Reply with ONE JSON object with keys: "
    '"category" (exactly one of plumbing, electricity, cleanliness, internet; never anything else), '
    '"severity" (1 minor, 2 needs quick action, 3 safety risk or widespread outage), '
    '"summary" (max 80 characters, plain English words, even if the complaint is in Hindi), '
    '"confidence" (number 0 to 1: how sure you are about the category), '
    '"language" ("en" or "hi", the language the student wrote in), '
    '"missing_fields" (array using only: description, landmark, room), '
    '"follow_up_question" (one short question if something is missing, else empty string). '
    "Use the stated location; only list a field as missing if it is not given anywhere."
)


def extract_room(text: str) -> str:
    """Pull a room number like '204' from free text, or '' if none."""
    m = _ROOM_RE.search(text) or _NUM_RE.search(text)
    return m.group(1).upper() if m else ""


def _severity(text: str, category: str) -> int:
    severe = routing_guide()[category]["severe_keywords"]
    if any(has_keyword(text, k) for k in severe):
        return 3
    return 2 if any(w in text.lower() for w in URGENT_WORDS) else 1


def _missing(text: str, location: dict) -> list[str]:
    missing = []
    if len(text.split()) < 3:
        missing.append("description")
    if not location.get("landmark"):
        missing.append("landmark")
    if not (location.get("room") or location.get("nearby") or extract_room(text)):
        missing.append("room")
    return missing


def _summary(text: str) -> str:
    first = re.split(r"[.!?\n]", text.strip(), maxsplit=1)[0].strip()
    first = first[:80].rstrip()
    return first[:1].upper() + first[1:] if first else "Campus issue"


def rules_analyse(text: str, location: dict) -> dict:
    """Keyword-only analysis. Always works, no network."""
    scores = category_scores(text)
    best = max(scores.values())
    needs_review = best == 0
    category = DEFAULT_CATEGORY if needs_review else max(scores, key=lambda c: scores[c])
    missing = _missing(text, location)
    ranked = sorted(scores.values(), reverse=True)
    margin = ranked[0] - ranked[1]
    confidence = 0.2 if needs_review else min(0.9, 0.45 + 0.1 * best + 0.1 * margin)
    return {
        "confidence": round(confidence, 2),
        "language": language_of(text),
        "out_of_scope": needs_review and out_of_scope_hit(text),
        "category": category,
        "severity": _severity(text, category),
        "summary": _summary(text),
        "missing_fields": missing,
        "follow_up_question": QUESTIONS[missing[0]] if missing else "",
        "needs_review": needs_review,
        "mode": "rules",
    }


def _validate(data: dict) -> dict:
    """Check an LLM reply against the schema. Raises ValueError if unusable."""
    category = str(data["category"]).strip().lower()
    if category not in config.CATEGORIES:
        raise ValueError(f"category must be one of {config.CATEGORIES}")
    severity = int(data["severity"])
    if severity not in (1, 2, 3):
        raise ValueError("severity must be 1, 2 or 3")
    summary = str(data["summary"]).strip()
    if not summary:
        raise ValueError("summary is empty")
    missing = data.get("missing_fields") or []
    if not isinstance(missing, list) or any(m not in MISSING_FIELDS for m in missing):
        raise ValueError(f"missing_fields may only contain {MISSING_FIELDS}")
    question = str(data.get("follow_up_question") or "").strip()
    if missing and not question:
        question = QUESTIONS[missing[0]]
    try:
        confidence = min(1.0, max(0.0, float(data.get("confidence", 0.7))))
    except (TypeError, ValueError):
        confidence = 0.7
    return {
        "confidence": round(confidence, 2),
        "category": category,
        "severity": severity,
        "summary": summary[:80],
        "missing_fields": list(missing),
        "follow_up_question": question if missing else "",
    }


def _location_line(location: dict) -> str:
    parts = [location.get("landmark"), location.get("floor"), location.get("room"), location.get("nearby")]
    return ", ".join(p for p in parts if p) or "not given"


def analyse(text: str, location: dict | None = None, photo_note: str | None = None) -> dict:
    """Analyse a complaint. Returns category, severity, summary, missing_fields, follow_up_question, needs_review, mode.

    location keys (all optional): landmark, floor, room, nearby.
    """
    location = location or {}
    text = text.strip()
    fallback = rules_analyse(text, location)
    prompt = f"Complaint: {text}\nLocation: {_location_line(location)}"
    if photo_note:
        prompt += f"\nPhoto shows: {photo_note}"
    try:
        result = llm.chat_json([{"role": "user", "content": prompt}], SYSTEM_PROMPT, _validate)
    except llm.LLMError:
        return fallback
    # Trust the code for facts it can check: missing location fields come from the form, not the model.
    missing = _missing(text, location)
    result["missing_fields"] = missing
    result["follow_up_question"] = QUESTIONS[missing[0]] if missing else ""
    result["language"] = language_of(text)  # trust the code, not the model, for the script check
    result["out_of_scope"] = False
    result["needs_review"] = result["confidence"] < config.LOW_CONFIDENCE
    result["mode"] = "ai"
    return result


def merge_answer(ticket: dict, answer: str) -> dict:
    """Merge a student's answer to the follow-up question into the ticket.

    ticket needs: description, category, landmark (name), floor, room, nearby.
    Returns the updated description, room, category, summary, severity and needs_review.
    The ticket is marked complete: the student has answered, so we stop asking.
    """
    description = f"{ticket['description']}\nAdditional details: {answer.strip()}"
    room = ticket.get("room") or extract_room(answer)
    location = {
        "landmark": ticket.get("landmark"), "floor": ticket.get("floor"),
        "room": room, "nearby": ticket.get("nearby") or ("" if room else answer.strip()[:80]),
    }
    analysis = analyse(description, location)
    return {
        "description": description,
        "room": room or None,
        "nearby": location["nearby"] or None,
        "category": analysis["category"],
        "summary": analysis["summary"],
        "severity": max(analysis["severity"], int(ticket.get("severity") or 1)),
        "needs_review": analysis["needs_review"],
        "confidence": analysis["confidence"],
        "mode": analysis["mode"],
    }
