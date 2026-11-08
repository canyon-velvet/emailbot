"""Run `emailbot config ...` in-process and check only its output and exit code."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from emailbot.cli import app

runner = CliRunner()


def write(tmp_path, text):
    path = tmp_path / "config.yaml"
    path.write_text(text)
    return path


def check(path):
    return runner.invoke(app, ["--config", str(path), "config", "check"])


def test_config_path_prints_the_file_given_with_config(tmp_path):
    path = tmp_path / "my.yaml"

    result = runner.invoke(app, ["--config", str(path), "config", "path"])

    assert result.exit_code == 0
    assert result.stdout == f"{path}\n"


def test_config_path_makes_a_relative_config_absolute(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["--config", "my.yaml", "config", "path"])

    assert result.stdout == f"{tmp_path / 'my.yaml'}\n"


def test_config_path_expands_a_tilde_the_shell_left_alone(home):
    result = runner.invoke(app, ["--config", "~/my.yaml", "config", "path"])

    assert result.stdout == f"{home / 'my.yaml'}\n"


def test_config_path_defaults_to_the_os_config_folder(home):
    result = runner.invoke(app, ["config", "path"])

    path = Path(result.stdout.strip())
    assert result.exit_code == 0
    assert path.is_relative_to(home)
    assert path.parts[-2:] == ("emailbot", "config.yaml")


def test_check_accepts_a_valid_config(tmp_path):
    path = write(
        tmp_path,
        "mode: live\n"
        "accounts: [me@gmail.com, o'brien+news@my-company.co.uk]\n"
        "secrets: {backend: 1password, vault: Family}\n",
    )

    result = check(path)

    assert result.exit_code == 0
    assert result.stdout == (
        f"Config OK: {path} (mode: live, accounts: 2, secrets: 1password)\n"
    )


@pytest.mark.parametrize("text", ["", "mode:\naccounts:\nsecrets:\n"])
def test_check_uses_the_defaults_for_missing_or_empty_settings(tmp_path, text):
    path = write(tmp_path, text)

    result = check(path)

    assert result.exit_code == 0
    assert result.stdout == (
        f"Config OK: {path} (mode: shadow, accounts: 0, secrets: keychain)\n"
    )


def test_check_reports_unknown_settings_with_their_dotted_path(tmp_path):
    path = write(tmp_path, "mdoe: live\nsecrets: {backnd: keychain}\n")

    result = check(path)

    assert result.exit_code == 1
    assert result.stderr == (
        f"{path} has 2 problems:\n"
        "  secrets.backnd: unknown setting\n"
        "  mdoe: unknown setting\n"
    )


def test_check_escapes_control_characters_in_setting_names(tmp_path):
    path = write(tmp_path, '"k\\e]0;PWNED\\a": 1\n')

    result = check(path)

    assert result.stderr == (
        f"{path} has 1 problem:\n  'k\\x1b]0;PWNED\\x07': unknown setting\n"
    )


def test_check_reports_invalid_values_with_their_dotted_path(tmp_path):
    path = write(tmp_path, "mode: production\n")

    result = check(path)

    assert result.exit_code == 1
    assert result.stderr == (
        f"{path} has 1 problem:\n  mode: Input should be 'shadow' or 'live'\n"
    )


@pytest.mark.parametrize(
    "address",
    [
        "not-an-address",
        "<me@gmail.com>",
        "me@gmail..com",
        "me@-gmail.com",
        "me@gmail.com.",
        "../me@gmail.com",
        "me@gmail.com​",  # a zero-width space
    ],
)
def test_check_rejects_an_invalid_account_address(tmp_path, address):
    path = write(tmp_path, f"accounts: [{json.dumps(address)}]\n")

    result = check(path)

    assert result.exit_code == 1
    assert result.stderr == (
        f"{path} has 1 problem:\n"
        f"  accounts.0: {address!r} isn't a valid email address\n"
    )


def test_check_rejects_the_same_account_twice_whatever_its_case(tmp_path):
    path = write(tmp_path, "accounts: [me@gmail.com, Me@Gmail.com]\n")

    result = check(path)

    assert result.exit_code == 1
    assert result.stderr == (
        f"{path} has 1 problem:\n  accounts: 'Me@Gmail.com' is listed more than once\n"
    )


@pytest.mark.parametrize(
    ("secrets", "problem"),
    [
        ("{backend: 1password}", "required when the backend is 1password"),
        ("{backend: 1password, vault: '  '}", "required when the backend is 1password"),
        ("{vault: Family}", "only used when the backend is 1password"),
    ],
)
def test_check_requires_a_vault_with_1password_and_only_then(
    tmp_path, secrets, problem
):
    path = write(tmp_path, f"secrets: {secrets}\n")

    result = check(path)

    assert result.exit_code == 1
    assert result.stderr == f"{path} has 1 problem:\n  secrets.vault: {problem}\n"


def test_check_explains_a_value_that_should_be_a_group_of_settings(tmp_path):
    path = write(tmp_path, "secrets: keychain\n")

    result = check(path)

    assert result.exit_code == 1
    assert result.stderr == (
        f"{path} has 1 problem:\n"
        "  secrets: should be a group of `name: value` settings\n"
    )


def test_check_rejects_a_file_that_is_not_a_group_of_settings(tmp_path):
    path = write(tmp_path, "- live\n")

    result = check(path)

    assert result.exit_code == 1
    assert result.stderr == (
        f"{path} has 1 problem:\n"
        "  (whole file): should be a group of `name: value` settings\n"
    )


def test_check_rejects_a_setting_given_twice(tmp_path):
    path = write(tmp_path, "mode: shadow\naccounts: []\nmode: live\n")

    result = check(path)

    assert result.exit_code == 1
    assert result.stderr == (
        f"{path} isn't valid YAML at line 3, column 1: 'mode' is set more than once\n"
    )


def test_check_reports_yaml_syntax_errors_with_line_and_column(tmp_path):
    path = write(tmp_path, "mode: shadow\n  bad: indent\n")

    result = check(path)

    assert result.exit_code == 1
    assert result.stderr == (
        f"{path} isn't valid YAML at line 2, column 6: "
        "mapping values are not allowed here\n"
    )


def test_check_never_runs_python_tags_in_yaml(tmp_path):
    path = write(tmp_path, "mode: !!python/object/apply:os.getcwd []\n")

    result = check(path)

    assert result.exit_code == 1
    assert result.stderr.startswith(f"{path} isn't valid YAML at line 1, column 7: ")


def test_check_reports_a_file_nested_too_deeply(tmp_path):
    path = write(tmp_path, "[" * 3000 + "]" * 3000)

    result = check(path)

    assert result.exit_code == 1
    assert result.stderr == f"{path} is nested too deeply to read\n"


def test_check_reports_bytes_that_are_not_text(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_bytes(b"mode: \xff\n")

    result = check(path)

    assert result.exit_code == 1
    assert result.stderr == (
        f"{path} isn't valid YAML: unreadable or disallowed character at position 7\n"
    )


def test_check_reports_where_it_looked_for_a_missing_file(tmp_path):
    path = tmp_path / "missing.yaml"

    result = check(path)

    assert result.exit_code == 1
    assert result.stderr == (
        f"No config file at {path}. Create one, or pass --config PATH.\n"
    )


def test_check_reports_a_path_it_cannot_read(tmp_path):
    result = check(tmp_path)

    assert result.exit_code == 1
    assert result.stderr.startswith(f"Can't read {tmp_path}: ")
