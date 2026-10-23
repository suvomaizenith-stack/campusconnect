"""Locations: every numbered campus place with the reports open at it in the last 24 hours, and QR codes for each place."""
from urllib.parse import urlsplit

import streamlit as st

from logic import map_data, mapfile, qrcodes, tickets
from ui.session import require_role
from ui.theme import empty_state, esc, meta, page_header, section_head

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

st.divider()
section_head("Print", "QR codes for places", "Scan with a phone to open the report form with the place already chosen.")


def app_root() -> str:
    parts = urlsplit(st.context.url)
    return f"{parts.scheme}://{parts.netloc}"


base = st.text_input("App address", value=app_root(),
                     help="Use the public address, so phones can open it. Local addresses only work on this computer.")
landmarks = {lm["slug"]: lm["name"] for lm in tickets.landmark_options()}
pick = st.selectbox("Place", list(landmarks), format_func=lambda slug: landmarks[slug])
link = qrcodes.report_link(base, pick)
code = qrcodes.png(link)
q1, q2 = st.columns([1, 2], vertical_alignment="center")
q1.image(code, width=200, alt=f"QR code for {landmarks[pick]}")
with q2:
    st.markdown(f"**{esc(landmarks[pick])}**", unsafe_allow_html=True)
    st.caption(link)
    st.download_button("Download QR (PNG)", code, file_name=f"qr-{pick}.png", mime="image/png", key="dl_qr")
