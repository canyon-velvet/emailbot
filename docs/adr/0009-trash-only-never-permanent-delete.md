# Trash only, never permanent delete; only the user's rules or labels trash mail

Throwing away the wrong email is the worst mistake an inbox organizer can make. So emailbot never permanently deletes mail. It only moves mail to Trash, where Gmail keeps it for 30 days. And mail is trashed only because of a rule the user wrote (including what they chose to do with a category) or a label the user applied. The model only picks a category from the user's list. It never decides on its own that something should go.

## Consequences

- There is no code that permanently deletes. A check in CI fails if code that could permanently delete mail appears in the package. Gmail's `gmail.modify` permission also refuses permanent deletion, so Google enforces this too.
- Mistakes can be recovered from Trash for 30 days, and `emailbot undo` will put back what emailbot did.
- A Protected sender's mail is never trashed or archived because of a category the model chose.
- Each run has a cap on how many messages it may trash.
- The check currently flags every `.delete`, including harmless ones such as removing a Gmail filter. The Gmail work in M1 will narrow it to the dangerous calls.
