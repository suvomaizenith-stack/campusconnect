"""Latest reports: the newest open problems on campus. Students can confirm they face the same problem."""
import streamlit as st

from logic import map_data, tickets
from logic import settings as settings_logic
from logic.timeutil import time_ago
from ui.session import require_role
from ui.theme import category_chip, chip, empty_state, esc, meta, page_header

FEED_LIMIT = 30

student = require_role("student")
page_header("Latest reports", "What students are reporting",
            "The newest open problems. If you face one too, tap I face this too so staff see how many are affected.")
if not settings_logic.load()["latest_reports"]:
    empty_state("Latest reports are paused", "Staff have turned this feed off for now.", "megaphone")
    st.stop()

open_groups = [g for g in map_data.live_groups(24) if not g["resolved"]]
open_groups.sort(key=lambda g: g["last_reported_at"], reverse=True)

if not open_groups:
    empty_state("No open reports right now", "New problems will show up here as students report them.", "circle-check")

for g in open_groups[:FEED_LIMIT]:
    with st.container(border=True):
        st.markdown(f"### {esc(g['title'])}", unsafe_allow_html=True)
        place = (g["landmark"] or "Campus") + (f", {g['floor']} floor" if g["floor"] else "")
        st.markdown(
            meta("map-pin", place)
            + f'<div class="cc-meta">{category_chip(g["category"])} &nbsp; {chip(g["level"])}</div>'
            + meta("users", f"{g['count']} report{'s' if g['count'] != 1 else ''} · last reported {time_ago(g['last_reported_at'])}"),
            unsafe_allow_html=True,
        )
        if st.button("I face this too", key=f"i_hand-heart__lr{g['id']}", type="primary"):
            added = tickets.say_me_too({"id": student["id"], "name": student["name"], "roll": student["roll"]}, g["id"])
            st.toast("Thanks! Your report was added." if added else "You have already reported this.")
            st.rerun()
