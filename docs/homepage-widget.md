# Homepage Widget — AI Gateway Status

## What `/status` Returns

```json
{
  "status": "ok",
  "timestamp": 1716000000,
  "ollama": {
    "loaded_models": [
      {
        "name": "gemma3:4b",
        "size_vram_mb": 4200.5,
        "expires_at": "2026-05-26T12:00:00Z"
      }
    ],
    "total_vram_used_mb": 4200.5
  },
  "gateway": {
    "active_requests": 0
  }
}
```

## `services.yaml` Snippet

```yaml
- AI:
    - AI Gateway:
        icon: ollama.png
        href: http://192.168.1.X:8000/docs
        description: Unified AI Router
        widget:
          type: customapi
          url: http://192.168.1.X:8000/status
          refreshInterval: 10000
          mappings:
            - field:
                ollama: total_vram_used_mb
              label: VRAM Used (MB)
              format: number
            - field: gateway.active_requests
              label: Active Requests
              format: number
            - field: status
              label: Gateway
              format: text
```

Replace `192.168.1.X` with the LAN IP of the host running docker compose.

If Homepage runs in the same Docker network as `ai-router`, you can use:
```yaml
url: http://ai-router:8000/status
```
