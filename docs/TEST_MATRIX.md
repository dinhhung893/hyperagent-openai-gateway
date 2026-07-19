# Test Matrix

This file preserves the proof vocabulary and brownfield import shape used by
Harness consumers. The authoritative operational matrix is stored in SQLite
and queried with:

```bash
scripts/bin/harness-cli query matrix --active --summary
```

The upstream Harness repository has implemented behavior and executable proof.
An installed consumer starts without consumer-product rows and adds them only
when real work is accepted. Do not mark a row implemented until tests or other
validation evidence exist.

## Status Values

| Status | Meaning |
| --- | --- |
| planned | Accepted as intended behavior, not implemented |
| in_progress | Actively being built |
| implemented | Implemented and proof exists |
| changed | Contract changed after earlier implementation |
| retired | No longer part of the product contract |

## Matrix

Operational rows live in SQLite (`query matrix --active --summary`). Behavior →
proof for the gateway (Phase 1):

| Behavior | Proof | Status |
| --- | --- | --- |
| Message flattening & OpenAI response building | unit (`test_unit_parsing.py`) | implemented (E04) |
| MCP envelope parsing (SSE/JSON, tool result, agents, thread, running flag) | unit + live E2E (schemas via `tools/list`; PONG run; gateway smoke vs real MCP) | implemented (E02) |
| `GET /v1/models` from `list_agents` | integration (`test_api.py`) | implemented (E03) |
| `POST /v1/chat/completions` non-stream + attributes + errors | integration + OpenAI SDK | implemented (E04) |
| Emulated SSE streaming (`chat.completion.chunk` + `[DONE]` + usage) | integration + OpenAI SDK | implemented (E05) |
| Tool bridge: `/v1/tools` + Mode A observability + Mode B directed + Mode C tool-runner (roundtrip + auto) + disabled-tool policy | integration | implemented (E06) |
| Images (generations/edits) → fetchable URL via publish-public; audio speech/transcription/translation | integration + LIVE (image fetch 200, 1.5MB) | implemented (E08) |
| Embeddings local hashing fallback + keyword moderation heuristic | integration + LIVE | implemented (E11) |
| Responses API: sync/background/poll, SSE stream, cancel, input_items, stateful chain (context reconstruction) | integration + LIVE (recalled SPARROW-42) | implemented (E07) |
| Files: upload/list/get/content/delete + chat attachment passthrough | integration | implemented (E09) |
| Multi-tenant identities (GATEWAY_KEYS_FILE): auth + per-key tool policy | integration | implemented (E10) |
| Packaging: Docker, quickstart, client examples | integration | implemented (E12) |

All 12 epics implemented; `query matrix --active` is empty. Full proof: `python3.11 -m pytest tests/ -q` (46 passing) + live E2E against real MCP.
| Responses API: sync + background + poll + `previous_response_id` | integration | in_progress (E07) |
| Files upload/get via `create_attachment_upload` | integration | in_progress (E09) |
| Client-key auth enforcement | integration | implemented (E01) |
| Embeddings/media honest 501 per matrix | integration | implemented (E11 stub / E08 stub) |

Run all proof: `python3.11 -m pytest tests/ -q` (30 passing).

## Evidence Rules

- Unit proof covers pure domain and application rules.
- Integration proof covers backend enforcement, data integrity, provider
  behavior, jobs, or service contracts.
- E2E proof covers user-visible browser flows.
- Platform proof covers only shell, deployment, mobile, desktop, or runtime
  behavior that cannot be proven in lower layers.
- A story can be implemented without every proof column if the story packet
  explains why.
