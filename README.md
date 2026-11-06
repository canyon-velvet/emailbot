# emailbot

An open-source, security-first email assistant that works with any LLM. You run it on your own computer, and it never sends email on its own.

> **Status:** early development. There is nothing to install yet.

## What it will do

- **Newsletter digest:** one daily email that boils your tech newsletters down to the topics you care about.
- **Drafts in your voice:** reply drafts that sound like you, waiting in Gmail for you to edit and send.
- **Inbox organization:** sorts mail into labels; your own rules decide what gets archived or trashed.
- **Promo cleanup:** one-click unsubscribe, or send a sender to Promotions for good.

## Security principles

- Runs on your machine. There is no hosted service.
- It can't send, forward or permanently delete mail, because no code exists to do it.
- The model gets no tools. It only returns validated data, and every mailbox change goes through one policy gate and is logged.
- Sensitive mail (banks, health, password resets) never reaches an LLM unless you configure a local model.
- Works with any model: OpenAI, Anthropic, Gemini, Ollama, or any OpenAI-compatible endpoint.

## License

[MIT](LICENSE)
