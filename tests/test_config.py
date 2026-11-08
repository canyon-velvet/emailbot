"""Run `emailbot config ...` in-process and check only its output and exit code."""

from pathlib import Path

from typer.testing import CliRunner

from emailbot.cli import app

runner = CliRunner()


def test_config_path_prints_the_file_given_with_config(tmp_path):
    path = tmp_path / "my.yaml"

    result = runner.invoke(app, ["--config", str(path), "config", "path"])

    assert result.exit_code == 0
    assert result.stdout.strip() == str(path)


def test_config_path_defaults_to_the_os_config_folder(home):
    result = runner.invoke(app, ["config", "path"])

    path = Path(result.stdout.strip())
    assert result.exit_code == 0
    assert path.is_relative_to(home)
    assert path.parts[-2:] == ("emailbot", "config.yaml")


def check(tmp_path, text):
    path = tmp_path / "config.yaml"
    path.write_text(text)
    return path, runner.invoke(app, ["--config", str(path), "config", "check"])


def test_check_accepts_a_valid_config(tmp_path):
    path, result = check(
        tmp_path,
        "mode: live\n"
        "accounts: [me@gmail.com, kid@example.org]\n"
        "secrets: {backend: 1password, vault: Family}\n",
    )

    assert result.exit_code == 0
    assert result.stdout == (
        f"Config OK: {path} (mode: live, accounts: 2, secrets: 1password)\n"
    )


def test_check_shows_the_defaults_for_an_empty_config(tmp_path):
    path, result = check(tmp_path, "")

    assert result.exit_code == 0
    assert result.stdout == (
        f"Config OK: {path} (mode: shadow, accounts: 0, secrets: keychain)\n"
    )


def test_check_reports_unknown_settings_with_their_dotted_path(tmp_path):
    path, result = check(tmp_path, "mdoe: live\nsecrets: {backnd: keychain}\n")

    assert result.exit_code == 1
    assert result.stderr == (
        f"{path} has 2 problems:\n"
        "  mdoe: unknown setting\n"
        "  secrets.backnd: unknown setting\n"
    )


def test_check_reports_invalid_values_with_their_dotted_path(tmp_path):
    path, result = check(tmp_path, "mode: production\n")

    assert result.exit_code == 1
    assert result.stderr == (
        f"{path} has 1 problem:\n  mode: Input should be 'shadow' or 'live'\n"
    )


def test_check_rejects_an_invalid_account_address(tmp_path):
    path, result = check(tmp_path, "accounts: [me@gmail.com, not-an-address]\n")

    assert result.exit_code == 1
    assert result.stderr == (
        f"{path} has 1 problem:\n"
        "  accounts.1: 'not-an-address' isn't a valid email address\n"
    )


def test_check_rejects_the_same_account_twice_whatever_its_case(tmp_path):
    path, result = check(tmp_path, "accounts: [me@gmail.com, Me@Gmail.com]\n")

    assert result.exit_code == 1
    assert result.stderr == (
        f"{path} has 1 problem:\n  accounts: Me@Gmail.com is listed more than once\n"
    )


def test_check_requires_a_vault_for_the_1password_backend(tmp_path):
    path, result = check(tmp_path, "secrets: {backend: 1password}\n")

    assert result.exit_code == 1
    assert result.stderr == (
        f"{path} has 1 problem:\n"
        "  secrets.vault: required when the backend is 1password\n"
    )


def test_check_explains_a_value_that_should_be_a_group_of_settings(tmp_path):
    path, result = check(tmp_path, "secrets: keychain\n")

    assert result.exit_code == 1
    assert result.stderr == (
        f"{path} has 1 problem:\n"
        "  secrets: should be a group of `name: value` settings\n"
    )


def test_check_rejects_a_file_that_is_not_a_group_of_settings(tmp_path):
    path, result = check(tmp_path, "- live\n")

    assert result.exit_code == 1
    assert result.stderr == (
        f"{path} has 1 problem:\n"
        "  (whole file): should be a group of `name: value` settings\n"
    )


def test_check_reports_yaml_syntax_errors_with_line_and_column(tmp_path):
    path, result = check(tmp_path, "mode: shadow\n  bad: indent\n")

    assert result.exit_code == 1
    assert result.stderr == (
        f"{path} isn't valid YAML at line 2, column 6: "
        "mapping values are not allowed here\n"
    )


def test_check_never_runs_python_tags_in_yaml(tmp_path):
    path, result = check(tmp_path, "mode: !!python/object/apply:os.getcwd []\n")

    assert result.exit_code == 1
    assert result.stderr.startswith(f"{path} isn't valid YAML at line 1, column 7: ")


def test_check_reports_where_it_looked_for_a_missing_file(tmp_path):
    path = tmp_path / "missing.yaml"

    result = runner.invoke(app, ["--config", str(path), "config", "check"])

    assert result.exit_code == 1
    assert result.stderr == (
        f"No config file at {path}. Create one, or pass --config PATH.\n"
    )


def test_check_reports_a_path_it_cannot_read(tmp_path):
    result = runner.invoke(app, ["--config", str(tmp_path), "config", "check"])

    assert result.exit_code == 1
    assert result.stderr == f"Can't read {tmp_path}: Is a directory\n"


def test_check_reports_bytes_that_are_not_text(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_bytes(b"mode: \xff\n")

    result = runner.invoke(app, ["--config", str(path), "config", "check"])

    assert result.exit_code == 1
    assert result.stderr.startswith(f"{path} isn't valid YAML: ")
