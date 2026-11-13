"""Where emailbot keeps secrets, such as LLM API keys, and how it reads and writes
them."""

import contextlib
import json
import re
import shutil
import subprocess
from collections.abc import Iterator
from typing import Any, Protocol

import keyring
from keyring.backend import KeyringBackend
from keyring.backends import fail, null

from emailbot.config import SecretsConfig

SERVICE = "emailbot"
_NAME = re.compile(r"llm:[a-z0-9-]+")


class SecretStoreError(Exception):
    """A problem with a secret or where it's kept, explained in plain words."""


class SecretStore(Protocol):
    """Where secrets are kept. `where` names it for the user, e.g. "the keychain"."""

    where: str

    def get(self, name: str) -> str | None: ...
    def exists(self, name: str) -> bool: ...
    def set(self, name: str, value: str) -> None: ...
    def remove(self, name: str) -> bool: ...


def check_name(name: str) -> None:
    # The name isn't repeated back: it may be a value pasted in the wrong place.
    if not _NAME.fullmatch(name):
        raise SecretStoreError(
            "That isn't a secret name emailbot uses. Names look like llm:openai: "
            "llm: followed by lowercase letters, digits and hyphens."
        )


def _usable_keyring() -> KeyringBackend:
    try:
        backend = keyring.get_keyring()
    except Exception as error:
        # keyring loads the backend its settings name here, and a bad name can fail
        # in many ways.
        raise SecretStoreError(
            "Couldn't use the keychain: keyring's backend settings, in "
            f"PYTHON_KEYRING_BACKEND or keyringrc.cfg, don't work here ({error})"
        ) from None
    # keyring uses `fail` when it finds no keychain, and `null` when it's turned off.
    if isinstance(backend, fail.Keyring | null.Keyring):
        raise SecretStoreError(
            "No usable keychain was found on this computer. You can keep secrets in "
            "1Password instead, with `secrets.backend: 1password` and a "
            "`secrets.vault` in the config file. Support for computers without a "
            "keychain is coming in a later version."
        )
    return backend


@contextlib.contextmanager
def _keychain_problems() -> Iterator[None]:
    try:
        yield
    # Not just KeyringError: some keychains (Linux's, Windows') raise their own
    # platform's errors.
    except Exception as error:
        raise SecretStoreError(f"Couldn't use the keychain: {error}") from None


class Keychain:
    """Secrets in the operating system's keychain, under the service `emailbot`."""

    where = "the keychain"

    def __init__(self, backend: KeyringBackend):
        self._backend = backend

    def get(self, name: str) -> str | None:
        check_name(name)
        with _keychain_problems():
            return self._backend.get_password(SERVICE, name)

    def exists(self, name: str) -> bool:
        return self.get(name) is not None

    def set(self, name: str, value: str) -> None:
        check_name(name)
        with _keychain_problems():
            self._backend.set_password(SERVICE, name, value)
            kept = self._backend.get_password(SERVICE, name)
        # Read back: some backends, e.g. keyring's chainer with nothing to chain,
        # accept a secret and keep nothing.
        if kept != value:
            raise SecretStoreError(
                f"The keychain accepted {name} but didn't keep it, so nothing was "
                "stored. Check keyring's backend settings, in PYTHON_KEYRING_BACKEND "
                "or keyringrc.cfg."
            )

    # Not `delete`: the forbidden-code check flags any `.delete` attribute.
    def remove(self, name: str) -> bool:
        """Remove the secret. False if it wasn't set."""
        # Checked first: macOS raises the same error for "not found" and for a
        # removal it refused.
        if not self.exists(name):
            return False
        with _keychain_problems():
            self._backend.delete_password(SERVICE, name)
        return True


# How `op` 2.x says it's locked, signed out, or can't reach the 1Password app.
_LOCKED_OR_SIGNED_OUT = (
    "not signed in",
    "not currently signed in",
    "No accounts configured",
    "authorization",
    "desktop app",
)
_ERROR_PREFIX = re.compile(r"^\[ERROR\] \S+ \S+ ", re.MULTILINE)


class _NoSuchItem(Exception):
    pass


def _password(value: str) -> dict[str, Any]:
    return {
        "id": "password",
        "type": "CONCEALED",
        "purpose": "PASSWORD",
        "value": value,
    }


def _password_field(item: dict[str, Any]) -> dict[str, Any] | None:
    fields = item.get("fields", [])
    return next((field for field in fields if field.get("id") == "password"), None)


class OnePassword:
    """Secrets as items in a 1Password vault, through 1Password's own CLI, `op`.

    Each secret is a Password item titled with its name. Values reach `op` only
    through its input, never its arguments, where other programs could see them.
    """

    def __init__(self, op: str, vault: str):
        self._op_path = op
        self._vault = vault
        self.where = f"the 1Password vault {vault!r}"

    def get(self, name: str) -> str | None:
        item = self._item(name)
        field = _password_field(item) if item else None
        return field.get("value") if field else None

    def exists(self, name: str) -> bool:
        return self.get(name) is not None

    def set(self, name: str, value: str) -> None:
        item = self._item(name)
        if item is None:
            new = {"title": name, "category": "PASSWORD", "fields": [_password(value)]}
            create = ["create", "--category=Password", f"--title={name}", "-"]
            self._op("item", *create, input=new)
            return
        # Edited, not created again: 1Password allows two items with the same title.
        field = _password_field(item)
        if field is None:  # an item made by hand, without a password field
            item.setdefault("fields", []).append(_password(value))
        else:
            field["value"] = value
        self._op("item", "edit", name, input=item)

    # Not `delete`: the forbidden-code check flags any `.delete` attribute.
    def remove(self, name: str) -> bool:
        """Remove the secret. False if it wasn't set."""
        check_name(name)
        try:
            self._op("item", "delete", name)
        except _NoSuchItem:
            return False
        return True

    def _item(self, name: str) -> dict[str, Any] | None:
        check_name(name)
        try:
            return json.loads(self._op("item", "get", name, "--reveal"))
        except _NoSuchItem:
            return None

    def _op(self, *args: str, input: dict[str, Any] | None = None) -> str:
        # One `--vault=` argument, so a vault name starting with `-` isn't an option.
        command = [self._op_path, *args, f"--vault={self._vault}"]
        try:
            # S603: the arguments are fixed words, a checked secret name and the vault.
            result = subprocess.run(  # noqa: S603
                [*command, "--format=json", "--no-color"],
                input=None if input is None else json.dumps(input),
                # `op` reads piped input, so give it none unless it needs some.
                stdin=subprocess.DEVNULL if input is None else None,
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError as error:
            message = f"Couldn't run the 1Password CLI (op): {error.strerror or error}"
            raise SecretStoreError(message) from None
        if result.returncode == 0:
            return result.stdout
        problem = _ERROR_PREFIX.sub("", result.stderr).strip()
        if "isn't an item" in problem:
            raise _NoSuchItem
        if "isn't a vault" in problem:
            raise SecretStoreError(
                f"1Password has no vault named {self._vault!r} that you can use. "
                "Check secrets.vault in the config file."
            )
        if any(sign in problem for sign in _LOCKED_OR_SIGNED_OUT):
            raise SecretStoreError(
                "Couldn't get into 1Password: it's locked or signed out, or the app "
                "isn't running. Unlock the 1Password app (or sign in with "
                "`op signin`), then try again."
            )
        raise SecretStoreError(f"The 1Password CLI (op) failed: {problem}")


def open_store(settings: SecretsConfig) -> SecretStore:
    """The store `secrets.backend` chooses."""
    if settings.backend == "keychain":
        return Keychain(_usable_keyring())
    op = shutil.which("op")
    if op is None:
        raise SecretStoreError(
            "The 1Password CLI (op) isn't installed, or isn't on PATH. Install it and "
            "turn on its integration with the 1Password app: "
            "https://developer.1password.com/docs/cli/get-started/"
        )
    # The config check requires a vault with 1Password.
    return OnePassword(op, settings.vault or "")
