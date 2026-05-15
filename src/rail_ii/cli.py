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


if __name__ == "__main__":
    app()
