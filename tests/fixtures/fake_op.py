"""A fake 1Password CLI (`op`) for tests.

It keeps vaults and items in `$FAKE_OP_HOME/vaults.json`, logs each call's arguments
to `$FAKE_OP_HOME/calls.jsonl`, and answers like the real `op` 2.x for the commands
emailbot uses. Like the real one, it allows two items with the same title. If
`$FAKE_OP_HOME/failure` exists, every call fails with its text as the error.
"""

import json
import os
import sys
from pathlib import Path

HOME = Path(os.environ["FAKE_OP_HOME"])
VAULTS = HOME / "vaults.json"

# The flags each command accepts, besides its one positional argument.
COMMANDS = {
    "get": {"vault", "reveal", "format", "no-color"},
    "create": {"vault", "category", "title", "format", "no-color"},
    "edit": {"vault", "format", "no-color"},
    "delete": {"vault", "format", "no-color"},
}


def fail(message):
    print(f"[ERROR] 2026/11/13 10:00:00 {message}", file=sys.stderr)
    sys.exit(1)


def main(args):
    with (HOME / "calls.jsonl").open("a") as log:
        log.write(json.dumps(args) + "\n")
    if (HOME / "failure").exists():
        fail((HOME / "failure").read_text())
    if len(args) < 2 or args[0] != "item" or args[1] not in COMMANDS:
        fail(f"unknown command: {args[:2]}")
    command, flags, positionals = args[1], {}, []
    for arg in args[2:]:
        if arg.startswith("--"):
            name, _, value = arg[2:].partition("=")
            if name not in COMMANDS[command]:
                fail(f"unknown flag: --{name}")
            flags[name] = value
        else:
            positionals.append(arg)
    if len(positionals) != 1:
        fail(f"expected one argument, got {positionals}")

    vaults = json.loads(VAULTS.read_text())
    vault = flags.get("vault")
    if vault not in vaults:
        fail(
            f'"{vault}" isn\'t a vault in this account. Specify the vault with its ID '
            "or name."
        )
    items = vaults[vault]

    if command == "create":
        if positionals != ["-"]:
            fail("create reads its template from stdin only in these tests")
        template = json.load(sys.stdin)
        item = {"id": f"id{len(items)}", "title": flags["title"], **template}
        items.append(item)
    else:
        name = positionals[0]
        matches = [item for item in items if item["title"] == name]
        if not matches:
            fail(
                f'"{name}" isn\'t an item in the "{vault}" vault. Specify the item '
                "with its UUID, name, or domain."
            )
        if len(matches) > 1:
            fail(
                f'More than one item matches "{name}". Try again and specify the item '
                "by its ID"
            )
        item = matches[0]
        if command == "edit":
            item.update(json.load(sys.stdin), id=item["id"])
        elif command == "delete":
            items.remove(item)
    VAULTS.write_text(json.dumps(vaults))
    if command != "delete":
        print(json.dumps(item))


main(sys.argv[1:])
