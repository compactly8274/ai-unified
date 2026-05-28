import os
from contextlib import asynccontextmanager

import httpx
import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from .config import get_settings, load_routing_config, load_tools_config
from .router import chat_router
from .status import status_router
from .tools.memory import init_db
from .tools.registry import build_tool_registry

logger = structlog.get_logger()

ROUTING_CONFIG_PATH = os.environ.get("ROUTING_CONFIG_PATH", "/config/routing.yaml")
TOOLS_CONFIG_PATH = os.environ.get("TOOLS_CONFIG_PATH", "/config/tools.yaml")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    await init_db(settings.sqlite_path)
    logger.info("SQLite memory DB ready", path=settings.sqlite_path)

    app.state.http_client = httpx.AsyncClient(timeout=httpx.Timeout(120.0))
    app.state.active_requests = 0

    app.state.routing_config = load_routing_config(ROUTING_CONFIG_PATH)
    app.state.tools_config = load_tools_config(TOOLS_CONFIG_PATH)
    app.state.tool_registry = build_tool_registry(app.state.tools_config, settings)

    logger.info("Startup complete", ollama=settings.ollama_base_url)
    yield

    await app.state.http_client.aclose()
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Unified AI Gateway",
        version="1.0.0",
        description="OpenAI-compatible proxy for Ollama with model routing and tool injection",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def count_requests(request: Request, call_next) -> Response:
        # Don't count the /status poll itself
        if request.url.path != "/status":
            request.app.state.active_requests += 1
        try:
            return await call_next(request)
        finally:
            if request.url.path != "/status":
                request.app.state.active_requests -= 1

    app.include_router(chat_router, prefix="/v1")
    app.include_router(status_router)

    return app


app = create_app()
