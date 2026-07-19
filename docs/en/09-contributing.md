[![English](https://img.shields.io/badge/lang-English-1f6feb?style=flat-square)](../en/09-contributing.md) [![Tiếng Việt](https://img.shields.io/badge/lang-Ti%E1%BA%BFng%20Vi%E1%BB%87t-8b949e?style=flat-square)](../vi/09-contributing.md) · [🏠 README](../../README.md) · [📚 Index](00-index.md)

# Contributing & development

## Dev setup

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install pytest pytest-asyncio openai   # dev extras
python3.11 -m pytest tests/ -q             # 46 tests, all green
```

Tests use the **mock** upstream, so no network or account is needed.

## Code layout

See [Architecture](03-architecture.md). The golden rule: keep OpenAI translation
*above* the `UpstreamAdapter` and Hyperagent specifics *below* it.

## Adding a new endpoint (recipe)

1. Add a route in `gateway/app.py`.
2. Reuse `_run(...)` (create/continue a thread + wait) or the store for state.
3. Translate to/from OpenAI shapes in `gateway/translate.py`.
4. Add a test in `tests/` using the mock adapter (and, if user-facing, an
   `openai` SDK test).
5. Update the docs in **both** `docs/en/` and `docs/vi/` (keep them in sync).

## Conventions

- Be honest about limits: prefer an explicit `501` over faking a feature.
- Keep every upstream turn self-contained (see the stateless design in
  [Architecture](03-architecture.md)) — never rely on upstream cross-turn memory.
- Keep English and Vietnamese docs in sync; both carry the language-switch header.
- Run `pytest tests/ -q` before opening a PR.

## Reporting issues

Open a GitHub issue with: what you did, what you expected, what happened, and the
`x-request-id` header if the error came from upstream.
