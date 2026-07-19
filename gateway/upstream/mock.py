"""Deterministic in-memory upstream for tests and offline dev.

Simulates Hyperagent's async model: create_thread returns immediately with a
threadId, the "run" completes after get_thread is polled once (running -> done),
and the assistant echoes a summary of the prompt. It can also emit a synthetic
tool event so the tool-bridge (Mode A) can be exercised without a network.
"""
from __future__ import annotations

import json
import uuid
from typing import Optional

from .base import Agent, ThreadMessage, ThreadSnapshot, ToolEvent, UpstreamAdapter


class MockAdapter(UpstreamAdapter):
    def __init__(self, *, complete_after_polls: int = 0):
        self._agents = [
            Agent(id="agent_default", name="Default Agent",
                  description="General-purpose Hyperagent agent", model="hyperagent-default"),
            Agent(id="agent_research", name="Researcher",
                  description="Web research specialist", model="hyperagent-research"),
        ]
        self._threads: dict[str, dict] = {}
        self._complete_after_polls = complete_after_polls
        self._uploads: dict[str, dict] = {}

    async def list_agents(self) -> list[Agent]:
        return list(self._agents)

    def _reply_for(self, prompt: str) -> tuple[str, list[ToolEvent]]:
        # Simulate agent behavior for bridge + media tests.
        events: list[ToolEvent] = []
        low = prompt.lower()
        # Mode A observability: emit a shell tool event on "shell:"/"run:"
        if "shell:" in low or "run:" in low:
            cmd = prompt.split(":", 1)[1].strip()
            events.append(ToolEvent(id="call_" + uuid.uuid4().hex[:8], name="shell",
                                    arguments={"command": cmd}, result="(mock stdout)"))
        # Mode C auto-exec directive: "Use ONLY your '<tool>' capability ..."
        if "use only your '" in low and "capability" in low:
            tool = prompt.split("'", 2)[1] if "'" in prompt else "tool"
            return f"(mock {tool} result)", events
        # Media artifacts -> return a fake artifact URL the endpoints can extract
        if "generate an image" in low or "generate_image" in low or "image:" in low:
            return f"https://mock.artifact/img_{uuid.uuid4().hex[:8]}.png", events
        if "generate audio" in low or "text-to-speech" in low or "speech:" in low:
            return f"https://mock.artifact/audio_{uuid.uuid4().hex[:8]}.mp3", events
        if "transcribe" in low:
            return "This is the mock transcription of the attached audio.", events
        text = f"[mock:{self._active_agent}] " + (prompt.strip()[:400] or "(empty)")
        return text, events

    async def create_thread(self, agent_id: str, message: str,
                            file_ids: Optional[list[str]] = None) -> str:
        tid = "thr_" + uuid.uuid4().hex[:12]
        self._active_agent = agent_id
        self._threads[tid] = {
            "agent_id": agent_id,
            "polls": 0,
            "messages": [ThreadMessage(role="user", content=message)],
            "pending": message,
            "file_ids": file_ids or [],
        }
        return tid

    async def send_message(self, thread_id: str, message: str,
                           file_ids: Optional[list[str]] = None) -> None:
        t = self._threads[thread_id]
        self._active_agent = t["agent_id"]
        t["messages"].append(ThreadMessage(role="user", content=message))
        t["pending"] = message
        t["polls"] = 0

    async def get_thread(self, thread_id: str) -> ThreadSnapshot:
        t = self._threads[thread_id]
        if t.get("pending") is not None:
            if t["polls"] >= self._complete_after_polls:
                self._active_agent = t["agent_id"]
                text, events = self._reply_for(t["pending"])
                t["messages"].append(
                    ThreadMessage(role="assistant", content=text, tool_events=events)
                )
                t["pending"] = None
            else:
                t["polls"] += 1
                return ThreadSnapshot(thread_id, running=True, messages=list(t["messages"]))
        return ThreadSnapshot(thread_id, running=False, messages=list(t["messages"]))

    async def create_attachment_upload(self, filename: str, content_type: str,
                                       size: int) -> dict:
        fid = "file_" + uuid.uuid4().hex[:12]
        self._uploads[fid] = {"filename": filename, "content_type": content_type, "size": size}
        return {"fileId": fid, "uploadUrl": f"https://mock.upload/{fid}"}
