"""Fail if code that could send, delete or forward mail appears in the package.

A tripwire for honest mistakes, not a defence against deliberately disguised code.
"""

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
PACKAGE = ROOT / "src" / "emailbot"

# Gmail API names for sending, permanent deletion, forwarding and delegated access.
BANNED_ATTRIBUTES = {
    "send",
    "delete",
    "batchDelete",
    "forwardingAddresses",
    "autoForwarding",
    "updateAutoForwarding",  # the API method that turns auto-forwarding on
    "delegates",
}


def find_forbidden(source: str, path: str) -> list[str]:
    """Return a `path:line: rule` message for each banned use in `source`."""
    found: list[tuple[int, str]] = []
    for node in ast.walk(ast.parse(source, filename=path)):
        if isinstance(node, ast.Attribute) and node.attr in BANNED_ATTRIBUTES:
            found.append((node.lineno, f"banned attribute `.{node.attr}`"))
        elif isinstance(node, ast.Import) and "smtplib" in {a.name for a in node.names}:
            found.append((node.lineno, "banned import of `smtplib`"))
        elif isinstance(node, ast.ImportFrom) and node.module == "smtplib":
            found.append((node.lineno, "banned import of `smtplib`"))
    return [f"{path}:{line}: {rule}" for line, rule in sorted(found)]


def test_package_has_no_forbidden_code() -> None:
    files = sorted(PACKAGE.rglob("*.py"))
    assert files, f"no Python files under {PACKAGE}"
    found = [
        message
        for file in files
        for message in find_forbidden(
            file.read_text(encoding="utf-8"), str(file.relative_to(ROOT))
        )
    ]
    assert not found, "\n".join(found)


@pytest.mark.parametrize(
    ("sample", "expected"),
    [
        pytest.param(
            "def f(service):\n"
            "    service.users().drafts().send(userId='me', body=draft)\n",
            "sample.py:2: banned attribute `.send`",
            id="send",
        ),
        pytest.param(
            "def f(service):\n"
            "    service.users().messages().delete(userId='me', id=message_id)\n",
            "sample.py:2: banned attribute `.delete`",
            id="delete",
        ),
        pytest.param(
            "def f(service):\n"
            "    service.users().messages().batchDelete(userId='me', body=ids)\n",
            "sample.py:2: banned attribute `.batchDelete`",
            id="batchDelete",
        ),
        pytest.param(
            "def f(service):\n"
            "    service.users().settings().forwardingAddresses().create()\n",
            "sample.py:2: banned attribute `.forwardingAddresses`",
            id="forwardingAddresses",
        ),
        pytest.param(
            "def f(settings):\n    return settings.autoForwarding\n",
            "sample.py:2: banned attribute `.autoForwarding`",
            id="autoForwarding",
        ),
        pytest.param(
            "def f(service):\n"
            "    service.users().settings().updateAutoForwarding(userId='me')\n",
            "sample.py:2: banned attribute `.updateAutoForwarding`",
            id="updateAutoForwarding",
        ),
        pytest.param(
            "def f(service):\n"
            "    service.users().settings().delegates().create(userId='me')\n",
            "sample.py:2: banned attribute `.delegates`",
            id="delegates",
        ),
        pytest.param(
            "import email\nimport smtplib\n",
            "sample.py:2: banned import of `smtplib`",
            id="import smtplib",
        ),
        pytest.param(
            "import email\nfrom smtplib import SMTP\n",
            "sample.py:2: banned import of `smtplib`",
            id="from smtplib import",
        ),
    ],
)
def test_checker_catches_each_banned_pattern(sample: str, expected: str) -> None:
    assert find_forbidden(sample, "sample.py") == [expected]


def test_checker_passes_code_that_only_trashes_labels_and_drafts() -> None:
    clean = (
        "from email.message import EmailMessage\n"
        "\n"
        "import keyring\n"
        "\n"
        "\n"
        "def tidy(service, message_id):\n"
        "    messages = service.users().messages()\n"
        "    messages.trash(userId='me', id=message_id).execute()\n"
        "    messages.modify(userId='me', id=message_id, body={}).execute()\n"
        "    service.users().drafts().create(userId='me', body={}).execute()\n"
        "    keyring.delete_password('emailbot', 'token')\n"
    )
    assert find_forbidden(clean, "sample.py") == []
