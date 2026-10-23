"""Settings: routing, response targets, alert thresholds, saved feature toggles and AI guardrails."""
import streamlit as st

import config
from logic import settings as settings_logic
from ui.session import require_role
from ui.theme import page_header, section_head

staff = require_role("staff")
page_header("Admin", "Settings", "Routing, targets and rules. Feature toggles save as soon as you change them.")
if not staff.get("is_admin"):
    st.warning("Only admins can see settings.")
    st.stop()


def hours_text(h: float) -> str:
    return f"{round(h * 60)} minutes" if h < 1 else f"{h:g} hour{'s' if h != 1 else ''}"


def save_toggle(key: str) -> None:
    try:
        settings_logic.save(key, st.session_state[f"set_{key}"], staff["name"])
    except Exception:
        st.toast("Could not save this setting. Try again.")


section_head("Routing", "Departments & response targets")
st.table([
    {
        "Category": config.CATEGORY_LABELS[c],
        "Department": config.DEPARTMENTS[c],
        "First response target": hours_text(config.FIRST_RESPONSE_HOURS[c]),
        "Overdue after": hours_text(config.OVERDUE_HOURS[c]),
    }
    for c in config.CATEGORIES
])

current = settings_logic.load()

section_head("Features", "Show or hide")
st.toggle("Recurring-problem banners on the staff dashboard", value=current["recurring_banners"],
          key="set_recurring_banners", on_change=save_toggle, args=("recurring_banners",))
st.toggle("Latest reports feed for students", value=current["latest_reports"],
          key="set_latest_reports", on_change=save_toggle, args=("latest_reports",))

section_head("Alerts", "Threshold settings")
st.markdown(
    f"- **Hotspot:** {current['hotspot_reports']} reports at one place within {config.ALERT_WINDOW_HOURS} hours. "
    f"Change it on the Urgency page.\n"
    f"- **Critical:** {config.CRITICAL_REPORTS} reports, or a single safety-critical report.\n"
    f"- **Recurring problem:** {config.RECURRING_YELLOW} tickets (yellow) or {config.RECURRING_RED} tickets (red) "
    f"for the same place and category within {config.RECURRING_DAYS} days."
)

section_head("AI", "Guardrails")
st.markdown(
    "- Suggests a department from the report text. Staff make the final routing decision.\n"
    "- Points out possible duplicates for review. Nothing is merged or deleted automatically.\n"
    "- Asks the student only for details that are missing.\n"
    "- Tickets close only when staff mark them resolved with a note."
)
st.caption("Toggles and the hotspot threshold are saved in the database. The other values come from the app's configuration file.")
