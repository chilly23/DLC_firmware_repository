#!/usr/bin/env bash
# One command: bash run.sh. First launch provisions; subsequent launches run.
set -euo pipefail
APP_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_DIR"
mkdir -p logs
exec > >(tee -a logs/pi-startup.log) 2>&1
fail() {
  echo "Nexatom launch failed. See $APP_DIR/logs/pi-startup.log"
  if command -v zenity >/dev/null; then zenity --error --title='Nexatom v1.9' --text="Startup failed. See $APP_DIR/logs/pi-startup.log" || true;
  elif [[ -t 0 ]]; then read -r -p 'Press Enter to close.' _ || true; fi
}
trap fail ERR
if [[ -z "${DISPLAY:-}" && -z "${WAYLAND_DISPLAY:-}" && -z "${QT_QPA_PLATFORM:-}" ]]; then
  echo 'Open this launcher in the Pi desktop session so it can reach the touchscreen.'; exit 1
fi
if ((EUID==0)); then echo 'Run as the normal desktop user. The installer alone requests administrator access.'; exit 1; fi
if [[ "${1:-}" == '--repair-setup' ]]; then rm -f -- .os-ready-v18; shift; fi
if [[ ! -f .os-ready-v18 ]]; then
  if ! command -v apt-get >/dev/null; then echo 'Automatic setup targets Raspberry Pi OS. For Yocto, see README.md.'; exit 1; fi
  echo 'Installing GPIO, display and Qt dependencies. The OS may ask for authentication.'
  if command -v pkexec >/dev/null && [[ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]]; then
    pkexec /bin/bash "$APP_DIR/setup_pi.sh" "$(id -un)"
  else sudo /bin/bash "$APP_DIR/setup_pi.sh" "$(id -un)"; fi
  touch .os-ready-v18
fi
if [[ ! -x .venv/bin/python ]]; then python3 -m venv .venv; fi
if ! .venv/bin/python -c 'import PySide6,gpiod; from PySide6.QtQuick import QQuickWindow; assert PySide6.__version__=="6.8.0.2" and hasattr(gpiod,"request_lines")' >/dev/null 2>&1; then
  .venv/bin/python -m pip install --upgrade pip
  .venv/bin/python -m pip install -r requirements.txt
fi
.venv/bin/python install_pi_shortcut.py
echo 'Starting Nexatom v1.9. Close the standalone RKJXT demo if it owns the pins.'
.venv/bin/python main.py "$@"
