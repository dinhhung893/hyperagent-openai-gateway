"""Emulated OpenAI SSE streaming via get_thread poll-diff.

Hyperagent does not push partial tokens, so we poll get_thread, diff the assistant
message content, and emit chat.completion.chunk events as new text appears.
"""
from __future__ import annotations

import asyncio
import json
import time
import uuid
from typing import AsyncIterator, Optional

from .toolbridge import tool_events_to_tool_calls
from .upstream.base import UpstreamAdapter


def _chunk(cid: str, model: str, created: int, delta: dict,
           finish: Optional[str] = None) -> str:
    obj = {
        "id": cid,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
    }
    return f"data: {json.dumps(obj)}\n\n"


async def chat_completion_stream(
    adapter: UpstreamAdapter, *, model: str, agent_id: str, message: str,
    thread_id: Optional[str] = None, file_ids: Optional[list[str]] = None,
    poll_interval: float = 1.0, timeout: float = 600.0,
    include_usage: bool = False,
) -> AsyncIterator[str]:
    cid = "chatcmpl-" + uuid.uuid4().hex[:24]
    created = int(time.time())

    # role delta first (OpenAI convention)
    yield _chunk(cid, model, created, {"role": "assistant", "content": ""})

    if thread_id is None:
        baseline = 0
        thread_id = await adapter.create_thread(agent_id, message, file_ids)
    else:
        baseline = adapter.assistant_count(await adapter.get_thread(thread_id))
        await adapter.send_message(thread_id, message, file_ids)

    emitted = ""
    deadline = time.monotonic() + timeout
    snap = await adapter.get_thread(thread_id)
    while True:
        has_new = adapter.assistant_count(snap) > baseline
        asst = snap.last_assistant if has_new else None
        if asst and asst.content and asst.content != emitted:
            new = asst.content[len(emitted):] if asst.content.startswith(emitted) else asst.content
            emitted = asst.content
            if new:
                yield _chunk(cid, model, created, {"content": new})
        if not snap.running and has_new:
            break
        if time.monotonic() > deadline:
            yield _chunk(cid, model, created, {"content": "\n[stream timed out]"}, finish="length")
            yield "data: [DONE]\n\n"
            return
        await asyncio.sleep(poll_interval)
        snap = await adapter.get_thread(thread_id)

    # tool_calls (observability) + finish
    asst = snap.last_assistant
    tool_calls = tool_events_to_tool_calls(asst.tool_events) if asst else []
    finish = "tool_calls" if tool_calls else "stop"
    if tool_calls:
        yield _chunk(cid, model, created, {"tool_calls": [
            {"index": i, **tc} for i, tc in enumerate(tool_calls)
        ]})
    yield _chunk(cid, model, created, {}, finish=finish)

    if include_usage:
        from .translate import estimate_usage
        usage = estimate_usage(snap)
        obj = {
            "id": cid, "object": "chat.completion.chunk", "created": created,
            "model": model, "choices": [], "usage": usage,
        }
        yield f"data: {json.dumps(obj)}\n\n"

    yield "data: [DONE]\n\n"


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def responses_stream(
    adapter: UpstreamAdapter, *, model: str, rid: str, thread_id: str, baseline: int = 0,
    poll_interval: float = 1.0, timeout: float = 600.0,
) -> AsyncIterator[str]:
    """Emulated OpenAI Responses API streaming (E07): response.created ->
    response.output_text.delta* -> response.completed, via get_thread poll-diff.
    The caller must have already started the turn on `thread_id`; `baseline` is the
    assistant-message count before the turn, so only the NEW reply is streamed."""
    created = int(time.time())
    base = {"id": rid, "object": "response", "model": model, "created_at": created}
    seq = 0

    def env(status, output_text=None, output=None):
        r = dict(base, status=status)
        if output is not None:
            r["output"] = output
        if output_text is not None:
            r["output_text"] = output_text
        return r

    yield _sse("response.created", {"type": "response.created", "response": env("in_progress")})

    emitted = ""
    deadline = time.monotonic() + timeout
    snap = await adapter.get_thread(thread_id)
    while True:
        has_new = adapter.assistant_count(snap) > baseline
        asst = snap.last_assistant if has_new else None
        if asst and asst.content and asst.content != emitted:
            new = asst.content[len(emitted):] if asst.content.startswith(emitted) else asst.content
            emitted = asst.content
            if new:
                seq += 1
                yield _sse("response.output_text.delta",
                           {"type": "response.output_text.delta", "response_id": rid,
                            "output_index": 0, "content_index": 0, "sequence_number": seq,
                            "delta": new})
        if not snap.running and has_new:
            break
        if time.monotonic() > deadline:
            break
        await asyncio.sleep(poll_interval)
        snap = await adapter.get_thread(thread_id)

    output = [{
        "type": "message", "id": "msg_" + uuid.uuid4().hex[:20], "role": "assistant",
        "status": "completed",
        "content": [{"type": "output_text", "text": emitted, "annotations": []}],
    }]
    yield _sse("response.completed",
               {"type": "response.completed", "response": env("completed", emitted, output)})
    yield "data: [DONE]\n\n"
