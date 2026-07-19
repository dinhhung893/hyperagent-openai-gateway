# OpenAI API Compatibility Matrix

This is the exhaustive list of OpenAI-callable **endpoints** and **attributes** the
gateway accepts, and how each maps to Hyperagent. Every attribute a client can
send is given a defined behavior:

- **Impl** — implemented with real Hyperagent-backed behavior.
- **Map** — accepted and translated to the closest Hyperagent control.
- **Accept/no-op** — accepted for compatibility; has no effect on an agent run
  (documented so clients don't break).
- **501** — explicitly unsupported; returns an OpenAI-shaped error explaining why.

Base URL clients set: `https://<gateway-host>/v1`. Auth header: `Authorization:
Bearer <gateway key>` (see `auth.md`).

## Endpoints

| Method & path | Purpose | Status | Hyperagent mapping |
| --- | --- | --- | --- |
| `POST /v1/chat/completions` | Chat Completions (core) | **Impl** | messages→thread; poll `get_thread`; stream emulated |
| `POST /v1/completions` | Legacy text completion | **Map** | prompt→thread; single choice text |
| `POST /v1/responses` | Responses API (stateful/agentic) | **Impl** | Best fit: maps 1:1 to threads; supports background + polling + tool events + `previous_response_id`→threadId |
| `GET /v1/responses/{id}` | Retrieve a response | **Impl** | `get_thread` |
| `POST /v1/responses/{id}/cancel` | Cancel a background response | **Map** | best-effort thread stop [U] |
| `GET /v1/responses/{id}/input_items` | List input items | **Map** | from thread messages |
| `GET /v1/models` | List models | **Impl** | `list_agents` → models |
| `GET /v1/models/{model}` | Retrieve a model | **Impl** | agent by id |
| `POST /v1/embeddings` | Embeddings | **Map (fallback)** | Local deterministic hashing vectors (`GATEWAY_EMBEDDINGS=off` → 501); swap in a provider/skill for semantic quality |
| `POST /v1/images/generations` | Text→image | **Impl** | agent runs Image Generation (Gemini Flash/Pro, GPT Image 2) |
| `POST /v1/images/edits` | Image editing | **Impl** | Image Generation with input images |
| `POST /v1/images/variations` | Image variations | **Map** | Image Generation |
| `POST /v1/audio/speech` | Text→speech | **Impl** | Audio Generation (TTS, 30 voices, dialogue) |
| `POST /v1/audio/transcriptions` | Speech→text | **Impl** | Audio Transcription (diarization, timestamps) |
| `POST /v1/audio/translations` | Speech→English text | **Map** | Transcription + translate |
| `POST /v1/moderations` | Content moderation | **Map (heuristic)** | Transparent keyword classifier across OpenAI categories |
| `POST /v1/files` | Upload a file | **Impl** | `create_attachment_upload` → PUT |
| `GET /v1/files`, `GET /v1/files/{id}`, `GET /v1/files/{id}/content`, `DELETE /v1/files/{id}` | File lifecycle | **Map** | gateway-tracked fileId registry |
| `POST /v1/batches`, `GET /v1/batches/{id}`, `POST /v1/batches/{id}/cancel` | Batch jobs | **Map (phase 3)** | fan-out to threads |
| `GET /v1/health` (`/healthz`) | Liveness (non-OpenAI) | **Impl** | gateway self-check |

## Chat Completions — request attributes (complete)

| Attribute | Status | Behavior / mapping |
| --- | --- | --- |
| `model` | **Impl** | → `agentId` via `list_agents` (cached). Reserved aliases: `hyperagent-default`, `hyperagent-auto`. |
| `messages[]` | **Impl** | roles `system`/`developer`/`user`/`assistant`/`tool`. Flattened to a self-contained prompt (stateless) or mapped to a persistent thread (stateful). |
| `messages[].content` (string) | **Impl** | text prompt. |
| `messages[].content[]` (parts) | **Impl** | `text`, `image_url` (→ attachment/URL), `input_audio` (→ attachment), `file` (→ `create_attachment_upload`). |
| `messages[].name` | Accept | included in transcript. |
| `messages[].tool_call_id` / `tool` role | **Impl** | tool-result turn in the tool round-trip (see `tool-bridge.md`). |
| `stream` | **Impl (emulated)** | SSE `chat.completion.chunk` via `get_thread` polling + delta diff. |
| `stream_options.include_usage` | **Map** | emit final usage chunk (best-effort usage). |
| `tools[]` (`type:function`) | **Impl** | client-defined functions offered to the agent; agent may emit `tool_calls`. |
| `tool_choice` (`none`/`auto`/`required`/named) | **Map** | biases/forces a tool; `required`/named steer the agent or the tool-runner. |
| `parallel_tool_calls` | **Map** | allow multiple `tool_calls` per turn. |
| `functions[]` / `function_call` (legacy) | **Map** | translated to `tools`/`tool_choice`. |
| `response_format` `text` | **Impl** | default. |
| `response_format` `json_object` | **Impl** | instruct agent to emit valid JSON; validate/repair. |
| `response_format` `json_schema` | **Impl** | instruct + validate against schema; `strict` enforced by re-ask. |
| `max_tokens` / `max_completion_tokens` | **Map** | → agent Budget/output ceiling (best-effort). |
| `reasoning_effort` (o-series) | **Map** | → agent **Effort** / thinking-tokens setting. |
| `temperature`, `top_p` | Accept/no-op | agent controls sampling; documented no-op. |
| `n` | **Map** | `n>1` → multiple runs (costly) or 400 (configurable). Default supports `n=1`. |
| `stop` | **Map** | applied as a post-process trim (best-effort). |
| `presence_penalty`, `frequency_penalty`, `logit_bias` | Accept/no-op | not applicable to agent runs. |
| `logprobs`, `top_logprobs` | **501-in-field** | not available; returns `null` logprobs. |
| `seed` | Accept/no-op | runs are non-deterministic. |
| `stored`/`store`, `metadata` | **Map** | persisted with the thread mapping. |
| `user`, `safety_identifier`, `prompt_cache_key` | Accept | logged for abuse/routing; may key the conversation→thread map. |
| `service_tier` | Accept/no-op | single tier. |
| `modalities` (`["text","audio"]`) | **Map** | audio out via Audio Generation. |
| `audio` (`{voice,format}`) | **Map** | TTS voice/format for audio modality. |
| `prediction` (predicted outputs) | Accept/no-op | not applicable. |
| `web_search_options` | **Map** | enables the agent's Web Search tool. |

## Chat Completions — response shape (exact OpenAI wire format)

```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "created": 1730000000,
  "model": "<agent-model-id>",
  "system_fingerprint": "hyperagent-<threadId>",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "…",
      "tool_calls": [ { "id": "...", "type": "function",
                        "function": { "name": "...", "arguments": "{…}" } } ],
      "refusal": null
    },
    "finish_reason": "stop"        // stop | length | tool_calls | content_filter
  }],
  "usage": { "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0 }
}
```

- Streaming: `object:"chat.completion.chunk"`, `choices[].delta` carries
  incremental `content` and `tool_calls[{index,id,type,function{name,arguments}}]`;
  terminate with `data: [DONE]`.
- `usage` is best-effort (Hyperagent does not expose per-request token counts via
  MCP; derived/estimated and clearly documented). **[U]**
- `system_fingerprint` encodes the Hyperagent `threadId` for traceability.

## Responses API mapping (why it fits best)

Hyperagent threads are stateful, tool-using, and background-executing — exactly
the Responses API model. Mapping:
- `POST /v1/responses` with `input` → `create_thread` (or `send_message` when
  `previous_response_id` is set → its threadId).
- `background: true` → return immediately with `status:"in_progress"`; client
  polls `GET /v1/responses/{id}` (→ `get_thread`).
- `stream: true` → emit Responses stream events (`response.output_text.delta`,
  `response.function_call_arguments.delta`, `response.completed`) from poll diffs.
- `tools` (incl. built-in-style tools) → the tool bridge (`tool-bridge.md`).
- `store`, `metadata`, `previous_response_id` → the conversation→thread registry.

## Multi-turn & state (decision 0010)

The gateway never depends on upstream cross-turn memory (live-verified unreliable).
- **Chat Completions is stateless:** the full `messages[]` is flattened into a
  fresh thread each call (clients resend history), so `system_fingerprint`
  (threadId) differs per call — expected.
- **Responses API is stateful by reconstruction:** `previous_response_id` →
  the gateway reads the prior thread, flattens it, and prepends it to a new
  self-contained thread. Live-verified: a chain recalled a code across turns.
- Turn completion requires a NEW assistant message (baseline-guarded), removing
  the just-queued stale-reply race.

## Error envelope (all endpoints)

```json
{ "error": { "message": "…", "type": "invalid_request_error",
             "param": "model", "code": "model_not_found" } }
```
HTTP status mirrors OpenAI (400/401/404/409/429/500/503). Upstream MCP/JSON-RPC
errors and 401/405 are normalized into this envelope.
