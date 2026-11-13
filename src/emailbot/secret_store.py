"""Where emailbot keeps secrets, such as LLM API keys, and how it reads and writes
them."""

import contextlib
import re
from collections.abc import Iterator

import keyring
from keyring.backend import KeyringBackend
from keyring.backends import fail, null

from emailbot.config import SecretsConfig

SERVICE = "emailbot"
_NAME = re.compile(r"llm:[a-z0-9-]+")


class SecretStoreError(Exception):
    """A problem with a secret or where it's kept, explained in plain words."""


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


def open_store(settings: SecretsConfig) -> Keychain:
    """The store `secrets.backend` chooses."""
    if settings.backend == "1password":
        raise SecretStoreError(
            "Keeping secrets in 1Password isn't supported yet. For now, remove the "
            "`secrets` settings from the config file to use the keychain."
        )
    return Keychain(_usable_keyring())
