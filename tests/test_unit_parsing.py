"""Unit tests for pure helpers (no network)."""
import json

from gateway.schemas import ChatMessage
from gateway.translate import build_chat_completion, flatten_messages
from gateway.upstream.base import ThreadMessage, ThreadSnapshot, ToolEvent
from gateway.upstream import mcp


def test_parse_sse_or_json_json():
    body = json.dumps({"jsonrpc": "2.0", "id": "1", "result": {"ok": True}})
    msg = mcp.parse_sse_or_json("application/json", body)
    assert msg["result"] == {"ok": True}


def test_parse_sse_or_json_sse():
    body = (
        "event: message\n"
        'data: {"jsonrpc":"2.0","id":"1","result":{"ok":true}}\n\n'
    )
    msg = mcp.parse_sse_or_json("text/event-stream; charset=utf-8", body)
    assert msg["result"]["ok"] is True


def test_tool_result_payload_structured():
    assert mcp.tool_result_payload({"structuredContent": {"a": 1}}) == {"a": 1}


def test_tool_result_payload_text_json():
    res = {"content": [{"type": "text", "text": '{"threadId":"t1"}'}]}
    assert mcp.tool_result_payload(res) == {"threadId": "t1"}


def test_parse_agents_variants():
    agents = mcp.parse_agents({"agents": [
        {"id": "a1", "name": "One", "description": "d"},
        {"agentId": "a2", "name": "Two"},
    ]})
    assert [a.id for a in agents] == ["a1", "a2"]


def test_parse_thread_id():
    assert mcp.parse_thread_id({"threadId": "t9"}) == "t9"
    assert mcp.parse_thread_id("t7") == "t7"


def test_extract_running_status_strings():
    assert mcp._extract_running({"status": "in_progress"}) is True
    assert mcp._extract_running({"status": "completed"}) is False
    assert mcp._extract_running({"isRunning": True}) is True


def test_parse_thread_snapshot_messages():
    payload = {"running": False, "messages": [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello",
         "toolCalls": [{"id": "c1", "name": "shell", "arguments": {"command": "ls"}}]},
    ]}
    snap = mcp.parse_thread_snapshot("t1", payload)
    assert snap.running is False
    assert snap.last_assistant.content == "hello"
    assert snap.last_assistant.tool_events[0].name == "shell"


def test_flatten_messages_single_user():
    msgs = [ChatMessage(role="user", content="What is 2+2?")]
    assert flatten_messages(msgs) == "What is 2+2?"


def test_flatten_messages_with_system_and_history():
    msgs = [
        ChatMessage(role="system", content="Be terse."),
        ChatMessage(role="user", content="Hi"),
        ChatMessage(role="assistant", content="Hello"),
        ChatMessage(role="user", content="Bye"),
    ]
    out = flatten_messages(msgs)
    assert "Be terse." in out and "User: Hi" in out and "Bye" in out


def test_flatten_messages_content_parts():
    msgs = [ChatMessage(role="user", content=[
        {"type": "text", "text": "describe"},
        {"type": "image_url", "image_url": {"url": "http://x/y.png"}},
    ])]
    out = flatten_messages(msgs)
    assert "describe" in out and "image: http://x/y.png" in out


def test_build_chat_completion_shape():
    snap = ThreadSnapshot("t1", running=False, messages=[
        ThreadMessage(role="user", content="hi"),
        ThreadMessage(role="assistant", content="yo",
                      tool_events=[ToolEvent(id="c1", name="shell", arguments={"command": "ls"})]),
    ])
    obj = build_chat_completion("agent_default", snap)
    assert obj["object"] == "chat.completion"
    assert obj["choices"][0]["finish_reason"] == "tool_calls"
    assert obj["choices"][0]["message"]["tool_calls"][0]["function"]["name"] == "shell"
    assert obj["system_fingerprint"] == "hyperagent-t1"
