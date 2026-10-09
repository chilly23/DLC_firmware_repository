# Nexatom v1.11

Right shortcut GPIO7 and left shortcut GPIO16.

Originally delivered **01 October 2026, 15:24 IST** as an in-place v1.8 build.
Recovered and renumbered on 5 October 2026.

## Run

- Windows: double-click **[start.cmd](start.cmd)**. Bundled Python and Qt are included.
- Raspberry Pi OS: copy this entire folder, then run **`bash start.sh`** on the Pi desktop.
- [Application documentation](README.md) · [Historical README](ORIGINAL.md) · [All releases](../README.md).

## Changes in this release

- Kept right shortcut Button 3 on GPIO7; assigned and enabled left shortcut Button 4 on GPIO16.
- Added wiring revision 3 migration while preserving custom pin maps and saved calibration.
- Updated help, tour, wiring instructions and migration tests; GPIO8 remains Knob 2 D.

## Historical scope

This preserves the behavior of this checkpoint, including limitations later corrected.
Only application version labels and launch aliases were adjusted for the new numbering.
About firmware remains V1.6.0 as originally requested. GPIO and host controls are real;
laser traces remain simulated. Physical Pi hardware was not retested during recovery.

The source change inventory and original file hashes are in [RELEASE.json](RELEASE.json).
A local Git tag, **recovered-v1.11**, preserves this completed recovery.

## Files changed from the preceding release

**Modified**

`README.md`, `data/controls.json`, `hardware/config.py`, `hardware/panel.py`, `settings_ui/help_content.py`, `settings_ui/tour.py`, `tests/test_gpio_adapter.py`, `tests/test_panel_inputs.py`, `tests/test_wiring_migration.py`.

## Recovery verification

33 unit tests and 33 UI checks passed. The actual Windows `start.cmd`
completed fullscreen boot and live acquisition. Python compilation and Bash syntax
passed. All retained dependencies/assets and recovered source text were verified.

The original animation test passed unchanged when run serially; its first
parallel run missed its fixed animation deadline. Run GUI checks serially.

[Verification summary](VALIDATION.json). Physical Raspberry Pi hardware was not tested.
