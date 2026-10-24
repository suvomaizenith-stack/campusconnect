"""Remembered-device tokens for students. Only a hash of the token is stored."""
from db.db import get_conn

MAX_PER_STUDENT = 5  # oldest devices are signed out beyond this


def add(token_hash: str, student_id: int, days: int) -> None:
    """Store a new device token, drop expired ones and keep only the newest few for this student."""
    with get_conn() as conn:
        conn.execute("DELETE FROM device_tokens WHERE expires_at < now()")
        conn.execute(
            "INSERT INTO device_tokens (token_hash, student_id, expires_at)"
            " VALUES (%s, %s, now() + make_interval(days => %s))",
            (token_hash, student_id, days),
        )
        conn.execute(
            "DELETE FROM device_tokens WHERE student_id = %s AND token_hash NOT IN"
            " (SELECT token_hash FROM device_tokens WHERE student_id = %s ORDER BY created_at DESC LIMIT %s)",
            (student_id, student_id, MAX_PER_STUDENT),
        )


def student_for(token_hash: str) -> dict | None:
    """Return the student (id, name, roll_no) for a valid, unexpired token hash, else None."""
    with get_conn() as conn:
        return conn.execute(
            "SELECT s.id, s.name, s.roll_no FROM device_tokens d JOIN students s ON s.id = d.student_id"
            " WHERE d.token_hash = %s AND d.expires_at > now()",
            (token_hash,),
        ).fetchone()


def remove(token_hash: str) -> None:
    """Forget one device."""
    with get_conn() as conn:
        conn.execute("DELETE FROM device_tokens WHERE token_hash = %s", (token_hash,))
