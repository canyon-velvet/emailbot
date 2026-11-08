# Secrets go in the OS keychain by default, or in 1Password

emailbot holds Gmail login tokens, which can read and change a mailbox, and LLM API keys, which cost money. A config file or a plain file would leak them through backups, dotfile repos and screenshots. So secrets are stored by default in the operating system's keychain through the `keyring` library: macOS Keychain, Windows Credential Manager, or the Linux desktop keyring. People who already use 1Password can choose it instead, through the official `op` command-line tool and the 1Password app's unlock (for example Touch ID). Secrets are never written to config, printed or logged.

## Considered options

- **1Password's Python SDK and third-party `keyring` plugins.** Rejected: they mean more dependencies to trust, while the official `op` tool already handles unlocking.

## Consequences

- All secrets go through one small secrets module (get, set, remove, exists), whichever backend is chosen.
- emailbot gives a secret's value to `op` through its input, never as a command-line argument, so other programs can't read it from the process list.
- Machines with no keychain, such as headless servers and Docker containers, can't store secrets until M7 adds a store for them.
- Tests use a fake keychain and a fake `op`, so they never touch real secrets.
