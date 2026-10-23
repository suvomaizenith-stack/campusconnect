"""Password hashing and login validation."""
import hashlib
import hmac
import os
import re

from db.db import find_staff_by_email

PBKDF2_ITERS = 100_000
ROLL_RE = re.compile(r"^[A-Za-z0-9/-]{3,20}$")


def hash_password(password: str, salt: bytes | None = None) -> str:
    """Return 'salt$hash' using PBKDF2-SHA256."""
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERS)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Check a password against a 'salt$hash' string."""
    salt = bytes.fromhex(stored.split("$", 1)[0])
    candidate = hash_password(password, salt)
    return hmac.compare_digest(candidate, stored)


def authenticate_staff(username: str, password: str) -> dict | None:
    """Return staff identity for a valid email/password pair, else None."""
    staff = find_staff_by_email(username.strip().lower())
    if not staff or not verify_password(password, staff["password_hash"]):
        return None
    return {"id": staff["id"], "name": staff["name"], "department": staff["department"]}


def clean_student(name: str, roll: str) -> tuple[str, str]:
    """Validate and trim student name and roll number. Raises ValueError."""
    name, roll = name.strip(), roll.strip().upper()
    if not name:
        raise ValueError("Please enter your name.")
    if not ROLL_RE.match(roll):
        raise ValueError("Roll number should be 3-20 letters, digits, '/' or '-'.")
    return name, roll
