import json
import sys
from pathlib import Path

import keyring
import pytest
from keyring.backend import KeyringBackend
from keyring.compat import properties
from keyring.errors import PasswordDeleteError

FAKE_OP = Path(__file__).parent / "fixtures" / "fake_op.py"


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    """Point every per-OS config folder at a temporary one, so no test touches real
    config."""
    for variable in ("HOME", "USERPROFILE", "XDG_CONFIG_HOME", "APPDATA"):
        monkeypatch.setenv(variable, str(tmp_path))
    return tmp_path


@pytest.fixture(autouse=True)
def bin_dir(tmp_path, monkeypatch):
    """Make PATH just an empty folder, so no test can run a real 1Password CLI."""
    path = tmp_path / "bin"
    path.mkdir()
    monkeypatch.setenv("PATH", str(path))
    return path


class FakeOp:
    """Looks inside, and steers, the fake 1Password CLI (tests/fixtures/fake_op.py)."""

    def __init__(self, home: Path):
        self.home = home

    def calls(self) -> list[list[str]]:
        log = self.home / "calls.jsonl"
        lines = log.read_text().splitlines() if log.exists() else []
        return [json.loads(line) for line in lines]

    def items(self) -> list[dict]:
        """The items in the vault Private."""
        vaults = (self.home / "vaults.json").read_text(encoding="utf-8")
        return json.loads(vaults)["Private"]

    def passwords(self) -> list[tuple[str, str | None]]:
        """(title, password) for each item; None for an item without one."""
        return [(item["title"], next(_passwords(item), None)) for item in self.items()]

    def add_item(self, item: dict) -> None:
        (self.home / "vaults.json").write_text(
            json.dumps({"Private": [*self.items(), item]})
        )

    def break_with(self, error: str) -> None:
        """Make every call fail with this error."""
        (self.home / "failure").write_text(error)

    def hang(self) -> None:
        """Make every call wait, and never answer."""
        (self.home / "hang").touch()

    def ignore_input(self) -> None:
        """Make `create` and `edit` ignore the item they're given."""
        (self.home / "ignore-input").touch()


def _passwords(item: dict):
    for field in item.get("fields", []):
        if field["id"] == "password":
            yield field["value"]


@pytest.fixture(scope="session")
def fake_op_program(tmp_path_factory):
    """The fake `op`, written once: macOS checks each new program on its first run,
    which takes about half a second."""
    op = tmp_path_factory.mktemp("fake-op-program") / "op"
    op.write_text(f'#!/bin/sh\nexec "{sys.executable}" -I -S "{FAKE_OP}" "$@"\n')
    op.chmod(0o755)
    return op


@pytest.fixture
def fake_op(bin_dir, tmp_path, monkeypatch, fake_op_program):
    """Put a fake `op` on PATH, with one empty vault called Private."""
    home = tmp_path / "fake-op"
    home.mkdir()
    (home / "vaults.json").write_text(json.dumps({"Private": []}))
    (bin_dir / "op").symlink_to(fake_op_program)
    monkeypatch.setenv("FAKE_OP_HOME", str(home))
    return FakeOp(home)


class FakeKeychain(KeyringBackend):
    """An in-memory keychain: `items` maps (service, username) to the secret."""

    @properties.classproperty
    def priority(cls) -> float:
        return 0

    def __init__(self):
        super().__init__()
        self.items: dict[tuple[str, str], str] = {}

    def get_password(self, service, username):
        return self.items.get((service, username))

    def set_password(self, service, username, password):
        self.items[(service, username)] = password

    def delete_password(self, service, username):
        if self.items.pop((service, username), None) is None:
            raise PasswordDeleteError("not set")


@pytest.fixture(autouse=True)
def keychain():
    """Give every test an empty fake keychain, so no test touches the real one."""
    fake = FakeKeychain()
    keyring.set_keyring(fake)
    return fake
