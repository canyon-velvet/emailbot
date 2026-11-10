"""The `emailbot` command-line interface."""

import contextlib
from collections.abc import Iterator
from importlib.metadata import version
from pathlib import Path
from typing import Annotated, NoReturn

import typer

from emailbot import config, secret_store

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
secrets_app = typer.Typer(no_args_is_help=True, rich_markup_mode=None)
app.add_typer(
    secrets_app,
    name="secrets",
    help="Store, check and remove secrets, such as LLM API keys.",
)

SecretName = Annotated[
    str,
    typer.Argument(help="The secret's name, such as llm:openai.", show_default=False),
]


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


@contextlib.contextmanager
def _explain_problems() -> Iterator[None]:
    """Turn a config or secret problem into its message and exit status 1."""
    try:
        yield
    except (config.ConfigError, secret_store.SecretStoreError) as error:
        _fail(str(error))


def _fail(message: str) -> NoReturn:
    typer.echo(message, err=True)
    raise typer.Exit(1)


def _store(ctx: typer.Context) -> secret_store.Keychain:
    path: Path = ctx.obj
    # With no config file yet, every setting has its default.
    settings = config.load(path) if path.exists() else config.Config()
    return secret_store.open_store(settings.secrets)


def _ask_hidden(text: str) -> str:
    return typer.prompt(text, hide_input=True, default="", show_default=False)


# Extra arguments are refused here: Click's own error would print them.
@secrets_app.command("set", context_settings={"allow_extra_args": True})
def set_secret(ctx: typer.Context, name: SecretName) -> None:
    """Store a secret. It asks for the value twice, without showing it."""
    if ctx.args:
        typer.echo(
            "secrets set takes only a name. It asks for the value, so the value "
            "doesn't end up in your shell history.",
            err=True,
        )
        raise typer.Exit(2)
    with _explain_problems():
        secret_store.check_name(name)  # before the user types the value
        store = _store(ctx)
        value = _ask_hidden(f"Value for {name}")
        if not value.strip():
            _fail("No value entered; nothing was stored.")
        if _ask_hidden("Enter it again") != value:
            _fail("The two values don't match; nothing was stored.")
        store.set(name, value)
    typer.echo(f"Stored {name} in the keychain.")


@secrets_app.command("status")
def status(ctx: typer.Context, name: SecretName) -> None:
    """Say whether a secret is set, without showing it."""
    with _explain_problems():
        is_set = _store(ctx).exists(name)
    typer.echo("set" if is_set else "not set")


@secrets_app.command("delete")
def remove_secret(ctx: typer.Context, name: SecretName) -> None:
    """Remove a secret."""
    with _explain_problems():
        removed = _store(ctx).remove(name)
    typer.echo(f"Removed {name}." if removed else f"{name} wasn't set.")
