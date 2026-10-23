"""Safety wording that shows emergency contacts on the report page. It never changes ticket routing."""
from ai.keywords import has_keyword

SAFETY_TERMS = (
    "fainted", "faint", "unconscious", "bleeding", "blood", "injured", "injury", "fire", "smoke", "burning",
    "shock", "sparking", "exposed wire", "gas leak", "gas smell", "chest pain", "breathing", "drowning",
    "stranger", "harass", "harassment", "assault", "threat", "stalking",
)
CONTACT_SERVICES = ("medical", "security", "helpdesk")


def is_safety_report(text: str) -> bool:
    return any(has_keyword(text or "", term) for term in SAFETY_TERMS)
