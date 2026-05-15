"""Smoke tests for domain models."""

from datetime import datetime

from rail_ii.models import Incident


def test_incident_minimal() -> None:
    inc = Incident(id="INC-001", title="Track defect", description="Cracked rail at km 42.3")
    assert inc.id == "INC-001"
    assert inc.severity is None


def test_incident_full() -> None:
    inc = Incident(
        id="INC-002",
        title="Signal failure",
        description="Signal S14 stuck at red.",
        severity="high",
        occurred_at=datetime(2026, 1, 15, 8, 30),
        resolved_at=datetime(2026, 1, 15, 10, 0),
        operator="Network Rail",
        source_file="report_2026_01.pdf",
    )
    assert inc.severity == "high"
    assert inc.operator == "Network Rail"


def test_incident_round_trip() -> None:
    data = {
        "id": "INC-003",
        "title": "Points failure",
        "description": "Points 22A failed to lock.",
    }
    inc = Incident(**data)
    dumped = inc.model_dump()
    assert dumped["id"] == "INC-003"
    assert dumped["title"] == "Points failure"
