"""Smoke-test the LLM wrapper with one plain and one JSON-mode prompt. Run: python scripts/test_llm.py"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ai.llm import LLMError, chat  # noqa: E402
from config import PROVIDER  # noqa: E402


def main() -> int:
    print(f"Provider: {PROVIDER}")
    try:
        print("Plain reply:", chat([{"role": "user", "content": "Reply with exactly one word: pong"}]).strip())
        raw = chat(
            [{"role": "user", "content": 'Return JSON {"category": ..., "urgent": ...} for: "tap in the washroom is leaking".'}],
            json_mode=True,
        )
    except LLMError as e:
        print(f"FAILED: {e}")
        return 1
    try:
        print("JSON reply:", json.loads(raw))
    except json.JSONDecodeError:
        print(f"FAILED: reply is not valid JSON: {raw!r}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
