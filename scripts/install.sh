#!/usr/bin/env sh
set -eu

if [ -x ".venv/bin/python" ]; then
  exec .venv/bin/python -m pip install -e ".[dev]"
fi

exec python -m pip install -e ".[dev]"
