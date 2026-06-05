"""Tests for the baseline rule-based extractor."""

from pathlib import Path

import pytest

from rail_ii.extraction.baseline import extract_baseline
from rail_ii.ingestion import TxtLoader
from rail_ii.schema.incident import IncidentRecord, IncidentSeverity, IncidentSystem


class TestExtractBaseline:
    """Test the extract_baseline function with synthetic reports."""

    def test_extract_baseline_from_sr001_door_malfunction(self) -> None:
        """Test extraction from SR001: door pneumatic actuator leak."""
        fixture_path = Path(__file__).parent / "fixtures" / "SR_FIXTURE_001.txt"
        document = TxtLoader.load(fixture_path)

        # Create a document with door-related content
        document.raw_text = """
        MAINTENANCE REPORT - 24 March 2024

        Train ID: TR-452
        Depot: Central Maintenance Facility

        Door System Malfunction

        During routine inspection of unit TR-452, the pneumatic actuator on car 3,
        door set B, was found to be leaking compressed air. The door closes
        intermittently and does not maintain seal pressure. This poses a safety
        risk during revenue service as doors may not close completely between
        stations. Recommend immediate replacement of pneumatic cylinder assembly.
        """
        document.normalized_text = document.raw_text.lower()

        record = extract_baseline(document)

        assert isinstance(record, IncidentRecord)
        assert record.report_id == document.document_id
        assert record.train_id == "TR-452"
        assert record.system == IncidentSystem.DOORS
        assert record.severity in [IncidentSeverity.HIGH, IncidentSeverity.CRITICAL]
        assert "pneumatic" in record.symptom.lower()
        assert record.component is not None
        assert "pneumatic" in record.component.lower()
        assert record.confidence > 0.5

    def test_extract_baseline_from_brake_failure(self) -> None:
        """Test extraction from brake pressure failure."""
        fixture_path = Path(__file__).parent / "fixtures" / "SR_FIXTURE_001.txt"
        document = TxtLoader.load(fixture_path)

        document.raw_text = """
        INCIDENT REPORT

        Brake failure on line 7 service. Brake pressure dropped suddenly.
        Operator reported soft pedal feel. Unit pulled out of service for shop.
        """
        document.normalized_text = document.raw_text.lower()

        record = extract_baseline(document)

        assert record.system == IncidentSystem.BRAKES
        assert record.severity in [IncidentSeverity.HIGH, IncidentSeverity.CRITICAL]
        assert "brake" in record.symptom.lower()
        assert record.service_impact is not None
        assert "out of service" in record.service_impact.lower()
        assert record.confidence > 0.4

    def test_extract_baseline_from_hvac_issue(self) -> None:
        """Test extraction from HVAC failure."""
        fixture_path = Path(__file__).parent / "fixtures" / "SR_FIXTURE_001.txt"
        document = TxtLoader.load(fixture_path)

        document.raw_text = """
        MAINTENANCE LOG

        Train TR-203 in maintenance bay 4. AC not working on the morning run.
        The compressor is running but fans aren't spinning. Been like this
        since yesterday afternoon. Probably the fan relay went bad.
        """
        document.normalized_text = document.raw_text.lower()

        record = extract_baseline(document)

        assert record.train_id == "TR-203"
        assert record.system == IncidentSystem.HVAC
        assert "fan" in record.component.lower() if record.component else True
        assert record.confidence > 0.4

    def test_extract_baseline_handles_unknown_system(self) -> None:
        """Test that unknown system falls back to UNKNOWN."""
        fixture_path = Path(__file__).parent / "fixtures" / "SR_FIXTURE_001.txt"
        document = TxtLoader.load(fixture_path)

        document.raw_text = "Some random maintenance note with no clear system."
        document.normalized_text = document.raw_text.lower()

        record = extract_baseline(document)

        assert record.system == IncidentSystem.UNKNOWN
        assert record.severity in [
            IncidentSeverity.MEDIUM,
            IncidentSeverity.UNKNOWN,
        ]
        assert record.confidence <= 0.5  # Low confidence for unknown extraction

    def test_extract_baseline_always_has_valid_symptom(self) -> None:
        """Test that symptom is never empty."""
        fixture_path = Path(__file__).parent / "fixtures" / "SR_FIXTURE_001.txt"
        document = TxtLoader.load(fixture_path)

        # Even with minimal text, symptom should be non-empty
        document.raw_text = "TR-100"
        document.normalized_text = document.raw_text.lower()

        record = extract_baseline(document)

        assert record.symptom
        assert len(record.symptom) > 0
        assert isinstance(record.symptom, str)

    def test_extract_baseline_report_id_from_document_id(self) -> None:
        """Test that report_id is always extracted from document_id."""
        fixture_path = Path(__file__).parent / "fixtures" / "SR_FIXTURE_001.txt"
        document = TxtLoader.load(fixture_path)

        document.raw_text = "Empty report"
        document.normalized_text = "empty report"

        record = extract_baseline(document)

        assert record.report_id == document.document_id

    def test_extract_baseline_confidence_increases_with_fields(self) -> None:
        """Test that confidence increases as more fields are extracted."""
        fixture_path = Path(__file__).parent / "fixtures" / "SR_FIXTURE_001.txt"

        # Minimal text, few fields
        document_minimal = TxtLoader.load(fixture_path)
        document_minimal.raw_text = "A problem occurred."
        document_minimal.normalized_text = "a problem occurred."
        record_minimal = extract_baseline(document_minimal)

        # Rich text, many fields
        document_rich = TxtLoader.load(fixture_path)
        document_rich.raw_text = """
        Train TR-500 in central maintenance facility reported critical door
        fault on pneumatic actuator. Pulled from service immediately.
        """
        document_rich.normalized_text = document_rich.raw_text.lower()
        record_rich = extract_baseline(document_rich)

        # Rich report should have higher confidence
        assert record_rich.confidence >= record_minimal.confidence

    def test_extract_baseline_never_crashes_on_empty_document(self) -> None:
        """Test robustness with empty or minimal input."""
        fixture_path = Path(__file__).parent / "fixtures" / "SR_FIXTURE_001.txt"
        document = TxtLoader.load(fixture_path)

        document.raw_text = ""
        document.normalized_text = ""

        # Should not raise an exception
        record = extract_baseline(document)

        assert isinstance(record, IncidentRecord)
        assert record.report_id
        assert record.symptom  # Should have default

    def test_extract_baseline_with_real_synthetic_reports(self) -> None:
        """Integration test with actual synthetic report files."""
        data_dir = Path(__file__).parent.parent.parent.parent / "data" / "synthetic"

        # Check if synthetic data exists
        if not (data_dir / "reports" / "SR001.txt").exists():
            pytest.skip("Synthetic data not available")

        # Load SR001 and extract
        sr001_path = data_dir / "reports" / "SR001.txt"
        document = TxtLoader.load(sr001_path)
        record = extract_baseline(document)

        # Should have successfully extracted something
        assert record.report_id == "SR001"
        assert record.symptom
        assert record.system in [s for s in IncidentSystem]
        assert record.severity in [s for s in IncidentSeverity]

    def test_extract_baseline_severity_critical(self) -> None:
        """Test that critical keywords trigger CRITICAL severity."""
        fixture_path = Path(__file__).parent / "fixtures" / "SR_FIXTURE_001.txt"
        document = TxtLoader.load(fixture_path)

        document.raw_text = "This is a critical emergency situation with a severe safety risk."
        document.normalized_text = document.raw_text.lower()

        record = extract_baseline(document)

        assert record.severity == IncidentSeverity.CRITICAL

    def test_extract_baseline_severity_high(self) -> None:
        """Test that failure keywords trigger HIGH severity."""
        fixture_path = Path(__file__).parent / "fixtures" / "SR_FIXTURE_001.txt"
        document = TxtLoader.load(fixture_path)

        document.raw_text = "Motor failure detected. Compressor malfunction."
        document.normalized_text = document.raw_text.lower()

        record = extract_baseline(document)

        assert record.severity == IncidentSeverity.HIGH

    def test_extract_baseline_severity_medium(self) -> None:
        """Test that problem keywords trigger MEDIUM severity."""
        fixture_path = Path(__file__).parent / "fixtures" / "SR_FIXTURE_001.txt"
        document = TxtLoader.load(fixture_path)

        document.raw_text = "Intermittent issue with door actuator."
        document.normalized_text = document.raw_text.lower()

        record = extract_baseline(document)

        assert record.severity == IncidentSeverity.MEDIUM

    def test_extract_baseline_system_classification(self) -> None:
        """Test system classification for different keyword combinations."""
        fixture_path = Path(__file__).parent / "fixtures" / "SR_FIXTURE_001.txt"

        test_cases = [
            ("door actuator failure", IncidentSystem.DOORS),
            ("brake pressure issue", IncidentSystem.BRAKES),
            ("hvac compressor failure", IncidentSystem.HVAC),
            ("propulsion motor problem", IncidentSystem.PROPULSION),
            ("signal light malfunction", IncidentSystem.SIGNALLING),
            ("passenger announcement system down", IncidentSystem.PASSENGER_INFORMATION),
        ]

        for text, expected_system in test_cases:
            document = TxtLoader.load(fixture_path)
            document.raw_text = text
            document.normalized_text = text.lower()

            record = extract_baseline(document)

            assert record.system == expected_system, f"Failed for text: {text}"

    def test_extract_baseline_train_id_extraction(self) -> None:
        """Test train ID pattern matching."""
        fixture_path = Path(__file__).parent / "fixtures" / "SR_FIXTURE_001.txt"

        test_cases = [
            ("Train TR-452 reported an issue", "TR-452"),
            ("Unit tr-203 in maintenance", "TR-203"),
            ("TR 999 had a problem", "TR-999"),
            ("No train mentioned here", None),
        ]

        for text, expected_train_id in test_cases:
            document = TxtLoader.load(fixture_path)
            document.raw_text = text
            document.normalized_text = text.lower()

            record = extract_baseline(document)

            assert record.train_id == expected_train_id, f"Failed for text: {text}"

    def test_extract_baseline_location_extraction(self) -> None:
        """Test location extraction."""
        fixture_path = Path(__file__).parent / "fixtures" / "SR_FIXTURE_001.txt"

        document = TxtLoader.load(fixture_path)
        document.raw_text = "Unit in central maintenance facility reported a problem."
        document.normalized_text = document.raw_text.lower()

        record = extract_baseline(document)

        assert record.location is not None
        assert "maintenance" in record.location.lower()
