# CampusConnect Routing Guide

This is the routing guide the AI (Gemini) and the assignment logic follow. One campus, four categories. Anything else is "Out of scope".
Response times are targets agreed for this demo.

## 1. Categories and departments

| Category | Responsible department | Typical issues | First response | Resolution target |
|----------|-----------------------|----------------|----------------|-------------------|
| Plumbing | Plumbing Team | Leaking tap or pipe, blocked drain, overflowing toilet, no water or low pressure, dirty drinking water, water cooler leak | 2 hours | 1 working day |
| Electricity | Electrical Team | Fan, light, tubelight, power cut, tripped MCB, sparking socket, exposed wire, AC or projector not powering on | 1 hour | 1 working day |
| Cleanliness | Housekeeping Team | Dirty washroom, overflowing dustbin, uncleaned classroom or corridor, pests, spills | 2 hours | Same working day |
| Internet connectivity | IT Network Team | Wi-Fi not connecting, slow internet, dead zone, access point or router down, LAN port not working | 30 minutes | 1 working day |
| Out of scope | None | Anything else (fees, hostel allotment, food, academics) | Bot replies immediately | No ticket, redirect student |

## 2. Urgency levels

| Urgency | When to use | Target first response |
|---------|-------------|-----------------------|
| Urgent | Sparking or exposed wire, shock, burst pipe or flooding, sewage overflow, contaminated drinking water, animal inside a building | 15 minutes |
| High | Whole block or floor without power, water or Wi-Fi, blocked toilet, network down in lab or exam hall | 30 minutes |
| Normal | Single fan, light, tap, bin or Wi-Fi spot | Category target above |
| Low | Cosmetic or non-blocking issue, routine cleaning | 1 working day |

## 3. Information every ticket needs

| Field | Required | If missing, the bot asks |
|-------|----------|--------------------------|
| Location (building, floor, room or area) | Yes | "Which building, floor and room or area is this in?" |
| What is wrong | Yes | "Can you describe what is happening?" |
| Severity or extent | Yes | "Is it only your room or the whole floor?" |
| Since when | Recommended | "Since when has this been happening?" |
| Photo | Optional | "A photo would help us fix this faster." |

Category-specific questions are in `data/kb.json` under `ask_if_missing`.
Ask at most 2 questions at a time. Do not create the ticket until Location and What is wrong are both known.

## 4. Classification rules

1. Choose the category by the main cause, not the symptom.
2. Water near electrical items: category Electricity, urgency Urgent, note "Plumbing follow-up needed".
3. Overflowing toilet or drain: Plumbing primary. Add "Cleanliness follow-up" in the notes.
4. Water cooler or RO not cooling or not powering on: Electricity. Water cooler leaking or dirty water: Plumbing.
5. Router or access point without power: Internet connectivity primary, note "Check power supply".
6. Dirty washroom with no water: Plumbing if the water supply is the cause, otherwise Cleanliness.
7. If the complaint is unclear after 2 questions, create the ticket as "Needs review" so staff choose the category.
8. Photo and text disagree: trust the photo and mention the difference in the AI note.

## 5. Possible duplicate rules

Flag as **Possible duplicate** (never merge automatically) when all of these are true:
- Same category.
- Same building and floor, and the same room or a neighbouring area (or the map pin is within about 50 metres).
- The existing ticket is still open (not resolved or closed) and was created in the last 7 days.
- The descriptions refer to the same problem, for example "tap leaking in B-204 washroom" and "water dripping near B block second floor toilet".

Staff then choose:
- **Confirm duplicate:** link to the original ticket. The student keeps their own ticket number and sees shared progress.
- **Not a duplicate:** process as a separate ticket.

The duplicate card should show why it was flagged (same location, same category, similar words).

## 6. Recurring-issue rule (extension)

If the same category appears 3 or more times at one location within 7 days, mark the location as **Recurring**. At 5 or more, show a staff alert suggesting a permanent fix rather than another repair.

## 7. Student-visible progress statuses

Submitted -> Needs info (if applicable) -> Assigned -> In progress -> Resolved -> Closed
(Use the exact names agreed in `docs/ticket_rules.md`.)
