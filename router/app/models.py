from __future__ import annotations
from typing import Any, Literal, Union
from pydantic import BaseModel, Field


class FunctionParameters(BaseModel):
    type: Literal["object"] = "object"
    properties: dict[str, Any]
    required: list[str] = Field(default_factory=list)


class FunctionDefinition(BaseModel):
    name: str
    description: str
    parameters: FunctionParameters


class ToolDefinition(BaseModel):
    type: Literal["function"] = "function"
    function: FunctionDefinition


class FunctionCall(BaseModel):
    name: str
    arguments: str  # JSON string per OpenAI spec


class ToolCall(BaseModel):
    id: str
    type: Literal["function"] = "function"
    function: FunctionCall


class SystemMessage(BaseModel):
    role: Literal["system"]
    content: str


class UserMessage(BaseModel):
    role: Literal["user"]
    content: str


class AssistantMessage(BaseModel):
    role: Literal["assistant"]
    content: str | None = None
    tool_calls: list[ToolCall] | None = None


class ToolMessage(BaseModel):
    role: Literal["tool"]
    tool_call_id: str
    content: str


Message = Union[SystemMessage, UserMessage, AssistantMessage, ToolMessage]


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[Message]
    stream: bool = False
    temperature: float | None = None
    max_tokens: int | None = None
    tools: list[ToolDefinition] | None = None
    tool_choice: str | dict | None = None


class Delta(BaseModel):
    role: str | None = None
    content: str | None = None
    tool_calls: list[ToolCall] | None = None


class StreamChoice(BaseModel):
    index: int = 0
    delta: Delta
    finish_reason: str | None = None


class StreamChunk(BaseModel):
    id: str
    object: Literal["chat.completion.chunk"] = "chat.completion.chunk"
    created: int
    model: str
    choices: list[StreamChoice]


class Choice(BaseModel):
    index: int = 0
    message: AssistantMessage
    finish_reason: str | None = None


class Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(BaseModel):
    id: str
    object: Literal["chat.completion"] = "chat.completion"
    created: int
    model: str
    choices: list[Choice]
    usage: Usage


class ModelInfo(BaseModel):
    id: str
    object: Literal["model"] = "model"
    created: int = 0
    owned_by: str = "ollama"


class ModelList(BaseModel):
    object: Literal["list"] = "list"
    data: list[ModelInfo]
