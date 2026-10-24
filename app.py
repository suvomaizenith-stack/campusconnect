"""Campus Saathi entry point: theme, one-time DB setup, role-based navigation, staff alert bar."""
import streamlit as st

from ai.llm import get_ai_status
from logic import drafts as drafts_logic
from logic import views
from logic.setup import bootstrap
from ui.icons import icon
from ui.session import current_user, logout
from ui.theme import banner, brand, inject_css, theme_toggle, user_card

st.set_page_config(page_title="Campus Saathi", page_icon=":material/school:", layout="wide")


@st.cache_resource(show_spinner=False)
def _boot() -> str | None:
    """Create tables and load landmarks once per server process. Returns an error message or None."""
    try:
        bootstrap()
    except Exception as e:  # database unreachable or misconfigured
        return f"{type(e).__name__}"
    return None


inject_css()
_error = _boot()
if _error:
    _boot.clear()
    st.error("Campus Saathi cannot reach its database right now. Check DATABASE_URL in .env (or the app's Secrets on Streamlit Cloud) and try again.")
    st.caption(f"Technical detail: {_error}")
    st.stop()

# TODO (post-MVP): voice notes, Telegram intake, staff-to-staff channels, learned ETA.
HOME = st.Page("pages/0_Home.py", title="Home", default=True)
REPORT = st.Page("pages/1_Report_a_Problem.py", title="Report a Problem", url_path="report")
TICKETS = st.Page("pages/2_My_Tickets.py", title="My Tickets")
DRAFTS = st.Page("pages/10_My_Drafts.py", title="My drafts")
DASH = st.Page("pages/3_Staff_Dashboard.py", title="Dashboard")
MAP = st.Page("pages/4_Outage_Map.py", title="Outage Map")
URGENCY = st.Page("pages/5_Urgency.py", title="Urgency")
ANALYTICS = st.Page("pages/6_Analytics.py", title="Analytics")
LOCATIONS = st.Page("pages/7_Locations.py", title="Locations")
SETTINGS = st.Page("pages/8_Settings.py", title="Settings")
LATEST = st.Page("pages/9_Latest_Reports.py", title="Latest reports")
ALL_TICKETS = st.Page("pages/11_All_Tickets.py", title="All tickets")
ROLE_PAGES = {
    None: [HOME],
    "student": [HOME, REPORT, TICKETS, DRAFTS, MAP, LATEST],
    "staff": [HOME, DASH, ALL_TICKETS, URGENCY, ANALYTICS, LOCATIONS, MAP],
}
NAV_ICONS = {
    HOME: "house", REPORT: "file-pen-line", TICKETS: "ticket", DRAFTS: "sticky-note", DASH: "layout-dashboard", MAP: "map",
    URGENCY: "triangle-alert", ANALYTICS: "activity", LOCATIONS: "map-pinned", SETTINGS: "wrench", LATEST: "megaphone",
    ALL_TICKETS: "clipboard-list",

}

user = current_user()
pages = ROLE_PAGES[user["role"] if user else None]
if user and user.get("is_admin"):
    pages = pages + [SETTINGS]
nav = st.navigation(pages, position="hidden")

with st.sidebar:
    st.markdown(brand(), unsafe_allow_html=True)
    if len(pages) > 1:
        st.markdown('<div class="cc-side-label">MENU</div>', unsafe_allow_html=True)
    for i, page in enumerate(pages):
        label = f"My drafts ({len(drafts_logic.for_student(user))})" if page is DRAFTS else page.title
        with st.container(key=f"i_{NAV_ICONS[page]}__nav{i}"):
            st.page_link(page, label=label)
    if not user:
        st.markdown(
            f'<div class="cc-side-note"><b>{icon("shield-check", 15)}Sign in to begin</b>'
            "<p>Students report problems and track them. Staff manage their department's tickets.</p></div>",
            unsafe_allow_html=True,
        )


@st.fragment(run_every=15)
def _staff_alert_bar(staff: dict) -> None:
    """Banner for open alerts, a toast for new ones, and the AI status note."""
    try:
        alerts = views.open_alerts(None if staff.get("is_admin") else staff["department"])
    except Exception:
        return
    seen = st.session_state.setdefault("seen_alerts", set())
    for a in alerts:
        if a["id"] not in seen:
            seen.add(a["id"])
            st.toast(a["message"], icon=":material/warning:")
    for a in alerts[:3]:
        banner(a["message"], "critical" if a["level"] == "critical" else "hotspot")
    if get_ai_status() == "degraded":
        st.caption("AI status: degraded (using backup rules)")


with st.container(key="topbar"):
    crumb, switch = st.columns([14, 1], vertical_alignment="center")
    crumb.markdown(
        '<div class="cc-crumb"><small>CAMPUS SAATHI &nbsp;/&nbsp; <b>KR MANGALAM UNIVERSITY</b></small></div>',
        unsafe_allow_html=True,
    )
    with switch:
        theme_toggle()

if user and user["role"] == "staff":
    _staff_alert_bar(user)

if user:
    with st.sidebar:
        if user["role"] == "student":
            role = f"Student · {user['roll']}"
        else:
            role = "Admin · all departments" if user.get("is_admin") else user["department"].title() + " staff"
        st.markdown(user_card(user["name"], role), unsafe_allow_html=True)
        with st.container(key="i_log-out__logout"):
            if st.button("Log out", width="stretch"):
                logout()
                st.rerun()

nav.run()
