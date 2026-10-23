"""CampusConnect entry point: theme, one-time seeding, role-based navigation."""
import streamlit as st

from data.seed_staff import seed
from ui.session import current_user, logout
from ui.theme import inject_css

st.set_page_config(page_title="CampusConnect", page_icon="🎓", layout="wide")


@st.cache_resource
def _boot() -> bool:
    """Create tables and demo data once per server process."""
    seed()
    return True


_boot()
inject_css()

# TODO (post-MVP): Telegram intake and staff-to-staff channels.
HOME = st.Page("pages/0_Home.py", title="Home", icon="🏠", default=True)
STUDENT_PAGES = [
    HOME,
    st.Page("pages/1_Report_a_Problem.py", title="Report a Problem", icon="📝"),
    st.Page("pages/2_My_Tickets.py", title="My Tickets", icon="🎫"),
    st.Page("pages/4_Outage_Map.py", title="Outage Map", icon="🗺️"),
]
STAFF_PAGES = [
    HOME,
    st.Page("pages/3_Staff_Dashboard.py", title="Dashboard", icon="🛠️"),
    st.Page("pages/4_Outage_Map.py", title="Outage Map", icon="🗺️"),
]
ROLE_PAGES = {None: [HOME], "student": STUDENT_PAGES, "staff": STAFF_PAGES}

user = current_user()
nav = st.navigation(ROLE_PAGES[user["role"] if user else None])

if user:
    st.sidebar.markdown(f"**{user['name']}**  \n{user['role'].title()}")
    if st.sidebar.button("Log out"):
        logout()
        st.rerun()

nav.run()
