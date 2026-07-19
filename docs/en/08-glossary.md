[![English](https://img.shields.io/badge/lang-English-1f6feb?style=flat-square)](../en/08-glossary.md) [![Tiếng Việt](https://img.shields.io/badge/lang-Ti%E1%BA%BFng%20Vi%E1%BB%87t-8b949e?style=flat-square)](../vi/08-glossary.md) · [🏠 README](../../README.md) · [📚 Index](00-index.md)

# Glossary

Plain-language definitions, roughly beginner → advanced.

- **API** — a way for programs to talk to a service over the internet using agreed
  rules.
- **Endpoint** — a specific URL of an API that does one thing, e.g.
  `/v1/chat/completions`.
- **HTTP / HTTPS** — the protocol web requests use; HTTPS is the encrypted version.
- **JSON** — a simple text format for structured data (`{"key": "value"}`).
- **Client / SDK** — the program (or library) that calls the API, e.g. the
  `openai` Python package.
- **LLM (Large Language Model)** — the AI that predicts text; the "brain" behind
  chat.
- **Token** — a chunk of text (~¾ of a word) that models read/produce; usage is
  measured in tokens.
- **Streaming / SSE** — sending a reply in pieces as it's produced.
  **SSE (Server-Sent Events)** is the HTTP technique used.
- **Agent** — an AI that can *act*: use tools, run steps, and produce results, not
  just chat.
- **Thread** — a persistent workspace where one agent run happens (messages,
  tool calls, artifacts).
- **Hyperagent** — the platform running these agents (`hyperagent.com`).
- **MCP (Model Context Protocol)** — an open standard connecting AI clients to
  tools/services. Hyperagent exposes an MCP server.
- **JSON-RPC** — a simple "call a function over the network with JSON" protocol;
  MCP uses it.
- **OAuth 2.1** — the standard "sign in and grant access" flow. Hyperagent uses it
  (no API keys).
- **PKCE** — a security add-on to OAuth for apps that can't keep a secret; a code
  proves the same app that started login is finishing it.
- **Access token / Refresh token** — a short-lived key to call the API / a
  long-lived key to get new access tokens without logging in again.
- **Gateway** — this project: the adapter turning OpenAI calls into Hyperagent
  calls.
- **Upstream adapter** — the swappable component that talks to Hyperagent
  (`mcp`) or fakes it (`mock`).
- **Poll** — repeatedly asking "done yet?" until a background job finishes.
- **`tool_calls`** — OpenAI's format for an AI asking to run a function/tool.
- **Tool bridge** — how this gateway exposes Hyperagent's tools as OpenAI
  `tool_calls`.
- **Embeddings** — numeric vectors representing text meaning (for search/similarity).
- **Moderation** — checking whether text is harmful/allowed.
- **Multi-tenant** — one server safely serving many separate users/accounts.
- **Stateless** — each request stands alone; the server keeps no per-user memory
  between calls.
- **`repository-harness`** — the framework used to *develop* this repo (intake,
  stories, decisions, tests). See [Contributing](09-contributing.md).
