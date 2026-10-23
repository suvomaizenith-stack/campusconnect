"""Thin LLM wrapper supporting Groq and Gemini."""
import os

from dotenv import load_dotenv

load_dotenv()

GROQ_MODEL = "llama-3.3-70b-versatile"
GEMINI_MODEL = "gemini-2.0-flash"


class LLMError(Exception):
    """Raised when an LLM call fails or is misconfigured."""


def _groq(messages: list[dict], system: str | None, json_mode: bool) -> str:
    """Call Groq chat completions."""
    from groq import Groq

    msgs = ([{"role": "system", "content": system}] if system else []) + messages
    kwargs = {"response_format": {"type": "json_object"}} if json_mode else {}
    resp = Groq(api_key=os.environ["GROQ_API_KEY"]).chat.completions.create(
        model=GROQ_MODEL, messages=msgs, **kwargs
    )
    return resp.choices[0].message.content or ""


def _gemini(messages: list[dict], system: str | None, json_mode: bool) -> str:
    """Call Gemini generate_content."""
    from google import genai
    from google.genai import types

    contents = [
        types.Content(
            role="model" if m["role"] == "assistant" else "user",
            parts=[types.Part(text=m["content"])],
        )
        for m in messages
    ]
    config = types.GenerateContentConfig(
        system_instruction=system,
        response_mime_type="application/json" if json_mode else None,
    )
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    resp = client.models.generate_content(
        model=GEMINI_MODEL, contents=contents, config=config
    )
    return resp.text or ""


def chat(messages: list[dict], system: str | None = None, json_mode: bool = False) -> str:
    """Send chat messages to the configured PROVIDER and return the reply text."""
    provider = os.getenv("PROVIDER", "groq").lower()
    calls = {"groq": _groq, "gemini": _gemini}
    if provider not in calls:
        raise LLMError(f"Unknown PROVIDER '{provider}' (use 'groq' or 'gemini').")
    try:
        return calls[provider](messages, system, json_mode)
    except KeyError as e:
        raise LLMError(f"Missing environment variable: {e}") from e
    except Exception as e:
        raise LLMError(f"{provider} call failed: {e}") from e
