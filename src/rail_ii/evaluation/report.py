"""
Plain-text and Markdown report generators for EvaluationMetrics.

Both renderers are pure functions: they accept an EvaluationMetrics instance
and return a string, making them trivially testable and composable.
"""

from __future__ import annotations

from rail_ii.evaluation.metrics import EvaluationMetrics


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def render_text(metrics: EvaluationMetrics) -> str:
    """
    Render a compact plain-text evaluation summary.

    Example output::

        Evaluation Summary
        ==================
        Records evaluated : 10
        Fields evaluated  : 80
        Correct fields    : 42
        Overall accuracy  : 52.5%

        Per-field accuracy
        ------------------
        report_id       : 100.0%
        train_id        :  60.0%
        ...

        Per-record breakdown
        --------------------
        SR001  5 / 8  (62.5%)
        ...
    """
    lines: list[str] = []

    n_records = len(metrics.record_results)
    lines += [
        "Evaluation Summary",
        "==================",
        f"Records evaluated : {n_records}",
        f"Fields evaluated  : {metrics.total_fields}",
        f"Correct fields    : {metrics.correct_fields}",
        f"Overall accuracy  : {_pct(metrics.overall_accuracy)}",
        "",
    ]

    per_field = metrics.per_field_accuracy()
    if per_field:
        lines += ["Per-field accuracy", "------------------"]
        col_w = max(len(k) for k in per_field) + 2
        for fname, acc in per_field.items():
            lines.append(f"{fname:<{col_w}}: {_pct(acc):>7}")
        lines.append("")

    if metrics.record_results:
        lines += ["Per-record breakdown", "--------------------"]
        for rr in metrics.record_results:
            lines.append(
                f"{rr.report_id:<10}  {rr.correct_count} / {rr.total_count}  ({_pct(rr.accuracy)})"
            )

    return "\n".join(lines)


def render_markdown(metrics: EvaluationMetrics) -> str:
    """
    Render a Markdown evaluation summary suitable for GitHub PR comments or
    documentation.
    """
    lines: list[str] = []

    n_records = len(metrics.record_results)
    lines += [
        "## Evaluation Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Records evaluated | {n_records} |",
        f"| Fields evaluated | {metrics.total_fields} |",
        f"| Correct fields | {metrics.correct_fields} |",
        f"| **Overall accuracy** | **{_pct(metrics.overall_accuracy)}** |",
        "",
    ]

    per_field = metrics.per_field_accuracy()
    if per_field:
        lines += [
            "### Per-field accuracy",
            "",
            "| Field | Accuracy |",
            "|-------|----------|",
        ]
        for fname, acc in per_field.items():
            lines.append(f"| {fname} | {_pct(acc)} |")
        lines.append("")

    if metrics.record_results:
        lines += [
            "### Per-record breakdown",
            "",
            "| Report | Correct | Total | Accuracy |",
            "|--------|---------|-------|----------|",
        ]
        for rr in metrics.record_results:
            lines.append(
                f"| {rr.report_id} | {rr.correct_count} | {rr.total_count} | {_pct(rr.accuracy)} |"
            )

    return "\n".join(lines)
