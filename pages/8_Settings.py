"""Settings: routing, response targets, alert thresholds and AI guardrails, shown read-only to admins."""
import streamlit as st

import config
from ui.session import require_role
from ui.theme import page_header, section_head

staff = require_role("staff")
page_header("Admin", "Settings", "The routing, targets and rules the app uses today. Read-only.")
if not staff.get("is_admin"):
    st.warning("Only admins can see settings.")
    st.stop()


def hours_text(h: float) -> str:
    return f"{round(h * 60)} minutes" if h < 1 else f"{h:g} hour{'s' if h != 1 else ''}"


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

section_head("Alerts", "Threshold settings")
st.markdown(
    f"- **Hotspot:** {config.HOTSPOT_REPORTS} reports at one place within {config.ALERT_WINDOW_HOURS} hours.\n"
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
st.caption("These values come from the app's configuration. Editing them here needs a saved settings table, which is not built yet.")
