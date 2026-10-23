"""Create or update Supabase tables, added columns and RLS. Run: python scripts/apply_schema.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db.db import init_db  # noqa: E402


def main() -> int:
    try:
        init_db()
    except RuntimeError as e:  # missing DATABASE_URL
        print(f"FAILED: {e}")
        return 1
    print("Schema applied: tables, added columns, RLS enabled.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
