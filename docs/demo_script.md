# CampusConnect Demo Script (4 minutes)

**Presenter:** Samriddhi (talks). **Driver:** Suvom (clicks and types). **Backup:** Arsh or Deepanshi (second device, ready to show the student page or a spare staff login).

## Before the demo (do 10 minutes earlier)
- App running, browser zoom 125%, notifications off, Wi-Fi checked, hotspot ready as backup.
- Test photo saved on the laptop: leaking tap at the "Block B, 2nd floor washroom".
- Seed data loaded: one open plumbing ticket at the same location (this will become the duplicate), plus 2 other tickets elsewhere so the dashboard looks alive.
- Two staff accounts ready: a Plumbing Team staff member and an admin.
- Hindi sample copied: "बी ब्लॉक के दूसरे फ्लोर वॉशरूम में नल से पानी टपक रहा है".

## Flow (matches the required demonstration)

**0:00 - 0:25 Hook**
"Today a broken tap gets reported on WhatsApp, to a warden, or not at all. Students never know what happened, and staff have to work out what the issue is and who should fix it. CampusConnect turns a messy complaint into a clear ticket, assigns it to the right team, and shows the student every step."

**0:25 - 1:10 Step 1: incomplete complaint**
Student types: "Water is leaking, please fix quickly."
- Gemini replies: "Sorry about that. Which building, floor and room or washroom is this in? A photo would help too."
- Say: "The AI doesn't guess. It asks only for what is missing."

**1:10 - 1:50 Step 2: supply missing details**
Student answers: "Block B, 2nd floor, boys' washroom" and uploads the photo.
- Ticket card appears: ticket number, issue summary, category **Plumbing**, department **Plumbing Team**, urgency, and the photo analysis ("Gemini confirms a leaking tap from the photo").
- Say: "Gemini read both the text and the photo, extracted the issue, and used our routing guide to pick the category and department."

**1:50 - 2:30 Step 3: duplicate review (staff side)**
Switch to the staff dashboard. The new ticket has a **Possible duplicate** badge.
- Open the side-by-side card. Point out the reasons: same category, same location, similar words.
- Click **Confirm duplicate**. The student keeps their own ticket number but is linked to the original.
- Say: "The AI only flags. The staff member makes the final decision, so there are no wrong auto-merges."

**2:30 - 3:15 Step 4: assign and resolve**
- Assign to the Plumbing Team staff member, move to **In progress**, send a quick reply "Plumber on the way", then mark **Resolved** with a one-line note.
- Say: "Quick replies are one click, and they work in Hindi too."

**3:15 - 3:40 Step 5: student tracks progress**
Switch to the student page. Show the ticket number and the timeline: Submitted, AI categorised, Info requested, Duplicate linked, Assigned, In progress, Resolved.
- Say: "Students can see exactly where their complaint is, so they stop chasing people."

**3:40 - 4:00 Extension and close**
- Show the Hindi complaint being understood (paste the Hindi sample) and the **Recurring issue** banner for Block B washroom.
- Close: "Less chasing for students, less guesswork for staff, and the data to fix repeat problems for good. We are CampusConnect. Thank you."

## Requirement checklist (say it or show it)
| Requirement | Where it is shown |
|-------------|-------------------|
| Complaint, location and optional photo | Step 1 and 2 |
| Extract issue, summarise, ask for missing info | Step 1 and 2 |
| Category and department from the routing guide | Step 2 |
| Flag possible duplicates for staff | Step 3 |
| Staff assign and update status | Step 4 |
| Ticket number and progress history for students | Step 5 |
| Optional: Hindi and recurring-issue analysis | Closing |

## Likely judge questions
- **How do you use Gemini?** It reads the complaint and photo, extracts structured fields (issue, summary, location, category, department, urgency, missing info) as JSON, and writes follow-up questions. Our routing guide and knowledge base are given to it as context.
- **What if Gemini is wrong?** Staff can override category, department and urgency, and every change is logged in the history.
- **How do you handle duplicates safely?** Same category, same location, still open and similar text. It only flags, and staff confirm.
- **What about complaints outside the four categories?** The bot politely says it is out of scope and points the student to the right office, with no ticket created.
- **How would it scale?** Add more campuses and categories in the routing guide, swap SQLite for a hosted database, add university login and push or SMS notifications.
- **Privacy and safety?** API keys are in .env and never committed. Staff only see their department. Urgent safety issues are flagged immediately.

## If something breaks
- Wi-Fi down: switch to the phone hotspot.
- Gemini slow: say "this usually takes a couple of seconds" and keep talking about the routing guide; the backup has a ticket already created.
- App crash: show the screen recording, or screenshots in this order: incomplete complaint, follow-up question, ticket card, duplicate review, timeline.
