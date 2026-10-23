"""Ticket chat between a student and the assigned staff member. Access is enforced in the db layer."""
from ai import triage
from db import tickets as tdb
from logic import alerts


def get_thread(ticket_id: int, viewer: dict) -> list[dict]:
    """Messages oldest first. Raises PermissionError for anyone but the ticket's student or assigned staff."""
    return tdb.get_messages(ticket_id, viewer)


def send_chat(ticket_id: int, viewer: dict, body: str) -> bool:
    """Post a message. If a student answers the follow-up question on an incomplete ticket, the AI merges the
    answer into the ticket, marks it complete and logs 'details added'. Returns True if details were merged.
    """
    tdb.add_message(ticket_id, viewer, body)
    if viewer["role"] != "student":
        return False
    ticket = tdb.get_ticket(ticket_id)
    if ticket["info_complete"]:
        return False
    merged = triage.merge_answer(ticket, body)
    tdb.update_ticket(ticket_id, {
        "description": merged["description"], "room": merged["room"], "nearby": merged["nearby"],
        "title": merged["summary"], "severity": merged["severity"], "needs_review": merged["needs_review"],
        "info_complete": True, "missing_fields": [], "follow_up_question": None,
    })
    tdb.add_history(ticket_id, ticket["status"], "Details added by the student.", f"{viewer['name']} (student)")
    tdb.add_system_message(ticket_id, "Thanks! I added those details to your ticket.")
    if ticket["group_id"]:
        alerts.evaluate_group(ticket["group_id"])
    return True
