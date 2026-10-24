"""Keep a student signed in on one device with a random token in a cookie (students only, never staff)."""
import hashlib
import secrets

from db import devices

COOKIE = "cc_device"
DAYS = 30


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def issue(student_id: int) -> str:
    """Create and store a token for this device. Returns the raw token to put in the cookie."""
    token = secrets.token_urlsafe(32)
    devices.add(_hash(token), student_id, DAYS)
    return token


def restore(token: str | None) -> dict | None:
    """Return the student identity {id, name, roll} for a valid cookie token, else None."""
    if not token or len(token) > 100:
        return None
    row = devices.student_for(_hash(token))
    return {"id": row["id"], "name": row["name"], "roll": row["roll_no"]} if row else None


def forget(token: str | None) -> None:
    """Invalidate a token (used on log out)."""
    if token:
        devices.remove(_hash(token))
