"""Create or update Supabase tables, RLS and landmarks. Run: python scripts/apply_schema.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db.db import close_pool  # noqa: E402
from logic.setup import bootstrap  # noqa: E402


def main() -> int:
    try:
        bootstrap()
    except RuntimeError as e:  # missing DATABASE_URL
        print(f"FAILED: {e}")
        return 1
    except Exception as e:
        print(f"FAILED: could not reach the database ({type(e).__name__}). Check DATABASE_URL in .env.")
        return 1
    finally:
        close_pool()
    print("Schema applied: tables, RLS enabled, landmarks loaded.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
