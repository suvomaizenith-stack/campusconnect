"""Student: my tickets with status, ETA, timeline and chat with the assigned staff member."""
import streamlit as st

from logic import chat, views, workflow
from ui.session import require_role
from ui.theme import category_chip, chip, empty_state, esc, meta, page_header, timeline

student = require_role("student")
viewer = {"role": "student", "id": student["id"], "name": student["name"]}

page_header("My tickets", "Everything you reported", "Follow each problem from report to fix, and chat with the person handling it.")

rows = views.student_tickets(student["id"])
if not rows:
    empty_state("Nothing reported yet", "Use Report a Problem to create your first ticket.", "ticket")
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
        with st.form(f"chat_form_{ticket_id}", clear_on_submit=True, border=False):
            msg = st.text_input("Message", key=f"chat_{ticket_id}")
            if st.form_submit_button("Send", key=f"i_send__chat{ticket_id}") and msg.strip():
                chat.send_chat(ticket_id, viewer, msg)
                st.rerun(scope="fragment")


for t in rows:
    done = t["status"] == "resolved"
    with st.expander(f"{t['code']} · {t['title']}", expanded=not done and t is rows[0]):
        st.markdown(
            f"{category_chip(t['category'])} "
            f"{chip('self_resolved' if t['self_resolved'] else t['status'], t['status_label'])}",
            unsafe_allow_html=True,
        )
        st.markdown(meta("map-pin", (t["landmark"] or "Campus") + (f", {t['floor']} floor" if t["floor"] else "")),
                    unsafe_allow_html=True)
        if not done:
            st.markdown(meta("user-check", f"{t['eta_text']}", f"Handled by {t['staff_name'] or 'nobody yet'}."),
                        unsafe_allow_html=True)
        if t["missing_fields"] and not t["info_complete"]:
            st.warning("We need a bit more detail. Please answer in the chat below.")
        st.markdown("**Progress**")
        timeline([{"label": h["status"].replace("_", " ").title(), "detail": h["note"], "when": h["when"]}
                  for h in views.ticket_timeline(t["id"])])
        if not done and st.button("Mark as solved", key=f"i_circle-check__solved{t['id']}"):
            workflow.mark_self_resolved(t["id"], student)
            st.rerun()
        st.markdown("**Chat**")
        chat_box(t["id"], done)
