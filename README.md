# CampusConnect

AI complaint-to-ticket system for K.R. Mangalam University, Gurugram. Students describe
a problem in chat; the AI turns it into a ticket routed to the right department. Staff
manage tickets on a dashboard, and an outage map shows issues around campus.

## Team roles
- **AI/LLM:** prompts, `ai/llm.py`, `ai/kb.py`
- **Backend/DB:** `db/`, seed data
- **Frontend:** Streamlit pages
- **Map/Demo:** outage map, pitch

## Setup
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your API keys
python -m data.seed_staff
```

## Run
```bash
streamlit run app.py
```
