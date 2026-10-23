"""Describe a ticket photo. Gemini only; on any failure the photo is still attached, just not analysed."""
import os

import config

NOT_ANALYSED = "Photo attached (not analysed)."


def describe_photo(data: bytes, mime: str) -> tuple[str, bool]:
    """Return (one-line description, analysed). Never raises."""
    if not os.getenv("GEMINI_API_KEY"):
        return NOT_ANALYSED, False
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(
            api_key=os.environ["GEMINI_API_KEY"],
            http_options=types.HttpOptions(timeout=int(config.LLM_TIMEOUT_S * 1000)),
        )
        resp = client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=[
                types.Part.from_bytes(data=data, mime_type=mime),
                "In one short sentence, describe the campus maintenance problem visible in this photo.",
            ],
        )
        text = (resp.text or "").strip()
        return (text[:200], True) if text else (NOT_ANALYSED, False)
    except Exception:
        return NOT_ANALYSED, False
