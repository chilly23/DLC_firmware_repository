"""Operator help is displayed as documents inside the right panel."""
TOPICS={
 'Knob controls':[
 ('Physical layout','Knob 1 is top left, Knob 2 bottom left and Knob 4 bottom right. Knob 3 at the top right is not connected. Control Settings shows the live stick, centre press and encoder orientation.'),
 ('Calibrate before use','Open Control Settings, Configure, then Calibrate directions and push. Capture the released state. Press the centre without tilting first, then move Up, Right, Down and Left, releasing completely after each movement. A direction may also close the centre contact; this is supported. Check both encoder directions and Save. Cancel keeps the previous calibration.'),
 ('Assign shortcuts','Choose the target corner and an action for clockwise, anticlockwise, four directions and a short push. Parameter actions follow the laser and module displayed in that corner. Changes are saved immediately.'),
 ('Select a digit','The top knobs initially use left/right to move the selected digit, rotation to increase/decrease it, and push to toggle graph lock. An underline identifies the digit. Parameter limits always apply.'),
 ('Navigation mode','Hold a calibrated knob push for 700 ms. Rotation moves focus; push or stick right activates; stick left goes back. Hold push again to restore assigned shortcuts. On a slider, push to adjust, rotate, then push to finish. In Settings, focus the wheel or scroll rail and push before rotating it.'),
 ('Reset and reconnect','Reset calibration preserves shortcuts and wiring. Restore shortcut defaults preserves calibration. Retry GPIO opens the configured lines again. Close the standalone RKJXT demo: two programs cannot own the same GPIO lines.'),
 ('Screen check','Test corner taps, trace an outline continuously, drag between targets, then inspect solid colors. Skipped tests remain not completed. This is a touch and visual inspection tool, not an automatic crack detector.')],
 'Graphs':[
 ('Spectroscopy','The solid trace shows the selected laser’s spectroscopy signal. Peaks identify resonances in the current scan. These traces are generated locally in this version; they are not ADC measurements.'),
 ('Error signal','The dashed trace shows the associated dispersive error signal. It shares the spectroscopy X coordinates. In Split mode, only the bottom chart labels the X axis.'),
 ('Pan and zoom','Drag briefly to pan. Pinch to zoom horizontally; a mouse wheel works on a desktop. Double-tap to restore the view. Bounds keep acquired data in view.'),
 ('Rearrange','Hold a graph for 550 ms. Drag up or down within the same half to swap the two plots. Cross the center to move the entire laser panel. Release outside the chart area to cancel.'),
 ('Graph lock','The padlock blocks pan, zoom, reset, peak selection and graph dragging. It does not stop acquisition or prevent numeric edits.'),
 ('Fullscreen','Use the square icon beside a laser heading. Exit fullscreen returns to the two-panel home screen with the updated viewing range.')],
 'Analysis':[
 ('Combined and Split','Tap the Spectroscopy / Error label area to open Signals. Combined overlays the traces and provides visibility switches. Split assigns each signal to an upper or lower slot.'),
 ('Y axes','Open Y axis to set V/div and center position for Main or Error. Changes apply immediately. The height slider changes the split ratio from 20:80 to 80:20.'),
 ('Baseline calibration','In Function settings select a laser, then Calibrate baseline with emission on. The median of each current raw signal becomes its zero reference. Reset baseline removes the offsets.'),
 ('Bandwidth','Auto bandwidth applies a temporal low-pass stage using a cutoff derived from the sampling rate. Stabilise is a separate smoothing control. Both alter live signal samples.'),
 ('Sampling and points','Sampling rate controls sample-buffer updates per second, not the monitor refresh rate. Maximum points changes the number of values in each graph frame.')],
 'Parameters':[
 ('Module selection','Tap TC, CC or PC on a green parameter tile to select its module and field. Tap the field label to change the displayed parameter within that module.'),
 ('Edit a value','Tap the large number. Enter a value and press Return to apply. Invalid values remain in the editor. The red X or outside tap cancels the draft.'),
 ('Editing shortcuts','Use caret arrows to insert at a position. The minus key toggles sign. Hold backspace for 650 ms to clear the entire entry. A short tap deletes one character.'),
 ('Channel ownership','Values and chart configuration belong to a laser, not to a screen half. Both halves can show Laser 1; editing either view updates that same laser.'),
 ('Emission','The second side button toggles emission. Traces rise smoothly from zero and return to zero when off. The channel dims while idle; its emission and parameter controls stay accessible.')],
 'System':[
 ('Display controls','Brightness and contrast send commands to the actual display driver or monitor. If the monitor does not support a control, its reason is shown. No dimming overlay substitutes for hardware brightness.'),
 ('Resolution and refresh','Choose a mode reported by the host. Keep it within 15 seconds or the previous mode is restored. Refresh rate here is the physical display frequency.'),
 ('Appearance','Accent changes the parameter tiles. Light/Dark changes the interface palette. UI scale changes control density; font family and text size apply across the application.'),
 ('Clock and power','Date and time edits are sent to the host and may require permission. Automatic sleep/shutdown watches inactivity in this app and shows a cancellable countdown first.'),
 ('Restore','Restore defaults resets application preferences and graph settings. Factory reset also clears search history and resets this application’s laser session; it never reflashes the device.')],
 'Storage':[
 ('Local data','Storage shows actual disk usage for the application data location. Preferences and recent searches are saved there in settings.json.'),
 ('Export settings','Export writes the current settings and graph preferences as JSON in the application exports folder.'),
 ('Export graph frame','Capture frame writes the current X, spectroscopy and error samples for both lasers to CSV. This is a snapshot, not continuous data logging.'),
 ('Search history','The history button beside Search shows the eight most recent non-empty queries. Queries are saved on Return or dismissal. Clear removes the persisted list.'),
 ('Version scope','Application v1.9 adds real GPIO knob controls. Upgrade remains a preview; laser signals remain simulated. Firmware V1.6.0 is the requested About identifier, independent of application version 1.9.0.')]
}
