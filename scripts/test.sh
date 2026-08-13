#!/usr/bin/env sh
set -eu

if [ -x ".venv/bin/pytest" ]; then
  exec .venv/bin/pytest "$@"
fi

exec pytest "$@"
