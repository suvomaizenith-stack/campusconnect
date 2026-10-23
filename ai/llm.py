"""Thin LLM wrapper for Gemini or Groq with timeouts and clean errors."""
import os

from config import GEMINI_MODEL, GROQ_MODEL, LLM_RETRIES, LLM_TIMEOUT_S, PROVIDER


class LLMError(Exception):
    """Raised when an LLM call fails or is misconfigured."""


def _groq(messages: list[dict], system: str | None, json_mode: bool) -> str:
    """Call Groq chat completions."""
    from groq import Groq

    msgs = ([{"role": "system", "content": system}] if system else []) + messages
    kwargs = {"response_format": {"type": "json_object"}} if json_mode else {}
    client = Groq(
        api_key=os.environ["GROQ_API_KEY"], timeout=LLM_TIMEOUT_S, max_retries=LLM_RETRIES
    )
    resp = client.chat.completions.create(model=GROQ_MODEL, messages=msgs, **kwargs)
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
    client = genai.Client(
        api_key=os.environ["GEMINI_API_KEY"],
        http_options=types.HttpOptions(timeout=int(LLM_TIMEOUT_S * 1000)),  # ms
    )
    resp = client.models.generate_content(model=GEMINI_MODEL, contents=contents, config=config)
    return resp.text or ""


def chat(messages: list[dict], system: str | None = None, json_mode: bool = False) -> str:
    """Send chat messages to the configured PROVIDER and return the reply text."""
    calls = {"groq": _groq, "gemini": _gemini}
    if PROVIDER not in calls:
        raise LLMError(f"Unknown PROVIDER '{PROVIDER}' (use 'groq' or 'gemini').")
    try:
        return calls[PROVIDER](messages, system, json_mode)
    except KeyError as e:
        raise LLMError(f"Missing environment variable: {e}") from e
    except Exception as e:  # timeouts, network, quota, bad responses
        raise LLMError(f"{PROVIDER} call failed: {e}") from e
