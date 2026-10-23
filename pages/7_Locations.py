"""Locations: every numbered campus place with the reports open at it in the last 24 hours."""
import streamlit as st

from logic import map_data, mapfile
from ui.session import require_role
from ui.theme import empty_state, esc, meta, page_header

require_role("staff")
page_header("Campus setup", "Locations", "Every numbered place on the campus map, with the open reports at each one in the last 24 hours.")

query = st.text_input("Search locations", placeholder="e.g. library, block C or 7", label_visibility="collapsed")
places = [e for e in map_data.index_with_counts(24) if e["kind"] == "place"]
if query.strip():
    q = query.strip().lower()
    places = [e for e in places if q in e["name"].lower() or (e["number"] is not None and q == str(e["number"]))]

if not places:
    empty_state("No location matches", "Try a different name or number.", "map-pin")

for e in places:
    lm = mapfile.by_id(e["id"]) or {"floors": []}
    with st.container(border=True):
        left, right = st.columns([4, 1], vertical_alignment="center")
        with left:
            head = f"{e['number']}. " if e["number"] else ""
            st.markdown(f"**{head}{esc(e['name'])}**", unsafe_allow_html=True)
            floors = ", ".join(lm["floors"]) if lm["floors"] else "Ground"
            st.markdown(meta("layers", f"Floors: {floors}") + meta("users", f"{e['count']} open in 24 hours"),
                        unsafe_allow_html=True)
