"""Staff and student actions that change ticket state. Every change writes status_history."""
from datetime import datetime

from ai.keywords import issue_tokens
from db import groups as gdb
from db import tickets as tdb
import config
from logic import alerts, assignment, priority
from logic.timeutil import fmt_ist, now_utc

STAFF_STATUSES = ["assigned", "in_progress", "resolved"]
_RANK = {"waiting": 0, "assigned": 1, "in_progress": 2, "resolved": 3}


def _group_tickets(group_id: int, exclude_id: int) -> list[dict]:
    return [
        t for t in tdb.list_tickets(group_id=group_id)
        if t["id"] != exclude_id and t["dup_review"] != "separate"
    ]


def is_primary(ticket: dict) -> bool:
    """True if this ticket is the first (oldest) non-separated ticket of its group."""
    group = gdb.get_group(ticket["group_id"]) if ticket["group_id"] else None
    return bool(group and group["primary"] and group["primary"]["id"] == ticket["id"])


def set_status(ticket_id: int, status: str, note: str, staff: dict) -> None:
    """Staff status update with a note. If this is the group's primary ticket, linked tickets follow it.

    Raises ValueError for an unknown status, a missing resolution note, or a backwards move without a note.
    """
    if status not in STAFF_STATUSES:
        raise ValueError(f"Status must be one of {STAFF_STATUSES}.")
    ticket = tdb.get_ticket(ticket_id)
    if ticket is None:
        raise ValueError("Unknown ticket.")
    by = f"{staff['name']} (staff)"
    note = (note or "").strip() or None
    if status == "resolved" and not note:
        raise ValueError("Add a resolution note before marking this resolved.")
    if _RANK[status] < _RANK[ticket["status"]] and not note:
        raise ValueError("Add a note explaining why this ticket is moving back.")
    tdb.add_status(ticket_id, status, note, by)
    if not ticket["group_id"] or not is_primary(ticket):
        return
    group_fields = {"latest_note": note}
    if status == "resolved":
        group_fields |= {"status": "resolved", "resolved_at": now_utc()}
    else:
        group_fields |= {"status": "open", "resolved_at": None}
    gdb.update_group(ticket["group_id"], group_fields)
    for other in _group_tickets(ticket["group_id"], ticket_id):
        if other["self_resolved"] and status != "resolved":
            continue
        tdb.add_status(other["id"], status, f"Same issue as {ticket['code']}: {note or status.replace('_', ' ')}", by)
        if other["assigned_to"] != ticket["assigned_to"] and ticket["assigned_to"]:
            tdb.assign_ticket(other["id"], ticket["assigned_to"], by)


def set_eta(ticket_id: int, eta_at: datetime, staff: dict) -> None:
    """Staff promise a time for the fix. The student sees it on the ticket; a primary ticket's group and linked tickets follow."""
    ticket = tdb.get_ticket(ticket_id)
    if ticket is None:
        raise ValueError("Unknown ticket.")
    if ticket["status"] == "resolved":
        raise ValueError("This ticket is already resolved.")
    if eta_at <= now_utc():
        raise ValueError("Pick a time in the future.")
    by = f"{staff['name']} (staff)"
    text = f"Expected by {fmt_ist(eta_at)}."
    tdb.update_ticket(ticket_id, {"eta_at": eta_at})
    tdb.add_history(ticket_id, ticket["status"], text, by)
    if not ticket["group_id"] or not is_primary(ticket):
        return
    gdb.update_group(ticket["group_id"], {"eta_at": eta_at})
    for other in _group_tickets(ticket["group_id"], ticket_id):
        if other["self_resolved"]:
            continue
        tdb.update_ticket(other["id"], {"eta_at": eta_at})
        tdb.add_history(other["id"], other["status"], f"Same issue as {ticket['code']}. {text}", by)


def mark_self_resolved(ticket_id: int, student: dict) -> None:
    """Student says the problem is solved. The ticket is kept; only this ticket changes."""
    ticket = tdb.get_ticket(ticket_id)
    if not ticket or ticket["student_id"] != student["id"]:
        raise PermissionError("This is not your ticket.")
    tdb.update_ticket(ticket_id, {"self_resolved": True})
    tdb.add_status(ticket_id, "resolved", "Marked solved by the student.", f"{student['name']} (student)")


def add_internal_note(ticket_id: int, note: str, staff: dict) -> None:
    """Staff-only note on the timeline. Students never see it."""
    note = (note or "").strip()
    if not note:
        raise ValueError("Type a note first.")
    ticket = tdb.get_ticket(ticket_id)
    if ticket is None:
        raise ValueError("Unknown ticket.")
    tdb.add_history(ticket_id, ticket["status"], note, f"{staff['name']} (staff)", internal=True)


def override_urgency(ticket_id: int, urgency: str, staff: dict) -> None:
    """Pin the ticket's urgency tier (critical|high|normal|later). Logged as an internal history entry."""
    if urgency not in priority.TIER_ORDER:
        raise ValueError(f"Urgency must be one of {priority.TIER_ORDER}.")
    ticket = tdb.get_ticket(ticket_id)
    if ticket is None:
        raise ValueError("Unknown ticket.")
    old = ticket["urgency_override"] or ticket["tier"]
    if old == urgency:
        return
    tdb.update_ticket(ticket_id, {"urgency_override": urgency, "tier": urgency})
    labels = config.URGENCY_LABELS
    tdb.add_history(ticket_id, ticket["status"], f"Urgency changed from {labels[old]} to {labels[urgency]}.",
                    f"{staff['name']} (staff)", internal=True)


def override_category(ticket_id: int, category: str, staff: dict) -> None:
    """Move a ticket to another category (= department). It leaves its group, gets a fresh one and is re-assigned."""
    if category not in config.CATEGORIES:
        raise ValueError(f"Category must be one of {config.CATEGORIES}.")
    ticket = tdb.get_ticket(ticket_id)
    if ticket is None:
        raise ValueError("Unknown ticket.")
    if ticket["category"] == category:
        return
    old_group = ticket["group_id"]
    new_group = gdb.create_group(
        category, ticket["landmark_id"], ticket["floor"], ticket["title"],
        sorted(issue_tokens(ticket["description"] or ticket["title"])), ticket["map_x"], ticket["map_y"], ticket["eta_at"],
    )
    if ticket["student_id"]:
        if old_group:
            gdb.remove_ticket_report(old_group, ticket["student_id"])
        gdb.add_report(new_group, ticket["student_id"], ticket_id, "ticket")
    status = "waiting" if ticket["status"] == "assigned" else ticket["status"]
    tdb.update_ticket(ticket_id, {"category": category, "group_id": new_group, "dup_review": "none", "needs_review": False})
    labels = config.CATEGORY_LABELS
    tdb.add_history(ticket_id, status, f"Category changed from {labels[ticket['category']]} to {labels[category]}.",
                    f"{staff['name']} (staff)", internal=True)
    if ticket["status"] in ("waiting", "assigned"):
        tdb.clear_assignment(ticket_id)
        assignment.assign_new(ticket_id, category)
    alerts.evaluate_group(new_group)
    if old_group:
        alerts.evaluate_group(old_group)


def confirm_duplicate(ticket_id: int, staff: dict) -> None:
    """Staff confirm that a ticket is a duplicate of its group's primary ticket. It stays linked; the student is told."""
    ticket = tdb.get_ticket(ticket_id)
    if ticket is None:
        raise ValueError("Unknown ticket.")
    tdb.update_ticket(ticket_id, {"dup_review": "confirmed"})
    code = ticket["primary_code"] or "an existing ticket"
    tdb.add_history(ticket_id, ticket["status"], f"Duplicate of {code}", f"{staff['name']} (staff)")
    tdb.add_system_message(ticket_id, f"Staff checked your report: it is the same issue as {code}. "
                                      "You will get updates on that ticket's progress here.", f"{staff['name']} (staff)")


def separate_duplicate(ticket_id: int, staff: dict) -> None:
    """Staff say this is a different problem: unlink it into its own group and recount both groups."""
    ticket = tdb.get_ticket(ticket_id)
    if not ticket or not ticket["group_id"]:
        raise ValueError("Ticket has no group to separate from.")
    old_group_id = ticket["group_id"]
    code = ticket["primary_code"] or "another ticket"
    new_id = gdb.create_group(
        ticket["category"], ticket["landmark_id"], ticket["floor"], ticket["title"],
        sorted(issue_tokens(ticket["description"] or ticket["title"])), ticket["map_x"], ticket["map_y"], ticket["eta_at"],
    )
    if ticket["student_id"]:
        gdb.remove_ticket_report(old_group_id, ticket["student_id"])
        gdb.add_report(new_id, ticket["student_id"], ticket_id, "ticket")
    tdb.update_ticket(ticket_id, {"group_id": new_id, "dup_review": "separate"})
    tdb.add_history(ticket_id, ticket["status"], f"Staff reviewed: this is a separate issue from {code}.", f"{staff['name']} (staff)")
    tdb.add_system_message(ticket_id, f"Staff checked your report: it is a separate issue from {code} and is being handled on its own.",
                           f"{staff['name']} (staff)")
    alerts.evaluate_group(old_group_id)
    alerts.evaluate_group(new_id)
