#!/usr/bin/env bash
# Invoked by run.sh. Installs only missing desktop runtime prerequisites.
set -euo pipefail
case "$(uname -m)" in
    aarch64|x86_64) ;;
    *) echo 'Use a 64-bit Raspberry Pi OS Desktop installation (aarch64).' >&2; exit 1 ;;
esac
packages=(python3-venv libegl1 libopengl0 libxkbcommon0 libxkbcommon-x11-0
          libxcb-cursor0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1
          libxcb-render-util0 libxcb-xinerama0 libxcb-xkb1)
missing=()
for package in "${packages[@]}"; do
    if ! dpkg-query -W -f='${Status}' "$package" 2>/dev/null | grep -q 'install ok installed'; then
        missing+=("$package")
    fi
done
if ((${#missing[@]})); then
    echo "Installing missing Qt desktop prerequisites: ${missing[*]}"
    if ((EUID == 0)); then
        apt-get update
        apt-get install -y "${missing[@]}"
    else
        sudo apt-get update
        sudo apt-get install -y "${missing[@]}"
    fi
fi
if [[ -z "${DISPLAY:-}" && -z "${WAYLAND_DISPLAY:-}" && -z "${QT_QPA_PLATFORM:-}" ]]; then
    echo 'Run from a terminal in the Pi desktop session so Qt can reach the touchscreen.' >&2
    exit 1
fi
