"""Central settings. Provider, timeouts, database and (later) thresholds live here."""
import os

from dotenv import load_dotenv

def _copy_streamlit_secrets() -> None:
    try:
        import streamlit as st
        for key, value in st.secrets.items():
            if isinstance(value, str):
                os.environ.setdefault(key, value)
    except Exception:  # no secrets file or not running under Streamlit
        pass


_copy_streamlit_secrets()
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "")  # Supabase Postgres connection string
APP_URL = os.getenv("APP_URL", "").strip().rstrip("/")  # public app link, printed in the QR codes
PROVIDER = os.getenv("PROVIDER", "gemini").lower()  # "gemini" (demo) or "groq"
# gemini-2.0-flash was shut down by Google on 1 June 2026; override with GEMINI_MODEL in .env / Secrets.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
GROQ_MODEL = "llama-3.3-70b-versatile"
LLM_TIMEOUT_S = 15  # per AI call; on timeout the caller falls back to keyword rules
LLM_RETRIES = 1
PHOTO_MAX_PX = 800  # longest side of stored ticket photos

NVIDIA_MODEL = "meta/llama-3.3-70b-instruct"
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
LLM_CHAIN = ["gemini", "groq", "nvidia"]  # tried in order; PROVIDER is moved to the front
BREAKER_FAILURES = 3  # consecutive failures before skipping the LLM
BREAKER_COOLDOWN_S = 60

CATEGORIES = ["plumbing", "electricity", "cleanliness", "internet"]
HOTSPOT_REPORTS = 3  # reports in the window that make a group a hotspot
CRITICAL_REPORTS = 5  # reports in the window that make a group critical
ALERT_WINDOW_HOURS = 24
CACHE_RESOLVED_HOURS = 24  # recently resolved groups still answer new reports
CACHE_MATCH_THRESHOLD = 0.3  # keyword Jaccard needed to match an existing group
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_MINUTES = 15

# --- Map -------------------------------------------------------------------
MAP_DIR = "data"
MAP_IMAGE = "campus_map.png"
LANDMARK_SNAP_RADIUS_M = 30  # open-area taps snap to a landmark within this distance
HIT_RADIUS_PX = 20  # issue dots and service icons are hit within this screen distance
MAP_WINDOWS = {"1 hour": 1, "24 hours": 24, "7 days": 168}
MAP_DEFAULT_WINDOW = "24 hours"
RESOLVED_TICK_HOURS = 24  # resolved issues keep a check mark on the map this long

# --- Staff dashboard -------------------------------------------------------
RECURRING_DAYS = 7
RECURRING_YELLOW = 3  # same location + category in RECURRING_DAYS
RECURRING_RED = 5
OVERDUE_HOURS = {"plumbing": 24, "electricity": 24, "cleanliness": 24, "internet": 24}
URGENCY_LABELS = {"critical": "Urgent", "high": "High", "normal": "Normal", "later": "Low"}
DEPARTMENTS = {
    "plumbing": "Plumbing & Water",
    "electricity": "Electrical",
    "cleanliness": "Housekeeping",
    "internet": "IT & Network",
}
CATEGORY_LABELS = {
    "plumbing": "Plumbing",
    "electricity": "Electricity",
    "cleanliness": "Cleanliness",
    "internet": "Internet connectivity",
}

LOW_CONFIDENCE = 0.5  # AI category confidence below this flags the ticket for staff review
FIRST_RESPONSE_HOURS = {"plumbing": 2, "electricity": 1, "cleanliness": 2, "internet": 0.5}  # staff must touch a ticket within this

DB_POOL_MAX = 10  # shared connections; many concurrent users reuse these
