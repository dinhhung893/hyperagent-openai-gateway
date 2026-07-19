"""Translate between OpenAI wire shapes and Hyperagent thread operations."""
from __future__ import annotations

import time
import uuid
from typing import Any, Optional

from .schemas import ChatMessage
from .toolbridge import tool_events_to_tool_calls
from .upstream.base import ThreadSnapshot

ROLE_LABEL = {"system": "System", "developer": "Developer", "user": "User",
              "assistant": "Assistant", "tool": "Tool result"}


def _content_to_text(content: Any) -> str:
    """Flatten a message content (string or content-parts array) to text."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    parts: list[str] = []
    for p in content:
        if not isinstance(p, dict):
            parts.append(str(p))
            continue
        t = p.get("type")
        if t in (None, "text", "input_text", "output_text"):
            parts.append(p.get("text", ""))
        elif t in ("image_url", "input_image"):
            url = p.get("image_url", {})
            url = url.get("url") if isinstance(url, dict) else (p.get("image_url") or p.get("url"))
            parts.append(f"[image: {url}]")
        elif t in ("input_audio",):
            parts.append("[audio attachment]")
        elif t in ("file", "input_file"):
            f = p.get("file", {})
            parts.append(f"[file: {f.get('filename') or f.get('file_id') or 'attached'}]")
        else:
            parts.append(p.get("text", ""))
    return "\n".join(x for x in parts if x)


def flatten_messages(messages: list[ChatMessage]) -> str:
    """Build a single self-contained prompt from an OpenAI message list.

    Used for stateless requests (one Hyperagent thread per call). System and
    developer messages become a preamble; the transcript preserves turn order.
    """
    preamble: list[str] = []
    transcript: list[str] = []
    for m in messages:
        text = _content_to_text(m.content)
        if m.role in ("system", "developer"):
            if text:
                preamble.append(text)
            continue
        if m.role == "tool":
            transcript.append(f"Tool result ({m.tool_call_id or ''}): {text}")
            continue
        if m.role == "assistant" and m.tool_calls:
            calls = ", ".join(
                f"{c.get('function', {}).get('name')}({c.get('function', {}).get('arguments')})"
                for c in m.tool_calls
            )
            transcript.append(f"Assistant (tool calls): {calls}")
            if text:
                transcript.append(f"Assistant: {text}")
            continue
        transcript.append(f"{ROLE_LABEL.get(m.role, m.role.title())}: {text}")

    out = []
    if preamble:
        out.append("\n".join(preamble))
    if len(transcript) == 1 and not preamble:
        return transcript[0].split(": ", 1)[-1]  # single user turn -> bare text
    out.append("\n".join(transcript))
    return "\n\n".join(out).strip()


def extract_file_ids(messages: list[ChatMessage]) -> list[str]:
    """Collect Hyperagent file ids referenced by message content parts, so chat
    requests can carry attachments (E09). Supports OpenAI `file` parts and an
    `image_url` whose url is a `file_<id>` reference."""
    ids: list[str] = []
    for m in messages:
        if not isinstance(m.content, list):
            continue
        for p in m.content:
            if not isinstance(p, dict):
                continue
            t = p.get("type")
            if t in ("file", "input_file"):
                f = p.get("file", {}) or {}
                fid = f.get("file_id") or p.get("file_id")
                if fid:
                    ids.append(fid)
            elif t in ("image_url", "input_image"):
                u = p.get("image_url", {})
                u = u.get("url") if isinstance(u, dict) else (p.get("image_url") or p.get("url"))
                if isinstance(u, str) and u.startswith("file_"):
                    ids.append(u)
    seen: set[str] = set()
    out: list[str] = []
    for i in ids:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def latest_user_text(messages: list[ChatMessage]) -> str:
    for m in reversed(messages):
        if m.role == "user":
            return _content_to_text(m.content)
    return flatten_messages(messages)


def flatten_snapshot(snap) -> str:
    """Turn a thread snapshot's messages into a transcript, so a follow-up turn
    can carry prior context in its message body (the gateway never relies on
    upstream cross-turn memory)."""
    lines = []
    for m in snap.messages:
        if m.content:
            lines.append(f"{ROLE_LABEL.get(m.role, m.role.title())}: {m.content}")
    return "\n".join(lines)


def _finish_reason(has_tool_calls: bool) -> str:
    return "tool_calls" if has_tool_calls else "stop"


def build_chat_completion(model: str, snapshot: ThreadSnapshot, *,
                          created: Optional[int] = None) -> dict:
    """Render an OpenAI chat.completion object from a finished thread snapshot."""
    msg = snapshot.last_assistant
    content = msg.content if msg else ""
    tool_calls = tool_events_to_tool_calls(msg.tool_events) if msg else []
    message: dict[str, Any] = {"role": "assistant", "content": content or None, "refusal": None}
    if tool_calls:
        message["tool_calls"] = tool_calls
    return {
        "id": "chatcmpl-" + uuid.uuid4().hex[:24],
        "object": "chat.completion",
        "created": created or int(time.time()),
        "model": model,
        "system_fingerprint": f"hyperagent-{snapshot.thread_id}",
        "choices": [{
            "index": 0,
            "message": message,
            "logprobs": None,
            "finish_reason": _finish_reason(bool(tool_calls)),
        }],
        "usage": estimate_usage(snapshot),
    }


def estimate_usage(snapshot: ThreadSnapshot) -> dict:
    """Best-effort token usage (Hyperagent does not expose per-request counts)."""
    def approx(txt: str) -> int:
        return max(1, len(txt) // 4)

    prompt = sum(approx(m.content) for m in snapshot.messages if m.role in ("user", "system"))
    completion = approx(snapshot.last_assistant.content) if snapshot.last_assistant else 0
    return {
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": prompt + completion,
        "_note": "estimated; upstream does not expose exact token counts",
    }


def model_object(agent) -> dict:
    return {
        "id": agent.id,
        "object": "model",
        "created": 0,
        "owned_by": "hyperagent",
        "metadata": {"name": agent.name, "description": agent.description, "model": agent.model},
    }
