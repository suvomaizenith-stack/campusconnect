"""LLM wrapper: Gemini -> Groq -> NVIDIA with timeouts, retry, a circuit breaker and JSON repair.

Callers must always have a rule-based fallback: every function here raises LLMError on failure.
"""
import json
import os
import threading
import time

import httpx

import config


class LLMError(Exception):
    """Raised when every provider failed, none is configured, or the breaker is open."""


_lock = threading.Lock()
_state = {"streak": 0, "skip_until": 0.0, "last_ok": None, "last_provider": None}

_KEY_VARS = {"gemini": "GEMINI_API_KEY", "groq": "GROQ_API_KEY", "nvidia": "NVIDIA_API_KEY"}


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
    cfg = types.GenerateContentConfig(
        system_instruction=system,
        response_mime_type="application/json" if json_mode else None,
    )
    client = genai.Client(
        api_key=os.environ["GEMINI_API_KEY"],
        http_options=types.HttpOptions(timeout=int(config.LLM_TIMEOUT_S * 1000)),  # ms
    )
    resp = client.models.generate_content(model=config.GEMINI_MODEL, contents=contents, config=cfg)
    return resp.text or ""


def _groq(messages: list[dict], system: str | None, json_mode: bool) -> str:
    """Call Groq chat completions (retries are handled by this module, not the SDK)."""
    from groq import Groq

    msgs = ([{"role": "system", "content": system}] if system else []) + messages
    kwargs = {"response_format": {"type": "json_object"}} if json_mode else {}
    client = Groq(api_key=os.environ["GROQ_API_KEY"], timeout=config.LLM_TIMEOUT_S, max_retries=0)
    resp = client.chat.completions.create(model=config.GROQ_MODEL, messages=msgs, **kwargs)
    return resp.choices[0].message.content or ""


def _nvidia(messages: list[dict], system: str | None, json_mode: bool) -> str:
    """Call NVIDIA's OpenAI-compatible chat completions endpoint."""
    msgs = ([{"role": "system", "content": system}] if system else []) + messages
    body = {"model": config.NVIDIA_MODEL, "messages": msgs, "temperature": 0.2}
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    resp = httpx.post(
        f"{config.NVIDIA_BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {os.environ['NVIDIA_API_KEY']}"},
        json=body,
        timeout=config.LLM_TIMEOUT_S,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"] or ""


_CALLS = {"gemini": _gemini, "groq": _groq, "nvidia": _nvidia}


def _chain() -> list[str]:
    """Providers with an API key set, in order, with config.PROVIDER first."""
    order = [config.PROVIDER] + [p for p in config.LLM_CHAIN if p != config.PROVIDER]
    return [p for p in order if p in _CALLS and os.getenv(_KEY_VARS[p])]


def _try_provider(name: str, messages: list[dict], system: str | None, json_mode: bool) -> str:
    """One provider with retry and exponential backoff. Raises the last error."""
    last: Exception | None = None
    for attempt in range(config.LLM_RETRIES + 1):
        try:
            return _CALLS[name](messages, system, json_mode)
        except Exception as e:  # timeouts, network, quota, bad responses
            last = e
            if attempt < config.LLM_RETRIES:
                time.sleep(0.5 * (2**attempt))
    raise last  # type: ignore[misc]


def chat(messages: list[dict], system: str | None = None, json_mode: bool = False) -> str:
    """Return reply text from the first provider that answers. Raises LLMError if none does."""
    with _lock:
        if time.monotonic() < _state["skip_until"]:
            raise LLMError("AI paused after repeated failures; using rule-based fallback.")
    providers = _chain()
    if not providers:
        with _lock:
            _state["last_ok"] = False
        raise LLMError("No LLM API key is configured.")
    errors = []
    for name in providers:
        try:
            text = _try_provider(name, messages, system, json_mode)
        except Exception as e:
            errors.append(f"{name}: {type(e).__name__}")
            continue
        with _lock:
            _state.update(streak=0, last_ok=True, last_provider=name)
        return text
    with _lock:
        _state["streak"] += 1
        _state["last_ok"] = False
        if _state["streak"] >= config.BREAKER_FAILURES:
            _state["skip_until"] = time.monotonic() + config.BREAKER_COOLDOWN_S
            _state["streak"] = 0
    raise LLMError("All providers failed (" + ", ".join(errors) + ").")


def _parse_json(text: str) -> dict:
    """Parse a JSON object, tolerating ```json fences."""
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[4:] if text.lower().startswith("json") else text
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("expected a JSON object")
    return data


def chat_json(messages: list[dict], system: str | None, validate) -> dict:
    """Ask for JSON, check it with validate(data) (raises ValueError if bad), repair once, else LLMError.

    validate may return a cleaned dict; if it returns None the parsed dict is used as is.
    """
    text = chat(messages, system, json_mode=True)
    for attempt in range(2):
        try:
            data = _parse_json(text)
            return validate(data) or data
        except (ValueError, KeyError, TypeError) as e:
            if attempt == 1:
                raise LLMError(f"AI returned invalid JSON: {e}") from e
            repair = messages + [
                {"role": "assistant", "content": text},
                {"role": "user", "content": f"That was not valid ({e}). Reply again with only the corrected JSON object."},
            ]
            text = chat(repair, system, json_mode=True)
    raise LLMError("unreachable")


def get_ai_status() -> str:
    """Return 'normal' if the last AI call worked (or none was made yet), else 'degraded'."""
    with _lock:
        if time.monotonic() < _state["skip_until"]:
            return "degraded"
    if not _chain():
        return "degraded"
    return "degraded" if _state["last_ok"] is False else "normal"


def reset_state() -> None:
    """Clear breaker and status. Used by tests."""
    with _lock:
        _state.update(streak=0, skip_until=0.0, last_ok=None, last_provider=None)
