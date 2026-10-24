"""Staff: the ticket register. Every ticket in the staff member's scope as a searchable, filterable table."""
import streamlit as st

import config
from logic import views
from ui.session import require_role
from ui.theme import category_chip, chip, dash_head, empty_state, esc, panel_head, stat_row

PAGE_ROWS = 100
STATUS_FILTERS = {"All statuses": None, "Waiting": "waiting", "Assigned": "assigned", "In progress": "in_progress",
                  "Resolved": "resolved", "Needs info": "needs_info", "Overdue": "overdue"}
URGENCY_FILTERS = {"All priorities": None, **{label: tier for tier, label in config.URGENCY_LABELS.items()}}

staff = require_role("staff")

head, cta = st.columns([3, 1], vertical_alignment="center")
with head:
    dash_head("Ticket management", "All tickets", "Search, review, and track the complaints reported across campus.")
with cta, st.container(key="i_layout-dashboard__cta_dash"):
    st.page_link("pages/3_Staff_Dashboard.py", label="Open dashboard")

everything = views.staff_tickets(staff, include_resolved=True)
open_n = sum(1 for t in everything if t["status"] in ("waiting", "assigned"))
stat_row([
    {"label": "All tickets", "value": len(everything), "icon": "ticket",
     "hint": "All departments" if staff.get("is_admin") else config.DEPARTMENTS.get(staff["department"], "")},
    {"label": "Open", "value": open_n, "icon": "clock", "hint": "Awaiting action", "color": "amber"},
    {"label": "In progress", "value": sum(1 for t in everything if t["status"] == "in_progress"), "icon": "refresh-cw",
     "hint": "Assigned to staff", "color": "blue"},
    {"label": "Resolved", "value": sum(1 for t in everything if t["status"] == "resolved"), "icon": "circle-check",
     "hint": "Completed reports", "color": "green"},
])
st.write("")

with st.container(border=True):
    cols = st.columns([2, 1.3, 1, 1, 1] if staff.get("is_admin") else [2, 1.3, 1, 1], vertical_alignment="center")
    with cols[0]:
        panel_head("Ticket register", "Most urgent first, then oldest. Student names are never shown here.")
    search = cols[1].text_input("Search", placeholder="Code, title or place", label_visibility="collapsed", key="at_q")
    status = cols[2].selectbox("Status", list(STATUS_FILTERS), label_visibility="collapsed", key="at_status")
    urgency = cols[3].selectbox("Priority", list(URGENCY_FILTERS), label_visibility="collapsed", key="at_urgency")
    category = None
    if staff.get("is_admin"):
        cats = {"All categories": None, **{config.CATEGORY_LABELS[c]: c for c in config.CATEGORIES}}
        category = cats[cols[4].selectbox("Category", list(cats), label_visibility="collapsed", key="at_cat")]

    rows = views.staff_tickets(staff, status=STATUS_FILTERS[status], urgency=URGENCY_FILTERS[urgency],
                               category=category, search=search, include_resolved=True)
    if not rows:
        empty_state("Nothing matches these filters", "Try another status or clear the search.", "search")
    else:
        body = "".join(
            "<tr>"
            f"<td class='mono'>{esc(t['code'])}</td>"
            f"<td class='title'>{esc(t['title'])}</td>"
            f"<td>{esc((t['landmark'] or 'Campus') + (', ' + t['floor'] + ' floor' if t['floor'] else ''))}</td>"
            f"<td>{category_chip(t['category'])}</td>"
            f"<td>{chip('self_resolved' if t['self_resolved'] else t['status'], t['status_label'])}"
            f"{chip('overdue', 'Overdue') if t['overdue'] else ''}</td>"
            f"<td>{chip(t['tier'], t['urgency_label'])}</td>"
            f"<td>{esc(t['staff_name'] or 'Unassigned')}</td>"
            f"<td class='muted'>{esc(t['age'])}</td>"
            "</tr>"
            for t in rows[:PAGE_ROWS]
        )
        st.markdown(
            "<div class='cc-tablewrap'><table class='cc-table'><thead><tr><th>ID</th><th>Issue</th><th>Location</th>"
            "<th>Category</th><th>Status</th><th>Priority</th><th>Assigned to</th><th>Created</th></tr></thead>"
            f"<tbody>{body}</tbody></table></div>", unsafe_allow_html=True)
        shown = min(len(rows), PAGE_ROWS)
        note, dl = st.columns([3, 1], vertical_alignment="center")
        note.caption(f"Showing {shown} of {len(rows)} tickets. Open a ticket from the dashboard to assign it or reply.")
        dl.download_button("Download CSV", views.tickets_csv(rows), file_name="campus_saathi_tickets.csv",
                           mime="text/csv", key="i_arrow-right__at_csv", width="stretch")
