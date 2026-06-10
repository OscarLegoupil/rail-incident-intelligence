"""
OpenAI provider adapter.

Builds a small callable that satisfies the ``LLMClient`` protocol from
``rail_ii.extraction.llm_extractor``. Kept intentionally thin: no retries,
no caching, no abstraction layer. Wire it up where you call
``extract_with_llm``.

Usage::

    from rail_ii.config import settings
    from rail_ii.extraction.openai_client import make_openai_client
    from rail_ii.extraction.llm_extractor import extract_with_llm

    client = make_openai_client(
        api_key=settings.openai_api_key.get_secret_value(),
        model=settings.openai_model,
    )
    result = extract_with_llm(document, client)
"""

from __future__ import annotations

from rail_ii.extraction.llm_extractor import LLMClient

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TEMPERATURE = 0.0


def make_openai_client(
    api_key: str,
    model: str = DEFAULT_MODEL,
    temperature: float = DEFAULT_TEMPERATURE,
) -> LLMClient:
    """Return a callable that sends prompts to OpenAI Chat Completions.

    The returned callable matches the ``LLMClient`` protocol:
    ``(system_prompt, user_prompt) -> str``.

    Args:
        api_key: OpenAI API key. Never hard-code; pass from Settings.
        model: Chat model id. ``gpt-4o-mini`` is a good default for extraction.
        temperature: 0.0 for near-deterministic outputs (recommended for eval).

    Notes:
        - ``response_format={"type": "json_object"}`` forces the model to
          return parseable JSON, which makes the extractor's malformed-JSON
          branch rare in practice.
        - Requires the word "json" to appear in the messages; the system
          prompt already does, so no extra work needed.
    """
    if not api_key:
        raise ValueError("api_key is required to build an OpenAI client")

    # Imported lazily so the package only fails when actually used, not at
    # module import time (helpful in test environments without the SDK).
    from openai import OpenAI

    sdk_client = OpenAI(api_key=api_key)

    def call(system_prompt: str, user_prompt: str) -> str:
        response = sdk_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=temperature,
        )
        content = response.choices[0].message.content
        return content or ""

    return call
