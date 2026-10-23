"""Password hashing, signup and login rules for students (roll number + PIN) and staff (username + access key)."""
import hashlib
import hmac
import os
import re
import secrets

import config
from db import users

PBKDF2_ITERS = 100_000
ROLL_RE = re.compile(r"^[A-Za-z0-9/-]{3,20}$")
PIN_RE = re.compile(r"^\d{4,8}$")
KEY_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no look-alike characters
_DUMMY_HASH = "00" * 16 + "$" + "00" * 32


class AuthError(ValueError):
    """A login or signup problem whose message is safe to show to the user."""


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


def generate_access_key() -> str:
    """Return a random staff access key like 'K7QF-2MXD-9WAH'."""
    chars = [secrets.choice(KEY_ALPHABET) for _ in range(12)]
    return "-".join("".join(chars[i : i + 4]) for i in (0, 4, 8))


def clean_student(name: str, roll: str) -> tuple[str, str]:
    """Validate and trim student name and roll number. Raises AuthError."""
    name, roll = name.strip(), roll.strip().upper()
    if not name:
        raise AuthError("Please enter your name.")
    if not ROLL_RE.match(roll):
        raise AuthError("Roll number should be 3-20 letters, digits, '/' or '-'.")
    return name, roll


def signup_student(name: str, roll: str, pin: str, pin_again: str) -> dict:
    """Create a student account and return the session identity. Raises AuthError."""
    name, roll = clean_student(name, roll)
    if not PIN_RE.match(pin or ""):
        raise AuthError("PIN should be 4 to 8 digits.")
    if pin != pin_again:
        raise AuthError("The two PINs do not match.")
    try:
        row = users.create_student(name, roll, hash_password(pin))
    except ValueError as e:
        raise AuthError(str(e)) from e
    return {"id": row["id"], "name": row["name"], "roll": row["roll_no"]}


def _check_secret(table: str, row: dict | None, secret: str, hash_field: str) -> dict:
    """Shared lockout + verification. Returns the row or raises AuthError."""
    if row is None:
        verify_password(secret or "", _DUMMY_HASH)  # keep timing similar for unknown users
        raise AuthError("Wrong details. Please try again.")
    if users.is_locked(table, row["id"]):
        raise AuthError(f"Too many wrong attempts. Try again in {config.LOCKOUT_MINUTES} minutes.")
    if not verify_password(secret or "", row[hash_field]):
        users.record_login_failure(table, row["id"], config.MAX_LOGIN_ATTEMPTS, config.LOCKOUT_MINUTES)
        raise AuthError("Wrong details. Please try again.")
    users.reset_login_failures(table, row["id"])
    return row


def login_student(roll: str, pin: str) -> dict:
    """Return the student identity for a valid roll number and PIN. Raises AuthError."""
    row = users.get_student_by_roll((roll or "").strip().upper())
    row = _check_secret("students", row, pin, "pin_hash")
    return {"id": row["id"], "name": row["name"], "roll": row["roll_no"]}


def login_staff(username: str, access_key: str) -> dict:
    """Return the staff identity for a valid username and access key. Raises AuthError."""
    row = users.get_staff_by_username((username or "").strip().lower())
    row = _check_secret("staff", row, (access_key or "").strip().upper(), "access_key_hash")
    return {"id": row["id"], "name": row["name"], "department": row["department"], "username": row["username"],
            "is_admin": row.get("role") == "admin"}
