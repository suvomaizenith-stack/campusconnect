"""Staff login page (placeholder)."""
import streamlit as st

st.title("🔐 Staff Login")

with st.form("login"):
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.form_submit_button("Log in"):
        st.info("TODO: verify credentials and set st.session_state['staff'].")
