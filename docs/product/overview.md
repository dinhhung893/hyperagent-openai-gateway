# Product Overview: Hyperagent → OpenAI-Compatible API Gateway

**Project:** Hyperagent.com-to-API
**Status:** Accepted spec (v1 intake 2026-07-19)

## What we are building

A gateway service that makes **Hyperagent.com behave like an OpenAI API server**.
Any OpenAI-compatible client (OpenAI Python/JS SDK, Cursor, Continue, LibreChat,
LangChain, LlamaIndex, `llm` CLI, OpenWebUI, etc.) points its `base_url` at the
gateway and calls the standard OpenAI endpoints. The gateway translates each call
into Hyperagent operations, runs them against a Hyperagent agent, and returns
responses in exact OpenAI wire format (including SSE streaming and tool calls).

The design goal is **maximal surface coverage**, on two axes:

1. **Every OpenAI API attribute/endpoint** a client can call is accepted and
   given a defined behavior — implemented, mapped, or an explicit, honest error.
   See `openai-compatibility.md`.
2. **Every Hyperagent capability** — Shell/Bash, filesystem Write/Read/Edit, web
   search, browser automation, image/video/audio generation, tables, documents,
   maps, integrations, and more — is reachable through the OpenAI protocol, via
   agent execution and an OpenAI `tools`/`tool_calls` bridge. See
   `capability-catalog.md` and `tool-bridge.md`.

## Why this is possible

Hyperagent exposes a hosted **MCP server** at `https://hyperagent.com/api/mcp`
(the only public programmatic surface). The gateway is an MCP client of that
server. See `upstream-mcp.md` for the confirmed transport, auth, and tools.

## Architecture

```
OpenAI-compatible client
   | HTTP  (Authorization: Bearer <gateway key>)
   v
[ Gateway ]  (OpenAI wire protocol in/out)
   - AuthN/AuthZ: validate client key -> resolve a Hyperagent OAuth identity
   - Router: /v1/chat/completions, /v1/responses, /v1/models, /v1/images/*,
             /v1/audio/*, /v1/embeddings, /v1/files, /v1/moderations, ...
   - Translator: OpenAI request  <-> Hyperagent thread operations
   - UpstreamAdapter (swappable): McpAdapter | MockAdapter | (future) RestAdapter
   |
   | MCP JSON-RPC 2.0 over HTTPS POST  (Authorization: Bearer <OAuth token>)
   v
Hyperagent MCP server  https://hyperagent.com/api/mcp
   list_agents · create_thread · send_message · get_thread ·
   list_threads · create_attachment_upload
   |
   v
Hyperagent agent run (uses its full internal tool catalog inside the thread)
```

## Core translation model

- **`model` → agent.** An OpenAI `model` string maps to a Hyperagent `agentId`
  (resolved via `list_agents`, cached). `/v1/models` lists agents as models.
- **`messages[]` → thread.** The conversation is turned into a self-contained
  opening message for `create_thread`; multi-turn conversations map to a
  persistent Hyperagent thread reused via `send_message`.
- **Execution is asynchronous.** `create_thread`/`send_message` return a
  `threadId`; the gateway polls `get_thread` until the run is no longer running,
  then emits the assistant result.
- **Streaming is emulated.** Hyperagent does not push token-level output, so
  `stream: true` is served by polling `get_thread`, diffing the messages array,
  and emitting OpenAI `chat.completion.chunk` / Responses stream events.
- **Tools are bridged both ways.** The agent's internal tool activity (Shell,
  Write, web search, image gen, …) is surfaced to the client as OpenAI
  `tool_calls`; and clients can direct/force specific Hyperagent capabilities
  through the OpenAI tool-calling protocol. See `tool-bridge.md`.

## Non-goals / honest limits (see individual docs for detail)

- No raw single-token model inference: every call runs a full agent pipeline, so
  latency is higher and `temperature`/`top_p`/`seed` are best-effort or no-ops.
- No native streaming of partial generation (emulated only).
- No embeddings via MCP (documented fallback in `openai-compatibility.md`).
- Auth is per-user OAuth (no Hyperagent API keys exist); the gateway holds and
  refreshes each user's Hyperagent token. See `auth.md`.

## Product docs in this directory

| File | Contents |
| --- | --- |
| `overview.md` | This file. |
| `upstream-mcp.md` | Confirmed MCP transport, OAuth, six tools, polling, files. |
| `openai-compatibility.md` | Full endpoint + parameter compatibility matrix. |
| `capability-catalog.md` | Complete Hyperagent tool/capability inventory. |
| `tool-bridge.md` | How Hyperagent tools map to OpenAI `tools`/`tool_calls`. |
| `auth.md` | Client-key ↔ Hyperagent OAuth model; multi-tenant. |
