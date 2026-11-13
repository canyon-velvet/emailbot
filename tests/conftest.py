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
        lines = (self.home / "calls.jsonl").read_text().splitlines()
        return [json.loads(line) for line in lines]

    def items(self, vault: str = "Private") -> list[tuple[str, str]]:
        """(title, password) for each item in the vault."""
        vaults = json.loads((self.home / "vaults.json").read_text())
        return [
            (item["title"], field["value"])
            for item in vaults[vault]
            for field in item["fields"]
            if field["id"] == "password"
        ]

    def add_item(self, item: dict, vault: str = "Private") -> None:
        vaults = json.loads((self.home / "vaults.json").read_text())
        vaults[vault].append(item)
        (self.home / "vaults.json").write_text(json.dumps(vaults))

    def fail_with(self, error: str) -> None:
        (self.home / "failure").write_text(error)


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
