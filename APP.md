# Nexatom v1.15 - Lobby and navigation

Built on **v1.14**, which remains untouched. Native PySide6/QML application for the existing 1600 x 720 HMI; no HTML or browser dependency.

![Lobby preview](tests/lobby/03-lobby.png)

## Run

**Windows:** open [start.cmd](start.cmd). Python, Qt and assets are included. The normal three-second boot leads to fullscreen Home. Use `start.cmd --windowed` for a desktop window.

**Raspberry Pi OS, 64-bit desktop:** copy this folder, then run `bash start.sh`. The inherited installer stages to `~/nexatom`, preserves installed data/calibration, installs dependencies, configures GPIO access and desktop startup. It may request OS administrator authentication and a reboot. The existing GPIO pin and startup behavior is described in the [v1.14 documentation](../v1.14/README.md).

Wayland screen capture uses **grim**, now included in setup and checked on upgrade. Capture needs a compatible compositor such as Raspberry Pi OS labwc. This release has been tested on Windows, not on a physical CM5.

## Navigation

**Home > More > Lobby** opens the additional tools. More's QML is the v1.9 source, unchanged except for replacing the Display and Diagnostics destinations with Logs and Lobby. Its geometry, timing, easing, drawing and cancellation animation are preserved.

The Lobby packs **20 square-corner rectangles** into an eight-column, six-row grid with eight-pixel gutters: 17 working options and three visible placeholders. Larger rectangles prioritize Buttons Panel, DLC, File Manager and Control Parameters. Every option has an icon. Lobby and its subpages retain the application background and use zero corner radius.

| Lobby option | Behavior |
| --- | --- |
| Buttons Panel | Assign left/right shortcuts; drag rows with mouse or touch to reorder each side. Up/down controls also work. Assignments and order persist. |
| DLC | Open the existing GPU 3D assembly viewer; access laser configuration and controller information. |
| Graph Size | Small, Medium or Large, applied immediately to both Home graphs and their drag targets. Large is the default; its graph frames have a 12 px centre gap. |
| Screenshot | Capture the entire current display, including other visible applications. |
| File Manager | Browse data, screenshots, exports and user files; open folders/files using the host. |
| Diagnostics | Open the existing Control Settings interface, returning to Lobby. |
| System Monitoring | Live host CPU, memory, temperature where available, storage, uptime and control-input status. Polling stops when this page closes. |
| Control Parameters | Open existing Function Settings. |
| Laser Config / Sub Parameters | Edit both lasers through the existing validated numeric editor. |
| Home Controls | Choose Home corner fields and side-button labels. |
| Legal Info | Software notices; explicitly identified space for product-specific legal terms. |
| Digital Manual | Existing searchable help and interactive guide. |
| Display Settings / Notifications / About | Existing interfaces, returning to Lobby. |
| Logs | Same journal and log controls in the separate fullscreen Logs window. |

**Home > More > Logs** also opens Logs directly. Logs is removed from the Settings wheel and search catalogue. Live/pause, severity filtering, timestamps, description, outcome, export, confirmed clearing and reading-position preservation remain available. Closing Logs reveals the previous Home or Lobby page. Export writes `exports/logs.csv` and `exports/logs.md`.

Settings history entries are actionable: selecting one copies it into the search bar and immediately performs the search.

## Screen captures and shortcuts

Captures are saved as **`phototype_YYYYMMDD_HHMMSS_microseconds.png`** under `data/screenshots/` (under the selected data directory when using `--data-dir`). Choose **Screenshot** in Lobby > Buttons Panel to assign it to either side's shortcut button. Existing shortcut actions plus Open Lobby and Open Logs are also available. Knob navigation can adjust the shortcut choice and log filter.

On a multi-monitor desktop, capture covers the application's current display. Windows/X11 uses root-screen capture; Wayland uses the compositor through grim. Failures produce a visible message rather than saving a window-only substitute.

## Existing 3D assembly viewer

The DLC tile launches the separately installed [HMI-3D-RPi viewer](../../HMI-3D-RPi/README.md) fullscreen, using its own Python environment and OpenGL backend. It does not re-tessellate the STEP model or change the HMI rendering backend.

On this workstation the viewer is already at `Nexatom/HMI-3D-RPi`. On the Pi, install it as `~/HMI-3D-RPi`, beside `~/nexatom`, and run its own installer. Alternatively set `NEXATOM_VIEWER_DIR` to its project directory. The viewer and its Qt Quick 3D dependencies are separate from this HMI package.

## Validation

Verified on Windows with isolated test data: native Lobby navigation; packed grid with no overlaps or unfilled cells; zero tile radii; original v1.9 wheel source comparison; real mouse/touch reorder; shortcut persistence and knob selection; full-display PNG capture from Lobby and a shortcut; Settings history; fullscreen Logs controls and scrolling. No QML warnings were emitted by the navigation check.

Additional checks cover 54 unit tests, 21 baseline regressions, 54 chart checks and nine touch/pinch paths. The normal fullscreen launcher is checked after boot. See [VALIDATION.json](VALIDATION.json), [native navigation results](tests/lobby/results.json) and [release notes](RELEASE.md).

Run GUI checks serially from this folder:

```powershell
.\runtime\python.exe -m unittest discover -s tests -p "test_*.py"
.\runtime\python.exe tests/verify_lobby.py --native
.\runtime\python.exe tests/fixes.py
.\runtime\python.exe tests/verify_charts.py
.\runtime\python.exe tests/verify_zoom_paths.py
```

Older historical UI scripts remain as reference and may assert superseded layouts/version numbers. `verify_lobby.py` covers the new More/Lobby/Logs flow. Laser traces remain simulated, as in the base release. Physical CM5 GPIO, capture and rendering acceptance still need to be performed on the target device.
