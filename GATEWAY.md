# Hyperagent → OpenAI-Compatible Gateway

Run Hyperagent.com behind an OpenAI-compatible API. Point any OpenAI client's
`base_url` at this gateway and call `/v1/chat/completions`, `/v1/models`,
`/v1/responses`, and more. Full spec: `docs/product/`. This file is the operator
quickstart.

## Install

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # or: pip install -e .
```

## Run

**Offline / mock upstream** (no Hyperagent account — great for trying clients):

```bash
GATEWAY_UPSTREAM=mock python -m gateway         # serves on :8000
# or: GATEWAY_UPSTREAM=mock uvicorn gateway.app:app --port 8000
```

**Real Hyperagent upstream** (needs a one-time OAuth token, see below):

```bash
GATEWAY_UPSTREAM=mcp \
SHIM_API_KEYS=sk-mylocalkey \
HYPERAGENT_TOKEN_FILE=~/.hyperagent-gateway/tokens.json \
uvicorn gateway.app:app --port 8000
```

## Requirement: at least one named agent

The MCP upstream only starts threads on **named agents**. If `GET /v1/models`
returns an empty list, create a named agent in Hyperagent first (this project
uses the **API Bridge** agent, whose system prompt is tuned for serving API
responses). The OpenAI `model` field accepts the agent **id**, its exact
**name** (e.g. `"API Bridge"`), or the alias `hyperagent-default`.

**Live-verified (2026-07-19):** `/v1/models` ~0.3s; non-stream chat ~17s;
streamed chat ~15s for short prompts (full agent pipeline per call — expect
tens of seconds, not milliseconds).

## One-time Hyperagent OAuth (real upstream)

Hyperagent's MCP server uses OAuth 2.1 (browser sign-in; **no API keys**). Run the
helper once on a machine with a browser; it performs Dynamic Client Registration
+ PKCE, opens the sign-in page, and writes a refresh-capable token bundle:

```bash
python tools/oauth_login.py --out ~/.hyperagent-gateway/tokens.json
```

The gateway then loads that bundle and auto-refreshes. See `docs/product/auth.md`.

## Use it from any OpenAI client

**curl**

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "authorization: Bearer sk-mylocalkey" -H "content-type: application/json" \
  -d '{"model":"<agentId>","messages":[{"role":"user","content":"Hello"}]}'
```

**OpenAI Python SDK**

```python
from openai import OpenAI
client = OpenAI(base_url="http://localhost:8000/v1", api_key="sk-mylocalkey")
print(client.models.list())                      # your Hyperagent agents
r = client.chat.completions.create(
    model="<agentId>",                            # or "hyperagent-default"
    messages=[{"role": "user", "content": "Research X and summarize"}],
)
print(r.choices[0].message.content)
```

**Cursor / Continue / LibreChat / OpenWebUI:** set the OpenAI base URL to
`http://localhost:8000/v1` and the API key to one of your `SHIM_API_KEYS`. Pick a
model = a Hyperagent agent id (from `GET /v1/models`).

## Endpoints (Phase 1)

| Endpoint | State |
| --- | --- |
| `GET /v1/health`, `GET /v1/models`, `GET /v1/models/{id}` | ✅ |
| `POST /v1/chat/completions` (stream + non-stream) | ✅ |
| `POST /v1/responses`, `GET /v1/responses/{id}` (+ background) | ✅ core |
| `GET /v1/tools` (Hyperagent tool catalog as OpenAI tools) | ✅ |
| `POST /v1/completions` (legacy) | ✅ |
| `POST /v1/files`, `GET /v1/files/{id}` | ✅ basic |
| `GET /v1/tools` + forced `tool_choice` (shell/write_file/… via `tool_calls`) | ✅ Mode A/B/C |
| `POST /v1/images/generations`+`/edits` (publish-public → fetchable URL) | ✅ live |
| `POST /v1/audio/speech`, `/transcriptions`, `/translations` | ✅ |
| `POST /v1/embeddings` (local hashing fallback), `/v1/moderations` (heuristic) | ✅ |

**Tool bridge exec mode:** `GATEWAY_EXEC_MODE=roundtrip` (default — the gateway
emits a `tool_call` for the client to run) or `auto` (a Hyperagent tool-runner
agent executes the forced tool and returns its result). Restrict tools per key
with `GATEWAY_DISABLED_TOOLS=shell,write_file`.

**Responses API** (`/v1/responses`): sync, `background:true` + poll `GET
/v1/responses/{id}`, SSE `stream:true`, `POST .../cancel`, `GET .../input_items`,
and stateful chains via `previous_response_id`. **Files**: upload/list/get/
`/content`/delete; reference an uploaded `file_id` in a chat `file` content part
to attach it.

**Multi-tenant (per-user OAuth):** set `GATEWAY_KEYS_FILE` to a JSON array
mapping each gateway key to a Hyperagent identity + policy:

```json
[{"api_key":"sk-alice","token_file":"~/.hyperagent-gateway/alice.json",
  "default_agent":"<agentId>","disabled_tools":["shell"],"label":"alice"},
 {"api_key":"sk-bob","token_file":"~/.hyperagent-gateway/bob.json"}]
```

Each user runs `tools/oauth_login.py` (or the remote handoff variant) once to
mint their own token bundle. Unknown keys are rejected; each key acts strictly as
its own Hyperagent user.

**State model (decision 0010):** the gateway is stateless per call — chat
flattens full history into a fresh thread; Responses reconstructs prior context
from `previous_response_id`. It never relies on upstream cross-turn memory.

Full attribute-level behavior: `docs/product/openai-compatibility.md`.

## Configuration (env vars)

| Var | Default | Meaning |
| --- | --- | --- |
| `GATEWAY_UPSTREAM` | `mcp` | `mcp` or `mock` |
| `HYPERAGENT_MCP_URL` | `https://hyperagent.com/api/mcp` | upstream endpoint |
| `HYPERAGENT_TOKEN_FILE` | `~/.hyperagent-gateway/tokens.json` | OAuth bundle |
| `SHIM_API_KEYS` | (empty = dev, allow any) | comma-separated client keys |
| `GATEWAY_DEFAULT_AGENT` | (first agent) | agent for `hyperagent-default` |
| `GATEWAY_POLL_INTERVAL` | `1.0` | seconds between `get_thread` polls |
| `GATEWAY_RUN_TIMEOUT` | `600` | max seconds per run |
| `GATEWAY_DISABLED_TOOLS` | (none) | canonical tools to hide, e.g. `shell,write_file` |
| `GATEWAY_STATE_PATH` | `~/.hyperagent-gateway/state.db` | conversation/file registry |

## Test

```bash
python3.11 -m pytest tests/ -q     # 30 passing (unit + ASGI API + OpenAI SDK)
```

## Docker

```bash
docker build -t hyperagent-openai-gateway .
docker run -p 8000:8000 -e GATEWAY_UPSTREAM=mock hyperagent-openai-gateway
```
