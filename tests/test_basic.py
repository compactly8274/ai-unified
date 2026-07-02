"""Basic smoke tests for the AI gateway router logic (no live Ollama required)."""
import os
import sys

import pytest
import yaml

# Add router to path so tests can import from app.*
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "router"))

from app.router import _normalize_response, resolve_model


@pytest.fixture
def routing_config():
    cfg_path = os.path.join(os.path.dirname(__file__), "..", "config", "routing.yaml")
    with open(cfg_path) as f:
        return yaml.safe_load(f)


class _Msg:
    def __init__(self, role: str, content: str = ""):
        self.role = role
        self.content = content


# ── Model routing tests ────────────────────────────────────────────────────

def test_passthrough(routing_config):
    assert resolve_model("gemma3:4b", [], None, routing_config) == "gemma3:4b"


def test_default_model(routing_config):
    msgs = [_Msg("user", "hello")]
    assert resolve_model("auto", msgs, None, routing_config) == "gemma3:4b"


def test_keyword_coding(routing_config):
    msgs = [_Msg("user", "write code to parse JSON in Python")]
    assert resolve_model("auto", msgs, None, routing_config) == "qwen2.5-coder:7b"


def test_keyword_document(routing_config):
    msgs = [_Msg("user", "find my invoice from last month")]
    assert resolve_model("auto", msgs, None, routing_config) == "phi4-mini"


def test_header_coding(routing_config):
    assert resolve_model("auto", [], "coding", routing_config) == "qwen2.5-coder:7b"


def test_header_document(routing_config):
    assert resolve_model("auto", [], "document", routing_config) == "phi4-mini"


def test_header_long_context(routing_config):
    assert resolve_model("auto", [], "long_context", routing_config) == "gemma3:27b"


def test_unknown_header_falls_back(routing_config):
    msgs = [_Msg("user", "hello")]
    assert resolve_model("auto", msgs, "nonexistent", routing_config) == "gemma3:4b"


# ── finish_reason tests ──────────────────────────────────────────────────────

def test_finish_reason_stop_for_plain_response():
    """finish_reason should be 'stop' when no tool_calls are present."""
    ollama_data = {
        "message": {"role": "assistant", "content": "Hello!"},
        "prompt_eval_count": 10,
        "eval_count": 5,
    }
    result = _normalize_response(ollama_data, "gemma3:4b")
    assert result["choices"][0]["finish_reason"] == "stop"
    assert result["choices"][0]["message"]["content"] == "Hello!"
    assert result["choices"][0]["message"]["tool_calls"] is None


def test_finish_reason_tool_calls_when_tools_present():
    """finish_reason should be 'tool_calls' when tool_calls are present."""
    ollama_data = {
        "message": {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "function": {
                        "name": "web_search",
                        "arguments": {"query": "test"},
                    }
                }
            ],
        },
        "prompt_eval_count": 10,
        "eval_count": 5,
    }
    result = _normalize_response(ollama_data, "gemma3:4b")
    assert result["choices"][0]["finish_reason"] == "tool_calls"
    assert result["choices"][0]["message"]["tool_calls"] is not None
    assert len(result["choices"][0]["message"]["tool_calls"]) == 1


# ── Usage tracking tests ────────────────────────────────────────────────────

def test_usage_tokens_summed_correctly():
    """Usage should correctly sum prompt + completion tokens."""
    ollama_data = {
        "message": {"role": "assistant", "content": "Hi"},
        "prompt_eval_count": 42,
        "eval_count": 8,
    }
    result = _normalize_response(ollama_data, "gemma3:4b")
    assert result["usage"]["prompt_tokens"] == 42
    assert result["usage"]["completion_tokens"] == 8
    assert result["usage"]["total_tokens"] == 50


def test_usage_defaults_to_zero_when_missing():
    """Usage should default to 0 when Ollama doesn't return counts."""
    ollama_data = {"message": {"role": "assistant", "content": "Hi"}}
    result = _normalize_response(ollama_data, "gemma3:4b")
    assert result["usage"]["prompt_tokens"] == 0
    assert result["usage"]["completion_tokens"] == 0
    assert result["usage"]["total_tokens"] == 0


# ── Response structure tests ────────────────────────────────────────────────

def test_response_has_valid_id_and_object():
    """Response should have a valid chat.completion structure."""
    ollama_data = {"message": {"role": "assistant", "content": "Hi"}}
    result = _normalize_response(ollama_data, "gemma3:4b")
    assert result["object"] == "chat.completion"
    assert result["id"].startswith("chatcmpl-")
    assert result["model"] == "gemma3:4b"
    assert "created" in result