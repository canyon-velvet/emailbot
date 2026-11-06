"""Run the `emailbot` command in-process and check only its output and exit code."""

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


def test_help_describes_emailbot_and_its_version_option():
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "It never sends email." in result.output
    assert "--version" in result.output
