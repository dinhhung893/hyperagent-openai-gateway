"""OpenAI-compatible request models.

Models are permissive (extra="allow") so every documented OpenAI attribute is
accepted even when it maps to a no-op. Known fields are typed for convenient
access in the translation layer.
"""
from __future__ import annotations

from typing import Any, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class _Permissive(BaseModel):
    model_config = ConfigDict(extra="allow")


class ChatMessage(_Permissive):
    role: str
    content: Optional[Union[str, list[dict[str, Any]]]] = None
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_calls: Optional[list[dict[str, Any]]] = None


class ChatCompletionRequest(_Permissive):
    model: str
    messages: list[ChatMessage]
    stream: bool = False
    stream_options: Optional[dict[str, Any]] = None
    tools: Optional[list[dict[str, Any]]] = None
    tool_choice: Optional[Union[str, dict[str, Any]]] = None
    parallel_tool_calls: Optional[bool] = None
    functions: Optional[list[dict[str, Any]]] = None
    function_call: Optional[Union[str, dict[str, Any]]] = None
    response_format: Optional[dict[str, Any]] = None
    max_tokens: Optional[int] = None
    max_completion_tokens: Optional[int] = None
    reasoning_effort: Optional[str] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    n: Optional[int] = 1
    stop: Optional[Union[str, list[str]]] = None
    modalities: Optional[list[str]] = None
    audio: Optional[dict[str, Any]] = None
    web_search_options: Optional[dict[str, Any]] = None
    store: Optional[bool] = None
    metadata: Optional[dict[str, Any]] = None
    user: Optional[str] = None
    # conversation continuity extension (non-OpenAI): reuse a Hyperagent thread
    conversation_id: Optional[str] = None


class CompletionRequest(_Permissive):
    model: str
    prompt: Union[str, list[str]] = ""
    stream: bool = False
    max_tokens: Optional[int] = None


class EmbeddingRequest(_Permissive):
    model: str
    input: Union[str, list[str], list[int], list[list[int]]]


class ResponsesRequest(_Permissive):
    model: str
    input: Optional[Union[str, list[dict[str, Any]]]] = None
    instructions: Optional[str] = None
    stream: bool = False
    background: bool = False
    previous_response_id: Optional[str] = None
    tools: Optional[list[dict[str, Any]]] = None
    tool_choice: Optional[Union[str, dict[str, Any]]] = None
    store: Optional[bool] = None
    metadata: Optional[dict[str, Any]] = None


class ModerationRequest(_Permissive):
    input: Union[str, list[str]]
    model: Optional[str] = "omni-moderation-latest"


class ImagesRequest(_Permissive):
    prompt: str = ""
    model: Optional[str] = None
    n: Optional[int] = 1
    size: Optional[str] = None
    response_format: Optional[str] = "url"


class SpeechRequest(_Permissive):
    model: Optional[str] = None
    input: str = ""
    voice: Optional[str] = None
    response_format: Optional[str] = None
