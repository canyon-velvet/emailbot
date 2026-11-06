"""The top-level `emailbot` command, run in-process (Seam 1)."""

import tomllib
from pathlib import Path

from typer.testing import CliRunner

from emailbot.cli import app

runner = CliRunner()


def declared_version() -> str:
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    return tomllib.loads(pyproject.read_text())["project"]["version"]


def test_version_prints_the_declared_version():
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.output.strip() == f"emailbot {declared_version()}"


def test_help_shows_usage_and_the_version_option():
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Usage:" in result.output
    assert "--version" in result.output
