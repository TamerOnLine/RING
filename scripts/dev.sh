#!/usr/bin/env sh
set -eu

if [ -x ".venv/bin/python" ]; then
  exec .venv/bin/python -m rimg.cli "$@"
fi

exec python -m rimg.cli "$@"
