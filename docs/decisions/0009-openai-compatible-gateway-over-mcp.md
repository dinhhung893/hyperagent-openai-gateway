# 0009 OpenAI-Compatible Gateway Over Hyperagent MCP

Date: 2026-07-19

## Status

Accepted

## Context

The project goal is to let OpenAI-compatible software send chat requests to
Hyperagent.com. Research (docs + live endpoint probing, 2026-07-19) established
that Hyperagent's only public programmatic surface is the hosted **MCP server**
at `https://hyperagent.com/api/mcp`: JSON-RPC 2.0 over POST, OAuth 2.1
(Authorization Code + PKCE, DCR, refresh via `offline_access`; **no API keys**),
six tools (`list_agents`, `create_thread`, `send_message`, `get_thread`,
`list_threads`, `create_attachment_upload`), asynchronous background execution
polled via `get_thread`, and no native token streaming. There is no REST/GraphQL/
OpenAPI/SDK alternative. See `docs/product/upstream-mcp.md`.

The requirement is **maximal** coverage: every OpenAI-callable attribute and
endpoint, and exposure of Hyperagent's entire tool catalog (Shell, filesystem
Write/Read/Edit, web, browser, media generation, tables, docs, maps,
integrations, orchestration) through the OpenAI protocol.

## Decision

Build a stateless-friendly **gateway** that speaks the OpenAI wire protocol to
clients and the **MCP JSON-RPC protocol** to Hyperagent, with a swappable
`UpstreamAdapter` (MCP / mock / future REST). Specifically:

1. Map `model` → Hyperagent `agentId`; `/v1/models` lists agents.
2. Map conversations → threads; poll `get_thread`; **emulate** streaming.
3. Implement the full OpenAI endpoint family, prioritizing Chat Completions and
   the **Responses API** (closest to Hyperagent's stateful, tool-using,
   background thread model). Accept every documented request attribute with a
   defined behavior (impl / map / accept-no-op / explicit 501).
4. Bridge Hyperagent's tool catalog into OpenAI `tools`/`tool_calls` in three
   modes: observability, directed, and direct tool-runner execution
   (`docs/product/tool-bridge.md`).
5. Auth: client bearer keys decoupled from Hyperagent identity; gateway holds and
   rotates each user's Hyperagent OAuth refresh token; multi-tenant by user
   (`docs/product/auth.md`).

## Alternatives Considered

1. **Per-agent Webhook/API trigger** instead of MCP — rejected as primary: the
   inbound webhook creates a new thread per POST and its payload/token schema is
   undocumented; MCP is the richer, documented control surface (list/create/
   poll/continue/attach). May be added later as an adapter.
2. **Browser automation of the web UI** — rejected: fragile, slow, not a stable
   contract.
3. **Wait for a native OpenAI-compatible endpoint** — none exists or is
   announced.

## Consequences

Positive:
- Uses the official, documented surface; works for any OpenAI client; full tool
  reach via agent execution + tool bridge.

Tradeoffs:
- Higher latency (full agent pipeline) and emulated streaming.
- Sampling params (`temperature`/`top_p`/`seed`) are best-effort/no-op.
- Embeddings/logprobs not natively available (documented fallbacks).
- Per-user OAuth onboarding (no headless API key).

## Follow-Up

- Obtain verbatim MCP tool schemas via a live `tools/list` (needs a token).
- Slice into stories: core chat, streaming, models, tool-bridge, media/audio,
  files, Responses API, auth/onboarding, embeddings-fallback.
- Record a decision if the auth/onboarding or tool-exec policy changes.
