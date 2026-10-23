"""Staff dashboard: metrics, recurring banners, filterable ticket list, detail panel, duplicate review, alerts, insights."""
from datetime import timedelta

import streamlit as st

import config
from logic import assignment, chat, priority, views, workflow
from logic import settings as settings_logic
from logic.timeutil import from_ist, now_utc, to_ist
from ui.session import require_role
from ui.theme import banner, chip, empty_state, esc, meta, page_header, section_head, stat_row, timeline

staff = require_role("staff")
is_admin = bool(staff.get("is_admin"))
viewer = {"role": "staff", "id": staff["id"], "name": staff["name"]}
by = f"{staff['name']} (staff)"
STATUS_FILTERS = {"All open": None, "New": "new", "Needs info": "needs_info", "In progress": "in_progress",
                  "Resolved": "resolved", "Overdue": "overdue"}
URGENCY_FILTERS = {"Any urgency": None} | {config.URGENCY_LABELS[t]: t for t in priority.TIER_ORDER}


def flash(msg: str, error: bool = False) -> None:
    st.session_state["flash"] = (msg, error)


head, toggle_col = st.columns([4, 1])
with head:
    page_header("Staff dashboard", "All departments" if is_admin else f"{staff['department'].title()} desk",
                "Every ticket in your queue, with the tools to assign, update and close them.")
online_now = views.is_online(staff["id"])
with toggle_col:
    online = st.toggle("Online", value=online_now, key="online_toggle")
if online != online_now:
    if online:
        n = assignment.go_online(staff)
        st.toast(f"You are online. {n} waiting ticket{'s' if n != 1 else ''} assigned to you." if n else "You are online.")
    else:
        assignment.go_offline(staff)
        st.toast("You are offline. New tickets will not be assigned to you.")
if not online:
    st.info("You are offline. Go online to receive tickets.")
if "flash" in st.session_state:
    msg, is_err = st.session_state.pop("flash")
    (st.error if is_err else st.success)(msg)

if settings_logic.load()["recurring_banners"]:
    for r in views.recurring(staff):
        banner(r["message"], "critical" if r["level"] == "red" else "hotspot")

m = views.staff_metrics(staff)
stat_row([
    {"label": "New", "value": m["new"], "icon": "inbox", "featured": True},
    {"label": "Needs info", "value": m["needs_info"], "icon": "message-circle", "color": "amber"},
    {"label": "In progress", "value": m["in_progress"], "icon": "wrench", "color": "violet"},
    {"label": "Resolved today", "value": m["resolved_today"], "icon": "circle-check", "color": "green"},
    {"label": "Overdue", "value": m["overdue"], "icon": "timer", "color": "red"},
])

reviews = views.duplicate_reviews(staff)
tab_tickets, tab_dups, tab_alerts, tab_insights = st.tabs(
    ["Tickets", f"Duplicate review ({len(reviews)})", "Alerts", "Insights"])


@st.fragment(run_every=5)
def staff_chat(ticket: dict) -> None:
    """Live chat with EN/HI quick replies. Only the assigned staff member can write."""
    tid = ticket["id"]
    try:
        thread = chat.get_thread(tid, viewer)
    except PermissionError:
        st.caption("Assign this ticket to yourself to chat with the student.")
        return
    for msg in thread:
        with st.chat_message("user" if msg["sender_role"] == "student" else "assistant"):
            st.markdown(f"**{esc(msg['sender_name'])}**", unsafe_allow_html=True)
            st.text(msg["body"])

    replies = views.quick_replies(ticket["category"])
    box = f"sc_{tid}"
    if replies:
        by_label = {r["label"]: r for r in replies}
        lang_key, pick_key = f"qrlang_{tid}", f"qr_{tid}"

        def fill() -> None:
            r = by_label.get(st.session_state.get(pick_key))
            if r:
                lang = "hi" if st.session_state.get(lang_key) == "हिन्दी" else "en"
                st.session_state[box] = views.fill_reply(views.reply_text(r, lang), ticket, staff, lang)

        q1, q2 = st.columns([3, 1])
        q1.selectbox("Quick reply", [""] + list(by_label), key=pick_key, on_change=fill)
        q2.radio("Language", ["English", "हिन्दी"], key=lang_key, horizontal=False, on_change=fill,
                 index=1 if ticket.get("language") == "hi" else 0)
    err = f"scerr_{tid}"

    def send() -> None:
        body = st.session_state.get(box, "")
        if not body.strip():
            st.session_state[err] = True
            return
        chat.send_chat(tid, viewer, body)
        st.session_state[box] = ""
        st.session_state.pop(err, None)

    st.text_area("Message", key=box, height=90)
    st.button("Send", key=f"i_send__send{tid}", on_click=send)
    if st.session_state.pop(err, False):
        st.warning("Type a reply first.")


def detail_panel(ticket_id: int) -> None:
    d = views.ticket_detail(ticket_id)
    if d is None:
        st.warning("That ticket no longer exists.")
        return
    t = d["ticket"]
    with st.container(border=True):
        st.markdown(f"### {esc(t['code'])} &nbsp; {chip(t['status'], t['status_label'])} &nbsp; "
                    f"{chip(t['tier'], t['urgency_label'])}", unsafe_allow_html=True)
        if t["overdue"]:
            st.error(t["overdue"])
        st.write(f"**{t['title']}**")
        st.write(t["description"])
        where = (t["landmark"] or "Campus") + (f", {t['floor']} floor" if t["floor"] else "")
        if t["room"]:
            where += f", room {t['room']}"
        st.caption(f"{where} · {t['student_name']} ({t['student_roll']}) · reported {t['age']}"
                   + (f" · near {t['nearby']}" if t["nearby"] else ""))
        if not t["info_complete"]:
            st.info(f"Waiting for the student's answer: {t['follow_up_question']}")
        if d["group"] and d["group"]["report_count"] > 1:
            st.markdown(meta("users", f"{d['group']['report_count']} students reported this problem."), unsafe_allow_html=True)
        if d["photo"]:
            st.image(d["photo"][0], caption=t["photo_note"] or "Photo from the student")
        st.write(f"Assigned to: **{t['staff_name'] or 'nobody yet'}** · {t['eta_text']}")

        with st.expander("AI analysis", expanded=bool(t["needs_review"])):
            conf = t.get("ai_confidence")
            a1, a2, a3 = st.columns(3)
            a1.metric("Confidence", f"{round(conf * 100)}%" if conf is not None else "n/a")
            a2.metric("Language", "Hindi" if t.get("language") == "hi" else "English")
            a3.metric("Analysed by", "AI" if t.get("ai_mode") == "ai" else "Rules")
            if t["needs_review"]:
                st.warning("The AI was unsure about the category. Please check it.")
            o1, o2 = st.columns(2)
            cats = list(config.CATEGORIES)
            new_cat = o1.selectbox("Category / department", cats, index=cats.index(t["category"]),
                                   format_func=lambda c: config.CATEGORY_LABELS[c], key=f"ocat_{ticket_id}")
            tiers = list(priority.TIER_ORDER)
            new_tier = o2.selectbox("Urgency", tiers, index=tiers.index(t["tier"]),
                                    format_func=lambda x: config.URGENCY_LABELS[x], key=f"otier_{ticket_id}")
            if st.button("Apply changes", key=f"i_check__ovr{ticket_id}"):
                try:
                    workflow.override_category(ticket_id, new_cat, staff)
                    workflow.override_urgency(ticket_id, new_tier, staff)
                    flash("Changes saved and logged.")
                except ValueError as e:
                    flash(str(e), True)
                st.rerun()

        b1, b2 = st.columns(2)
        if b1.button("Assign to me", key=f"i_user-check__take{ticket_id}", disabled=t["assigned_to"] == staff["id"]):
            err = assignment.assign_to_me(t, staff)
            flash(err or "Assigned to you.", bool(err))
            st.rerun()
        if b2.button("Auto-assign", key=f"i_sparkles__auto{ticket_id}"):
            err = assignment.auto_assign(t, staff)
            flash(err or "Assigned automatically.", bool(err))
            st.rerun()
        team = {s["name"]: s["id"] for s in views.staff_directory(t["category"])}
        if team:
            with st.form(f"assign_{ticket_id}"):
                who = st.selectbox("Assign / reassign to", list(team),
                                   index=list(team.values()).index(t["assigned_to"]) if t["assigned_to"] in team.values() else 0)
                if st.form_submit_button("Assign", key=f"i_user-check__assign{ticket_id}"):
                    err = assignment.reassign(t, team[who], by)
                    flash(err or f"Assigned to {who}.", bool(err))
                    st.rerun()

        with st.form(f"status_{ticket_id}"):
            options = workflow.STAFF_STATUSES
            status = st.selectbox("Update status", options, index=options.index(t["status"]) if t["status"] in options else 0,
                                  format_func=lambda s: s.replace("_", " ").title())
            note = st.text_input("Note (the student sees it; required to resolve or move backwards)", max_chars=300)
            if st.form_submit_button("Save update", type="primary", key=f"i_check__status{ticket_id}"):
                try:
                    workflow.set_status(ticket_id, status, note, staff)
                    flash("Status updated.")
                except ValueError as e:
                    flash(str(e), True)
                st.rerun()
        with st.form(f"eta_{ticket_id}"):
            ist_now = to_ist(now_utc())
            seed = to_ist(t["eta_at"]) if t["eta_at"] else ist_now + timedelta(hours=2)
            e1, e2 = st.columns(2)
            eta_day = e1.date_input("Expected by (IST date)", value=max(seed.date(), ist_now.date()),
                                    min_value=ist_now.date())
            eta_clock = e2.time_input("Expected by (IST time)", value=seed.time().replace(second=0, microsecond=0),
                                      step=900)
            if st.form_submit_button("Share expected time", key=f"i_clock__eta{ticket_id}"):
                try:
                    workflow.set_eta(ticket_id, from_ist(eta_day, eta_clock), staff)
                    flash("Expected time shared with the student.")
                except ValueError as e:
                    flash(str(e), True)
                st.rerun()
        with st.form(f"inote_{ticket_id}", clear_on_submit=True):
            inote = st.text_input("Internal note (staff only)", max_chars=300)
            if st.form_submit_button("Add internal note", key=f"i_sticky-note__inote{ticket_id}"):
                try:
                    workflow.add_internal_note(ticket_id, inote, staff)
                    flash("Internal note added.")
                except ValueError as e:
                    flash(str(e), True)
                st.rerun()

        st.markdown("**Progress**")
        timeline([{"label": h["status"].replace("_", " ").title(), "internal": bool(h["internal"]), "detail": h["note"],
                   "when": f"{h['when']} · {h['changed_by'] or ''}"} for h in d["timeline"]])
        st.markdown("**Chat**")
        staff_chat(t)


with tab_tickets:
    f = st.columns([2, 2, 2, 3, 1.4])
    status_f = STATUS_FILTERS[f[0].selectbox("Status", list(STATUS_FILTERS))]
    urgency_f = URGENCY_FILTERS[f[1].selectbox("Urgency", list(URGENCY_FILTERS))]
    cat_f = None
    if is_admin:
        cat_name = f[2].selectbox("Department", ["All"] + [config.CATEGORY_LABELS[c] for c in config.CATEGORIES])
        cat_f = next((c for c in config.CATEGORIES if config.CATEGORY_LABELS[c] == cat_name), None)
    search = f[3].text_input("Search", placeholder="Ticket id, title or student")
    mine = f[4].toggle("Mine", help="Only tickets assigned to me")
    rows = views.staff_tickets(staff, status_f, urgency_f, cat_f, search, mine)

    left, right = st.columns([2, 3], gap="large")
    with left:
        st.download_button("Download CSV", views.tickets_csv(rows), file_name="campus_saathi_tickets.csv",
                           mime="text/csv", key="dl_tickets")
        if not rows:
            empty_state("Nothing matches these filters", "Try a different status or clear the search.", "party-popper")
        for t in rows:
            with st.container(border=True):
                st.markdown(f"{chip(t['tier'], t['urgency_label'])} &nbsp; **{esc(t['code'])}** {esc(t['title'])}",
                            unsafe_allow_html=True)
                bits = [t["status_label"], t["landmark"] or "Campus", t["age"], t["staff_name"] or "unassigned"]
                if not t["info_complete"]:
                    bits.append("needs info")
                if t["dup_review"] == "pending":
                    bits.append("dup review")
                st.caption(" · ".join(bits))
                if t["overdue"]:
                    st.markdown(f":red[{t['overdue']}]")
                if st.button("Open", key=f"i_arrow-right__open{t['id']}"):
                    st.session_state["sel_ticket"] = t["id"]
    with right:
        sel = st.session_state.get("sel_ticket")
        if sel:
            detail_panel(sel)
        else:
            st.caption("Pick a ticket from the list to see details.")

with tab_dups:
    if not reviews:
        empty_state("No possible duplicates to review", "New reports that look like existing ones will appear here.", "git-merge")
    for r in reviews:
        t, p = r["ticket"], r["primary"]
        with st.container(border=True):
            st.markdown("**Possible duplicate: are these the same problem?**")
            c1, c2 = st.columns(2)
            for col, tk, title in ((c1, t, "New ticket"), (c2, p, "Existing ticket")):
                with col:
                    st.markdown(f"**{title} · {esc(tk['code'])}**", unsafe_allow_html=True)
                    st.write(tk["title"])
                    st.caption(f"{tk['landmark'] or 'Campus'}" + (f", {tk['floor']} floor" if tk["floor"] else "")
                               + f" · {tk['student_name']}")
            a, b, _ = st.columns([1, 1, 3])
            if a.button("Confirm duplicate", key=f"i_git-merge__cf{t['id']}", type="primary"):
                workflow.confirm_duplicate(t["id"], staff)
                flash(f"{t['code']} marked as a duplicate of {p['code']}. The student was told.")
                st.rerun()
            if b.button("Not a duplicate", key=f"i_undo-2__sp{t['id']}"):
                workflow.separate_duplicate(t["id"], staff)
                flash(f"{t['code']} is now its own issue.")
                st.rerun()

with tab_alerts:
    alerts = views.open_alerts(None if is_admin else staff["department"])
    if not alerts:
        empty_state("No open alerts", "Hotspots and critical issues will show up here.", "bell")
    for a in alerts:
        banner(f"{a['message']} ({a['age']})", "critical" if a["level"] == "critical" else "hotspot")
        if st.button("Acknowledge", key=f"i_check__ack{a['id']}"):
            views.acknowledge_alert(a["id"], staff)
            st.rerun()
    section_head("Team", "Who is online")
    for s in views.staff_directory(None if is_admin else staff["department"]):
        st.markdown(f"{chip('confirmed', 'Online') if s['is_online'] else chip('later', 'Offline')} &nbsp; {esc(s['name'])} · "
                    f"{esc(config.CATEGORY_LABELS.get(s['department'], s['department']))}", unsafe_allow_html=True)

with tab_insights:
    ins = views.insights(staff)
    st.markdown("**Tickets by category, last 7 days**")
    if ins["by_category"]:
        st.bar_chart({config.CATEGORY_LABELS[r["category"]]: r["count"] for r in ins["by_category"]})
    else:
        st.caption("No tickets yet this week.")
    i1, i2 = st.columns(2)
    with i1:
        st.markdown("**Top 5 locations**")
        for r in ins["top_locations"] or []:
            st.write(f"{r['landmark']}: {r['count']} tickets, mostly {config.CATEGORY_LABELS.get(r['top_category'], r['top_category']).lower()}")
        if not ins["top_locations"]:
            st.caption("Nothing yet.")
    with i2:
        st.markdown("**Average resolution time**")
        for r in ins["avg_resolution"] or []:
            st.write(f"{config.CATEGORY_LABELS[r['category']]}: {r['hours']} h ({r['resolved']} resolved)")
        if not ins["avg_resolution"]:
            st.caption("No resolved tickets yet.")
