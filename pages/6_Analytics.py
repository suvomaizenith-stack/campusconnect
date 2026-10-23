"""Analytics: report volume, resolution and repeat places for the staff member's scope."""
import streamlit as st

import config
from logic import views
from ui.session import require_role
from ui.theme import empty_state, page_header, section_head, stat_row

staff = require_role("staff")
scope_name = "all departments" if staff.get("is_admin") else config.CATEGORY_LABELS[staff["department"]].lower()
page_header("Analytics", "How the queue is moving", f"Volume, resolution and repeat places for {scope_name}.")

data = views.analytics(staff)
diff = data["this_week"] - data["last_week"]
hint = "Same as last week" if diff == 0 else f"{diff:+d} vs last week"
rate = f"{round(100 * data['resolved'] / data['total'])}%" if data["total"] else "—"
stat_row([
    {"label": "Reports this week", "value": data["this_week"], "hint": hint, "featured": True, "icon": "activity"},
    {"label": "Resolution rate", "value": rate, "hint": f"{data['resolved']} of {data['total']} resolved", "icon": "circle-check", "color": "green"},
    {"label": "Repeat places", "value": data["repeat_places"], "hint": "Two or more reports in 7 days", "icon": "map-pin", "color": "amber"},
])

section_head("Volume", "Reports per day, last 14 days")
if any(n for _, n in data["daily"]):
    st.bar_chart({d.strftime("%d %b"): n for d, n in data["daily"]})
else:
    empty_state("No reports in the last 14 days", "", "inbox")

ins = views.insights(staff)
c1, c2 = st.columns(2)
with c1:
    st.markdown("**Top places, last 7 days**")
    for r in ins["top_locations"]:
        st.write(f"{r['landmark']}: {r['count']} tickets, mostly {config.CATEGORY_LABELS.get(r['top_category'], r['top_category']).lower()}")
    if not ins["top_locations"]:
        st.caption("Nothing yet.")
with c2:
    st.markdown("**Average resolution time**")
    for r in ins["avg_resolution"]:
        st.write(f"{config.CATEGORY_LABELS[r['category']]}: {r['hours']} h ({r['resolved']} resolved)")
    if not ins["avg_resolution"]:
        st.caption("No resolved tickets yet.")
