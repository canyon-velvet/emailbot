# emailbot

A security-first email assistant that each person runs on their own computer. It reads their Gmail to organize it, summarize newsletters and draft replies, and never sends mail itself.

## Language

### Changing the mailbox

**Action**:
One change emailbot wants to make to the user's mail, such as adding a label, archiving a message, moving it to Trash or creating a draft. Putting the Digest into the inbox is not an Action.
_Avoid_: operation, command, task

**Policy gate**:
The single checkpoint that decides whether an Action may change the mailbox.
_Avoid_: guard, approval step, filter (a Gmail filter is something else)

**Shadow mode**:
The state in which emailbot works out its Actions but applies none of them. Its opposite is live mode, in which allowed Actions are applied.
_Avoid_: dry run (a one-off option on a single command), preview, test mode

### Sorting mail

**Category**:
One of the user's own groups for sorting mail, such as Receipts or Travel, shown in Gmail as a label. Gmail's built-in tabs, such as Primary and Promotions, are not Categories.
_Avoid_: folder, bucket

**Protected sender**:
A sender the user trusts: anyone they have written to, marked to keep, or listed as protected in their settings.
_Avoid_: safe sender, whitelist, VIP

### Privacy

**Sensitive mail**:
Mail about money, health, government matters or account security, such as bank statements, medical results, one-time codes and password resets.
_Avoid_: private mail, confidential mail

**Redaction**:
Replacing personal details and secrets in an email with placeholders such as `<PHONE_1>`, in a way that lets the real values be put back later.
_Avoid_: anonymization, scrubbing

### Gmail as the interface

**Command label**:
A Gmail label under `bot/` that the user puts on a message to ask emailbot to do something with it, such as `bot/reply` or `bot/unsubscribe`. Labels emailbot adds itself, such as `bot/drafted`, are not Command labels.
_Avoid_: tag, trigger, action label

**Digest**:
The daily email emailbot puts in the user's inbox, holding Digest items and a report of what emailbot did, or in Shadow mode would have done.
_Avoid_: summary, newsletter (newsletters are what it reads)

**Digest item**:
One piece of news in the Digest, taken from a newsletter, with a short summary, its source and the Interest it matched.
_Avoid_: article, entry, post

### Personalization

**Interest**:
A short phrase on the user's checklist, such as "Rust" or "AI agents", naming a topic they want Digest items about.
_Avoid_: keyword, tag, preference

**Tone example**:
A reply the user actually sent, shown to the model so that a draft sounds like the user wrote it.
_Avoid_: sample, template, training data (nothing is trained)
