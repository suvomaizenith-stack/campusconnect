# Campus Saathi (CampusConnect)

AI complaint-to-ticket system for K.R. Mangalam University, Gurugram. Students describe
a problem in chat; the AI turns it into a ticket routed to the right department. Staff
manage tickets on a dashboard, and an interactive outage map shows issues around campus.

## Team roles
- **AI/LLM:** prompts, `ai/llm.py`, `ai/kb.py`
- **Backend/DB:** `db/`, seed data
- **Frontend:** Streamlit pages, `ui/theme.py`
- **Map/Demo:** outage map, pitch

## Setup
```bash
python3 -m venv venv && source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # then fill DATABASE_URL and at least one AI key (GEMINI_API_KEY)
python scripts/apply_schema.py   # creates the tables in Supabase (safe to re-run)
python scripts/create_staff.py   # staff + admin accounts; prints the access keys once, save them
python scripts/seed_demo.py      # optional demo data; demo student roll DEMO001, PIN 1234
```

## Run
```bash
streamlit run app.py
```

## Test
```bash
pytest -q          # database tests run only when DATABASE_URL is set
```

## Notes
- The Gemini model is set by `GEMINI_MODEL` (default `gemini-3.6-flash`); `gemini-2.0-flash` was shut down by Google on 1 June 2026.
- On Streamlit Cloud, put the same keys as `.env` in the app's Secrets.
- The look (colours, fonts) lives in `ui/theme.py` (`VARS` for colours) and `.streamlit/config.toml`.
