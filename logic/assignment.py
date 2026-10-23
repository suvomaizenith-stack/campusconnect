"""Who gets a ticket: online staff in the department with the fewest open tickets, else it waits."""
from db import tickets as tdb
from db import users


def choose_staff(online: list[dict], open_counts: dict[int, int]) -> dict | None:
    """Pick the online staff member with the fewest open tickets (lowest id breaks ties)."""
    if not online:
        return None
    return min(online, key=lambda s: (open_counts.get(s["id"], 0), s["id"]))


def pick_staff(category: str) -> dict | None:
    """Best online staff member for a category, or None if nobody is online."""
    return choose_staff(tdb.online_staff(category), tdb.open_ticket_counts(category))


def assign_new(ticket_id: int, category: str) -> dict | None:
    """Assign a fresh ticket automatically. Returns the staff dict, or None if it stays waiting."""
    staff = pick_staff(category)
    if staff:
        tdb.assign_ticket(ticket_id, staff["id"], "System")
    else:
        tdb.add_history(ticket_id, "waiting", "No staff online in this department yet. Waiting for someone to come online.", "System")
    return staff


def go_online(staff: dict) -> int:
    """Mark staff online and assign waiting tickets of their department (priority first, then oldest).

    Returns how many tickets were assigned.
    """
    users.set_staff_online(staff["id"], True)
    assigned = 0
    for t in tdb.waiting_tickets(staff["department"]):
        chosen = pick_staff(staff["department"])
        if chosen is None:
            break
        tdb.assign_ticket(t["id"], chosen["id"], "System")
        assigned += 1
    return assigned


def go_offline(staff: dict) -> None:
    """Mark staff offline. Their tickets stay assigned to them."""
    users.set_staff_online(staff["id"], False)


def assign_to_me(ticket: dict, staff: dict) -> str | None:
    """Staff takes a ticket. Returns an error message to show, or None on success.

    'Already assigned' if someone else took it since the page loaded; offline staff cannot take tickets.
    """
    current = users.get_staff(staff["id"])
    if not current or not current["is_online"]:
        return "You are offline. Go online to receive tickets."
    if ticket["assigned_to"] == staff["id"]:
        return None
    if not tdb.assign_ticket(ticket["id"], staff["id"], f"{staff['name']} (staff)", expected=ticket["assigned_to"]):
        return "Already assigned"
    return None


def auto_assign(ticket: dict, staff: dict) -> str | None:
    """Give the ticket to the best online person in its department. Returns an error message or None."""
    chosen = pick_staff(ticket["category"])
    if chosen is None:
        return "Nobody in this department is online."
    if not tdb.assign_ticket(ticket["id"], chosen["id"], f"{staff['name']} (staff)", expected=ticket["assigned_to"]):
        return "Already assigned"
    return None


def reassign(ticket: dict, staff_id: int, by: str) -> str | None:
    """Manually assign or reassign. Returns 'Already assigned' if the ticket changed hands since it was loaded."""
    if not tdb.assign_ticket(ticket["id"], staff_id, by, expected=ticket["assigned_to"]):
        return "Already assigned"
    return None
