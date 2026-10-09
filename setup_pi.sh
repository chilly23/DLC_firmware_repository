#!/usr/bin/env bash
# Root-only, one-time Raspberry Pi OS dependencies and device access.
set -euo pipefail
if ((EUID != 0)); then echo 'This helper is invoked by run.sh through the OS authentication dialog.' >&2; exit 1; fi
device_user="${1:?Device username is required}"
device_uid="$(id -u "$device_user")"
case "$(uname -m)" in aarch64|x86_64) ;; *) echo 'Use 64-bit Raspberry Pi OS Desktop.' >&2; exit 1;; esac
case "$(dpkg --print-architecture)" in arm64|amd64) ;; *) echo 'A 64-bit userland is required for the Qt wheel.' >&2; exit 1;; esac
apt-get update
apt-get install -y python3-venv python3-pip python3-dev build-essential gpiod ddcutil i2c-tools acl zenity \
  libegl1 libopengl0 libxkbcommon0 libxkbcommon-x11-0 libxcb-cursor0 libxcb-icccm4 \
  libxcb-image0 libxcb-keysyms1 libxcb-render-util0 libxcb-xinerama0 libxcb-xkb1 fonts-dejavu-core
if apt-cache show wlr-randr >/dev/null 2>&1; then apt-get install -y wlr-randr; fi
for group in gpio i2c video; do
  getent group "$group" >/dev/null || groupadd --system "$group"
  usermod -aG "$group" "$device_user"
done
cat > /etc/udev/rules.d/72-nexatom-controls.rules <<EOF
SUBSYSTEM=="gpio", KERNEL=="gpiochip*", GROUP="gpio", MODE="0660", TAG+="uaccess"
SUBSYSTEM=="i2c-dev", KERNEL=="i2c-*", GROUP="i2c", MODE="0660", TAG+="uaccess"
SUBSYSTEM=="backlight", ACTION=="add", RUN+="/bin/chown $device_uid /sys%p/brightness"
EOF
# HDMI DDC uses existing I2C buses. Do NOT enable i2c_arm: GPIO2/3 are Knob 1 inputs.
printf 'i2c-dev\n' > /etc/modules-load.d/nexatom-ddc.conf
modprobe i2c-dev || true
udevadm control --reload-rules
udevadm trigger --subsystem-match=gpio
udevadm trigger --subsystem-match=i2c-dev
udevadm settle
for node in /dev/gpiochip* /dev/i2c-*; do
  if [[ -e "$node" ]]; then setfacl -m "u:$device_user:rw" "$node"; fi
done
for file in /sys/class/backlight/*/brightness; do
  if [[ -f "$file" ]]; then chown "$device_uid" "$file"; fi
done
echo 'Nexatom OS dependencies and GPIO/display access installed.'
