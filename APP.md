# Nexatom v1.17 — input reliability and graph performance

Version **1.17.0**, based exclusively on completed **v1.16.0**. The normal application remains the 1600 × 720 touch HMI with the same Home, Lobby, More wheel and settings. Earlier version folders are preserved.

## Run

| Platform / purpose | Entry point |
|---|---|
| Windows, normal application | Double-click **[start.cmd](start.cmd)**. Bundled Python, Qt and NumPy are included. |
| Raspberry Pi OS 64-bit desktop | Run **`bash start.sh`** from this folder in the graphical desktop. |
| Windowed development | `start.cmd --windowed` or `bash start.sh --windowed` |
| Windows, isolated benchmark | Double-click **[bench.cmd](bench.cmd)**. |
| Pi, isolated benchmark | `bash bench.sh` after installing normal OS dependencies. |
| Pi, physical input measurements | Close the normal application, then `bash bench.sh --benchmark-hardware`. |

The inherited Pi launcher stages the app at `~/nexatom`, preserves installed preferences/calibration, installs dependencies and registers desktop startup. First-time OS provisioning can request authentication/reboot. The dependency check now includes NumPy. Run as the normal desktop user, not root. An SSH shell alone does not provide a graphical display.

Normal startup retains the three-second boot and fullscreen Home. Windows has no GPIO device; touch and simulated graphs remain available. Synthetic benchmark mode never requests GPIO. The physical benchmark uses separate preferences/calibration.

## What changed

- GPIO requests, reads, edge decoding, configuration and cleanup have one owner in an isolated process. The GUI cannot call the driver.
- Kernel-buffered edge events replace normal contact polling. Capture timestamps survive batching and a busy GUI.
- Ordered delivery retains press/release transitions and signed encoder steps. Commands have IDs, one in-flight driver operation and matched acknowledgements.
- Partial failure releases/retries only the affected control. Healthy requests remain owned. Unexpected owner exit can recover without restarting the application.
- Three reproduced v1.16 gesture bugs are fixed: delayed long presses, repeated panel presses in one batch, and a standalone push followed by a separate tilt.
- Every numeric delta updates the model. Redundant presentation updates are combined, hidden parameter pages are not rebuilt for every pulse, and stable scene lookups are cached.
- A single background SQLite writer removes disk waits from the knob handler. Logs remain immediately visible and normal exit flushes queued writes.
- Simulation math is vectorized. Plot drawing preserves each horizontal bucket's extrema while all acquisition samples remain available to processing/exports.
- Smaller Home plot padding and central/split gaps make the graphs larger. Mirrored axes and existing gestures remain.
- An isolated benchmark offers a **100–10,000 point slider**, optional all-point raster stress, synthetic input, owner probes and JSON measurements.

Lobby and More wheel QML are byte-identical to v1.16. No USB update, Yocto packaging or new laser hardware protocol is included. Traces/readbacks remain the existing simulation. The About firmware identifier remains **V1.6.0**.

## Retained application flow

Home → More → Lobby retains twenty cards: Control Parameters, Laser Config, Sub Parameters, Home Controls, Buttons Panel, Diagnostics, System Monitoring, Screenshot, File Manager, Graph Size, Logs, Notifications, Display Settings, System, Signals, Help, About, DLC View, Legal Info and Digital Manual.

CC/TC/PC edits share validation and the existing numpad. Home assignments and accepted setpoints persist in `control_state`. Emission confirmation, lock/stabilisation, graph drag/swap, pan/zoom, combined/split signals and per-signal axes remain available. DLC, Legal and Digital Manual retain their intentional placeholders.

Screenshots are timestamped full-display PNGs in `data/screenshots`. File Manager browses screenshots, recordings, logs and exports. Logs remains fullscreen with filter, pause/live, clear and export. Notification appearance, deduplication, two-card limit and countdown rings are retained. Storage failures are reported; unsaved logs remain exportable from memory while the application is open.

## Code structure

```text
main.py                   Composition, startup and shutdown
hardware/
  capture.py              Single-owner libgpiod reactor (child process, no Qt)
  discovery.py            Chip identification and concise errors
  decoder.py, panel.py    Electrical decoding and capture-time debounce
  events.py               Timestamp ordering and intermediate contact states
  gpio.py                 IPC bridge, command serialization, GUI scheduling
  mailbox.py              Explicit input FIFO and ACK completion lane
  metrics.py              Bounded, synchronized latency measurements
  service.py              Calibration, release-to-arm, semantic commands
  replay.py               Benchmark-only synthetic electrical source
  config.py               Existing validated wiring and mappings
interaction/
  router.py               Semantic commands to existing UI/model operations
  journal.py              Immediate bounded log view and export API
  journal_io.py           Dedicated serialized SQLite writer
  workspace.py            Existing Lobby services; adjusted graph geometry
controller/
  bridge.py               Shared validated model and timed acquisition steps
  simulation.py           Vectorized simulated traces
  plot.py                 Measured rendering, extrema reduction and gestures
  parameters.py           Persistence and visible-page updates
benchmark.py              Isolated profile, controls and measurement export
qml/, settings_ui/        Existing application UI
tests/                    Unit, lifecycle, native UI and stress verification
```

Normal state remains in `data/settings.json`, `controls.json`, `events.db` and `notifications.json`. Diagnostics are in `logs/` (or the selected `--data-dir`). Benchmark profiles are separate: `benchmark/replay/data`, `benchmark/hardware/data`; exports go to `benchmark/reports`.

## Engineering evidence

- [Architecture, root causes and policies](HARDWARE.md)
- [Benchmark procedure and measurements](BENCHMARK.md)
- [Release notes](RELEASE.md)
- [Current validation manifest](VALIDATION.json)
- [Source comparison against v1.16](RELEASE.json)

Built and run on Windows with actual Qt rendering, process/IPC stress and injected driver faults. **Physical Pi timing and electrical acceptance still require the target device.** Finite buffers and Linux userspace are not a hard-realtime guarantee. Overflow is detected and reported, never converted into invented steps.

Run GUI suites sequentially:

```powershell
.\runtime\python.exe -m unittest discover -s tests -p "test_*.py"
.\runtime\python.exe tests/verify_release.py --native
.\runtime\python.exe tests/verify_charts.py
.\runtime\python.exe tests/verify_zoom_paths.py
.\runtime\python.exe tests/fixes.py
.\runtime\python.exe tests/verify_benchmark.py
.\runtime\python.exe tests/stress.py --native --seconds 60
```

Create a new folder for subsequent versions. Source checkpoint/tag: `v1.17.0`. Bundled runtimes and generated runtime state are excluded from Git but remain in the runnable folder.
