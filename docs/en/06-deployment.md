[![English](https://img.shields.io/badge/lang-English-1f6feb?style=flat-square)](../en/06-deployment.md) [![Tiếng Việt](https://img.shields.io/badge/lang-Ti%E1%BA%BFng%20Vi%E1%BB%87t-8b949e?style=flat-square)](../vi/06-deployment.md) · [🏠 README](../../README.md) · [📚 Index](00-index.md)

# Deployment & security

## Docker

**Compose (recommended).** Put settings in `.env` and your token bundle in
`./secrets/tokens.json`, then:

```bash
docker compose up -d --build
```

**Plain docker:**

```bash
docker build -t hyperagent-openai-gateway .
docker run -d --name gateway -p 8000:8000 --env-file .env \
  -v ~/.hyperagent-gateway:/root/.hyperagent-gateway \
  hyperagent-openai-gateway
```

Mount a volume so the OAuth token bundle and local state persist across restarts.
The image's entrypoint is the CLI (`hyperagent-gateway serve`).

## Behind a reverse proxy (HTTPS)

Run the gateway on `127.0.0.1:8000` and put Nginx/Caddy in front for TLS.

Caddy example:
```
api.example.com {
  reverse_proxy 127.0.0.1:8000
}
```
Nginx: proxy_pass to `http://127.0.0.1:8000;` and set `proxy_buffering off;` so
SSE streaming flows through.

## One-time OAuth on a server

If the server has no browser, use the two-step remote flow:

```bash
# On the server: register + print an authorize URL
hga login --remote-start --redirect https://YOUR_CALLBACK/cb
# Open the printed URL in ANY browser, approve, copy the ?code=… (and &state=…)
hga login --remote-finish --code <CODE> --state <STATE>
```
This writes `~/.hyperagent-gateway/tokens.json` with a refresh token; the gateway
auto-rotates it afterwards.

## Multi-tenant (many users, one gateway)

Create a keys file and point `GATEWAY_KEYS_FILE` at it:

```json
[
  {"api_key":"sk-alice","token_file":"~/.hyperagent-gateway/alice.json","default_agent":"<agentId>","disabled_tools":["shell"],"label":"alice"},
  {"api_key":"sk-bob","token_file":"~/.hyperagent-gateway/bob.json","label":"bob"}
]
```

- Each user runs the OAuth helper once to create their own `token_file`.
- Unknown keys get `401`. Each key acts strictly as its own Hyperagent user.
- Per-key `disabled_tools` and `default_agent` are enforced.

## Security checklist

- **Never commit secrets.** `tokens.json`, `.env`, and local state are gitignored;
  keep token files `chmod 600`.
- **Use strong `SHIM_API_KEYS`** and rotate them; treat them like OpenAI keys.
- **Lock down dangerous tools** for shared keys: `GATEWAY_DISABLED_TOOLS=shell,write_file`.
- **Terminate TLS** at the proxy; don't expose plain HTTP publicly.
- **Remember tokens act as the user** — a leaked token bundle = full access to
  that Hyperagent account. Store them in a secret manager for production.

## Scaling notes

- Runs are long (seconds). Use generous client timeouts and a process manager
  (systemd, Docker restart policy) or multiple uvicorn workers.
- `GATEWAY_RUN_TIMEOUT` caps how long the gateway waits for one run.
