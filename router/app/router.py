from __future__ import annotations

import json
import time
import uuid
from typing import AsyncGenerator

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from .config import get_settings
from .models import ChatCompletionRequest, ModelInfo, ModelList
from .tools.executor import ToolExecutor
from .tools.memory import MemoryTool

chat_router = APIRouter()


# ── Model resolution ──────────────────────────────────────────────────────

def resolve_model(
    request_model: str,
    messages: list,
    task_type_header: str | None,
    routing_config: dict,
) -> str:
    passthrough = routing_config.get("passthrough", [])
    if request_model in passthrough:
        return request_model

    models_map = routing_config.get("models", {})
    task_types = routing_config.get("task_types", {})

    if task_type_header and task_type_header in task_types:
        logical = task_types[task_type_header]["model"]
        return models_map.get(logical, routing_config.get("default_model", "gemma3:4b"))

    probe_text = _extract_probe_text(messages)
    for rule in routing_config.get("keyword_rules", []):
        for kw in rule["keywords"]:
            if kw.lower() in probe_text.lower():
                logical = task_types[rule["task_type"]]["model"]
                return models_map.get(logical, routing_config.get("default_model", "gemma3:4b"))

    return routing_config.get("default_model", "gemma3:4b")


def _extract_probe_text(messages: list) -> str:
    parts = []
    seen_user = False
    for msg in messages:
        if hasattr(msg, "role"):
            role, content = msg.role, msg.content or ""
        else:
            role, content = msg.get("role", ""), msg.get("content", "") or ""
        if role == "system":
            parts.append(content)
        elif role == "user" and not seen_user:
            parts.append(content)
            seen_user = True
    return " ".join(parts)


# ── Memory helpers ─────────────────────────────────────────────────────────

def _get_memory_tool(request: Request) -> MemoryTool | None:
    """Get the MemoryTool from the registry, if enabled."""
    registry = request.app.state.tool_registry
    return registry.get_tool("memory_recall")


async def _persist_turns(request: Request, conversation_id: str, turns: list[dict]):
    """Persist conversation turns to SQLite memory."""
    mem = _get_memory_tool(request)
    if mem and turns:
        await mem.append_turns(conversation_id, turns)


# ── /v1/models ────────────────────────────────────────────────────────────

@chat_router.get("/models", response_model=ModelList)
async def list_models(request: Request) -> ModelList:
    client: httpx.AsyncClient = request.app.state.http_client
    settings = get_settings()

    try:
        resp = await client.get(f"{settings.ollama_base_url}/api/tags")
        resp.raise_for_status()
        ollama_models = resp.json().get("models", [])
    except httpx.HTTPError as e:
        raise HTTPException(502, f"Ollama unreachable: {type(e).__name__}: {e or 'no details'}")

    data = [ModelInfo(id=m["name"]) for m in ollama_models]
    for alias in ("coding", "general", "document", "long_context"):
        data.append(ModelInfo(id=f"auto/{alias}", owned_by="router"))
    data.append(ModelInfo(id="auto", owned_by="router"))

    return ModelList(data=data)


# ── /v1/chat/completions ──────────────────────────────────────────────────

@chat_router.post("/chat/completions")
async def chat_completions(body: ChatCompletionRequest, request: Request):
    settings = get_settings()
    client: httpx.AsyncClient = request.app.state.http_client
    routing_config = request.app.state.routing_config
    tool_registry = request.app.state.tool_registry

    task_type_header = request.headers.get("X-Task-Type")
    resolved_model = resolve_model(
        body.model, body.messages, task_type_header, routing_config
    )

    messages = [m.model_dump(exclude_none=True) for m in body.messages]
    tool_defs = tool_registry.get_openai_definitions()

    # Merge client-provided tools with registry tools
    if body.tools:
        client_tool_names = {t.function.name for t in body.tools if hasattr(t, "function")}
        merged = [td for td in tool_defs if td.get("function", {}).get("name") not in client_tool_names]
        merged.extend(t.model_dump(exclude_none=True) for t in body.tools)
        tool_defs = merged

    ollama_payload: dict = {
        "model": resolved_model,
        "messages": messages,
        "stream": body.stream,
    }
    if tool_defs:
        ollama_payload["tools"] = tool_defs
    if body.temperature is not None:
        ollama_payload.setdefault("options", {})["temperature"] = body.temperature
    if body.max_tokens is not None:
        ollama_payload.setdefault("options", {})["num_predict"] = body.max_tokens

    # Generate conversation ID for memory persistence
    conversation_id = request.headers.get("X-Conversation-ID", str(uuid.uuid4()))

    # Persist incoming messages to memory (fire-and-forget best-effort)
    incoming_turns = [{"role": m.get("role", "user"), "content": m.get("content", "")}
                      for m in messages if m.get("content")]
    await _persist_turns(request, conversation_id, incoming_turns)

    if body.stream:
        return StreamingResponse(
            _stream_with_tool_loop(
                client, settings, ollama_payload, tool_registry, resolved_model,
                request, conversation_id,
            ),
            media_type="text/event-stream",
            headers={"X-Accel-Buffering": "no"},
        )
    return await _complete_with_tool_loop(
        client, settings, ollama_payload, tool_registry, resolved_model,
        request, conversation_id,
    )


# ── Non-streaming tool loop ───────────────────────────────────────────────

async def _complete_with_tool_loop(
    client: httpx.AsyncClient,
    settings,
    payload: dict,
    tool_registry,
    model: str,
    request: Request,
    conversation_id: str,
    max_rounds: int = 5,
) -> JSONResponse:
    executor = ToolExecutor(tool_registry)
    current_messages = list(payload["messages"])

    for _ in range(max_rounds):
        payload["messages"] = current_messages
        try:
            resp = await client.post(
                f"{settings.ollama_base_url}/api/chat",
                json=payload,
            )
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise HTTPException(502, f"Ollama error: {type(e).__name__}: {e or 'no details'}")

        ollama_data = resp.json()
        assistant_msg = ollama_data.get("message", {})
        tool_calls = assistant_msg.get("tool_calls", [])

        if not tool_calls:
            # Persist final assistant response
            await _persist_turns(request, conversation_id, [assistant_msg])
            return JSONResponse(_normalize_response(ollama_data, model))

        current_messages.append(assistant_msg)
        tool_results = await executor.execute_all(tool_calls)
        current_messages.extend(tool_results)

    return JSONResponse(_normalize_response(ollama_data, model))


# ── Streaming tool loop ───────────────────────────────────────────────────

async def _stream_with_tool_loop(
    client: httpx.AsyncClient,
    settings,
    payload: dict,
    tool_registry,
    model: str,
    request: Request,
    conversation_id: str,
) -> AsyncGenerator[bytes, None]:
    executor = ToolExecutor(tool_registry)
    current_messages = list(payload["messages"])

    for _ in range(5):
        payload["messages"] = current_messages
        payload["stream"] = True

        accumulated_content = ""
        accumulated_tool_calls: list[dict] = []
        chunk_id = f"chatcmpl-{uuid.uuid4().hex}"

        try:
            async with client.stream(
                "POST",
                f"{settings.ollama_base_url}/api/chat",
                json=payload,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    msg = chunk.get("message", {})
                    content = msg.get("content", "")
                    tool_calls_chunk = msg.get("tool_calls", [])
                    done = chunk.get("done", False)

                    if tool_calls_chunk:
                        accumulated_tool_calls.extend(tool_calls_chunk)
                        # Emit tool call deltas to the client (OpenAI-compatible)
                        for tc in tool_calls_chunk:
                            func = tc.get("function", {})
                            sse = _make_sse_chunk(
                                chunk_id, model, "",
                                finish_reason=None,
                                tool_calls=[{
                                    "index": 0,
                                    "id": tc.get("id", f"call_{uuid.uuid4().hex[:8]}"),
                                    "type": "function",
                                    "function": {
                                        "name": func.get("name", ""),
                                        "arguments": json.dumps(func.get("arguments", {})),
                                    },
                                }],
                            )
                            yield f"data: {json.dumps(sse)}\n\n".encode()
                    elif content:
                        accumulated_content += content
                        sse = _make_sse_chunk(chunk_id, model, content, None)
                        yield f"data: {json.dumps(sse)}\n\n".encode()

                    if done:
                        break
        except httpx.HTTPError as e:
            error_msg = f"Ollama error: {type(e).__name__}: {e or 'no details'}"
            yield f"data: {json.dumps({'error': error_msg})}\n\n".encode()
            yield b"data: [DONE]\n\n"
            return

        if not accumulated_tool_calls:
            final = _make_sse_chunk(chunk_id, model, "", "stop")
            yield f"data: {json.dumps(final)}\n\n".encode()
            yield b"data: [DONE]\n\n"
            # Persist final assistant response
            await _persist_turns(request, conversation_id, [{"role": "assistant", "content": accumulated_content}])
            return

        # Execute tools and loop back
        assistant_msg = {
            "role": "assistant",
            "content": accumulated_content or None,
            "tool_calls": accumulated_tool_calls,
        }
        current_messages.append(assistant_msg)
        tool_results = await executor.execute_all(accumulated_tool_calls)
        current_messages.extend(tool_results)
        accumulated_tool_calls = []

    # Hit max rounds — emit stop
    final = _make_sse_chunk(chunk_id, model, "", "stop")
    yield f"data: {json.dumps(final)}\n\n".encode()
    yield b"data: [DONE]\n\n"


# ── Helpers ───────────────────────────────────────────────────────────────

def _normalize_response(ollama_data: dict, model: str) -> dict:
    msg = ollama_data.get("message", {})
    tool_calls = msg.get("tool_calls")
    finish_reason = "tool_calls" if tool_calls else "stop"

    return {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "message": {
                "role": msg.get("role", "assistant"),
                "content": msg.get("content"),
                "tool_calls": tool_calls,
            },
            "finish_reason": finish_reason,
        }],
        "usage": {
            "prompt_tokens": ollama_data.get("prompt_eval_count", 0),
            "completion_tokens": ollama_data.get("eval_count", 0),
            "total_tokens": (
                ollama_data.get("prompt_eval_count", 0) +
                ollama_data.get("eval_count", 0)
            ),
        },
    }


def _make_sse_chunk(
    chunk_id: str,
    model: str,
    content: str,
    finish_reason: str | None,
    tool_calls: list | None = None,
) -> dict:
    delta: dict = {}
    if content:
        delta["content"] = content
    if tool_calls:
        delta["tool_calls"] = tool_calls
    return {
        "id": chunk_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "delta": delta,
            "finish_reason": finish_reason,
        }],
    }