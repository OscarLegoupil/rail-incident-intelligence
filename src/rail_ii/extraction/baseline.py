"""
Baseline rule-based incident extractor.

Uses simple deterministic rules to extract structured incident information from
maintenance reports. Intended as a minimal working baseline, not for production use.

Known limitations:
- No temporal parsing; dates are not extracted
- Severity is inferred heuristically from keywords
- Component extraction is minimal
- Service impact extraction relies on keyword matching
- Confidence scores are conservative and reflect extraction certainty only,
  not accuracy of the extracted values
"""

from __future__ import annotations

import re

from rail_ii.ingestion.document import Document
from rail_ii.schema.incident import (
    IncidentRecord,
    IncidentSeverity,
    IncidentSystem,
)

# Keywords for system classification
SYSTEM_KEYWORDS = {
    IncidentSystem.DOORS: [
        "door",
        "actuator",
        "pneumatic",
        "seal",
        "latch",
        "mechanism",
    ],
    IncidentSystem.BRAKES: [
        "brake",
        "braking",
        "pressure",
        "pedal",
        "caliper",
        "pad",
    ],
    IncidentSystem.HVAC: [
        "ac",
        "air",
        "compressor",
        "cooling",
        "ventilation",
        "hvac",
        "fan",
        "temperature",
        "thermal",
    ],
    IncidentSystem.PROPULSION: [
        "motor",
        "engine",
        "propulsion",
        "traction",
        "drive",
        "transmission",
        "fuel",
    ],
    IncidentSystem.SIGNALLING: [
        "signal",
        "light",
        "indicator",
        "display",
        "warning",
        "alert",
    ],
    IncidentSystem.PASSENGER_INFORMATION: [
        "passenger",
        "information",
        "announcement",
        "display",
        "screen",
        "audio",
    ],
}

# Keywords for severity classification
CRITICAL_KEYWORDS = ["critical", "emergency", "severe", "dangerous", "safety risk"]
HIGH_KEYWORDS = ["fault", "failure", "malfunction", "leaking", "broken", "not working"]
MEDIUM_KEYWORDS = ["issue", "problem", "intermittent", "degraded"]

# Keywords for service impact
SERVICE_IMPACT_KEYWORDS = [
    "out of service",
    "pulled out",
    "removed from service",
    "not in service",
    "disruption",
    "delay",
]


def extract_baseline(document: Document) -> IncidentRecord:
    """
    Extract incident information from a Document using simple rules.

    Args:
        document: A Document object containing the report text

    Returns:
        An IncidentRecord with extracted fields. Always returns a valid record
        even if extraction fails on individual fields.
    """
    text = document.normalized_text.lower()
    lines = text.split("\n")

    # Always extractable from document metadata
    report_id = document.document_id

    # Extract train_id (pattern: TR-XXX or similar)
    train_id = _extract_train_id(text)

    # Extract location (maintenance facility, depot, etc.)
    location = _extract_location(text)

    # Extract system type
    system = _extract_system(text)

    # Extract symptom (main issue description)
    symptom = _extract_symptom(text, lines)

    # Extract severity
    severity = _extract_severity(text)

    # Extract component (what failed)
    component = _extract_component(text)

    # Extract service impact
    service_impact = _extract_service_impact(text)

    # Calculate confidence based on extracted fields
    confidence = _calculate_confidence(train_id, location, system, component, service_impact)

    # Create the record; operator is typically not in reports
    return IncidentRecord(
        report_id=report_id,
        operator=None,
        train_id=train_id,
        location=location,
        system=system,
        component=component,
        symptom=symptom,
        severity=severity,
        service_impact=service_impact,
        confidence=confidence,
        source_text=document.normalized_text[:500] if document.normalized_text else None,
    )


def _extract_train_id(text: str) -> str | None:
    """Extract train ID using pattern matching (e.g., TR-452)."""
    # Look for common patterns: TR-XXX, unit TR-XXX
    match = re.search(r"\btr[- ]?(\d{1,4})\b", text, re.IGNORECASE)
    if match:
        return f"TR-{match.group(1)}"
    return None


def _extract_location(text: str) -> str | None:
    """Extract location keywords from text."""
    location_keywords = [
        "maintenance facility",
        "maintenance bay",
        "depot",
        "station",
        "facility",
        "bay",
        "shop",
    ]

    for keyword in location_keywords:
        if keyword in text:
            # Try to extract surrounding context
            idx = text.find(keyword)
            start = max(0, idx - 50)
            end = min(len(text), idx + len(keyword) + 50)
            snippet = text[start:end].strip()

            # Clean up the snippet to be reasonable
            if len(snippet) > 100:
                snippet = snippet[50:100]
            return snippet.title()

    return None


def _extract_system(text: str) -> IncidentSystem:
    """Determine the system type using keyword matching."""
    # Score each system based on keyword presence
    scores = {}

    for system, keywords in SYSTEM_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in text)
        scores[system] = score

    # Find system with highest score
    best_system = max(scores, key=scores.get)

    if scores[best_system] > 0:
        return best_system

    return IncidentSystem.UNKNOWN


def _extract_symptom(text: str, lines: list[str]) -> str:
    """
    Extract the main symptom/issue description.

    Strategy: Look for sentences with problem keywords or take a significant
    portion of the text. Always returns a non-empty string.
    """
    # Remove lines that are just names or single words (likely headers)
    cleaned_lines = [
        line.strip() for line in text.split("\n") if line.strip() and len(line.strip()) > 10
    ]
    cleaned_text = " ".join(cleaned_lines)

    # Split into sentences
    sentences = re.split(r"[.!?]\s+", cleaned_text)
    sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 15]

    if not sentences:
        return "unknown issue"

    # Look for sentences with problem keywords
    problem_keywords = [
        "broken",
        "fail",
        "fault",
        "malfunction",
        "not",
        "leak",
        "damage",
        "issue",
        "problem",
        "error",
    ]

    for sentence in sentences:
        if any(keyword in sentence for keyword in problem_keywords):
            return sentence.capitalize()

    # If no problem keyword found, use first substantial sentence
    for sentence in sentences:
        if len(sentence) > 20:
            return sentence.capitalize()

    # Fallback: use first sentence long enough
    return sentences[0].capitalize() if sentences else "unknown issue"


def _extract_severity(text: str) -> IncidentSeverity:
    """Determine severity using keyword matching."""
    if any(keyword in text for keyword in CRITICAL_KEYWORDS):
        return IncidentSeverity.CRITICAL

    if any(keyword in text for keyword in HIGH_KEYWORDS):
        return IncidentSeverity.HIGH

    if any(keyword in text for keyword in MEDIUM_KEYWORDS):
        return IncidentSeverity.MEDIUM

    return IncidentSeverity.UNKNOWN


def _extract_component(text: str) -> str | None:
    """Extract component name using pattern matching."""
    # Look for component patterns like "door set B", "pneumatic actuator", etc.
    component_patterns = [
        r"(pneumatic\s+actuator(?:\s+(?:on|car|at|for)\s+\w+\s*\d*)?)",
        r"(door\s+(?:set|mechanism|actuator)?(?:\s+[a-zA-Z0-9]+)?)",
        r"(brake\s+(?:system|pad|caliper)?)",
        r"(fan\s+(?:motor|relay)?)",
        r"(compressor)",
    ]

    for pattern in component_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            component = match.group(1).strip()
            # Remove trailing verb forms
            component = re.sub(r"\s+(?:went|went bad|was|had|have)$", "", component)
            return component

    return None


def _extract_service_impact(text: str) -> str | None:
    """Extract service impact if mentioned."""
    # Keywords that indicate service impact
    impact_keywords = [
        "out of service",
        "pulled out",
        "removed from service",
        "not in service",
        "disruption",
        "delay",
        "safety risk",
        "revenue service",
        "shutdown",
    ]

    for keyword in impact_keywords:
        if keyword in text:
            # Try to find a sentence mentioning this impact
            idx = text.find(keyword)
            start = max(0, idx - 100)
            end = min(len(text), idx + len(keyword) + 100)
            snippet = text[start:end]

            # Extract sentence containing the keyword
            sentences = re.split(r"[.!?]\s+", snippet)
            for sentence in sentences:
                if keyword in sentence and len(sentence) > 10:
                    return sentence.strip().capitalize()

            return f"{keyword.strip().capitalize()} issue"

    return None


def _calculate_confidence(
    train_id: str | None,
    location: str | None,
    system: IncidentSystem,
    component: str | None,
    service_impact: str | None,
) -> float:
    """
    Calculate confidence score based on extraction success.

    This reflects confidence in the extraction process, not the accuracy
    of the values themselves.
    """
    base_confidence = 0.3  # Start with conservative baseline

    # Add for each successfully extracted field
    if train_id:
        base_confidence += 0.1
    if location:
        base_confidence += 0.1
    if system != IncidentSystem.UNKNOWN:
        base_confidence += 0.1
    if component:
        base_confidence += 0.1
    if service_impact:
        base_confidence += 0.1

    # Cap at 1.0
    return min(base_confidence, 1.0)
