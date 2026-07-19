"""Upstream adapters: the swappable boundary to Hyperagent.

- base.UpstreamAdapter: the interface every adapter implements.
- mock.MockAdapter: deterministic, no-network adapter for tests/dev.
- mcp.McpAdapter: the real MCP JSON-RPC client for hyperagent.com/api/mcp.
"""
from .base import Agent, ThreadMessage, ThreadSnapshot, ToolEvent, UpstreamAdapter

__all__ = [
    "Agent",
    "ThreadMessage",
    "ThreadSnapshot",
    "ToolEvent",
    "UpstreamAdapter",
]


def build_adapter(settings) -> UpstreamAdapter:
    """Factory selecting the adapter from settings.upstream."""
    if settings.upstream == "mock":
        from .mock import MockAdapter

        return MockAdapter()
    if settings.upstream == "mcp":
        from .mcp import McpAdapter

        return McpAdapter(endpoint=settings.mcp_endpoint, token_file=settings.token_file)
    raise ValueError(f"Unknown upstream: {settings.upstream!r}")
