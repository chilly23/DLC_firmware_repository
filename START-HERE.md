# NEXATOM v1.4

Double-click **Start Nexatom v1.4.cmd** for the 1600 × 720 window, or
**Start Fullscreen v1.4.cmd** for the touch display. Windows Python and Qt are included;
no installation is needed. Extract the entire ZIP before launching.

The original v1.2 folder is unchanged.

The three side buttons, from top to bottom:

1. **Graph lock:** white fill and a closed padlock mean pan, zoom, peak selection,
   reset and graph drag are blocked. The live trace continues updating.
2. **Emission:** white fill means on. Turning it on raises both signals smoothly;
   turning it off lowers them to zero. The zero lines remain visible.
3. **Stabilise:** white fill means live noise filtering is on. Turn it off to see
   the unfiltered signal again.

Tap a green value to edit it. Tap its module icon for TC / CC / PC selection.
Hold an unlocked graph to move the channel, or pinch/drag to zoom/pan.
The switch icon changes only that pane's channel; fullscreen works for either pane.

**More → Settings** opens the attached Frame 58 wheel. Search accepts native typing
and the touch keyboard. The adjacent notepad opens recent search history; **Clear**
erases that history. Tap outside a popup to dismiss it.

Signals are local visual simulations, as requested. This release does not send
commands to laser hardware. The two channels deliberately have different peak
positions, heights and widths.

Linux / Raspberry Pi details and the source structure are in [README.md](README.md).
