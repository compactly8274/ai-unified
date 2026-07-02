import os
from contextlib import asynccontextmanager

import httpx
import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings, load_routing_config, load_tools_config
from .router import chat_router
from .status import status_router
from .tools.memory import init_db
from .tools.registry import build_tool_registry

logger = structlog.get_logger()

ROUTING_CONFIG_PATH = os.environ.get("ROUTING_CONFIG_PATH", "config/routing.yaml")
TOOLS_CONFIG_PATH = os.environ.get("TOOLS_CONFIG_PATH", "config/tools.yaml")

# Paths that don't require API key auth
PUBLIC_PATHS = {"/status", "/docs", "/openapi.json", "/redoc"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    await init_db(settings.sqlite_path)
    logger.info("SQLite memory DB ready", path=settings.sqlite_path)

    app.state.http_client = httpx.AsyncClient(timeout=httpx.Timeout(120.0))
    app.state.active_requests = 0

    app.state.routing_config = load_routing_config(ROUTING_CONFIG_PATH)
    app.state.tools_config = load_tools_config(TOOLS_CONFIG_PATH)
    app.state.tool_registry = build_tool_registry(
        app.state.tools_config, settings, http_client=app.state.http_client,
    )

    logger.info("Startup complete", ollama=settings.ollama_base_url)
    yield

    await app.state.http_client.aclose()
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Unified AI Gateway",
        version="1.1.0",
        description="OpenAI-compatible proxy for Ollama with model routing and tool injection",
        lifespan=lifespan,
    )

    # ── CORS (configurable via CORS_ORIGINS env var) ──────────────────────────
    cors_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── API Key authentication ─────────────────────────────────────────────────
    @app.middleware("http")
    async def api_key_auth(request: Request, call_next) -> Response:
        if settings.api_key and request.url.path not in PUBLIC_PATHS:
            auth = request.headers.get("Authorization", "")
            token = ""
            if auth.startswith("Bearer "):
                token = auth[7:]
            elif auth.startswith(""):
                token = auth
            if token != settings.api_key:
                return Response(
                    content='{"detail":"Invalid or missing API key"}',
                    status_code=401,
                    media_type="application/json",
                )
        return await call_next(request)

    # ── Request counter ────────────────────────────────────────────────────────
    @app.middleware("http")
    async def count_requests(request: Request, call_next) -> Response:
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