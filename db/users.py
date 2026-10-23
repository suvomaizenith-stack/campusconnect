"""Student and staff account queries. Hashing and rules live in logic/auth.py."""
import psycopg.errors

from db.db import get_conn

_LOGIN_TABLES = {"students", "staff"}  # table names are never taken from user input


def create_student(name: str, roll_no: str, pin_hash: str) -> dict:
    """Insert a student and return the row. Raises ValueError if the roll number is taken."""
    try:
        with get_conn() as conn:
            return conn.execute(
                "INSERT INTO students (name, roll_no, pin_hash) VALUES (%s, %s, %s) RETURNING *",
                (name, roll_no, pin_hash),
            ).fetchone()
    except psycopg.errors.UniqueViolation as e:
        raise ValueError("That roll number is already registered. Please log in.") from e


def get_student_by_roll(roll_no: str) -> dict | None:
    """Return the student with this roll number, or None."""
    with get_conn() as conn:
        return conn.execute("SELECT * FROM students WHERE roll_no = %s", (roll_no,)).fetchone()


def get_staff_by_username(username: str) -> dict | None:
    """Return the staff row with this username, or None."""
    with get_conn() as conn:
        return conn.execute("SELECT * FROM staff WHERE username = %s", (username,)).fetchone()


def get_staff(staff_id: int) -> dict | None:
    """Return the staff row with this id, or None."""
    with get_conn() as conn:
        return conn.execute("SELECT * FROM staff WHERE id = %s", (staff_id,)).fetchone()


def list_staff() -> list[dict]:
    """Return all staff (without secrets), ordered by department."""
    with get_conn() as conn:
        return conn.execute(
            "SELECT id, username, name, department, role, is_online FROM staff ORDER BY department, name"
        ).fetchall()


def upsert_staff(username: str, name: str, department: str, access_key_hash: str, role: str = "staff") -> None:
    """Create a staff account, or replace the access key of an existing username."""
    if role not in ("staff", "admin"):
        raise ValueError("role must be 'staff' or 'admin'")
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO staff (username, name, department, role, access_key_hash) VALUES (%s, %s, %s, %s, %s)"
            " ON CONFLICT (username) DO UPDATE SET access_key_hash = EXCLUDED.access_key_hash,"
            " name = EXCLUDED.name, department = EXCLUDED.department, role = EXCLUDED.role,"
            " failed_attempts = 0, locked_until = NULL",
            (username, name, department, role, access_key_hash),
        )


def record_login_failure(table: str, user_id: int, max_attempts: int, lock_minutes: int) -> None:
    """Count a failed login; lock the account for lock_minutes once max_attempts is reached."""
    if table not in _LOGIN_TABLES:
        raise ValueError("unknown table")
    with get_conn() as conn:
        conn.execute(
            f"UPDATE {table} SET failed_attempts = failed_attempts + 1,"
            " locked_until = CASE WHEN failed_attempts + 1 >= %s"
            " THEN now() + make_interval(mins => %s) ELSE locked_until END WHERE id = %s",
            (max_attempts, lock_minutes, user_id),
        )


def reset_login_failures(table: str, user_id: int) -> None:
    """Clear the failed-attempt counter and any lock after a successful login."""
    if table not in _LOGIN_TABLES:
        raise ValueError("unknown table")
    with get_conn() as conn:
        conn.execute(f"UPDATE {table} SET failed_attempts = 0, locked_until = NULL WHERE id = %s", (user_id,))


def is_locked(table: str, user_id: int) -> bool:
    """Return True if the account's lock has not expired yet."""
    if table not in _LOGIN_TABLES:
        raise ValueError("unknown table")
    with get_conn() as conn:
        row = conn.execute(
            f"SELECT locked_until IS NOT NULL AND locked_until > now() AS locked FROM {table} WHERE id = %s",
            (user_id,),
        ).fetchone()
    return bool(row and row["locked"])


def set_staff_online(staff_id: int, online: bool) -> None:
    """Mark a staff member online or offline."""
    with get_conn() as conn:
        conn.execute("UPDATE staff SET is_online = %s WHERE id = %s", (online, staff_id))
