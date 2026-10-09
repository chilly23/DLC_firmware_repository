#!/usr/bin/env bash
# One entry point: stage, provision, register startup, launch.
set -euo pipefail
APP_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ "$APP_DIR" != "$HOME/nexatom" ]]; then
  if ! APP_DIR="$(python3 "$APP_DIR/install.py")"; then
    echo 'Could not copy Nexatom into your home folder. Check free space and folder permissions.' >&2
    if command -v zenity >/dev/null; then zenity --error --title=Nexatom --text='Could not copy the app to ~/nexatom. Check free space and permissions.' || true;
    elif [[ -t 0 ]]; then read -r -p 'Setup failed. Close this terminal after reviewing the error.' ignored || true;fi
    exit 1
  fi
  exec /bin/bash "$APP_DIR/start.sh" "$@"
fi
cd "$APP_DIR"
mkdir -p logs
exec > >(tee -a logs/setup.txt) 2>&1
fail() {
  echo 'Nexatom could not start. Read logs/setup.txt.'
  if command -v zenity >/dev/null; then zenity --error --title=Nexatom --text="Setup/start failed. Details: $APP_DIR/logs/setup.txt" || true; fi
}
trap fail ERR
if ((EUID==0)); then echo 'Launch as the normal desktop user; setup requests administrator access itself.'; exit 1; fi
if [[ -z "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]]; then echo 'Launch in the Raspberry Pi graphical desktop.'; exit 1; fi
automatic=false
if [[ "${1:-}" == --autostart ]]; then automatic=true;shift; fi
repair=false
if [[ "${1:-}" == --repair || "${1:-}" == --repair-setup ]]; then repair=true;shift; fi
# No two app/setup launches may own the same pins. Repair may run beside the UI.
if ! $repair; then
  exec 9>"${XDG_RUNTIME_DIR:-/tmp}/nexatom-$UID.lock"
  if ! flock -n 9; then
    echo 'Nexatom is already running. Close it before starting this update.'
    if ! $automatic && command -v zenity >/dev/null; then
      zenity --info --title=Nexatom --text='Nexatom is already running. Close the running app before starting this update.' || true
    fi
    exit 0
  fi
fi
healthy=false
if [[ -x .venv/bin/python ]] && .venv/bin/python -c 'from PySide6.QtQuick import QQuickWindow; import numpy; import gpiod; assert hasattr(gpiod,"request_lines")' >/dev/null 2>&1; then healthy=true; fi
gpio_access=true
for node in /dev/gpiochip*; do
  if [[ -e "$node" && ( ! -r "$node" || ! -w "$node" ) ]]; then gpio_access=false; fi
done
capture_ready=true
if [[ -n "${WAYLAND_DISPLAY:-}" ]] && ! command -v grim >/dev/null; then capture_ready=false; fi
if [[ ! -f .ready ]] || ! $healthy || ! $gpio_access || ! $capture_ready || $repair; then
  echo 'Installing operating-system packages and configuring GPIO access...'
  if command -v sudo >/dev/null && sudo -n true 2>/dev/null; then sudo -n /bin/bash "$APP_DIR/setup.sh" "$(id -un)";
  elif command -v pkexec >/dev/null; then pkexec /bin/bash "$APP_DIR/setup.sh" "$(id -un)";
  else sudo /bin/bash "$APP_DIR/setup.sh" "$(id -un)"; fi
  if [[ ! -x .venv/bin/python ]]; then python3 -m venv .venv; fi
  .venv/bin/python -m pip install --upgrade pip
  .venv/bin/python -m pip install -r requirements.txt
  .venv/bin/python -c 'from PySide6.QtQuick import QQuickWindow; import numpy; import gpiod; assert hasattr(gpiod,"request_lines")'
  python3 startup.py
  touch .ready
  if $repair; then zenity --info --title=Nexatom --text='Setup complete. Restart the app to use repaired dependencies. Reboot the Pi if GPIO boot configuration changed.' || true;exit 0;fi
fi
if [[ -f .reboot ]] && ! $automatic; then
  if zenity --question --title=Nexatom --ok-label='Restart now' --cancel-label='Start app' --text='GPIO boot settings and desktop startup are ready. Restart once to apply pin changes, or open the app now.'; then
    rm -f .reboot
    systemctl reboot
    exit 0
  fi
fi
echo 'Starting Nexatom...'
.venv/bin/python main.py "$@"
