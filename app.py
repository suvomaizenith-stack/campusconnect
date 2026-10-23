"""CampusConnect landing page."""
import streamlit as st

from db.db import init_db

st.set_page_config(page_title="CampusConnect", page_icon="🎓")
init_db()

st.title("🎓 CampusConnect")
st.write("Report campus issues in plain language. We turn them into tickets.")

col1, col2 = st.columns(2)
if col1.button("I'm a Student", use_container_width=True):
    st.switch_page("pages/1_Student_Chat.py")
if col2.button("I'm Staff", use_container_width=True):
    st.switch_page("pages/2_Staff_Login.py")
