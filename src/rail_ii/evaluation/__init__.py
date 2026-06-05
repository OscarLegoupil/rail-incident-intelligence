"""Evaluation module."""

from __future__ import annotations

from rail_ii.evaluation.evaluator import compare_records, load_label, run_evaluation
from rail_ii.evaluation.metrics import (
    EvaluationMetrics,
    FieldResult,
    RecordResult,
    exact_match,
    normalized_match,
    nullable_exact,
)
from rail_ii.evaluation.report import render_markdown, render_text

__all__ = [
    "EvaluationMetrics",
    "FieldResult",
    "RecordResult",
    "compare_records",
    "exact_match",
    "load_label",
    "normalized_match",
    "nullable_exact",
    "render_markdown",
    "render_text",
    "run_evaluation",
]
