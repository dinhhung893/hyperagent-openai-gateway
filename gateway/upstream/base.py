"""Normalized upstream types and the adapter interface.

The gateway is written against these normalized shapes so the OpenAI translation
layer never depends on the exact (partly undocumented) MCP envelope. Each adapter
maps the real upstream into these types.
"""
from __future__ import annotations

import abc
import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Agent:
    id: str
    name: str = ""
    description: str = ""
    # Best-effort underlying model label, surfaced in /v1/models metadata.
    model: str = "hyperagent"
    raw: dict = field(default_factory=dict)


@dataclass
class ToolEvent:
    """An agent-internal tool invocation observed in a thread (Mode A bridge)."""
    id: str
    name: str
    arguments: dict = field(default_factory=dict)
    result: Any = None


@dataclass
class ThreadMessage:
    role: str                       # user | assistant | tool | system
    content: str = ""
    tool_events: list[ToolEvent] = field(default_factory=list)
    raw: dict = field(default_factory=dict)


@dataclass
class ThreadSnapshot:
    thread_id: str
    running: bool
    messages: list[ThreadMessage] = field(default_factory=list)
    raw: dict = field(default_factory=dict)

    @property
    def last_assistant(self) -> Optional[ThreadMessage]:
        for m in reversed(self.messages):
            if m.role == "assistant":
                return m
        return None


class UpstreamAdapter(abc.ABC):
    """Interface every adapter implements. All methods are async."""

    # --- core MCP-equivalent operations ---
    @abc.abstractmethod
    async def list_agents(self) -> list[Agent]: ...

    @abc.abstractmethod
    async def create_thread(self, agent_id: str, message: str,
                            file_ids: Optional[list[str]] = None) -> str: ...

    @abc.abstractmethod
    async def send_message(self, thread_id: str, message: str,
                           file_ids: Optional[list[str]] = None) -> None: ...

    @abc.abstractmethod
    async def get_thread(self, thread_id: str) -> ThreadSnapshot: ...

    @abc.abstractmethod
    async def create_attachment_upload(self, filename: str, content_type: str,
                                       size: int) -> dict: ...

    async def aclose(self) -> None:  # optional cleanup
        return None

    # --- shared helpers built on the primitives ---
    @staticmethod
    def assistant_count(snap: ThreadSnapshot) -> int:
        return sum(1 for m in snap.messages if m.role == "assistant")

    async def wait_until_done(self, thread_id: str, *, poll_interval: float = 1.0,
                              timeout: float = 600.0) -> ThreadSnapshot:
        """Poll get_thread until the run is no longer running or timeout."""
        deadline = time.monotonic() + timeout
        snap = await self.get_thread(thread_id)
        while snap.running:
            if time.monotonic() > deadline:
                raise TimeoutError(f"thread {thread_id} still running after {timeout}s")
            await asyncio.sleep(poll_interval)
            snap = await self.get_thread(thread_id)
        return snap

    async def wait_for_new_assistant(self, thread_id: str, baseline: int, *,
                                     poll_interval: float = 1.0,
                                     timeout: float = 600.0) -> ThreadSnapshot:
        """Wait for a NEW assistant message to appear (count > baseline) and the
        run to be idle. Avoids the race where get_thread reports not-running for a
        just-queued follow-up turn before it starts (stale last-assistant)."""
        deadline = time.monotonic() + timeout
        snap = await self.get_thread(thread_id)
        while True:
            has_new = self.assistant_count(snap) > baseline
            if not snap.running and has_new:
                return snap
            if time.monotonic() > deadline:
                if has_new:
                    return snap
                raise TimeoutError(f"thread {thread_id} produced no new reply in {timeout}s")
            await asyncio.sleep(poll_interval)
            snap = await self.get_thread(thread_id)

    async def run_sync(self, *, agent_id: str, message: str,
                       thread_id: Optional[str] = None,
                       file_ids: Optional[list[str]] = None,
                       poll_interval: float = 1.0, timeout: float = 600.0) -> ThreadSnapshot:
        """Create-or-continue a thread and block until the new turn completes."""
        if thread_id is None:
            thread_id = await self.create_thread(agent_id, message, file_ids)
            baseline = 0
        else:
            base_snap = await self.get_thread(thread_id)
            baseline = self.assistant_count(base_snap)
            await self.send_message(thread_id, message, file_ids)
        return await self.wait_for_new_assistant(thread_id, baseline,
                                                 poll_interval=poll_interval, timeout=timeout)
