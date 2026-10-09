#!/usr/bin/env bash
set -euo pipefail
APP_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_DIR"
if [[ "$(uname -s)" == Linux ]] && command -v apt-get >/dev/null 2>&1; then
    bash "$APP_DIR/setup_pi.sh"
fi
if [[ ! -x .venv/bin/python ]]; then
    python3 -m venv .venv
fi
if ! .venv/bin/python -c 'import PySide6; assert PySide6.__version__ == "6.8.0.2"' >/dev/null 2>&1; then
    .venv/bin/python -m pip install --upgrade pip
    .venv/bin/python -m pip install -r requirements.txt
fi
exec .venv/bin/python main.py "$@"
