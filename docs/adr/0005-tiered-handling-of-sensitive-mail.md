# Tiered handling of Sensitive mail

Sending mail to a cloud model shows it to that provider. Running everything on a local model would protect it, but most people don't have hardware that can run a good model. Sending everything to the cloud would expose bank statements, medical results and password resets. So mail is handled in three tiers:

1. **Newsletters** are bulk mail with public content, so they go to a cloud model as they are.
2. **Other personal mail** goes through Redaction first: personal details and secrets are replaced with placeholders, and put back on the user's computer afterwards.
3. **Sensitive mail** never reaches a cloud model. It is handled only by plain rules, unless the user configures a model marked `local: true`. That mark is accepted only for an address that really is on the user's computer or private network.

## Consequences

- Before any model call, a check decides whether the email is Sensitive mail. A Sensitive email the check misses would reach a cloud model with only Redaction protecting it, so that check needs tests on realistic examples.
- emailbot gives Sensitive mail less help (rules only) unless the user runs a local model.
- Link-local addresses such as 169.254.x.x don't count as local, because cloud metadata services live there.
