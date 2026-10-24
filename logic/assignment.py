"""Who gets a ticket: the staff in the department with the fewest open tickets, else it waits."""
from db import tickets as tdb


def choose_staff(staff: list[dict], open_counts: dict[int, int]) -> dict | None:
    """Pick the staff member with the fewest open tickets (lowest id breaks ties)."""
    if not staff:
        return None
    return min(staff, key=lambda s: (open_counts.get(s["id"], 0), s["id"]))


def pick_staff(category: str) -> dict | None:
    """Best staff member for a category, or None if the department has no staff."""
    return choose_staff(tdb.department_staff(category), tdb.open_ticket_counts(category))


def assign_new(ticket_id: int, category: str) -> dict | None:
    """Assign a fresh ticket automatically. Returns the staff dict, or None if it stays waiting."""
    staff = pick_staff(category)
    if staff:
        tdb.assign_ticket(ticket_id, staff["id"], "System")
    else:
        tdb.add_history(ticket_id, "waiting", "No staff in this department yet. Waiting for a staff member.", "System")
    return staff


def assign_to_me(ticket: dict, staff: dict) -> str | None:
    """Staff takes a ticket. Returns an error message to show, or None on success."""
    if ticket["assigned_to"] == staff["id"]:
        return None
    if not tdb.assign_ticket(ticket["id"], staff["id"], f"{staff['name']} (staff)", expected=ticket["assigned_to"]):
        return "Already assigned"
    return None


def auto_assign(ticket: dict, staff: dict) -> str | None:
    """Give the ticket to the best person in its department. Returns an error message or None."""
    chosen = pick_staff(ticket["category"])
    if chosen is None:
        return "No staff in this department."
    if not tdb.assign_ticket(ticket["id"], chosen["id"], f"{staff['name']} (staff)", expected=ticket["assigned_to"]):
        return "Already assigned"
    return None


def reassign(ticket: dict, staff_id: int, by: str) -> str | None:
    """Manually assign or reassign. Returns 'Already assigned' if the ticket changed hands since it was loaded."""
    if not tdb.assign_ticket(ticket["id"], staff_id, by, expected=ticket["assigned_to"]):
        return "Already assigned"
    return None
