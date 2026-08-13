#!/usr/bin/env sh
set -eu

if [ -x ".venv/bin/python" ]; then
  exec .venv/bin/python -m build "$@"
fi

exec python -m build "$@"
