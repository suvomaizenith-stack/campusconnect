"""Keyword-based FAQ knowledge base (data/kb.json). The only source of self-help text."""
import json
from pathlib import Path

from ai.keywords import has_keyword

KB_PATH = Path(__file__).resolve().parent.parent / "data" / "kb.json"


def _raw() -> dict:
    try:
        raw = json.loads(KB_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"faq": [], "contacts": {}}
    return {"faq": raw, "contacts": {}} if isinstance(raw, list) else raw


def load_kb() -> list[dict]:
    """Load the FAQ entries from data/kb.json."""
    return _raw().get("faq", [])


def contact(key: str) -> dict | None:
    """Contact card {name, phone, hours, note} for helpdesk / security / medical / it_support, or None."""
    return _raw().get("contacts", {}).get(key)


def find_answer(text: str, category: str | None = None) -> str | None:
    """Return the answer of the entry with most keyword hits, or None.

    When a category is given, entries of that category are preferred.
    """
    best, best_score = None, 0
    for entry in load_kb():
        score = sum(1 for k in entry["keywords"] + entry.get("keywords_hi", []) if has_keyword(text, k))
        if category and entry.get("category") == category:
            score += 2
        if score > best_score:
            best, best_score = entry["answer"], score
    return best


def self_help(category: str, text: str = "") -> str | None:
    """Return the self-help answer for a category (the kb entry of that category), or None."""
    return find_answer(text, category) if any(e.get("category") == category for e in load_kb()) else None
