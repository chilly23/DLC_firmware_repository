# Nexatom v1.5

Run **Start Nexatom v1.5.cmd** (windowed) or **Start Fullscreen v1.5.cmd**.
Windows Python/Qt are included. This folder is the working source for the next
version; v1.4 is untouched. No archives are needed.

## New chart controls

- Hold a split graph for 550 ms, then drag to the other vertical slot to exchange
  spectroscopy and error for that laser. Release in the original slot to cancel.
- Crossing the centre divider changes the preview to the whole laser pair.
  Dropping in the other half swaps the two channel assignments, including each
  laser's chart configuration. Returning to the original half restores local drag.
- Release outside the chart region to cancel. Graph lock blocks drag; a locked
  destination also rejects a channel drop.
- Tap the spectroscopy/error label area on either side, or **More → Signals**.
  The panel opens opposite the chosen chart so its live preview remains visible.
  Fullscreen labels open the same controls.
- **Combined** overlays both signals. Each has its own visibility toggle. With
  both visible, the left Y axis is spectroscopy and the right Y axis is error.
  **Split** shows both graphs, with complementary Upper/Lower choices. Switching
  tabs applies immediately; closing does not undo it.
- **Y axis** slides in from the right. Main/Error select the signal. V/div sets
  each of four vertical divisions; Position is the voltage at the graph centre.
  Use +/− or tap a number for the existing numpad. Input ranges are 0.01–100 V/div
  and −1000–1000 V; invalid input leaves the previous value intact.
- The slider sets spectroscopy:error height between 20:80 and 80:20, updating
  split graphs during the drag. In combined mode it stores the next split ratio.
  **Restore defaults** resets both Y axes and the ratio, preserving mode, order,
  visibility, acquisition state, and the X range.

Chart configuration belongs to the laser, not its screen half. Laser 1 changes
do not change Laser 2. If both halves display Laser 1, both show Laser 1's state.
Chart configuration lasts for this app session. Signals remain the v1.4 visual
simulation, without hardware I/O.

## Useful files for v1.6

| File | Responsibility |
|---|---|
| `controller/charts.py` | Chart state, axis defaults, numeric validation |
| `controller/bridge.py` | Chart commands and shared channel state |
| `controller/plot.py` | Split/combined drawing, independent Y scales, shared X labels |
| `qml/ChartPair.qml` | Plot ordering, height ratio, legend touch target |
| `qml/GraphDrag.qml` | Local versus whole-channel drag preview and drop rules |
| `qml/SignalsPanel.qml` | Signals panel, sliding axis page, live controls |
| `qml/ChoiceButton.qml` | Shared neutral option button |
| `qml/NumberPad.qml` | Existing editor, now also accepts chart parameters |

Run `runtime\python.exe tests\verify_v15.py` for the new behavior checks.
`tests\verify_base.py` checks preserved v1.4 behavior; `tests\verify_desktop.py`
checks both Windows launchers. Test screenshots and results are under `tests`.
On a provisioned Pi/Yocto graphical session use `python3 main.py`; Raspberry Pi
OS setup remains `bash run.sh`. The Windows runtime does not run on ARM Linux.
