import time
import httpx
from fastapi import APIRouter, Request

status_router = APIRouter()

_active_requests: int = 0


@status_router.get("/status")
async def status(request: Request):
    from .config import get_settings
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
        ollama_error = str(e)

    return {
        "status": "ok",
        "timestamp": int(time.time()),
        "ollama": {
            "loaded_models": ollama_models,
            "total_vram_used_mb": round(sum(m["size_vram_mb"] for m in ollama_models), 1),
            **({"error": ollama_error} if ollama_error else {}),
        },
        "gateway": {
            "active_requests": _active_requests,
        },
    }
