"""The `emailbot` command-line interface."""

import contextlib
from importlib.metadata import version
from pathlib import Path
from typing import Annotated

import typer

from emailbot import config

app = typer.Typer(
    no_args_is_help=True,
    # `--install-completion` would edit the user's shell config.
    add_completion=False,
    # Plain help text: Rich formatting forces ANSI colours in CI.
    rich_markup_mode=None,
    # Standard tracebacks: Typer's pretty ones print local variables, which can
    # include secrets.
    pretty_exceptions_enable=False,
)
config_app = typer.Typer(
    no_args_is_help=True,
    # Each Typer app has its own help format, so this one needs plain text too.
    rich_markup_mode=None,
)
app.add_typer(config_app, name="config", help="See and check the config file.")


def _print_version(requested: bool) -> None:
    if requested:
        typer.echo(f"emailbot {version('emailbot')}")
        raise typer.Exit()


@app.callback()
def main(
    ctx: typer.Context,
    config_path: Annotated[
        Path | None,
        typer.Option("--config", help="Use this config file instead of the default."),
    ] = None,
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
    path = config_path or Path(typer.get_app_dir("emailbot")) / "config.yaml"
    # Expand a `~` the shell left alone (e.g. quoted). Like a shell, keep `~name`
    # as it is when there's no such user.
    with contextlib.suppress(RuntimeError):
        path = path.expanduser()
    ctx.obj = path.absolute()


@config_app.command("path")
def show_path(ctx: typer.Context) -> None:
    """Show which config file emailbot uses."""
    typer.echo(ctx.obj)


@config_app.command("check")
def check(ctx: typer.Context) -> None:
    """Check the config file and explain any problems."""
    path: Path = ctx.obj
    try:
        settings = config.load(path)
    except config.ConfigError as error:
        typer.echo(error, err=True)
        raise typer.Exit(1) from None
    summary = (
        f"mode: {settings.mode}, accounts: {len(settings.accounts)}, "
        f"secrets: {settings.secrets.backend}"
    )
    typer.echo(f"Config OK: {path} ({summary})")
