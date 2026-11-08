# Gmail is the user interface; no web server

Users want to use emailbot from their phone. A web or mobile app would mean running a server with open ports and its own logins, which is exactly the kind of attack surface a security-first tool should avoid. So Gmail itself is the interface:

- The Digest is an email that emailbot puts straight into the inbox each day. It is inserted, never sent.
- Drafts appear in Gmail's Drafts.
- Categories are Gmail labels.
- The user gives instructions by putting a Command label such as `bot/reply` on a message in the Gmail app.

emailbot runs no web server and opens no ports.

## Consequences

- It works on every device Gmail works on, with nothing extra to install on a phone.
- Command labels are trusted because whoever sends an email can't put a label on it. Only the account owner, and people and apps the owner has let into the account, can.
- Users can only ask for what a label or the Digest can express. Instructions sent by replying to the Digest come later, and will be trusted only when Gmail marks the reply as sent by the owner, so a spoofed message can't give orders.
- emailbot notices a new Command label when it next checks the mailbox, a few minutes later, not instantly.
