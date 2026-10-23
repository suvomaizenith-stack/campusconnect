"""My Tickets page. Built in Phase B."""
from ui.session import require_role
from ui.theme import card

require_role("student")
card("My Tickets", "Coming in Phase B.")
