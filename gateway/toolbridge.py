"""Tool bridge: expose Hyperagent's tool catalog as OpenAI tool definitions,
and translate agent tool activity into OpenAI tool_calls.

See docs/product/tool-bridge.md for the three exposure modes.
"""
from __future__ import annotations

import json
from typing import Any

from .upstream.base import ToolEvent


def _fn(name: str, description: str, params: dict) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {"type": "object", **params},
        },
    }


_STR = {"type": "string"}

# Canonical catalog (1:1 with docs/product/capability-catalog.md). Kept compact;
# parameter schemas are the gateway's source of truth and can be refined against
# the live runtime signatures.
CANONICAL_TOOLS: list[dict] = [
    _fn("shell", "Run a bash command in the agent sandbox (Python/Node/CLI; cwd persists).",
        {"properties": {"command": _STR}, "required": ["command"]}),
    _fn("write_file", "Create or overwrite a file in the sandbox.",
        {"properties": {"path": _STR, "content": _STR}, "required": ["path", "content"]}),
    _fn("read_file", "Read a file from the sandbox.",
        {"properties": {"path": _STR}, "required": ["path"]}),
    _fn("edit_file", "String-replace edit a file.",
        {"properties": {"path": _STR, "old": _STR, "new": _STR}, "required": ["path", "old", "new"]}),
    _fn("list_files", "List or glob files.",
        {"properties": {"pattern": _STR}}),
    _fn("web_search", "Semantic/keyword web search (Exa).",
        {"properties": {"query": _STR}, "required": ["query"]}),
    _fn("web_fetch", "Fetch and parse a URL's clean content.",
        {"properties": {"url": _STR}, "required": ["url"]}),
    _fn("image_search", "Search the web for images.",
        {"properties": {"query": _STR}, "required": ["query"]}),
    _fn("generate_image", "Generate or edit an image (Gemini / GPT Image).",
        {"properties": {"prompt": _STR, "aspect_ratio": _STR}, "required": ["prompt"]}),
    _fn("generate_video", "Generate a short video (Veo).",
        {"properties": {"prompt": _STR}, "required": ["prompt"]}),
    _fn("generate_audio", "Text-to-speech (single or multi-speaker).",
        {"properties": {"text": _STR, "voice": _STR}, "required": ["text"]}),
    _fn("transcribe_audio", "Transcribe audio (diarization, timestamps).",
        {"properties": {"file_id": _STR}, "required": ["file_id"]}),
    _fn("generate_avatar", "Talking-head avatar video (HeyGen).",
        {"properties": {"script": _STR, "avatar_id": _STR}, "required": ["script"]}),
    _fn("create_table", "Create a typed table.",
        {"properties": {"title": _STR, "columns": {"type": "array"}}, "required": ["title"]}),
    _fn("update_table", "Update table cells/rows.",
        {"properties": {"table_id": _STR}, "required": ["table_id"]}),
    _fn("create_document", "Create a persistent document.",
        {"properties": {"title": _STR, "sections": {"type": "array"}}, "required": ["title"]}),
    _fn("update_document", "Update a document section.",
        {"properties": {"document_id": _STR, "operation": _STR}, "required": ["document_id"]}),
    _fn("publish_webpage", "Publish a self-contained HTML webpage artifact.",
        {"properties": {"title": _STR, "html": _STR}, "required": ["title", "html"]}),
    _fn("publish_slides", "Publish a slide deck artifact.",
        {"properties": {"title": _STR, "html": _STR}, "required": ["title", "html"]}),
    _fn("generate_map", "Generate an interactive map.",
        {"properties": {"title": _STR, "markers": {"type": "array"}}, "required": ["title"]}),
    _fn("geocode", "Address <-> coordinates.",
        {"properties": {"address": _STR}}),
    _fn("directions", "Turn-by-turn directions.",
        {"properties": {"origin": _STR, "destination": _STR}, "required": ["origin", "destination"]}),
    _fn("place_search", "Find places near a location.",
        {"properties": {"query": _STR}, "required": ["query"]}),
    _fn("weather", "Current/forecast weather.",
        {"properties": {"location": _STR}, "required": ["location"]}),
    _fn("timezone", "Time zone for a location.",
        {"properties": {"location": _STR}, "required": ["location"]}),
    _fn("search_integrations", "Discover third-party integrations and actions.",
        {"properties": {"query": _STR}, "required": ["query"]}),
    _fn("execute_integration", "Run an action on a connected integration.",
        {"properties": {"action": _STR, "params": {"type": "object"}}, "required": ["action"]}),
    _fn("search_knowledge", "Search skills and memories.",
        {"properties": {"query": _STR}, "required": ["query"]}),
    _fn("create_agent_thread", "Spawn a background agent thread (orchestration).",
        {"properties": {"agent_id": _STR, "message": _STR}, "required": ["agent_id", "message"]}),
]

CANONICAL_TOOL_NAMES = {t["function"]["name"] for t in CANONICAL_TOOLS}


def catalog(disabled: set[str] | None = None) -> list[dict]:
    disabled = disabled or set()
    return [t for t in CANONICAL_TOOLS if t["function"]["name"] not in disabled]


def tool_events_to_tool_calls(events: list[ToolEvent]) -> list[dict]:
    """Render observed agent tool activity as OpenAI tool_calls (Mode A)."""
    calls = []
    for ev in events:
        args = ev.arguments if isinstance(ev.arguments, str) else json.dumps(ev.arguments or {})
        calls.append({
            "id": ev.id,
            "type": "function",
            "function": {"name": ev.name, "arguments": args},
        })
    return calls


def forced_tool_name(tool_choice: Any) -> str | None:
    """Return the canonical tool name a client forced via tool_choice, else None."""
    if isinstance(tool_choice, dict):
        name = (tool_choice.get("function") or {}).get("name")
        if name in CANONICAL_TOOL_NAMES:
            return name
    return None


def primary_param(tool_name: str) -> str:
    """First required parameter of a canonical tool (for arg mapping)."""
    for t in CANONICAL_TOOLS:
        if t["function"]["name"] == tool_name:
            req = t["function"]["parameters"].get("required") or []
            if req:
                return req[0]
            props = list(t["function"]["parameters"].get("properties", {}).keys())
            return props[0] if props else "input"
    return "input"


def build_exec_directive(tool_name: str, arguments: dict) -> str:
    """Mode C auto-exec: instruct the agent to run exactly one capability and
    return only its raw result."""
    import json as _json
    args = _json.dumps(arguments, ensure_ascii=False)
    return (f"[Directive] Use ONLY your '{tool_name}' capability with these arguments: "
            f"{args}. Execute it and reply with only the raw result of that tool — "
            f"no explanation, no extra text.")


def directive_from_tool_choice(tool_choice: Any, tools: list[dict] | None) -> str:
    """Turn a forced tool_choice into a natural-language directive for the agent
    (Mode B). Returns '' when nothing is forced."""
    if not tool_choice or tool_choice in ("auto", "none"):
        return ""
    if tool_choice == "required":
        return "\n\n[Directive] You must use at least one available tool to fulfill this request."
    if isinstance(tool_choice, dict):
        name = (tool_choice.get("function") or {}).get("name")
        if name:
            return f"\n\n[Directive] Use the '{name}' capability to fulfill this request."
    return ""
