# CampusConnect backend API

Status: step 1 (Postgres). Only the functions listed here are public; underscore names are private.
Pages may call `db/`, `ai/`, `logic/` and `ui/`. Pages never run SQL or AI calls directly.

## db/db.py (Supabase Postgres)
| Function | Signature | Returns | Called by |
|---|---|---|---|
| `get_conn` | `()` | context manager yielding a pooled psycopg connection (commits on success) | all db functions |
| `migrate` | `(conn)` | `None`; adds missing columns (`ADD COLUMN IF NOT EXISTS`) | `init_db` |
| `init_db` | `()` | `None`; runs `schema_postgres.sql` (tables + RLS), then `migrate` | `app.py` (via `data.seed_staff.seed`), `scripts/apply_schema.py` |
| `find_staff_by_email` | `(email: str)` | `dict` of the staff row, or `None` | `logic/auth.py` |
| `upsert_landmarks` | `(landmarks: list[dict])` | `None`; inserts by name, skips existing | `data/seed_staff.py` |
| `create_ticket` | `(title, description, category, student_email) -> int` | not built yet (step 3+) | — |
| `assign_ticket` | `(ticket_id, staff_id)` | not built yet | — |
| `add_status` | `(ticket_id, status, changed_by=None)` | not built yet | — |
| `add_comment` | `(ticket_id, author, body)` | not built yet | — |
| `set_staff_online` | `(staff_id, online: bool)` | not built yet | — |

## logic/auth.py
| Function | Signature | Returns | Called by |
|---|---|---|---|
| `hash_password` | `(password, salt=None) -> str` | `"salt$hash"` (PBKDF2-SHA256) | `data/seed_staff.py` |
| `verify_password` | `(password, stored) -> bool` | constant-time check | `authenticate_staff` |
| `authenticate_staff` | `(username, password) -> dict \| None` | `{id, name, department}` or `None` | `pages/0_Home.py` |
| `clean_student` | `(name, roll) -> (name, roll)`; raises `ValueError` | trimmed name, upper-cased roll | `pages/0_Home.py` |

## logic/photos.py
| Function | Signature | Returns | Called by |
|---|---|---|---|
| `shrink_photo` | `(data: bytes) -> (bytes, mime)` | JPEG, longest side ≤ `config.PHOTO_MAX_PX` (800) | ticket creation (step 3+) |

## ai/llm.py
| Function | Signature | Returns | Called by |
|---|---|---|---|
| `chat` | `(messages, system=None, json_mode=False) -> str`; raises `LLMError` | reply text; 15 s timeout, 1 retry | `scripts/test_llm.py` (fallback chain in step 3) |
| `LLMError` | exception class | — | callers of `chat` |

## ai/kb.py
| Function | Signature | Returns | Called by |
|---|---|---|---|
| `load_kb` | `() -> list[dict]` | entries from `data/kb.json` | `find_answer` |
| `find_answer` | `(text: str) -> str \| None` | answer with most keyword hits | not wired yet (step 3) |

## ui/session.py
| Function | Signature | Returns | Called by |
|---|---|---|---|
| `current_user` | `() -> dict \| None` | `{role, ...}` | `app.py`, `pages/0_Home.py` |
| `login_student` | `(name, roll)` | `None` | `pages/0_Home.py` |
| `login_staff` | `(staff: dict)` | `None` | `pages/0_Home.py` |
| `logout` | `()` | `None` (staff offline update added in step 2) | `app.py` |
| `require_role` | `(*roles) -> dict`; calls `st.stop()` on failure | user dict | every page |

## ui/theme.py
| Function | Signature | Returns | Called by |
|---|---|---|---|
| `inject_css` | `()` | renders Aurora-style CSS (teal palette and light/dark variables come in step 6) | `app.py` |
| `esc` | `(text) -> str` | HTML-escaped text | all HTML helpers |
| `chip` | `(status: str) -> str` | HTML pill; use with `st.markdown(unsafe_allow_html=True)` | staff/student pages |
| `card` | `(title, body="")` | renders card | pages |
| `metric_card` | `(label, value, accent="cyan")` | renders KPI tile | staff dashboard |
| `timeline` | `(steps: list[dict])` | renders stepper; keys `label`, `detail`, `when` | My Tickets |

## data/seed_staff.py
| Function | Signature | Returns | Called by |
|---|---|---|---|
| `seed` | `()` | `None`; idempotent demo staff and landmarks | `app.py` (cached once per process) |

## Pages
| Page | Role guard | Calls |
|---|---|---|
| `pages/0_Home.py` | none (landing) | `authenticate_staff`, `clean_student`, `login_*`, `current_user` |
| `pages/1_Report_a_Problem.py` | `student` | placeholder |
| `pages/2_My_Tickets.py` | `student` | placeholder |
| `pages/3_Staff_Dashboard.py` | `staff` | placeholder |
| `pages/4_Outage_Map.py` | `student`, `staff` | placeholder |
