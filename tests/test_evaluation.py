"""Tests for the evaluation pipeline."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

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
from rail_ii.schema.incident import IncidentRecord, IncidentSeverity, IncidentSystem

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_record(**kwargs) -> IncidentRecord:
    defaults = {
        "report_id": "SR000",
        "symptom": "unknown issue",
        "system": IncidentSystem.UNKNOWN,
        "severity": IncidentSeverity.UNKNOWN,
    }
    defaults.update(kwargs)
    return IncidentRecord(**defaults)


# ---------------------------------------------------------------------------
# exact_match
# ---------------------------------------------------------------------------


class TestExactMatch:
    def test_equal_strings(self) -> None:
        assert exact_match("doors", "doors") is True

    def test_unequal_strings(self) -> None:
        assert exact_match("brakes", "doors") is False

    def test_equal_enums(self) -> None:
        assert exact_match(IncidentSystem.DOORS, IncidentSystem.DOORS) is True

    def test_unequal_enums(self) -> None:
        assert exact_match(IncidentSystem.DOORS, IncidentSystem.BRAKES) is False

    def test_both_none(self) -> None:
        assert exact_match(None, None) is True

    def test_one_none(self) -> None:
        assert exact_match(None, "something") is False
        assert exact_match("something", None) is False


# ---------------------------------------------------------------------------
# normalized_match
# ---------------------------------------------------------------------------


class TestNormalizedMatch:
    def test_same_string(self) -> None:
        assert normalized_match("Brake Fault", "Brake Fault") is True

    def test_case_insensitive(self) -> None:
        assert normalized_match("Brake Fault", "brake fault") is True

    def test_extra_whitespace(self) -> None:
        assert normalized_match("brake   fault", "brake fault") is True

    def test_leading_trailing_whitespace(self) -> None:
        assert normalized_match("  brake fault  ", "brake fault") is True

    def test_different_strings(self) -> None:
        assert normalized_match("brake fault", "door fault") is False

    def test_both_none(self) -> None:
        assert normalized_match(None, None) is True

    def test_predicted_none(self) -> None:
        assert normalized_match(None, "brake fault") is False

    def test_expected_none(self) -> None:
        assert normalized_match("brake fault", None) is False


# ---------------------------------------------------------------------------
# nullable_exact
# ---------------------------------------------------------------------------


class TestNullableExact:
    def test_both_none(self) -> None:
        assert nullable_exact(None, None) is True

    def test_matching_values(self) -> None:
        assert nullable_exact("TR-100", "TR-100") is True

    def test_mismatched_values(self) -> None:
        assert nullable_exact("TR-100", "TR-200") is False

    def test_one_none(self) -> None:
        assert nullable_exact(None, "TR-100") is False
        assert nullable_exact("TR-100", None) is False


# ---------------------------------------------------------------------------
# RecordResult / EvaluationMetrics
# ---------------------------------------------------------------------------


class TestRecordResult:
    def _make_record_result(self, corrects: list[bool]) -> RecordResult:
        rr = RecordResult(report_id="SR001")
        for i, c in enumerate(corrects):
            rr.field_results.append(
                FieldResult(
                    field_name=f"field_{i}",
                    predicted="a",
                    expected="a" if c else "b",
                    correct=c,
                )
            )
        return rr

    def test_accuracy_all_correct(self) -> None:
        rr = self._make_record_result([True, True, True])
        assert rr.accuracy == 1.0

    def test_accuracy_none_correct(self) -> None:
        rr = self._make_record_result([False, False])
        assert rr.accuracy == 0.0

    def test_accuracy_partial(self) -> None:
        rr = self._make_record_result([True, False, True, False])
        assert rr.accuracy == 0.5

    def test_empty_record_result_accuracy(self) -> None:
        rr = RecordResult(report_id="SRX")
        assert rr.accuracy == 0.0


class TestEvaluationMetrics:
    def _build_metrics(self, per_record_corrects: list[list[bool]]) -> EvaluationMetrics:
        m = EvaluationMetrics()
        for i, corrects in enumerate(per_record_corrects):
            rr = RecordResult(report_id=f"SR{i:03d}")
            for j, c in enumerate(corrects):
                rr.field_results.append(
                    FieldResult(
                        field_name=f"field_{j}",
                        predicted="x",
                        expected="x" if c else "y",
                        correct=c,
                    )
                )
            m.record_results.append(rr)
        return m

    def test_overall_accuracy_perfect(self) -> None:
        m = self._build_metrics([[True, True], [True, True]])
        assert m.overall_accuracy == 1.0

    def test_overall_accuracy_zero(self) -> None:
        m = self._build_metrics([[False, False], [False]])
        assert m.overall_accuracy == 0.0

    def test_overall_accuracy_partial(self) -> None:
        m = self._build_metrics([[True, False], [True, True]])
        assert m.total_fields == 4
        assert m.correct_fields == 3
        assert m.overall_accuracy == pytest.approx(0.75)

    def test_per_field_accuracy(self) -> None:
        m = EvaluationMetrics()
        rr1 = RecordResult(report_id="SR001")
        rr1.field_results.append(
            FieldResult(field_name="system", predicted="doors", expected="doors", correct=True)
        )
        rr1.field_results.append(
            FieldResult(field_name="severity", predicted="high", expected="low", correct=False)
        )
        rr2 = RecordResult(report_id="SR002")
        rr2.field_results.append(
            FieldResult(field_name="system", predicted="brakes", expected="brakes", correct=True)
        )
        rr2.field_results.append(
            FieldResult(field_name="severity", predicted="low", expected="low", correct=True)
        )
        m.record_results.extend([rr1, rr2])

        pfa = m.per_field_accuracy()
        assert pfa["system"] == 1.0
        assert pfa["severity"] == pytest.approx(0.5)

    def test_empty_metrics(self) -> None:
        m = EvaluationMetrics()
        assert m.total_fields == 0
        assert m.correct_fields == 0
        assert m.overall_accuracy == 0.0
        assert m.per_field_accuracy() == {}


# ---------------------------------------------------------------------------
# compare_records
# ---------------------------------------------------------------------------


class TestCompareRecords:
    def test_perfect_match(self) -> None:
        rec = _make_record(
            report_id="SR001",
            train_id="TR-100",
            system=IncidentSystem.DOORS,
            severity=IncidentSeverity.HIGH,
            symptom="door fault",
        )
        result = compare_records(rec, rec)
        assert result.accuracy == 1.0

    def test_system_mismatch(self) -> None:
        predicted = _make_record(report_id="SR001", system=IncidentSystem.BRAKES)
        expected = _make_record(report_id="SR001", system=IncidentSystem.DOORS)
        result = compare_records(predicted, expected)
        system_fr = next(fr for fr in result.field_results if fr.field_name == "system")
        assert system_fr.correct is False

    def test_train_id_both_none_counts_correct(self) -> None:
        predicted = _make_record(report_id="SR001", train_id=None)
        expected = _make_record(report_id="SR001", train_id=None)
        result = compare_records(predicted, expected)
        tid_fr = next(fr for fr in result.field_results if fr.field_name == "train_id")
        assert tid_fr.correct is True

    def test_symptom_normalized_match(self) -> None:
        predicted = _make_record(symptom="  Brake   Fault  ")
        expected = _make_record(symptom="brake fault")
        result = compare_records(predicted, expected)
        symptom_fr = next(fr for fr in result.field_results if fr.field_name == "symptom")
        assert symptom_fr.correct is True

    def test_all_evaluated_fields_present(self) -> None:
        from rail_ii.evaluation.metrics import EVALUATED_FIELDS

        rec = _make_record()
        result = compare_records(rec, rec)
        evaluated = {fr.field_name for fr in result.field_results}
        assert evaluated == set(EVALUATED_FIELDS)


# ---------------------------------------------------------------------------
# load_label
# ---------------------------------------------------------------------------


class TestLoadLabel:
    def test_load_valid_label(self, tmp_path: Path) -> None:
        label_data = {
            "report_id": "SR001",
            "symptom": "door fault",
            "system": "doors",
            "severity": "high",
            "train_id": "TR-452",
            "location": "Central Facility",
        }
        label_file = tmp_path / "SR001.json"
        label_file.write_text(json.dumps(label_data), encoding="utf-8")

        record = load_label(label_file)
        assert record.report_id == "SR001"
        assert record.system == IncidentSystem.DOORS
        assert record.severity == IncidentSeverity.HIGH
        assert record.train_id == "TR-452"

    def test_load_label_with_nulls(self, tmp_path: Path) -> None:
        label_data = {
            "report_id": "SR002",
            "symptom": "brake failure",
            "system": "brakes",
            "severity": "high",
            "train_id": None,
            "location": None,
        }
        label_file = tmp_path / "SR002.json"
        label_file.write_text(json.dumps(label_data), encoding="utf-8")

        record = load_label(label_file)
        assert record.train_id is None
        assert record.location is None


# ---------------------------------------------------------------------------
# run_evaluation (integration)
# ---------------------------------------------------------------------------


class TestRunEvaluation:
    def test_run_evaluation_with_synthetic_data(self) -> None:
        """Integration test using the real synthetic dataset."""
        repo_root = Path(__file__).parent.parent
        reports_dir = repo_root / "data" / "synthetic" / "reports"
        labels_dir = repo_root / "data" / "synthetic" / "labels"

        if not reports_dir.exists() or not labels_dir.exists():
            pytest.skip("Synthetic data not available")

        metrics = run_evaluation(reports_dir=reports_dir, labels_dir=labels_dir)

        assert len(metrics.record_results) > 0
        assert metrics.total_fields > 0
        assert 0.0 <= metrics.overall_accuracy <= 1.0
        per_field = metrics.per_field_accuracy()
        assert "system" in per_field
        assert "severity" in per_field

    def test_run_evaluation_skips_unlabelled_reports(self, tmp_path: Path) -> None:
        """Reports without a matching label file are skipped silently."""
        reports_dir = tmp_path / "reports"
        labels_dir = tmp_path / "labels"
        reports_dir.mkdir()
        labels_dir.mkdir()

        # Write a report with no matching label
        (reports_dir / "SR_ORPHAN.txt").write_text("Brake failure on unit TR-10.", encoding="utf-8")

        metrics = run_evaluation(reports_dir=reports_dir, labels_dir=labels_dir)
        assert len(metrics.record_results) == 0

    def test_run_evaluation_empty_dirs(self, tmp_path: Path) -> None:
        reports_dir = tmp_path / "reports"
        labels_dir = tmp_path / "labels"
        reports_dir.mkdir()
        labels_dir.mkdir()

        metrics = run_evaluation(reports_dir=reports_dir, labels_dir=labels_dir)
        assert metrics.total_fields == 0
        assert metrics.overall_accuracy == 0.0


# ---------------------------------------------------------------------------
# render_text / render_markdown
# ---------------------------------------------------------------------------


class TestRenderText:
    def _simple_metrics(self) -> EvaluationMetrics:
        m = EvaluationMetrics()
        rr = RecordResult(report_id="SR001")
        rr.field_results.append(
            FieldResult(field_name="system", predicted="doors", expected="doors", correct=True)
        )
        rr.field_results.append(
            FieldResult(field_name="severity", predicted="high", expected="low", correct=False)
        )
        m.record_results.append(rr)
        return m

    def test_render_text_contains_summary(self) -> None:
        text = render_text(self._simple_metrics())
        assert "Evaluation Summary" in text
        assert "Records evaluated" in text
        assert "Overall accuracy" in text

    def test_render_text_contains_per_field(self) -> None:
        text = render_text(self._simple_metrics())
        assert "system" in text
        assert "severity" in text

    def test_render_text_contains_per_record(self) -> None:
        text = render_text(self._simple_metrics())
        assert "SR001" in text

    def test_render_text_empty_metrics(self) -> None:
        text = render_text(EvaluationMetrics())
        assert "0" in text  # zero fields


class TestRenderMarkdown:
    def _simple_metrics(self) -> EvaluationMetrics:
        m = EvaluationMetrics()
        rr = RecordResult(report_id="SR001")
        rr.field_results.append(
            FieldResult(field_name="system", predicted="doors", expected="doors", correct=True)
        )
        m.record_results.append(rr)
        return m

    def test_render_markdown_has_headings(self) -> None:
        md = render_markdown(self._simple_metrics())
        assert "## Evaluation Summary" in md

    def test_render_markdown_has_tables(self) -> None:
        md = render_markdown(self._simple_metrics())
        assert "|" in md

    def test_render_markdown_has_record_row(self) -> None:
        md = render_markdown(self._simple_metrics())
        assert "SR001" in md
