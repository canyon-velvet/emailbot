# New accounts start in Shadow mode

A new user can't know in advance how their rules and the model's Categories will treat their real inbox, and a wrongly archived or trashed email costs trust, or the email itself. So emailbot starts in Shadow mode. It works out every Action and lists it in the Digest ("would trash 12 emails from deals@shop.com"), but applies none of them until the user sets `mode: live`.

## Consequences

- For the first days the Digest shows what emailbot would have done, so the user can compare it with their own judgment before switching.
- `emailbot config check` shows the mode, so users can see they are in Shadow mode.
- Shadow mode works alongside `--dry-run` on a single command and `emailbot undo`. It doesn't replace them.
- Today `mode` is one setting for the whole install, so an account added to an install that is already live would be live at once. Before M1's `accounts add` lands, new accounts must start in Shadow mode some other way, such as a mode per account.
