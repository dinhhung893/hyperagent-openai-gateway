"""Real MCP adapter for https://hyperagent.com/api/mcp.

Transport: MCP Streamable HTTP, JSON-RPC 2.0 over POST. The POST may return a
JSON object or an SSE stream (we handle both). Auth: OAuth 2.1 bearer token,
loaded from a token file and refreshed via the refresh_token grant.

NOTE: The exact input schemas / return envelopes of the six tools are not
published; parsing is defensive and centralized in the _parse_* helpers below.
Run `tools/list` once with a real token and adjust these helpers to the verbatim
schemas (fetch them live with a real token via the tools/list JSON-RPC call).
"""
from __future__ import annotations

import json
import time
import uuid
from typing import Any, Optional

import httpx

from .base import Agent, ThreadMessage, ThreadSnapshot, ToolEvent, UpstreamAdapter

PROTOCOL_VERSION = "2025-06-18"


# --------------------------------------------------------------------------- #
# Pure, testable parsing helpers (no network)                                 #
# --------------------------------------------------------------------------- #
def parse_sse_or_json(content_type: str, body: str) -> dict:
    """Return the JSON-RPC message from either a JSON body or an SSE stream."""
    if "text/event-stream" in (content_type or ""):
        last: dict = {}
        for line in body.splitlines():
            line = line.strip()
            if line.startswith("data:"):
                data = line[len("data:"):].strip()
                if not data or data == "[DONE]":
                    continue
                try:
                    last = json.loads(data)
                except json.JSONDecodeError:
                    continue
        return last
    return json.loads(body) if body.strip() else {}


def tool_result_payload(result: dict) -> Any:
    """Extract a tool's payload from an MCP CallToolResult.

    Prefers structuredContent; else concatenates text content blocks and tries
    to JSON-decode. Returns dict/list/str.
    """
    if not isinstance(result, dict):
        return result
    if "structuredContent" in result and result["structuredContent"] is not None:
        return result["structuredContent"]
    content = result.get("content")
    if isinstance(content, list):
        texts = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
        joined = "\n".join(t for t in texts if t)
        if joined:
            try:
                return json.loads(joined)
            except json.JSONDecodeError:
                return joined
    return result


def parse_agents(payload: Any) -> list[Agent]:
    items = _as_list(payload, keys=("agents", "items", "data"))
    out: list[Agent] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        out.append(Agent(
            id=str(it.get("id") or it.get("agentId") or it.get("slug") or ""),
            name=it.get("name", ""),
            description=it.get("description", ""),
            model=it.get("model") or it.get("modelId") or "hyperagent",
            raw=it,
        ))
    return [a for a in out if a.id]


def parse_thread_id(payload: Any) -> str:
    if isinstance(payload, str):
        return payload
    if isinstance(payload, dict):
        for k in ("threadId", "thread_id", "id"):
            if payload.get(k):
                return str(payload[k])
    raise ValueError(f"could not find threadId in {payload!r}")


def parse_thread_snapshot(thread_id: str, payload: Any) -> ThreadSnapshot:
    raw = payload if isinstance(payload, dict) else {"value": payload}
    running = _extract_running(raw)
    messages = [_parse_message(m) for m in _as_list(raw, keys=("messages", "items", "data"))]
    return ThreadSnapshot(thread_id=thread_id, running=running, messages=messages, raw=raw)


def parse_upload(payload: Any) -> dict:
    if not isinstance(payload, dict):
        return {}
    return {
        "fileId": payload.get("fileId") or payload.get("file_id") or payload.get("id"),
        "uploadUrl": payload.get("uploadUrl") or payload.get("upload_url") or payload.get("url"),
    }


def _as_list(payload: Any, keys: tuple[str, ...]) -> list:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for k in keys:
            v = payload.get(k)
            if isinstance(v, list):
                return v
    return []


def _extract_running(raw: dict) -> bool:
    for k in ("running", "isRunning", "is_running"):
        if k in raw:
            return bool(raw[k])
    status = str(raw.get("status", "")).lower()
    if status:
        return status in {"running", "in_progress", "pending", "queued", "working"}
    return False


def _parse_message(m: Any) -> ThreadMessage:
    if not isinstance(m, dict):
        return ThreadMessage(role="assistant", content=str(m))
    role = m.get("role", "assistant")
    content = m.get("content", "")
    if isinstance(content, list):  # content parts -> concat text
        content = "\n".join(
            p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") in (None, "text")
        )
    events = []
    for tc in m.get("toolCalls", m.get("tool_calls", []) or []):
        if isinstance(tc, dict):
            events.append(ToolEvent(
                id=str(tc.get("id") or "call_" + uuid.uuid4().hex[:8]),
                name=tc.get("name") or (tc.get("function", {}) or {}).get("name", "tool"),
                arguments=tc.get("arguments") or (tc.get("function", {}) or {}).get("arguments", {}),
                result=tc.get("result"),
            ))
    return ThreadMessage(role=role, content=content or "", tool_events=events, raw=m)


# --------------------------------------------------------------------------- #
# OAuth token manager                                                         #
# --------------------------------------------------------------------------- #
class OAuthTokenManager:
    """Loads a stored token bundle and refreshes access tokens as needed.

    Token file JSON: {access_token, refresh_token, expires_at (epoch), client_id,
    token_endpoint}. token_endpoint defaults to the discovered metadata value.
    """

    def __init__(self, token_file: str, issuer: str = "https://hyperagent.com"):
        self.token_file = token_file
        self.issuer = issuer
        self._bundle: dict = {}
        self._loaded = False

    def _load(self) -> None:
        try:
            with open(self.token_file) as f:
                self._bundle = json.load(f)
        except FileNotFoundError:
            self._bundle = {}
        self._loaded = True

    def _save(self) -> None:
        import os
        os.makedirs(os.path.dirname(self.token_file) or ".", exist_ok=True)
        with open(self.token_file, "w") as f:
            json.dump(self._bundle, f)

    async def access_token(self, client: httpx.AsyncClient) -> str:
        if not self._loaded:
            self._load()
        tok = self._bundle.get("access_token")
        exp = self._bundle.get("expires_at", 0)
        if tok and time.time() < exp - 30:
            return tok
        if self._bundle.get("refresh_token"):
            await self._refresh(client)
            return self._bundle["access_token"]
        if tok:
            return tok  # no refresh available; use as-is
        raise RuntimeError(
            "No Hyperagent OAuth token available. Complete the one-time browser "
            "authorization and write the token bundle to the token file "
            f"({self.token_file}). See docs/en/06-deployment.md."
        )

    async def _refresh(self, client: httpx.AsyncClient) -> None:
        token_endpoint = self._bundle.get("token_endpoint") or f"{self.issuer}/api/oauth/token"
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self._bundle["refresh_token"],
        }
        if self._bundle.get("client_id"):
            data["client_id"] = self._bundle["client_id"]
        resp = await client.post(token_endpoint, data=data,
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
        resp.raise_for_status()
        payload = resp.json()
        self._bundle["access_token"] = payload["access_token"]
        if payload.get("refresh_token"):
            self._bundle["refresh_token"] = payload["refresh_token"]
        self._bundle["expires_at"] = time.time() + int(payload.get("expires_in", 3600))
        self._save()


# --------------------------------------------------------------------------- #
# JSON-RPC client + adapter                                                   #
# --------------------------------------------------------------------------- #
class McpError(RuntimeError):
    def __init__(self, code: int, message: str, data: Any = None):
        super().__init__(f"MCP error {code}: {message}")
        self.code, self.message, self.data = code, message, data


class McpAdapter(UpstreamAdapter):
    def __init__(self, endpoint: str, token_file: str,
                 client: Optional[httpx.AsyncClient] = None):
        self.endpoint = endpoint
        self._client = client or httpx.AsyncClient(timeout=httpx.Timeout(60.0))
        self._owns_client = client is None
        self._tokens = OAuthTokenManager(token_file)
        self._session_id: Optional[str] = None
        self._initialized = False

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def _headers(self) -> dict:
        token = await self._tokens.access_token(self._client)
        h = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": PROTOCOL_VERSION,
        }
        if self._session_id:
            h["Mcp-Session-Id"] = self._session_id
        return h

    async def _rpc(self, method: str, params: Optional[dict] = None) -> Any:
        body = {"jsonrpc": "2.0", "id": uuid.uuid4().hex, "method": method, "params": params or {}}
        resp = await self._client.post(self.endpoint, headers=await self._headers(),
                                       content=json.dumps(body))
        sid = resp.headers.get("Mcp-Session-Id")
        if sid:
            self._session_id = sid
        resp.raise_for_status()
        msg = parse_sse_or_json(resp.headers.get("content-type", ""), resp.text)
        if "error" in msg and msg["error"]:
            err = msg["error"]
            raise McpError(err.get("code", -1), err.get("message", "unknown"), err.get("data"))
        return msg.get("result")

    async def _ensure_init(self) -> None:
        if self._initialized:
            return
        await self._rpc("initialize", {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "hyperagent-openai-gateway", "version": "0.1.0"},
        })
        # notifications/initialized is fire-and-forget; ignore errors.
        try:
            await self._rpc("notifications/initialized", {})
        except Exception:
            pass
        self._initialized = True

    async def _call_tool(self, name: str, arguments: dict) -> Any:
        await self._ensure_init()
        result = await self._rpc("tools/call", {"name": name, "arguments": arguments})
        return tool_result_payload(result or {})

    # --- interface ---
    async def list_agents(self) -> list[Agent]:
        return parse_agents(await self._call_tool("list_agents", {}))

    async def create_thread(self, agent_id: str, message: str,
                            file_ids: Optional[list[str]] = None) -> str:
        # Verbatim schema (tools/list 2026-07-19): agentId, message (required);
        # namingHint, attachmentIds (optional).
        args: dict[str, Any] = {"agentId": agent_id, "message": message}
        if file_ids:
            args["attachmentIds"] = file_ids
        return parse_thread_id(await self._call_tool("create_thread", args))

    async def send_message(self, thread_id: str, message: str,
                           file_ids: Optional[list[str]] = None) -> None:
        # Verbatim schema: threadId, message (required); attachmentIds (optional).
        args: dict[str, Any] = {"threadId": thread_id, "message": message}
        if file_ids:
            args["attachmentIds"] = file_ids
        await self._call_tool("send_message", args)

    async def get_thread(self, thread_id: str) -> ThreadSnapshot:
        payload = await self._call_tool("get_thread", {"threadId": thread_id})
        return parse_thread_snapshot(thread_id, payload)

    async def create_attachment_upload(self, filename: str, content_type: str,
                                       size: int) -> dict:
        # Verbatim schema: filename, mimeType, sizeBytes (all required).
        payload = await self._call_tool("create_attachment_upload", {
            "filename": filename, "mimeType": content_type, "sizeBytes": size,
        })
        return parse_upload(payload)

    async def list_tools_raw(self) -> Any:
        """Build-time helper: fetch verbatim tool schemas from the live server."""
        await self._ensure_init()
        return await self._rpc("tools/list", {})
