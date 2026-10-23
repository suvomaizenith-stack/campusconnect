"""Keyword helpers shared by rule-based triage and the reply cache. No network, no database."""
import json
import re
from functools import lru_cache
from pathlib import Path

ROUTING_PATH = Path(__file__).resolve().parent.parent / "data" / "routing_guide.json"
_TOKEN_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
STOPWORDS = frozenset(
    "a an the is are was were be been am i me my we our you your it its this that these those there here "
    "to of in on at by for from with and or but not no so very too just please pls sir mam since "
    "has have had do does did can could will would should near around some any all again also still "
    "get getting got since morning today yesterday now again really".split()
)


@lru_cache(maxsize=1)
def routing_guide() -> dict:
    """Return data/routing_guide.json as a dict keyed by category."""
    return json.loads(ROUTING_PATH.read_text(encoding="utf-8"))


def _stem(token: str) -> str:
    """Very light stemming so 'taps'/'tap' and 'leaking'/'leak' compare equal."""
    for suffix in ("ing", "ed", "es", "s"):
        if token.endswith(suffix) and len(token) - len(suffix) >= 3:
            return token[: -len(suffix)]
    return token


SYNONYMS = {
    "leakage": "leak", "leaky": "leak", "dripping": "leak", "toilet": "washroom", "restroom": "washroom",
    "bathroom": "washroom", "wi-fi": "wifi", "internet": "wifi", "network": "wifi", "tubelight": "light", "bulb": "light", "lights": "light",
}


def tokens(text: str) -> set[str]:
    """Return the set of stemmed, non-stopword tokens of the text (common synonyms merged)."""
    out = set()
    for t in _TOKEN_RE.findall(text.lower()):
        t = SYNONYMS.get(t, t)
        if t not in STOPWORDS and len(t) > 1:
            out.add(_stem(t))
    return out


def has_keyword(text: str, keyword: str) -> bool:
    """True if the keyword (a word or a short phrase) appears in the text."""
    low = text.lower()
    if not keyword.isascii():  # Devanagari has no stemming; a substring match covers verb forms (टपक -> टपक रहा है)
        return keyword in low
    if " " in keyword or "-" in keyword:
        return keyword in low
    return _stem(keyword) in {_stem(t) for t in _TOKEN_RE.findall(low)}


def jaccard(a: set[str], b: set[str]) -> float:
    """Jaccard similarity of two token sets (0 when either is empty)."""
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def category_scores(text: str) -> dict[str, int]:
    """Number of routing-guide keywords found in the text, per category."""
    return {
        cat: sum(1 for kw in info["keywords"] + info.get("keywords_hi", []) if has_keyword(text, kw))
        for cat, info in routing_guide().items() if not cat.startswith("_")
    }


NOISE = frozenset("first second third fourth fifth floor room block ground area side corner building near next opposite hall wing".split())
_ORDINAL_RE = re.compile(r"^\d+(st|nd|rd|th)?$")


def issue_tokens(text: str) -> set[str]:
    """Tokens describing the problem itself: no stopwords, numbers, floors or place words."""
    return {t for t in tokens(text) if not _ORDINAL_RE.match(t) and _stem(t) not in NOISE and t not in NOISE}


def language_of(text: str) -> str:
    """'hi' if a fifth or more of the letters are Devanagari, else 'en'."""
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return "en"
    return "hi" if sum(1 for c in letters if "\u0900" <= c <= "\u097f") / len(letters) >= 0.2 else "en"


def out_of_scope_hit(text: str) -> bool:
    """True if the text mentions a topic the routing guide lists as outside the four categories."""
    return any(has_keyword(text, k) for k in routing_guide().get("_out_of_scope", []))
