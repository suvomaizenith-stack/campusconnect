"""Schema checks run offline; the round-trip test needs DATABASE_URL and is skipped without it."""
import re
from pathlib import Path

import pytest

from config import DATABASE_URL
from db.db import SCHEMA_PATH, init_db
from db.users import get_staff_by_username

SCHEMA = SCHEMA_PATH.read_text(encoding="utf-8")


def test_every_table_has_rls_and_no_policies():
    tables = re.findall(r"CREATE TABLE IF NOT EXISTS (\w+)", SCHEMA)
    assert tables, "no tables found in schema"
    for table in tables:
        assert f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;" in SCHEMA, table
    assert "CREATE POLICY" not in SCHEMA.upper()


def test_no_sqlite_placeholders_left():
    assert "?" not in re.sub(r"--.*", "", SCHEMA)
    assert "AUTOINCREMENT" not in SCHEMA


@pytest.mark.skipif(not DATABASE_URL, reason="DATABASE_URL not set")
def test_init_is_idempotent_and_lookup_misses_cleanly():
    init_db()
    init_db()
    assert get_staff_by_username("nobody-here") is None
