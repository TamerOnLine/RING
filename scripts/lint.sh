#!/usr/bin/env sh
set -eu

if [ -x ".venv/bin/ruff" ]; then
  exec .venv/bin/ruff check . "$@"
fi

exec ruff check . "$@"
