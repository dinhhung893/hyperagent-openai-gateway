# Story Backlog

This backlog will be populated after a user provides a project spec or selects a
specific initiative.

Do not create every possible story packet up front. Create story packets when
the work is selected or when a product decision needs a durable place to land.

## Candidate Epics

Derived from intake #1 (Hyperagent → OpenAI-compatible API gateway). Slice into
story packets when selected; high-risk epics use `docs/templates/high-risk-story/`.

| Epic | Description | Risk | Status |
| --- | --- | --- | --- |
| E01 Service scaffold | FastAPI app, config, `/v1/health`, `UpstreamAdapter` interface + `MockAdapter`, test harness | normal | unsliced |
| E02 MCP upstream adapter | MCP JSON-RPC client, OAuth token store/refresh, `list_agents`/`create_thread`/`send_message`/`get_thread`, live `tools/list` schema capture | high-risk | unsliced |
| E03 Models endpoint | `GET /v1/models` + `/v1/models/{id}` from `list_agents`; model↔agent cache | normal | unsliced |
| E04 Chat Completions (non-stream) | Full request-attribute handling; messages→thread; poll→response; OpenAI response + error envelope | high-risk | unsliced |
| E05 Streaming | Emulated SSE `chat.completion.chunk` via poll diff; `stream_options` | normal | unsliced |
| E06 Tool bridge | Canonical tool catalog, `GET /v1/tools`, observability + directed + tool-runner modes (Shell/Write/etc.) | high-risk | unsliced |
| E07 Responses API | `POST /v1/responses` (+ retrieve/cancel/input_items), background + `previous_response_id`→thread | high-risk | unsliced |
| E08 Media & audio | `/v1/images/*`, `/v1/audio/{speech,transcriptions,translations}` → agent media tools | normal | unsliced |
| E09 Files | `/v1/files*` → `create_attachment_upload` + gateway file registry | normal | unsliced |
| E10 Auth & onboarding | Gateway keys + policy; per-user Hyperagent OAuth onboarding + refresh; multi-tenant | high-risk | unsliced |
| E11 Embeddings & long tail | `/v1/embeddings` fallback (skill or 501), `/v1/moderations`, `/v1/completions`, batches | normal | unsliced |
| E12 Packaging & docs | Dockerfile, compose, README quickstart, client examples, test matrix wiring | tiny | unsliced |
