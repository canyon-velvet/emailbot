# Each user runs their own copy; there is no hosted service

emailbot reads a person's whole mailbox and holds login tokens that can change it. A hosted service would gather every user's tokens and mail in one place, which makes it a valuable target, and would make us the operator of a service that handles other people's mail. So each person installs and runs their own copy on their own computer, the way OpenBot works. One install can serve several Gmail accounts, such as a family's, and keeps each account separate.

## Consequences

- There is no server to run and no shared store of anyone's mail or tokens.
- Each user creates their own Google Cloud login client for Gmail, so setup needs a step-by-step guide. That client stays unverified:
  - Google shows a warning screen and allows at most 100 users, which is plenty for a household.
  - The client must be set to "In production", because in "Testing" Google expires the login every 7 days.
- Installing must be easy enough for people who aren't developers.
- Each user keeps their own copy up to date. CI audits dependencies, and releases will be published to PyPI with Trusted Publishing, so users can trust what they install.
- Running on an always-on machine (a start-at-boot service, a Docker image, hosts without a keychain) is its own milestone, M7.
