"""Staff dashboard page (placeholder)."""
import streamlit as st

st.title("🛠️ Staff Dashboard")

if "staff" not in st.session_state:
    st.warning("Please log in.")
    st.stop()

st.write(f"Welcome, {st.session_state['staff'].get('name', 'staff')}.")
st.info("TODO: ticket list and actions.")
