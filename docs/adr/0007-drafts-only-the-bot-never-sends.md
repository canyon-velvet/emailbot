# Drafts only; the bot never sends

An assistant that can send mail can be turned by one malicious email into a spam or phishing relay, or into a way to mail private data out. A wrong automatic reply can't be taken back either. So emailbot never sends. It writes drafts, and the user reads them and presses Send in Gmail. In a draft, emailbot's own code sets the recipients, subject and thread. The model writes only the body. For the same reasons, emailbot never forwards mail and never sends automatic replies.

## Consequences

- There is no code that sends or forwards mail. A check in CI catches the usual ways of writing such code by mistake, including Gmail's forwarding settings, forwarding filters and the vacation responder. It's a tripwire for honest mistakes, not a defence against disguised code, which reviews cover.
- Gmail's `gmail.modify` permission technically allows sending, and `gmail.settings.basic` allows forwarding and automatic replies. So this promise rests on emailbot's code, not on Google, and the threat model (`SECURITY.md`) must say so.
- The Digest is put into the inbox directly, not sent.
- Unsubscribing never sends an email to a mailto address, even when that's the only way a sender offers.
