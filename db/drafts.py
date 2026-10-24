"""Student report drafts: unsent problems saved for later. Every query is scoped to one student."""
from db.db import get_conn


def list_drafts(student_id: int) -> list[dict]:
    """The student's drafts, most recently saved first."""
    with get_conn() as conn:
        return conn.execute(
            "SELECT id, title, location, kind, details, updated_at FROM drafts"
            " WHERE student_id = %s ORDER BY updated_at DESC, id DESC",
            (student_id,),
        ).fetchall()


def save_draft(student_id: int, title: str, location: str | None, kind: str | None, details: str | None) -> int:
    """Insert a draft and return its id."""
    with get_conn() as conn:
        return conn.execute(
            "INSERT INTO drafts (student_id, title, location, kind, details) VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (student_id, title, location, kind, details),
        ).fetchone()["id"]


def delete_draft(student_id: int, draft_id: int) -> None:
    """Remove one of the student's drafts. Other students' drafts are never touched."""
    with get_conn() as conn:
        conn.execute("DELETE FROM drafts WHERE id = %s AND student_id = %s", (draft_id, student_id))
