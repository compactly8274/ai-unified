import os
from functools import lru_cache
from typing import list

import yaml
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Upstream services (no hardcoded LAN IPs — set via .env) ───────────────
    ollama_base_url: str = "http://localhost:11434"
    searxng_base_url: str = "http://localhost:8080"
    browserless_url: str = ""
    paperless_base_url: str = ""
    paperless_api_token: str = ""

    # ── SQLite Memory ─────────────────────────────────────────────────────────
    sqlite_path: str = "/data/memory.db"
    memory_max_turns: int = 20

    # ── App ───────────────────────────────────────────────────────────────────
    app_port: int = 8000
    log_level: str = "info"

    # ── Security ──────────────────────────────────────────────────────────────
    # Set a random API key to require Bearer auth on all endpoints.
    # Leave empty to disable auth (NOT recommended for networked deployments).
    api_key: str = ""

    # ── CORS ──────────────────────────────────────────────────────────────────
    # Comma-separated list of allowed origins, e.g. "https://chat.example.com"
    # Use "*" to allow all (NOT recommended with auth disabled).
    cors_origins: str = "*"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


def load_routing_config(path: str | None = None) -> dict:
    path = path or os.environ.get("ROUTING_CONFIG_PATH", "config/routing.yaml")
    with open(path) as f:
        return yaml.safe_load(f)


def load_tools_config(path: str | None = None) -> dict:
    path = path or os.environ.get("TOOLS_CONFIG_PATH", "config/tools.yaml")
    with open(path) as f:
        return yaml.safe_load(f)