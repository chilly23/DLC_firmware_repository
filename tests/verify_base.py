"""Behavioral regression suite: model, actual QML controls, mouse and native touch."""
import json
import math
import os
import statistics
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('QT_QUICK_BACKEND', 'software')
from PySide6.QtCore import QObject, QPoint, QPointF, Qt, QCoreApplication, QEvent, qInstallMessageHandler
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from controller.bridge import Controller
from controller.model import Laser
from settings_ui.model import SettingsStore
from main import create_application

messages, checks = [], []
qInstallMessageHandler(lambda kind, context, message: messages.append(message))
temporary = tempfile.TemporaryDirectory()
app, engine, ctl, window = create_application(skip_boot=False, animate=False, data_dir=temporary.name)
host = ctl.settings_host
previews = ROOT / 'tests' / 'base-screenshots'
previews.mkdir(exist_ok=True)

def check(name, condition):
    assert condition, name
    checks.append(name)
    print('PASS', name, flush=True)

def item(name):
    obj = window.findChild(QObject, name)
    if obj is not None:
        return obj
    stack = [window.contentItem()]
    while stack:
        obj = stack.pop()
        if obj.objectName() == name:
            return obj
        stack.extend(obj.childItems())
    raise AssertionError('Missing: ' + name)

def center(name):
    obj = item(name)
    return obj.mapToScene(QPointF(obj.width()/2, obj.height()/2)).toPoint()

def tap(name):
    QTest.mouseClick(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, center(name))
    QTest.qWait(40)

def step(duration):
    for _ in range(round(duration/.05)):
        ctl.step(.05)

def shot(name):
    QTest.qWait(80)
    assert window.grabWindow().save(str(previews/(name+'.png')))

def settings_action(kind, value=None, touch=False):
    w = host.window
    w.repaint()
    for rect, action in w.hits:
        if action[0] == kind and (value is None or action[1] == value):
            pos = (rect.center()*w.scale+w.offset).toPoint()
            if touch:
                QTest.touchEvent(w, device).press(0, pos, w)
                QTest.touchEvent(w, device).release(0, pos, w)
            else:
                QTest.mouseClick(w, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, pos)
            QTest.qWait(30)
            return pos
    raise AssertionError(f'Missing settings action {kind} {value}')

def drag(start, end, hold=False):
    QTest.mousePress(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
    if hold: QTest.qWait(650)
    QTest.mouseMove(window, end, 40)
    QTest.mouseRelease(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, end)
    QTest.qWait(50)

device = QTest.createTouchDevice()
try:
    QTest.qWait(350)
    check('Boot holds both signals at zero before acquisition', window.property('booting') and not ctl._live and all(l.sample(53, 0)==(0.,0.) for l in ctl.instrument.lasers))
    shot('01-boot')
    QTest.qWait(3000)
    check('Three-second boot finishes and starts acquisition', not window.property('booting') and ctl._live)
    shot('02-start-at-zero')
    levels=[]
    for n in range(30):
        ctl.step(.05)
        levels.append(ctl.instrument.lasers[0].signal.level)
        if n==10: shot('03-rising')
    check('Smooth monotonic startup reaches full amplitude in 1.5 seconds', 0<levels[0]<.01 and levels==sorted(levels) and levels[-1]==1.)
    spec=item('absorption0Renderer'); err=item('error0Renderer')
    check('Startup leaves shared x coordinates fixed', spec.xMinimum==err.xMinimum==48.2 and spec.xMaximum==err.xMaximum==68.2)
    check('Only bottom graph draws x labels', not spec.showXAxis and err.showXAxis)
    check('Both channels have genuinely different peaks and error signals', ctl.instrument.lasers[0].signal.peaks!=ctl.instrument.lasers[1].signal.peaks and abs(ctl.instrument.lasers[0].sample(53.5,0)[0]-ctl.instrument.lasers[1].sample(53.5,0)[0])>2)
    check('v1.2 frame, green readouts, background and divider retained', window.width()==1600 and window.height()==720 and window.color().name()=='#0e140f' and item('topParameter0').property('color').name()=='#008622' and item('divider').height()==605)
    shot('04-home-live')
    for side in (0,1):
        plot=item(f'absorption{side}Renderer')
        laser=ctl.instrument.lasers[side]
        plot.zoom(1.3,330)
        tap('lock'+str(side))
        bounds=(plot.xMinimum,plot.xMaximum,plot._yshift,laser.selected)
        plot.pan(70,20);plot.zoom(1.5,320);plot.resetView();plot.pick(350)
        drag(center('absorption'+str(side)),center('absorption'+str(side))+QPoint(90,30))
        drag(center('absorption'+str(side)),QPoint(1100 if side==0 else 300,300),True)
        check(f'Laser {side+1} lock blocks pan/zoom/reset/pick/hold-drag', plot.interactionLocked and bounds==(plot.xMinimum,plot.xMaximum,plot._yshift,laser.selected) and not item('graphDrag').isVisible())
        check(f'Laser {side+1} lock uses closed icon and white active fill', item('lock'+str(side)).property('iconName')=='lock' and item('lock'+str(side)).property('color').name()=='#bdc0bb')
        before=laser.sample(55,0);ctl.step(.15)
        check(f'Laser {side+1} signal remains live while view locked', before!=laser.sample(55,0))
        tap('fullscreen'+str(side))
        full=item('fullscreenAbsorptionRenderer');fullbounds=(full.xMinimum,full.xMaximum)
        full.zoom(1.5,600);full.pan(70,0);full.resetView()
        check(f'Fullscreen {side+1} shares lock and one bottom x axis', full.interactionLocked and (full.xMinimum,full.xMaximum)==fullbounds and not full.showXAxis and item('fullscreenErrorRenderer').showXAxis)
        tap('exitFullscreen');tap('lock'+str(side))
        check(f'Laser {side+1} unlock uses open icon with transparent fill', item('lock'+str(side)).property('iconName')=='unlock' and item('lock'+str(side)).property('color').alpha()==0)
        plot.resetView()
        tap('emission'+str(side))
        before=laser.signal.level
        step(.5)
        check(f'Laser {side+1} emission falls smoothly and remains positive in transition', 0<laser.signal.level<before and item('emission'+str(side)).property('color').alpha()==0)
        step(1.1)
        check(f'Laser {side+1} off leaves exact zero spectroscopy and error', laser.signal.level==0 and all(laser.sample(x,0)==(0.,0.) for x in (48.2,53.5,61,68.2)))
        if side==0:shot('05-emission-off')
        tap('emission'+str(side));step(.4)
        level=laser.signal.level
        tap('emission'+str(side))
        check(f'Laser {side+1} transition reversal has no amplitude jump', laser.signal.level==level)
        step(.25);tap('emission'+str(side));step(1.6)
        check(f'Laser {side+1} restarts and active emission is white', laser.signal.level==1 and item('emission'+str(side)).property('color').name()=='#bdc0bb')
        tap('stabilise'+str(side));step(1.)
        check(f'Laser {side+1} third button activates real smoothing', laser.stabilised and laser.signal.smoothing>.99 and item('stabilise'+str(side)).property('color').name()=='#bdc0bb')
        tap('stabilise'+str(side))
    noise=Laser(1);noise.signal.emission(True)
    raw=[];smooth=[]
    for n in range(200):
        noise.signal.advance(.05,n*.05,noise.values,True)
        if n>30:
            raw.append(noise.signal.raw_e[10]);smooth.append(noise.signal.filtered_e[10])
    check('Stabilisation measurably reduces noise (>30%)', statistics.pstdev(smooth)<statistics.pstdev(raw)*.7)
    changes={'current':120,'temperature':27,'umax':1.3,'pid':-15,'feedforward':10,'offset':60,'amplitude':12,'frequency':30,'setpoint':.5}
    for key,value in changes.items():
        normal=Laser(1);edited=Laser(1);edited.set_value(key,str(value))
        for laser in (normal,edited):
            laser.signal.emission(True)
            laser.signal.advance(2,2,laser.values,False)
        difference=max(abs(a-b) for a,b in zip(normal.signal.raw_s+normal.signal.raw_e,edited.signal.raw_s+edited.signal.raw_e))
        check(f'{key} changes the live simulated signal', difference>.01)
    for side,bottom,module,field in [(0,False,'TC','temperature'),(1,False,'CC','feedforward'),(0,True,'PC','offset'),(1,True,'TC','pid')]:
        prefix=('bottom' if bottom else 'top')+'Parameter'+str(side)
        tap(prefix+'Module');tap('module'+module);tap('field'+field)
        check(f'{prefix} control panel selects {field}',ctl.channel(side)['bottom' if bottom else 'top']==field)
    ctl.selectField(0,False,'current');ctl.selectField(1,False,'temperature');ctl.selectField(0,True,'umax')
    for button,side,key,digits,expected in [('topParameter0Value',0,'current','240',240.),('topParameter1Value',1,'temperature','25',25.),('bottomParameter0Value',0,'umax','3',3.),('bottomParameter1Value',1,'pid','2',2.)]:
        tap(button)
        for d in digits:tap('key'+d)
        tap('keyEnter')
        check(f'Numeric editor updates accepted {key} value',ctl.instrument.lasers[side].values[key]==expected and not item('keypad').isVisible())
    tap('bottomParameter1Value');pad=item('keypad');editor=item('keypadDraft')
    pad.setProperty('draft','1234');pad.setProperty('cursor',2);pad.setProperty('replaceDraft',False)
    tap('key9');check('Numpad inserts once at cursor',pad.property('draft')=='12934')
    tap('keyBackspace');tap('keyMinus')
    check('Wide minus toggles sign while preserving cursor', pad.property('draft')=='-1234' and pad.property('cursor')==3 and item('keyMinus').property('iconName')=='minus')
    check('Numpad has focused blinking native cursor',editor.property('activeFocus') and editor.property('cursorVisible') and app.cursorFlashTime()==1000)
    shot('06-numpad-minus')
    tap('keyEnter');check('Out-of-range value is rejected without mutation',pad.isVisible() and ctl.instrument.lasers[1].values['pid']==2.)
    tap('keyCancel')
    tap('switch1');check('Independent view switch can show Laser 1 twice',ctl.instrument.views==[0,0])
    tap('lock0');check('Duplicated view shares the same graph lock',item('absorption1Renderer').interactionLocked)
    tap('lock1');tap('switch1')
    start=center('absorption0');old=spec.xMinimum
    drag(start,start+QPoint(70,10))
    check('Pan remains working and synchronises graph pair',spec.xMinimum!=old and spec.xMinimum==err.xMinimum)
    spec.resetView()
    touch=QTest.touchEvent(window,device,False);a,b=QPoint(380,280),QPoint(530,280)
    touch.press(0,a,window).press(1,b,window).commit()
    for delta in (10,25,40,60):
        QTest.qWait(40);touch.move(0,a-QPoint(delta,0),window).move(1,b+QPoint(delta,0),window).commit()
    touch.release(0,a-QPoint(60,0),window).release(1,b+QPoint(60,0),window).commit();QTest.qWait(60)
    check('Native pinch zoom remains working with shared x range',spec.xMaximum-spec.xMinimum<19 and err.xMinimum==spec.xMinimum)
    spec.resetView()
    touch=QTest.touchEvent(window,device,False)
    touch.press(0,start,window).commit();QTest.qWait(700)
    check('Native long press opens existing graph drag skeleton',item('graphDrag').isVisible())
    end=QPoint(1180,350);touch.move(0,end,window).commit();QTest.qWait(100);shot('07-drag-drop')
    touch.release(0,end,window).commit();QTest.qWait(100)
    check('Drop swaps full channel assignment',ctl.instrument.views==[1,0]);ctl.moveGraph(0,1)
    for side in (0,1):
        tap('fullscreen'+str(side));shot('08-fullscreen-laser'+str(side+1))
        check(f'Fullscreen displays correct channel {side+1}',item('fullscreenAbsorptionRenderer').channelIndex==side)
        tap('exitFullscreen')
    tap('shortcut0');check('Unassigned shortcut remains Not Set',item('shortcut0').property('text')=='Not\nSet')
    for side in (0,1):
        tap('more'+str(side));QTest.qWait(250)
        angle=math.radians(-100+1.5*36.25)
        p=QPoint(round((63 if side==0 else 1537)+(1 if side==0 else -1)*270*math.cos(angle)),round(539+270*math.sin(angle)))
        QTest.mouseClick(window,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,p);QTest.qWait(200)
        check(f'Radial Settings {side+1} opens Frame 58',host.window.isVisible() and host.window.variant==58 and not window.isVisible())
        w=host.window
        if side==0:
            settings_action('search');pos=settings_action('key','a',touch=True)
            local=QPointF(pos)
            for kind,buttons in [(QEvent.Type.MouseButtonPress,Qt.MouseButton.LeftButton),(QEvent.Type.MouseButtonRelease,Qt.MouseButton.NoButton)]:
                ev=QMouseEvent(kind,local,local,QPointF(w.mapToGlobal(pos)),Qt.MouseButton.LeftButton,buttons,Qt.KeyboardModifier.NoModifier,Qt.MouseEventSource.MouseEventSynthesizedByQt)
                QCoreApplication.sendEvent(w,ev)
            check('Native touch plus compatibility mouse inserts exactly once',w.search.text()=='a')
            settings_action('key','a');settings_action('key','a')
            check('Real rapid repeat taps are not swallowed',w.search.text()=='aaa')
            w.search.selectAll();settings_action('key','d')
            check('Virtual keyboard replaces selected text',w.search.text()=='d')
            settings_action('key','shift');settings_action('key','a')
            settings_action('key','mode');settings_action('key','1');settings_action('key','backspace')
            check('Shift, numeric mode and backspace each execute once',w.search.text()=='dA')
            settings_action('key','mode');w.search.setText('dis');w.search.setCursorPosition(3)
            settings_action('suggest','display')
            check('Suggestion replaces prefix without duplicating input',w.search.text()=='display ')
            check('Search uses focused native blinking cursor',w.search.hasFocus() and app.cursorFlashTime()==1000)
            QTest.keyClicks(w.search,'x');check('Physical key event inserts once',w.search.text()=='display x')
            w.search.setText('display');w.grab().save(str(previews/'09-keyboard.png'))
            suggestions=[action[1] for _,action in w.hits if action[0]=='suggest']
            check('Suggestion bar contains three distinct completions',len(suggestions)==3 and len(set(suggestions))==3)
            settings_action('key','enter');QTest.qWait(650)
            check('Submitted search navigates and records real history',w.content=='display' and w.store.history==['display'])
            settings_action('history');QTest.qWait(50)
            check('Adjacent search button only opens history viewer',w.overlay=='history' and not any(a[0]=='history_item' for _,a in w.hits))
            w.grab().save(str(previews/'10-history.png'))
            settings_action('clear_history')
            check('Clear history persists to disk',SettingsStore(w.store.path).history==[] and w.search.text()=='display')
            QTest.mouseClick(w,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,QPoint(1400,650))
            check('Outside tap closes history',w.overlay is None)
            w.select(w.order.index('function'));QTest.qWait(700)
            settings_action('toggle','laser1')
            check('Settings emission shares the home channel model',not ctl.instrument.lasers[0].emission)
            settings_action('toggle','laser1');settings_action('toggle','stabilisation')
            check('Settings stabilisation controls both live filters',all(l.stabilised for l in ctl.instrument.lasers))
            settings_action('choice','scan_rate');check('Refresh control changes actual frame timer',ctl.timer.interval()==33)
            settings_action('toggle','stabilisation')
        w.close();QTest.qWait(70)
        check(f'Closing settings {side+1} restores same home state',window.isVisible() and ctl.instrument.views==[0,1])
    errors=[m for m in messages if any(k in m for k in ('TypeError','ReferenceError','Cannot assign','Binding loop','failed to load','Error:'))]
    check('No QML runtime errors',not errors)
    (ROOT/'tests'/'base-validation.json').write_text(json.dumps({'checks':checks,'count':len(checks),'warnings':messages,'platform':app.platformName(),'hardware_tested':False},indent=2),encoding='utf8')
    print(f'{len(checks)} checks passed',flush=True)
finally:
    host.shutdown();ctl.timer.stop();window.close();engine.deleteLater()
    QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
    temporary.cleanup()
