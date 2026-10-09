# Nexatom v1.14

Mirrored layout, two notifications, GPIO recovery and emission-off guards.

Originally delivered **05 October 2026, 13:45 IST** as an in-place v1.8 build.
Recovered and renumbered on 5 October 2026.

## Run

- Windows: double-click **[start.cmd](start.cmd)**. Bundled Python and Qt are included.
- Raspberry Pi OS: copy this entire folder, then run **`bash start.sh`** on the Pi desktop.
- [Application documentation](README.md) · [Historical README](ORIGINAL.md) · [All releases](../README.md).

## Changes in this release

- Mirrored side-button spacing, header controls, corner selectors, chart labels and graph-drop placeholders.
- Moved right-side Y-axis readings to the outer right edge.
- Restored the actual v1.6 sector geometry/animation, aligned with the More button.
- Limited visible notifications to two, including fading cards; kept full action history.
- Made Settings open directly without hiding/recreating Home and gave Signals neutral controls.
- Blocked Lock and Stabilise while emission is off, including controller and knob commands.
- Separated encoder edge capture from polled switch contacts; isolated GPIO request failures and shortened operator-facing errors.
- Originally delivered as Nexatom/fixed; its source now matches the surviving Nexatom/app.

## Historical scope

This preserves the behavior of this checkpoint, including limitations later corrected.
Only application version labels and launch aliases were adjusted for the new numbering.
About firmware remains V1.6.0 as originally requested. GPIO and host controls are real;
laser traces remain simulated. Physical Pi hardware was not retested during recovery.

The source change inventory and original file hashes are in [RELEASE.json](RELEASE.json).
A local Git tag, **recovered-v1.14**, preserves this completed recovery.

## Files changed from the preceding release

**Added**

`tests/fixes.py`, `tests/handoff.py`, `tests/test_inputs.py`.

**Modified**

`README.md`, `controller/bridge.py`, `controller/plot.py`, `hardware/gpio.py`, `interaction/notifications.py`, `qml/ChannelPane.qml`, `qml/ChartPair.qml`, `qml/ChoiceButton.qml`, `qml/GraphDrag.qml`, `qml/Main.qml`, `qml/ParameterTile.qml`, `qml/PlotView.qml`, `qml/RadialMenu.qml`, `qml/SignalsPanel.qml`, `qml/ToggleChoice.qml`, `qml/TouchButton.qml`, `settings_ui/control_panel.py`, `settings_ui/integration.py`, `start.sh`, `tests/console.py`, `tests/test_gpio_adapter.py`, `tests/test_gpio_recovery.py`, `tests/test_notifications.py`, `tests/verify_control_update.py`, `tests/verify_interaction_update.py`.

## Recovery verification

54 unit tests and 75 UI checks passed. The actual Windows `start.cmd`
completed fullscreen boot and live acquisition. Python compilation and Bash syntax
passed. All retained dependencies/assets and recovered source text were verified.

[Verification summary](VALIDATION.json). Physical Raspberry Pi hardware was not tested.
