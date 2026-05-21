from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class IncidentSystem(str, Enum):
    DOORS = "doors"
    BRAKES = "brakes"
    PROPULSION = "propulsion"
    SIGNALLING = "signalling"
    HVAC = "hvac"
    PASSENGER_INFORMATION = "passenger_information"
    OTHER = "other"
    UNKNOWN = "unknown"


class IncidentSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class SourceSpan(BaseModel):
    field_name: str
    text: str
    page: Optional[int] = None
    start_char: Optional[int] = None
    end_char: Optional[int] = None

    @model_validator(mode="after")
    def validate_character_offsets(self) -> "SourceSpan":
        if self.start_char is not None and self.end_char is not None:
            if self.start_char < 0:
                raise ValueError("start_char must be non-negative")
            if self.end_char < 0:
                raise ValueError("end_char must be non-negative")
            if self.end_char < self.start_char:
                raise ValueError("end_char must be greater than or equal to start_char")
        return self


class IncidentRecord(BaseModel):
    report_id: str
    operator: Optional[str] = None
    train_id: Optional[str] = None
    incident_datetime: Optional[datetime] = None
    location: Optional[str] = None
    system: IncidentSystem = IncidentSystem.UNKNOWN
    component: Optional[str] = None
    symptom: str
    severity: IncidentSeverity = IncidentSeverity.UNKNOWN
    service_impact: Optional[str] = None
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    source_text: Optional[str] = None
    source_spans: list[SourceSpan] = Field(default_factory=list)

    @field_validator("report_id", mode="before")
    @classmethod
    def validate_report_id(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("report_id cannot be empty")
        return value

    @field_validator("symptom", mode="before")
    @classmethod
    def validate_symptom(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("symptom cannot be empty")
        return value
