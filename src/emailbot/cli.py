"""The `emailbot` command-line interface."""

from importlib.metadata import version
from typing import Annotated

import typer

# No shell-completion options: `--install-completion` edits the user's shell config.
app = typer.Typer(no_args_is_help=True, add_completion=False)


def _print_version(requested: bool) -> None:
    if requested:
        typer.echo(f"emailbot {version('emailbot')}")
        raise typer.Exit()


@app.callback()
def main(
    show_version: Annotated[
        bool,
        typer.Option(
            "--version",
            help="Show the installed version and exit.",
            callback=_print_version,
            is_eager=True,
        ),
    ] = False,
) -> None:
    """A security-first email assistant for Gmail. It never sends email."""
