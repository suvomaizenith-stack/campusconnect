"""Student: unsent report drafts. Save one now, continue it in Report a Problem, or delete it."""
import streamlit as st

import config
from logic import drafts, tickets
from logic.timeutil import time_ago
from ui.session import require_role
from ui.theme import category_chip, empty_state, list_row, page_header, panel_head

REPORT_PAGE = "pages/1_Report_a_Problem.py"
NOT_SURE = "Not sure"
KIND_BY_LABEL = {config.CATEGORY_LABELS[c]: c for c in config.CATEGORIES}

student = require_role("student")
places = [NOT_SURE] + [lm["name"] for lm in tickets.landmark_options()]
kinds = [NOT_SURE] + list(KIND_BY_LABEL)


def save_quick() -> None:
    place, kind = st.session_state["qd_place"], st.session_state["qd_kind"]
    try:
        drafts.save(student, st.session_state["qd_title"], None if place == NOT_SURE else place,
                    KIND_BY_LABEL.get(kind), st.session_state["qd_details"])
    except ValueError as e:
        st.session_state["qd_error"] = str(e)
        return
    st.session_state["qd_error"] = None
    st.session_state["qd_flash"] = "Draft saved."
    st.session_state["qd_title"] = ""
    st.session_state["qd_details"] = ""
    st.session_state["qd_place"] = NOT_SURE
    st.session_state["qd_kind"] = NOT_SURE


def remove(draft_id: int) -> None:
    drafts.remove(student, draft_id)
    st.session_state["qd_flash"] = "Draft deleted."


def continue_draft(draft: dict) -> None:
    st.session_state["rp_prefill"] = draft
    st.switch_page(REPORT_PAGE)


page_header("Saved for later", "My drafts", "Start a report now and finish it later. Continue opens it in the report form.")

if flash := st.session_state.pop("qd_flash", None):
    st.success(flash)
if st.session_state.get("qd_error"):
    st.error(st.session_state["qd_error"])

top, _ = st.columns([1, 3])
if top.button("New report", type="primary", key="i_file-pen-line__newreport"):
    st.switch_page(REPORT_PAGE)

with st.container(border=True):
    panel_head("Quick draft", "Jot down the basics. You can add the rest when you report it.")
    st.text_input("Title", key="qd_title", max_chars=120, placeholder="e.g. Tap leaking near the water cooler")
    p1, p2 = st.columns(2)
    p1.selectbox("Location", places, key="qd_place")
    p2.selectbox("Kind of problem", kinds, key="qd_kind")
    st.text_area("Details (optional)", key="qd_details", max_chars=2000, height=110)
    st.button("Save draft", type="primary", key="qd_save", on_click=save_quick)

panel_head("Saved drafts", "Continue to finish one, or delete it.")
rows = drafts.for_student(student)
if not rows:
    empty_state("No drafts yet", "Drafts you save will appear here until you delete them.", "sticky-note")

for d in rows:
    with st.container(border=True):
        main, go, drop = st.columns([6, 1, 1], vertical_alignment="center")
        place = d["location"] or "Location not sure"
        with main:
            chips = category_chip(d["kind"]) if d["kind"] in config.CATEGORIES else ""
            st.markdown(list_row("sticky-note", d["title"], f"{place} · Saved {time_ago(d['updated_at'])}", chips),
                        unsafe_allow_html=True)
        with go:
            if st.button("Continue", key=f"qd_continue{d['id']}", type="primary"):
                continue_draft({"id": d["id"], "title": d["title"], "location": d["location"],
                                "kind": d["kind"], "details": d["details"]})
        with drop:
            st.button("Delete", key=f"i_trash__del{d['id']}", on_click=remove, args=(d["id"],))
