FOR SUVOM
Feature: Staff dashboard (ticket list, duplicate review, assignment, status history, quick replies)
Branch: samriddhi/staff-ui
File to edit: pages/2_Staff_Dashboard.py
Prompt:

Edit only pages/2_Staff_Dashboard.py. Build the staff dashboard in Streamlit using the existing SQLite helpers in db/. If a helper you need does not exist, add a short one in db/ and tell me its name. Keep code short, with comments. Do not hardcode API keys.

Context: CampusConnect, one campus, four categories: Plumbing, Electricity, Cleanliness, Internet connectivity. Departments: Plumbing Team, Electrical Team, Housekeeping Team, IT Network Team. Use the exact status names from docs/ticket_rules.md.

What the user sees:
1. Login form (email, password). Wrong details show "Invalid email or password". After login keep staff id, name, role (admin or staff) and department in st.session_state. Add a Log out button in the sidebar. Admin sees all departments; staff sees only their own department.
2. Header with name, department and an Online/Offline toggle. Going online runs the existing assignment function for waiting tickets in that department. Below it show metric cards: New, Needs info, In progress, Resolved today, Overdue.
3. A banner if any location has 3 or more reports of the same category in 7 days (yellow) or 5 or more (red): "Recurring issue: [location] has [n] [category] reports in 7 days".
4. Ticket list with filters (status, category, urgency, department, "Possible duplicates only", search by ticket number or location), sorted by urgency then oldest first. Each row shows ticket number, urgency badge, category, location, AI summary, status, assigned staff, age, and badges Possible duplicate, Recurring, Overdue. Overdue means the target in the routing guide has passed (Plumbing 2h/1d, Electricity 1h/1d, Cleanliness 2h/same day, Internet 30m/1d for first response / resolution).
5. Selecting a ticket opens a detail panel with:
   - Original complaint, language, photo (or "No photo provided"), and location.
   - AI analysis: extracted issue, summary, suggested category and department, urgency, confidence.
   - Override dropdowns for category, department and urgency. Save who changed it and when to the history.
   - Assign: dropdown of staff in the department showing their open ticket counts, plus "Assign to me" and "Auto-assign". Block it with "Already assigned" if someone else took it first.
   - Status dropdown with a note. Resolved requires a one-line resolution note. Every change is added to the progress history.
   - Progress history timeline (time, event, who did it). Mark internal notes as staff-only. The student page reads the same history but hides internal notes.
   - Reply to student: text box plus a quick-reply dropdown loaded from data/quick_replies.json filtered by the ticket's category (and "All"). A language toggle (English or Hindi) picks the "en" or "hi" text. Replace {student_name}, {ticket_id}, {department}, {staff_name}, {eta} before showing it. Staff can edit before sending. Empty replies show "Type a reply first."
6. Possible duplicate review: if a ticket is flagged, show a side-by-side card with the new ticket and the existing ticket (text, photo, location, time) and the reasons for the match. Buttons: "Confirm duplicate" (link to the original, mark this ticket "Duplicate of #id", keep its own ticket number, notify the student) and "Not a duplicate". Never merge automatically.
7. A simple Insights tab: bar chart of tickets by category this week, table of top 5 locations by report count, and average resolution time by department.

Functions (inputs and outputs):
- login(email, password) -> staff dict or None.
- set_online(staff_id, online) -> None. Runs assignment for waiting tickets when going online.
- list_tickets(filters, staff) -> list of tickets sorted by urgency then oldest.
- assign_ticket(ticket_id, staff_id, by_staff_id) -> bool. False if already assigned.
- update_status(ticket_id, status, note, by_staff_id) -> None. Adds a history row.
- override_fields(ticket_id, category, department, urgency, by_staff_id) -> None. Adds a history row.
- resolve_duplicate(ticket_id, original_id, is_duplicate, by_staff_id) -> None. Adds history rows to both tickets.
- send_reply(ticket_id, staff_id, text, internal: bool) -> None.
- load_quick_replies(category, lang) -> list of {label, text}.
- recurring_locations() -> list of {location, category, count}.

Edge cases:
- Offline staff can view but cannot take tickets ("You are offline. Go online to receive tickets.").
- Two staff taking the same ticket: second one sees "Already assigned" and the list refreshes.
- Moving a status backwards requires a note and is logged.
- Empty lists show friendly messages such as "No tickets match your filters."
- If not logged in, show only the login form.

Do not change any other file.

--------------------------------------------------
HOW SUVOM CAN USE MY OTHER FILES (no extra work)
- data/kb.json: give it to Gemini as context for self-help answers, category, department, urgency, and the follow-up questions in ask_if_missing. keywords_en and keywords_hi help with Hindi complaints.
- docs/routing_guide.md: paste it into the Gemini system prompt as the routing guide. It has the categories, departments, urgency, required fields, classification rules and duplicate rules.
- data/quick_replies.json: loaded by the dashboard as described above.
