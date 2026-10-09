# Nexatom v1.8

First delivered RKJXT v1.8.

Originally delivered **30 September 2026, 16:31 IST** as an in-place v1.8 build.
Recovered and renumbered on 5 October 2026.

## Run

- Windows: double-click **[start.cmd](start.cmd)**. Bundled Python and Qt are included.
- Raspberry Pi OS: copy this entire folder, then run **`bash start.sh`** on the Pi desktop.
- [Application documentation](README.md) · [Historical README](ORIGINAL.md) · [All releases](../README.md).

## Changes in this release

- First RKJXT integration: independent hardware decoding, configurable commands and digit editing.
- Knob direction/push calibration, screen touch diagnostics and expanded guide/tooltips.
- White large numeric values, restored CC/TC/PC selectors, graph gesture/display detection changes.
- Knobs 1, 2 and 3 enabled; Knob 4 disconnected. This is the first delivery, before the reported corrections.

## Historical scope

This preserves the behavior of this checkpoint, including limitations later corrected.
Only application version labels and launch aliases were adjusted for the new numbering.
About firmware remains V1.6.0 as originally requested. GPIO and host controls are real;
laser traces remain simulated. Physical Pi hardware was not retested during recovery.

The source change inventory and original file hashes are in [RELEASE.json](RELEASE.json).
A local Git tag, **recovered-v1.8**, preserves this completed recovery.

## Recovery verification

18 unit tests and 41 UI checks passed. The actual Windows `start.cmd`
completed fullscreen boot and live acquisition. Python compilation and Bash syntax
passed. All retained dependencies/assets and recovered source text were verified.

[Verification summary](VALIDATION.json). Physical Raspberry Pi hardware was not tested.
