"""Command-line interface powered by Typer."""

from pathlib import Path
from typing import Annotated

import typer

from rail_ii import __version__

app = typer.Typer(
    name="rail-ii",
    help="Rail Incident Intelligence - extract structured data from rail operator reports.",
    no_args_is_help=True,
)


@app.command()
def version() -> None:
    """Print the current version."""
    typer.echo(f"rail-ii {__version__}")


@app.command()
def extract(
    source: Annotated[Path, typer.Argument(help="Path to the operator report file.")],
) -> None:
    """Extract incidents from a report file."""
    from rail_ii.pipeline import extract_incidents

    typer.echo(f"Extracting incidents from {source} ...")
    incidents = extract_incidents(source)
    typer.echo(f"Extracted {len(incidents)} incident(s).")


@app.command()
def evaluate(
    reports_dir: Annotated[
        Path,
        typer.Option("--reports-dir", help="Directory containing .txt report files."),
    ] = Path("data/synthetic/reports"),
    labels_dir: Annotated[
        Path,
        typer.Option("--labels-dir", help="Directory containing .json label files."),
    ] = Path("data/synthetic/labels"),
    fmt: Annotated[
        str,
        typer.Option("--format", help="Output format: text or markdown."),
    ] = "text",
    extractor_name: Annotated[
        str,
        typer.Option(
            "--extractor",
            help="Which extractor to evaluate: 'baseline' or 'llm'.",
        ),
    ] = "baseline",
) -> None:
    """Evaluate an extractor against labelled ground-truth data."""
    from rail_ii.evaluation.evaluator import run_evaluation
    from rail_ii.evaluation.report import render_markdown, render_text

    extractor = _resolve_extractor(extractor_name)
    metrics = run_evaluation(
        reports_dir=reports_dir,
        labels_dir=labels_dir,
        extractor=extractor,
    )

    if fmt == "markdown":
        typer.echo(render_markdown(metrics))
    else:
        typer.echo(render_text(metrics))


def _resolve_extractor(name: str):
    """Map a CLI extractor name to a callable Document -> IncidentRecord."""
    from rail_ii.extraction.baseline import extract_baseline

    if name == "baseline":
        return extract_baseline

    if name == "llm":
        from rail_ii.config import settings
        from rail_ii.extraction.llm_extractor import extract_with_llm
        from rail_ii.extraction.openai_client import make_openai_client
        from rail_ii.schema.incident import IncidentRecord, IncidentSystem

        if settings.openai_api_key is None:
            raise typer.BadParameter("RAIL_II_OPENAI_API_KEY is not set. Add it to your .env file.")

        client = make_openai_client(
            api_key=settings.openai_api_key.get_secret_value(),
            model=settings.openai_model,
        )

        def llm_extractor(document):
            result = extract_with_llm(document, client)
            if result.record is not None:
                return result.record
            # Evaluation needs a valid IncidentRecord even on failure; emit a
            # minimal record that scores as a miss on every field.
            return IncidentRecord(
                report_id=document.document_id,
                symptom=f"[llm extraction failed: {result.error}]",
                system=IncidentSystem.UNKNOWN,
            )

        return llm_extractor

    raise typer.BadParameter(f"Unknown extractor: {name!r}. Use 'baseline' or 'llm'.")


@app.command()
def inspect(
    report_id: Annotated[
        str,
        typer.Argument(help="Report id or filename stem, e.g. 'SR001'."),
    ],
    reports_dir: Annotated[
        Path,
        typer.Option("--reports-dir", help="Directory containing .txt report files."),
    ] = Path("data/synthetic/reports"),
    labels_dir: Annotated[
        Path,
        typer.Option("--labels-dir", help="Directory containing .json label files."),
    ] = Path("data/synthetic/labels"),
    extractor_name: Annotated[
        str,
        typer.Option("--extractor", help="'baseline' or 'llm'."),
    ] = "llm",
    show_prompt: Annotated[
        bool,
        typer.Option(
            "--show-prompt/--no-show-prompt",
            help="Include the full system + user prompt.",
        ),
    ] = False,
) -> None:
    """Run one report through an extractor and dump everything: prompt, raw
    response, parsed record, expected label, per-field diff.

    Use this to diagnose why the LLM extractor disagrees with the labels.
    """
    from rail_ii.evaluation.evaluator import load_label
    from rail_ii.ingestion import TxtLoader

    report_path = reports_dir / f"{report_id}.txt"
    label_path = labels_dir / f"{report_id}.json"
    if not report_path.exists():
        raise typer.BadParameter(f"Report not found: {report_path}")

    document = TxtLoader.load(report_path)
    expected = load_label(label_path) if label_path.exists() else None

    typer.echo(f"=== Report: {report_path} ===")
    typer.echo(document.normalized_text)
    typer.echo("")

    if extractor_name == "llm":
        _inspect_llm(document, expected, show_prompt=show_prompt)
    else:
        extractor = _resolve_extractor(extractor_name)
        predicted = extractor(document)
        _dump_records_and_diff(predicted, expected)


def _inspect_llm(document, expected, *, show_prompt: bool) -> None:
    from rail_ii.config import settings
    from rail_ii.extraction.llm_extractor import extract_with_llm
    from rail_ii.extraction.openai_client import make_openai_client
    from rail_ii.extraction.prompts import SYSTEM_PROMPT, build_user_prompt

    if settings.openai_api_key is None:
        raise typer.BadParameter("RAIL_II_OPENAI_API_KEY is not set. Add it to your .env file.")

    user_prompt = build_user_prompt(document)
    if show_prompt:
        typer.echo("=== System prompt ===")
        typer.echo(SYSTEM_PROMPT)
        typer.echo("")
        typer.echo("=== User prompt ===")
        typer.echo(user_prompt)
        typer.echo("")

    client = make_openai_client(
        api_key=settings.openai_api_key.get_secret_value(),
        model=settings.openai_model,
    )
    result = extract_with_llm(document, client)

    typer.echo(f"=== Raw LLM response (model={settings.openai_model}) ===")
    typer.echo(result.raw_response or "<empty>")
    typer.echo("")

    if result.error:
        typer.echo(f"=== Extraction error ===\n{result.error}\n")
        return

    _dump_records_and_diff(result.record, expected)


def _dump_records_and_diff(predicted, expected) -> None:
    from rail_ii.evaluation.evaluator import compare_records

    typer.echo("=== Parsed record (predicted) ===")
    typer.echo(predicted.model_dump_json(indent=2))
    typer.echo("")

    if expected is None:
        typer.echo("(no label file found — skipping diff)")
        return

    typer.echo("=== Expected label ===")
    typer.echo(expected.model_dump_json(indent=2))
    typer.echo("")

    typer.echo("=== Per-field diff ===")
    record_result = compare_records(predicted, expected)
    for fr in record_result.field_results:
        mark = "OK  " if fr.correct else "MISS"
        typer.echo(f"[{mark}] {fr.field_name}")
        if not fr.correct:
            typer.echo(f"       predicted: {fr.predicted!r}")
            typer.echo(f"       expected:  {fr.expected!r}")
    typer.echo("")
    typer.echo(f"Accuracy: {record_result.correct_count}/{record_result.total_count}")


if __name__ == "__main__":
    app()
