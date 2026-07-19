[![English](https://img.shields.io/badge/lang-English-1f6feb?style=flat-square)](../en/04-api-reference.md) [![Tiếng Việt](https://img.shields.io/badge/lang-Ti%E1%BA%BFng%20Vi%E1%BB%87t-8b949e?style=flat-square)](../vi/04-api-reference.md) · [🏠 README](../../README.md) · [📚 Index](00-index.md)

# API reference

Base URL: `http://<host>:8000/v1`. Auth: `Authorization: Bearer <gateway key>`.
All responses use OpenAI wire format. Errors use the OpenAI envelope:

```json
{ "error": { "message": "…", "type": "invalid_request_error", "param": "model", "code": "model_not_found" } }
```

## `GET /v1/models` · `GET /v1/models/{id}`
Lists your Hyperagent agents as OpenAI models (`id`, `owned_by:"hyperagent"`,
`metadata` with name/description). Use an `id` as the `model` field, or the alias
`hyperagent-default`.

## `POST /v1/chat/completions`
The core endpoint. Body highlights:

| Field | Behavior |
| --- | --- |
| `model` | Agent id or `hyperagent-default`. |
| `messages[]` | Roles `system`/`developer`/`user`/`assistant`/`tool`; string or content-parts (`text`, `image_url`, `input_audio`, `file`). |
| `stream` | `true` → SSE `chat.completion.chunk` + `[DONE]` (emulated). |
| `stream_options.include_usage` | Adds a final usage chunk. |
| `tools`, `tool_choice`, `parallel_tool_calls` | The [tool bridge](05-tool-bridge.md). |
| `response_format` | `text`, `json_object`, or `json_schema` (validated). |
| `max_tokens`/`max_completion_tokens`, `reasoning_effort` | Mapped to agent budget/effort (best-effort). |
| `temperature`, `top_p`, `seed`, penalties, `logit_bias` | Accepted, no-op. |
| `n`, `stop` | Best-effort. |

**Example**
```bash
curl .../v1/chat/completions -H "authorization: Bearer sk-..." -H "content-type: application/json" -d '{
  "model":"hyperagent-default",
  "messages":[{"role":"system","content":"Be terse."},{"role":"user","content":"2+2?"}]
}'
```
Response: a standard `chat.completion` with `choices[0].message.content`. If the
agent used tools, `choices[0].message.tool_calls[]` is present and
`finish_reason` is `tool_calls`.

## `POST /v1/responses` (+ lifecycle)
The stateful, agentic surface — the closest match to Hyperagent threads.

- `input` (string or items), `instructions`, `tools`, `tool_choice`
- `stream: true` → events `response.created` → `response.output_text.delta` → `response.completed`
- `background: true` → returns `status:"in_progress"`; poll `GET /v1/responses/{id}`
- `previous_response_id` → **stateful chain** (prior context reconstructed)
- `POST /v1/responses/{id}/cancel` → marks the response cancelled (best-effort)
- `GET /v1/responses/{id}/input_items` → the input messages

**Stateful example** (verified live):
```bash
# 1) store a fact
curl .../v1/responses -d '{"model":"hyperagent-default","input":"Remember the code SPARROW-42. Reply: stored."}'
# → {"id":"resp_abc",...,"output_text":"stored."}
# 2) recall it
curl .../v1/responses -d '{"model":"hyperagent-default","input":"What was the code?","previous_response_id":"resp_abc"}'
# → output_text: "SPARROW-42"
```

## `POST /v1/completions` (legacy)
Prompt in, single text choice out. Maps to a thread run.

## `GET /v1/tools`
Returns the canonical Hyperagent tool catalog as OpenAI tool definitions (honors
per-key disabled tools). See [Tool bridge](05-tool-bridge.md).

## `POST /v1/images/generations` · `/v1/images/edits`
Runs the agent's image tool and returns fetchable public URLs:
```json
{ "created": 0, "data": [ { "url": "https://pub.hyperagent.com/...png", "revised_prompt": "…" } ] }
```

## `POST /v1/audio/speech` · `/transcriptions` · `/translations`
- **speech**: text → audio; returns audio bytes when fetchable, else a JSON `{url}`.
- **transcriptions/translations**: upload a `file` (multipart) → `{ "text": "…" }`.

## `POST /v1/files` · `GET /v1/files` · `GET /v1/files/{id}` · `/content` · `DELETE`
Upload stores the file with Hyperagent (`create_attachment_upload`) and keeps a
local record; reference the returned `id` in a chat `file` content part to attach
it to a request.

## `POST /v1/embeddings`
Local, deterministic **hashing** vectors (not semantic) so clients work
end-to-end. Set `GATEWAY_EMBEDDINGS=off` to return `501` instead, or wire a real
provider.

## `POST /v1/moderations`
Transparent keyword **heuristic** across OpenAI categories. Returns
`results[].flagged` + per-category scores.

## `GET /v1/health`
Liveness: `{ "status": "ok", "version": "…", "upstream": "mcp|mock" }`.
