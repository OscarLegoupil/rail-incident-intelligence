"""
Field-level comparison utilities and metric accumulators.

Three comparison modes are supported:

- ``exact_match``     - identity equality; used for enum fields (system, severity)
  and structured IDs (report_id, train_id).
- ``normalized_match`` - lower-case, collapse-whitespace equality; used for
  free-text string fields (symptom, component, location, service_impact).
- ``nullable_exact``  - like exact_match but treats (None, None) as correct and
  (None, <value>) / (<value>, None) as incorrect.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


def _normalize(value: str) -> str:
    """Lower-case and collapse internal whitespace."""
    return re.sub(r"\s+", " ", value.strip().lower())


def exact_match(predicted: object, expected: object) -> bool:
    """Return True when the two values are equal."""
    return predicted == expected


def normalized_match(predicted: str | None, expected: str | None) -> bool:
    """
    Return True when the normalised strings are equal.

    Both ``None`` → True.  One ``None`` → False.
    """
    if predicted is None and expected is None:
        return True
    if predicted is None or expected is None:
        return False
    return _normalize(predicted) == _normalize(expected)


def nullable_exact(predicted: object, expected: object) -> bool:
    """
    Return True when values are equal or both absent.

    Identical to ``exact_match`` but explicit about the nullable intent so
    field-level logs are self-documenting.
    """
    return predicted == expected


# ---------------------------------------------------------------------------
# Metric accumulator
# ---------------------------------------------------------------------------

EVALUATED_FIELDS: tuple[str, ...] = (
    "report_id",
    "train_id",
    "location",
    "system",
    "component",
    "symptom",
    "severity",
    "service_impact",
)


@dataclass
class FieldResult:
    """Outcome for a single field in one prediction-label pair."""

    field_name: str
    predicted: object
    expected: object
    correct: bool


@dataclass
class RecordResult:
    """Aggregated results for one prediction-label pair."""

    report_id: str
    field_results: list[FieldResult] = field(default_factory=list)

    @property
    def correct_count(self) -> int:
        return sum(1 for r in self.field_results if r.correct)

    @property
    def total_count(self) -> int:
        return len(self.field_results)

    @property
    def accuracy(self) -> float:
        if self.total_count == 0:
            return 0.0
        return self.correct_count / self.total_count


@dataclass
class EvaluationMetrics:
    """Dataset-level aggregated metrics."""

    record_results: list[RecordResult] = field(default_factory=list)

    @property
    def total_fields(self) -> int:
        return sum(r.total_count for r in self.record_results)

    @property
    def correct_fields(self) -> int:
        return sum(r.correct_count for r in self.record_results)

    @property
    def overall_accuracy(self) -> float:
        if self.total_fields == 0:
            return 0.0
        return self.correct_fields / self.total_fields

    def per_field_accuracy(self) -> dict[str, float]:
        """Return accuracy per field name across all evaluated records."""
        totals: dict[str, int] = {}
        corrects: dict[str, int] = {}
        for record in self.record_results:
            for fr in record.field_results:
                totals[fr.field_name] = totals.get(fr.field_name, 0) + 1
                corrects[fr.field_name] = corrects.get(fr.field_name, 0) + (1 if fr.correct else 0)
        return {fname: corrects.get(fname, 0) / totals[fname] for fname in totals}
