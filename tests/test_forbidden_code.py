"""Fail if code that could send, delete or forward mail appears in the package.

A tripwire for honest mistakes, not a defence against deliberately disguised code.
"""

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "emailbot"

# Gmail API names that send mail (auto-replies too), permanently delete it,
# forward it, or grant delegated access.
BANNED_ATTRIBUTES = {
    "send",
    "delete",
    "batchDelete",
    "forwardingAddresses",
    "autoForwarding",
    "updateAutoForwarding",  # the API method that turns auto-forwarding on
    "delegates",
    "updateVacation",  # turns on Gmail's auto-reply, which sends mail for the user
}

# Clients that send mail, or (imaplib) can permanently delete it.
BANNED_MODULES = {"smtplib", "aiosmtplib", "imaplib"}


def find_forbidden(source: str | bytes, path: str) -> list[str]:
    """Return a `path:line: rule` message for each banned use in `source`."""
    found: list[tuple[int, str]] = []
    for node in ast.walk(ast.parse(source, filename=path)):
        match node:
            case ast.Attribute(attr=name) if name in BANNED_ATTRIBUTES:
                found.append((node.lineno, f"banned attribute `.{name}`"))
            # A Gmail filter's forward action, `{"action": {"forward": address}}`,
            # as a string, a keyword or an attribute. Crude on purpose: the real
            # fix is building filters from a fixed template.
            case (
                ast.Constant(value="forward")
                | ast.keyword(arg="forward")
                | ast.Attribute(attr="forward")
            ):
                rule = "banned name `forward` (Gmail filter forwarding)"
                found.append((node.lineno, rule))
            case ast.Import() | ast.ImportFrom():
                for module in imported_modules(node):
                    if module.split(".")[0] in BANNED_MODULES:
                        found.append((node.lineno, f"banned import of `{module}`"))
    return [f"{path}:{line}: {rule}" for line, rule in sorted(found)]


def imported_modules(node: ast.Import | ast.ImportFrom) -> list[str]:
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    return [node.module] if node.module else []


def test_package_has_no_forbidden_code():
    files = sorted(PACKAGE.rglob("*.py"))
    assert files, f"no Python files under {PACKAGE}"
    found = [
        message
        for file in files
        # Bytes, so a `# coding:` line is decoded the way Python decodes it.
        for message in find_forbidden(file.read_bytes(), str(file.relative_to(ROOT)))
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
            "def f(service):\n"
            "    service.users().settings().updateVacation(userId='me', body=reply)\n",
            "sample.py:2: banned attribute `.updateVacation`",
            id="updateVacation",
        ),
        pytest.param(
            "def f(address):\n"
            "    return {'criteria': {}, 'action': {'forward': address}}\n",
            "sample.py:2: banned name `forward` (Gmail filter forwarding)",
            id="forward as a string",
        ),
        pytest.param(
            "def f(address):\n    return {'action': dict(forward=address)}\n",
            "sample.py:2: banned name `forward` (Gmail filter forwarding)",
            id="forward as a keyword",
        ),
        pytest.param(
            "def f(action, address):\n    action.forward = address\n",
            "sample.py:2: banned name `forward` (Gmail filter forwarding)",
            id="forward as an attribute",
        ),
        pytest.param(
            "import email\nimport os, smtplib as mail\n",
            "sample.py:2: banned import of `smtplib`",
            id="import smtplib",
        ),
        pytest.param(
            "import email\nfrom smtplib import SMTP\n",
            "sample.py:2: banned import of `smtplib`",
            id="from smtplib import",
        ),
        pytest.param(
            "import email\nimport imaplib\n",
            "sample.py:2: banned import of `imaplib`",
            id="import imaplib",
        ),
        pytest.param(
            "import email\nfrom aiosmtplib.smtp import SMTP\n",
            "sample.py:2: banned import of `aiosmtplib.smtp`",
            id="from aiosmtplib submodule import",
        ),
    ],
)
def test_checker_catches_each_banned_pattern(sample, expected):
    assert find_forbidden(sample, "sample.py") == [expected]


def test_checker_passes_allowed_gmail_calls_and_near_miss_names():
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
        "    promo = {'criteria': {'from': 'a@b.c'}, 'action': {'addLabelIds': []}}\n"
        "    service.users().settings().filters().create(userId='me', body=promo)\n"
        "    keyring.delete_password('emailbot', 'token')\n"
    )
    assert find_forbidden(clean, "sample.py") == []
