# Gmail API first, behind a mail-provider interface; Outlook later

The first users have Gmail, and Gmail's own concepts carry the design: labels, inbox categories, drafts, filters and the history API for spotting new mail. So emailbot talks to Gmail through Google's official API with OAuth, and the rest of the code reaches it only through a mail-provider interface, so that Outlook (through Microsoft Graph) can be added later.

## Considered options

- **IMAP and SMTP with an app password.** Rejected. An app password gives full access to the account, including sending, with no narrower permission to ask for. IMAP can also permanently delete mail (expunge), and it has no real labels or categories.

## Consequences

- emailbot asks for two Gmail permissions: `gmail.modify` (read, label, trash, drafts, and putting a message into the user's own inbox) and `gmail.settings.basic` (filters). Both technically allow more than emailbot does, so emailbot's own code enforces the limits (ADR 0007, ADR 0009).
- The mail-provider interface never gains a way to send, forward or permanently delete mail.
- Until a second provider exists, Gmail ideas such as labels and categories will appear throughout the code and docs.
