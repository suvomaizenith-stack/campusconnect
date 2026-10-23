"""Data for the outage map: overlay badges, issue dots, tap resolution, search, and the side panels. No UI code."""
import config
from db import groups as gdb
from logic import location, mapfile, priority
from logic.timeutil import eta_text, fmt_ist, time_ago

LEVEL_COLORS = {"normal": "#3B82F6", "hotspot": "#F59E0B", "critical": "#EF4444", "resolved": "#22C55E"}
WINDOWS = config.MAP_WINDOWS
_LEVEL_RANK = {"normal": 0, "hotspot": 1, "critical": 2}


def _group_level(g: dict, count: int) -> str:
    level = priority.level_for(count)
    if g["level"] == "critical" and count < config.CRITICAL_REPORTS:
        level = "critical"  # raised by a safety-risk report, not by volume
    return level


def _group_landmark(g: dict) -> dict | None:
    if g.get("landmark_slug"):
        lm = mapfile.by_id(g["landmark_slug"])
        if lm:
            return lm
    if g.get("map_x") is not None:
        return mapfile.hit_test(g["map_x"], g["map_y"])["landmark"]
    return None


def live_groups(hours: int = 24, category: str | None = None) -> list[dict]:
    """Groups on the map with their landmark resolved from landmarks.json. Each gets
    count, level (normal|hotspot|critical), resolved, landmark (dict or None)."""
    out = []
    for g in gdb.groups_for_map(hours, category, config.RESOLVED_TICK_HOURS):
        resolved = g["status"] == "resolved"
        count = g["report_count"] if resolved else g["window_count"]
        out.append({**g, "count": count, "resolved": resolved, "level": _group_level(g, count),
                    "lm": _group_landmark(g)})
    return out


def overlay(hours: int = 24, category: str | None = None) -> dict:
    """Everything the map component draws on top of the base image.

    badges: one per landmark with activity {id, x, y, count, level, resolved, pulse, ring}
    issues: one dot per group {id, x, y, level, category, title}
    services: icons with a position {id, x, y, icon, name}
    """
    groups = live_groups(hours, category)
    per: dict[str, list[dict]] = {}
    for g in groups:
        if g["lm"]:
            per.setdefault(g["lm"]["id"], []).append(g)
    badges = []
    for lid, gs in per.items():
        lm = mapfile.by_id(lid)
        open_gs = [g for g in gs if not g["resolved"]]
        x, y = mapfile.badge_anchor(lm)
        if open_gs:
            level = max((g["level"] for g in open_gs), key=_LEVEL_RANK.get)
            badges.append({"id": lid, "x": x, "y": y, "count": sum(g["count"] for g in open_gs), "level": level,
                           "resolved": False, "pulse": level == "critical", "ring": level in ("hotspot", "critical")})
        else:
            badges.append({"id": lid, "x": x, "y": y, "count": 0, "level": "resolved", "resolved": True,
                           "pulse": False, "ring": False})
    dots = [
        {"id": g["id"], "x": g["map_x"], "y": g["map_y"], "level": "resolved" if g["resolved"] else g["level"],
         "category": g["category"], "title": g["title"]}
        for g in groups if g["map_x"] is not None
    ]
    svc = [{"id": s["id"], "x": s["map_x"], "y": s["map_y"], "icon": s["icon"], "name": s["name"]}
           for s in mapfile.services() if s["map_x"] is not None]
    return {"badges": badges, "issues": dots, "services": svc}


def resolve_pin(nx: float, ny: float, scale: float = 1.0, issues: list[dict] | None = None) -> dict:
    """Turn a tap into a card-ready result.

    Returns {"kind", "via", "landmark" (dict|None), "landmark_id" (slug), "name", "floors", "distance_m",
    "outside_campus", "x", "y", "issue_id", "service"}. kind is 'issue' | 'service' | 'landmark'.
    """
    hit = mapfile.hit_test(nx, ny, scale, [{"id": i["id"], "map_x": i["x"], "map_y": i["y"]} for i in issues or []])
    lm = hit["landmark"]
    return {**hit, "landmark_id": lm["id"] if lm else None, "name": mapfile.display_name(lm) if lm else "Campus",
            "floors": lm["floors"] if lm else ["Ground"]}


def search(query: str) -> dict | None:
    """Find the entry a search box text means: 'd block' -> D Block, '7' -> place number 7. None if nothing fits."""
    q = query.strip()
    if not q:
        return None
    if q.isdigit():
        return next((lm for lm in mapfile.landmarks() if lm["number"] == int(q)), None)
    found = location.match_landmark(q)
    if found["landmark"]:
        return found["landmark"]
    ql = q.lower()
    for lm in mapfile.landmarks():
        if ql in lm["name"].lower() or any(ql in a.lower() for a in lm["aliases"]):
            return lm
    return None


def index_with_counts(hours: int = 24, category: str | None = None) -> list[dict]:
    """Index entries (places, roads, services) with the open report count at each landmark."""
    counts = {b["id"]: b["count"] for b in overlay(hours, category)["badges"]}
    return [{**e, "count": counts.get(e["id"], 0)} for e in mapfile.index_entries()]


def landmark_panel(landmark_id: str, hours: int = 24, category: str | None = None, student_id: int | None = None) -> dict | None:
    """Panel for a tapped landmark: floors breakdown with the issues on each floor.

    Returns {"id", "name", "number", "outside_campus", "floors": [{"floor", "count", "issues": [...]}], "open", "resolved"}.
    Each issue: {group_id, title, category, count, level, resolved, already_reported}.
    """
    lm = mapfile.by_id(landmark_id)
    if lm is None:
        return None
    by_floor: dict[str, list[dict]] = {f: [] for f in lm["floors"]}
    for g in live_groups(hours, category):
        if not g["lm"] or g["lm"]["id"] != landmark_id:
            continue
        floor = g["floor"] if g["floor"] in by_floor else "Unspecified"
        by_floor.setdefault(floor, []).append({
            "group_id": g["id"], "title": g["title"], "category": g["category"], "count": g["count"],
            "level": "resolved" if g["resolved"] else g["level"], "resolved": g["resolved"],
            "already_reported": bool(student_id and gdb.student_reported(g["id"], student_id)),
        })
    floors = [{"floor": f, "count": sum(i["count"] for i in items if not i["resolved"]), "issues": items}
              for f, items in by_floor.items() if items or f != "Unspecified"]
    flat = [i for f in floors for i in f["issues"]]
    return {"id": lm["id"], "name": mapfile.display_name(lm), "number": lm["number"], "outside_campus": lm["outside_campus"],
            "category": lm["category"], "floors": floors,
            "open": sum(1 for i in flat if not i["resolved"]), "resolved": sum(1 for i in flat if i["resolved"])}


def service_panel(service_id: str) -> dict | None:
    """Contact card for a service icon (helpdesk, security, medical, IT support)."""
    from ai import kb

    s = next((s for s in mapfile.services() if s["id"] == service_id), None)
    if s is None:
        return None
    return {"id": s["id"], "name": s["name"], "contact": kb.contact(s["kb_contact"]) if s["kb_contact"] else None}


def group_panel(group_id: int, student_id: int | None = None) -> dict | None:
    """Details for the action panel after an issue is picked.

    Returns title, category, report_count, first_reported (IST text and 'time ago'), status, eta_text,
    location label, resolved flag and, for a student, whether they already reported it.
    """
    g = gdb.get_group(group_id)
    if g is None:
        return None
    where = g["landmark"] or "Campus"
    if g["floor"]:
        where += f", {g['floor']} floor"
    primary = g["primary"] or {}
    return {
        "group_id": group_id, "title": g["title"], "category": g["category"], "report_count": g["report_count"],
        "first_reported": fmt_ist(g["first_reported_at"]), "first_reported_ago": time_ago(g["first_reported_at"]),
        "status": primary.get("status") or g["status"], "eta_text": eta_text(primary.get("eta_at") or g["eta_at"]),
        "location": where, "resolved": g["status"] == "resolved", "level": g["level"],
        "already_reported": bool(student_id and gdb.student_reported(group_id, student_id)),
    }
