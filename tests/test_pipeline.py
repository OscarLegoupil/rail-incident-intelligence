"""Tests for the extraction pipeline."""

from pathlib import Path

import pandas as pd
import pytest

from rail_ii.models import Incident
from rail_ii.pipeline import extract_incidents, incidents_to_dataframe


def test_extract_not_implemented() -> None:
    with pytest.raises(NotImplementedError):
        extract_incidents(Path("dummy.pdf"))


def test_incidents_to_dataframe() -> None:
    incidents = [
        Incident(id="INC-001", title="Track defect", description="Crack at km 12."),
        Incident(id="INC-002", title="Signal fault", description="S7 intermittent."),
    ]
    df = incidents_to_dataframe(incidents)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert list(df["id"]) == ["INC-001", "INC-002"]
