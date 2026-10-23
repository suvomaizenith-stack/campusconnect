"""Urgency: places where reports are piling up, with an escalate action that raises a critical alert."""
import streamlit as st

from logic import settings as settings_logic
from logic import views
from ui.session import require_role
from ui.theme import category_chip, empty_state, esc, page_header

staff = require_role("staff")
page_header("Urgency", "Locations needing attention",
            "Places where reports are piling up. Escalate raises a critical alert for the team.")


def save_threshold() -> None:
    try:
        settings_logic.save("hotspot_reports", st.session_state["ug_threshold"], staff["name"])
    except Exception:
        st.toast("Could not save the threshold. Try again.")


WINDOWS = {"Last 24 hours": 1, "Last 7 days": 7}
window = st.segmented_control("Window", list(WINDOWS), default="Last 24 hours", key="ug_window")
threshold = st.slider("Threshold reached at this many reports", *settings_logic.HOTSPOT_RANGE,
                      value=settings_logic.load()["hotspot_reports"], key="ug_threshold", on_change=save_threshold,
                      disabled=not staff.get("is_admin"),
                      help="Places with this many reports are marked 'Threshold reached'. Only admins can change it.")
rows = views.urgent_locations(staff, WINDOWS[window or "Last 24 hours"], threshold)

if not rows:
    empty_state("Nothing needs attention", "No place has reports in this window.", "circle-check")

messages = {
    "sent": "Escalated. The team has a critical alert.",
    "exists": "Already escalated and waiting for a response.",
    "none": "No open report to escalate here.",
}
for i, r in enumerate(rows):
    with st.container(border=True):
        left, right = st.columns([4, 1], vertical_alignment="center")
        with left:
            st.markdown(f"**{esc(r['landmark'])}** &nbsp; {category_chip(r['category'])}", unsafe_allow_html=True)
            state = "Threshold reached" if r["at_threshold"] else "Monitoring"
            st.caption(f"{r['count']} report{'s' if r['count'] != 1 else ''} · {state}")
        with right:
            if st.button("Escalate", key=f"i_triangle-alert__esc{i}", width="stretch"):
                result = views.escalate(staff, r["landmark_id"], r["landmark"], r["category"])
                st.toast(messages[result])
