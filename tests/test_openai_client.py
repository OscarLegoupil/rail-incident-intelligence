"""Tests for the OpenAI provider adapter.

These tests mock the OpenAI SDK so no network calls are made and no API key
is required.
"""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from rail_ii.extraction.llm_extractor import extract_with_llm
from rail_ii.extraction.openai_client import make_openai_client
from rail_ii.ingestion import TxtLoader

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "SR_FIXTURE_001.txt"


def _fake_chat_response(content: str) -> MagicMock:
    """Build a MagicMock shaped like an openai ChatCompletion response."""
    choice = MagicMock()
    choice.message.content = content
    response = MagicMock()
    response.choices = [choice]
    return response


@pytest.fixture
def fake_openai_module(monkeypatch: pytest.MonkeyPatch):
    """Install a fake ``openai`` module exposing an ``OpenAI`` class.

    Returns the mock ``OpenAI`` class so tests can inspect calls.
    """
    mock_openai_class = MagicMock()
    fake_module = types.ModuleType("openai")
    fake_module.OpenAI = mock_openai_class
    monkeypatch.setitem(sys.modules, "openai", fake_module)
    return mock_openai_class


class TestMakeOpenAIClient:
    def test_rejects_empty_api_key(self) -> None:
        with pytest.raises(ValueError, match="api_key is required"):
            make_openai_client(api_key="")

    def test_passes_api_key_and_model(self, fake_openai_module: MagicMock) -> None:
        client = make_openai_client(api_key="sk-test", model="gpt-4o-mini")

        # Constructing the adapter should have built the SDK client with our key.
        fake_openai_module.assert_called_once_with(api_key="sk-test")

        # And invoking it should send a chat completion with the configured model.
        sdk_instance = fake_openai_module.return_value
        sdk_instance.chat.completions.create.return_value = _fake_chat_response('{"k":1}')

        result = client("SYS", "USR")

        assert result == '{"k":1}'
        call_kwargs = sdk_instance.chat.completions.create.call_args.kwargs
        assert call_kwargs["model"] == "gpt-4o-mini"
        assert call_kwargs["temperature"] == 0.0
        assert call_kwargs["response_format"] == {"type": "json_object"}
        assert call_kwargs["messages"] == [
            {"role": "system", "content": "SYS"},
            {"role": "user", "content": "USR"},
        ]

    def test_returns_empty_string_when_content_is_none(
        self, fake_openai_module: MagicMock
    ) -> None:
        sdk_instance = fake_openai_module.return_value
        sdk_instance.chat.completions.create.return_value = _fake_chat_response(None)

        client = make_openai_client(api_key="sk-test")
        assert client("s", "u") == ""

    def test_integrates_with_extract_with_llm(
        self, fake_openai_module: MagicMock
    ) -> None:
        """End-to-end: stubbed OpenAI -> extract_with_llm -> IncidentRecord."""
        document = TxtLoader.load(FIXTURE_PATH)
        payload = {
            "report_id": document.document_id,
            "operator": None,
            "train_id": "TR-999",
            "incident_datetime": None,
            "location": None,
            "system": "doors",
            "component": "actuator",
            "symptom": "door fails to close",
            "severity": "high",
            "service_impact": None,
            "confidence": 0.8,
            "source_text": None,
        }
        sdk_instance = fake_openai_module.return_value
        sdk_instance.chat.completions.create.return_value = _fake_chat_response(
            json.dumps(payload)
        )

        client = make_openai_client(api_key="sk-test")
        result = extract_with_llm(document, client)

        assert result.error is None
        assert result.record is not None
        assert result.record.train_id == "TR-999"
        assert result.record.symptom == "door fails to close"

    def test_sdk_exception_surfaces_as_client_error(
        self, fake_openai_module: MagicMock
    ) -> None:
        """SDK errors must be caught by extract_with_llm, never crash callers."""
        document = TxtLoader.load(FIXTURE_PATH)
        sdk_instance = fake_openai_module.return_value
        sdk_instance.chat.completions.create.side_effect = RuntimeError("rate limited")

        client = make_openai_client(api_key="sk-test")
        result = extract_with_llm(document, client)

        assert result.record is None
        assert result.error is not None
        assert result.error.startswith("llm_client_error")
        assert "rate limited" in result.error


class TestConfigSecretHandling:
    """Verify the API key is wrapped in SecretStr and not leaked by repr()."""

    def test_api_key_is_secretstr_and_not_in_repr(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("RAIL_II_OPENAI_API_KEY", "sk-super-secret-12345")

        # Re-import config fresh so it picks up the env var.
        import importlib

        from rail_ii import config as config_module

        importlib.reload(config_module)

        assert config_module.settings.openai_api_key is not None
        assert (
            config_module.settings.openai_api_key.get_secret_value()
            == "sk-super-secret-12345"
        )
        assert "sk-super-secret-12345" not in repr(config_module.settings)
        assert "sk-super-secret-12345" not in str(config_module.settings)

    def test_missing_api_key_is_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("RAIL_II_OPENAI_API_KEY", raising=False)

        import importlib

        from rail_ii import config as config_module

        # Stop pydantic-settings from reading the developer's local .env during the test.
        with patch.object(
            config_module.Settings,
            "model_config",
            {"env_prefix": "RAIL_II_", "env_file": None, "extra": "ignore"},
        ):
            importlib.reload(config_module)
            assert config_module.settings.openai_api_key is None
