"""Student report flow: analyse, match, create the ticket now, assign, and build the reply."""
import config
from ai import triage
from ai.keywords import issue_tokens, routing_guide
from ai.kb import self_help
from ai.vision import describe_photo
from db import db as core
from db import groups as gdb
from db import tickets as tdb
from logic import alerts, assignment, cache, location, mapfile
from logic.photos import shrink_photo
from logic.timeutil import eta_text, hours_from_now

MAX_TEXT = 2000


def validate_category(category: str) -> str:
    """Return the category if it is one of the four allowed ones, else raise ValueError. There is no 'General'."""
    if category not in config.CATEGORIES:
        raise ValueError(f"Category must be one of {config.CATEGORIES}, got {category!r}.")
    return category


def landmark_options() -> list[dict]:
    """Landmarks for pickers: id, slug, name, category, number, floors (from the database)."""
    return core.list_landmarks()


def pin_conflict(pin_slug: str | None, chosen_slug: str | None) -> bool:
    """True if the dropped pin and the landmark named in the text disagree (so the UI asks which is right)."""
    return location.pin_conflict(mapfile.by_id(pin_slug) if pin_slug else None, mapfile.by_id(chosen_slug) if chosen_slug else None)


def read_location(text: str) -> dict:
    """What the text says about where it is: {landmark (slug|None), name, ambiguous [{id,name}], floor, room, nearby}."""
    g = location.extract_location(text or "")
    lm = g["landmark"]
    return {"landmark": lm["id"] if lm else None, "name": mapfile.display_name(lm) if lm else None,
            "ambiguous": [{"id": a["id"], "name": a["name"]} for a in g["ambiguous"]],
            "floor": g["floor"], "room": g["room"], "nearby": g["nearby"]}


def _clean_location(landmark_slug: str | None, floor: str | None) -> tuple[dict | None, str | None]:
    lm = core.get_landmark_by_slug(landmark_slug) if landmark_slug else None
    if floor and (lm is None or floor not in lm["floors"]):
        floor = None  # only the landmark's own floors are accepted
    return lm, floor


def submit_report(
    student: dict, text: str, landmark: str | None = None, floor: str | None = None,
    room: str | None = None, nearby: str | None = None, photo: bytes | None = None, photo_mime: str | None = None,
    map_x: float | None = None, map_y: float | None = None,
) -> dict:
    """Turn a complaint into a ticket right away and return what to show the student.

    landmark is a landmark slug (e.g. "b_block"). Anything left blank (landmark, floor, room, nearby) is read
    from the text where possible. Never blocked by AI failure. Returns a dict with: ticket_id, code, category,
    summary, status, staff_name, eta_text, self_help, follow_up_question, missing_fields, cache (live reply of a
    matching group or None), mode ("ai"|"rules"), photo_note, out_of_scope, ambiguous (landmark options to ask about).
    """
    text = (text or "").strip()
    if not text:
        raise ValueError("Please describe the problem.")
    text = text[:MAX_TEXT]
    guess = location.extract_location(text)
    if not landmark and guess["landmark"]:
        landmark = guess["landmark"]["id"]
    lm, floor = _clean_location(landmark, floor)
    if lm and not floor:
        floor = location.extract_floor(text, lm["floors"])
    room = (room or "").strip()[:60] or guess["room"]
    nearby = (nearby or "").strip()[:120] or guess["nearby"]
    where = {"landmark": lm["name"] if lm else None, "floor": floor, "room": room, "nearby": nearby}
    if map_x is None and lm:
        map_x, map_y = mapfile.by_id(lm["slug"])["map_x"], mapfile.by_id(lm["slug"])["map_y"]

    photo_bytes = photo_mime_out = photo_note = None
    if photo:
        photo_bytes, photo_mime_out = shrink_photo(photo)
        photo_note, _ = describe_photo(photo_bytes, photo_mime_out)

    analysis = triage.analyse(text, where, photo_note if photo_note and "not analysed" not in photo_note else None)
    category = validate_category(analysis["category"])

    match = cache.lookup({"category": category, "landmark_id": lm["id"] if lm else None, "floor": floor, "text": text})
    primary = tdb.get_ticket(match["primary"]["id"]) if match and match["primary"] else None
    open_match = match is not None and match["status"] != "resolved"

    default_eta = hours_from_now(routing_guide()[category]["default_eta_hours"])
    if match:
        group_id = match["id"]
        gdb.update_group(group_id, {"keywords": sorted(set(match["keywords"]) | issue_tokens(text))})
        eta =(primary["eta_at"] if open_match and primary and primary["eta_at"] else default_eta)
    else:
        group_id = gdb.create_group(
            category, lm["id"] if lm else None, floor, analysis["summary"], sorted(issue_tokens(text)),
            map_x, map_y, default_eta,
        )
        eta = default_eta

    ticket_id = tdb.create_ticket({
        "student_id": student["id"], "student_name": student["name"], "student_roll": student["roll"],
        "title": analysis["summary"], "description": text, "category": category,
        "severity": analysis["severity"], "status": "waiting",
        "landmark_id": lm["id"] if lm else None, "floor": floor, "room": room, "nearby": nearby,
        "map_x": map_x, "map_y": map_y, "group_id": group_id,
        "ai_confidence": analysis["confidence"], "language": analysis["language"],
        "dup_review": "pending" if match else "none",
        "info_complete": not analysis["missing_fields"], "needs_review": analysis["needs_review"],
        "missing_fields": analysis["missing_fields"], "follow_up_question": analysis["follow_up_question"] or None,
        "eta_at": eta, "photo": photo_bytes, "photo_mime": photo_mime_out, "photo_note": photo_note,
        "ai_mode": analysis["mode"],
    })
    tdb.add_history(ticket_id, "waiting", "Ticket created.", f"{student['name']} (student)")
    gdb.add_report(group_id, student["id"], ticket_id, "ticket")

    if open_match and primary and primary["assigned_to"]:
        tdb.assign_ticket(ticket_id, primary["assigned_to"], "System")
        if primary["status"] != "assigned":
            tdb.add_status(ticket_id, primary["status"], f"Same issue as {primary['code']}.", "System")
    else:
        assignment.assign_new(ticket_id, category)
    alerts.evaluate_group(group_id)

    if analysis["follow_up_question"]:
        tdb.add_system_message(ticket_id, analysis["follow_up_question"])

    ticket = tdb.get_ticket(ticket_id)
    return {
        "ticket_id": ticket_id, "code": ticket["code"], "category": category, "summary": analysis["summary"],
        "status": ticket["status"], "staff_name": ticket["staff_name"], "eta_text": eta_text(ticket["eta_at"]),
        "self_help": self_help(category, text), "follow_up_question": analysis["follow_up_question"],
        "missing_fields": analysis["missing_fields"], "cache": cache.build_reply(group_id) if match else None,
        "mode": analysis["mode"], "photo_note": photo_note, "out_of_scope": analysis["out_of_scope"],
        "ambiguous": [{"id": a["id"], "name": a["name"]} for a in guess["ambiguous"]] if not lm else [],
        "location": where,
    }


def say_me_too(student: dict, group_id: int) -> bool:
    """'I face this too': one report per student per group. Returns False if they already reported it."""
    added = gdb.add_report(group_id, student["id"], None, "me_too")
    if added:
        alerts.evaluate_group(group_id)
    return added
