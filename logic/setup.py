"""One-time setup shared by the app and scripts: create tables and load landmarks."""
from db.db import init_db, upsert_landmarks
from logic import mapfile


def bootstrap() -> None:
    """Create tables, apply RLS and load landmarks from data/landmarks.json. Safe to run repeatedly."""
    init_db()
    upsert_landmarks(mapfile.landmarks())
