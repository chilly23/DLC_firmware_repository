#!/usr/bin/env bash
# Separate profile: no staging, startup registration or production preferences.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if [[ ! -x .benchvenv/bin/python ]]; then python3 -m venv .benchvenv; fi
if ! .benchvenv/bin/python -c 'import numpy; from PySide6.QtQuick import QQuickWindow; import gpiod' >/dev/null 2>&1; then
  .benchvenv/bin/python -m pip install -r requirements.txt
fi
exec .benchvenv/bin/python main.py --benchmark --skip-boot "$@"
