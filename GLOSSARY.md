# emailbot

A security-first email assistant that each person runs on their own computer. It reads their Gmail to organize it, summarize newsletters and draft replies, and never sends mail itself.

## Language

### Changing the mailbox

**Action**:
One change emailbot wants to make to a mailbox, such as adding a label, archiving a message, moving it to Trash or creating a draft.
_Avoid_: operation, command, task

**Policy gate**:
The single checkpoint every Action passes through before it can change a mailbox, and the place that decides whether it is applied.
_Avoid_: guard, approval step, filter (a Gmail filter is something else)

**Shadow mode**:
The state in which emailbot works out its Actions but applies none of them, listing them in the daily digest instead. Its opposite is live mode, in which allowed Actions are applied.
_Avoid_: dry run (a one-off option on a single command), preview, test mode

**Protected sender**:
A sender whose mail is never trashed or archived because of a category the model chose: anyone the user has written to, or has marked to keep.
_Avoid_: safe sender, whitelist, VIP

### Privacy

**Sensitive mail**:
Mail about money, health, government matters or account security, such as bank statements, medical results, one-time codes and password resets. It never reaches a cloud model.
_Avoid_: private mail, confidential mail

**Redaction**:
Replacing personal details and secrets in an email with placeholders such as `<PHONE_1>` before it goes to a cloud model, in a way that lets the real values be put back afterwards on the user's computer.
_Avoid_: anonymization, scrubbing

### Talking to emailbot

**Command label**:
A Gmail label under `bot/` that the user puts on a message to ask emailbot to do something with it, such as `bot/reply` or `bot/unsubscribe`. Labels emailbot adds itself, such as `bot/drafted`, are not Command labels.
_Avoid_: tag, trigger, action label

**Digest item**:
One piece of news in the daily digest email, taken from a newsletter, with a short summary, its source and the Interest it matched.
_Avoid_: article, entry, post

**Interest**:
A short phrase on the user's checklist, such as "Rust" or "AI agents", naming a topic they want Digest items about.
_Avoid_: keyword, tag, preference

**Tone example**:
A reply the user actually sent, shown to the model so that a draft sounds like the user wrote it.
_Avoid_: sample, template, training data (nothing is trained)
