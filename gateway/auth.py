"""Client-side auth and model->agent resolution."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from fastapi import Request

from .config import Settings
from .errors import OAIError
from .identities import Identity, IdentityStore
from .upstream.base import Agent, UpstreamAdapter

RESERVED_DEFAULT = {"hyperagent-default", "hyperagent-auto", "gpt-3.5-turbo", "gpt-4", "gpt-4o"}


@dataclass
class Policy:
    key: str = ""
    identity: Optional[Identity] = None
    disabled_tools: set[str] = field(default_factory=set)


def extract_bearer(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return ""


def verify_key(request: Request, settings: Settings, identities: IdentityStore) -> Policy:
    key = extract_bearer(request)
    if identities.configured:
        # multi-tenant: the key must exist in the identity store
        ident = identities.resolve(key)
        if ident is None:
            raise OAIError(401, "Invalid API key.", type_="invalid_request_error",
                           code="invalid_api_key")
    else:
        # single-tenant/dev: optional SHIM_API_KEYS allowlist
        keyset = settings.key_set
        if keyset and key not in keyset:
            raise OAIError(401, "Invalid API key.", type_="invalid_request_error",
                           code="invalid_api_key")
        ident = identities.resolve(key)
    return Policy(key=key, identity=ident, disabled_tools=set(ident.disabled_tools))


class AgentResolver:
    """Caches list_agents and resolves an OpenAI model string to an agentId."""

    def __init__(self, adapter: UpstreamAdapter, settings: Settings, ttl: float = 60.0,
                 default_agent: str = ""):
        self._adapter = adapter
        self._settings = settings
        self._ttl = ttl
        self._default_agent = default_agent or settings.default_agent
        self._agents: list[Agent] = []
        self._at: float = 0.0

    async def agents(self, force: bool = False) -> list[Agent]:
        if force or (time.monotonic() - self._at) > self._ttl or not self._agents:
            self._agents = await self._adapter.list_agents()
            self._at = time.monotonic()
        return self._agents

    async def resolve(self, model: str) -> str:
        agents = await self.agents()
        if not agents:
            raise OAIError(503, "No Hyperagent agents are available for this account.",
                           type_="server_error", code="no_agents")
        if model in RESERVED_DEFAULT:
            return self._default_agent or agents[0].id
        for a in agents:
            if a.id == model:
                return a.id
        for a in agents:
            if a.name == model:
                return a.id
        for a in agents:
            if a.name.lower().replace(" ", "-") == model.lower():
                return a.id
        raise OAIError(404, f"The model '{model}' does not map to any Hyperagent agent.",
                       type_="invalid_request_error", param="model", code="model_not_found")
