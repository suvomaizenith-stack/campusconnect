"""Student: my tickets with status, ETA, timeline and chat with the assigned staff member."""
import streamlit as st

from logic import chat, views, workflow
from ui.session import require_role
from ui.theme import chip, esc, timeline

student = require_role("student")
viewer = {"role": "student", "id": student["id"], "name": student["name"]}

st.title("My tickets")

rows = views.student_tickets(student["id"])
if not rows:
    st.info("You have not reported anything yet. Use Report a Problem to create your first ticket.")
    st.stop()


@st.fragment(run_every=5)
def chat_box(ticket_id: int, closed: bool) -> None:
    """Chat thread that refreshes every 5 seconds, plus the message box."""
    for m in chat.get_thread(ticket_id, viewer):
        who = "user" if m["sender_role"] == "student" else "assistant"
        with st.chat_message(who):
            st.markdown(f"**{esc(m['sender_name'])}**", unsafe_allow_html=True)
            st.text(m["body"])
    if not closed:
        with st.form(f"chat_form_{ticket_id}", clear_on_submit=True):
            msg = st.text_input("Message", key=f"chat_{ticket_id}")
            if st.form_submit_button("Send") and msg.strip():
                chat.send_chat(ticket_id, viewer, msg)
                st.rerun(scope="fragment")


for t in rows:
    done = t["status"] == "resolved"
    with st.expander(f"{t['code']} · {t['title']}", expanded=not done and t is rows[0]):
        st.markdown(
            f"{chip('self_resolved' if t['self_resolved'] else t['status'], t['status_label'])} "
            f"&nbsp; {esc(t['category'].title())} · {esc(t['landmark'] or 'Campus')}"
            + (f", {esc(t['floor'])} floor" if t["floor"] else ""),
            unsafe_allow_html=True,
        )
        if not done:
            who = t["staff_name"] or "waiting for a staff member"
            st.write(f"Handled by: **{who}** · {t['eta_text']}")
        if t["missing_fields"] and not t["info_complete"]:
            st.warning("We need a bit more detail. Please answer in the chat below.")
        timeline([{"label": h["status"].replace("_", " ").title(), "detail": h["note"], "when": h["when"]}
                  for h in views.ticket_timeline(t["id"])])
        if not done and st.button("Mark as solved", key=f"solved_{t['id']}"):
            workflow.mark_self_resolved(t["id"], student)
            st.rerun()
        st.markdown("**Chat**")
        chat_box(t["id"], done)
