"""Create the four staff accounts plus one admin. Run once: python scripts/create_staff.py

Each account gets a fresh random access key, printed once. Only the hash is stored.
Re-running replaces the keys of existing usernames.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db.db import close_pool  # noqa: E402
from db.users import upsert_staff  # noqa: E402
from logic.auth import generate_access_key, hash_password  # noqa: E402
from logic.setup import bootstrap  # noqa: E402

STAFF = [
    ("suvom", "Suvom", "plumbing"),
    ("deepanshi", "Deepanshi", "electricity"),
    ("arsh", "Arsh", "cleanliness"),
    ("samriddhi", "Samriddhi", "internet"),
]
ADMIN = ("admin", "Admin", "admin")  # sees every department


def main() -> int:
    try:
        bootstrap()
        print("Staff accounts. Save these keys now, they are not shown again:\n")
        for username, name, dept in [*STAFF, ADMIN]:
            key = generate_access_key()
            upsert_staff(username, name, dept, hash_password(key), "admin" if username == "admin" else "staff")
            print(f"  {name:<10} username: {username:<10} department: {dept:<12} access key: {key}")
        print()
    except Exception as e:
        print(f"FAILED: {type(e).__name__}. Check DATABASE_URL in .env, then run scripts/apply_schema.py.")
        return 1
    finally:
        close_pool()
    return 0


if __name__ == "__main__":
    sys.exit(main())
