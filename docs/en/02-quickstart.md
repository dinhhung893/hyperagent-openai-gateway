[![English](https://img.shields.io/badge/lang-English-1f6feb?style=flat-square)](../en/02-quickstart.md) [![Tiếng Việt](https://img.shields.io/badge/lang-Ti%E1%BA%BFng%20Vi%E1%BB%87t-8b949e?style=flat-square)](../vi/02-quickstart.md) · [🏠 README](../../README.md) · [📚 Index](00-index.md)

# Quick start

The tool is one command — `hyperagent-gateway` (alias **`hga`**). Install it, then
two commands take you live.

## 1. Install (pick one)

| Method | Command | Best for |
| --- | --- | --- |
| **pipx** ⭐ | `pipx install git+https://github.com/dinhhung893/hyperagent-openai-gateway` | a clean global CLI |
| **uv** (zero-install) | `uvx --from git+https://github.com/dinhhung893/hyperagent-openai-gateway hyperagent-gateway serve` | just trying it |
| **Docker** | `docker compose up -d --build` | servers |
| **pip / source** | `git clone … && cd … && pip install -e .` | development |
| **one-liner** | `curl -fsSL https://raw.githubusercontent.com/dinhhung893/hyperagent-openai-gateway/main/install.sh \| bash` | guided setup |

Requires Python 3.11+ (except the Docker path).

## 2. Try it offline (no account)

```bash
hga serve --upstream mock
# in another terminal:
curl http://localhost:8000/v1/chat/completions -H "content-type: application/json" \
  -d '{"model":"agent_default","messages":[{"role":"user","content":"Hello"}]}'
```

## 3. Connect the real Hyperagent

```bash
hga login                 # one-time browser sign-in; stores a refreshable token
hga agents                # confirm your agents appear
hga serve                 # start on http://localhost:8000/v1
```

`hga login` opens your browser (Google/Apple/Microsoft) and writes the token to
`~/.hyperagent-gateway/tokens.json`. On a headless server, use the two-step remote
flow — see [Deployment](06-deployment.md#one-time-oauth-on-a-server).

> You need at least one **named agent** in Hyperagent (the MCP server only starts
> threads on named agents). If `hga agents` is empty, create one in the Hyperagent
> app.

## 4. Configure with a `.env` (optional, recommended)

Instead of long inline env vars, run `hga init` (interactive) or drop a `.env`:

```bash
# ~/.hyperagent-gateway/.env  (or ./.env in your working dir)
GATEWAY_UPSTREAM=mcp
SHIM_API_KEYS=sk-mylocalkey
GATEWAY_PORT=8000
```

Precedence: CLI flags → environment → `.env` (current dir, then home) → defaults.

## 5. Point your client at it

**OpenAI Python SDK**
```python
from openai import OpenAI
client = OpenAI(base_url="http://localhost:8000/v1", api_key="sk-mylocalkey")
print(client.chat.completions.create(
    model="hyperagent-default",
    messages=[{"role":"user","content":"Summarize today's AI news"}]).choices[0].message.content)
```

**Cursor / Continue / LibreChat / OpenWebUI:** Base URL `http://localhost:8000/v1`,
API key = one of your `SHIM_API_KEYS`, model = an agent id from `hga agents`.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `hga agents` empty | Create a **named agent** in Hyperagent. |
| `401 Invalid API key` | Client key isn't in `SHIM_API_KEYS`. |
| "No Hyperagent OAuth token" | Run `hga login` (or set `HYPERAGENT_TOKEN_FILE`). |
| First real call is slow | Normal — a full agent runs. Raise `GATEWAY_RUN_TIMEOUT` if needed. |
| Not sure what's wrong | Run `hga doctor`. |

Next: [Architecture](03-architecture.md) · [API reference](04-api-reference.md).
