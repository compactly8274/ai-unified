# AI Unified

A lightweight Python library that provides a unified interface for multiple AI models and services. It includes helpers for OpenAI, Azure, Anthropic, and other LLM providers, as well as utilities for text processing, token counting, and streaming responses.

## Features

- Unified client abstraction for different AI providers
- Helper functions for prompts, tokenization, and streaming
- Easy integration with FastAPI, Flask, and other Python frameworks
- Docker support for containerised deployment
- CI/CD pipelines with GitHub Actions

## Installation

```bash
pip install ai-unified
```

## Quick Start

```python
from ai_unified import OpenAIClient

client = OpenAIClient(api_key="YOUR_OPENAI_KEY")
response = client.chat(messages=[{"role": "user", "content": "Hello!"}])
print(response)
```

## Contributing

Please see our [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to contribute.

## License

This project is licensed under the MIT License – see the [LICENSE](LICENSE) file for details.
