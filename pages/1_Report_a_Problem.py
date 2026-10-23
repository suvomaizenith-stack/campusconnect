"""Report a Problem page. Built in Phase B."""
import streamlit as st

from ui.session import require_role
from ui.theme import card

require_role("student")
# TODO (post-MVP): voice-note input, pin-drop location picker.
card("Report a Problem", "Coming in Phase B.")
