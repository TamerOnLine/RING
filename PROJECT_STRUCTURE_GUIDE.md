# Project Structure Guide

A standard guide for building maintainable, scalable, and professional Python projects using the Rimg-style architecture.

---

# Goals

Every project should aim to be:

- Clean and easy to understand
- Modular and maintainable
- Easy to test
- Easy to package and distribute
- Ready for future expansion
- Separated by responsibility
- CLI-friendly
- GitHub and PyPI ready

---

# Standard Directory Layout

```text
project-name/
├── pyproject.toml
├── README.md
├── LICENSE
├── .gitignore
├── requirements.txt
├── Makefile
├── .env.example
├── src/
│   └── project_name/
│       ├── __init__.py
│       ├── cli.py
│       ├── web.py
│       ├── core.py
│       ├── config.py
│       ├── utils.py
│       ├── models.py
│       ├── logging.py
│       └── features/
│           ├── __init__.py
│           └── feature_x.py
├── tests/
│   ├── test_core.py
│   ├── test_web.py
│   └── test_features.py
├── scripts/
│   ├── install.sh
│   ├── dev.sh
│   ├── test.sh
│   ├── lint.sh
│   ├── format.sh
│   └── release.sh
├── examples/
├── docs/
├── assets/
└── .github/
    └── workflows/
```

---

# Core Architecture Rules

## 1. Separate Responsibilities

Each file must have a clear responsibility.

### Recommended Structure

| File | Responsibility |
|---|---|
| `web.py` | UI / web interface |
| `cli.py` | command-line interface |
| `core.py` | business logic |
| `config.py` | configuration loading |
| `utils.py` | shared helpers |
| `models.py` | data structures |
| `logging.py` | logging configuration |
| `features/` | isolated feature modules |

Avoid mixing:

- UI code
- business logic
- file operations
- networking
- configuration

inside a single file.

---

# src Layout Rule

Always use:

```text
src/project_name/
```

Do NOT place application code directly in the repository root.

This improves:

- packaging
- imports
- testing
- deployment consistency

---

# pyproject.toml Standard

All projects must use `pyproject.toml`.

Avoid relying only on `requirements.txt`.

Example:

```toml
[project]
name = "project-name"
version = "0.1.0"
description = "Project description"
requires-python = ">=3.11"

dependencies = [
    "fastapi",
    "uvicorn",
]

[project.scripts]
project-name = "project_name.cli:main"

[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"
```

---

# CLI Rules

Every project should expose a runnable command.

Example:

```bash
project-name --help
project-name --port 8080
```

CLI entrypoints should live in:

```text
cli.py
```

---

# Web UI Rules

If the project has a UI:

- UI code goes in `web.py`
- Keep UI independent from core logic
- UI should call clean APIs/functions from `core.py`

Never place processing logic directly inside UI callbacks.

---

# Business Logic Rules

Core logic belongs in:

```text
core.py
```

Core logic must:

- be reusable
- testable
- independent from UI

Good example:

```python
result = process_image(path)
```

Bad example:

```python
button.click(lambda: process_image(path))
```

---

# Feature Isolation

Large features should live in:

```text
features/
```

Example:

```text
features/
├── OCR/
├── export/
├── analysis/
└── ai/
```

Each feature should:

- be isolated
- minimize dependencies
- expose clean APIs

---

# Configuration Rules

Configuration must live in:

```text
config.py
```

Avoid hardcoded:

- ports
- paths
- API keys
- URLs

Use:

- environment variables
- config files
- CLI options

---

# Environment Configuration

Use environment variables for secrets and deployment-specific settings.

Recommended:

```text
.env
.env.example
```

Never commit:

- API keys
- tokens
- credentials

Example:

```python
from dotenv import load_dotenv
```

---

# Logging Rules

Use structured logging.

Avoid excessive `print()` usage.

Preferred:

```python
import logging

logger = logging.getLogger(__name__)
logger.info("Server started")
```

---

# Async Rules

Use async/await consistently when building:

- web APIs
- networking systems
- concurrent pipelines

Avoid mixing sync and async patterns unnecessarily.

Example:

```python
async def fetch_data():
    ...
```

---

# Type Hint Rules

All public functions should use type hints.

Example:

```python
def process_image(path: str) -> bytes:
    ...
```

Benefits:

- better IDE support
- safer refactoring
- easier maintenance
- static analysis support

---

# Testing Rules

All projects should include tests.

Use:

```text
tests/
```

Recommended:

- pytest
- isolated unit tests
- minimal mocking

Tests should cover:

- business logic
- edge cases
- critical workflows

---

# Naming Conventions

## Files

Use:

```text
snake_case.py
```

## Classes

Use:

```python
PascalCase
```

## Functions & Variables

Use:

```python
snake_case
```

---

# Dependency Rules

Keep dependencies minimal.

Before adding a package:

- verify necessity
- verify maintenance quality
- verify compatibility

Avoid dependency bloat.

---

# Code Quality Rules

Projects should use automated formatting and linting.

Recommended tools:

- ruff
- black
- mypy

Example:

```bash
ruff check .
black .
mypy src/
```

Recommended configuration should live in:

```text
pyproject.toml
```

---

# Documentation Rules

Every project should include:

- `README.md`
- installation instructions
- usage examples
- CLI examples
- development notes

---

# Git Rules

Projects should include:

```text
.gitignore
```

Recommended ignores:

```text
__pycache__/
*.pyc
.env
dist/
build/
.venv/
```

---

# Packaging Rules

Projects should be installable using:

```bash
pip install -e .
```

And runnable via:

```bash
project-name
```

---

# Unified Development & Execution Rules

All projects should expose a unified and predictable development workflow.

Developers should be able to run common tasks using standardized commands across all projects.

This improves:

- developer experience
- onboarding speed
- CI/CD consistency
- maintainability
- team collaboration

---

## Standard Commands

Every project should support consistent commands for:

| Task | Command |
|---|---|
| Install | `pip install -e .` |
| Run CLI | `project-name` |
| Run Tests | `pytest` |
| Lint | `ruff check .` |
| Format | `ruff format .` |
| Full Check | `ruff check . && pytest` |

---

## scripts/ Standard

Reusable development scripts should live in:

```text
scripts/
```

Recommended:

```text
scripts/
├── install.sh
├── dev.sh
├── test.sh
├── lint.sh
├── format.sh
└── release.sh
```

Examples:

```bash
bash scripts/dev.sh
bash scripts/test.sh
```

---

## Makefile Standard (Recommended)

Projects are encouraged to expose unified developer commands using:

```text
Makefile
```

Example:

```makefile
install:
	pip install -e .

run:
	project-name

web:
	project-name web

test:
	pytest

lint:
	ruff check .

format:
	ruff format .

check:
	ruff check .
	pytest

clean:
	rm -rf build dist *.egg-info .pytest_cache .mypy_cache .ruff_cache
```

Usage:

```bash
make install
make run
make web
make test
make check
```

---

## CLI Consistency Rule

CLI behavior should remain predictable across projects.

Recommended patterns:

```bash
project-name --help
project-name run
project-name web
project-name serve
project-name test
```

Avoid inconsistent command structures between projects.

---

## Development Environment Rule

Projects should support isolated development environments.

Recommended:

```bash
python -m venv .venv
source .venv/bin/activate
```

Or modern tooling such as:

- uv
- hatch
- poetry

---

## CI Consistency Rule

CI pipelines should use the same standardized commands used locally.

Example:

```bash
make check
```

Avoid duplicating logic between:

- local development
- CI pipelines
- release workflows

---

# Development Scripts

Useful scripts belong in:

```text
scripts/
```

Examples:

```text
scripts/dev.sh
scripts/test.sh
scripts/release.sh
```

Recommended scripts:

```text
scripts/
├── install.sh
├── dev.sh
├── test.sh
├── lint.sh
├── format.sh
└── release.sh
```

Scripts should be simple wrappers around standard project commands.

Example `scripts/test.sh`:

```bash
#!/usr/bin/env bash
set -e

pytest
```

Example `scripts/lint.sh`:

```bash
#!/usr/bin/env bash
set -e

ruff check .
```

---

# Security Rules

Never:

- hardcode secrets
- trust user input
- disable SSL verification
- expose internal stack traces

Validate:

- file paths
- API input
- uploaded files
- external URLs
- environment variables

Use safe defaults.

Keep credentials outside the repository.

---

# Error Handling Rules

Prefer explicit exceptions over silent failures.

Good:

```python
raise ValueError("Invalid image format")
```

Avoid:

```python
except:
    pass
```

Log important failures appropriately.

Do not hide errors that developers need to debug.

Use clear error messages.

---

# Versioning

Use semantic versioning:

```text
MAJOR.MINOR.PATCH
```

Example:

```text
1.4.2
```

Recommended version lifecycle:

- `0.x.x` for early development
- `1.0.0` for stable public release
- patch versions for bug fixes
- minor versions for backward-compatible features
- major versions for breaking changes

---

# CI/CD Rules

Projects should include automated:

- testing
- linting
- formatting checks
- packaging checks

Recommended:

```text
.github/workflows/
```

Example workflow:

```yaml
name: CI

on:
  push:
  pull_request:

jobs:
  check:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - run: pip install -e .
      - run: ruff check .
      - run: pytest
```

CI should run the same commands developers run locally.

---

# Example Workflow

## Create environment

```bash
python -m venv .venv
source .venv/bin/activate
```

## Install

```bash
pip install -e .
```

## Run

```bash
project-name
```

## Run Web App

```bash
project-name web
```

## Test

```bash
pytest
```

## Lint

```bash
ruff check .
```

## Format

```bash
ruff format .
```

## Full Check

```bash
make check
```

---

# Architecture Philosophy

This structure prioritizes:

- long-term maintainability
- clean separation
- scalability
- professional packaging
- deployment readiness

The goal is not minimal file count.

The goal is:

- clarity
- maintainability
- professional engineering structure

---

# Recommended Principles

Always prefer:

- explicit structure
- modularity
- reusable logic
- isolated components
- clean APIs
- predictable layouts
- tested business logic
- standardized commands

Avoid:

- giant files
- mixed responsibilities
- hidden side effects
- hardcoded values
- tightly coupled systems
- inconsistent command patterns
- undocumented setup steps

---

# Final Rule

This structure is recommended for projects expected to grow.

For small scripts or prototypes, start with a minimal subset and expand as needed.
