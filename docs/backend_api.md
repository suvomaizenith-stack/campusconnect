# CampusConnect backend API

Pages call only `ui/`, `logic/`, `ai/` and `db/`. Pages never contain SQL or AI calls. Timestamps are stored in UTC and shown in IST. Student identity dict: `{id, name, roll}`. Staff identity dict: `{id, name, department, username}`. Chat viewer dict: `{role, id, name}`.

"Pages" column: R = 1_Report_a_Problem, T = 2_My_Tickets, D = 3_Staff_Dashboard, M = 4_Outage_Map, H = 0_Home, A = app.py.

## logic/ (called by pages)

| Module | Function | Returns | Pages |
|---|---|---|---|
| auth | `signup_student(name, roll, pin, pin_again)` | student dict; raises `AuthError` | H |
| auth | `login_student(roll, pin)` | student dict; raises `AuthError` (attempt limit and lockout) | H |
| auth | `login_staff(username, access_key)` | staff dict; raises `AuthError` (lockout) | H |
| auth | `hash_password`, `verify_password`, `generate_access_key`, `clean_student` | helpers | scripts/create_staff.py |
| setup | `bootstrap()` | None; creates tables and loads landmarks | A |
| tickets | `landmark_options()` | list of landmarks `{id, name, lat, lng, floors}` | R, M |
| tickets | `submit_report(student, text, landmark_name, floor, room, nearby, photo, photo_mime, lat, lng)` | `{ticket_id, code, category, summary, status, staff_name, eta_text, self_help, follow_up_question, missing_fields, cache, mode, photo_note}`; never blocked by AI failure | R |
| tickets | `say_me_too(student, group_id)` | True if added, False if already reported | M |
| tickets | `validate_category(category)` | the category; raises `ValueError` for anything but the four allowed | tests |
| chat | `get_thread(ticket_id, viewer)` | messages oldest first; `PermissionError` for anyone but the ticket's student or assigned staff | T, D |
| chat | `send_chat(ticket_id, viewer, body)` | True if a student's answer was merged into an incomplete ticket | R, T, D |
| cache | `lookup(analysis)` | matching group with `similarity`, or None | (used by tickets) |
| cache | `build_reply(group_id)` | live reply `{kind, text, report_count, status, staff_name, eta_text, latest_note, self_help, can_reopen}` | (used by tickets), R |
| cache | `reopen_group(group_id, student)` | None; reopens a recently resolved group | R |
| workflow | `set_status(ticket_id, status, note, staff)` | None; writes history; primary ticket status propagates to linked tickets | D |
| workflow | `mark_self_resolved(ticket_id, student)` | None; ticket is kept | R, T |
| workflow | `confirm_duplicate(ticket_id, staff)` / `separate_duplicate(ticket_id, staff)` | None | D |
| assignment | `go_online(staff)` | number of waiting tickets assigned (priority first, then oldest) | D |
| assignment | `go_offline(staff)` | None | D, logout |
| assignment | `reassign(ticket_id, staff_id, by)` | None; writes history | D |
| assignment | `choose_staff(online, open_counts)` | fewest open tickets, lowest id breaks ties (pure) | tests |
| alerts | `evaluate_group(group_id)` | `{level, count, alert_id}`; raises alerts at 3 (hotspot) and 5 (critical) reports or a safety risk | (used by tickets, workflow) |
| priority | `level_for(report_count, max_severity)`, `score(category, severity, report_count)`, `tier(score, level)` | pure helpers | (internal), M |
| map_data | `map_markers(hours, category)` | markers `{id, lat, lng, title, level, color, count, pulse, radius, resolved}` | M |
| map_data | `hotspot_circles(markers)` | circles `{lat, lng, radius_m, color}` | M |
| map_data | `group_panel(group_id, student_id)` | click-panel dict or None | M |
| map_data | `resolve_pin(lat, lng)` | nearest landmark `{landmark, landmark_id, floors, distance_m}` | R |
| views | `student_tickets(student_id)` | tickets with `eta_text`, `status_label` | T |
| views | `ticket_timeline(ticket_id)` | history with IST `when` | T, D |
| views | `staff_queue(staff)` | `{tier: [tickets]}` | D |
| views | `ticket_detail(ticket_id)` | `{ticket, timeline, group, linked, photo}` | D |
| views | `duplicate_reviews(staff)` | `[{ticket, primary, group}]` | D |
| views | `staff_metrics(staff)` | `{open, in_progress, waiting, resolved_today, avg_hours, per_day}` | D |
| views | `urgency_board(staff)`, `open_alerts(department)`, `acknowledge_alert(alert_id, staff)` | alert and urgency data | A, D |
| views | `staff_directory(department)`, `is_online(staff_id)`, `quick_replies(category)`, `status_label(ticket)` | helpers | D, T |
| timeutil | `fmt_ist`, `time_ago`, `eta_text`, `hours_from_now`, `now_utc`, `to_ist` | formatting helpers | logic only |
| photos | `shrink_photo(data)` | `(bytes, mime)` | (used by tickets) |

## ai/

| Module | Function | Returns |
|---|---|---|
| llm | `chat(messages, system, json_mode)` | text. Chain Gemini, Groq, NVIDIA; retries; breaker (3 failures, skip 60 s); raises `LLMError` when all fail |
| llm | `chat_json(messages, system, validate)` | validated dict, one repair attempt |
| llm | `get_ai_status()` | `"normal"` or `"degraded"` (shown on the staff dashboard) |
| triage | `analyse(text, location, photo_note)` | `{category, severity, summary, missing_fields, follow_up_question, needs_review, mode}`; never raises, falls back to rules |
| triage | `merge_answer(ticket, answer)` | updated description, room, nearby, summary, severity |
| vision | `describe_photo(data, mime)` | `(text, analysed)`; Gemini only, "not analysed" on failure |
| kb | `self_help(category, text)` | self-help text from `data/kb.json` or None |
| keywords | `issue_tokens`, `jaccard`, `category_scores`, `routing_guide` | keyword helpers |

## db/ (SQL lives here only)

| Module | Functions |
|---|---|
| db | `get_conn`, `init_db`, `migrate`, `upsert_landmarks`, `list_landmarks`, `get_landmark_by_name`, `ping`, `close_pool` |
| users | `create_student`, `get_student_by_roll`, `get_staff_by_username`, `get_staff`, `list_staff`, `upsert_staff`, `record_login_failure`, `reset_login_failures`, `is_locked`, `set_staff_online` |
| tickets | `create_ticket`, `update_ticket`, `get_ticket`, `get_ticket_photo`, `list_tickets`, `waiting_tickets`, `open_ticket_counts`, `online_staff`, `add_history`, `add_status`, `assign_ticket`, `get_history`, `add_message`, `get_messages`, `add_system_message`, `department_metrics` |
| groups | `create_group`, `get_group`, `update_group`, `candidate_groups`, `add_report`, `remove_ticket_report`, `student_reported`, `count_reports`, `max_severity`, `groups_for_map`, `create_alert`, `list_alerts`, `acknowledge_alert` |

## ui/

`session`: `current_user`, `login_student`, `login_staff`, `logout` (sets staff offline), `require_role`. `theme`: `inject_css`, `esc`, `chip`, `card`, `metric_card`, `banner`, `timeline`. `mapview`: `outage_map`, `pin_picker`, `group_id_from_tooltip`.

## Not built (TODO only)

Voice notes, Telegram intake, staff-to-staff channels, drafts, learned ETA.
