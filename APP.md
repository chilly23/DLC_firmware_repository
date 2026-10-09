# NEXATOM v1.4 — based on v1.2

An incremental PySide6 release preserving the accepted v1.2 home layout, green
parameter readouts, radial menu, module selectors, graph drag/drop, and attached
Frame 58 settings wheel. The original v1.2 files are not modified.

## Run

Windows: double-click `Start Nexatom v1.4.cmd` or `Start Fullscreen v1.4.cmd`.
The included runtime uses Python 3.13 and PySide6 6.11.2. Startup errors are written
to `logs/startup.log` and shown in a dialog instead of silently closing.

For Raspberry Pi OS, the existing installer remains available:

```bash
bash run.sh
```

It creates a virtual environment and installs the requirements, so its first run
requires network access. For an already provisioned Linux/Yocto Python environment
with PySide6 QtQuick, QtQml, QtWidgets, QtGui and QtCore available:

```bash
python3 main.py
```

Run inside the device's graphical session. The bundled Windows `runtime` and
`packages` directories cannot be used on ARM Linux. `--windowed`, `--software`,
`--skip-boot`, and `--data-dir PATH` are available. This release was verified on
Windows; the physical Pi/Yocto image and its touchscreen have not been tested.

## Behavior

The logo/progress boot lasts three seconds. Acquisition then begins at exactly
zero, with a 1.5-second smooth rise of both spectroscopy and error signals.
Emission-off uses the same smooth transition down to exact zero. Reversing the
transition starts from the current amplitude without a jump. X coordinates stay
fixed during these transitions.

The first side button locks the graph view, including pan, zoom, peak selection,
double-tap reset, and long-press channel drag. Acquisition continues. The second
button controls simulated emission. The third blends into a warm temporal
low-pass filter to reduce live noise. Each channel owns these states, so two
panes showing the same laser stay consistent. White means active; inactive
buttons are unfilled. Open/closed padlocks and vector chevrons use the same stroke
width as the other vector controls. The numeric minus is a 32-pixel horizontal line.

Each plot pair uses one coherent signal buffer and one synchronized X range.
Only the lower error plot labels the shared X axis, including in fullscreen.
Vertical pan is bounded so the zero line remains within view. The two laser
models use different peak positions, widths, strengths and noise phases.

Accepted numeric edits update the channel immediately and the signal model
approaches the new values smoothly. Values remain setpoints; they are not invented
measurement readbacks. Parameter effects in this visual model:

| Parameter | Simulated effect |
|---|---|
| Current | Peak intensity |
| Temperature | Peak position |
| Umax | Intensity scaling |
| PID P | Error-signal gain |
| Feedforward | Baseline slope |
| Offset | Peak positions |
| Scan amplitude | Peak spacing |
| Scan frequency | Drift/noise rate |
| Lock setpoint | Error-signal offset |

This is a visual simulation, not a model of a physical control loop. There is no
hardware transport, hardware emission command, or real servo loop in this release.

## Keyboard and settings

Native touch owns its gesture. Compatibility mouse events immediately following
that touch are ignored; genuine rapid mouse taps remain valid. Suggestions replace
the word at the cursor rather than appending the current query again. Shift,
numeric mode, backspace, selection replacement and native physical-key input work.
The search editor and numpad retain native blinking cursors.

The adjacent search button is a read-only history viewer with Clear. Submitted
queries are saved to `data/settings.json`, deduplicated, and limited to eight.
History entries do not re-run a search. Clear persists, and outside taps dismiss
the popup. The Frame 58 function page controls the same emission and smoothing
states as home, and its refresh-rate choice changes the actual display timer.
Other inherited settings pages retain their v1.2 preview behavior; device-level
brightness, firmware, storage and sound are not hardware integrations.

## Code map

| Location | Responsibility |
|---|---|
| `main.py` | App creation, fonts, QML registration, settings attachment |
| `controller/model.py` | Two channel states, parameter validation, pane assignments |
| `controller/simulation.py` | Distinct signals, smooth envelopes, slew and filtering |
| `controller/bridge.py` | Shared controller API and live frame timer |
| `controller/plot.py` | Trace rendering, gestures and shared axis presentation |
| `qml/` | Preserved home, number pad, selectors, radial menu and graph drag |
| `settings_ui/` | Frame 58 wheel, native search, touch keyboard and history |
| `tests/` | Behavioral checks, desktop launcher checks, package builder |
| `screenshots/` | Rendered verification states |

## Verification

```powershell
.\runtime\python.exe tests\verify_v14.py
.\runtime\python.exe tests\verify_desktop.py
```

The regression suite drives the actual Qt UI using mouse and native touch events,
checks startup/emission transitions, locked gestures, real parameter effects,
measured noise reduction, module/numpad edits, shared axes, fullscreen, pinch,
drag/drop, keyboard duplication, suggestions, history persistence, and settings
integration. Results are in `tests/validation.json`; desktop reports verify both
actual Windows launchers. `tests/reproduce_keyboard.py` is the original v1.2
regression reproduction and requires the sibling `mock1.2-pyside6` folder.

`tests/package_release.py` builds Windows and source ZIPs with SHA-256 checksums,
excluding personal settings/history, logs, exports and Python caches.
