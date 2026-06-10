"""Tests for the LLM-based incident extractor."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from rail_ii.extraction.llm_extractor import (
    LLMExtractionResult,
    extract_with_llm,
)
from rail_ii.extraction.prompts import (
    SYSTEM_PROMPT,
    build_user_prompt,
)
from rail_ii.ingestion import TxtLoader
from rail_ii.schema.incident import (
    IncidentRecord,
    IncidentSeverity,
    IncidentSystem,
)

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "SR_FIXTURE_001.txt"


def _load_doc() -> object:
    return TxtLoader.load(FIXTURE_PATH)


def _valid_payload(report_id: str) -> dict:
    return {
        "report_id": report_id,
        "operator": None,
        "train_id": "TR-452",
        "incident_datetime": "2024-03-24T09:00:00",
        "location": "Central Maintenance Facility",
        "system": "doors",
        "component": "pneumatic actuator car 3, door B",
        "symptom": "pneumatic actuator leaking compressed air",
        "severity": "high",
        "service_impact": "doors may not close completely",
        "confidence": 0.9,
        "source_text": "pneumatic actuator on car 3, door B leaking compressed air",
    }


class _StubClient:
    """Records prompts received and returns a canned response."""

    def __init__(self, response: str) -> None:
        self.response = response
        self.calls: list[tuple[str, str]] = []

    def __call__(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append((system_prompt, user_prompt))
        return self.response


class TestExtractWithLLM:
    def test_valid_structured_output_returns_record(self) -> None:
        document = _load_doc()
        client = _StubClient(json.dumps(_valid_payload(document.document_id)))

        result = extract_with_llm(document, client)

        assert isinstance(result, LLMExtractionResult)
        assert result.error is None
        assert isinstance(result.record, IncidentRecord)
        assert result.record.train_id == "TR-452"
        assert result.record.system == IncidentSystem.DOORS
        assert result.record.severity == IncidentSeverity.HIGH
        assert result.record.confidence == 0.9

    def test_client_receives_system_and_user_prompt(self) -> None:
        document = _load_doc()
        client = _StubClient(json.dumps(_valid_payload(document.document_id)))

        extract_with_llm(document, client)

        assert len(client.calls) == 1
        system_prompt, user_prompt = client.calls[0]
        assert system_prompt == SYSTEM_PROMPT
        assert user_prompt == build_user_prompt(document)
        assert document.document_id in user_prompt

    def test_report_id_anchored_to_document(self) -> None:
        """Even if the model returns a wrong report_id, we use the document's."""
        document = _load_doc()
        payload = _valid_payload(document.document_id)
        payload["report_id"] = "WRONG-ID-FROM-MODEL"
        client = _StubClient(json.dumps(payload))

        result = extract_with_llm(document, client)

        assert result.record is not None
        assert result.record.report_id == document.document_id

    def test_json_inside_markdown_fence_is_parsed(self) -> None:
        document = _load_doc()
        payload = _valid_payload(document.document_id)
        wrapped = f"Here is the result:\n```json\n{json.dumps(payload)}\n```\n"
        client = _StubClient(wrapped)

        result = extract_with_llm(document, client)

        assert result.error is None
        assert result.record is not None
        assert result.record.system == IncidentSystem.DOORS

    def test_json_embedded_in_prose_is_extracted(self) -> None:
        document = _load_doc()
        payload = _valid_payload(document.document_id)
        wrapped = f"Sure! The extracted data is {json.dumps(payload)} - hope that helps."
        client = _StubClient(wrapped)

        result = extract_with_llm(document, client)

        assert result.error is None
        assert result.record is not None

    def test_malformed_json_returns_error_not_exception(self) -> None:
        document = _load_doc()
        client = _StubClient("{not valid json at all,,,}")

        result = extract_with_llm(document, client)

        assert result.record is None
        assert result.error is not None
        assert result.error.startswith("malformed_json")
        assert result.raw_response == "{not valid json at all,,,}"

    def test_empty_response_returns_error(self) -> None:
        document = _load_doc()
        client = _StubClient("   \n\t  ")

        result = extract_with_llm(document, client)

        assert result.record is None
        assert result.error == "empty_response"

    def test_non_object_json_returns_error(self) -> None:
        document = _load_doc()
        client = _StubClient(json.dumps(["not", "an", "object"]))

        result = extract_with_llm(document, client)

        assert result.record is None
        assert result.error is not None
        assert result.error.startswith("unexpected_json_type")

    def test_missing_required_symptom_returns_validation_error(self) -> None:
        document = _load_doc()
        payload = _valid_payload(document.document_id)
        del payload["symptom"]
        client = _StubClient(json.dumps(payload))

        result = extract_with_llm(document, client)

        assert result.record is None
        assert result.error is not None
        assert result.error.startswith("schema_validation_error")

    def test_empty_symptom_returns_validation_error(self) -> None:
        document = _load_doc()
        payload = _valid_payload(document.document_id)
        payload["symptom"] = "   "
        client = _StubClient(json.dumps(payload))

        result = extract_with_llm(document, client)

        assert result.record is None
        assert result.error is not None
        assert result.error.startswith("schema_validation_error")

    def test_invalid_enum_value_returns_validation_error(self) -> None:
        document = _load_doc()
        payload = _valid_payload(document.document_id)
        payload["system"] = "not-a-real-system"
        client = _StubClient(json.dumps(payload))

        result = extract_with_llm(document, client)

        assert result.record is None
        assert result.error is not None
        assert result.error.startswith("schema_validation_error")

    def test_confidence_out_of_range_returns_validation_error(self) -> None:
        document = _load_doc()
        payload = _valid_payload(document.document_id)
        payload["confidence"] = 1.7
        client = _StubClient(json.dumps(payload))

        result = extract_with_llm(document, client)

        assert result.record is None
        assert result.error is not None
        assert result.error.startswith("schema_validation_error")

    def test_optional_fields_can_be_null(self) -> None:
        document = _load_doc()
        payload = {
            "report_id": document.document_id,
            "operator": None,
            "train_id": None,
            "incident_datetime": None,
            "location": None,
            "system": "unknown",
            "component": None,
            "symptom": "unclear maintenance issue",
            "severity": "unknown",
            "service_impact": None,
            "confidence": 0.3,
            "source_text": None,
        }
        client = _StubClient(json.dumps(payload))

        result = extract_with_llm(document, client)

        assert result.error is None
        assert result.record is not None
        assert result.record.system == IncidentSystem.UNKNOWN
        assert result.record.severity == IncidentSeverity.UNKNOWN

    def test_client_exception_is_caught(self) -> None:
        document = _load_doc()

        def broken_client(system_prompt: str, user_prompt: str) -> str:
            raise RuntimeError("network down")

        result = extract_with_llm(document, broken_client)

        assert result.record is None
        assert result.error is not None
        assert result.error.startswith("llm_client_error")
        assert "network down" in result.error

    def test_raw_response_preserved_on_failure(self) -> None:
        document = _load_doc()
        bad = "totally garbage output"
        client = _StubClient(bad)

        result = extract_with_llm(document, client)

        assert result.record is None
        assert result.raw_response == bad


class TestPrompts:
    def test_system_prompt_lists_enum_values(self) -> None:
        for system in IncidentSystem:
            assert system.value in SYSTEM_PROMPT
        for severity in IncidentSeverity:
            assert severity.value in SYSTEM_PROMPT

    def test_user_prompt_contains_report_id_and_text(self) -> None:
        document = _load_doc()
        prompt = build_user_prompt(document)
        assert document.document_id in prompt
        # The fixture has non-empty content
        assert "REPORT" in prompt.upper()

    @pytest.mark.parametrize("normalized,raw", [("", "some raw text"), ("normalized", "raw")])
    def test_user_prompt_prefers_normalized_then_raw(
        self, normalized: str, raw: str
    ) -> None:
        document = _load_doc()
        document.normalized_text = normalized
        document.raw_text = raw
        prompt = build_user_prompt(document)
        expected = normalized if normalized else raw
        assert expected in prompt
