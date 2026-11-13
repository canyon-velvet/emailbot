import keyring
import pytest
from keyring.backend import KeyringBackend
from keyring.compat import properties
from keyring.errors import PasswordDeleteError


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    """Point every per-OS config folder at a temporary one, so no test touches real
    config."""
    for variable in ("HOME", "USERPROFILE", "XDG_CONFIG_HOME", "APPDATA"):
        monkeypatch.setenv(variable, str(tmp_path))
    return tmp_path


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
