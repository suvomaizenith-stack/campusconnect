FOR SUVOM
Feature: Map data is ready — notes for FOR_SUVOM_campus_map.md
Branch: arsh/student-ui (PR: "data: add illustrated campus map and 31 landmarks")
Files: data/campus_map.png, data/landmarks.json (replaces the old file)
Prompt: not a Copilot prompt — read before running FOR_SUVOM_campus_map.md, and paste the "Changes to the map spec" block into Copilot together with that prompt.

Suvom — note from Arsh:
1. data/campus_map.png is the final illustrated map (1600×1000, traced from the real satellite view). data/landmarks.json already has every position and clickable outline filled — SKIP tools/map_calibrator.py (Section 7 of the map spec).
2. landmarks.json has no lat/lng anymore. Everything is normalised map_x / map_y (0–1).
3. 31 landmarks: 21 numbered places, 2 numbered areas (Utility Yard, Open Plot), 8 unnumbered roads.

---------------------------------------------------------------------

## Changes to the map spec (paste with FOR_SUVOM_campus_map.md)

landmarks.json facts (do not change the data, read it as-is):
- Every landmark has `category`: "place" | "area" | "road".
- Places and areas: `number` 1–23, `area` = one polygon (normalised).
- Roads: `number: null`, `area: null`, `areas` = list of rectangles (one per road segment). Sohna Road has `outside_campus: true`.
- `map.hit_rule` (also below) is the source of truth for tap matching.
- `map.meters_per_px` is filled — use it for all metre-based radii.
- Services: helpdesk and security have positions; medical and it_support have null map_x/map_y → skip drawing them (still list them in the Index with contacts from kb.json).

hit_test / resolve_pin order (replaces the order in Section 3 of the map spec):
1. Issue dot within 20 px → issue.
2. Service icon within 20 px → service.
3. Places + areas (`area` polygon, point-in-polygon). If several match, the SMALLEST polygon wins (canteens and messes sit inside bigger buildings).
4. Only if no place matched: roads (any rectangle in `areas`).
5. Nothing matched → open area near the nearest landmark within LANDMARK_SNAP_RADIUS_M (else nearest overall).
- Landmarks with outside_campus = true: allowed as a complaint location, label "Outside campus — Sohna Road".

Drawing:
- The base image already contains building colours, numbers, names, road names, zone banners and the compass. Draw ONLY live overlays (badges, ✅, service icons, issue dots, pin, selection outline). Do not redraw names.
- Badge anchor: top-right corner of the landmark's area (max x, min y), not the centre — the centre holds the name label.
- Roads get badges too (a pothole on Entrance Road), placed at the road's map_x/map_y.

Index list under the map: numbered places 1–23 first, then a "Roads" section (unnumbered), then "Services".

Location text matching: use name + aliases. The plain word "canteen" is deliberately NOT an alias of any canteen (there are four) — if the student just says "canteen", the location card asks which one.

Floors are placeholders (blocks and hostels Ground–4th). Arsh will confirm real counts; code must read floors from the file, never hardcode.
# Arsh — CampusConnect handoff v2 (replaces arsh_handoff.md)
Branch: `arsh/student-ui` · Code freeze: **9:15 am** · Ends: 12:15 pm

The old handoff's chat and map prompts are retired. They used folium, real latitude/longitude, and "ticket only if Not solved".

---

## 1. Your files and where they go

| File | Goes to | Who uses it |
|---|---|---|
| `campus_map.png` | `data/campus_map.png` | the app (map base image) |
| `landmarks.json` | `data/landmarks.json` (replace old) | the app + Suvom |
| `campus_map_preview.png` | keep for demo / pitch slides | team, judges |
| `build_campus_map.py` | your laptop (ask Suvom before adding to `tools/`) | you, to redraw the map |
| `FOR_SUVOM_backend_features.md` | send to Suvom | backend, 10 features |
| `FOR_SUVOM_precise_location.md` | send to Suvom | floor / room / nearby spot |
| `FOR_SUVOM_campus_map.md` | send to Suvom | interactive map |
| `FOR_SUVOM_map_data_note.md` | send to Suvom | data is ready, tap rules, roads |
| `FOR_SUVOM_student_pages.md` | send to Suvom (after backend) | your 3 page prompts |

---

## 2. Right now: commit the map data (10 min)

```
cd campus-connect
git checkout arsh/student-ui
git pull origin main
```
Copy `campus_map.png` and `landmarks.json` into `data/`, then:
```
python -m json.tool data/landmarks.json > /dev/null && echo OK
git add data/campus_map.png data/landmarks.json
git commit -m "data: add illustrated campus map and 31 landmarks"
git push
```
(Windows: skip the `json.tool` line or run `python -m json.tool data\landmarks.json`.)
Open a pull request on GitHub → "Compare & pull request" → title "data: illustrated campus map + landmarks" → tell Suvom.

---

## 3. Message to send Suvom (copy-paste, privately)

> Hi Suvom, all the CampusConnect specs are attached. Run them in this order:
> 1. FOR_SUVOM_backend_features.md: Phase 1 first (schema + role login).
> 2. FOR_SUVOM_precise_location.md
> 3. FOR_SUVOM_campus_map.md together with FOR_SUVOM_map_data_note.md. The map image and landmarks.json are in my PR with every position filled, so skip the calibrator.
> 4. FOR_SUVOM_student_pages.md: my 3 student pages, once the backend functions exist.
>
> Suggested order tonight: backend Phase 1, then map step 1 (map + badges on both dashboards), then backend Phases 2–3, then my Report page and Outrage Map page, then the rest.
> When a phase is done, please share docs/backend_api.md so I can match the function names. Send code as "CODE FOR: <path>" and I'll paste, test and push.

---

## 4. Order of work tonight

| Time (approx) | Suvom | You |
|---|---|---|
| 7:45–9:30 pm | Backend Phase 1 (schema, login) | Merge-ready map data PR; confirm building names and floor counts with the team |
| 9:30–11 pm | Map build step 1–2 (map + badges + details panel) | Test map: checklist A below; screenshots |
| 11 pm–1 am | Backend Phases 2–3 (AI-first tickets, ETA, me-too, priority, alerts) | Paste/test Report page when ready (checklist B) |
| 1–3 am | Map step 3 (pin-drop) + Outrage Map page + My Dashboard | Checklists C, D |
| 3–7 am | Phases 4–7 as time allows (duplicates, drafts, photo/voice, chat) | Test, fix list, screenshots for demo |
| 7–9:15 am | Bug fixes only | Final run-through, status post, freeze |

Commit at least every hour (`feat:` for pasted code, `data:` for JSON, `fix:` for fixes).

---

## 5. Testing checklists

**A. Map (both dashboards)**
- [ ] Map shows as a student and as staff; works with Wi-Fi off
- [ ] Tap each of the 23 numbered places: the right name opens (canteens and messes open themselves, not the big building)
- [ ] Tap a road: "Entrance Road" etc. Tap the empty plot: "Open Plot"
- [ ] Index list under the map selects the same places
- [ ] Phone-width window: taps still land on the right place

**B. Report a Problem**
- [ ] "cooler not cold near room 214, 2nd floor girls hostel" fills the location card (Girls Hostel / 2nd / Room 214 / near the water cooler)
- [ ] Tap D Block on the map: card shows D Block with its floors
- [ ] Pin in C Block but Girls Hostel chosen: the app asks which is right
- [ ] Submit: ticket code, ETA, self-help with phone numbers from kb.json
- [ ] Same complaint from a 2nd student: "already reported by 1 student" message, own ticket code
- [ ] "Solved" closes the ticket; "Chat with staff" requests chat
- [ ] Hindi voice note: English text + transcript shown before submit
- [ ] Photo-only + one line of text: sensible category
- [ ] Half-written report, click away, refresh: draft is still there
- [ ] AI key removed: ticket still created with a warning

**C. Outrage Map**
- [ ] 3 reports at one place: orange badge; 5: red with ring
- [ ] Tap Girls Hostel: floors listed; "2nd floor · N" expands to issues
- [ ] "I face this too": count goes up at once; second tap disabled
- [ ] Time filter 1h / 24h / 7d changes badges; search "d block" selects D Block
- [ ] Resolved issue shows ✅ for 24 h

**D. My Dashboard**
- [ ] Tickets with status, ETA, "also reported by N"
- [ ] Staff reply appears within about 5 s; my reply reaches staff
- [ ] Drafts: Resume opens the Report page prefilled; Delete asks twice

Errors: send Suvom the last 15 lines or a screenshot. On a merge conflict, stop and send a screenshot.

---

## 6. Open questions for the team (ask now)
- Is the unlabelled building on the north of the academic loop really **B Block**?
- Real floor counts for A/B/C/D Block and both hostels.
- Where are the **medical room** and **IT / Wi-Fi help desk**? (positions are empty)
- Is the "Amul" pin near Bus Parking a campus kiosk? (add as a landmark if yes)
- Samriddhi: does `kb.json` have a contact for helpdesk, security, medical, IT? (`kb_contact` keys in landmarks.json point there)

To change names or floors: edit `LANDMARKS` in `build_campus_map.py`, run `python build_campus_map.py data`, and commit both files again.

---

## 7. Status post templates
```
Done: campus map + 31 landmarks in PR; all specs sent to Suvom
Doing: confirming floors/B Block; testing map when Phase 1 lands
Blocked: waiting on backend_api.md for page function names
```
```
Done: Report page + Outrage Map tested (checklists B, C)
Doing: My Dashboard testing, demo screenshots
Blocked: —
```
