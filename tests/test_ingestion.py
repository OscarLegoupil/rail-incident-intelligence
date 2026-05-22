from pathlib import Path

import pytest

from rail_ii.ingestion import Document, TxtLoader, normalize_text


def test_txt_loader_reads_fixture_and_extracts_document_id() -> None:
    fixture_path = Path(__file__).parent / "fixtures" / "SR_FIXTURE_001.txt"
    document = TxtLoader.load(fixture_path)

    assert document.document_id == "SR_FIXTURE_001"
    assert document.source_type == "txt"
    assert document.source_path == fixture_path
    assert "Test report fixture" in document.raw_text
    assert "Line 3" in document.normalized_text
    assert "\r" not in document.normalized_text


def test_normalization_removes_trailing_whitespace_and_collapses_blank_lines() -> None:
    raw_text = "Line 1   \r\n\r\n\r\nLine 2  \n  \nLine 3   \r\n"
    normalized = normalize_text(raw_text)

    assert normalized == "Line 1\n\nLine 2\n\nLine 3"


def test_load_txt_invalid_path_raises_file_not_found(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing_report.txt"

    with pytest.raises(FileNotFoundError):
        TxtLoader.load(missing_path)


def test_load_txt_directory_path_raises_value_error(tmp_path: Path) -> None:
    directory_path = tmp_path / "reports"
    directory_path.mkdir()

    with pytest.raises(ValueError):
        TxtLoader.load(directory_path)
