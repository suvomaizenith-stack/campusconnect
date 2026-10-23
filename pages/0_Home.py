"""Landing page: student signup/login and staff login."""
import streamlit as st

from logic import auth
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
    st.stop()

col_student, col_staff = st.columns(2, gap="large")

with col_student, st.container(border=True):
    st.subheader("🎓 I'm a Student")
    login_tab, signup_tab = st.tabs(["Log in", "Sign up"])
    with login_tab, st.form("student_login"):
        roll = st.text_input("Roll number")
        pin = st.text_input("PIN", type="password")
        if st.form_submit_button("Log in", type="primary"):
            try:
                login_student(auth.login_student(roll, pin))
            except auth.AuthError as e:
                st.error(str(e))
            else:
                st.rerun()
    with signup_tab, st.form("student_signup"):
        name = st.text_input("Full name")
        roll_new = st.text_input("Roll number", key="roll_new")
        pin1 = st.text_input("Choose a PIN (4-8 digits)", type="password")
        pin2 = st.text_input("Repeat PIN", type="password")
        if st.form_submit_button("Create account", type="primary"):
            try:
                login_student(auth.signup_student(name, roll_new, pin1, pin2))
            except auth.AuthError as e:
                st.error(str(e))
            else:
                st.rerun()

with col_staff, st.container(border=True):
    st.subheader("🛠️ I'm Staff")
    st.caption("Staff accounts are created by the admin. Use the username and access key you were given.")
    with st.form("staff_login"):
        username = st.text_input("Username")
        key = st.text_input("Access key", type="password")
        if st.form_submit_button("Log in", type="primary"):
            try:
                login_staff(auth.login_staff(username, key))
            except auth.AuthError as e:
                st.error(str(e))
            else:
                st.rerun()
