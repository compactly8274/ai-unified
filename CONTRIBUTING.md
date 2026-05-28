# Contributing to AI Unified

Thank you for considering contributing! We welcome contributions of all kinds.

## How to Contribute

1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/awesome-feature`).
3. Write code and tests.
4. Ensure the test suite passes: `pytest`.
5. Open a pull request against the `repo-improvements` branch.

## Development Setup

```bash
git clone https://github.com/compactly8274/ai-unified.git
cd ai-unified
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

The `[dev]` extra installs testing and linting dependencies (see `pyproject.toml`).

## Code Style

- Run `ruff` and `black` before committing.
- Type hints should be added where possible; run `mypy`.
- Keep the public API stable; update the documentation as needed.
