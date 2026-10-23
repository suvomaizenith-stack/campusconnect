"""Check data/landmarks.json and data/campus_map.png before a demo. Run: python scripts/validate_map_data.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from logic import mapfile  # noqa: E402


def main() -> int:
    problems = mapfile.validate()
    lms = mapfile.landmarks()
    print(f"{sum(1 for lm in lms if lm['category'] != 'road')} places/areas, "
          f"{sum(1 for lm in lms if lm['category'] == 'road')} roads, {len(mapfile.services())} services.")
    if problems:
        print("Problems:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("landmarks.json looks fine.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
