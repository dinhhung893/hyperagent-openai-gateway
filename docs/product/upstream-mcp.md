# Upstream: Hyperagent MCP Server

Confirmed 2026-07-19 by docs (`hyperagent.com/docs/reference/mcp-server`) and live
endpoint probing. Tags: **[C]** confirmed, **[I]** inferred, **[U]** undocumented
(resolve at build time with a real token).

## Endpoint & transport

- **Endpoint:** `https://hyperagent.com/api/mcp` (apex host `hyperagent.com`, not
  `www.`). **[C]**
- **Protocol:** Streamable HTTP MCP, **JSON-RPC 2.0 over POST**. `GET` → `405`
  (`Allow: POST`). The POST may return a JSON object or an SSE stream per the MCP
  Streamable-HTTP spec; there is **no** separate long-lived GET SSE channel. **[C]**
- **Recommended headers:** `Content-Type: application/json`,
  `Accept: application/json, text/event-stream`, `Authorization: Bearer <token>`.
- **Infra:** fronted by Cloudflare; responses carry `x-request-id` (log it). **[C]**

## Authentication (OAuth 2.1) — no API keys exist

The MCP endpoint is an RFC 9728 protected resource; `hyperagent.com` is itself the
authorization server. All **[C]** via live probe:

- Protected-resource metadata: `GET /.well-known/oauth-protected-resource`
  → `resource=https://hyperagent.com/api/mcp`,
  `authorization_servers=[https://hyperagent.com]`,
  `bearer_methods_supported=["header"]`.
- Auth-server metadata: `GET /.well-known/oauth-authorization-server`:
  - `authorization_endpoint = /api/oauth/authorize`
  - `token_endpoint = /api/oauth/token`
  - `registration_endpoint = /api/oauth/register` (RFC 7591 Dynamic Client Reg)
  - `grant_types_supported = [authorization_code, refresh_token]`
  - `code_challenge_methods_supported = [S256]` (PKCE required)
  - `token_endpoint_auth_methods_supported = [none]` (public clients)
  - `client_id_metadata_document_supported = true`
- **Scopes:** `threads:read`, `threads:write`, `approvals:read`,
  `approvals:write`, `offline_access`.
- **Flow:** (DCR or client-id-metadata) → Authorization Code + PKCE(S256) →
  **mandatory browser sign-in** (Google/Apple/Microsoft) + consent →
  code → token. Request `offline_access` to receive a **refresh token**.
- **No client-credentials grant, no API key, no PAT.** A headless gateway must
  complete the browser handshake **once per user**, store the refresh token, and
  rotate it. Tokens act **as that user** with no elevated access → the gateway is
  inherently multi-tenant-by-user. Token/refresh lifetimes: **[U]**.

## Tools (six) — schemas CONFIRMED via live `tools/list` (2026-07-19)

Verbatim input schemas captured with a real bearer token through the gateway's
own `McpAdapter`; full JSON in `mcp-tool-schemas.json` (this directory).

| Tool | Input schema (verbatim; * = required) | Returns (observed live) |
| --- | --- | --- |
| `list_agents` | (none) | `{"agents": [{id, name, description, ...}]}` |
| `create_thread` | `agentId`*, `message`*, `namingHint`, `attachmentIds` | threadId (returned immediately; run continues in background) |
| `send_message` | `threadId`*, `message`*, `attachmentIds` | ack |
| `get_thread` | `threadId`*, `messageLimit` | `{"thread": {id, name, namedAgentId, invocationSource, isArchived, createdAt, updatedAt}, "messages": [...], "isRunning": bool}` |
| `list_threads` | `cursor`, `limit` | threads page |
| `create_attachment_upload` | `filename`*, `mimeType`*, `sizeBytes`* | upload URL + fileId |

Observed live (2026-07-19):
- **Running flag is `isRunning`** (top-level of `get_thread`). **[C]**
- Message shape: `{id, role, content, contentBlocks, createdAt}` — `content` is
  the text; `contentBlocks` carries rich structure (likely where tool activity
  lives — relevant to the E06 tool bridge). **[C]**
- Latency for a trivial prompt: create_thread returns in ~0.1s; full run
  completes in ~15–21s end-to-end. **[C]**

**Constraint [C]: the account must have at least one *named agent*.**
`list_agents` returns only named agents ("agents you can start threads on");
an account with none returns `{"agents": []}` and no thread can be started.
This project provisions the **API Bridge** agent for gateway serving.

No other MCP tools are exposed (`tools/list` returned exactly six). The
`approvals:*` scopes imply approval capability but no approval tool exists in
the list — confirmed absent from the tool surface.

## Execution & streaming semantics

- `create_thread` returns a `threadId` **immediately**; the agent works in the
  **background**. **[C]**
- Documented loop: `create_thread` → **poll `get_thread` until not running** →
  read final messages (or `send_message` to continue). **[C]**
- **No token-level streaming.** Progress = re-poll `get_thread` and diff the
  messages array. The gateway must **emulate** OpenAI streaming this way. **[C/I]**
- `send_message` runs immediately if idle, else **queues** after the current
  turn. **[C]**
- **Cross-turn memory is unreliable [C, live 2026-07-19]:** a follow-up
  `send_message` turn did not recall a fact from the first turn on the same
  thread. Also, right after `send_message`, `get_thread` can report
  `isRunning=false` before the queued turn starts (stale last-assistant). The
  gateway therefore treats every turn as self-contained (see decision 0010) and
  waits for a NEW assistant message beyond a baseline count.

## Attachments (files)

Confirmed 3-step flow **[C]** (some field names [I], PUT headers/size/TTL [U]):
1. `create_attachment_upload` → `{ uploadUrl, fileId }`.
2. HTTP `PUT` raw bytes to `uploadUrl`.
3. Pass `fileId` to `create_thread` / `send_message`.

## What is NOT available upstream (design around these)

- No REST/GraphQL/OpenAPI/SDK. All `/api/*` paths return a blanket `401`
  (auth-middleware artifact, **not** real endpoints). `/openapi.json` → 404. **[C]**
- No embeddings, no direct single-tool RPC, no synchronous completions, no usage
  meter API documented. **[C/U]**

## Build-time task to close [U] gaps

With a real bearer token, run once and record the verbatim schemas:
```
POST https://hyperagent.com/api/mcp
Authorization: Bearer <token>
Accept: application/json, text/event-stream
{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}
```
Also call `initialize` to capture `protocolVersion` + server `capabilities`.
