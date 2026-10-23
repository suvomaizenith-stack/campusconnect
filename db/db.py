"""Supabase Postgres helpers for CampusConnect. Connections come from a shared pool."""
import atexit
import threading
from pathlib import Path

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

import config
from config import DATABASE_URL

SCHEMA_PATH = Path(__file__).resolve().parent / "schema_postgres.sql"

# Columns added to tables that already existed in an older deployment; keeps init_db re-runnable.
ADDED_COLUMNS = [
    "ALTER TABLE landmarks ADD COLUMN IF NOT EXISTS floors TEXT[] NOT NULL DEFAULT '{}'",
    "ALTER TABLE landmarks ADD COLUMN IF NOT EXISTS slug TEXT",
    "ALTER TABLE landmarks ADD COLUMN IF NOT EXISTS category TEXT NOT NULL DEFAULT 'place'",
    "ALTER TABLE landmarks ADD COLUMN IF NOT EXISTS number INT",
    "ALTER TABLE landmarks ADD COLUMN IF NOT EXISTS map_x DOUBLE PRECISION",
    "ALTER TABLE landmarks ADD COLUMN IF NOT EXISTS map_y DOUBLE PRECISION",
    "ALTER TABLE landmarks ADD COLUMN IF NOT EXISTS outside_campus BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE issue_groups ADD COLUMN IF NOT EXISTS map_x DOUBLE PRECISION",
    "ALTER TABLE issue_groups ADD COLUMN IF NOT EXISTS map_y DOUBLE PRECISION",
    "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS map_x DOUBLE PRECISION",
    "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS map_y DOUBLE PRECISION",
    "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS ai_confidence DOUBLE PRECISION",
    "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS language TEXT",
    "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS urgency_override TEXT",
    "ALTER TABLE status_history ADD COLUMN IF NOT EXISTS internal BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE staff ADD COLUMN IF NOT EXISTS role TEXT NOT NULL DEFAULT 'staff'",
    "CREATE UNIQUE INDEX IF NOT EXISTS landmarks_slug_idx ON landmarks (slug)",
    # Older deployments stored lat/lng; the map now uses normalised map_x/map_y.
    """DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'landmarks' AND column_name = 'lat') THEN
            ALTER TABLE landmarks ALTER COLUMN lat DROP NOT NULL;
            ALTER TABLE landmarks ALTER COLUMN lng DROP NOT NULL;
        END IF;
    END $$""",
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
                max_size=config.DB_POOL_MAX,
                open=True,
                kwargs={"row_factory": dict_row, "prepare_threshold": None},
            )
        return _pool


def close_pool() -> None:
    """Close the shared pool so interpreter shutdown does not raise from the pool's finalizer."""
    global _pool
    with _pool_lock:
        if _pool is not None:
            _pool.close()
            _pool = None


atexit.register(close_pool)


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


_LM_COLS = "id, slug, name, category, number, map_x, map_y, outside_campus, floors"


def upsert_landmarks(landmarks: list[dict]) -> None:
    """Insert landmarks keyed by slug (id in landmarks.json); existing ones are refreshed in place."""
    rows = [
        {"slug": lm["id"], "name": lm["name"], "category": lm.get("category", "place"), "number": lm.get("number"),
         "map_x": lm.get("map_x"), "map_y": lm.get("map_y"), "outside": bool(lm.get("outside_campus")),
         "floors": lm.get("floors") or []}
        for lm in landmarks
    ]
    with get_conn() as conn:
        cur = conn.cursor()
        for r in rows:
            updated = cur.execute(
                "UPDATE landmarks SET name = %(name)s, category = %(category)s, number = %(number)s, map_x = %(map_x)s,"
                " map_y = %(map_y)s, outside_campus = %(outside)s, floors = %(floors)s WHERE slug = %(slug)s",
                r,
            ).rowcount
            if not updated:  # first load, or an older row created by name only
                cur.execute(
                    "INSERT INTO landmarks (slug, name, category, number, map_x, map_y, outside_campus, floors)"
                    " VALUES (%(slug)s, %(name)s, %(category)s, %(number)s, %(map_x)s, %(map_y)s, %(outside)s, %(floors)s)"
                    " ON CONFLICT (name) DO UPDATE SET slug = EXCLUDED.slug, category = EXCLUDED.category,"
                    " number = EXCLUDED.number, map_x = EXCLUDED.map_x, map_y = EXCLUDED.map_y,"
                    " outside_campus = EXCLUDED.outside_campus, floors = EXCLUDED.floors",
                    r,
                )


def list_landmarks() -> list[dict]:
    """Return all landmarks ordered by number (places first), then name."""
    with get_conn() as conn:
        return conn.execute(f"SELECT {_LM_COLS} FROM landmarks ORDER BY number NULLS LAST, name").fetchall()


def get_landmark_by_name(name: str) -> dict | None:
    """Return the landmark with this exact name, or None."""
    with get_conn() as conn:
        return conn.execute(f"SELECT {_LM_COLS} FROM landmarks WHERE name = %s", (name,)).fetchone()


def get_landmark_by_slug(slug: str) -> dict | None:
    """Return the landmark with this slug (the id used in landmarks.json), or None."""
    with get_conn() as conn:
        return conn.execute(f"SELECT {_LM_COLS} FROM landmarks WHERE slug = %s", (slug,)).fetchone()


def ping() -> bool:
    """Return True if the database answers a trivial query."""
    try:
        with get_conn() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:
        return False
