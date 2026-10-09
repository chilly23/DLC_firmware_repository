# NEXATOM v1.2

A separate copy of `mock1-pyside6` with the requested incremental changes. The supplied v1, v2 and standalone settings projects are untouched.

## Windows

Double-click **Start Nexatom v1.2.cmd** for a 1600 × 720 window, or **Start Fullscreen v1.2.cmd** for fullscreen. Python and Qt are included; no installation is needed. Keep the entire folder together. Startup failures show a message and write `logs/startup.log`.

## Changes

- **TC / CC / PC panels from v2:** tap the module area of any corner readout to choose a module and field. Tap its underlined label to choose a field within the current module. Tap the number to edit. Assignments follow their laser when a pane switches channels. Existing Umax and TC PID P remain in the lists so the original readouts can be restored.
- **White active state:** lock and stabilisation use v1's existing light fill when active; inactive controls have no background fill and use light icons. They no longer turn green. The green readouts retain their original colour.
- **Not Set:** the shortcut text always reads “Not Set”. The existing target-button, shortcut-button and graph peak-selection actions are retained; the numbered target label is removed.
- **Drag/drop:** a short drag pans the v1 graph. Pinch/wheel zoom and double-tap reset are retained. Hold for 550 ms, then drag to the opposite pane to exchange channel panels using v2's skeleton/drop presentation. Releasing outside a valid destination cancels. Short taps still select nearby resonance peaks.
- **Divider:** the central divider ends at Y=605, alongside the graph area.
- **Blinking cursors:** the numeric editor uses native Qt TextInput with cursor-aware insertion, sign changes and backspace. Search retains its native QLineEdit caret. Touch keyboard clicks retain text focus and selection.
- **Settings:** More → Settings on either side opens the supplied **Frame 58 Vertical Wheel** within the app. Closing it returns to the same home and channel state. Its wheel, design, content, keyboard and history are copied from the requested standalone settings application.

## Retained from v1

Home geometry, background `#0E140F`, green readouts `#008622`, typography, graph renderer, waveform behavior, separate graph axes, fullscreen appearance, three-second logo/progress boot, radial menu and the existing button mappings are based on v1. Signals still toggles the error trace, Display opens fullscreen, and Diagnostics shows the original mock-status notice.

This remains the standalone v1 mock: signals and values are simulated locally and work without a controller connection. No v2 TCP transport or disconnected-state behavior is added. New parameter fields store and validate local mock values; their ranges are mock limits, not device specifications. The supplied Frame 58 content is also a preview. Attaching it does not add hardware configuration or firmware updating.

## Raspberry Pi

The included `runtime` and `packages` directories are Windows binaries. On a Pi, use native Python/PySide6 from an existing graphical session:

```sh
python3 main.py
```

Use `--windowed` for a desktop window or `--software` for Qt's software renderer. The original v1 `run.sh` and `setup_pi.sh` are retained for Raspberry Pi OS setup. The Pi dependency pin remains v1's PySide6 Essentials 6.8.0.2; the bundled Windows runtime uses 6.11.2. Yocto needs native Qt/PySide6 and its display plugin. No physical Pi was tested for this revision.

## Verification

```bat
runtime\python.exe tests\verify_v12.py
runtime\python.exe tests\verify_desktop.py
```

51 focused regression checks passed, including actual Qt mouse/touch events. The suite verifies that `controller/plot.py` matches v1 byte for byte when the original folder is present. Both actual Windows launchers also passed startup checks. Results are in `tests/validation.json`, `tests/desktop-window.json` and `tests/desktop-fullscreen.json`. `screenshots/` contains rendered v1.2 states.

Search history/preferences are saved in this copy's `data/`. The source settings application's data is not copied or modified. Channel values and field assignments remain in memory, matching v1's session behavior.
