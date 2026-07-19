[![English](https://img.shields.io/badge/lang-English-1f6feb?style=flat-square)](../en/07-faq.md) [![Tiếng Việt](https://img.shields.io/badge/lang-Ti%E1%BA%BFng%20Vi%E1%BB%87t-8b949e?style=flat-square)](../vi/07-faq.md) · [🏠 README](../../README.md) · [📚 Index](00-index.md)

# FAQ

### Beginner

**Do I have to change my code?** No. Set your OpenAI client's `base_url` to the
gateway and `api_key` to one of your `SHIM_API_KEYS`. Everything else stays.

**What do I put as `model`?** A Hyperagent agent id from `GET /v1/models`, or the
alias `hyperagent-default`.

**Why is it slower than ChatGPT?** Because each call runs a full *agent* (which
may search, browse, run code), not a single model inference. Seconds are normal.

**Do I need to know what MCP is?** No, to *use* it. Yes, if you want to
understand the internals — see the [Glossary](08-glossary.md).

### Using it

**Does streaming work?** Yes, as standard SSE — but it's *emulated* by polling, so
text may arrive in a few chunks rather than token-by-token.

**Can it generate images/audio?** Yes: `/v1/images/generations`,
`/v1/audio/speech`, etc. Images come back as fetchable public URLs.

**Can the model run a shell command or write a file for me?** Yes, via the
[tool bridge](05-tool-bridge.md). For safety, `shell`/`write_file` can be disabled
per key.

**How do I keep a conversation's memory?** For chat, just send the full
`messages[]` each call (standard OpenAI). For the Responses API, use
`previous_response_id` — the gateway reconstructs prior context.

**Embeddings look random / low quality.** The default embeddings are a *local
fallback* (deterministic hashing, not semantic). Wire a real provider or set
`GATEWAY_EMBEDDINGS=off`.

### Operations

**Where are my secrets stored?** OAuth tokens in `~/.hyperagent-gateway/tokens.json`
(keep `chmod 600`); never committed. See [Deployment](06-deployment.md).

**Can one gateway serve my whole team?** Yes — `GATEWAY_KEYS_FILE` maps each key
to its own Hyperagent identity + policy.

**`/v1/models` is empty.** Your account has no **named agent**. Create one in the
Hyperagent app.

**A request returned `504`.** It exceeded `GATEWAY_RUN_TIMEOUT` (default 600s).
Raise it for long agent tasks.

### Compatibility & limits

**Is it 100% OpenAI-compatible?** Core surfaces yes (the official SDK works).
Some parameters (`temperature`, `top_p`, `seed`, `logprobs`) don't apply to agent
runs and are accepted-but-ignored or return nulls. See
[API reference](04-api-reference.md).

**Is this affiliated with OpenAI?** No. It's an independent compatibility layer.

**Where's the source of truth for behavior?** The code and the tests
(`pytest tests/`).
