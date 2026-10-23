"""SQLite helpers for CampusConnect."""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "campusconnect.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def get_conn() -> sqlite3.Connection:
    """Open a SQLite connection with row access by column name."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Create all tables by running schema.sql."""
    with get_conn() as conn:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))


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
