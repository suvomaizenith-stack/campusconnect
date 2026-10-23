"""Saved app settings (key/value rows in app_settings). SQL only; defaults and checks live in logic/settings.py."""
from db.db import get_conn


def all_settings() -> dict[str, str]:
    with get_conn() as conn:
        rows = conn.execute("SELECT key, value FROM app_settings").fetchall()
    return {r["key"]: r["value"] for r in rows}


def put_setting(key: str, value: str, updated_by: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO app_settings (key, value, updated_by) VALUES (%s, %s, %s)"
            " ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_by = EXCLUDED.updated_by,"
            " updated_at = now()",
            (key, value, updated_by),
        )
