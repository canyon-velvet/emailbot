"""A fake 1Password CLI (`op`) for tests.

It keeps vaults and items in `$FAKE_OP_HOME/vaults.json`, logs each call's arguments
to `$FAKE_OP_HOME/calls.jsonl`, and answers like the real `op` 2.x for the commands
emailbot uses. Like the real one, it allows two items with the same title, hides
concealed values unless asked to `--reveal` them, and replaces an item with the one
`edit` is given. Files in `$FAKE_OP_HOME` change how it behaves:

- `failure`: every call fails, with the file's text as the error.
- `hang`: every call waits, and never answers.
- `ignore-input`: `create` and `edit` ignore the item they're given, like an `op`
  too old to read one.
"""

import json
import os
import sys
import time
from pathlib import Path

HOME = Path(os.environ["FAKE_OP_HOME"])
VAULTS = HOME / "vaults.json"
HIDDEN = "[use 'op item get --reveal' to reveal]"

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


def given_item():
    """The item on stdin, or None if told to ignore it."""
    item = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    return None if (HOME / "ignore-input").exists() else item


def shown(item, flags):
    if "reveal" in flags:
        return item
    fields = [
        {**field, "value": HIDDEN} if field.get("type") == "CONCEALED" else field
        for field in item.get("fields", [])
    ]
    return {**item, "fields": fields}


def main(args):
    with (HOME / "calls.jsonl").open("a") as log:
        log.write(json.dumps(args) + "\n")
    if (HOME / "failure").exists():
        fail((HOME / "failure").read_text())
    if (HOME / "hang").exists():
        time.sleep(600)
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

    vaults = json.loads(VAULTS.read_text(encoding="utf-8"))
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
        given = given_item() or {}
        item = {**given, "id": f"id{len(items)}", "title": flags["title"]}
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
        index = items.index(item)
        if command == "edit" and (given := given_item()) is not None:
            item = items[index] = {**given, "id": item["id"]}
        elif command == "delete":
            items.remove(item)
    VAULTS.write_text(json.dumps(vaults, ensure_ascii=False), encoding="utf-8")
    if command != "delete":
        sys.stdout.buffer.write(
            json.dumps(shown(item, flags), ensure_ascii=False).encode("utf-8")
        )


main(sys.argv[1:])
