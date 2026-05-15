"""Extraction pipeline - placeholder for future implementation."""

from pathlib import Path

import pandas as pd

from rail_ii.models import Incident


def extract_incidents(source: Path) -> list[Incident]:
    """Extract structured incidents from a source file.

    Args:
        source: Path to the raw operator report.

    Returns:
        A list of extracted ``Incident`` objects.

    Raises:
        NotImplementedError: Always - extraction logic is not yet implemented.
    """
    raise NotImplementedError("Extraction logic has not been implemented yet.")


def incidents_to_dataframe(incidents: list[Incident]) -> pd.DataFrame:
    """Convert a list of incidents to a pandas DataFrame."""
    return pd.DataFrame([inc.model_dump() for inc in incidents])
