"""Non-destructive walkthrough targets. Each entry opens a real application surface."""
TOUR=[]
def step(title,body,rect=None,section='',action='',**extra):
    TOUR.append(dict(title=title,body=body,rect=rect or [650,185,900,487],section=section,action=action,**extra))

step('Two lasers, one workspace','Each half can show either laser. Switching one half does not change the other.',[485,8,640,88])
step('Parameter controls','Tap a number to edit. The module and field selectors choose which measurement occupies that corner.',[7,7,418,80])
step('Lock the view','Lock prevents pan, zoom and rearranging while acquisition continues.',[0,124,96,90])
step('Emission and stabilisation','Emission raises traces from zero. Stabilise reduces live noise. White fill indicates an active button.',[0,230,96,181])
step('Inspect and arrange','Pan or pinch to inspect. Hold a plot for 550 ms: move vertically to swap signals, or across the divider to swap laser panels.',[122,100,680,511])
step('Signals and axes','The signal labels open this panel. All changes belong to the laser, even when it appears on both sides.',[830,60,740,600],action='signals')
step('Fullscreen charts','Expand one laser. Signal labels still open chart controls; Exit returns to the shared workspace.',[19,90,1564,603],action='fullscreen')
step('More controls','The quarter-ring contains Settings, Display, Alarms, Diagnostics and Notifications. Rotate to move upright icons into the fixed white sector, then push to open. The red X closes it.',[0,330,600,390],action='more')
step('Display preferences','Hardware controls report the connected screen capabilities. Unsupported controls explain why they are unavailable.',section='display')
for side in (0,1):
    side_name='Left' if side==0 else 'Right'
    for action,title,body in [
        ('modules','Module selection','Choose TC for temperature, CC for current or PC for piezo. Each corner can use its own module.'),
        ('fields','Parameter fields','Choose a field from the module. Its units, accepted range and decimal precision follow the selected field.'),
        ('numpad','Numeric editor','Type a value and Apply. Arrow keys move the caret; minus changes sign. Hold Backspace to clear. Red X cancels.'),
        ('signals','Signals panel','Combined overlays both traces. Split uses upper and lower plots with one shared X scale.'),
        ('combined','Signal visibility','Each switch independently shows or hides a signal. This affects this laser only.'),
        ('axes','Main signal axis','Use minus/plus to step V/div and position, or tap a number for the numpad. The slider sets the main/error height ratio from 20:80 to 80:20.'),
        ('error_axes','Error signal axis','The Error tab has independent V/div and position. Restore defaults resets both axes and the height ratio.'),
        ('alarms','Trace alarms','Enable monitoring and set spectroscopy and absolute error limits. Alarms require a sustained breach; Acknowledge marks the event. History can be cleared.'),
    ]:
        x=830 if side==0 else 30
        rect=[x,60,740,600] if action in ('signals','combined','axes','error_axes','alarms') else [0 if side==0 else 964,90,636,530]
        step(side_name+' · '+title,body,rect,action=action,side=side)
    step(side_name+' · channel buttons','Channel switch changes this half only. The square expands it. Not set is an unassigned shortcut and stays dim.',[0 if side==0 else 1504,118,96,488],side=side)
    step(side_name+' · lower parameter','The lower corner has its own module, field and numeric entry, using the same controls as the upper corner.',[7 if side==0 else 1175,634,418,80],side=side)

display=[('Brightness','brightness','Move the value tile; release to send one hardware command. The preview stays steady until hardware readback finishes.'),
 ('Contrast','contrast','Changes monitor contrast through its driver, when supported. It never adds a fake dim layer.'),
 ('Recommended themes','theme_preset','Choose Classic, Lab Light, Ion Cyber, Porcelain, Orchid or Clay. Presets update the actual interface palette and trace contrast.'),
 ('Corner number color','corner_number_color','Choose a number color independently of labels and icons. Automatic selects readable ink for the current accent.'),
 ('Corner label / icon color','corner_detail_color','Choose the foreground for all corner labels, units, chevrons and rules. This applies to all four corners.'),
 ('Accent color','accent','Choose from all fifteen supplied colors, including Black and White. Swipe the dropdown to see more.'),
 ('Appearance','appearance','Light and Dark update both the home screen and settings.'),
 ('Resolution','resolution','Only reported display modes appear. Confirm within 15 seconds or the previous mode returns.'),
 ('Refresh rate','refresh','Choose a physical display refresh rate reported for the current resolution.'),
 ('UI scale','ui_scale','Adjust control and text density while retaining the 1600 × 720 design coordinate system.')]
for i,(title,key,body) in enumerate(display):step(title,body,section='display',row=i,key=key)

function=[('Sampling rate','Sets simulated frame updates per second; this setting is shared by both lasers.'),
 ('Calibrate baseline','Capture the current frame median as zero. Emission must be on and settled.'),
 ('Reset baseline','Remove the captured baseline for this laser.'),
 ('Auto bandwidth','Enable a temporal low-pass filter whose cutoff follows the sample rate.'),
 ('Maximum points','Choose the number of samples generated per frame.'),
 ('X minimum','Set the lower scan coordinate. Both signals always share the same X domain.'),
 ('X maximum','Set the upper scan coordinate. Invalid or excessive spans are rejected.'),
 ('Main minimum','Set the lower spectroscopy voltage limit.'),('Main maximum','Set the upper spectroscopy voltage limit.'),
 ('Error minimum','Set the lower error voltage limit.'),('Error maximum','Set the upper error voltage limit.'),
 ('Graph color','Choose the trace color from the supplied palette.'),('Laser color','Choose the channel identity color.'),
 ('Line width','Adjust the rendered trace stroke width.')]
for i,(title,body) in enumerate(function):
    step(title,body+' Laser 1 and Laser 2 have adjacent controls in this table.',section='function',row=i)

system=[('Date and time','Send a valid local date and time to the host OS. This may require OS permission.'),
 ('Language','Change the interface language. Technical documentation falls back to English when a translation is unavailable.'),
 ('Font family','Choose an installed font family. Scroll the dropdown to reach all installed fonts.'),
 ('Text size','Adjust the text scale across the instrument interface.'),
 ('Side buttons','Choose icons only or icon + name for Lock, Emission, Stabilise, Not set and More.'),
 ('Automatic power','Choose Sleep or Shutdown and an idle timeout. A 30-second countdown allows cancellation.'),
 ('System information','Inspect application, firmware, OS, architecture, Python, Qt and data location.'),
 ('Restore defaults','Reset preferences and chart settings, preserving search history. Confirmation is required.'),
 ('Factory reset','Reset application preferences, chart session and history. It does not reflash the device.'),
 ('Take a tour','Start this guide again. Previous, Next, Pause and Skip are always available.')]
for i,(title,body) in enumerate(system):step(title,body,section='system',row=i)
step('Host clock','The clock page shows the real system time. Set date and time opens a numeric editor.',section='system',route='clock')
step('Power options','Choose the action and timeout from dropdowns. Never disables automatic power actions.',section='system',route='power')
step('System details','Swipe to inspect the runtime and host information.',section='system',route='info')
for i,(title,body) in enumerate([('Export settings','Save preferences as a JSON file in the exports folder.'),('Capture graph frame','Save both lasers’ current X, spectroscopy and error samples as CSV.'),('Clear search history','Remove stored queries. This does not erase exported files.')]):
    step(title,body,section='storage',row=i)
for topic in ('Graphs','Analysis','Parameters','System','Storage'):
    step(topic+' help','Swipe this document to read the full topic. Back returns to the Help list.',section='help',route='help:'+topic)
step('Three physical knobs','The cards match the panel: Knob 1 top left, Knob 2 bottom left, Knob 4 bottom right. Knob 3 is not connected. Calibration is required before GPIO shortcuts run.',section='control',knob_intro=True)
step('Live input feedback','The stick on each card follows the physical directions, centre press and encoder rotation. Retry GPIO reconnects after a wiring or permission correction.',[680,190,846,308],section='control')
step('Choose a target corner','Each knob has a target corner. Parameter actions follow the module and laser currently displayed there, even after a channel swap.',section='control',route='knob:0',control_row=0)
step('Calibrate physical directions','Choose Calibrate. Release the knob and capture its idle state. Press the centre alone first, then move Up, Right, Down and Left; release completely after each. Direction plus centre contact is accepted. Then check both rotation directions and Save.',section='control',route='knob:0',control_row=1)
step('Encoder click sensitivity','If one physical click produces two steps, select four transitions per click. Two is the supplied demo default. This changes decoding without changing your shortcuts.',section='control',route='knob:0',control_row=2)
step('Map every operation','Clockwise and anticlockwise rotation, four stick directions and a short push each have a dropdown. Pick an action; it is saved immediately. Not assigned disables just that operation.',section='control',route='knob:0',control_row=4)
step('Edit one digit at a time','Knob 1 and Knob 4 initially use left and right to select a digit; rotation changes it. An underline shows the selected digit. Values remain inside the selected parameter limits.',[7,7,418,80])
step('Navigate without touching','Hold any calibrated knob push for 700 ms to enter navigation mode. Rotate to move the filled white focus, then short-push to activate. Stick left goes back; stick right activates. Hold push again to restore your shortcuts.',section='control',route='knob:0',control_row=10)
step('Adjust sliders and scroll','In navigation mode, focus a slider or scroll rail and push once. Rotate to adjust; push again to finish. Hardware brightness and contrast are sent once on finish. Stick left cancels a pending hardware adjustment.',section='display')
step('Navigate the Settings wheel','Focus the left Settings wheel and push to enter it. Rotate to change category. Push again to leave the wheel and choose controls in the right panel.',[15,306,577,108],section='control')
step('Reset only what you need','Restore shortcut defaults keeps calibration. Reset calibration keeps the shortcuts and requires calibration again. Neither changes the supplied wiring.',section='control',route='knob:0',control_row=12)
step('Check touchscreen coverage','Screen check tests four corner taps, a continuous rectangular trace, dragging a puck, and solid screen colors. Skipping a step never marks it passed. This checks touch response and visible pixels; it cannot diagnose glass damage.',[928,581,265,62],section='control')
step('Upgrade','Update is a preview. No firmware is installed and no download source is configured.',section='upgrade')
step('About','Model, firmware, organization, serial number and the supplied QR identify the instrument.',section='about')
step('Search keyboard','Tap Search to open the custom keyboard. Suggestions complete words. Hold Backspace to clear; tap outside to dismiss.',[255,228,1090,456],section='display',action='keyboard')
step('Search history','The history button shows real saved queries in a read-only list. Clear removes the saved list from disk.',[480,90,640,320],section='display',action='history')
step('Touch help','Hold a supported control for 850 ms to show its tooltip without activating it. Backspace keeps its 650 ms clear action.',[0,124,96,90])

step('Side-specific focus','The two left knobs navigate the left home half. Knob 4 navigates the right half. A knob cannot take over the opposite-side open panel. Shared Settings is accessible from either side.',[7,100,786,510])
step('Emission confirmation','Tap Emission, then drag the slider fully across. With a knob, turn clockwise to fill it and push. The dedicated emission button opens this request; press it again after half a second to confirm. Outside tap or stick left cancels.',[7,230,88,86])
step('Buttons and physical lock','Open Buttons & lock to view each GPIO input, select its pin and active level, calibrate its released/pressed states, and configure both side shortcuts.',section='control',route='panel')
step('One pin per control','The right shortcut uses GPIO7 and the left shortcut uses GPIO16. Both are enabled and active when grounded through a button. GPIO8 stays on Knob 2 direction D. Software rejects duplicate assignments.',section='control',route='contact:left_shortcut')
step('Locked screen and shutdown','GPIO20 defaults to locked when connected to ground. The blurred lock screen blocks touch and knobs. Unlock before the 60-second countdown ends to resume. The countdown is configurable; expiry requests actual OS shutdown.',section='control',route='panel')
step('Notification history','Normal actions fade away. Warnings use a yellow triangle; critical errors remain until dismissed. History keeps the latest 200 entries. Clear asks for confirmation; Action updates can mute routine action notices.',section='notifications')
