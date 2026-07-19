[![English](https://img.shields.io/badge/lang-English-1f6feb?style=flat-square)](../en/02-quickstart.md) [![Tiếng Việt](https://img.shields.io/badge/lang-Ti%E1%BA%BFng%20Vi%E1%BB%87t-8b949e?style=flat-square)](../vi/02-quickstart.md) · [🏠 README](../../README.md) · [📚 Index](00-index.md)

# Quick start

Two ways to run: **offline (mock)** to see it work in 30 seconds, then **real**
against Hyperagent.

## 0. Requirements

- Python **3.11+** (`python3.11 --version`)
- A terminal. No database or cloud account needed for the mock mode.

## 1. Install

```bash
git clone https://github.com/dinhhung893/hyperagent-openai-gateway.git
cd hyperagent-openai-gateway
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## 2. Run offline (mock upstream)

The **mock** upstream fakes Hyperagent so you can test the OpenAI surface with no
account:

```bash
GATEWAY_UPSTREAM=mock uvicorn gateway.app:app --port 8000
```

In another terminal:

```bash
curl http://localhost:8000/v1/models
# → {"object":"list","data":[{"id":"agent_default",...},{"id":"agent_research",...}]}

curl http://localhost:8000/v1/chat/completions -H "content-type: application/json" \
  -d '{"model":"agent_default","messages":[{"role":"user","content":"Hello"}]}'
# → a chat.completion echoing your message
```

That confirms the gateway works. Now let's connect the real thing.

## 3. Authorize Hyperagent (one time)

Hyperagent has **no API keys** — you log in through a browser once, and the
gateway stores a refreshable token.

```bash
python tools/oauth_login.py --out ~/.hyperagent-gateway/tokens.json
```

This opens your browser, you sign in (Google/Apple/Microsoft) and approve. A
token bundle is written to `~/.hyperagent-gateway/tokens.json` (keep it secret).

> On a headless server (no browser), use `tools/oauth_remote.py` — see
> [Deployment](06-deployment.md#one-time-oauth-on-a-server).

**You also need at least one named agent** in your Hyperagent account (the MCP
server only starts threads on named agents). Create one in the Hyperagent app; a
good choice is an agent tuned to answer API requests (this repo used one named
**API Bridge**).

## 4. Run against real Hyperagent

```bash
GATEWAY_UPSTREAM=mcp \
SHIM_API_KEYS=sk-mylocalkey \
HYPERAGENT_TOKEN_FILE=~/.hyperagent-gateway/tokens.json \
uvicorn gateway.app:app --port 8000
```

- `SHIM_API_KEYS` = the key(s) your client must send (like an OpenAI key). Leave
  empty only for local dev.

Check your real agents appear:

```bash
curl http://localhost:8000/v1/models -H "authorization: Bearer sk-mylocalkey"
```

Send a real chat (this runs a full agent — it can take tens of seconds):

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "authorization: Bearer sk-mylocalkey" -H "content-type: application/json" \
  -d '{"model":"hyperagent-default","messages":[{"role":"user","content":"What is the capital of Vietnam? One word."}]}'
```

## 5. Point your favorite client at it

**OpenAI Python SDK**
```python
from openai import OpenAI
client = OpenAI(base_url="http://localhost:8000/v1", api_key="sk-mylocalkey")
print(client.chat.completions.create(
    model="hyperagent-default",
    messages=[{"role":"user","content":"Summarize today's AI news"}]).choices[0].message.content)
```

**Cursor / Continue / LibreChat / OpenWebUI**
- OpenAI Base URL: `http://localhost:8000/v1`
- API key: `sk-mylocalkey`
- Model: an agent id from `/v1/models` (or `hyperagent-default`)

## Troubleshooting

| Symptom | Cause & fix |
| --- | --- |
| `/v1/models` returns empty list | No **named agent** in your account. Create one in Hyperagent. |
| `401 Invalid API key` | Your client's key isn't in `SHIM_API_KEYS`. |
| `No Hyperagent OAuth token` | Run `tools/oauth_login.py` and set `HYPERAGENT_TOKEN_FILE`. |
| First real call is slow | Normal — the agent runs a full pipeline. Increase `GATEWAY_RUN_TIMEOUT` if needed. |
| `504 upstream_timeout` | The run took longer than `GATEWAY_RUN_TIMEOUT` (default 600s). Raise it. |

Next: [Architecture](03-architecture.md) or [API reference](04-api-reference.md).
