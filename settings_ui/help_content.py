"""Operator help is displayed as documents inside the right panel."""
TOPICS={
 'Knob controls':[
 ('Physical layout','Knob 1 is top left, Knob 2 bottom left and Knob 4 bottom right. Knob 3 at the top right is not connected. Control Settings shows the live stick, centre press and encoder orientation.'),
 ('Calibrate before use','Open Control Settings, Configure, then Calibrate directions and push. Capture the released state. Press the centre without tilting first, then move Up, Right, Down and Left, releasing completely after each movement. A direction may also close the centre contact; this is supported. Check both encoder directions and Save. Cancel keeps the previous calibration.'),
 ('Assign shortcuts','Choose the target corner and an action for clockwise, anticlockwise, four directions and a short push. Parameter actions follow the laser and module displayed in that corner. Changes are saved immediately.'),
 ('Select a digit','Knob 1 and Knob 4 initially use left/right to move the selected digit, rotation to increase/decrease it, and push to toggle graph lock. An underline identifies the digit. Parameter limits always apply.'),
 ('Navigation mode','Hold a calibrated knob push for 700 ms. Rotation moves focus; push or stick right activates; stick left goes back. Home focus stays on the physical side of the knob. An open side-owned panel accepts that side only. Shared Settings accepts either side. More uses direct rotation even outside navigation mode. Hold push again to restore assigned shortcuts. On a slider, push to adjust, rotate, then push to finish. In Settings, focus the wheel or scroll rail and push before rotating it.'),
 ('Reset and reconnect','Reset calibration preserves shortcuts and wiring. Restore shortcut defaults preserves calibration. Failed GPIO connections retry automatically. A busy pin blocks only its knob or button; unaffected controls stay live. The status names the pin and owner. Close the standalone RKJXT demo if it owns those pins. Released pins are detected automatically; Retry GPIO also reconnects immediately. Reading - calibrate to operate means input capture works but calibration is required.'),
 ('Screen check','Test corner taps, trace an outline continuously, drag between targets, then inspect solid colors. Skipped tests remain not completed. This is a touch and visual inspection tool, not an automatic crack detector.')],
 'Buttons and system lock':[
 ('Dedicated inputs','Right emission: GPIO12. Left emission: GPIO1. Right shortcut: GPIO7. Left shortcut: GPIO16. Both shortcut inputs are enabled and connect through their buttons to GND. GPIO8 remains assigned to Knob 2 D. All numbers are BCM GPIO numbers.'),
 ('Calibrate a button','Choose its input page. Release the contact, then select Calibrate. Press or operate it once and release completely. The measured active level is saved after release. Cancel discards the capture. Inputs default to pull-up, active LOW; do not infer polarity from an unconnected pin reading.'),
 ('Assign side shortcuts','Select Left shortcut or Right shortcut to choose an action. Touch and the dedicated button use the same assignment. Not assigned leaves the side button dim. Emission always uses the confirmation panel.'),
 ('Physical system lock','GPIO20 defaults to active LOW: connect to GND to lock. The screen is captured and blurred, inputs are blocked, and a countdown begins. Unlocking cancels a pending shutdown and restores the current application state. Knobs must be released before rearming.'),
 ('Automatic shutdown','The default lock timeout is 60 seconds; choose Never, 30, 60, 120 or 300 seconds. At expiry the application asks the host OS to shut down. An OS permission or service failure is shown while the interface remains locked. This is an application UI lock, not a hardware laser interlock.')],
 'More and notifications':[
 ('More wheel','Touch More or use its assigned knob push. Four black sectors expand over 800 ms and retract on closing. Tap a sector directly, or turn the knob to rotate options through the filled white highlight. Stick left/right opens the selection. Icons and labels stay upright. The same knob push or the red X closes it.'),
 ('Continuous navigation','The four options wrap indefinitely: Alarms, Settings, Logs and Diagnostics. Within an opened panel, rotation moves focus and push selects. In Settings, push the wheel or scroll rail to adjust it with rotation, then push to finish. Open Notifications from the Settings categories.'),
 ('Action feedback','Lock, stabilise, emission, channel changes, swaps and completed graph gestures create compact notices. New cards appear above older cards, up to four at once; overflow waits for space. Each keeps its own timer. Normal notices last about three seconds and warnings six, then blur and fade over 650 ms. Red critical errors remain until dismissed. Close removes a card immediately, even during fading. Identical rapid notices coalesce.'),
 ('History and consent','Open Settings, Notifications to read the latest 200 records and clear them. Clear requests confirmation in its own card. New messages do not discard that request. Confirm executes its action once; Close or knob Back cancels. Turn Action updates off to mute routine graph and control feedback; warnings and errors remain available.')],
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
 ('Emission','The second side button opens a slide-to-confirm panel. Drag the thumb fully across and release. Alternatively, rotate the owning knob to fill the track and push. A dedicated emission button opens the panel and a second press after 500 ms confirms. Cancelling keeps the previous state. Traces rise smoothly from zero and return to zero when off. The channel dims while idle; its emission and parameter controls stay accessible.')],
 'System':[
 ('Display controls','Brightness and contrast send commands to the actual display driver or monitor. If the monitor does not support a control, its reason is shown. No dimming overlay substitutes for hardware brightness.'),
 ('Resolution and refresh','Choose a mode reported by the host. Keep it within 15 seconds or the previous mode is restored. Refresh rate here is the physical display frequency.'),
 ('Appearance','Recommended themes apply coordinated palettes: Lab Light is the recommended light option; Ion Cyber provides the cyan instrument look. Classic preserves the original green. Accent changes parameter tiles. Corner number and label/icon colors are independently selectable; Automatic restores adaptive ink. Light/Dark changes the interface palette. UI scale changes control density; font family and text size apply across the application.'),
 ('Clock and power','Date and time edits are sent to the host and may require permission. Automatic sleep/shutdown watches inactivity in this app and shows a cancellable countdown first.'),
 ('Restore','Restore defaults resets application preferences and graph settings. Factory reset also clears search history and resets this application’s laser session; it never reflashes the device.')],
 'Storage':[
 ('Local data','Storage shows actual disk usage for the application data location. Preferences and recent searches are saved there in settings.json.'),
 ('Export settings','Export writes the current settings and graph preferences as JSON in the application exports folder.'),
 ('Export graph frame','Capture frame writes the current X, spectroscopy and error samples for both lasers to CSV. This is a snapshot, not continuous data logging.'),
 ('Search history','The history button beside Search shows the eight most recent non-empty queries. Queries are saved on Return or dismissal. Clear removes the persisted list.'),
 ('Version scope','Application v1.13 adds real GPIO knob controls. Upgrade remains a preview; laser signals remain simulated. Firmware V1.6.0 is the requested About identifier, independent of application version 1.13.0.')]
}

TOPICS["Logs and startup"]=[
 ("User logs","Open More > Logs. The latest event appears first. Each record includes a local timestamp, description, outcome and default/warning/critical level. Recording continues when the view is paused. Scroll with touch or the knob scroll rail. Up to 10,000 records are retained."),
 ("Export and clear","Export saves all retained records to exports/logs.csv and exports/logs.md, replacing the previous export. Clear asks for confirmation and leaves a clearing audit record. It never deletes error reports."),
 ("Error reports","Unexpected Python and Qt errors are written to logs/errors.txt, handled failures to logs/bugs.txt and fatal traces to logs/fatal.txt. Reports are local. Keep these with a description of the problem for debugging."),
 ("Manual lock","System Settings > Lock screen > Lock screen now. Hold Unlock for one second to resume. GPIO20 remains authoritative: touch cannot unlock an active physical switch. Never disables lock shutdown; other choices request actual OS shutdown at expiry."),
 ("Startup","The first Pi setup installs dependencies and enables automatic desktop login and app startup. System Settings > Startup controls Start on login and Repair setup. Setup uses the desktop user and requests OS authentication for installation. GPIO boot changes require one restart."),
 ("Trace styles","Function Settings has separate Main and Error color, width and stroke dropdowns for both lasers. Their voltage limits are also independent. Each pair shares one horizontal scale. Choosing a theme preset reapplies its coordinated trace colors."),
 ("Notification size","Small, Medium and Large adjust cards and text on home and Settings. Routine feedback can be muted; operator logging continues.")]
