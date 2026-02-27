# Contributing to feishu-miqroera-mcp

Thank you for your interest in this project! Contributions of any kind are welcome.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How to Contribute](#how-to-contribute)
- [Development Setup](#development-setup)
- [Code Style](#code-style)
- [Submitting a PR](#submitting-a-pr)
- [Issue Guidelines](#issue-guidelines)

## Code of Conduct

Please be kind and respectful. We welcome contributors from all backgrounds.

## How to Contribute

- **Bug fixes**: Open an Issue describing the problem, or submit a PR directly
- **New Tool**: Open an Issue first to discuss the design; start development after approval
- **Documentation improvements**: Submit a PR directly; no Issue needed
- **Performance optimizations**: Include benchmark data

## Development Setup

```bash
# 1. Fork and clone
git clone https://github.com/your-username/feishu-miqroera-mcp.git
cd feishu-miqroera-mcp

# 2. Create a virtual environment
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# 3. Install dev dependencies
pip install -e ".[dev]"

# 4. Configure environment variables
cp .env.example .env
# Edit .env and fill in your Feishu app credentials

# 5. Run tests
pytest tests/unit/ -v
```

## Code Style

This project uses the following tools; ensure all checks pass before submitting:

```bash
# Format
ruff format src/ tests/

# Lint
ruff check src/ tests/

# Type check (optional but recommended)
mypy src/feishu_mcp/
```

### Key conventions

- All functions and classes must have docstrings (English)
- New Tools should be implemented in the corresponding module under `src/feishu_mcp/tools/`
- Each Tool function must be registered in `server.py`
- Integration tests require real Feishu credentials — do **not** commit credentials to the repository

## Submitting a PR

1. Create a feature branch from `main`: `git checkout -b feat/my-feature`
2. Finish development and pass all unit tests
3. Update `docs/api.md` if you added a new Tool
4. Submit a PR with a title following this format:
   - `feat: add XXX tool`
   - `fix: fix XXX issue`
   - `docs: update API docs`
   - `refactor: refactor XXX module`
5. In the PR description explain: what changed, why, and how to test

## Issue Guidelines

### Bug Report

Please include:
- Steps to reproduce
- Expected behavior vs. actual behavior
- Python version and OS
- Relevant logs (anonymized)

### Feature Request

Please include:
- Description of the use case
- Proposed interface design (Tool name, parameters)
- Link to the relevant Feishu API documentation

## Directory Structure

```
src/feishu_mcp/
├── server.py          # MCP entry point, registers all Tools
├── auth.py            # Token management
├── tools/
│   ├── messages.py    # Message-related Tools
│   ├── tasks.py       # Task-related Tools
│   ├── calendar.py    # Calendar-related Tools
│   ├── documents.py   # Document-related Tools
│   └── users.py       # User-related Tools
└── webhook/
    ├── longconn.py    # Feishu long-connection event listener
    └── handler.py     # HTTP Webhook (fallback)
```

## Steps to Develop a New Tool

1. Implement the business function in the corresponding module (e.g. `tools/tasks.py`)
2. Add the new Tool in the `@app.tool()` section of `server.py`
3. Write a corresponding unit test under `tests/unit/`
4. Add Tool documentation in `docs/api.md`
5. Update the tool list in `README.md`
