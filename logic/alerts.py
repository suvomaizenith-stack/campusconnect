"""Threshold alerts: recount a group, set its level, create alerts, and re-score its tickets."""
import config
from db import groups as gdb
from db import tickets as tdb
from logic import priority


def _alert_message(group: dict, level: str, count: int, severe: bool) -> str:
    where = group["landmark"] or "campus"
    if group.get("floor"):
        where += f", {group['floor']} floor"
    if severe and count < config.CRITICAL_REPORTS:
        return f"Safety risk reported: {group['title']} at {where}."
    label = "Critical" if level == "critical" else "Hotspot"
    return f"{label}: {count} reports in {config.ALERT_WINDOW_HOURS} h for {group['title']} at {where}."


def evaluate_group(group_id: int) -> dict:
    """Recount reports in the alert window, update level, create an alert if a threshold is crossed,
    and refresh priority score and tier of every linked ticket.

    Returns {"level", "count", "alert_id"} (alert_id is None when no new alert was created).
    """
    group = gdb.get_group(group_id)
    if group is None:
        raise ValueError("Unknown group.")
    count = gdb.count_reports(group_id, config.ALERT_WINDOW_HOURS)
    severity = gdb.max_severity(group_id)
    level = priority.level_for(count, severity)
    if level != group["level"]:
        gdb.update_group(group_id, {"level": level})
    alert_id = None
    if level in ("hotspot", "critical"):
        alert_id = gdb.create_alert(group_id, level, _alert_message(group, level, count, severity >= 3))
    for t in tdb.list_tickets(group_id=group_id):
        if t["dup_review"] == "separate":
            continue
        s = priority.score(t["category"], t["severity"], count)
        tdb.update_ticket(t["id"], {"priority_score": s, "tier": priority.effective_tier(priority.tier(s, level), t["urgency_override"])})
    return {"level": level, "count": count, "alert_id": alert_id}


def recurring_banners(department: str | None = None) -> list[dict]:
    """Places where the same department keeps getting tickets: yellow at RECURRING_YELLOW, red at RECURRING_RED
    within RECURRING_DAYS. Each: {landmark, category, count, level ('yellow'|'red'), message}. department None = all."""
    out = []
    for r in tdb.recurring_locations(config.RECURRING_DAYS, config.RECURRING_YELLOW):
        if department and r["category"] != department:
            continue
        level = "red" if r["count"] >= config.RECURRING_RED else "yellow"
        label = config.CATEGORY_LABELS[r["category"]].lower()
        out.append({**r, "level": level,
                    "message": f"Recurring: {r['count']} {label} tickets at {r['landmark']} in {config.RECURRING_DAYS} days."})
    return out
