"""Landing page: hero plus student and staff login cards."""
import streamlit as st

from logic.auth import authenticate_staff, clean_student
from ui.session import current_user, login_staff, login_student
from ui.theme import card

st.markdown(
    '<div class="cc-hero"><h1>CampusConnect</h1>'
    "<p>Report campus issues in plain language. We turn them into tickets your team can track.</p></div>",
    unsafe_allow_html=True,
)

user = current_user()
if user:
    who = "a student" if user["role"] == "student" else f"staff ({user['department']})"
    card(f"Welcome, {user['name']}", f"You are signed in as {who}. Pick a page from the menu.")
else:
    col_student, col_staff = st.columns(2, gap="large")

    with col_student, st.container(border=True):
        st.subheader("🎓 I'm a Student")
        st.caption("Report a problem and track your tickets.")
        with st.form("student_login"):
            name = st.text_input("Full name")
            roll = st.text_input("Roll number")
            if st.form_submit_button("Continue", type="primary"):
                try:
                    login_student(*clean_student(name, roll))
                except ValueError as e:
                    st.error(str(e))
                else:
                    st.rerun()

    with col_staff, st.container(border=True):
        st.subheader("🛠️ I'm Staff")
        st.caption("Work the queue for your department.")
        with st.form("staff_login"):
            username = st.text_input("Username (staff email)")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Log in", type="primary"):
                staff = authenticate_staff(username, password)
                if staff:
                    login_staff(staff)
                    st.rerun()
                else:
                    st.error("Wrong username or password.")
        st.caption("Demo: plumbing@campus.edu, electricity@campus.edu, cleanliness@campus.edu, internet@campus.edu · password changeme123")
