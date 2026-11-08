# Any model through Pydantic AI, behind a single LLM client

Users must be able to use any model they like: a cloud provider (OpenAI, Anthropic, Gemini and others) or a model on their own computer or home network (Ollama, LM Studio, vLLM). They may also use different models for classifying mail, writing the digest and drafting replies. So every model call goes through Pydantic AI (`pydantic-ai-slim`, with only the provider extras needed), and only one module, the LLM client, uses it. Pydantic AI supports the main providers directly and any OpenAI-compatible address. It returns typed, validated output and retries automatically when a model's answer doesn't fit, and it has tool support if a future version needs it (within ADR 0008's rules).

## Considered options

- **LangChain.** Rejected: a large dependency tree and far more abstraction than a few structured calls need.
- **LiteLLM.** Rejected: its PyPI releases were compromised in March 2026. A package that sees every prompt and API key must not carry that supply-chain risk.

## Consequences

- Replacing Pydantic AI later touches only the LLM client.
- `CONTRIBUTING.md` bans LangChain and LiteLLM.
- Each provider extra is a dependency and needs a written reason, like any other.
