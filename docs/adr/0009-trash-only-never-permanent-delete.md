# Trash only, never permanent delete; only the user's rules or labels trash mail

Throwing away the wrong email is the worst mistake an inbox organizer can make. So emailbot never permanently deletes mail. It only moves mail to Trash, where Gmail keeps it for 30 days. And mail is trashed only because of a rule the user wrote (including what they chose to do with a Category) or a label the user applied. The model only picks a Category from the user's list. It never decides on its own that something should go.

## Consequences

- There is no code that permanently deletes. A check in CI catches the usual ways of writing such code by mistake. It's a tripwire, not a defence against disguised code. Gmail's `gmail.modify` permission can't permanently delete messages or threads either, so Google backs this up.
- Mistakes can be recovered from Trash for 30 days, and `emailbot undo` will put back what emailbot did.
- A Protected sender's mail is never trashed or archived because of a Category the model chose.
- Each run has a cap on how many messages it may trash.
