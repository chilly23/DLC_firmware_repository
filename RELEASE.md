# Nexatom v1.10

Full knob-step delivery, quarter wheel, themes, physical controls, lock and notifications.

Originally delivered **01 October 2026, 14:46 IST** as an in-place v1.8 build.
Recovered and renumbered on 5 October 2026.

## Run

- Windows: double-click **[start.cmd](start.cmd)**. Bundled Python and Qt are included.
- Raspberry Pi OS: copy this entire folder, then run **`bash start.sh`** on the Pi desktop.
- [Application documentation](README.md) · [Historical README](ORIGINAL.md) · [All releases](../README.md).

## Changes in this release

- Removed the 24-step rotation cap and retained complete decoded batches; added diagnostic counters.
- Added side-specific navigation and fixed the right-edge button clipping.
- Introduced a rotating quarter-ring More menu, fixed filled highlight, upright icons and caption card.
- Added six theme presets and a screenshot gallery, independent corner number/detail colours, and noisier independent signals.
- Added slide-to-confirm emission and physical-button confirmation.
- Added GPIO20 interface lock, blurred screen and configurable real shutdown countdown.
- Added physical button/lock calibration, compact notifications, consent and persistent notification history.
- Button 4 was disabled because GPIO8 conflicted with Knob 2; the next release resolves this.

## Historical scope

This preserves the behavior of this checkpoint, including limitations later corrected.
Only application version labels and launch aliases were adjusted for the new numbering.
About firmware remains V1.6.0 as originally requested. GPIO and host controls are real;
laser traces remain simulated. Physical Pi hardware was not retested during recovery.

The source change inventory and original file hashes are in [RELEASE.json](RELEASE.json).
A local Git tag, **recovered-v1.10**, preserves this completed recovery.

## Files changed from the preceding release

**Added**

`hardware/panel.py`, `interaction/notifications.py`, `interaction/session_lock.py`, `previews/README.md`, `previews/index.html`, `qml/EmissionConfirm.qml`, `qml/NotificationToast.qml`, `settings_ui/extended_controls.py`, `tests/test_panel_inputs.py`, `tests/test_step_delivery.py`, `tests/verify_control_update.py`.

**Modified**

`README.md`, `controller/bridge.py`, `controller/plot.py`, `controller/simulation.py`, `data/controls.json`, `hardware/config.py`, `hardware/gpio.py`, `hardware/service.py`, `interaction/icons.py`, `interaction/router.py`, `main.py`, `qml/ChannelPane.qml`, `qml/GraphDrag.qml`, `qml/Icon.qml`, `qml/Main.qml`, `qml/NumberPad.qml`, `qml/ParameterTile.qml`, `qml/RadialMenu.qml`, `qml/SignalsPanel.qml`, `settings_ui/control_panel.py`, `settings_ui/coordinator.py`, `settings_ui/drawing.py`, `settings_ui/help_content.py`, `settings_ui/integration.py`, `settings_ui/model.py`, `settings_ui/preferences.py`, `settings_ui/tooltips.py`, `settings_ui/tour.py`, `tests/test_gpio_adapter.py`, `tests/verify_v18.py`.

## Recovery verification

31 unit tests and 33 UI checks passed. The actual Windows `start.cmd`
completed fullscreen boot and live acquisition. Python compilation and Bash syntax
passed. All retained dependencies/assets and recovered source text were verified.

The original animation test passed unchanged when run serially; its first
parallel run missed its fixed animation deadline. Run GUI checks serially.

[Verification summary](VALIDATION.json). Physical Raspberry Pi hardware was not tested.
