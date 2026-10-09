# Nexatom v1.12

Restored sector wheel, GPIO recovery and notification blur/stacking.

Originally delivered **03 October 2026, 13:40 IST** as an in-place v1.8 build.
Recovered and renumbered on 5 October 2026.

## Run

- Windows: double-click **[start.cmd](start.cmd)**. Bundled Python and Qt are included.
- Raspberry Pi OS: copy this entire folder, then run **`bash start.sh`** on the Pi desktop.
- [Application documentation](README.md) · [Historical README](ORIGINAL.md) · [All releases](../README.md).

## Changes in this release

- Restored the earlier black four-sector More fan, with 800 ms expansion/contraction and a 16 px downward offset.
- Added GPIO automatic retries and isolated busy/unavailable pins so they do not disable all controls.
- Added newest-first notification stacking, independent timers and 650 ms blur/fade expiry; manual close remains immediate.
- Preserved pending consent and kept routine cards underneath active editors/dropdowns.
- This release still permits up to four visible notifications; the two-card limit arrives in v1.14.

## Historical scope

This preserves the behavior of this checkpoint, including limitations later corrected.
Only application version labels and launch aliases were adjusted for the new numbering.
About firmware remains V1.6.0 as originally requested. GPIO and host controls are real;
laser traces remain simulated. Physical Pi hardware was not retested during recovery.

The source change inventory and original file hashes are in [RELEASE.json](RELEASE.json).
A local Git tag, **recovered-v1.12**, preserves this completed recovery.

## Files changed from the preceding release

**Added**

`interaction/notification_art.py`, `tests/test_gpio_recovery.py`, `tests/test_notifications.py`, `tests/verify_interaction_update.py`.

**Modified**

`README.md`, `hardware/gpio.py`, `hardware/service.py`, `interaction/notifications.py`, `main.py`, `qml/NotificationToast.qml`, `qml/RadialMenu.qml`, `settings_ui/control_panel.py`, `settings_ui/extended_controls.py`, `settings_ui/help_content.py`, `settings_ui/tour.py`, `tests/test_gpio_adapter.py`, `tests/verify_control_update.py`, `tests/verify_refinements.py`, `tests/verify_v18.py`.

## Recovery verification

42 unit tests and 20 UI checks passed. The actual Windows `start.cmd`
completed fullscreen boot and live acquisition. Python compilation and Bash syntax
passed. All retained dependencies/assets and recovered source text were verified.

[Verification summary](VALIDATION.json). Physical Raspberry Pi hardware was not tested.
