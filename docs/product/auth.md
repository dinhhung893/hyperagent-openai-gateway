# Authentication & Multi-Tenancy

Two independent auth boundaries: **client → gateway** and **gateway → Hyperagent**.

## Client → gateway (OpenAI-style)

- Clients send `Authorization: Bearer <gateway key>` exactly like OpenAI.
- Gateway keys are issued/managed by the gateway (`SHIM_API_KEYS` or a key store).
- Each gateway key maps to:
  - a **Hyperagent identity** (which stored OAuth token to use upstream), and
  - a **policy**: allowed models/agents, allowed canonical tools (e.g. permit or
    deny `shell`/`write_file`), rate limits, default agent, exec mode.
- Missing/invalid key → OpenAI `401` error envelope.

## Gateway → Hyperagent (OAuth 2.1, per-user)

Hyperagent has **no API keys** — only per-user OAuth (see `upstream-mcp.md`).
Therefore:

- Each Hyperagent user authorizes the gateway **once** via browser sign-in +
  consent (Authorization Code + PKCE, `offline_access` scope).
- The gateway stores that user's **refresh token** (encrypted at rest) and mints
  short-lived access tokens as needed; it rotates refresh tokens automatically.
- A gateway key is bound to one such stored identity → the gateway is
  **multi-tenant by Hyperagent user**. A token acts strictly **as that user**
  with no elevated access.

### Onboarding flow (one-time per user)

1. Admin/user hits `POST /admin/oauth/start` → gateway performs DCR (or uses a
   client-id metadata document), returns the `authorize` URL.
2. User completes browser sign-in + consent.
3. Gateway exchanges the code (PKCE) → stores refresh token, issues a gateway
   key bound to that identity.

In this sandbox the browser step is done via an interactive **browser handoff**;
in production it is a normal hosted redirect.

## Secrets & storage

- Refresh tokens and gateway keys are stored via env/secret manager, encrypted at
  rest; never logged. `x-request-id` from upstream is logged for support.
- No end-user credential is ever requested in chat.

## Risk classification (harness)

This area triggers hard gates: **Auth**, **External provider**, **Public
contract**. All auth changes require a decision record and high-risk validation.
