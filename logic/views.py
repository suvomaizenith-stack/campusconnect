"""Read-side helpers for the student and staff pages: queues, detail views, metrics, alerts, quick replies."""
import csv
import io
import json
from datetime import timedelta
from pathlib import Path

import streamlit as st

import config
from db import groups as gdb
from db import tickets as tdb
from db import users as udb
from logic import alerts as alert_logic
from logic import priority
from logic.timeutil import eta_text, fmt_ist, now_utc, time_ago

QUICK_REPLIES_PATH = Path(__file__).resolve().parent.parent / "data" / "quick_replies.json"
OPEN_STATUSES = ["waiting", "assigned", "in_progress"]
STATUS_LABELS = {"waiting": "Waiting", "assigned": "Assigned", "in_progress": "In progress", "resolved": "Resolved"}
_REPLY_CATEGORY = {"plumbing": "Plumbing", "electricity": "Electricity", "cleanliness": "Cleanliness",
                   "internet": "Internet connectivity"}


def scope(staff: dict) -> str | None:
    """The category a staff member works on, or None for an admin (all departments)."""
    return None if staff.get("is_admin") else staff["department"]


def status_label(ticket: dict) -> str:
    """Human label for a ticket's status; confirmed duplicates read 'Duplicate of CC-xxxx'."""
    if ticket.get("dup_review") == "confirmed" and ticket.get("primary_code") and ticket["primary_code"] != ticket["code"]:
        return f"Duplicate of {ticket['primary_code']}"
    if ticket.get("self_resolved"):
        return "Self-resolved"
    return STATUS_LABELS.get(ticket["status"], ticket["status"].title())


def urgency_label(ticket: dict) -> str:
    """Urgent / High / Normal / Low."""
    return config.URGENCY_LABELS.get(ticket["tier"], ticket["tier"].title())


# --- quick replies ---------------------------------------------------------------------------------

def quick_replies(category: str | None = None) -> list[dict]:
    """Canned replies [{id, label, en, hi}] from data/quick_replies.json: the 'All' ones plus the category's."""
    try:
        data = json.loads(QUICK_REPLIES_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    want = _REPLY_CATEGORY.get(category or "")
    return [d for d in data if d.get("category") in ("All", None, "", want)]


def fill_reply(template: str, ticket: dict, staff: dict, language: str = "en") -> str:
    """Fill {student_name} {ticket_id} {department} {staff_name} {eta} in a template. Unknown braces are left alone."""
    values = {
        "student_name": ticket["student_name"], "ticket_id": ticket["code"],
        "department": config.DEPARTMENTS.get(ticket["category"], ticket["category"]),
        "staff_name": staff["name"], "eta": eta_text(ticket["eta_at"]),
    }
    out = template
    for key, val in values.items():
        out = out.replace("{" + key + "}", str(val))
    return out


def reply_text(reply: dict, language: str) -> str:
    """The reply in 'en' or 'hi', falling back to English."""
    return reply.get(language) or reply["en"]


# --- student side ----------------------------------------------------------------------------------

def student_tickets(student_id: int) -> list[dict]:
    """The student's tickets, newest first, each with eta_text and status_label added."""
    rows = tdb.list_tickets(student_id=student_id)
    rows.sort(key=lambda t: t["created_at"], reverse=True)
    return [{**t, "eta_text": eta_text(t["eta_at"]), "status_label": status_label(t)} for t in rows]


def ticket_timeline(ticket_id: int, include_internal: bool = False) -> list[dict]:
    """Status history oldest first with a formatted IST time. Staff-only notes appear only if include_internal."""
    return [{**h, "when": fmt_ist(h["changed_at"])} for h in tdb.get_history(ticket_id, include_internal)]


# --- staff: list, filters, metrics ------------------------------------------------------------------

def _overdue_reason(t: dict, first_response, now) -> str | None:
    if t["status"] == "resolved":
        return None
    age = now - t["created_at"]
    limit = timedelta(hours=config.OVERDUE_HOURS[t["category"]])
    if age > limit:
        return f"Overdue: open for more than {config.OVERDUE_HOURS[t['category']]} h"
    first = config.FIRST_RESPONSE_HOURS[t["category"]]
    if first_response is None and age > timedelta(hours=first):
        label = f"{int(first * 60)} min" if first < 1 else f"{first:g} h"
        return f"Overdue: no staff response in {label}"
    return None


def with_overdue(tickets: list[dict]) -> list[dict]:
    """Add 'overdue' (reason text or None) to each ticket using the department's response targets."""
    now = now_utc()
    firsts = tdb.first_response_times([t["id"] for t in tickets if t["status"] != "resolved"])
    return [{**t, "overdue": _overdue_reason(t, firsts.get(t["id"]), now)} for t in tickets]


def staff_tickets(staff: dict, status: str | None = None, urgency: str | None = None, category: str | None = None,
                  search: str = "", mine: bool = False, include_resolved: bool = False) -> list[dict]:
    """Tickets for the dashboard list, most urgent first then oldest. Admin sees every department.

    status: 'new' | 'needs_info' | 'waiting' | 'assigned' | 'in_progress' | 'resolved' | 'overdue' | None
    urgency: critical|high|normal|later. category narrows an admin's view; staff are fixed to their own.
    """
    cat = scope(staff) or category
    statuses = None if (include_resolved or status == "resolved") else OPEN_STATUSES
    if status in ("waiting", "assigned", "in_progress", "resolved"):
        statuses = [status]
    rows = tdb.list_tickets(category=cat, statuses=statuses, search=search or None,
                            assigned_to=staff["id"] if mine else None, limit=500)
    if status == "new":
        rows = [t for t in rows if t["status"] in ("waiting", "assigned") and t["info_complete"]]
    elif status == "needs_info":
        rows = [t for t in rows if not t["info_complete"] and t["status"] != "resolved"]
    if urgency:
        rows = [t for t in rows if t["tier"] == urgency]
    rows = [{**t, "age": time_ago(t["created_at"]), "eta_text": eta_text(t["eta_at"]),
             "status_label": status_label(t), "urgency_label": urgency_label(t)} for t in with_overdue(rows)]
    if status == "overdue":
        rows = [t for t in rows if t["overdue"]]
    rows.sort(key=lambda t: (priority.TIER_ORDER.index(t["tier"]), t["created_at"]))
    return rows


CSV_COLUMNS = [("code", "Ticket"), ("title", "Title"), ("status_label", "Status"), ("urgency_label", "Urgency"),
               ("landmark", "Place"), ("floor", "Floor"), ("staff_name", "Assigned to"), ("eta_text", "ETA"),
               ("created_at", "Reported at")]


def _csv_safe(value: object) -> str:
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@") else text


def tickets_csv(rows: list[dict]) -> str:
    """The staff ticket list as CSV. Student names and roll numbers are left out."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([label for _, label in CSV_COLUMNS])
    for t in rows:
        cells = [fmt_ist(t[k]) if k == "created_at" else t.get(k) for k, _ in CSV_COLUMNS]
        writer.writerow([_csv_safe(c) for c in cells])
    return buf.getvalue()


def staff_metrics(staff: dict) -> dict:
    """Dashboard cards: new, needs_info, in_progress, resolved_today, overdue."""
    counts = tdb.status_counts(scope(staff))
    overdue = sum(1 for t in with_overdue(tdb.list_tickets(category=scope(staff), statuses=OPEN_STATUSES, limit=500)) if t["overdue"])
    return {**counts, "overdue": overdue}


@st.cache_data(ttl=60)
def recurring(category: str | None) -> list[dict]:
    """Recurring-problem banners for a category, or all when None. Cached a minute: these change slowly."""
    return alert_logic.recurring_banners(category)


def duplicate_reviews(staff: dict) -> list[dict]:
    """Tickets awaiting Confirm/Separate, each with its primary ticket for the side-by-side view."""
    out = []
    for t in tdb.list_tickets(category=scope(staff), dup_review="pending"):
        g = gdb.get_group(t["group_id"]) if t["group_id"] else None
        primary = g["primary"] if g else None
        if primary and primary["id"] != t["id"]:
            out.append({"ticket": t, "primary": tdb.get_ticket(primary["id"]), "group": g})
    return out


def ticket_detail(ticket_id: int) -> dict | None:
    """Everything the staff detail panel needs: ticket, full timeline (with internal notes), group, linked, photo."""
    t = tdb.get_ticket(ticket_id)
    if t is None:
        return None
    group = gdb.get_group(t["group_id"]) if t["group_id"] else None
    linked = [x for x in tdb.list_tickets(group_id=t["group_id"]) if x["id"] != ticket_id] if t["group_id"] else []
    overdue = with_overdue([t])[0]["overdue"]
    return {
        "ticket": {**t, "age": time_ago(t["created_at"]), "eta_text": eta_text(t["eta_at"]), "overdue": overdue,
                   "status_label": status_label(t), "urgency_label": urgency_label(t), "created_text": fmt_ist(t["created_at"])},
        "timeline": ticket_timeline(ticket_id, include_internal=True), "group": group, "linked": linked,
        "photo": tdb.get_ticket_photo(ticket_id) if t["has_photo"] else None,
    }


def insights(staff: dict) -> dict:
    """Insights tab data: {by_category, top_locations, avg_resolution}. Staff see their own category; admin sees all."""
    return _insights(scope(staff))


@st.cache_data(ttl=60)
def _insights(cat: str | None) -> dict:
    by_cat = [r for r in tdb.tickets_by_category(7) if not cat or r["category"] == cat]
    avg = [r for r in tdb.avg_resolution_by_category() if not cat or r["category"] == cat]
    return {"by_category": by_cat, "top_locations": tdb.top_locations(7, 5), "avg_resolution": avg}


def staff_directory(department: str | None = None) -> list[dict]:
    """Staff list for the assign dropdown (id, name, department). Admins are not assignable."""
    return [s for s in udb.list_staff() if s["role"] != "admin" and (department is None or s["department"] == department)]


def open_alerts(department: str | None = None) -> list[dict]:
    """Unacknowledged alerts, newest first, optionally for one department."""
    return [{**a, "age": time_ago(a["created_at"])} for a in gdb.list_alerts(department, only_open=True)]


def acknowledge_alert(alert_id: int, staff: dict) -> None:
    """Mark an alert acknowledged by this staff member."""
    gdb.acknowledge_alert(alert_id, staff["name"])


def analytics(staff: dict) -> dict:
    """Analytics page data for the staff member's scope: 14-day daily volume, this week against last week, resolution, repeat places."""
    return _analytics(scope(staff))


@st.cache_data(ttl=60)
def _analytics(cat: str | None) -> dict:
    daily = tdb.daily_volume(14, cat)
    week = tdb.window_summary(7, cat)
    repeats = {r["landmark_id"] for r in tdb.recurring_locations(7, 2) if not cat or r["category"] == cat}
    return {
        "daily": [(r["day"], r["n"]) for r in daily],
        "this_week": sum(r["n"] for r in daily[7:]),
        "last_week": sum(r["n"] for r in daily[:7]),
        "total": week["total"],
        "resolved": week["resolved"],
        "repeat_places": len(repeats),
    }


def urgent_locations(staff: dict, days: int, threshold: int = config.HOTSPOT_REPORTS) -> list[dict]:
    """Place and category pairs with reports in the last N days; at_threshold once threshold reports are reached."""
    cat = scope(staff)
    rows = [r for r in tdb.recurring_locations(days, 1) if not cat or r["category"] == cat]
    return [{**r, "at_threshold": r["count"] >= threshold} for r in rows[:25]]


def escalate(staff: dict, landmark_id: int, landmark: str, category: str) -> str:
    """Raise a critical alert on the open group at a place. Returns 'sent', 'exists' or 'none'."""
    group = gdb.open_group_at(landmark_id, category)
    if group is None:
        return "none"
    msg = f"Escalated by {staff['name']}: {group['title']} at {landmark}."
    return "sent" if gdb.create_alert(group["id"], "critical", msg) else "exists"
