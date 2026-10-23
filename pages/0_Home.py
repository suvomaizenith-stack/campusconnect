"""Landing page: sign-in screen for visitors, a welcome hero for signed-in users."""
import streamlit as st

from logic import auth
from ui.session import current_user, login_staff, login_student
from ui.theme import auth_art, esc, hero_art, kicker

user = current_user()

if user:
    is_student = user["role"] == "student"
    first = user["name"].split()[0] if user["name"].strip() else user["name"]
    with st.container(key="hero"):
        st.markdown(hero_art(), unsafe_allow_html=True)
        st.markdown(kicker("Welcome back"), unsafe_allow_html=True)
        st.markdown(f"<h1>Hello, <em>{esc(first)}</em>.</h1>", unsafe_allow_html=True)
        st.markdown(
            '<p class="sub">Report a problem, follow it to the fix, and see what is happening across campus.</p>'
            if is_student else
            '<p class="sub">Your queue, duplicate reviews and campus alerts are one click away.</p>',
            unsafe_allow_html=True,
        )
        with st.container(key="i_arrow-up-right__cta"):
            if is_student:
                st.page_link("pages/1_Report_a_Problem.py", label="Report a problem")
            else:
                st.page_link("pages/3_Staff_Dashboard.py", label="Open dashboard")
    st.stop()

art, form = st.columns([5, 4], gap="large")
art.markdown(auth_art(), unsafe_allow_html=True)

with form:
    st.markdown(
        f'<div class="cc-auth-form">{kicker("Welcome")}<h2>Sign in to Campus Saathi</h2>'
        "<p>Pick the option that matches you.</p></div>",
        unsafe_allow_html=True,
    )
    tab_student, tab_staff = st.tabs(["Student", "Staff"])

    with tab_student:
        login_tab, signup_tab = st.tabs(["Log in", "Sign up"])
        with login_tab, st.form("student_login", border=False):
            roll = st.text_input("Roll number")
            pin = st.text_input("PIN", type="password")
            if st.form_submit_button("Log in", type="primary", key="i_log-in__student_login", use_container_width=True):
                try:
                    login_student(auth.login_student(roll, pin))
                except auth.AuthError as e:
                    st.error(str(e))
                else:
                    st.rerun()
        with signup_tab, st.form("student_signup", border=False):
            name = st.text_input("Full name")
            roll_new = st.text_input("Roll number", key="roll_new")
            pin1 = st.text_input("Choose a PIN (4-8 digits)", type="password")
            pin2 = st.text_input("Repeat PIN", type="password")
            if st.form_submit_button("Create account", type="primary", key="i_user-plus__student_signup", use_container_width=True):
                try:
                    login_student(auth.signup_student(name, roll_new, pin1, pin2))
                except auth.AuthError as e:
                    st.error(str(e))
                else:
                    st.rerun()

    with tab_staff:
        st.caption("Staff accounts are created by the admin. Use the username and access key you were given.")
        with st.form("staff_login", border=False):
            username = st.text_input("Username")
            key = st.text_input("Access key", type="password")
            if st.form_submit_button("Log in", type="primary", key="i_log-in__staff_login", use_container_width=True):
                try:
                    login_staff(auth.login_staff(username, key))
                except auth.AuthError as e:
                    st.error(str(e))
                else:
                    st.rerun()
