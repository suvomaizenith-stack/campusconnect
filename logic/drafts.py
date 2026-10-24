"""Report drafts: validate and save what a student typed, list it, and delete it."""
from db import drafts as ddb

TITLE_MAX = 120
DETAILS_MAX = 2000


def save(student: dict, title: str, location: str | None, kind: str | None, details: str) -> int:
    """Save a draft. Only the title is required; location and kind may be None for 'not sure'."""
    title = (title or "").strip()
    if not title:
        raise ValueError("Give the draft a short title so you can find it later.")
    return ddb.save_draft(student["id"], title[:TITLE_MAX], location or None, kind or None,
                          (details or "").strip()[:DETAILS_MAX] or None)


def for_student(student: dict) -> list[dict]:
    return ddb.list_drafts(student["id"])


def remove(student: dict, draft_id: int) -> None:
    ddb.delete_draft(student["id"], draft_id)
