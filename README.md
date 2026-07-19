<!-- LANGUAGE SWITCH -->
[![English](https://img.shields.io/badge/README-English-1f6feb?style=for-the-badge)](README.md) [![Tiếng Việt](https://img.shields.io/badge/README-Ti%E1%BA%BFng%20Vi%E1%BB%87t-8b949e?style=for-the-badge)](README.vi.md)

# Hyperagent → OpenAI-Compatible API Gateway

![Python](https://img.shields.io/badge/Python-3.11+-3776ab?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-async-009688?logo=fastapi&logoColor=white)
![Tests](https://img.shields.io/badge/tests-46%20passing-3fb950)
![Upstream](https://img.shields.io/badge/upstream-Hyperagent%20MCP-7c5cff)

**Run Hyperagent.com behind an OpenAI-compatible API.** Point any OpenAI client
(the `openai` SDK, Cursor, Continue, LibreChat, LangChain, …) at this gateway and
call the endpoints you already know — `/v1/chat/completions`, `/v1/models`,
`/v1/responses`, and more. The gateway translates each request into Hyperagent
operations and returns responses in exact OpenAI wire format (streaming
included).

> **In one sentence:** your existing OpenAI code keeps working, but the "model"
> answering is a full Hyperagent **agent** that can search the web, run code,
> use a browser, generate media, and call your integrations.

📚 **Full documentation:** [English docs](docs/en/00-index.md) ·
[Tài liệu tiếng Việt](docs/vi/00-index.md)

---

## Table of contents

- [What is this?](#what-is-this)
- [How it works](#how-it-works)
- [Quick start](#quick-start)
- [Connect your client](#connect-your-client)
- [Supported endpoints](#supported-endpoints)
- [The tool bridge](#the-tool-bridge-shell-write-web-)
- [Multi-user / multi-tenant](#multi-user--multi-tenant)
- [Configuration](#configuration)
- [Deployment](#deployment)
- [Testing](#testing)
- [Project structure](#project-structure)
- [Limitations](#limitations)
- [FAQ](#faq)
- [License](#license)

---

## What is this?

The **OpenAI API** is a de-facto standard: a huge amount of software knows how to
"talk" to it. **Hyperagent.com** is a platform where AI *agents* do real work
inside persistent *threads* (research, code, browser automation, media, files,
integrations). Its only public programmatic door is a **hosted MCP server**
(Model Context Protocol) — not an OpenAI-style API.

This project is the **adapter** between those two worlds. Think of it as a
universal power plug: your device (the OpenAI client) plugs in the same way as
always, and behind the wall the electricity actually comes from Hyperagent.

**Who is it for?**
- People who already have OpenAI-based apps and want an agent backend without
  rewriting their code.
- Tools that only speak "OpenAI" (IDEs, chat UIs) but want Hyperagent's power.

New to these terms? Start with [Overview & concepts](docs/en/01-overview.md).

## How it works

```text
OpenAI-compatible client  (Cursor, Continue, LibreChat, openai SDK, …)
        │  HTTP:  POST /v1/chat/completions   (Authorization: Bearer <gateway key>)
        ▼
┌───────────────────────────────────────────────┐
│  Gateway (FastAPI)                             │
│  • Auth: gateway key → a Hyperagent identity   │
│  • Translate: OpenAI  ⇄  Hyperagent thread ops │
│  • UpstreamAdapter:  MCP (real)  |  Mock (dev) │
└───────────────────────────────────────────────┘
        │  MCP JSON-RPC 2.0 over HTTPS  (OAuth 2.1 Bearer token)
        ▼
Hyperagent MCP server   https://hyperagent.com/api/mcp
        │  list_agents · create_thread · get_thread (poll) · send_message · …
        ▼
Your Hyperagent agent runs the request end-to-end
(web search, browser, shell, files, images/audio, integrations)
```

Key ideas:
- **`model` = a Hyperagent agent.** `GET /v1/models` lists your agents; pick one
  as the `model`, or use the alias `hyperagent-default`.
- **A request = a thread run.** Hyperagent runs in the background, so the gateway
  **polls** until the answer is ready.
- **Streaming is emulated.** Hyperagent doesn't stream tokens, so the gateway
  turns poll updates into standard OpenAI SSE chunks.
- **Stateless by design.** Every call is self-contained (see
  [Architecture](docs/en/03-architecture.md)); the gateway never relies on
  fragile upstream memory.

## Quick start

**Prerequisites:** Python 3.11+ (except the Docker path). On **Windows**, install
Python from [python.org](https://www.python.org/downloads/) and tick *"Add
python.exe to PATH"* — that also gives you the `py` launcher.

**1. Install — the universal way** (works on Windows, macOS, Linux):

```bash
pip install git+https://github.com/dinhhung893/hyperagent-openai-gateway
```
> Windows PowerShell: if `pip` isn't found, use `py -m pip install git+…`.

This gives the `hyperagent-gateway` command (alias `hga`). If your shell can't find
it, the exact equivalent always works: `python -m gateway.cli …`
(Windows: `py -m gateway.cli …`).

<details><summary><b>Other install methods</b> — pipx · uv · Docker · one-liner</summary>

| Method | macOS / Linux | Windows (PowerShell) |
| --- | --- | --- |
| **pipx** | `pipx install git+…` | `py -m pip install --user pipx; py -m pipx ensurepath` → reopen shell → `pipx install git+…` |
| **uv** | `uvx --from git+… hyperagent-gateway serve` | `irm https://astral.sh/uv/install.ps1 \| iex` → `uvx --from git+… hyperagent-gateway serve` |
| **Docker** | `docker compose up -d --build` | `docker compose up -d --build` |
| **one-liner** | `curl -fsSL https://raw.githubusercontent.com/dinhhung893/hyperagent-openai-gateway/main/install.sh \| bash` | `irm https://raw.githubusercontent.com/dinhhung893/hyperagent-openai-gateway/main/install.ps1 \| iex` |

> **Windows note:** in PowerShell, `curl` is an alias for `Invoke-WebRequest` and
> there is no `bash`, so the `curl … \| bash` line is for macOS/Linux/WSL only.
> Use `install.ps1` (via `irm … \| iex`) instead.
</details>

**2. Go live — two commands:**

```bash
hga login      # one-time Hyperagent sign-in (opens a browser)
hga serve      # serves http://localhost:8000/v1
```
> Windows without the command on PATH: `py -m gateway.cli login` then `py -m gateway.cli serve`.

**Just trying it?** No account needed — run against the built-in mock:

```bash
hga serve --upstream mock          # or:  py -m gateway.cli serve --upstream mock
```

> Your Hyperagent account needs at least one **named agent** (the MCP server only
> starts threads on named agents). Check with `hga agents`.

Full walkthrough: [Quick start](docs/en/02-quickstart.md).

## Command-line interface

`hyperagent-gateway` (alias `hga`):

| Command | What it does |
| --- | --- |
| `hga init` | Write `~/.hyperagent-gateway/.env` (interactive; `--yes` for defaults) |
| `hga login` | One-time OAuth (`--remote-start` / `--remote-finish` for headless servers) |
| `hga serve` | Run the gateway (`--port`, `--upstream mcp\|mock`, `--reload`, …) |
| `hga agents` | List your Hyperagent agents |
| `hga doctor` | Check config + upstream reachability |
| `hga quickstart` | `login` (if needed) then `serve` |

**Config is auto-loaded** with precedence: CLI flags → environment → `.env` (current
dir, then `~/.hyperagent-gateway/.env`) → defaults. So you can drop a `.env` and
skip long inline env vars. (`uvicorn gateway.app:app` still works for power users.)

## Connect your client

**OpenAI Python SDK**

```python
from openai import OpenAI
client = OpenAI(base_url="http://localhost:8000/v1", api_key="sk-mylocalkey")
print(client.models.list())                     # your Hyperagent agents
r = client.chat.completions.create(
    model="hyperagent-default",
    messages=[{"role": "user", "content": "Research the latest on X and summarize"}],
)
print(r.choices[0].message.content)
```

**curl**

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "authorization: Bearer sk-mylocalkey" -H "content-type: application/json" \
  -d '{"model":"hyperagent-default","messages":[{"role":"user","content":"Hello"}],"stream":true}'
```

**Cursor / Continue / LibreChat / OpenWebUI:** set the OpenAI **Base URL** to
`http://localhost:8000/v1`, the **API key** to one of your `SHIM_API_KEYS`, and
the **model** to an agent id from `GET /v1/models`.

## Supported endpoints

| Endpoint | Status |
| --- | --- |
| `GET /v1/models`, `/v1/models/{id}` | ✅ lists your Hyperagent agents |
| `POST /v1/chat/completions` (stream + non-stream) | ✅ |
| `POST /v1/responses` (+ background, cancel, input_items, stateful chains) | ✅ |
| `GET /v1/tools` + forced `tool_choice` | ✅ tool bridge |
| `POST /v1/completions` (legacy) | ✅ |
| `POST /v1/images/generations`, `/v1/images/edits` | ✅ real fetchable URLs |
| `POST /v1/audio/speech`, `/transcriptions`, `/translations` | ✅ |
| `POST /v1/files`, `GET/DELETE /v1/files/{id}`, `/content` | ✅ + chat attachments |
| `POST /v1/embeddings` | ✅ local fallback (or `501` if disabled) |
| `POST /v1/moderations` | ✅ heuristic |

Full parameter-by-parameter behavior: [API reference](docs/en/04-api-reference.md).

## The tool bridge (Shell, Write, web, …)

Hyperagent agents have a rich toolbox (bash/shell, file read/write, web search,
browser, image/video/audio, tables, docs, maps, integrations). The gateway
exposes all of it through OpenAI's standard `tools` / `tool_calls` in three modes:

- **Observe** — an agent's tool activity shows up as `tool_calls` in the reply.
- **Direct** — force a capability with `tool_choice`.
- **Run** — a tool-runner executes a tool directly (e.g. run a shell command)
  and returns the result.

`GET /v1/tools` returns the full catalog. Details + examples:
[Tool bridge](docs/en/05-tool-bridge.md).

## Multi-user / multi-tenant

One gateway can serve many Hyperagent users. Map each API key to its own
Hyperagent identity and policy via `GATEWAY_KEYS_FILE`:

```json
[{"api_key":"sk-alice","token_file":"~/.hyperagent-gateway/alice.json","disabled_tools":["shell"]},
 {"api_key":"sk-bob","token_file":"~/.hyperagent-gateway/bob.json"}]
```

Each user authorizes once with `tools/oauth_login.py`. See
[Deployment & security](docs/en/06-deployment.md).

## Configuration

| Variable | Default | Meaning |
| --- | --- | --- |
| `GATEWAY_UPSTREAM` | `mcp` | `mcp` (real) or `mock` (offline) |
| `HYPERAGENT_MCP_URL` | `https://hyperagent.com/api/mcp` | upstream endpoint |
| `HYPERAGENT_TOKEN_FILE` | `~/.hyperagent-gateway/tokens.json` | OAuth token bundle |
| `SHIM_API_KEYS` | (empty = dev) | comma-separated client keys |
| `GATEWAY_KEYS_FILE` | (none) | multi-tenant identity map (JSON) |
| `GATEWAY_DEFAULT_AGENT` | (first agent) | agent for `hyperagent-default` |
| `GATEWAY_EXEC_MODE` | `roundtrip` | tool-runner mode: `roundtrip` or `auto` |
| `GATEWAY_DISABLED_TOOLS` | (none) | hide tools, e.g. `shell,write_file` |
| `GATEWAY_EMBEDDINGS` | `fallback` | `fallback` or `off` |
| `GATEWAY_POLL_INTERVAL` / `GATEWAY_RUN_TIMEOUT` | `1.0` / `600` | polling |

## Deployment

Docker Compose (recommended for servers) — put settings in `.env` and your token
bundle in `./secrets/tokens.json`:

```bash
docker compose up -d --build
```

Full guide (VPS, reverse proxy, HTTPS, multi-tenant, headless OAuth):
[Deployment](docs/en/06-deployment.md).

## Testing

```bash
python3.11 -m pytest tests/ -q     # 46 tests: unit + ASGI API + OpenAI SDK
```

## Project structure

```text
gateway/            FastAPI app + translation + upstream adapters
  app.py            all HTTP routes
  upstream/         mcp.py (real) · mock.py (dev) · base.py · manager.py
  translate.py streaming.py toolbridge.py fallbacks.py media.py auth.py …
tools/              oauth_login.py, oauth_remote.py (one-time OAuth helpers)
tests/              46 tests (mock upstream + OpenAI SDK)
docs/en/  docs/vi/  bilingual documentation
Dockerfile  requirements.txt  pyproject.toml
```

## Limitations

- **Latency:** each call runs a full agent pipeline — expect seconds, not
  milliseconds.
- **Streaming is emulated** (poll-based), not true token streaming.
- **Sampling knobs** (`temperature`, `top_p`, `seed`) are best-effort / no-ops.
- **Embeddings** use a local non-semantic fallback unless you wire a real provider.
- **Auth** is per-user OAuth (Hyperagent has no API keys); the gateway stores and
  refreshes each user's token.

## FAQ

A few quick ones (full list: [FAQ](docs/en/07-faq.md)):

- **Do I need to change my OpenAI code?** No — just the `base_url` and `api_key`.
- **Which model do I pass?** A Hyperagent agent id (`GET /v1/models`) or
  `hyperagent-default`.
- **Is it really OpenAI-compatible?** Yes; the official `openai` SDK works
  unmodified (tested).

## License

No license file is included yet. Until one is added, all rights are reserved by
the repository owner. Open an issue if you'd like a specific license (e.g. MIT).

---

<sub>Built on the Hyperagent MCP server. "OpenAI" is a trademark of OpenAI; this
project is an independent compatibility layer and is not affiliated with OpenAI.</sub>
