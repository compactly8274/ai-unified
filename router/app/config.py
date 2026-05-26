from functools import lru_cache
import yaml
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ollama_base_url: str = "http://192.168.1.122:11434"
    searxng_base_url: str = "http://192.168.1.7:8080"
    browserless_url: str = "http://192.168.1.104:3012"
    paperless_base_url: str = ""
    paperless_api_token: str = ""
    sqlite_path: str = "/data/memory.db"
    memory_max_turns: int = 20
    app_port: int = 8000
    log_level: str = "info"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


def load_routing_config(path: str = "/config/routing.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def load_tools_config(path: str = "/config/tools.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)
