# Staff Dashboard Spec (pages/2_Staff_Dashboard.py)

**Goal:** Let staff see every ticket clearly, review possible duplicates, assign work, update status, and message students, all in a few clicks, with a full progress history.

## 1. Access
- Login (email and password). Wrong details: "Invalid email or password".
- After login keep staff id, name, role and department in session state. Log out button in the sidebar.
- Roles: **Admin** sees all departments and can assign to anyone. **Staff** sees their own department.

## 2. Header and live summary
- Staff name, department and an Online/Offline toggle (going online assigns waiting tickets in their department).
- Metric cards: New, Needs info, In progress, Resolved today, Overdue.
- Alert banner: "Recurring issue: [location] has [n] [category] reports in 7 days" (3 = yellow, 5 = red).

## 3. Ticket list (main view)
- Filters: status, category, urgency, department, "Possible duplicates only", search by ticket number or location.
- Sort: urgency first, then oldest first.
- Each row shows: ticket number, urgency badge, category, location, one-line AI summary, status, assigned to, age, and badges **Possible duplicate**, **Recurring**, **Overdue**.
- Overdue badge when the first response or resolution target in `docs/routing_guide.md` has passed.

## 4. Ticket detail panel
- **Complaint:** original text, language (English or Hindi), student's photo, and location.
- **AI analysis:** extracted issue, summary, suggested category and department, urgency, confidence, and any missing details Gemini asked about.
- **Override:** staff can change category, department or urgency (store who changed it and when).
- **Assign:** dropdown of staff in the department with their open ticket counts, plus "Assign to me" and "Auto-assign".
- **Update status:** dropdown with a short staff note. Moving to Resolved asks for a one-line resolution note.
- **Progress history:** timeline of every event with time and who did it, for example Submitted, AI categorised, Info requested, Student replied, Duplicate flagged, Assigned, In progress, Resolved. The same history is what the student sees (internal notes stay hidden).
- **Reply to student:** text box, with a quick-reply dropdown from `data/quick_replies.json` filtered by category. Placeholders are filled automatically and a language toggle (English or Hindi) switches the template text. Staff can edit before sending.
- **Internal note:** visible to staff only.

## 5. Duplicate review
- Open from the badge or the "Possible duplicates" filter.
- Side-by-side cards: new ticket and existing ticket (text, photo, location, time) with reasons for the match (same category, same location, similar words).
- Buttons: **Confirm duplicate** (link to the original, close the extra ticket as "Duplicate of #id", notify the student) and **Not a duplicate**.
- Nothing is merged without a staff click.

## 6. Insights tab (extension, only if time permits)
- Bar chart: tickets by category this week.
- Table: top 5 locations by report count and the most frequent issue there.
- Average resolution time by department.

## 7. Edge cases
- Staff offline: can view, but cannot take new tickets ("You are offline. Go online to receive tickets.").
- Two staff open the same ticket: the second to assign sees "Already assigned" and the list refreshes.
- Empty reply: "Type a reply first."
- Status moved backwards (for example Resolved to In progress): allowed with a required note, logged in history.
- No tickets: friendly empty state, never a blank page.
- Photo missing or fails to load: show "No photo provided".
- Not logged in: show only the login form.

## 8. Test checklist
1. Log in as staff and as admin and compare what each can see.
2. Submit an incomplete complaint and see it appear as "Needs info".
3. Open a possible duplicate and confirm it, then check both students see updates.
4. Assign a ticket, move it through In progress to Resolved, and check the history timeline.
5. Send a quick reply in English, then in Hindi.
6. Create 3 reports at one location and check the Recurring badge.
7. Go offline and confirm assigning is blocked.
