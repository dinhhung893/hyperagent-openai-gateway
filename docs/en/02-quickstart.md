[![English](https://img.shields.io/badge/lang-English-1f6feb?style=flat-square)](../en/02-quickstart.md) [![Tiếng Việt](https://img.shields.io/badge/lang-Ti%E1%BA%BFng%20Vi%E1%BB%87t-8b949e?style=flat-square)](../vi/02-quickstart.md) · [🏠 README](../../README.md) · [📚 Index](00-index.md)

# Quick start

The tool is one command — `hyperagent-gateway` (alias **`hga`**). Install it, then
two commands take you live.

## 1. Install

**Prerequisites:** Python 3.11+ (except Docker). On **Windows**, install Python from
[python.org](https://www.python.org/downloads/) with *"Add python.exe to PATH"*
checked (gives you the `py` launcher).

**Universal (Windows / macOS / Linux):**

```bash
pip install git+https://github.com/dinhhung893/hyperagent-openai-gateway
# Windows PowerShell, if pip isn't on PATH:
py -m pip install git+https://github.com/dinhhung893/hyperagent-openai-gateway
```

You get the `hyperagent-gateway` command (alias `hga`). If the shell can't find it,
`python -m gateway.cli …` (Windows: `py -m gateway.cli …`) is the exact equivalent.

**Other methods**

| Method | macOS / Linux | Windows (PowerShell) |
| --- | --- | --- |
| pipx | `pipx install git+…` | `py -m pip install --user pipx; py -m pipx ensurepath` → reopen → `pipx install git+…` |
| uv | `uvx --from git+… hyperagent-gateway serve` | `irm https://astral.sh/uv/install.ps1 \| iex` → `uvx …` |
| Docker | `docker compose up -d --build` | `docker compose up -d --build` |
| one-liner | `curl -fsSL …/install.sh \| bash` | `irm …/install.ps1 \| iex` |

> **Windows/PowerShell:** `curl` is an alias for `Invoke-WebRequest` and there is no
> `bash`; the `curl … | bash` line is macOS/Linux/WSL only — use `install.ps1`.

> Below, if `hga` isn't found on Windows, replace `hga` with `py -m gateway.cli`.

## 2. Try it offline (no account)

Start the server (mock upstream):

```bash
hga serve --upstream mock          # or:  py -m gateway.cli serve --upstream mock
```

Then send a test request from another terminal:

```bash
# macOS / Linux
curl http://localhost:8000/v1/chat/completions -H "content-type: application/json" \
  -d '{"model":"agent_default","messages":[{"role":"user","content":"Hello"}]}'
```

```powershell
# Windows PowerShell — its `curl` is Invoke-WebRequest, so use this:
Invoke-RestMethod -Uri http://localhost:8000/v1/chat/completions -Method Post `
  -ContentType 'application/json' `
  -Body '{"model":"agent_default","messages":[{"role":"user","content":"Hello"}]}'
```

> Non-ASCII text (Vietnamese, etc.) works too — the gateway auto-repairs Windows
> Latin-1/CP1252 bodies. For strict correctness use PowerShell 7, or
> `-Body ([Text.Encoding]::UTF8.GetBytes($body))`.

No curl needed at all? Just run `hga agents` — if it lists agents, it works.

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
