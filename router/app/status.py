import time
import httpx
from fastapi import APIRouter, Request

from .config import get_settings

status_router = APIRouter()


@status_router.get("/status")
async def status(request: Request):
    settings = get_settings()
    client: httpx.AsyncClient = request.app.state.http_client

    ollama_models = []
    ollama_error = None
    try:
        resp = await client.get(f"{settings.ollama_base_url}/api/ps", timeout=5.0)
        resp.raise_for_status()
        data = resp.json()
        for m in data.get("models", []):
            vram = m.get("size_vram", 0)
            ollama_models.append({
                "name": m.get("name"),
                "size_vram_mb": round(vram / 1024 / 1024, 1),
                "expires_at": m.get("expires_at"),
            })
    except Exception as e:
        ollama_error = f"{type(e).__name__}: {e or 'no details'}"

    return {
        "status": "ok",
        "timestamp": int(time.time()),
        "ollama": {
            "loaded_models": ollama_models,
            "total_vram_used_mb": round(sum(m["size_vram_mb"] for m in ollama_models), 1),
            **({"error": ollama_error} if ollama_error else {}),
        },
        "gateway": {
            "active_requests": request.app.state.active_requests,
        },
    }
