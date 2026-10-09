"""Actual Qt event tests and screenshots; no hardware or browser required."""
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('QT_QUICK_BACKEND', 'software')
from PySide6.QtCore import QObject, QPoint, QPointF, Qt, qInstallMessageHandler, QCoreApplication, QEvent
from PySide6.QtTest import QTest
from main import create_application

warnings = []
qInstallMessageHandler(lambda kind, context, text: warnings.append(text))
app, engine, ctl, window = create_application(animate=True)
shots = ROOT / 'screenshots'
shots.mkdir(exist_ok=True)
checks = []


def check(name, condition):
    assert condition, name
    checks.append(name)
    print('PASS', name, flush=True)


def item(name):
    value = window.findChild(QObject, name)
    if value is None:
        pending = [window.contentItem()]
        while pending:
            candidate = pending.pop()
            if candidate.objectName() == name:
                value = candidate
                break
            pending.extend(candidate.childItems())
    assert value is not None, name
    return value


def click(name):
    target = item(name)
    point = target.mapToScene(QPointF(target.width()/2, target.height()/2)).toPoint()
    QTest.mouseClick(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, point)
    QTest.qWait(70)


def shot(name):
    QTest.qWait(100)
    image = window.grabWindow()
    assert image.width() == 1600 and image.height() == 720
    assert image.save(str(shots / name))


QTest.qWait(1000)
check('Boot logo and progress remain visible during the 3-second animation', window.property('booting') and .2 < window.property('bootProgress') < .6)
shot('01-boot.png')
QTest.qWait(2150)
check('Boot automatically enters home after 3 seconds', not window.property('booting'))
shot('02-home.png')
old = ctl.elapsed
QTest.qWait(150)
check('Live mock stream continues to advance', ctl.elapsed > old)

click('switch1')
check('Right selector can show Laser 1 without changing the left', ctl.instrument.views == [0, 0])
click('lock1')
check('Both views use the same Laser 1 lock state; Laser 2 remains independent', ctl.instrument.lasers[0].locked and not ctl.instrument.lasers[1].locked)
click('lock0')
click('switch0')
check('Left selector changes only the left view', ctl.instrument.views == [1, 0])
click('switch0'); click('switch1')

click('fullscreen0')
check('Left fullscreen opens for its selected channel', window.property('fullscreenSide') == 0)
shot('03-fullscreen-laser1.png')
click('exitFullscreen')
click('fullscreen1')
check('Right fullscreen opens for its selected channel', window.property('fullscreenSide') == 1)
shot('03-fullscreen-laser2.png')
click('exitFullscreen')

click('topParameter0')
check('Corner opens the modal keypad', item('keypad').isVisible())
for k in ('key2', 'key4', 'key0', 'keyDecimal', 'key1', 'key2', 'key5'):
    click(k)
shot('04-keypad.png')
click('keyEnter')
check('Keypad commits decimal current with one Enter', ctl.instrument.lasers[0].values['current'] == 240.125 and not item('keypad').isVisible())
click('topParameter1')
for k in ('key2', 'key5', 'keyDecimal', 'key1', 'key2', 'key5'):
    click(k)
click('keyEnter')
check('Right keypad edits Laser 2 temperature only', ctl.instrument.lasers[1].values['temperature'] == 25.125 and ctl.instrument.lasers[0].values['temperature'] == 24)
click('bottomParameter0'); click('key3'); click('keyDecimal'); click('key5'); click('keyEnter')
check('Lower left corner edits Umax', ctl.instrument.lasers[0].values['umax'] == 3.5)
click('bottomParameter1'); click('key3'); click('key6'); click('keyMinus'); click('keyEnter')
check('Lower right corner accepts a negative PID value', ctl.instrument.lasers[1].values['pid'] == -36)

click('topParameter0'); click('key9'); click('key9'); click('key9'); click('keyEnter')
check('Out-of-range entry stays open without mutating accepted current', item('keypad').isVisible() and ctl.instrument.lasers[0].values['current'] == 240.125 and bool(item('keypad').property('errorMessage')))
click('keyLeft');click('keyBackspace');click('keyRight')
check('Cursor movement and backspace edit the draft', item('keypad').property('draft') == '99')
click('keyCancel')
check('Cancel preserves the accepted value', ctl.instrument.lasers[0].values['current'] == 240.125)

click('target0'); click('stabilise0')
check('Target and stabilisation controls update only their laser', ctl.instrument.lasers[0].selected >= 0 and ctl.instrument.lasers[0].stabilised and not ctl.instrument.lasers[1].stabilised)
plot = item('absorption0Renderer')
old_min = plot.xMinimum
QTest.mousePress(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(420,350))
QTest.mouseMove(window, QPoint(460,360), 50)
QTest.mouseRelease(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(460,360))
check('Dragging pans the graph without changing current', plot.xMinimum != old_min and ctl.instrument.lasers[0].values['current'] == 240.125)
check('Absorption and error maintain aligned X ranges', abs(plot.xMinimum-item('error0Renderer').xMinimum)<1e-6)
span = plot.xMaximum - plot.xMinimum
plot.zoom(2, 300)
check('Anchored zoom reduces the displayed range', abs((plot.xMaximum-plot.xMinimum)-span/2)<1e-6)
lo,hi=plot.xMinimum,plot.xMaximum
click('fullscreen0')
full_plot=item('fullscreenAbsorptionRenderer')
check('Fullscreen preserves the pane horizontal viewport', abs(full_plot.xMinimum-lo)<1e-6 and abs(full_plot.xMaximum-hi)<1e-6)
full_plot.zoom(1.5,400)
new_lo=full_plot.xMinimum
click('exitFullscreen')
check('Fullscreen viewport edits return to the originating pane', abs(plot.xMinimum-new_lo)<1e-6)
plot.resetView()
check('Reset restores the reference voltage span', plot.xMinimum == 48.2 and plot.xMaximum == 68.2)

touch = QTest.createTouchDevice()
QTest.touchEvent(window, touch).press(0, QPoint(1558,366), window).commit()
QTest.qWait(30)
QTest.touchEvent(window, touch).release(0, QPoint(1558,366), window).commit()
QTest.qWait(80)
check('A touchscreen tap activates the right stabilisation button', ctl.instrument.lasers[1].stabilised)
ctl.toggleStabilisation(1)
span = plot.xMaximum - plot.xMinimum
QTest.touchEvent(window, touch).press(0, QPoint(300,300), window).press(1, QPoint(500,300), window).commit()
QTest.qWait(50)
QTest.touchEvent(window, touch).move(0, QPoint(280,300), window).move(1, QPoint(520,300), window).commit()
QTest.qWait(50)
QTest.touchEvent(window, touch).move(0, QPoint(240,300), window).move(1, QPoint(560,300), window).commit()
QTest.qWait(50)
QTest.touchEvent(window, touch).release(0, QPoint(240,300), window).release(1, QPoint(560,300), window).commit()
QTest.qWait(50)
check('Two-finger touchscreen spread zooms the live plot', plot.xMaximum - plot.xMinimum < span)
plot.resetView()

click('more0'); QTest.qWait(240)
check('Left more menu expands to its final geometry', item('radialMenu').isVisible() and item('radialMenu').property('expansion') == 1)
shot('05-radial-left.png')
click('radialCancel')
check('Red X dismisses the radial menu', not item('radialMenu').isVisible())
click('more1'); QTest.qWait(240)
check('Right more menu mirrors inward and captures its laser', item('radialMenu').property('side') == 1 and item('radialMenu').property('channelIndex') == 1)
shot('05-radial-right.png')
click('radialCancel')
click('more0');QTest.qWait(240)
# Signals sector in the left annulus.
QTest.mouseClick(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(95,275));QTest.qWait(50)
check('Radial Signals sector toggles the selected laser error trace', not ctl.instrument.lasers[0].show_error and not item('radialMenu').isVisible())
ctl.toggleError(0)
click('more1');QTest.qWait(240)
QTest.mouseClick(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(1349,345));QTest.qWait(80)
check('Right radial Settings opens its captured channel keypad', item('keypad').isVisible() and item('keypad').property('channelIndex') == 1)
click('keyCancel')
click('more0');QTest.qWait(240)
QTest.mouseClick(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(326,500));QTest.qWait(80)
check('Radial Display enters fullscreen', window.property('fullscreenSide') == 0)
click('exitFullscreen')
click('more0');QTest.qWait(240)
QTest.mouseClick(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(300,650));QTest.qWait(80)
check('Radial Diagnostics reports the captured laser without adding a page', 'Laser 1' in window.property('notice'))

qml_errors = [w for w in warnings if any(s in w for s in ('TypeError', 'ReferenceError', 'Error:', 'Binding loop', 'failed to load', 'Cannot assign'))]
check('No QML runtime errors or binding loops', not qml_errors)
(ROOT / 'tests' / 'ui-results.json').write_text(json.dumps({'checks': checks, 'count': len(checks), 'viewport': [1600,720], 'platform': 'Qt offscreen/software on Windows; Raspberry Pi hardware not exercised', 'qml_errors': qml_errors}, indent=2), encoding='utf-8')
ctl.timer.stop()
window.close()
engine.deleteLater()
QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
print(f'{len(checks)} UI checks passed')
