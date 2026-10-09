# NEXATOM mock1 — PySide6 + Qt Quick

An executable recreation of the five supplied `mock1` frames. Scope is the three-second boot, two-channel home view, fullscreen graphs, numeric keypad, and expanding radial menu. All signals and values are simulated in memory; this app has no hardware transport.

## Run on Raspberry Pi 5

Use **64-bit Raspberry Pi OS Desktop**, with its graphical session running. Copy/extract this folder onto the Pi, open a terminal inside it, and run:

```bash
bash run.sh
```

The first launch checks/install missing Qt desktop libraries with apt (sudo may request your password), creates `.venv`, and installs the pinned Python dependency. It needs internet for that first setup. Later launches run offline. The app opens fullscreen and plays the 3-second boot animation on every normal launch. The Python/install startup precedes this animation.

Use the display's native **1600 × 720** mode with desktop scaling at 100% for the reference geometry. Other window sizes scale the complete canvas proportionally and letterbox it. There is no responsive rearrangement of controls.

```bash
bash run.sh --windowed             # Desktop review window
bash run.sh --software             # Fallback when GPU/driver setup fails
bash run.sh --windowed --skip-boot # Development only
```

The supported launch path is a Pi desktop session, not Raspberry Pi OS Lite or an unconfigured SSH console. No autostart, system service, GPIO or kiosk OS configuration is installed. The app has no extra exit control on the instrument screen; use the desktop window close action in windowed mode or Ctrl+C in its launch terminal.

PySide6 Essentials 6.8.0.2 is pinned because its ARM64 Linux wheel supports the manylinux 2.31 baseline, suitable for Raspberry Pi OS Bookworm. The same version is used for local verification. The package contains Qt Quick, QML and QtTest; Qt Charts and extra Qt add-ons are not required. Python 3.11 on 64-bit Bookworm is the intended Pi test environment.

## What works

| Control | Mock behavior |
|---|---|
| Arrow above fullscreen | Changes that pane between Laser 1 and Laser 2. Never changes the opposite pane. Both panes can show one laser. |
| Square fullscreen icon | Opens the selected pane's laser across the screen. Exit returns to the two-pane view. |
| Green corner value | Opens the keypad for that parameter and laser. The selected value remains highlighted above the dimmed background. |
| Keypad | Digits, decimal, sign toggle, cursor left/right, backspace, one Enter to apply, red X/outside tap to cancel. Invalid values stay in the editor. |
| Upper lock button | Toggles mock lock. Uses the selected resonance; if none is selected, selects the strongest one. Stops mock resonance drift. |
| Arrow/target button or target label | Selects the next resonance. A tap near a graph peak selects that resonance directly. |
| Wave/lock button | Toggles stabilisation, reducing simulated drift and error noise. The live stream keeps updating. |
| Graph drag | Pans X and Y display coordinates. Absorption and error keep their horizontal axes aligned. This does not write setpoints. |
| Two-finger pinch / mouse wheel | Zooms X around the touch center / pointer. |
| Double tap / double click | Resets that graph's view and the pair's horizontal range. |
| More / red X | Opens the mirrored ring menu in 220 ms / closes it. |

The menu has the **four options shown in Frame 5**. To keep this mock within the requested screens: Signals toggles the error trace; Settings opens the selected laser's top-parameter keypad; Display opens that pane fullscreen; Diagnostics briefly shows that laser's mock status. These are local mock mappings, not additional configuration pages.

Laser 1 defaults to Current / Umax; Laser 2 to Temperature / TC PID P. These fields follow the laser when a pane changes channel. Two views of the same laser share its values, lock, stabilisation, target and trace visibility. Pan/zoom state belongs to the view. The editor captures the laser at opening, and its backdrop prevents other controls from being activated beneath it.

## Code structure

```text
main.py                 Application lifecycle, font, QML registration
controller/model.py     Pure Python laser state, validation, waveform fixture
controller/bridge.py    QObject properties/signals/slots; 20 Hz simulation timer
controller/plot.py      QQuickPaintedItem graph rendering, pan/zoom/peak selection
qml/Main.qml            Screen composition and overlay routing
qml/ChannelPane.qml     Reusable left/right channel view
qml/FullscreenView.qml  Shared fullscreen view for either channel
qml/ParameterTile.qml   Corner value component
qml/NumberPad.qml       Captured edit session and keypad
qml/RadialMenu.qml      Mirrored animated ring and polar hit testing
qml/PlotView.qml        Touch and mouse gesture handling
qml/Icon.qml            Vector icons drawn in Qt
qml/TouchButton.qml     Shared button presentation and input
assets/                 Supplied logo, Roboto font and font license
tests/                  Model and Qt event tests
screenshots/            Captures from the actual running Qt application
```

The renderer samples a six-resonance illustrative waveform with small continuous drift and noise. Current changes its mock amplitude. Temperature, Umax and PID edits update the model/readouts; a physical plant response is intentionally not invented for these fields. The 20 Hz timer is a display refresh target, not a real laser control-loop rate. This renderer uses CPU QPainter into Qt Quick textures; it is adequate as a bounded mock approach, and Pi performance must be measured on the actual display/driver combination.

## Verification

```bash
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
.venv/bin/python tests/verify_ui.py
```

The second command launches Qt offscreen, sends actual pointer events, exercises channel identity/editing/overlays/gestures, and writes screenshots plus `tests/ui-results.json`. Font and icon edges may differ slightly across graphics backends. The original screenshots are visual references, not screenshots used as interactive backgrounds.

Validation was performed on Windows with Qt's offscreen/software renderer. Raspberry Pi hardware, physical multitouch calibration, and GPU frame timing are not verified here. The intended Pi dependency's ARM64 wheel availability was checked; no claim of on-device testing is made.

## Assets and dependencies

Logo: the exact supplied `full lockup transparent white.png`, copied without alteration. Font: Roboto supplied in the prior reference bundle, with its accompanying license. Icons and plots are rendered primitives. Qt/PySide licensing remains applicable to distribution; see the installed package's license material and [Qt for Python licensing](https://doc.qt.io/qtforpython-6/licenses.html).
