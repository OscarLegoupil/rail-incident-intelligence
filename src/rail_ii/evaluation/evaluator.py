"""
Evaluation pipeline: load reports → extract → compare against labels.

Usage::

    from pathlib import Path
    from rail_ii.evaluation.evaluator import run_evaluation

    metrics = run_evaluation(
        reports_dir=Path("data/synthetic/reports"),
        labels_dir=Path("data/synthetic/labels"),
    )
"""

from __future__ import annotations

import json
from pathlib import Path

from rail_ii.evaluation.metrics import (
    EVALUATED_FIELDS,
    EvaluationMetrics,
    FieldResult,
    RecordResult,
    exact_match,
    normalized_match,
    nullable_exact,
)
from rail_ii.extraction.baseline import extract_baseline
from rail_ii.ingestion import TxtLoader
from rail_ii.schema.incident import IncidentRecord

# Which comparison function to apply per field
_FIELD_COMPARATORS = {
    "report_id": exact_match,
    "train_id": nullable_exact,
    "location": normalized_match,
    "system": exact_match,
    "component": normalized_match,
    "symptom": normalized_match,
    "severity": exact_match,
    "service_impact": normalized_match,
}


def compare_records(predicted: IncidentRecord, expected: IncidentRecord) -> RecordResult:
    """
    Compare a predicted record against a ground-truth label record.

    Only fields listed in ``EVALUATED_FIELDS`` are evaluated; metadata fields
    (confidence, source_text, source_spans) are intentionally excluded.
    """
    result = RecordResult(report_id=predicted.report_id)
    for fname in EVALUATED_FIELDS:
        pred_val = getattr(predicted, fname)
        exp_val = getattr(expected, fname)
        comparator = _FIELD_COMPARATORS[fname]
        correct = comparator(pred_val, exp_val)
        result.field_results.append(
            FieldResult(
                field_name=fname,
                predicted=pred_val,
                expected=exp_val,
                correct=correct,
            )
        )
    return result


def load_label(label_path: Path) -> IncidentRecord:
    """Parse a JSON label file into an IncidentRecord."""
    data = json.loads(label_path.read_text(encoding="utf-8"))
    return IncidentRecord.model_validate(data)


def run_evaluation(
    reports_dir: Path,
    labels_dir: Path,
) -> EvaluationMetrics:
    """
    Run end-to-end evaluation over every report that has a matching label.

    Reports without a corresponding label file are silently skipped so the
    pipeline is robust to partially labelled datasets.

    Args:
        reports_dir: Directory containing ``.txt`` report files.
        labels_dir:  Directory containing ``.json`` label files.

    Returns:
        An :class:`EvaluationMetrics` instance covering all evaluated records.
    """
    metrics = EvaluationMetrics()

    for report_path in sorted(reports_dir.glob("*.txt")):
        label_path = labels_dir / f"{report_path.stem}.json"
        if not label_path.exists():
            continue

        document = TxtLoader.load(report_path)
        predicted = extract_baseline(document)
        expected = load_label(label_path)

        record_result = compare_records(predicted, expected)
        metrics.record_results.append(record_result)

    return metrics
