"""Seed demo staff accounts. Run: python -m data.seed_staff"""
import hashlib
import os

from db.db import get_conn, init_db

STAFF = [
    ("Ravi Plumber", "plumbing@campus.edu", "plumbing"),
    ("Esha Electric", "electricity@campus.edu", "electricity"),
    ("Clara Clean", "cleanliness@campus.edu", "cleanliness"),
    ("Ivan Internet", "internet@campus.edu", "internet"),
]
DEMO_PASSWORD = "changeme123"


def hash_password(password: str, salt: bytes | None = None) -> str:
    """Return 'salt$hash' using PBKDF2-SHA256."""
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return f"{salt.hex()}${digest.hex()}"


def seed() -> None:
    """Insert the demo staff accounts if missing."""
    init_db()
    with get_conn() as conn:
        for name, email, dept in STAFF:
            conn.execute(
                "INSERT OR IGNORE INTO staff (name, email, password_hash, department)"
                " VALUES (?, ?, ?, ?)",
                (name, email, hash_password(DEMO_PASSWORD), dept),
            )
    print(f"Seeded {len(STAFF)} staff (password: {DEMO_PASSWORD})")


if __name__ == "__main__":
    seed()
