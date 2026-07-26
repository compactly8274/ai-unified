# Unified AI Gateway

An OpenAI-compatible API gateway that proxies requests to a local [Ollama](https://ollama.ai) instance with intelligent model routing and tool injection.

## Features

- **OpenAI-compatible API** — drop-in replacement for `openai` client libraries
- **Automatic model routing** — routes requests to the right model based on keywords or headers
- **Tool injection** — automatically injects web search (SearXNG), document search (Paperless-NGX), and conversation memory (SQLite) as OpenAI-compatible tools
- **Streaming support** — full SSE streaming with tool call forwarding
- **API key authentication** — optional Bearer token auth for all endpoints
- **Docker-ready** — single Dockerfile + docker-compose for deployment

## Quick Start

### Docker Compose (recommended)

```bash
# 1. Copy environment file and edit values
cp .env.example .env

# 2. Start the gateway
docker compose up -d

# 3. Test it
curl http://localhost:8000/v1/models
```

### Local Development

```bash
cd router
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/chat/completions` | POST | OpenAI-compatible chat completions (stream + non-stream) |
| `/v1/models` | GET | List available Ollama models + router aliases |
| `/status` | GET | Gateway health + Ollama status (no auth required) |
| `/docs` | GET | Auto-generated API docs (Swagger UI) |

## Model Routing

### Passthrough

Any model in the `passthrough` list in `config/routing.yaml` is sent directly to Ollama without modification.

### Auto-routing

Use `model: "auto"` to let the gateway pick the best model:

- **Keyword-based** — scans system + first user message for keywords (e.g. "write code" → coding model)
- **Header-based** — set `X-Task-Type: coding|general|document|long_context` to force a model
- **Fallback** — falls back to `default_model` if no rules match

### Custom Headers

| Header | Description |
|--------|-------------|
| `X-Task-Type` | Force routing to a task type (overrides keyword detection) |
| `X-Conversation-ID` | Used for conversation memory persistence (auto-generated if absent) |
| `Authorization` | `Bearer <API_KEY>` when `API_KEY` env var is set |

## Configuration

### Environment Variables

See `.env.example` for all options. Key variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API URL |
| `SEARXNG_BASE_URL` | `http://localhost:8080` | SearXNG search URL |
| `PAPERLESS_BASE_URL` | _(empty)_ | Paperless-NGX URL |
| `PAPERLESS_API_TOKEN` | _(empty)_ | Paperless-NGX API token |
| `SQLITE_PATH` | `/data/memory.db` | SQLite DB path for conversation memory |
| `API_KEY` | _(empty)_ | Set to require Bearer auth |
| `CORS_ORIGINS` | `*` | Comma-separated allowed origins |

### Routing Config

Edit `config/routing.yaml` to define models, task types, keyword rules, and passthrough models.

### Tools Config

Edit `config/tools.yaml` to enable/disable individual tools and configure their behavior.

## Built-in Tools

| Tool | Name | Description |
|------|------|-------------|
| **SearXNG** | `web_search` | Web search via SearXNG |
| **Paperless** | `paperless_search` | Document search in Paperless-NGX |
| **Memory** | `memory_recall` | Recall previous conversation turns from SQLite |

Tools are automatically injected as OpenAI-compatible function definitions when enabled. Ollama models that support tool calling will use them automatically.

## License

MIT