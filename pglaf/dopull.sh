#!/usr/bin/env bash

# Backward-compatible wrapper around the Python implementation.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$SCRIPT_DIR/dopull.py" "$@"
