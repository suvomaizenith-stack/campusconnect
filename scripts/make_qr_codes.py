"""Make the printable QR codes for every spot in data/qr_spots.json.

Run:  python scripts/make_qr_codes.py --base-url https://your-app.streamlit.app
      (or set APP_URL in .env and leave --base-url out)
Writes to qr_codes/: one PNG poster per spot (A6), qr_codes_print.pdf (4 per A4 page) and links.csv.
"""
import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config  # noqa: E402
from logic import qr, qr_poster  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base-url", default=config.APP_URL, help="public link of the app (default: APP_URL)")
    ap.add_argument("--out", default="qr_codes", help="output folder (default: qr_codes)")
    ap.add_argument("--only", nargs="*", help="only these codes, e.g. bh-2-wr gh-g-wc")
    args = ap.parse_args()

    bad = qr.problems()
    if bad:
        print("Fix data/qr_spots.json first:\n  " + "\n  ".join(bad))
        return 1
    spots = [s for s in qr.spots().values() if not args.only or s["code"] in args.only]
    if not spots:
        print("No matching spots.")
        return 1
    try:
        qr.link(spots[0]["code"], args.base_url)
    except ValueError as e:
        print(e)
        return 1

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "links.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["code", "place", "floor", "spot", "link"])
        for s in spots:
            qr_poster.card(s, args.base_url).save(out / f"qr_{s['code']}.png", dpi=(qr_poster.DPI, qr_poster.DPI))
            w.writerow([s["code"], s["name"], s["floor"] or "", s["spot"], qr.link(s["code"], args.base_url)])
    (out / "qr_codes_print.pdf").write_bytes(qr_poster.pdf_bytes(spots, args.base_url))
    print(f"Made {len(spots)} QR codes in {out}/ (PNG each, qr_codes_print.pdf, links.csv)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
