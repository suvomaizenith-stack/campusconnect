"""Outage map: live badges on the illustrated campus map, tap a building to see its floors and issues."""
import streamlit as st

from logic import map_data, mapfile, tickets
from ui.mapview import campus_map, focus_on, outline
from ui.session import require_role
from ui.theme import chip, esc

user = require_role("student", "staff")
is_student = user["role"] == "student"
st.title("Outage map")

f1, f2 = st.columns([3, 2])
cat = f1.radio("Category", ["All", "plumbing", "electricity", "cleanliness", "internet"], horizontal=True,
               format_func=lambda c: c.title())
window = f2.radio("Time window", list(map_data.WINDOWS), horizontal=True, index=2)
hours, category = map_data.WINDOWS[window], (None if cat == "All" else cat)

query = st.text_input("Search a place", placeholder="e.g. D block, library, or a number like 7", label_visibility="collapsed")
if query != st.session_state.get("om_query"):
    st.session_state["om_query"] = query
    if query.strip():
        hit = map_data.search(query)
        if hit:
            st.session_state["om_sel"] = {"kind": "landmark", "id": hit["id"]}
            st.session_state["om_focus"] = focus_on(hit, 2.2)
        else:
            st.toast("No place matches that search.")

sel = st.session_state.get("om_sel")
overlay = map_data.overlay(hours, category)
sel_lm = mapfile.by_id(sel["id"]) if sel and sel["kind"] == "landmark" else None

left, right = st.columns([3, 2], gap="large")
with left:
    click = campus_map("om_map", overlay=overlay, mode="view", highlight=outline(sel_lm),
                       focus=st.session_state.get("om_focus"), height=560)
    if click:
        if click.get("badge"):
            st.session_state["om_sel"] = {"kind": "landmark", "id": click["badge"]}
        else:
            scale = click.get("scale", 1.0)
            dots = overlay["issues"] if scale >= 1.6 else []
            found = map_data.resolve_pin(click["nx"], click["ny"], scale, dots)
            if found["kind"] == "issue":
                st.session_state["om_sel"] = {"kind": "issue", "id": found["issue_id"]}
            elif found["kind"] == "service":
                st.session_state["om_sel"] = {"kind": "service", "id": found["service"]["id"]}
            elif found["landmark_id"]:
                st.session_state["om_sel"] = {"kind": "landmark", "id": found["landmark_id"]}
        st.rerun()
    if not overlay["badges"]:
        st.info("No active problems in this window. 🎉")

    with st.expander("Index"):
        for e in map_data.index_with_counts(hours, category):
            num = f"{e['number']}. " if e["number"] else "• "
            badge = f" — **{e['count']} open**" if e["count"] else ""
            st.markdown(f"{num}{esc(e['name'])}{badge}", unsafe_allow_html=True)


def me_too_button(group_id: int, already: bool, resolved: bool, key: str) -> None:
    if not is_student or resolved:
        return
    if already:
        st.button("✅ You reported this", key=key, disabled=True)
    elif st.button("I face this too", key=key, type="primary"):
        student = {"id": user["id"], "name": user["name"], "roll": user["roll"]}
        if tickets.say_me_too(student, group_id):
            st.toast("Thanks! Your report was added.")
        st.rerun()


with right:
    if not sel:
        st.caption("Tap a numbered building, a road, or a badge to see what is happening there.")
    elif sel["kind"] == "service":
        p = map_data.service_panel(sel["id"])
        with st.container(border=True):
            st.markdown(f"### {esc(p['name'])}" if p else "### Service", unsafe_allow_html=True)
            c = p and p["contact"]
            if c:
                st.write(f"☎️ {c['phone']}  \n🕘 {c['hours']}")
                if c.get("note"):
                    st.caption(c["note"])
            else:
                st.caption("No contact details are listed yet.")
    elif sel["kind"] == "issue":
        p = map_data.group_panel(sel["id"], user["id"] if is_student else None)
        if p is None:
            st.warning("That problem is no longer on the map.")
        else:
            with st.container(border=True):
                st.markdown(f"### {esc(p['title'])}", unsafe_allow_html=True)
                st.markdown(f"{chip('resolved' if p['resolved'] else p['status'])} &nbsp; {chip(p['level'])}", unsafe_allow_html=True)
                st.write(f"📍 {p['location']} · {p['category'].title()}")
                st.write(f"👥 {p['report_count']} report{'s' if p['report_count'] != 1 else ''} · first reported "
                         f"{p['first_reported_ago']} ({p['first_reported']})")
                st.write(p["eta_text"])
                me_too_button(sel["id"], p["already_reported"], p["resolved"], f"mt_{sel['id']}")
    else:
        p = map_data.landmark_panel(sel["id"], hours, category, user["id"] if is_student else None)
        if p is None:
            st.warning("That place is not on the map.")
        else:
            with st.container(border=True):
                head = f"{p['number']}. " if p["number"] else ""
                st.markdown(f"### {head}{esc(p['name'])}", unsafe_allow_html=True)
                st.caption(f"{p['open']} open · {p['resolved']} recently resolved")
                if p["open"] == 0 and p["resolved"] == 0:
                    st.success("No problems reported here.")
                for fl in p["floors"]:
                    if not fl["issues"] and len(p["floors"]) > 1:
                        continue
                    if len(p["floors"]) > 1 or fl["issues"]:
                        st.markdown(f"**{esc(fl['floor'])} floor** · {fl['count']} open", unsafe_allow_html=True)
                    for i in fl["issues"]:
                        with st.container(border=True):
                            st.markdown(f"**{esc(i['title'])}**  \n{chip('resolved' if i['resolved'] else i['level'])} "
                                        f"{i['category'].title()} · {i['count']} report{'s' if i['count'] != 1 else ''}",
                                        unsafe_allow_html=True)
                            me_too_button(i["group_id"], i["already_reported"], i["resolved"], f"mt_{i['group_id']}")
