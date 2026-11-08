# Drafts only; the bot never sends

An assistant that can send mail can be turned by one malicious email into a spam or phishing relay, or into a way to mail private data out. A wrong automatic reply can't be taken back either. So emailbot never sends. It writes drafts, and the user reads them and presses Send in Gmail. In a draft, emailbot's own code sets the recipients, subject and thread. The model writes only the body.

## Consequences

- There is no code that sends mail. A check in CI fails if code that could send mail appears in the package.
- Gmail's `gmail.modify` permission technically allows sending, so this promise rests on emailbot's code, not on Google. `SECURITY.md` says so.
- The digest is put into the inbox directly, not sent.
- Unsubscribing never sends an email to a mailto address, even when that's the only way a sender offers.
