"""Pull a location out of free text: which landmark, floor, room and nearby spot. Pure functions."""
import re

from logic import mapfile

# Hindi / Hinglish names that students actually type; keyed by landmark id from landmarks.json.
HINDI_ALIASES = {
    "a_block": ["ए ब्लॉक", "ए ब्लोक", "a blok"],
    "b_block": ["बी ब्लॉक", "बी ब्लोक", "b blok"],
    "c_block": ["सी ब्लॉक", "सी ब्लोक", "c blok"],
    "d_block": ["डी ब्लॉक", "डी ब्लोक", "d blok"],
    "girls_hostel": ["गर्ल्स हॉस्टल", "गर्ल्स हॉस्टल", "लड़कियों का हॉस्टल", "girls hostal"],
    "boys_hostel": ["बॉयज हॉस्टल", "बॉयज़ हॉस्टल", "लड़कों का हॉस्टल", "boys hostal"],
    "main_gate": ["मेन गेट", "मुख्य द्वार"],
    "reception": ["रिसेप्शन"],
    "tennis_court": ["टेनिस कोर्ट"],
    "bus_parking": ["बस पार्किंग"],
}

_ORDINALS = {
    "ground": 0, "gf": 0, "g": 0, "zero": 0, "first": 1, "1st": 1, "1": 1, "one": 1, "second": 2, "2nd": 2, "2": 2,
    "two": 2, "third": 3, "3rd": 3, "3": 3, "three": 3, "fourth": 4, "4th": 4, "4": 4, "four": 4, "fifth": 5,
    "5th": 5, "5": 5,
    "पहले": 1, "पहली": 1, "पहला": 1, "दूसरे": 2, "दूसरी": 2, "दूसरा": 2, "तीसरे": 3, "तीसरी": 3, "तीसरा": 3,
    "चौथे": 4, "चौथी": 4, "चौथा": 4, "ग्राउंड": 0,
}
_FLOOR_WORDS = r"(?:floor|flr|मंजिल|फ्लोर|तल)"
_ORD = "|".join(sorted((re.escape(k) for k in _ORDINALS), key=len, reverse=True))
_FLOOR_RE = [
    re.compile(rf"(?<![\w])({_ORD})\s*{_FLOOR_WORDS}", re.IGNORECASE),
    re.compile(rf"{_FLOOR_WORDS}\s*(?:no\.?|number|#)?\s*({_ORD})(?![\w])", re.IGNORECASE),
    re.compile(r"(?<![\w])(gf|g\s*floor)(?![\w])", re.IGNORECASE),
]
_ROOM_RE = re.compile(r"(?:room|rm|कमरा|कक्ष|lab)\s*(?:no\.?|number|#|-)?\s*([A-Za-z]?\d{1,4}[A-Za-z]?)", re.IGNORECASE)
_NEARBY_RE = re.compile(
    r"\b(?:near(?:\s+the|\s+to)?|next to|opposite(?:\s+the)?|beside|behind|in front of|outside)\s+([^,.;\n]{3,60})",
    re.IGNORECASE,
)
_NEARBY_STOP = re.compile(r"\s+(?:on|at|in|since|from|and|but|because|is|are|was|has|have)\b.*$", re.IGNORECASE)
_NEARBY_JUNK = re.compile(r"^(?:room|floor|\d|block\b)", re.IGNORECASE)


def _floor_label(n: int) -> str:
    return "Ground" if n == 0 else {1: "1st", 2: "2nd", 3: "3rd"}.get(n, f"{n}th")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower().replace("-", " ").replace("'", "").replace("’", "")).strip()


def _aliases(lm: dict) -> set[str]:
    out = {_norm(lm["name"])} | {_norm(a) for a in lm["aliases"]} | {_norm(a) for a in HINDI_ALIASES.get(lm["id"], [])}
    m = re.match(r"^([A-Za-z]) block(?: (.*))?$", lm["name"], re.IGNORECASE)
    if m:  # "B Block" is also written "Block B"
        letter, rest = m.group(1).lower(), (m.group(2) or "").lower()
        out.add(_norm(f"block {letter} {rest}"))
    return {a for a in out if a}


def _contains_phrase(text: str, phrase: str) -> bool:
    return re.search(rf"(?<![\w]){re.escape(phrase)}(?![\w])", text) is not None


def match_landmark(text: str) -> dict:
    """Find the landmark a complaint talks about, using names and aliases (longest phrase wins).

    Returns {"landmark": lm or None, "ambiguous": [lm, ...]}. The bare word "canteen" is ambiguous on purpose
    (there are four): it returns no landmark and lists them so the UI can ask which one.
    """
    t = _norm(text)
    t = re.sub(r"\bground floor\b|\bgf\b", " ", t)  # "D block ground floor" is not "D Block Ground"
    best, best_len = None, 0
    for lm in mapfile.landmarks():
        for alias in _aliases(lm):
            if len(alias) > best_len and _contains_phrase(t, alias):
                best, best_len = lm, len(alias)
    if best:
        return {"landmark": best, "ambiguous": []}
    for word in ("canteen", "mess", "hostel"):
        if _contains_phrase(t, word):
            options = [lm for lm in mapfile.landmarks() if word in lm["name"].lower()]
            if len(options) > 1:
                return {"landmark": None, "ambiguous": options}
    return {"landmark": None, "ambiguous": []}


def extract_floor(text: str, floors: list[str] | None = None) -> str | None:
    """Return a floor label like '2nd' or 'Ground' found in the text, limited to `floors` when given."""
    t = text.lower()
    found = None
    for rx in _FLOOR_RE:
        m = rx.search(t)
        if m:
            key = m.group(1).replace(" ", "")
            if key in ("gf", "gfloor"):
                found = 0
            elif key in _ORDINALS:
                found = _ORDINALS[key]
            if found is not None:
                break
    if found is None and re.search(r"\bground\b", t):
        found = 0
    if found is None:
        return None
    label = _floor_label(found)
    if floors is not None and label not in floors:
        return None
    return label


def extract_room(text: str) -> str | None:
    """Return a room like '214' or 'Lab 2' if the text names one."""
    m = _ROOM_RE.search(text)
    if not m:
        return None
    prefix = "Lab " if m.group(0).lower().startswith("lab") else ""
    return f"{prefix}{m.group(1).upper()}"


_FIXTURES = {"cooler": "water cooler", "purifier": "water purifier", "lift": "lift", "elevator": "lift",
             "staircase": "stairs", "stairs": "stairs", "vending": "vending machine"}


def extract_nearby(text: str) -> str | None:
    """Return the 'near ...' phrase, e.g. 'the water cooler'. Falls back to a fixture the complaint is about."""
    for m in _NEARBY_RE.finditer(text):
        phrase = _NEARBY_STOP.sub("", m.group(1)).strip()
        phrase = re.sub(r"^(?:the)\s+", "", phrase, flags=re.IGNORECASE)
        if len(phrase) >= 3 and not _NEARBY_JUNK.match(phrase):
            return phrase[:120]
    low = text.lower()
    for word, label in _FIXTURES.items():
        if re.search(rf"\b{word}\b", low):
            return label
    return None


def extract_location(text: str) -> dict:
    """Everything we can read from a complaint: {landmark, ambiguous, floor, room, nearby}. Missing parts are None."""
    found = match_landmark(text)
    lm = found["landmark"]
    return {
        "landmark": lm, "ambiguous": found["ambiguous"],
        "floor": extract_floor(text, lm["floors"] if lm else None),
        "room": extract_room(text), "nearby": extract_nearby(text),
    }


def pin_conflict(pin_landmark: dict | None, chosen: dict | None) -> bool:
    """True if the pin and the chosen landmark disagree. A canteen inside a block does not count as a conflict."""
    if not pin_landmark or not chosen or pin_landmark["id"] == chosen["id"]:
        return False
    return not (mapfile.contains(pin_landmark, chosen) or mapfile.contains(chosen, pin_landmark))
