"""Staff dashboard. Built in Phase C."""
from ui.session import require_role
from ui.theme import card

require_role("staff")
card("Staff Dashboard", "Coming in Phase C.")
