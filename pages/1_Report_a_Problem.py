"""Student: report a problem. Ticket is created immediately; the reply shows self-help, staff and ETA."""
import streamlit as st

import config
from logic import cache, chat, map_data, mapfile, safety, tickets, workflow
from ui.mapview import campus_map, focus_on, outline
from ui.session import require_role
from ui.theme import category_chip, chip, esc, icon, meta, page_header
from ui.voice import voice_input

AUTO = "Detect from my message"
VOICE_KEY = "rp_voice"
CATEGORY_BY_LABEL = {config.CATEGORY_LABELS[c]: c for c in config.CATEGORIES}


def add_spoken_text() -> None:
    said = getattr(st.session_state.get(VOICE_KEY), "transcript", None)
    if said:
        st.session_state["rp_text"] = f"{st.session_state.get('rp_text', '')} {said}".strip()[:2000]

student = require_role("student")
page_header("Report a problem", "What is going wrong?", "Describe it the way you would tell a friend. We will create a ticket right away.")

landmarks = tickets.landmark_options()
if not landmarks:
    st.error("No campus locations are loaded yet. Please ask an admin to run the setup.")
    st.stop()
by_name = {lm["name"]: lm for lm in landmarks}
by_slug = {lm["slug"]: lm for lm in landmarks}

qr_slug = st.query_params.get("landmark")
if qr_slug in by_slug and st.session_state.get("rp_qr") != qr_slug:
    st.session_state["rp_qr"] = qr_slug
    st.session_state["rp_landmark"] = by_slug[qr_slug]["name"]

pin = st.session_state.get("rp_pin")
if pin and pin["landmark_id"] in by_slug and st.session_state.pop("rp_pin_apply", False):
    st.session_state["rp_landmark"] = by_slug[pin["landmark_id"]]["name"]
st.session_state.setdefault("rp_landmark", AUTO)
if st.session_state["rp_landmark"] not in by_name and st.session_state["rp_landmark"] != AUTO:
    st.session_state["rp_landmark"] = AUTO

left, right = st.columns([3, 2], gap="large")

with left:
    st.markdown(f"##### {icon('map-pin', 18)} Tap the spot on the map", unsafe_allow_html=True)
    pin_lm = mapfile.by_id(pin["landmark_id"]) if pin and pin["landmark_id"] else None
    click = campus_map(
        "rp_map", map_mode="pick", pin=(pin["x"], pin["y"]) if pin else None, highlight=outline(pin_lm),
        focus=st.session_state.get("rp_focus"), height=470,
    )
    if click:
        found = map_data.resolve_pin(click["nx"], click["ny"], click.get("scale", 1.0))
        if found["kind"] == "service":
            st.toast(f"That is the {found['service']['name']} icon. Tap a building or road instead.")
        elif found["landmark_id"]:
            st.session_state["rp_pin"] = {**found, "x": click["nx"], "y": click["ny"]}
            st.session_state["rp_pin_apply"] = True
            st.session_state["rp_focus"] = focus_on(found["landmark"], 2.0)
            st.rerun()
    if pin:
        near = f" (about {pin['distance_m']} m away)" if pin["via"] in ("snap", "nearest") and pin["distance_m"] else ""
        st.success(f"Pin set: **{esc(pin['name'])}**{near}")
        if st.button("Clear pin", key="i_x__clearpin"):
            for k in ("rp_pin", "rp_focus"):
                st.session_state.pop(k, None)
            st.session_state["rp_landmark"] = AUTO
            st.rerun()
    else:
        st.caption("Optional, but it helps staff find the place faster. Drag to move, scroll or pinch to zoom.")

with right:
    text = st.text_area("What is the problem?", height=130, max_chars=2000, key="rp_text",
                        placeholder="e.g. the tap near the water cooler on B block 2nd floor keeps leaking")
    voice_input(VOICE_KEY, add_spoken_text)
    if safety.is_safety_report(text):
        with st.container(border=True):
            st.markdown(f"**{icon('triangle-alert', 16)} If someone is hurt or in danger, contact them now**",
                        unsafe_allow_html=True)
            st.caption("Your report still goes to staff. Do not wait for a reply here.")
            for service_id in safety.CONTACT_SERVICES:
                panel = map_data.service_panel(service_id)
                if panel and panel["contact"]:
                    contact = panel["contact"]
                    st.markdown(f"**{esc(panel['name'])}** " + meta("phone", contact.get("phone", ""))
                                + meta("clock", contact.get("hours", "")), unsafe_allow_html=True)
    read = tickets.read_location(text) if text.strip() else None
    choice = st.selectbox("Where is it?", [AUTO] + list(by_name), key="rp_landmark")
    chosen_slug = by_name[choice]["slug"] if choice != AUTO else (read["landmark"] if read else None)
    kind = st.selectbox("What kind of problem?", [AUTO] + list(CATEGORY_BY_LABEL), key="rp_category")
    category = CATEGORY_BY_LABEL.get(kind)

    ambiguous_pick = None
    if not chosen_slug and not pin and read and read["ambiguous"]:
        ambiguous_pick = st.radio("Which one do you mean?", [a["id"] for a in read["ambiguous"]],
                                  format_func=lambda i: by_slug[i]["name"] if i in by_slug else i, index=None)
        chosen_slug = ambiguous_pick

    final_slug = chosen_slug
    if pin and pin["landmark_id"]:
        if chosen_slug and tickets.pin_conflict(pin["landmark_id"], chosen_slug):
            st.warning("Your pin and your description point to different places.")
            which = st.radio("Which is right?", ["text", "pin"], horizontal=True,
                             format_func=lambda k: f"{by_slug[chosen_slug]['name'] if chosen_slug in by_slug else chosen_slug}"
                             if k == "text" else f"{pin['name']} (my pin)")
            final_slug = chosen_slug if which == "text" else pin["landmark_id"]
        elif not chosen_slug:
            final_slug = pin["landmark_id"]

    shown = by_slug.get(final_slug) if final_slug else None
    floors = (shown["floors"] if shown else []) or []
    guessed_floor = read["floor"] if read and read["floor"] in floors else None
    options = ["Not sure"] + floors
    floor = st.selectbox("Floor", options, index=options.index(guessed_floor) if guessed_floor else 0,
                         key=f"rp_floor_{final_slug}_{guessed_floor}")
    c3, c4 = st.columns(2)
    room = c3.text_input("Room (optional)", max_chars=60, placeholder=(read or {}).get("room") or "e.g. 204")
    nearby = c4.text_input("Near (optional)", max_chars=120, placeholder=(read or {}).get("nearby") or "e.g. the stairs")
    if read and (read["name"] or read["floor"]):
        bits = [read["name"], f"{read['floor']} floor" if read["floor"] else None]
        st.caption("We read: " + " · ".join(b for b in bits if b))
    photo = st.file_uploader("Photo (optional)", type=["jpg", "jpeg", "png", "webp"])

    if st.button("Submit report", type="primary", key="i_send__submit", use_container_width=True):
        if not text.strip():
            st.warning("Please describe the problem first.")
        elif read and read["ambiguous"] and not final_slug:
            st.warning("Please pick which place you mean, or tap it on the map.")
        else:
            use_pin = pin and pin["landmark_id"] == final_slug
            with st.spinner("Creating your ticket..."):
                try:
                    st.session_state["rp_result"] = tickets.submit_report(
                        student, text, final_slug, None if floor == "Not sure" else floor, room, nearby,
                        photo.getvalue() if photo else None, photo.type if photo else None,
                        pin["x"] if use_pin else None, pin["y"] if use_pin else None, category=category,
                    )
                    st.session_state["rp_new"] = True
                    for k in ("rp_pin", "rp_focus"):
                        st.session_state.pop(k, None)
                except Exception:
                    st.error("Something went wrong while saving your report. Please try again.")

res = st.session_state.get("rp_result")
if res:
    if st.session_state.pop("rp_new", False):
        st.toast("Ticket created.", icon=":material/check_circle:")
    st.divider()
    with st.container(border=True):
        st.markdown(f"### Ticket {esc(res['code'])} &nbsp; {chip(res['status'])}", unsafe_allow_html=True)
        st.markdown(f"**{esc(res['summary'])}** &nbsp; {category_chip(res['category'])}", unsafe_allow_html=True)
        loc = res.get("location") or {}
        place = ", ".join(str(v) for v in (loc.get("landmark"), loc.get("floor") and f"{loc['floor']} floor",
                                           loc.get("room") and f"room {loc['room']}") if v)
        if place:
            st.markdown(meta("map-pin", place), unsafe_allow_html=True)
        who = f"Assigned to {res['staff_name']}." if res["staff_name"] else "Waiting for a staff member to be assigned."
        st.markdown(meta("user-check", res["eta_text"], who), unsafe_allow_html=True)
        if res["photo_note"]:
            st.caption(f"Photo: {res['photo_note']}")

    if res.get("out_of_scope"):
        desk = map_data.service_panel("helpdesk")
        with st.container(border=True):
            st.markdown("**This looks like something the helpdesk handles**")
            st.write("Campus Saathi covers plumbing, electricity, cleanliness and internet. For this, please contact the helpdesk.")
            if desk and desk["contact"]:
                st.markdown(meta("phone", desk["contact"].get("phone", "")) + meta("clock", desk["contact"].get("hours", "")),
                            unsafe_allow_html=True)

    reply = res.get("cache")
    if reply:
        with st.container(border=True):
            st.markdown("**We have seen this problem before**")
            st.write(reply["text"])
            if reply["can_reopen"] and st.button("Still broken?", key="i_refresh-cw__reopen"):
                cache.reopen_group(reply["group_id"], student)
                st.session_state["rp_result"]["cache"] = cache.build_reply(reply["group_id"])
                st.rerun()
    if res["self_help"]:
        with st.container(border=True):
            st.markdown("**Something you can try while you wait**")
            st.write(res["self_help"])
            if st.button("This solved it", key="i_circle-check__selfsolved"):
                workflow.mark_self_resolved(res["ticket_id"], student)
                st.session_state.pop("rp_result")
                st.success("Great! We marked your ticket as solved. It stays in My Tickets.")
                st.rerun()
    if res["follow_up_question"]:
        with st.container(border=True):
            st.markdown("**One quick question**")
            st.write(res["follow_up_question"])
            with st.form("rp_answer", clear_on_submit=True):
                answer = st.text_input("Your answer")
                if st.form_submit_button("Send answer", key="i_send__answer"):
                    if answer.strip():
                        chat.send_chat(res["ticket_id"], {"role": "student", "id": student["id"], "name": student["name"]}, answer)
                        st.session_state["rp_result"]["follow_up_question"] = None
                        st.rerun()
    st.caption("Track this ticket any time from My Tickets in the menu.")

st.divider()
with st.expander("Need another way?"):
    desk = map_data.service_panel("helpdesk")
    st.write("If chat is not solving it, contact the facilities helpdesk during working hours.")
    if desk and desk["contact"]:
        st.markdown(meta("phone", desk["contact"].get("phone", "")) + meta("clock", desk["contact"].get("hours", "")),
                    unsafe_allow_html=True)
    st.caption("For an emergency, do not use this app. Follow campus emergency procedures or call local emergency services.")
