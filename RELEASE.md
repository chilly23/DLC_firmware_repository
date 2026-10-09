# Nexatom v1.9

Corner colours, original green, zoom, shared-contact calibration and Knob 4.

Originally delivered **30 September 2026, 17:07 IST** as an in-place v1.8 build.
Recovered and renumbered on 5 October 2026.

## Run

- Windows: double-click **[start.cmd](start.cmd)**. Bundled Python and Qt are included.
- Raspberry Pi OS: copy this entire folder, then run **`bash start.sh`** on the Pi desktop.
- [Application documentation](README.md) · [Historical README](ORIGINAL.md) · [All releases](../README.md).

## Changes in this release

- Made all four corner foregrounds consistent: values, labels, units, dividers and icons.
- Restored Green to #008622 and retained contrast adaptation for pale accents.
- Added one pinch handler across both plots; second-finger pinch can take over a held graph drag.
- Calibration learns centre push first, accepts direction plus shared push, and suppresses accidental push actions during a tilt.
- Disabled Knob 3 and migrated its stock wiring/mappings to Knob 4 at the bottom right; replacement calibration resets.

## Historical scope

This preserves the behavior of this checkpoint, including limitations later corrected.
Only application version labels and launch aliases were adjusted for the new numbering.
About firmware remains V1.6.0 as originally requested. GPIO and host controls are real;
laser traces remain simulated. Physical Pi hardware was not retested during recovery.

The source change inventory and original file hashes are in [RELEASE.json](RELEASE.json).
A local Git tag, **recovered-v1.9**, preserves this completed recovery.

## Files changed from the preceding release

**Added**

`tests/test_shared_contact.py`, `tests/test_wiring_migration.py`, `tests/verify_zoom_paths.py`.

**Modified**

`README.md`, `data/controls.json`, `hardware/calibration.py`, `hardware/config.py`, `hardware/service.py`, `qml/ChartPair.qml`, `qml/ParameterTile.qml`, `qml/PlotView.qml`, `settings_ui/control_panel.py`, `settings_ui/help_content.py`, `settings_ui/preferences.py`, `settings_ui/tour.py`, `tests/test_gpio_adapter.py`, `tests/test_knobs.py`, `tests/verify_v18.py`.

## Recovery verification

24 unit tests and 55 UI checks passed. The actual Windows `start.cmd`
completed fullscreen boot and live acquisition. Python compilation and Bash syntax
passed. All retained dependencies/assets and recovered source text were verified.

[Verification summary](VALIDATION.json). Physical Raspberry Pi hardware was not tested.
