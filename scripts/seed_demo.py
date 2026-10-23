"""Load demo data that matches docs/demo_script.md: a Block B washroom leak (the duplicate target) plus a few
tickets elsewhere. Run once after create_staff.py: python scripts/seed_demo.py
Creates a demo student (roll DEMO001, PIN 1234). Uses the normal report flow, so AI or rules fallback apply.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db.db import close_pool  # noqa: E402
from db.users import create_student, get_student_by_roll  # noqa: E402
from logic import tickets  # noqa: E402
from logic.auth import hash_password  # noqa: E402
from logic.setup import bootstrap  # noqa: E402

REPORTS = [
    ("Tap is leaking in the 2nd floor washroom of B block, water all over the floor", "b_block", "2nd"),
    ("Wifi keeps disconnecting in D block 1st floor classrooms", "d_block", "1st"),
    ("Dustbins are overflowing near the main gate and it smells", "main_gate", "Ground"),
    ("Tube light flickering in girls hostel 2nd floor corridor", "girls_hostel", "2nd"),
]


def main() -> int:
    try:
        bootstrap()
        student = get_student_by_roll("DEMO001") or create_student("Demo Student", "DEMO001", hash_password("1234"))
        student = {"id": student["id"], "name": student["name"], "roll": student["roll_no"]}
        for text, landmark, floor in REPORTS:
            res = tickets.submit_report(student, text, landmark, floor)
            print(f"  {res['code']}  {res['category']:<12} {landmark}")
        print("Done. Demo student: roll DEMO001, PIN 1234.")
    except Exception as e:
        print(f"FAILED: {type(e).__name__}. Check DATABASE_URL in .env and that scripts/apply_schema.py ran.")
        return 1
    finally:
        close_pool()
    return 0


if __name__ == "__main__":
    sys.exit(main())
