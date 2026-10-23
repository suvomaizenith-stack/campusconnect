"""Central settings. Provider, timeouts, database and (later) thresholds live here."""
import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "")  # Supabase Postgres connection string
PROVIDER = os.getenv("PROVIDER", "gemini").lower()  # "gemini" (demo) or "groq"
GEMINI_MODEL = "gemini-2.0-flash"
GROQ_MODEL = "llama-3.3-70b-versatile"
LLM_TIMEOUT_S = 15  # per AI call; on timeout the caller falls back to keyword rules
LLM_RETRIES = 1
PHOTO_MAX_PX = 800  # longest side of stored ticket photos
