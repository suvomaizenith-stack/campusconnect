"""Ticket, status history and chat queries. All SQL is parameterised; no AI or UI code here."""
from db.db import get_conn

# Everything except the photo bytes, which are loaded separately.
_COLS = (
    "t.id, t.student_id, t.student_name, t.student_roll, t.title, t.description, t.category, t.severity,"
    " t.priority_score, t.tier, t.status, t.landmark_id, t.floor, t.room, t.nearby, t.map_x, t.map_y, t.group_id,"
    " t.dup_review, t.info_complete, t.needs_review, t.missing_fields, t.follow_up_question, t.assigned_to,"
    " t.eta_at, t.self_resolved, t.photo IS NOT NULL AS has_photo, t.photo_note, t.ai_mode, t.ai_confidence, t.language, t.urgency_override,"
    " t.created_at, t.updated_at, t.resolved_at,"
    " 'CC-' || lpad(t.id::text, 4, '0') AS code, l.name AS landmark, l.slug AS landmark_slug, s.name AS staff_name,"
    " g.title AS group_title, g.status AS group_status,"
    " (SELECT 'CC-' || lpad(p.id::text, 4, '0') FROM tickets p WHERE p.group_id = t.group_id"
    "  AND p.dup_review <> 'separate' ORDER BY p.id LIMIT 1) AS primary_code"
)
_FROM = (
    " FROM tickets t LEFT JOIN landmarks l ON l.id = t.landmark_id"
    " LEFT JOIN staff s ON s.id = t.assigned_to LEFT JOIN issue_groups g ON g.id = t.group_id"
)
_TIER_ORDER = "CASE t.tier WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'normal' THEN 2 ELSE 3 END"

CREATE_FIELDS = {
    "student_id", "student_name", "student_roll", "title", "description", "category", "severity",
    "priority_score", "tier", "status", "landmark_id", "floor", "room", "nearby", "map_x", "map_y", "group_id",
    "dup_review", "info_complete", "needs_review", "missing_fields", "follow_up_question", "assigned_to",
    "eta_at", "photo", "photo_mime", "photo_note", "ai_mode", "ai_confidence", "language", "urgency_override",
}
UPDATE_FIELDS = CREATE_FIELDS - {"student_id", "student_name", "student_roll", "photo", "photo_mime"} | {
    "self_resolved", "resolved_at"
}


def create_ticket(fields: dict) -> int:
    """Insert a ticket from a dict of allowed columns and return its id."""
    bad = set(fields) - CREATE_FIELDS
    if bad:
        raise ValueError(f"Unknown ticket fields: {sorted(bad)}")
    cols = ", ".join(fields)
    marks = ", ".join(["%s"] * len(fields))
    with get_conn() as conn:
        row = conn.execute(f"INSERT INTO tickets ({cols}) VALUES ({marks}) RETURNING id", list(fields.values())).fetchone()
    return row["id"]


def update_ticket(ticket_id: int, fields: dict) -> None:
    """Update allowed columns of a ticket and bump updated_at."""
    bad = set(fields) - UPDATE_FIELDS
    if bad:
        raise ValueError(f"Unknown ticket fields: {sorted(bad)}")
    if not fields:
        return
    sets = ", ".join(f"{k} = %s" for k in fields)
    with get_conn() as conn:
        conn.execute(f"UPDATE tickets SET {sets}, updated_at = now() WHERE id = %s", [*fields.values(), ticket_id])


def get_ticket(ticket_id: int) -> dict | None:
    """Return one ticket with code, landmark, staff and group info, or None."""
    with get_conn() as conn:
        return conn.execute(f"SELECT {_COLS}{_FROM} WHERE t.id = %s", (ticket_id,)).fetchone()


def get_ticket_photo(ticket_id: int) -> tuple[bytes, str] | None:
    """Return (photo bytes, mime type) or None."""
    with get_conn() as conn:
        row = conn.execute("SELECT photo, photo_mime FROM tickets WHERE id = %s", (ticket_id,)).fetchone()
    return (bytes(row["photo"]), row["photo_mime"] or "image/jpeg") if row and row["photo"] else None


def list_tickets(
    student_id: int | None = None,
    category: str | None = None,
    assigned_to: int | None = None,
    group_id: int | None = None,
    statuses: list[str] | None = None,
    dup_review: str | None = None,
    include_unassigned_for: str | None = None,
    search: str | None = None,
    limit: int = 200,
) -> list[dict]:
    """List tickets, most urgent first. Filters combine with AND.

    include_unassigned_for=<category>: also return unassigned tickets of that category
    (used with assigned_to for a staff queue).
    """
    where, params = [], []
    if student_id is not None:
        where.append("t.student_id = %s"); params.append(student_id)
    if category:
        where.append("t.category = %s"); params.append(category)
    if assigned_to is not None and include_unassigned_for:
        where.append("(t.assigned_to = %s OR (t.assigned_to IS NULL AND t.category = %s))")
        params += [assigned_to, include_unassigned_for]
    elif assigned_to is not None:
        where.append("t.assigned_to = %s"); params.append(assigned_to)
    if group_id is not None:
        where.append("t.group_id = %s"); params.append(group_id)
    if statuses:
        where.append("t.status = ANY(%s)"); params.append(statuses)
    if dup_review:
        where.append("t.dup_review = %s"); params.append(dup_review)
    if search and search.strip():
        q = search.strip()
        digits = "".join(c for c in q if c.isdigit())
        like = f"%{q}%"
        cond = "(l.name ILIKE %s OR t.title ILIKE %s OR t.room ILIKE %s"
        params += [like, like, like]
        if digits and (q.upper().startswith("CC") or q.isdigit() or q.startswith("#")):
            cond += " OR t.id = %s"; params.append(int(digits))
        where.append(cond + ")")
    clause = (" WHERE " + " AND ".join(where)) if where else ""
    order = f" ORDER BY {_TIER_ORDER}, t.priority_score DESC, t.created_at ASC LIMIT %s"
    with get_conn() as conn:
        return conn.execute(f"SELECT {_COLS}{_FROM}{clause}{order}", [*params, limit]).fetchall()


def waiting_tickets(category: str) -> list[dict]:
    """Unassigned waiting tickets of a category: priority tier first, then oldest."""
    with get_conn() as conn:
        return conn.execute(
            f"SELECT {_COLS}{_FROM} WHERE t.status = 'waiting' AND t.assigned_to IS NULL AND t.category = %s"
            f" ORDER BY {_TIER_ORDER}, t.created_at ASC",
            (category,),
        ).fetchall()


def open_ticket_counts(category: str) -> dict[int, int]:
    """Open (not resolved) ticket count per staff id for a category's department."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT assigned_to, count(*) AS n FROM tickets WHERE category = %s AND assigned_to IS NOT NULL"
            " AND status <> 'resolved' GROUP BY assigned_to",
            (category,),
        ).fetchall()
    return {r["assigned_to"]: r["n"] for r in rows}


def online_staff(department: str) -> list[dict]:
    """Online staff of a department, ordered by id."""
    with get_conn() as conn:
        return conn.execute(
            "SELECT id, name, department FROM staff WHERE department = %s AND is_online ORDER BY id", (department,)
        ).fetchall()


def add_history(ticket_id: int, status: str, note: str | None = None, changed_by: str | None = None,
                internal: bool = False) -> None:
    """Write a status_history row without changing the ticket. internal=True rows are staff-only."""
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO status_history (ticket_id, status, note, changed_by, internal) VALUES (%s, %s, %s, %s, %s)",
            (ticket_id, status, note, changed_by, internal),
        )


def add_status(ticket_id: int, status: str, note: str | None = None, changed_by: str | None = None) -> None:
    """Set the ticket status and record it in status_history."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE tickets SET status = %s, updated_at = now(),"
            " resolved_at = CASE WHEN %s = 'resolved' THEN now() ELSE NULL END WHERE id = %s",
            (status, status, ticket_id),
        )
        conn.execute(
            "INSERT INTO status_history (ticket_id, status, note, changed_by) VALUES (%s, %s, %s, %s)",
            (ticket_id, status, note, changed_by),
        )


def clear_assignment(ticket_id: int) -> None:
    """Remove the assignee and put the ticket back to waiting."""
    with get_conn() as conn:
        conn.execute("UPDATE tickets SET assigned_to = NULL, status = 'waiting', updated_at = now() WHERE id = %s", (ticket_id,))


_ANY = object()


def assign_ticket(ticket_id: int, staff_id: int, changed_by: str | None = None, expected=_ANY) -> bool:
    """Assign a ticket to a staff member (status becomes 'assigned' if it was waiting) and log it.

    expected: the assigned_to value the caller last saw (None = unassigned). If someone changed it since,
    nothing is written and False is returned, so two staff cannot silently overwrite each other.
    """
    with get_conn() as conn:
        staff = conn.execute("SELECT name FROM staff WHERE id = %s", (staff_id,)).fetchone()
        if not staff:
            raise ValueError("Unknown staff member.")
        guard, extra = ("", []) if expected is _ANY else (" AND assigned_to IS NOT DISTINCT FROM %s", [expected])
        row = conn.execute(
            "UPDATE tickets SET assigned_to = %s, updated_at = now(),"
            " status = CASE WHEN status = 'waiting' THEN 'assigned' ELSE status END WHERE id = %s"
            + guard + " RETURNING status",
            [staff_id, ticket_id, *extra],
        ).fetchone()
        if row is None:
            return False
        conn.execute(
            "INSERT INTO status_history (ticket_id, status, note, changed_by) VALUES (%s, %s, %s, %s)",
            (ticket_id, row["status"], f"Assigned to {staff['name']}", changed_by),
        )
    return True


def get_history(ticket_id: int, include_internal: bool = False) -> list[dict]:
    """Return status_history rows oldest first. Internal (staff-only) notes are excluded unless asked for."""
    with get_conn() as conn:
        return conn.execute(
            "SELECT status, note, changed_by, internal, changed_at FROM status_history"
            " WHERE ticket_id = %s AND (internal = FALSE OR %s) ORDER BY id",
            (ticket_id, include_internal),
        ).fetchall()


def _can_chat(conn, ticket_id: int, viewer: dict) -> dict:
    """Return the ticket row if the viewer is its student or its assigned staff, else raise PermissionError."""
    t = conn.execute("SELECT id, student_id, assigned_to FROM tickets WHERE id = %s", (ticket_id,)).fetchone()
    if not t:
        raise PermissionError("Ticket not found.")
    if viewer["role"] == "student" and t["student_id"] == viewer["id"]:
        return t
    if viewer["role"] == "staff" and t["assigned_to"] == viewer["id"]:
        return t
    raise PermissionError("You do not have access to this ticket's chat.")


def add_message(ticket_id: int, viewer: dict, body: str) -> None:
    """Post a chat message as the ticket's student or assigned staff. Raises PermissionError otherwise."""
    body = body.strip()
    if not body:
        raise ValueError("Message is empty.")
    with get_conn() as conn:
        _can_chat(conn, ticket_id, viewer)
        conn.execute(
            "INSERT INTO ticket_messages (ticket_id, sender_role, sender_name, body) VALUES (%s, %s, %s, %s)",
            (ticket_id, viewer["role"], viewer["name"], body[:2000]),
        )


def get_messages(ticket_id: int, viewer: dict) -> list[dict]:
    """Return chat messages oldest first. Raises PermissionError for anyone but the student or assigned staff."""
    with get_conn() as conn:
        _can_chat(conn, ticket_id, viewer)
        return conn.execute(
            "SELECT id, sender_role, sender_name, body, created_at FROM ticket_messages"
            " WHERE ticket_id = %s ORDER BY id",
            (ticket_id,),
        ).fetchall()


def department_metrics(category: str) -> dict:
    """Counts and pace for a department: open, in_progress, waiting, resolved_today, avg_resolution_hours, resolved_per_day."""
    with get_conn() as conn:
        counts = conn.execute(
            "SELECT count(*) FILTER (WHERE status IN ('assigned','in_progress','waiting')) AS open,"
            " count(*) FILTER (WHERE status = 'in_progress') AS in_progress,"
            " count(*) FILTER (WHERE status = 'waiting') AS waiting,"
            " count(*) FILTER (WHERE status = 'resolved' AND resolved_at >= date_trunc('day', now())) AS resolved_today,"
            " coalesce(round((avg(extract(epoch FROM resolved_at - created_at)) FILTER (WHERE status = 'resolved') / 3600)::numeric, 1), 0)"
            " AS avg_hours FROM tickets WHERE category = %s",
            (category,),
        ).fetchone()
        per_day = conn.execute(
            "SELECT d::date AS day, count(t.id) AS n FROM generate_series(now() - interval '6 days', now(), interval '1 day') d"
            " LEFT JOIN tickets t ON t.category = %s AND t.status = 'resolved' AND t.resolved_at::date = d::date"
            " GROUP BY d ORDER BY d",
            (category,),
        ).fetchall()
    return {**counts, "avg_hours": float(counts["avg_hours"]), "per_day": [(r["day"], r["n"]) for r in per_day]}


def add_system_message(ticket_id: int, body: str, sender_name: str = "Campus Saathi Assistant") -> None:
    """Post an assistant message (follow-up question, acknowledgement) to a ticket's chat."""
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO ticket_messages (ticket_id, sender_role, sender_name, body) VALUES (%s, 'assistant', %s, %s)",
            (ticket_id, sender_name, body[:2000]),
        )


def status_counts(category: str | None = None) -> dict:
    """Counts for the dashboard cards: new, needs_info, in_progress, resolved_today (category None = all)."""
    with get_conn() as conn:
        return conn.execute(
            "SELECT count(*) FILTER (WHERE status IN ('waiting','assigned') AND info_complete) AS new,"
            " count(*) FILTER (WHERE status <> 'resolved' AND NOT info_complete) AS needs_info,"
            " count(*) FILTER (WHERE status = 'in_progress') AS in_progress,"
            " count(*) FILTER (WHERE status = 'resolved' AND resolved_at >= date_trunc('day', now())) AS resolved_today"
            " FROM tickets WHERE (%s::text IS NULL OR category = %s)",
            (category, category),
        ).fetchone()


def first_response_times(ticket_ids: list[int]) -> dict[int, object]:
    """Time of the first staff-made history entry per ticket (assignment or status change by a person)."""
    if not ticket_ids:
        return {}
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT ticket_id, min(changed_at) AS at FROM status_history WHERE ticket_id = ANY(%s)"
            " AND changed_by LIKE %s GROUP BY ticket_id",
            (ticket_ids, "% (staff)"),
        ).fetchall()
    return {r["ticket_id"]: r["at"] for r in rows}


def recurring_locations(days: int, min_count: int) -> list[dict]:
    """Landmark + category pairs with at least min_count tickets in the last N days, highest count first."""
    with get_conn() as conn:
        return conn.execute(
            "SELECT l.id AS landmark_id, l.name AS landmark, l.slug AS landmark_slug, t.category, count(*) AS count"
            " FROM tickets t JOIN landmarks l ON l.id = t.landmark_id"
            " WHERE t.created_at >= now() - make_interval(days => %s)"
            " GROUP BY l.id, l.name, l.slug, t.category HAVING count(*) >= %s ORDER BY count(*) DESC, l.name",
            (days, min_count),
        ).fetchall()


def tickets_by_category(days: int) -> list[dict]:
    """Ticket counts per category over the last N days."""
    with get_conn() as conn:
        return conn.execute(
            "SELECT category, count(*) AS count FROM tickets WHERE created_at >= now() - make_interval(days => %s)"
            " GROUP BY category ORDER BY category",
            (days,),
        ).fetchall()


def top_locations(days: int, limit: int = 5) -> list[dict]:
    """Locations with the most tickets in the last N days, each with its most frequent category."""
    with get_conn() as conn:
        return conn.execute(
            "SELECT l.name AS landmark, count(*) AS count, mode() WITHIN GROUP (ORDER BY t.category) AS top_category"
            " FROM tickets t JOIN landmarks l ON l.id = t.landmark_id"
            " WHERE t.created_at >= now() - make_interval(days => %s)"
            " GROUP BY l.name ORDER BY count(*) DESC, l.name LIMIT %s",
            (days, limit),
        ).fetchall()


def avg_resolution_by_category() -> list[dict]:
    """Average hours from creation to resolution per category (resolved tickets only)."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT category, round((avg(extract(epoch FROM resolved_at - created_at)) / 3600)::numeric, 1) AS hours,"
            " count(*) AS resolved FROM tickets WHERE status = 'resolved' AND resolved_at IS NOT NULL"
            " GROUP BY category ORDER BY category"
        ).fetchall()
    return [{**r, "hours": float(r["hours"])} for r in rows]
