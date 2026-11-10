"""Run `emailbot secrets ...` in-process and check its output and exit code.

A fake keychain stands in for the real one (see conftest). Tests look inside it only
to check the service name secrets are kept under, and to make it fail.
"""

import keyring
import keyring.backends.fail
import keyring.backends.null
import pytest
from keyring.errors import KeyringError, PasswordDeleteError
from typer.testing import CliRunner

from emailbot.cli import app

runner = CliRunner()

SECRET = "sk-test-0123456789"  # noqa: S105 (made up; tests look for it in output)
TYPED_TWICE = f"{SECRET}\n{SECRET}\n"


def run(*args, input=None, config=None):
    """Run `emailbot secrets ARGS`. Every test goes through here, so every test also
    checks that the secret never appears in the output."""
    config_option = ["--config", str(config)] if config else []
    result = runner.invoke(app, [*config_option, "secrets", *args], input=input)
    assert SECRET not in result.stdout
    assert SECRET not in result.stderr
    return result


def store_secret():
    assert run("set", "llm:openai", input=TYPED_TWICE).exit_code == 0


def status():
    return run("status", "llm:openai").stdout


def write_config(tmp_path, text):
    path = tmp_path / "config.yaml"
    path.write_text(text)
    return path


def fail_with(error):
    def fail(*args):
        raise error

    return fail


def test_set_stores_the_value_typed_twice_under_the_emailbot_service(keychain):
    result = run("set", "llm:openai", input=TYPED_TWICE)

    assert result.exit_code == 0
    assert result.stdout == (
        "Value for llm:openai: \nEnter it again: \nStored llm:openai in the keychain.\n"
    )
    assert keychain.items == {("emailbot", "llm:openai"): SECRET}


def test_status_says_set_without_showing_the_secret():
    store_secret()

    result = run("status", "llm:openai")

    assert result.exit_code == 0
    assert result.stdout == "set\n"


def test_status_says_not_set_for_a_secret_never_stored():
    result = run("status", "llm:openai")

    assert result.exit_code == 0
    assert result.stdout == "not set\n"


def test_delete_removes_the_secret():
    store_secret()

    result = run("delete", "llm:openai")

    assert result.exit_code == 0
    assert result.stdout == "Removed llm:openai.\n"
    assert status() == "not set\n"


def test_delete_says_so_when_the_secret_was_not_set():
    result = run("delete", "llm:openai")

    assert result.exit_code == 0
    assert result.stdout == "llm:openai wasn't set.\n"


def test_set_stores_nothing_when_the_two_values_differ():
    result = run("set", "llm:openai", input=f"{SECRET}\n{SECRET}x\n")

    assert result.exit_code == 1
    assert result.stderr == "The two values don't match; nothing was stored.\n"
    assert status() == "not set\n"


@pytest.mark.parametrize("value", ["", "   "])
def test_set_stores_nothing_for_an_empty_value(value):
    result = run("set", "llm:openai", input=f"{value}\n{value}\n")

    assert result.exit_code == 1
    assert result.stderr == "No value entered; nothing was stored.\n"
    assert status() == "not set\n"


@pytest.mark.parametrize(
    "name", ["openai", "llm:", "llm:OpenAI", "llm:open_ai", SECRET]
)
@pytest.mark.parametrize("command", ["set", "status", "delete"])
def test_every_command_refuses_a_name_emailbot_does_not_use(command, name):
    result = run(command, name, input=TYPED_TWICE)

    assert result.exit_code == 1
    assert result.stdout == ""  # `set` doesn't ask for a value first
    assert result.stderr == (
        "That isn't a secret name emailbot uses. Names look like llm:openai: "
        "llm: followed by lowercase letters, digits and hyphens.\n"
    )


@pytest.mark.parametrize(
    "args",
    [
        ["llm:openai", SECRET],
        ["llm:openai", "--", SECRET],
        ["llm:openai", "--value", SECRET],
        [f"--value={SECRET}", "llm:openai"],
        ["llm:openai", f"-v{SECRET}"],
    ],
)
def test_set_never_takes_the_value_on_the_command_line(args):
    result = run("set", *args)

    assert result.exit_code == 2
    assert status() == "not set\n"


@pytest.mark.parametrize("command", ["set", "status", "delete"])
def test_every_command_refuses_extra_arguments_without_repeating_them(command):
    result = run(command, "llm:openai", SECRET)

    assert result.exit_code == 2
    assert result.stderr == (
        f"secrets {command} takes only a name. To store a secret, run "
        "`emailbot secrets set NAME` and type the value when asked, so it doesn't "
        "end up in your shell history.\n"
    )


@pytest.mark.parametrize("backend", [keyring.backends.fail, keyring.backends.null])
@pytest.mark.parametrize("command", ["set", "status", "delete"])
def test_every_command_explains_when_there_is_no_usable_keychain(command, backend):
    # keyring uses `fail` when it finds no keychain, and `null` when it's turned off.
    keyring.set_keyring(backend.Keyring())

    result = run(command, "llm:openai", input=TYPED_TWICE)

    assert result.exit_code == 1
    assert result.stdout == ""  # `set` doesn't ask for a value first
    assert result.stderr == (
        "No usable keychain was found on this computer. You can keep secrets in "
        "1Password instead, with `secrets.backend: 1password` and a `secrets.vault` "
        "in the config file. Support for computers without a keychain is coming in "
        "a later version.\n"
    )


def test_set_explains_a_keychain_backend_keyring_cannot_load(monkeypatch):
    # e.g. a mistyped PYTHON_KEYRING_BACKEND.
    missing = ModuleNotFoundError("No module named 'nosuch'")
    monkeypatch.setattr(keyring, "get_keyring", fail_with(missing))

    result = run("set", "llm:openai", input=TYPED_TWICE)

    assert result.exit_code == 1
    assert result.stdout == ""
    assert result.stderr == (
        "Couldn't use the keychain: the keyring backend set in "
        "PYTHON_KEYRING_BACKEND or keyringrc.cfg doesn't load "
        "(No module named 'nosuch')\n"
    )


@pytest.mark.parametrize("command", ["set", "status", "delete"])
def test_every_command_explains_any_other_keychain_problem(
    keychain, monkeypatch, command
):
    for method in ("get_password", "set_password", "delete_password"):
        monkeypatch.setattr(keychain, method, fail_with(KeyringError("It's locked")))

    result = run(command, "llm:openai", input=TYPED_TWICE)

    assert result.exit_code == 1
    assert result.stderr == "Couldn't use the keychain: It's locked\n"


def test_delete_reports_a_secret_the_keychain_refused_to_remove(keychain, monkeypatch):
    # macOS raises the same error for "not found" and for e.g. "access denied".
    store_secret()
    refused = PasswordDeleteError("Can't delete password in keychain: denied")
    monkeypatch.setattr(keychain, "delete_password", fail_with(refused))

    result = run("delete", "llm:openai")

    assert result.exit_code == 1
    assert result.stderr == (
        "Couldn't use the keychain: Can't delete password in keychain: denied\n"
    )
    assert status() == "set\n"


@pytest.mark.parametrize("command", ["set", "status", "delete"])
def test_every_command_says_1password_is_not_supported_yet(tmp_path, command):
    config = write_config(tmp_path, "secrets:\n  backend: 1password\n  vault: Mine\n")

    result = run(command, "llm:openai", input=TYPED_TWICE, config=config)

    assert result.exit_code == 1
    assert result.stdout == ""  # `set` doesn't ask for a value first
    assert result.stderr == (
        "Keeping secrets in 1Password isn't supported yet. For now, remove the "
        "`secrets` settings from the config file to use the keychain.\n"
    )


def test_set_explains_a_config_problem_before_asking_for_the_value(tmp_path):
    config = write_config(tmp_path, "secrets:\n  backend: vault\n")

    result = run("set", "llm:openai", input=TYPED_TWICE, config=config)

    assert result.exit_code == 1
    assert result.stdout == ""
    assert result.stderr.startswith(f"{config} has 1 problem:\n  secrets.backend: ")


def test_set_refuses_a_config_file_given_with_config_that_does_not_exist(tmp_path):
    # Defaults apply only when the default config file doesn't exist yet: a
    # mistyped --config shouldn't quietly switch to the keychain.
    config = tmp_path / "typo.yaml"

    result = run("set", "llm:openai", input=TYPED_TWICE, config=config)

    assert result.exit_code == 1
    assert result.stdout == ""
    assert result.stderr == (
        f"No config file at {config}. Create one, or pass --config PATH.\n"
    )
