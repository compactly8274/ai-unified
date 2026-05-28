"""Basic smoke tests for the AI gateway router logic (no live Ollama required)."""
import os
import sys

import pytest
import yaml

# Add router to path so tests can import from app.*
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "router"))

from app.router import resolve_model


@pytest.fixture
def routing_config():
    cfg_path = os.path.join(os.path.dirname(__file__), "..", "config", "routing.yaml")
    with open(cfg_path) as f:
        return yaml.safe_load(f)


class _Msg:
    def __init__(self, role: str, content: str = ""):
        self.role = role
        self.content = content


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
