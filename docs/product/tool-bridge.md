# Tool Bridge: Exposing Hyperagent's Tools via OpenAI `tools` / `tool_calls`

The user requirement is that **all** Hyperagent tools — Shell, Write/filesystem,
web search, browser, media generation, tables, docs, maps, integrations, etc. —
are reachable through the OpenAI API. The MCP surface cannot invoke those tools
directly (the agent runs them inside a thread), so the gateway bridges them in
**three modes**. All three use the standard OpenAI function-calling wire format,
so unmodified OpenAI clients work.

## Mode A — Observability (agent-initiated tool_calls)

When a client sends a normal chat request, the agent may use its internal tools
during the run. `get_thread` returns the thread's messages, which include the
agent's tool activity. The gateway **translates that activity into OpenAI
`tool_calls` + tool-result events**, so the client sees the full tool trace:

- Non-streaming: the final `message.tool_calls[]` (and a run summary) reflect
  which tools ran (e.g. `shell`, `write_file`, `web_search`, `generate_image`),
  with arguments and a compact result reference.
- Streaming: emitted as `tool_calls` deltas and (Responses API) as
  `response.*` step events as the poll diff reveals them.
- Artifacts (images, files, tables, docs, maps) are returned as URLs/attachments
  and, where the client asked for a modality, inline (e.g. image b64/URL).

This makes the entire tool catalog **visible** without the client doing anything
special.

## Mode B — Directed (client forces a capability)

A client can advertise/select Hyperagent capabilities via `tools` + `tool_choice`:

- The gateway publishes a **canonical tool catalog** (stable OpenAI function
  schemas) mirroring `capability-catalog.md`. A client can fetch it (see
  "Tool catalog endpoint") and pass the ones it wants, or use
  `tool_choice:{type:function,function:{name:"shell"}}` to force one.
- `tool_choice:"required"` or a named choice → the gateway steers the agent to
  use that capability (and/or routes to the tool-runner in Mode C).

### Canonical tool names (initial set; 1:1 with the catalog)

```
shell                 run a bash command in the sandbox
write_file            create/overwrite a file
read_file             read a file
edit_file             string-replace edit a file
list_files            list/glob files
web_search            Exa web search
web_fetch             fetch & parse a URL
image_search          web image search
generate_image        text/edit → image (Gemini/GPT Image)
generate_video        text → short video (Veo)
generate_audio        text → speech (TTS)
transcribe_audio      audio → text (diarized)
generate_avatar       talking-head video (HeyGen)
create_table / update_table
create_document / update_document
publish_webpage / publish_slides
geocode / directions / distance_matrix / place_search /
  street_view / weather / timezone / aerial_view / generate_map
search_integrations / connect_integration / execute_integration
search_knowledge / create_skill / create_memory
create_agent_thread / send_thread_message   (orchestration)
```

Each name carries a JSON-Schema `parameters` block derived from the real tool
signatures. `tool-registry.json` in the service is the single source of truth and
is also surfaced through the harness Tool Registry.

## Mode C — Direct tool execution (tool-runner)

For clients that want to **call one tool and get its result** (e.g. run a shell
command, write a file) through the OpenAI protocol, the gateway supports the
standard tool round-trip backed by a minimal **tool-runner agent**:

1. Client calls chat/responses with `tools:[shell]`,
   `tool_choice:{...shell}` and a request.
2. Gateway returns an assistant turn containing a `tool_call` for `shell`
   (arguments = the command) — OR, in "auto-exec" mode, it instructs a
   tool-runner agent to execute exactly that tool and returns the **tool result**
   directly.
3. In the standard round-trip, the client executes and posts a `tool` message
   with the result; the gateway feeds it back via `send_message` and continues.

Auto-exec vs round-trip is a per-request/gateway policy. Auto-exec gives direct
Shell/Write/etc. access; round-trip preserves OpenAI's human/client-in-the-loop
contract.

## Tool catalog endpoint

- `GET /v1/tools` (non-standard helper) → the canonical catalog as OpenAI tool
  definitions, so clients/UIs can discover every Hyperagent capability.
- The same catalog is emitted in `/v1/models` model metadata
  (`metadata.tools`) for clients that read it.

## Safety

- Directed/auto-exec Shell and filesystem tools run inside the Hyperagent
  agent's own sandbox with that user's permissions — never on the gateway host.
- A per-key allow/deny policy can restrict which canonical tools are exposed
  (e.g. disable `shell`/`write_file` for untrusted keys). See `auth.md`.
- Integration writes obey Hyperagent's own unattended-write and approval rules.
