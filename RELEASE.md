# Nexatom v1.13

Logs, trace styles, lock controls, startup installer and error reports.

Originally delivered **03 October 2026, 14:36 IST** as an in-place v1.8 build.
Recovered and renumbered on 5 October 2026.

## Run

- Windows: double-click **[start.cmd](start.cmd)**. Bundled Python and Qt are included.
- Raspberry Pi OS: copy this entire folder, then run **`bash start.sh`** on the Pi desktop.
- [Application documentation](README.md) · [Historical README](ORIGINAL.md) · [All releases](../README.md).

## Changes in this release

- Added manual lock settings and hold-to-unlock while keeping GPIO20 authoritative.
- Added independent main/error trace colours, widths and stroke styles for each laser.
- Replaced Display in More with persistent user Logs: timestamp, description, outcome, level, pause, scroll, export and confirmed clear.
- Changed knob More routing: repeated push closes it; rotation/joystick navigate, with left/right opening the highlighted option.
- Preserved live chart/theme/fullscreen state through the guide; adjusted axis corner spacing.
- Added Small/Medium/Large notifications, neutral grip sliders, keyboard press feedback and retry icons.
- Added short launchers, one-click Pi dependency/setup installer, desktop autostart controls and local error reports.
- Originally delivered as Nexatom/app rather than another versioned folder.

## Historical scope

This preserves the behavior of this checkpoint, including limitations later corrected.
Only application version labels and launch aliases were adjusted for the new numbering.
About firmware remains V1.6.0 as originally requested. GPIO and host controls are real;
laser traces remain simulated. Physical Pi hardware was not retested during recovery.

The source change inventory and original file hashes are in [RELEASE.json](RELEASE.json).
A local Git tag, **recovered-v1.13**, preserves this completed recovery.

## Files changed from the preceding release

**Added**

`boot.py`, `install.py`, `interaction/faults.py`, `interaction/journal.py`, `launch.py`, `settings_ui/console.py`, `setup.sh`, `start.cmd`, `start.desktop`, `start.sh`, `startup.py`, `tests/console.py`, `tests/regress.py`, `tests/test_console.py`.

**Modified**

`README.md`, `controller/bridge.py`, `controller/plot.py`, `hardware/gpio.py`, `interaction/icons.py`, `interaction/notification_art.py`, `interaction/notifications.py`, `interaction/router.py`, `interaction/session_lock.py`, `main.py`, `qml/ChartPair.qml`, `qml/Icon.qml`, `qml/Main.qml`, `qml/NotificationToast.qml`, `qml/RadialMenu.qml`, `qml/ReferenceSlider.qml`, `qml/SignalsPanel.qml`, `settings_ui/controls.py`, `settings_ui/coordinator.py`, `settings_ui/drawing.py`, `settings_ui/extended_controls.py`, `settings_ui/help_content.py`, `settings_ui/integration.py`, `settings_ui/keyboard.py`, `settings_ui/model.py`, `settings_ui/operational.py`, `settings_ui/preferences.py`, `settings_ui/refined.py`, `settings_ui/tooltips.py`, `settings_ui/tour.py`, `tests/verify_charts.py`, `tests/verify_control_update.py`, `tests/verify_desktop.py`.

**Removed**

`Start Fullscreen v1.8.cmd`, `Start Nexatom v1.8.cmd`, `desktop_launcher.py`, `install_pi_shortcut.py`, `previews/README.md`, `previews/index.html`, `run.sh`, `setup_pi.sh`.

## Recovery verification

48 unit tests and 37 UI checks passed. The actual Windows `start.cmd`
completed fullscreen boot and live acquisition. Python compilation and Bash syntax
passed. All retained dependencies/assets and recovered source text were verified.

[Verification summary](VALIDATION.json). Physical Raspberry Pi hardware was not tested.
