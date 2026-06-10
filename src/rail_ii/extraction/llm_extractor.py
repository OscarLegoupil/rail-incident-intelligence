"""
LLM-based incident extractor.

Converts a Document into a validated IncidentRecord by calling a pluggable
LLM client and parsing its structured JSON output.

The client integration is intentionally minimal: any callable that takes a
system prompt and user prompt and returns a string is a valid provider. This
keeps the extractor easy to test with stubs and easy to wire to a real
provider (OpenAI, Anthropic, local model, etc.) without an abstraction layer.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Protocol

from pydantic import ValidationError

from rail_ii.extraction.prompts import SYSTEM_PROMPT, build_user_prompt
from rail_ii.ingestion.document import Document
from rail_ii.schema.incident import IncidentRecord


class LLMClient(Protocol):
    """Minimal interface for an LLM provider.

    Implementations take a system prompt and a user prompt and return the
    raw model response as a string.
    """

    def __call__(self, system_prompt: str, user_prompt: str) -> str: ...


@dataclass
class LLMExtractionResult:
    """Outcome of one LLM extraction attempt.

    Exactly one of ``record`` or ``error`` is populated. ``raw_response`` is
    always retained for debugging and audit.
    """

    record: IncidentRecord | None
    error: str | None
    raw_response: str


_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)


def _extract_json_payload(text: str) -> str:
    """Pull a JSON object out of a raw LLM response.

    Handles three common shapes:
    1. Bare JSON: ``{...}``
    2. JSON inside a fenced code block: ```json\n{...}\n```
    3. JSON embedded in surrounding prose.

    Returns the candidate JSON substring, or the stripped original text if no
    object delimiters are found (in which case json.loads will fail cleanly).
    """
    stripped = text.strip()

    fence_match = _JSON_FENCE_RE.search(stripped)
    if fence_match:
        return fence_match.group(1).strip()

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end != -1 and end > start:
        return stripped[start : end + 1]

    return stripped


def extract_with_llm(document: Document, client: LLMClient) -> LLMExtractionResult:
    """Extract an IncidentRecord from a Document using an LLM client.

    Never raises on malformed JSON or schema validation failures; instead
    returns an ``LLMExtractionResult`` whose ``error`` field describes the
    problem and whose ``record`` is None.
    """
    user_prompt = build_user_prompt(document)

    try:
        raw_response = client(SYSTEM_PROMPT, user_prompt)
    except Exception as exc:  # noqa: BLE001 - provider errors must not crash callers
        return LLMExtractionResult(
            record=None,
            error=f"llm_client_error: {exc}",
            raw_response="",
        )

    if not isinstance(raw_response, str) or not raw_response.strip():
        return LLMExtractionResult(
            record=None,
            error="empty_response",
            raw_response=raw_response if isinstance(raw_response, str) else "",
        )

    payload = _extract_json_payload(raw_response)

    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        return LLMExtractionResult(
            record=None,
            error=f"malformed_json: {exc.msg} (line {exc.lineno}, col {exc.colno})",
            raw_response=raw_response,
        )

    if not isinstance(data, dict):
        return LLMExtractionResult(
            record=None,
            error=f"unexpected_json_type: expected object, got {type(data).__name__}",
            raw_response=raw_response,
        )

    # Ensure report_id is anchored to the document, not whatever the model emitted.
    data["report_id"] = document.document_id

    try:
        record = IncidentRecord.model_validate(data)
    except ValidationError as exc:
        return LLMExtractionResult(
            record=None,
            error=f"schema_validation_error: {exc.error_count()} error(s)",
            raw_response=raw_response,
        )

    return LLMExtractionResult(record=record, error=None, raw_response=raw_response)
