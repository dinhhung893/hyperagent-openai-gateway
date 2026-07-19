[![English](https://img.shields.io/badge/lang-English-1f6feb?style=flat-square)](../en/05-tool-bridge.md) [![Tiếng Việt](https://img.shields.io/badge/lang-Ti%E1%BA%BFng%20Vi%E1%BB%87t-8b949e?style=flat-square)](../vi/05-tool-bridge.md) · [🏠 README](../../README.md) · [📚 Index](00-index.md)

# Tool bridge

The tool bridge exposes Hyperagent's inner toolbox (shell, files, web, media,
integrations…) through OpenAI's standard **function calling** (`tools` /
`tool_calls`), so unmodified OpenAI clients can see and drive them.

## Three modes

**A. Observe (automatic).** On any chat, the agent may use tools while working.
The gateway surfaces that activity as `tool_calls` in the reply.
```bash
curl .../v1/chat/completions -d '{"model":"hyperagent-default",
  "messages":[{"role":"user","content":"shell: ls -la"}]}'
# → message.tool_calls = [{function:{name:"shell",arguments:"{\"command\":\"ls -la\"}"}}], finish_reason:"tool_calls"
```

**B. Direct (you force a capability).** Send a canonical tool + `tool_choice` to
steer the agent toward it.
```json
{ "model":"hyperagent-default",
  "messages":[{"role":"user","content":"a red cube"}],
  "tools":[{"type":"function","function":{"name":"generate_image"}}],
  "tool_choice":{"type":"function","function":{"name":"generate_image"}} }
```

**C. Run (tool-runner).** With `GATEWAY_EXEC_MODE=auto`, a tool-runner executes
the forced tool directly and returns its result as the assistant message. With
the default `roundtrip`, the gateway returns a `tool_call` for your client to
execute (standard OpenAI handshake).

## Discover the catalog

```bash
curl .../v1/tools -H "authorization: Bearer sk-..."
```
Returns OpenAI tool definitions for every capability. Initial set:

```
shell · write_file · read_file · edit_file · list_files
web_search · web_fetch · image_search
generate_image · generate_video · generate_audio · transcribe_audio · generate_avatar
create_table · update_table · create_document · update_document
publish_webpage · publish_slides · generate_map
geocode · directions · place_search · weather · timezone
search_integrations · execute_integration · search_knowledge · create_agent_thread
```

## Safety & policy

- Restrict tools per API key with `GATEWAY_DISABLED_TOOLS=shell,write_file` (or
  per-identity in `GATEWAY_KEYS_FILE`). Disabled tools are hidden from `/v1/tools`
  and forcing one returns `400 tool_disabled`.
- Tools run inside the Hyperagent agent's own sandbox with that user's
  permissions — never on the gateway host.
- Integration writes still obey Hyperagent's own approval/unattended rules.

Canonical spec: [`docs/product/tool-bridge.md`](../product/tool-bridge.md).
