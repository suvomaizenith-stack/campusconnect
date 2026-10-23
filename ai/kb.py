"""Keyword-based FAQ knowledge base."""
import json
from pathlib import Path

KB_PATH = Path(__file__).resolve().parent.parent / "data" / "kb.json"


def load_kb() -> list[dict]:
    """Load KB entries from data/kb.json."""
    return json.loads(KB_PATH.read_text(encoding="utf-8"))


def find_answer(text: str) -> str | None:
    """Return the answer of the entry with most keyword hits, or None."""
    text = text.lower()
    best, best_score = None, 0
    for entry in load_kb():
        score = sum(1 for k in entry["keywords"] if k in text)
        if score > best_score:
            best, best_score = entry["answer"], score
    return best
