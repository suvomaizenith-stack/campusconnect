"""Loads data/landmarks.json and answers geometry questions about it. Pure functions, no DB, no UI.

All coordinates are normalised 0-1 (x to the right, y downwards) on data/campus_map.png.
Categories: "place" and "area" have one polygon in `area`; "road" has a list of rectangles in `areas`.
"""
import json
import math
from functools import lru_cache
from pathlib import Path

import config

DATA_DIR = Path(__file__).resolve().parent.parent / config.MAP_DIR
LANDMARKS_PATH = DATA_DIR / "landmarks.json"
MAP_IMAGE_PATH = DATA_DIR / config.MAP_IMAGE

_DEFAULT_META = {"width_px": 1600, "height_px": 1000, "meters_per_px": 0.33, "image": config.MAP_IMAGE}


def _pt(p) -> tuple[float, float]:
    if isinstance(p, dict):
        return float(p["x"]), float(p["y"])
    return float(p[0]), float(p[1])


def _poly(raw) -> list[tuple[float, float]] | None:
    try:
        pts = [_pt(p) for p in raw or []]
    except (KeyError, TypeError, ValueError, IndexError):
        return None
    return pts if len(pts) >= 3 else None


def _clean_landmark(raw: dict) -> dict | None:
    """Normalise one landmark entry; returns None if it has no id or name."""
    lid, name = raw.get("id"), raw.get("name")
    if not lid or not name:
        return None
    category = raw.get("category") or "place"
    area = _poly(raw.get("area"))
    areas = [p for p in (_poly(a) for a in (raw.get("areas") or [])) if p]
    shapes = areas if category == "road" else ([area] if area else areas)
    map_x, map_y = raw.get("map_x"), raw.get("map_y")
    if (map_x is None or map_y is None) and shapes:
        xs = [x for s in shapes for x, _ in s]
        ys = [y for s in shapes for _, y in s]
        map_x, map_y = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    if map_x is None or map_y is None:
        return None
    return {
        "id": lid, "name": name, "number": raw.get("number"), "category": category,
        "map_x": float(map_x), "map_y": float(map_y), "shapes": shapes,
        "area": area, "areas": areas, "floors": list(raw.get("floors") or ["Ground"]),
        "aliases": [a for a in (raw.get("aliases") or []) if isinstance(a, str)],
        "outside_campus": bool(raw.get("outside_campus")), "kb_contact": raw.get("kb_contact"),
    }


def _clean_service(raw: dict) -> dict | None:
    if not raw.get("id") or not raw.get("name"):
        return None
    x, y = raw.get("map_x"), raw.get("map_y")
    return {
        "id": raw["id"], "name": raw["name"], "icon": raw.get("icon") or "info", "kb_contact": raw.get("kb_contact"),
        "map_x": None if x is None or y is None else float(x), "map_y": None if x is None or y is None else float(y),
    }


@lru_cache(maxsize=1)
def load_map() -> dict:
    """Return {"meta", "landmarks", "services"} from landmarks.json. Missing or broken file gives empty lists."""
    try:
        raw = json.loads(LANDMARKS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raw = {}
    if isinstance(raw, list):  # a bare list of landmarks
        raw = {"landmarks": raw}
    meta = {**_DEFAULT_META, **(raw.get("map") or {})}
    lms = [c for c in (_clean_landmark(r) for r in raw.get("landmarks") or []) if c]
    services = [c for c in (_clean_service(r) for r in raw.get("services") or []) if c]
    return {"meta": meta, "landmarks": lms, "services": services}


def landmarks() -> list[dict]:
    return load_map()["landmarks"]


def services() -> list[dict]:
    return load_map()["services"]


def by_id(landmark_id: str) -> dict | None:
    return next((lm for lm in landmarks() if lm["id"] == landmark_id), None)


def meta() -> dict:
    return load_map()["meta"]


# --- geometry ---------------------------------------------------------------------------------

def point_in_polygon(x: float, y: float, poly: list[tuple[float, float]]) -> bool:
    """Ray casting test. Points exactly on an edge may go either way."""
    inside = False
    j = len(poly) - 1
    for i, (xi, yi) in enumerate(poly):
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def polygon_area(poly: list[tuple[float, float]]) -> float:
    """Absolute shoelace area (normalised units)."""
    s = 0.0
    for i, (x1, y1) in enumerate(poly):
        x2, y2 = poly[(i + 1) % len(poly)]
        s += x1 * y2 - x2 * y1
    return abs(s) / 2


def _seg_dist(px, py, ax, ay, bx, by) -> float:
    dx, dy = bx - ax, by - ay
    t = 0.0 if dx == dy == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def px_dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Distance between two normalised points in map-image pixels."""
    m = meta()
    return math.hypot((a[0] - b[0]) * m["width_px"], (a[1] - b[1]) * m["height_px"])


def px_to_m(px: float) -> float:
    return px * float(meta()["meters_per_px"])


def distance_to_landmark_px(x: float, y: float, lm: dict) -> float:
    """0 inside the landmark; otherwise pixel distance to its nearest edge."""
    m = meta()
    best = math.inf
    for poly in lm["shapes"]:
        if point_in_polygon(x, y, poly):
            return 0.0
        for i, (ax, ay) in enumerate(poly):
            bx, by = poly[(i + 1) % len(poly)]
            d = _seg_dist(x * m["width_px"], y * m["height_px"], ax * m["width_px"], ay * m["height_px"],
                          bx * m["width_px"], by * m["height_px"])
            best = min(best, d)
    return best


def contains(parent: dict, child: dict) -> bool:
    """True if the child's centre lies inside the parent's polygon (e.g. a canteen inside a block)."""
    return parent["id"] != child["id"] and any(point_in_polygon(child["map_x"], child["map_y"], p) for p in parent["shapes"])


def hit_test(x: float, y: float, scale: float = 1.0, issues: list[dict] | None = None) -> dict:
    """Decide what a tap at normalised (x, y) means.

    scale: on-screen pixels per map-image pixel at tap time, so the 20 px touch radius shrinks when zoomed in.
    issues: [{"id", "map_x", "map_y"}] of visible issue dots.
    Order: issue dot -> service icon -> place/area (smallest polygon wins) -> road -> nearest landmark.
    Returns {"kind": "issue"|"service"|"landmark", "via", "landmark", "issue_id", "service", "distance_m",
    "x", "y", "outside_campus"} (landmark may be None only if the map has no landmarks).
    """
    reach = config.HIT_RADIUS_PX / max(scale, 0.05)
    base = {"x": x, "y": y, "landmark": None, "issue_id": None, "service": None, "distance_m": 0, "outside_campus": False}

    near = [(px_dist((x, y), (i["map_x"], i["map_y"])), i) for i in issues or [] if i.get("map_x") is not None]
    near = [n for n in near if n[0] <= reach]
    if near:
        return {**base, "kind": "issue", "via": "issue", "issue_id": min(near, key=lambda n: n[0])[1]["id"]}

    near_s = [(px_dist((x, y), (s["map_x"], s["map_y"])), s) for s in services() if s["map_x"] is not None]
    near_s = [n for n in near_s if n[0] <= reach]
    if near_s:
        return {**base, "kind": "service", "via": "service", "service": min(near_s, key=lambda n: n[0])[1]}

    lms = landmarks()
    inside = [lm for lm in lms if lm["category"] != "road" and any(point_in_polygon(x, y, p) for p in lm["shapes"])]
    if inside:
        best = min(inside, key=lambda lm: min(polygon_area(p) for p in lm["shapes"]))
        return {**base, "kind": "landmark", "via": "polygon", "landmark": best, "outside_campus": best["outside_campus"]}
    roads = [lm for lm in lms if lm["category"] == "road" and any(point_in_polygon(x, y, p) for p in lm["shapes"])]
    if roads:
        best = roads[0]
        return {**base, "kind": "landmark", "via": "road", "landmark": best, "outside_campus": best["outside_campus"]}
    if not lms:
        return {**base, "kind": "landmark", "via": "none"}

    # Open area: nearest landmark by edge distance, preferring campus ones within the snap radius.
    ranked = sorted(((distance_to_landmark_px(x, y, lm), lm) for lm in lms), key=lambda d: d[0])
    snap_px = config.LANDMARK_SNAP_RADIUS_M / float(meta()["meters_per_px"])
    campus = [d for d in ranked if not d[1]["outside_campus"]]
    within = [d for d in campus if d[0] <= snap_px]
    if within:
        dist, best, via = within[0][0], within[0][1], "snap"
    else:
        dist, best, via = ranked[0][0], ranked[0][1], "nearest"
    return {**base, "kind": "landmark", "via": via, "landmark": best, "distance_m": round(px_to_m(dist)),
            "outside_campus": best["outside_campus"]}


def display_name(lm: dict) -> str:
    """Label used on cards: outside-campus landmarks say so."""
    return f"Outside campus — {lm['name']}" if lm.get("outside_campus") else lm["name"]


def badge_anchor(lm: dict) -> tuple[float, float]:
    """Where a status badge sits: top-right corner of the polygon, or the map point for roads."""
    if lm["category"] == "road" or not lm["area"]:
        return lm["map_x"], lm["map_y"]
    return max(x for x, _ in lm["area"]), min(y for _, y in lm["area"])


def index_entries() -> list[dict]:
    """Index under the map: numbered places, then roads, then services. Each {kind, id, name, number}."""
    lms = landmarks()
    places = sorted((lm for lm in lms if lm["category"] != "road"), key=lambda lm: (lm["number"] or 999, lm["name"]))
    roads = sorted((lm for lm in lms if lm["category"] == "road"), key=lambda lm: lm["name"])
    out = [{"kind": "place", "id": lm["id"], "name": lm["name"], "number": lm["number"]} for lm in places]
    out += [{"kind": "road", "id": lm["id"], "name": lm["name"], "number": None} for lm in roads]
    out += [{"kind": "service", "id": s["id"], "name": s["name"], "number": None} for s in services()]
    return out


def validate() -> list[str]:
    """Human-readable problems in landmarks.json (empty list = fine). Used by scripts/validate_map_data.py."""
    problems = []
    try:
        raw = json.loads(LANDMARKS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return [f"cannot read landmarks.json: {e}"]
    if not MAP_IMAGE_PATH.exists():
        problems.append(f"{MAP_IMAGE_PATH.name} is missing")
    ids, numbers = set(), set()
    for r in raw.get("landmarks", []):
        c = _clean_landmark(r)
        if c is None:
            problems.append(f"landmark without id/name/position: {r.get('name') or r.get('id')!r}")
            continue
        if c["id"] in ids:
            problems.append(f"duplicate id {c['id']}")
        ids.add(c["id"])
        if c["category"] != "road":
            if not c["area"]:
                problems.append(f"{c['name']}: no usable polygon")
            if c["number"] is None or c["number"] in numbers:
                problems.append(f"{c['name']}: number missing or duplicated")
            numbers.add(c["number"])
        elif not c["areas"]:
            problems.append(f"{c['name']}: road has no rectangles")
        for poly in c["shapes"]:
            if any(not (0 <= x <= 1 and 0 <= y <= 1) for x, y in poly):
                problems.append(f"{c['name']}: coordinates outside 0-1")
                break
    return problems
