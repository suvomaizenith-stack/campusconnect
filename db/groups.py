"""Issue groups (one per real-world problem), per-student reports and alerts."""
from db.db import get_conn

_GROUP_COLS = (
    "g.id, g.category, g.landmark_id, g.floor, g.title, g.keywords, g.status, g.level, g.map_x, g.map_y, g.eta_at,"
    " g.latest_note, g.first_reported_at, g.last_reported_at, g.resolved_at, l.name AS landmark, l.slug AS landmark_slug"
)
_GROUP_FROM = " FROM issue_groups g LEFT JOIN landmarks l ON l.id = g.landmark_id"
_UPDATE_FIELDS = {"category", "title", "keywords", "status", "level", "eta_at", "latest_note", "last_reported_at", "resolved_at", "map_x", "map_y"}


def create_group(category: str, landmark_id: int | None, floor: str | None, title: str,
                 keywords: list[str], map_x: float | None, map_y: float | None, eta_at=None) -> int:
    """Insert a new issue group and return its id."""
    with get_conn() as conn:
        return conn.execute(
            "INSERT INTO issue_groups (category, landmark_id, floor, title, keywords, map_x, map_y, eta_at)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
            (category, landmark_id, floor, title, keywords, map_x, map_y, eta_at),
        ).fetchone()["id"]


def get_group(group_id: int) -> dict | None:
    """Return a group with its landmark name, plus primary ticket code/staff/status and the live report count."""
    with get_conn() as conn:
        g = conn.execute(f"SELECT {_GROUP_COLS}{_GROUP_FROM} WHERE g.id = %s", (group_id,)).fetchone()
        if not g:
            return None
        p = conn.execute(
            "SELECT t.id, 'CC-' || lpad(t.id::text, 4, '0') AS code, t.status, t.eta_at, s.name AS staff_name"
            " FROM tickets t LEFT JOIN staff s ON s.id = t.assigned_to"
            " WHERE t.group_id = %s AND t.dup_review <> 'separate' ORDER BY t.id LIMIT 1",
            (group_id,),
        ).fetchone()
        n = conn.execute("SELECT count(*) AS n FROM group_reports WHERE group_id = %s", (group_id,)).fetchone()["n"]
    return {**g, "primary": p, "report_count": n}


def update_group(group_id: int, fields: dict) -> None:
    """Update allowed group columns."""
    bad = set(fields) - _UPDATE_FIELDS
    if bad:
        raise ValueError(f"Unknown group fields: {sorted(bad)}")
    if not fields:
        return
    sets = ", ".join(f"{k} = %s" for k in fields)
    with get_conn() as conn:
        conn.execute(f"UPDATE issue_groups SET {sets} WHERE id = %s", [*fields.values(), group_id])


def candidate_groups(category: str, landmark_id: int | None, resolved_within_hours: int) -> list[dict]:
    """Groups of this category and landmark that are open, or were resolved within the given hours."""
    with get_conn() as conn:
        return conn.execute(
            f"SELECT {_GROUP_COLS}{_GROUP_FROM} WHERE g.category = %s AND g.landmark_id IS NOT DISTINCT FROM %s::bigint"
            " AND (g.status <> 'resolved' OR g.resolved_at >= now() - make_interval(hours => %s))"
            " ORDER BY g.first_reported_at",
            (category, landmark_id, resolved_within_hours),
        ).fetchall()


def add_report(group_id: int, student_id: int, ticket_id: int | None, source: str = "ticket") -> bool:
    """Record that a student faces this problem. Returns False if they already reported it."""
    with get_conn() as conn:
        row = conn.execute(
            "INSERT INTO group_reports (group_id, student_id, ticket_id, source) VALUES (%s, %s, %s, %s)"
            " ON CONFLICT (group_id, student_id) DO NOTHING RETURNING id",
            (group_id, student_id, ticket_id, source),
        ).fetchone()
        if row:
            conn.execute("UPDATE issue_groups SET last_reported_at = now() WHERE id = %s", (group_id,))
    return row is not None


def remove_ticket_report(group_id: int, student_id: int) -> None:
    """Drop a student's report from a group (used when staff mark their ticket as separate)."""
    with get_conn() as conn:
        conn.execute("DELETE FROM group_reports WHERE group_id = %s AND student_id = %s", (group_id, student_id))


def student_reported(group_id: int, student_id: int) -> bool:
    """True if this student already has a report in the group."""
    with get_conn() as conn:
        return conn.execute(
            "SELECT 1 FROM group_reports WHERE group_id = %s AND student_id = %s", (group_id, student_id)
        ).fetchone() is not None


def count_reports(group_id: int, hours: int) -> int:
    """Number of reports in the group within the last N hours."""
    with get_conn() as conn:
        return conn.execute(
            "SELECT count(*) AS n FROM group_reports WHERE group_id = %s AND created_at >= now() - make_interval(hours => %s)",
            (group_id, hours),
        ).fetchone()["n"]


def max_severity(group_id: int) -> int:
    """Highest severity among the group's linked tickets (1 if none)."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT coalesce(max(severity), 1) AS s FROM tickets WHERE group_id = %s AND dup_review <> 'separate'",
            (group_id,),
        ).fetchone()
    return row["s"]


def groups_for_map(hours: int, category: str | None = None, resolved_hours: int = 24) -> list[dict]:
    """Groups with a report in the last N hours (or resolved within resolved_hours), with window report counts."""
    with get_conn() as conn:
        return conn.execute(
            f"SELECT {_GROUP_COLS}, count(r.id) FILTER (WHERE r.created_at >= now() - make_interval(hours => %s)) AS window_count,"
            " count(r.id) AS report_count"
            f"{_GROUP_FROM} LEFT JOIN group_reports r ON r.group_id = g.id"
            " WHERE (%s::text IS NULL OR g.category = %s) AND (g.map_x IS NOT NULL OR g.landmark_id IS NOT NULL)"
            " GROUP BY g.id, l.name, l.slug HAVING"
            " (g.status <> 'resolved' AND count(r.id) FILTER (WHERE r.created_at >= now() - make_interval(hours => %s)) > 0)"
            " OR (g.resolved_at >= now() - make_interval(hours => %s))"
            " ORDER BY g.first_reported_at",
            (hours, category, category, hours, resolved_hours),
        ).fetchall()


def create_alert(group_id: int, level: str, message: str) -> int | None:
    """Create an alert unless an unacknowledged one of the same level exists for the group."""
    with get_conn() as conn:
        exists = conn.execute(
            "SELECT 1 FROM alerts WHERE group_id = %s AND level = %s AND acknowledged_at IS NULL", (group_id, level)
        ).fetchone()
        if exists:
            return None
        return conn.execute(
            "INSERT INTO alerts (group_id, level, message) VALUES (%s, %s, %s) RETURNING id",
            (group_id, level, message),
        ).fetchone()["id"]


def list_alerts(category: str | None = None, only_open: bool = True) -> list[dict]:
    """Alerts newest first with group info. only_open hides acknowledged ones."""
    with get_conn() as conn:
        return conn.execute(
            "SELECT a.id, a.group_id, a.level, a.message, a.created_at, a.acknowledged_by, a.acknowledged_at,"
            " g.title, g.category, l.name AS landmark FROM alerts a JOIN issue_groups g ON g.id = a.group_id"
            " LEFT JOIN landmarks l ON l.id = g.landmark_id"
            " WHERE (%s::text IS NULL OR g.category = %s) AND (NOT %s OR a.acknowledged_at IS NULL)"
            " ORDER BY a.created_at DESC",
            (category, category, only_open),
        ).fetchall()


def acknowledge_alert(alert_id: int, staff_name: str) -> None:
    """Mark an alert acknowledged."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE alerts SET acknowledged_by = %s, acknowledged_at = now() WHERE id = %s AND acknowledged_at IS NULL",
            (staff_name, alert_id),
        )


def open_group_at(landmark_id: int, category: str) -> dict | None:
    """Most recently reported unresolved group for a place and category, or None."""
    with get_conn() as conn:
        return conn.execute(
            "SELECT id, title FROM issue_groups WHERE landmark_id = %s AND category = %s AND status <> 'resolved'"
            " ORDER BY last_reported_at DESC LIMIT 1",
            (landmark_id, category),
        ).fetchone()
