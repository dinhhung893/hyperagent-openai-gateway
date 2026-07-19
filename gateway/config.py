"""Environment-driven settings for the gateway."""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env_bool(name: str, default: bool = False) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Settings:
    # Upstream selection: "mcp" or "mock"
    upstream: str = field(default_factory=lambda: os.environ.get("GATEWAY_UPSTREAM", "mcp"))
    mcp_endpoint: str = field(
        default_factory=lambda: os.environ.get("HYPERAGENT_MCP_URL", "https://hyperagent.com/api/mcp")
    )
    # Client-facing auth. Comma-separated keys; empty => dev mode (allow any key).
    api_keys: str = field(default_factory=lambda: os.environ.get("SHIM_API_KEYS", ""))
    # Default agent when the client asks for "hyperagent-default"/"hyperagent-auto".
    default_agent: str = field(default_factory=lambda: os.environ.get("GATEWAY_DEFAULT_AGENT", ""))
    # Polling
    poll_interval: float = field(default_factory=lambda: float(os.environ.get("GATEWAY_POLL_INTERVAL", "1.0")))
    run_timeout: float = field(default_factory=lambda: float(os.environ.get("GATEWAY_RUN_TIMEOUT", "600")))
    # Tool bridge execution policy: "roundtrip" (OpenAI-standard) or "auto" (agent executes)
    exec_mode: str = field(default_factory=lambda: os.environ.get("GATEWAY_EXEC_MODE", "roundtrip"))
    # Canonical tools disabled for all keys (comma-separated names), e.g. "shell,write_file"
    disabled_tools: str = field(default_factory=lambda: os.environ.get("GATEWAY_DISABLED_TOOLS", ""))
    # Embeddings fallback: "fallback" (local hashing vectors) or "off" (501)
    embeddings_mode: str = field(default_factory=lambda: os.environ.get("GATEWAY_EMBEDDINGS", "fallback"))
    embeddings_dim: int = field(default_factory=lambda: int(os.environ.get("GATEWAY_EMBEDDINGS_DIM", "1536")))
    # State (conversation registry + file registry)
    state_path: str = field(
        default_factory=lambda: os.environ.get("GATEWAY_STATE_PATH", os.path.expanduser("~/.hyperagent-gateway/state.db"))
    )
    token_file: str = field(
        default_factory=lambda: os.environ.get(
            "HYPERAGENT_TOKEN_FILE", os.path.expanduser("~/.hyperagent-gateway/tokens.json")
        )
    )
    log_level: str = field(default_factory=lambda: os.environ.get("GATEWAY_LOG_LEVEL", "info"))

    @property
    def key_set(self) -> set[str]:
        return {k.strip() for k in self.api_keys.split(",") if k.strip()}

    @property
    def disabled_tool_set(self) -> set[str]:
        return {t.strip() for t in self.disabled_tools.split(",") if t.strip()}


settings = Settings()
