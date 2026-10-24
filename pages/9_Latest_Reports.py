"""Latest reports: the newest open problems on campus. Students can confirm they face the same problem."""
import streamlit as st

import config
from db import groups as gdb
from logic import map_data, tickets
from logic import settings as settings_logic
from logic.timeutil import fmt_ist, now_utc, time_ago
from ui.session import require_role
from ui.theme import CATEGORY_STYLE, banner, category_chip, chip, dash_head, empty_state, list_row, panel_head, stat_row

FEED_LIMIT = 30
LEVEL_LABEL = {"critical": "Staff alerted", "hotspot": "Hotspot", "normal": "Monitoring"}

student = require_role("student")
dash_head("Live incident awareness", "Latest reports",
          "See recent reports by place and time. Confirming I face this too adds your signal without making you "
          "repeat the report.")
if not settings_logic.load()["latest_reports"]:
    empty_state("Latest reports are paused", "Staff have turned this feed off for now.", "megaphone")
    st.stop()

open_groups = [g for g in map_data.live_groups(24) if not g["resolved"]]
hour_ago = now_utc().timestamp() - 3600
recent = [g for g in open_groups if g["last_reported_at"].timestamp() >= hour_ago]
newest = max(open_groups, key=lambda g: g["last_reported_at"], default=None)
stat_row([
    {"label": "Recent incidents", "value": len(recent), "icon": "megaphone", "hint": "Reported in the last hour"},
    {"label": "Community confirmations", "value": sum(max(g["count"] - 1, 0) for g in open_groups), "icon": "users",
     "hint": "Extra students on open issues", "color": "amber"},
    {"label": "Threshold reached", "value": sum(1 for g in open_groups if g["level"] == "critical"), "icon": "siren",
     "hint": "Staff alert created", "color": "red"},
    {"label": "Latest report", "value": time_ago(newest["last_reported_at"]) if newest else "None",
     "icon": "clock", "hint": (newest["landmark"] or "Campus") if newest else "Nothing open", "color": "green"},
])
banner(f"Each I face this too is one signal per student, attached to the shared incident. At "
       f"{config.CRITICAL_REPORTS} reports in {config.ALERT_WINDOW_HOURS} hours staff get an immediate alert. "
       "Reporters' names are never shown.", "info")

with st.container(border=True):
    h, f1, f2 = st.columns([2.2, 1, 1], vertical_alignment="center")
    with h:
        panel_head("Recent campus incidents", "Choose an incident to confirm you are affected.")
    labels = {config.CATEGORY_LABELS[c]: c for c in config.CATEGORIES}
    kind = f1.selectbox("Category", ["All categories"] + list(labels), label_visibility="collapsed", key="lr_cat")
    order = f2.selectbox("Sort", ["Newest", "Most reported"], label_visibility="collapsed", key="lr_sort")
    rows = [g for g in open_groups if kind == "All categories" or g["category"] == labels[kind]]
    if order == "Most reported":
        rows.sort(key=lambda g: (g["count"], g["last_reported_at"]), reverse=True)
    else:
        rows.sort(key=lambda g: g["last_reported_at"], reverse=True)
    if not rows:
        empty_state("No open reports right now", "New problems will show up here as students report them.",
                    "circle-check")
    for g in rows[:FEED_LIMIT]:
        place = (g["landmark"] or "Campus") + (f" · {g['floor']} floor" if g["floor"] else "")
        n = g["count"]
        with st.container(border=True):
            st.markdown(list_row(
                CATEGORY_STYLE.get(g["category"], ("tag", "gray"))[0], g["title"],
                f"{place} · Reported {time_ago(g['last_reported_at'])} ({fmt_ist(g['last_reported_at'])})",
                category_chip(g["category"]) + chip(g["level"], LEVEL_LABEL.get(g["level"], g["level"])),
                right=(n, "signal" if n == 1 else "signals", "red" if g["level"] == "critical" else "amber"),
            ), unsafe_allow_html=True)
            if gdb.student_reported(g["id"], student["id"]):
                st.button("You confirmed this", key=f"i_circle-check__lr{g['id']}", disabled=True)
            elif st.button("I face this too", key=f"i_hand-heart__lr{g['id']}", type="primary"):
                added = tickets.say_me_too({"id": student["id"], "name": student["name"], "roll": student["roll"]}, g["id"])
                st.toast("Thanks, your confirmation was added to the incident." if added else "You have already reported this.")
                st.rerun()
    st.caption("A confirmation is an impact signal, not a new duplicate ticket.")
