"""Per-identity adapter + resolver pool (E10).

Creates one upstream adapter per Hyperagent identity (keyed by token file), lazily
and cached. In mock mode (or when a test injects an adapter) a single shared
adapter serves every identity.
"""
from __future__ import annotations

from typing import Optional

from ..auth import AgentResolver
from ..config import Settings
from ..identities import Identity
from .base import UpstreamAdapter


class UpstreamManager:
    def __init__(self, settings: Settings, injected: Optional[UpstreamAdapter] = None):
        self.settings = settings
        self._injected = injected
        self._adapters: dict[str, UpstreamAdapter] = {}
        self._resolvers: dict[str, AgentResolver] = {}

    def adapter_for(self, identity: Identity) -> UpstreamAdapter:
        if self._injected is not None:
            return self._injected
        if self.settings.upstream == "mock":
            if "__mock__" not in self._adapters:
                from .mock import MockAdapter
                self._adapters["__mock__"] = MockAdapter()
            return self._adapters["__mock__"]
        key = identity.token_file
        if key not in self._adapters:
            from .mcp import McpAdapter
            self._adapters[key] = McpAdapter(endpoint=self.settings.mcp_endpoint,
                                             token_file=identity.token_file)
        return self._adapters[key]

    def resolver_for(self, identity: Identity) -> AgentResolver:
        if identity.id not in self._resolvers:
            self._resolvers[identity.id] = AgentResolver(
                self.adapter_for(identity), self.settings, default_agent=identity.default_agent)
        return self._resolvers[identity.id]

    async def aclose(self) -> None:
        for a in self._adapters.values():
            await a.aclose()
