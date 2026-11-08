# New accounts start in Shadow mode

A new user can't know in advance how their rules and the model's categories will treat their real inbox, and a wrongly archived or trashed email costs trust, or the email itself. So emailbot starts in Shadow mode. It works out every Action and lists it in the daily digest ("would trash 12 emails from deals@shop.com"), but applies none of them until the user sets `mode: live`.

## Consequences

- For the first days the digest shows what emailbot would have done. The intended habit is to compare that with your own judgment for about a week, then switch.
- `emailbot config check` shows the mode, so users can see they are in Shadow mode.
- Shadow mode works alongside `--dry-run` on a single command and `emailbot undo`. It doesn't replace them.
- **Still open:**
  - Which Actions Shadow mode holds back, for example whether it still creates drafts, is decided in the organize milestone (M4).
  - Today `mode` is one setting for the whole install, so an account added to an install that is already live would be live at once. That needs deciding before M1's `accounts add`: either a mode per account, or new accounts starting in Shadow mode some other way.
