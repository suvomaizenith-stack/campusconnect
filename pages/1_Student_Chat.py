"""Student chat page (placeholder)."""
import streamlit as st

st.title("💬 Student Chat")

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.write(m["content"])

if prompt := st.chat_input("Describe your issue..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    reply = "TODO: AI reply goes here."
    st.session_state.messages.append({"role": "assistant", "content": reply})
    st.rerun()
