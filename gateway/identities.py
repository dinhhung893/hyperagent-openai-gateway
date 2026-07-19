"""Multi-tenant identity model (E10).

Each gateway API key maps to an Identity: which Hyperagent OAuth token bundle to
use upstream, plus per-key policy (default agent, disabled tools). Configured via
GATEWAY_KEYS_FILE (JSON list); absent that, a single default identity is used
(dev / single-tenant), preserving prior behavior.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Optional

from .config import Settings


@dataclass
class Identity:
    id: str
    token_file: str
    default_agent: str = ""
    disabled_tools: set[str] = field(default_factory=set)
    label: str = ""


class IdentityStore:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._by_key: dict[str, Identity] = {}
        self._configured = False
        self._default = Identity(
            id="default", token_file=os.path.expanduser(settings.token_file),
            default_agent=settings.default_agent,
            disabled_tools=set(settings.disabled_tool_set), label="default")
        self._load()

    def _load(self) -> None:
        path = os.environ.get("GATEWAY_KEYS_FILE", "").strip()
        if not path or not os.path.exists(os.path.expanduser(path)):
            return
        with open(os.path.expanduser(path)) as f:
            data = json.load(f)
        for i, e in enumerate(data):
            key = e["api_key"]
            self._by_key[key] = Identity(
                id=e.get("id", f"id{i}"),
                token_file=os.path.expanduser(e.get("token_file", self.settings.token_file)),
                default_agent=e.get("default_agent", ""),
                disabled_tools=set(e.get("disabled_tools", [])),
                label=e.get("label", e.get("id", f"id{i}")),
            )
        self._configured = True

    @property
    def configured(self) -> bool:
        return self._configured

    def resolve(self, key: str) -> Optional[Identity]:
        if self._configured:
            return self._by_key.get(key)
        return self._default  # dev/single-tenant: any accepted key -> default

    def all(self) -> list[Identity]:
        return list(self._by_key.values()) if self._configured else [self._default]
