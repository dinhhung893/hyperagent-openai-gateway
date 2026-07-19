# Product Docs

This directory is intentionally generic and mostly empty in Harness v0.

When a user provides a project spec, derive smaller product contract files here
instead of keeping one large spec as the living plan. Name files by the product
domains that actually exist in that spec, for example `overview.md`,
`billing.md`, `workflows.md`, `permissions.md`, or `api-conventions.md`.

Do not create domain files before the spec just to fill the folder. Empty
structure is healthier than fake product truth.

## Current Product Contracts

Project **Hyperagent.com-to-API** — an OpenAI-compatible API gateway over the
Hyperagent MCP server. Contract files:

- `overview.md` — what the gateway is and its architecture.
- `upstream-mcp.md` — confirmed MCP transport, OAuth, six tools, polling, files.
- `openai-compatibility.md` — full endpoint + attribute compatibility matrix.
- `capability-catalog.md` — complete Hyperagent tool/capability inventory.
- `tool-bridge.md` — mapping Hyperagent tools to OpenAI `tools`/`tool_calls`.
- `auth.md` — client-key ↔ Hyperagent OAuth, multi-tenant.

See also decision `docs/decisions/0009-openai-compatible-gateway-over-mcp.md`.

## Update Rule

When behavior changes:

1. Update the affected product doc.
2. Update or create the story packet.
3. Update durable proof status with `scripts/bin/harness-cli story add` or
   `scripts/bin/harness-cli story update`.
4. Record a decision if the change affects architecture, scope, risk, or a
   previously settled product rule.
