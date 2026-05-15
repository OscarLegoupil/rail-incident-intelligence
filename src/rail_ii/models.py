"""Domain models for rail maintenance incidents."""

from datetime import datetime

from pydantic import BaseModel


class Incident(BaseModel):
    """A single maintenance incident extracted from an operator report."""

    id: str
    title: str
    description: str
    severity: str | None = None
    occurred_at: datetime | None = None
    resolved_at: datetime | None = None
    operator: str | None = None
    source_file: str | None = None
