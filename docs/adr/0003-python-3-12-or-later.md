# Python 3.12 or later

The maintainer knows Python best. The libraries the plan depends on are also strongest in Python: Google's official Gmail client, Presidio for finding personal details to redact, fastembed for embeddings that run on the user's computer, and Pydantic AI for talking to any model. So emailbot is a Python package that supports 3.12 and later, managed with uv in the standard src layout.

## Consequences

- CI tests the oldest supported version (3.12) and the latest stable one.
- Code may use anything in 3.12, such as `match` statements and the newer generic syntax.
- Users need Python 3.12 or later. `uv tool install` fetches a suitable Python if they don't have one.
