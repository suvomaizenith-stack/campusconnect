"""QR codes stuck at fixed campus spots (e.g. Boys Hostel, 2nd floor, washroom).

A code opens "<APP_URL>/?qr=<code>". The app remembers the spot for the session; after sign-in the student lands on
Report a Problem with the place, floor and spot filled in and the map pin dropped on the place. Spots live in
data/qr_spots.json. Pure functions, no DB, no UI.
"""
import json
import math
import re
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote

import config
from logic import mapfile

SPOTS_PATH = Path(__file__).resolve().parent.parent / "data" / "qr_spots.json"
PARAM = "qr"  # the query parameter in the printed link
CODE_RE = re.compile(r"^[a-z0-9]{1,6}(?:-[a-z0-9]{1,6}){1,3}$")
SPOT_MAX = 60
MIN_CLEAR_PX = 25  # keep the auto pin this far (map pixels) from any edge when the centre is crowded


def _load() -> dict:
    try:
        data = json.loads(SPOTS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _raw() -> list[dict]:
    return [s for s in _load().get("spots", []) if isinstance(s, dict)]


def _place_pins() -> dict[str, dict]:
    """Per-place pin positions from "pins" in qr_spots.json, e.g. {"boys_hostel": {"x": 0.52, "y": 0.18}}."""
    return {k: v for k, v in (_load().get("pins") or {}).items() if isinstance(v, dict)}


def problems() -> list[str]:
    """Everything wrong with data/qr_spots.json (empty list when it is fine). Used by tests and the QR script."""
    out, seen = [], set()
    for i, s in enumerate(_raw()):
        code, lm = s.get("code"), mapfile.by_id(s.get("landmark") or "")
        if not isinstance(code, str) or not CODE_RE.match(code):
            out.append(f"spot {i}: code {code!r} must look like 'bh-2-wr' (lowercase letters, digits, dashes)")
        elif code in seen:
            out.append(f"spot {i}: code {code!r} is used twice")
        seen.add(code)
        if not lm:
            out.append(f"spot {i} ({code}): landmark {s.get('landmark')!r} is not in landmarks.json")
        elif s.get("floor") and s["floor"] not in lm["floors"]:
            out.append(f"spot {i} ({code}): {lm['name']} has no floor {s['floor']!r} (floors: {', '.join(lm['floors'])})")
        if lm and ("x" in s or "y" in s) and not _xy(s, lm):
            out.append(f"spot {i} ({code}): x/y must be numbers from 0 to 1 that lie inside {lm['name']}")
        if not (s.get("spot") or "").strip():
            out.append(f"spot {i} ({code}): spot name is empty")
    for lid, xy in _place_pins().items():
        lm = mapfile.by_id(lid)
        if not lm or not _xy(xy, lm):
            out.append(f"pins: {lid!r} must be a place in landmarks.json with x/y inside it")
    return out


@lru_cache(maxsize=1)
def spots() -> dict[str, dict]:
    """Valid spots by code: {code, landmark (id), name, floor, spot, xy (exact pin or None)}. Broken entries skipped."""
    out: dict[str, dict] = {}
    for s in _raw():
        code, lm = s.get("code"), mapfile.by_id(s.get("landmark") or "")
        if not isinstance(code, str) or not CODE_RE.match(code) or code in out or not lm:
            continue
        floor = s.get("floor") if s.get("floor") in lm["floors"] else None
        out[code] = {"code": code, "landmark": lm["id"], "name": lm["name"], "floor": floor,
                     "spot": str(s.get("spot") or "").strip()[:SPOT_MAX], "xy": _xy(s, lm)}
    return out


def _xy(raw: dict, lm: dict) -> tuple[float, float] | None:
    """Optional exact pin position ("x", "y" from 0 to 1), only if it lies inside the place."""
    try:
        x, y = float(raw["x"]), float(raw["y"])
    except (KeyError, TypeError, ValueError):
        return None
    return (x, y) if mapfile.distance_to_landmark_px(x, y, lm) == 0 else None


def _is_mine(x: float, y: float, lm: dict) -> bool:
    """A tap here resolves to this landmark (not to a smaller place drawn inside it, like a mess in a hostel)."""
    hit = mapfile.hit_test(x, y, scale=100.0)  # large scale: ignore the touch radius of service icons
    return hit["kind"] == "landmark" and hit["landmark"] is not None and hit["landmark"]["id"] == lm["id"]


def _clearance_px(x: float, y: float, lm: dict) -> float:
    """Distance from (x, y) to the nearest edge of this place or of any other place, in map pixels."""
    m = mapfile.meta()
    px, py = x * m["width_px"], y * m["height_px"]
    best = math.inf
    for other in mapfile.landmarks():
        if other["category"] == "road" and other["id"] != lm["id"]:
            continue
        for poly in other["shapes"]:
            for i, (ax, ay) in enumerate(poly):
                bx, by = poly[(i + 1) % len(poly)]
                best = min(best, mapfile._seg_dist(px, py, ax * m["width_px"], ay * m["height_px"],
                                                   bx * m["width_px"], by * m["height_px"]))
    return best


@lru_cache(maxsize=128)
def _auto_pin(landmark_id: str) -> tuple[float, float]:
    """A pin spot clearly inside the place: the centre when free, else the point furthest from any edge that
    still resolves to this place (so a hostel pin does not sit on its mess)."""
    lm = mapfile.by_id(landmark_id)
    fixed = _xy(_place_pins().get(landmark_id, {}), lm)
    if fixed:
        return fixed
    cx, cy = lm["map_x"], lm["map_y"]
    if lm["category"] == "road" or not lm["shapes"]:
        return cx, cy
    if _is_mine(cx, cy, lm) and _clearance_px(cx, cy, lm) >= MIN_CLEAR_PX:
        return cx, cy
    xs = [x for p in lm["shapes"] for x, _ in p]
    ys = [y for p in lm["shapes"] for _, y in p]
    best, best_key = (cx, cy), (-1.0, 0.0)
    steps = 30
    for i in range(1, steps):
        for j in range(1, steps):
            x = min(xs) + (max(xs) - min(xs)) * i / steps
            y = min(ys) + (max(ys) - min(ys)) * j / steps
            if not _is_mine(x, y, lm):
                continue
            key = (round(_clearance_px(x, y, lm)), -math.hypot(x - cx, y - cy))
            if key > best_key:
                best, best_key = (x, y), key
    return best


def pin_point(spot: dict) -> tuple[float, float]:
    """Where the map pin goes for a scanned spot: its own x/y, else the place's "pins" entry, else an auto point."""
    return spot.get("xy") or _auto_pin(spot["landmark"])


def get(code: object) -> dict | None:
    """The spot for a scanned code, or None for anything unknown or malformed."""
    if not isinstance(code, str):
        return None
    return spots().get(code.strip().lower())


def label(spot: dict) -> str:
    """'Boys Hostel · 2nd floor · Washroom'."""
    parts = [spot["name"], f"{spot['floor']} floor" if spot.get("floor") else "", spot.get("spot") or ""]
    return " · ".join(p for p in parts if p)


def link(code: str, base: str | None = None) -> str:
    """The URL printed in the QR code. base defaults to APP_URL. Raises ValueError when there is no base URL."""
    base = (base if base is not None else config.APP_URL).strip().rstrip("/")
    if not base.startswith(("http://", "https://")):
        raise ValueError("Set APP_URL (the public link of the app, e.g. https://campus-saathi.streamlit.app).")
    return f"{base}/?{PARAM}={quote(code)}"
