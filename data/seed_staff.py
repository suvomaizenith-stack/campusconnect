"""Seed demo staff accounts. Run: python -m data.seed_staff"""
import json
from pathlib import Path

from db.db import get_conn, init_db, upsert_landmarks
from logic.auth import hash_password

STAFF = [
    ("Ravi Plumber", "plumbing@campus.edu", "plumbing"),
    ("Esha Electric", "electricity@campus.edu", "electricity"),
    ("Clara Clean", "cleanliness@campus.edu", "cleanliness"),
    ("Ivan Internet", "internet@campus.edu", "internet"),
]
DEMO_PASSWORD = "changeme123"
LANDMARKS_PATH = Path(__file__).resolve().parent / "landmarks.json"


def seed() -> None:
    """Insert demo staff and landmarks if missing. Safe to re-run."""
    init_db()
    with get_conn() as conn:
        for name, email, dept in STAFF:
            conn.execute(
                "INSERT INTO staff (name, email, password_hash, department)"
                " VALUES (%s, %s, %s, %s) ON CONFLICT (email) DO NOTHING",
                (name, email, hash_password(DEMO_PASSWORD), dept),
            )
    upsert_landmarks(json.loads(LANDMARKS_PATH.read_text(encoding="utf-8")))


if __name__ == "__main__":
    seed()
    print(f"Seeded {len(STAFF)} staff (password: {DEMO_PASSWORD})")
