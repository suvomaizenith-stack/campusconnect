"""Supabase Postgres helpers for CampusConnect. Connections come from a shared pool."""
import threading
from pathlib import Path

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from config import DATABASE_URL

SCHEMA_PATH = Path(__file__).resolve().parent / "schema_postgres.sql"

# Columns added after the base schema; ADD COLUMN IF NOT EXISTS keeps this re-runnable.
ADDED_COLUMNS = [
    "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS student_roll TEXT",
    "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS student_name TEXT",
    "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS photo BYTEA",
    "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS photo_mime TEXT",
    "ALTER TABLE status_history ADD COLUMN IF NOT EXISTS note TEXT",
]

_pool: ConnectionPool | None = None
_pool_lock = threading.Lock()


def _get_pool() -> ConnectionPool:
    """Create the shared pool on first use, so importing this module never connects."""
    global _pool
    with _pool_lock:
        if _pool is None:
            if not DATABASE_URL:
                raise RuntimeError("DATABASE_URL is not set. Add your Supabase URL to .env.")
            # prepare_threshold=None: Supabase's transaction pooler does not support prepared statements.
            _pool = ConnectionPool(
                DATABASE_URL,
                min_size=1,
                max_size=5,
                kwargs={"row_factory": dict_row, "prepare_threshold": None},
            )
        return _pool


def get_conn():
    """Context manager yielding a pooled connection. Commits on success, rolls back on error."""
    return _get_pool().connection()


def migrate(conn) -> None:
    """Add columns that are missing from the base schema. Safe to run repeatedly."""
    for ddl in ADDED_COLUMNS:
        conn.execute(ddl)


def init_db() -> None:
    """Create tables and RLS from schema_postgres.sql, then apply added columns."""
    with get_conn() as conn:
        conn.execute(SCHEMA_PATH.read_text(encoding="utf-8"))
        migrate(conn)


def find_staff_by_email(email: str) -> dict | None:
    """Return the staff row with this email, or None."""
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM staff WHERE email = %s", (email,)).fetchone()
    return dict(row) if row else None


def upsert_landmarks(landmarks: list[dict]) -> None:
    """Insert landmarks by name, skipping ones that already exist."""
    with get_conn() as conn:
        conn.cursor().executemany(
            "INSERT INTO landmarks (name, lat, lng) VALUES (%(name)s, %(lat)s, %(lng)s)"
            " ON CONFLICT (name) DO NOTHING",
            landmarks,
        )


def create_ticket(title: str, description: str, category: str, student_email: str) -> int:
    """Insert a new ticket and return its id."""
    raise NotImplementedError


def assign_ticket(ticket_id: int, staff_id: int) -> None:
    """Assign a ticket to a staff member."""
    raise NotImplementedError


def add_status(ticket_id: int, status: str, changed_by: int | None = None) -> None:
    """Update ticket status and record it in status_history."""
    raise NotImplementedError


def add_comment(ticket_id: int, author: str, body: str) -> None:
    """Add a comment to a ticket."""
    raise NotImplementedError


def set_staff_online(staff_id: int, online: bool) -> None:
    """Mark a staff member online or offline."""
    raise NotImplementedError
