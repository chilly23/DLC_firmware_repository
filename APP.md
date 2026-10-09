# Nexatom v1.6

Double-click **Start Nexatom v1.6.cmd** or **Start Fullscreen v1.6.cmd**.
The Windows runtime is included. This is a separate working copy of v1.5;
no older version is modified and no ZIP exports are created.

## Changes

- Signals panels are centred within the opposite 800 × 720 half. Only that
  half gets the dark scrim; the selected laser stays at normal brightness.
  Active controls use the same `#BDC0BB` white as the home buttons.
- Emission-off dims that laser's charts, labels and side controls smoothly.
  Its emission button and both green parameter tiles retain full brightness.
  The controls remain usable, and the zero traces remain visible.
- The More menu expands and retracts over 800 ms with eased motion. Its cached
  sectors scale from the More button; selecting an option finishes the closing
  animation before opening that screen. Acquisition continues during animation;
  chart repainting resumes with current data afterward.
- Settings has no header strip. Its wheel spans the full height, and Settings
  plus the close button sit at the top right. The native window frame and panel
  outlines are removed. All input and keyboard fonts use the default Roboto.
- Drag targets use your supplied `assets/dragndrop-white.png` unchanged.
- Graph tick labels use 14 px type and at most two decimal places, without
  scientific notation or negative zero. This applies to both axes/fullscreen.
- Search uses the reference-inspired circular-key keyboard: letters, Shift,
  backspace, caret arrows, space and Return. It occupies 65% of the design width
  at the bottom centre, with the live native editor inside its header. Tap the
  dark background or X to dismiss it. No number row or suggestion bar is shown.
  Instrument and Y-axis numeric editors are retained.
- Hold backspace for 650 ms to clear the entire search or numeric input. A short
  press keeps normal backspace behavior; releasing after a hold does not repeat it.
- History displays the last eight actual searches, saved on Return or keyboard
  dismissal in `data/settings.json`. Clear removes the saved history immediately.
- Graph panning permits a small offset but keeps the acquired X domain and some
  trace visible. This also applies in fullscreen. Manual Y-axis entries retain
  their existing range.

The v1.5 per-laser Combined/Split, Y-axis, ratio, and drag behavior is preserved.
Signals remain local simulations. Physical Raspberry Pi/touchscreen testing is
still needed; on a provisioned Linux graphical session run `python3 main.py`.

## Files for the next version

| File | Purpose |
|---|---|
| `qml/Colors.js` | Shared active white and idle opacity |
| `qml/SignalsPanel.qml` | Panel placement, opposite-half scrim and controls |
| `qml/ChannelPane.qml` | Home idle appearance |
| `qml/RadialMenu.qml` | Cached radial reveal |
| `controller/plot.py` | Tick formatting and trace rendering |
| `controller/bridge.py` | Acquisition and short presentation-busy state |
| `settings_ui/keyboard.py` | Custom key geometry, drawing and hit regions |
| `settings_ui/window.py` | Native editor, dim layer, input routing and full-height wheel |
| `settings_ui/layout.py` | Keyboard and search dimensions |

Checks: `runtime\python.exe tests\verify_v16.py`,
`runtime\python.exe tests\verify_charts.py`, and
`runtime\python.exe tests\verify_desktop.py`.
Screenshots and results stay under `tests/`. `tests/profile_frames.py` is a small
profiling helper for later HMI performance work. Startup errors go to
`logs/startup.log`.
