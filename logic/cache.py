"""Reply cache: answer a new report from an existing group's live state. Works with keyword extraction only."""
import config
from ai.keywords import issue_tokens, jaccard
from ai.kb import self_help
from db import groups as gdb
from db import tickets as tdb
from logic import alerts
from logic.timeutil import eta_text, time_ago


def lookup(analysis: dict) -> dict | None:
    """Find the best matching group for a new report, or None.

    analysis needs: category, landmark_id, floor (optional), text. A group matches when it is open or
    resolved within CACHE_RESOLVED_HOURS, has the same category and landmark, the floors agree when both
    are stated, and keyword Jaccard similarity is at least CACHE_MATCH_THRESHOLD.
    Returns the group dict (see db.groups.get_group) with a "similarity" key.
    """
    words = issue_tokens(analysis["text"])
    floor = (analysis.get("floor") or "").strip().lower()
    best, best_sim = None, 0.0
    for g in gdb.candidate_groups(analysis["category"], analysis.get("landmark_id"), config.CACHE_RESOLVED_HOURS):
        gfloor = (g["floor"] or "").strip().lower()
        if floor and gfloor and floor != gfloor:
            continue
        sim = jaccard(words, set(g["keywords"]))
        if sim >= config.CACHE_MATCH_THRESHOLD and sim > best_sim:
            best, best_sim = g, sim
    if best is None:
        return None
    full = gdb.get_group(best["id"])
    full["similarity"] = round(best_sim, 2)
    return full


def build_reply(group_id: int) -> dict:
    """Build the student-facing reply from the group's LIVE state.

    Returns {"kind": "open"|"resolved", "text", "group_id", "report_count", "status", "staff_name", "eta_text",
    "latest_note", "self_help", "can_reopen"}.
    """
    g = gdb.get_group(group_id)
    primary = g["primary"] or {}
    staff = primary.get("staff_name")
    resolved = g["status"] == "resolved"
    where = g["landmark"] or "this location"
    help_text = self_help(g["category"], " ".join(g["keywords"]))
    if resolved:
        text = f"Staff marked this problem at {where} as resolved {time_ago(g['resolved_at'])}."
        if g["latest_note"]:
            text += f' Their note: "{g["latest_note"]}".'
        text += " If it is still broken, tap the button below and we will reopen it."
    else:
        n = g["report_count"]
        text = f"We already know about this problem at {where}: {n} report{'s' if n != 1 else ''} so far."
        text += f" It is being handled by {staff}." if staff else " It is waiting for a staff member to pick it up."
        if g["latest_note"]:
            text += f' Latest staff note: "{g["latest_note"]}".'
    return {
        "kind": "resolved" if resolved else "open",
        "text": text,
        "group_id": group_id,
        "report_count": g["report_count"],
        "status": primary.get("status") or g["status"],
        "staff_name": staff,
        "eta_text": eta_text(primary.get("eta_at") or g["eta_at"]),
        "latest_note": g["latest_note"],
        "self_help": None if resolved else help_text,
        "can_reopen": resolved,
    }


def reopen_group(group_id: int, student: dict) -> None:
    """A student says a recently resolved problem is still broken: reopen the group and its primary ticket."""
    g = gdb.get_group(group_id)
    if g is None or g["status"] != "resolved":
        raise ValueError("This problem is not marked resolved.")
    gdb.update_group(group_id, {"status": "open", "resolved_at": None})
    by = f"{student['name']} (student)"
    primary = g["primary"]
    if primary:
        full = tdb.get_ticket(primary["id"])
        reopened = "assigned" if full["assigned_to"] else "waiting"
        for t in tdb.list_tickets(group_id=group_id):
            if t["dup_review"] != "separate" and t["status"] == "resolved" and not t["self_resolved"]:
                tdb.add_status(t["id"], reopened, "Reopened: a student reports it is still broken.", by)
    gdb.add_report(group_id, student["id"], None, "still_broken")
    alerts.evaluate_group(group_id)
