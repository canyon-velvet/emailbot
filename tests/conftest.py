import pytest


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    """Point every per-OS config folder at a temporary one, so no test touches real
    config."""
    for variable in ("HOME", "USERPROFILE", "XDG_CONFIG_HOME", "APPDATA"):
        monkeypatch.setenv(variable, str(tmp_path))
    return tmp_path
