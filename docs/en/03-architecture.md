[![English](https://img.shields.io/badge/lang-English-1f6feb?style=flat-square)](../en/03-architecture.md) [![Tiếng Việt](https://img.shields.io/badge/lang-Ti%E1%BA%BFng%20Vi%E1%BB%87t-8b949e?style=flat-square)](../vi/03-architecture.md) · [🏠 README](../../README.md) · [📚 Index](00-index.md)

# Architecture

## Components

| Module | Responsibility |
| --- | --- |
| `gateway/app.py` | All HTTP routes; wires everything together. |
| `gateway/auth.py` | Client-key check; maps `model` → agent id. |
| `gateway/identities.py` | Multi-tenant: API key → Hyperagent identity + policy. |
| `gateway/upstream/base.py` | The `UpstreamAdapter` interface + normalized types. |
| `gateway/upstream/mcp.py` | Real MCP JSON-RPC client + OAuth token manager. |
| `gateway/upstream/mock.py` | Deterministic offline adapter for tests/dev. |
| `gateway/upstream/manager.py` | One adapter/resolver per identity (pool). |
| `gateway/translate.py` | OpenAI ⇄ Hyperagent message/response translation. |
| `gateway/streaming.py` | Emulated SSE for chat and Responses. |
| `gateway/toolbridge.py` | Canonical tool catalog + `tool_calls` mapping. |
| `gateway/media.py`, `fallbacks.py` | Images/audio helpers; embeddings + moderation fallbacks. |
| `gateway/state.py` | SQLite: conversations, responses, files. |

The **UpstreamAdapter** is the key seam: everything above it is pure OpenAI
translation; everything below is Hyperagent. Swapping `mock` ↔ `mcp` changes
nothing else.

## Request lifecycle — chat (non-streaming)

```mermaid
sequenceDiagram
  participant C as Client
  participant G as Gateway
  participant H as Hyperagent MCP
  C->>G: POST /v1/chat/completions (messages)
  G->>G: auth key → identity; model → agentId
  G->>G: flatten messages → one self-contained prompt
  G->>H: create_thread(agentId, prompt)
  H-->>G: threadId
  loop poll until a new reply appears
    G->>H: get_thread(threadId)
    H-->>G: messages + isRunning
  end
  G-->>C: chat.completion (assistant text + tool_calls)
```

## Streaming

Hyperagent doesn't emit tokens. The gateway **polls** `get_thread`, diffs the
assistant message, and emits OpenAI `chat.completion.chunk` events (and Responses
`response.output_text.delta` events), ending with `data: [DONE]`. It's real SSE
on the wire — the "streaming" is reconstructed from polling.

## Stateless design & context reconstruction

Live testing showed Hyperagent's cross-turn thread memory is **unreliable** for
MCP-driven turns, plus a race where a just-queued turn briefly looks "done". So
the gateway follows one rule: **never rely on upstream memory. Every turn is a
fresh, self-contained thread.**

- **Chat Completions** is stateless: OpenAI clients resend the full `messages[]`
  each call, so the gateway flattens all of it into a new thread. (A different
  `system_fingerprint`/threadId per call is expected.)
- **Responses API** is stateful *by reconstruction*: for `previous_response_id`,
  the gateway reads the prior thread, flattens it, and prepends it to a new
  thread.
- **New-reply detection:** waiting requires a *new* assistant message beyond a
  captured baseline (`wait_for_new_assistant`), which removes the stale-reply
  race.

This decision is recorded in
[`docs/decisions/0010`](../decisions/0010-stateless-gateway-context-reconstruction.md).

## The upstream (confirmed live)

- Endpoint `https://hyperagent.com/api/mcp`, JSON-RPC 2.0 over POST.
- OAuth 2.1 (Authorization Code + PKCE, Dynamic Client Registration, refresh via
  `offline_access`); **no API keys**.
- Six tools; `get_thread` returns `{thread, messages[], isRunning}`.
- Full details: [`docs/product/upstream-mcp.md`](../product/upstream-mcp.md).

## Auth boundaries

Two independent layers:
1. **Client → gateway:** an OpenAI-style `Authorization: Bearer <gateway key>`.
2. **Gateway → Hyperagent:** a per-user OAuth token the gateway stores & refreshes.

A gateway key maps to one Hyperagent identity, so one server is multi-tenant by
user. See [Deployment](06-deployment.md).
