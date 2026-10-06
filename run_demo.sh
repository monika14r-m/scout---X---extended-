#!/usr/bin/env bash
set -e

MODE="${1:-normal}"

cd "$(dirname "$0")"

if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

python3 demo.py --mode "$MODE"
