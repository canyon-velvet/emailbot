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


def test_config_path_keeps_a_tilde_name_that_is_no_user(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["--config", "~old.yaml", "config", "path"])

    assert result.stdout == f"{tmp_path / '~old.yaml'}\n"


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


@pytest.mark.parametrize("text", ["", "mode:\naccounts:\nsecrets:\nmodels:\n"])
def test_check_uses_the_defaults_for_missing_or_empty_settings(tmp_path, text):
    path = write(tmp_path, text)

    result = check(path)

    assert result.exit_code == 0
    assert result.stdout == (
        f"Config OK: {path} (mode: shadow, accounts: 0, secrets: keychain)\n"
    )


@pytest.mark.parametrize(
    "text",
    ["mdoe: live\nsecrets: {backnd: keychain}\n", "mdoe:\nsecrets:\n  backnd:\n"],
)
def test_check_reports_unknown_settings_with_their_dotted_path(tmp_path, text):
    path = write(tmp_path, text)

    result = check(path)

    assert result.exit_code == 1
    assert result.stderr == (
        f"{path} has 2 problems:\n"
        "  secrets.backnd: unknown setting\n"
        "  mdoe: unknown setting\n"
    )


@pytest.mark.parametrize(
    ("text", "shown"),
    [
        ('"k\\e]0;PWNED\\a": 1\n', "'k\\x1b]0;PWNED\\x07'"),  # control characters
        ("'': 1\n", "''"),
    ],
)
def test_check_quotes_setting_names_that_would_print_unclearly(tmp_path, text, shown):
    path = write(tmp_path, text)

    result = check(path)

    assert result.stderr == f"{path} has 1 problem:\n  {shown}: unknown setting\n"


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


# The vault name is passed to the 1Password CLI and shown in messages.
@pytest.mark.parametrize(
    "vault", ['"Pri\\tvate"', '"Pri\\nvate"', "!!binary UHJpCnZhdGU="]
)
def test_check_rejects_a_vault_name_with_control_characters(tmp_path, vault):
    path = write(tmp_path, f"secrets:\n  backend: 1password\n  vault: {vault}\n")

    result = check(path)

    assert result.exit_code == 1
    assert result.stderr == (
        f"{path} has 1 problem:\n  secrets.vault: can't contain control characters\n"
    )


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


@pytest.mark.parametrize(
    ("text", "where", "name"),
    [
        ("mode: shadow\naccounts: []\nmode: live\n", "line 3, column 1", "mode"),
        (
            "secrets:\n  <<: {backend: keychain, backend: 1password, vault: V}\n",
            "line 2, column 27",
            "backend",
        ),
    ],
)
def test_check_rejects_a_setting_given_twice(tmp_path, text, where, name):
    path = write(tmp_path, text)

    result = check(path)

    assert result.exit_code == 1
    assert result.stderr == (
        f"{path} isn't valid YAML at {where}: '{name}' is set more than once\n"
    )


def test_check_lets_a_merged_setting_be_overridden(tmp_path):
    # The anchor sits under an unknown name: the only place today's settings allow.
    path = write(
        tmp_path,
        "x:\n"
        "  sec: &sec\n"
        "    <<: {backend: keychain}\n"
        "    backend: 1password\n"
        "    vault: Family\n"
        "secrets:\n"
        "  <<: *sec\n",
    )

    result = check(path)

    assert result.stderr == f"{path} has 1 problem:\n  x: unknown setting\n"


@pytest.mark.parametrize("value", ["!!int abc", "!!bool maybe", "!!timestamp abc"])
def test_check_reports_a_value_that_does_not_fit_its_type_tag(tmp_path, value):
    path = write(tmp_path, f"mode: {value}\n")

    result = check(path)

    assert result.exit_code == 1
    assert result.stderr == (
        f"{path} isn't valid YAML: a value doesn't match its `!!` type tag\n"
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


def test_check_accepts_a_model_for_classify_digest_and_draft(tmp_path):
    path = write(
        tmp_path,
        "models:\n"
        "  classify: {provider: openai, model: gpt-5-mini}\n"
        "  digest: {provider: anthropic, model: claude-sonnet-5-5}\n"
        "  draft:\n"
        "    provider: openai-compatible\n"
        "    model: llama4\n"
        "    base_url: http://localhost:11434/v1\n"
        "    local: true\n",
    )

    result = check(path)

    assert result.exit_code == 0
    assert result.stdout.startswith("Config OK: ")


@pytest.mark.parametrize(
    ("model", "problem"),
    [
        (
            "{provider: openrouter, model: x}",
            "models.digest.provider: Input should be 'openai', 'anthropic', "
            "'gemini' or 'openai-compatible'",
        ),
        (
            "{provider: openai-compatible, model: x}",
            "models.digest.base_url: required when the provider is openai-compatible",
        ),
        ("{provider: openai}", "models.digest.model: Field required"),
        ("{provider: openai, model: '  '}", "models.digest.model: can't be blank"),
    ],
)
def test_check_rejects_an_incomplete_or_unknown_model(tmp_path, model, problem):
    path = write(tmp_path, f"models:\n  digest: {model}\n")

    result = check(path)

    assert result.exit_code == 1
    assert result.stderr == f"{path} has 1 problem:\n  {problem}\n"


@pytest.mark.parametrize(
    "base_url",
    [
        "'localhost:11434'",  # no http:// or https://
        "'http://[::1'",
        "'http://localhost:abc/v1'",
        "'http://localhost:99999/v1'",
        "'http://a b.local/v1'",
        "'http://.local/v1'",
        "'http://[v1.local]/v1'",  # brackets are only for IPv6 addresses
        '"http://evil.com\\n.local/v1"',  # a line break, which URL parsers drop
    ],
)
def test_check_rejects_a_base_url_that_is_not_a_full_address(tmp_path, base_url):
    path = write(
        tmp_path,
        f"models:\n  digest: {{provider: openai, model: x, base_url: {base_url}}}\n",
    )

    result = check(path)

    assert result.exit_code == 1
    assert result.stderr == (
        f"{path} has 1 problem:\n"
        "  models.digest.base_url: should be a full address such as "
        "http://localhost:11434/v1\n"
    )


def local_model(tmp_path, base_url, provider="openai-compatible"):
    return write(
        tmp_path,
        f"models:\n  draft: {{provider: {provider}, model: x, local: true, "
        f"base_url: '{base_url}'}}\n",
    )


@pytest.mark.parametrize(
    "host",
    [
        "localhost",
        "127.0.0.1",
        "[::1]",
        "10.0.0.5",
        "172.16.0.1",
        "192.168.1.20",
        "[fd00::1]",
        "mypc.local",
        "router.home.arpa",
    ],
)
def test_check_lets_a_model_on_this_computer_or_network_be_local(tmp_path, host):
    path = local_model(tmp_path, f"http://{host}:11434/v1")

    result = check(path)

    assert result.exit_code == 0
    assert result.stdout.startswith("Config OK: ")


@pytest.mark.parametrize(
    ("host", "why"),
    [
        ("api.openai.com", "isn't on this computer or a private network"),
        ("8.8.8.8", "isn't on this computer or a private network"),
        ("172.32.0.1", "isn't on this computer or a private network"),
        ("169.254.169.254", "is a link-local address"),
        ("[fe80::1]", "is a link-local address"),
    ],
)
def test_check_refuses_local_for_any_other_host(tmp_path, host, why):
    path = local_model(tmp_path, f"https://{host}/v1")

    result = check(path)

    assert result.exit_code == 1
    assert result.stderr.startswith(
        f"{path} has 1 problem:\n  models.draft.local: {host.strip('[]')!r} {why}"
    )


def test_check_explains_the_local_rule_for_other_hosts(tmp_path):
    path = local_model(tmp_path, "https://api.openai.com/v1")

    result = check(path)

    assert result.stderr == (
        f"{path} has 1 problem:\n"
        "  models.draft.local: 'api.openai.com' isn't on this computer or a private "
        "network (local allows localhost, loopback and private IP addresses, and "
        "names ending in .local or .home.arpa)\n"
    )


def test_check_explains_why_link_local_addresses_are_not_local(tmp_path):
    path = local_model(tmp_path, "http://169.254.169.254/v1")

    result = check(path)

    assert result.stderr == (
        f"{path} has 1 problem:\n"
        "  models.draft.local: '169.254.169.254' is a link-local address, which "
        "cloud metadata services use, so it can't count as local\n"
    )


def test_check_refuses_local_for_a_cloud_provider(tmp_path):
    path = local_model(tmp_path, "http://localhost:11434/v1", provider="openai")

    result = check(path)

    assert result.exit_code == 1
    assert result.stderr == (
        f"{path} has 1 problem:\n"
        "  models.draft.local: only for the openai-compatible provider: openai, "
        "anthropic and gemini are cloud services\n"
    )
