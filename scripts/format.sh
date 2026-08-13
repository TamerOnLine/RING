#!/usr/bin/env sh
set -eu

if [ -x ".venv/bin/ruff" ]; then
  exec .venv/bin/ruff format . "$@"
fi

exec ruff format . "$@"
