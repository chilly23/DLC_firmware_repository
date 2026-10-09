"""Regression checks for the deliberately small v1 -> v1.2 change set."""
import hashlib
import json
import math
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
from PySide6.QtCore import QObject, QPoint, QPointF, Qt, QCoreApplication, QEvent, qInstallMessageHandler
from PySide6.QtTest import QTest
from main import create_application

messages = []
qInstallMessageHandler(lambda kind, context, message: messages.append(message))
temporary = tempfile.TemporaryDirectory()
app, engine, ctl, window = create_application(skip_boot=True, animate=False, data_dir=temporary.name)
host = ctl.settings_host
checks = []
previews = ROOT / "screenshots"
previews.mkdir(exist_ok=True)

def check(name, condition):
    assert condition, name
    checks.append(name)
    print("PASS", name, flush=True)

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
    raise AssertionError("Missing: " + name)

def center(name):
    obj = item(name)
    return obj.mapToScene(QPointF(obj.width()/2,obj.height()/2)).toPoint()

def tap(name):
    QTest.mouseClick(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, center(name))
    QTest.qWait(75)

def shot(name):
    QTest.qWait(150)
    assert window.grabWindow().save(str(previews / (name + ".png")))

def settings_action(kind, value=None):
    w=host.window
    w.repaint()
    for rect, action in w.hits:
        if action[0] == kind and (value is None or action[1] == value):
            pos=(rect.center()*w.scale+w.offset).toPoint()
            QTest.mouseClick(w,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,pos)
            QTest.qWait(60)
            return
    raise AssertionError(f'Missing settings action {kind} {value}')

try:
    QTest.qWait(350)
    check('v1 home background retained', window.color().name() == '#0e140f')
    check('v1 green readouts retained', item('topParameter0').property('color').name() == '#008622')
    original=ROOT.parent/'mock1-pyside6'/'controller'/'plot.py'
    if original.exists():
        check('v1 graph renderer unchanged', hashlib.sha256(original.read_bytes()).digest() == hashlib.sha256((ROOT/'controller'/'plot.py').read_bytes()).digest())
    check('Divider stops at graph bottom', item('divider').height() == 605)
    shot('01-home')
    for side in (0,1):
        for button,attr in [('lock','locked'),('stabilise','stabilised')]:
            check(f'{button} {side+1} starts unfilled', item(button+str(side)).property('color').alpha()==0)
            tap(button+str(side))
            check(f'{button} {side+1} toggles model and white active fill', getattr(ctl.instrument.lasers[side],attr) and item(button+str(side)).property('color').name() == '#bdc0bb')
            if side==0 and button=='stabilise':shot('02-white-active')
            tap(button+str(side))
            check(f'{button} {side+1} returns to transparent', not getattr(ctl.instrument.lasers[side],attr) and item(button+str(side)).property('color').alpha()==0)
        old=ctl.instrument.lasers[side].selected
        tap('target'+str(side))
        tap('shortcut'+str(side))
        check(f'Target selection retained, shortcut stays Not Set on side {side+1}', ctl.instrument.lasers[side].selected != old and item('shortcut'+str(side)).property('text')=='Not\nSet')
    tap('switch1')
    check('Independent channel switching retained', ctl.instrument.views==[0,0])
    tap('switch1')

    for side, bottom, module, field in [(0,False,'TC','temperature'),(1,False,'CC','feedforward'),(0,True,'PC','offset'),(1,True,'TC','pid')]:
        prefix=('bottom' if bottom else 'top')+'Parameter'+str(side)
        tap(prefix+'Module')
        if side==0 and not bottom:shot('03-control-panels')
        tap('module'+module)
        if field=='offset':shot('04-piezo-fields')
        tap('field'+field)
        check(f'{prefix} selects {field}', ctl.channel(side)['bottom' if bottom else 'top']==field and not item('selector').isVisible())
        tap(prefix+'Value')
        check(f'{prefix} numeric editor follows selected field', item('keypad').property('fieldKey')==field and item('keypad').property('channelIndex')==side)
        tap('keyCancel')
    ctl.selectField(0,False,'current');ctl.selectField(1,False,'temperature');ctl.selectField(0,True,'umax')
    for button,side,key,digits,expected in [('topParameter0Value',0,'current','240',240.),('topParameter1Value',1,'temperature','25',25.),('bottomParameter0Value',0,'umax','3',3.),('bottomParameter1Value',1,'pid','2',2.)]:
        tap(button)
        for d in digits:tap('key'+d)
        tap('keyEnter')
        check(f'v1 numeric edit applies {key}', ctl.instrument.lasers[side].values[key]==expected and not item('keypad').isVisible())
    tap('topParameter0Value')
    pad=item('keypad');editor=item('keypadDraft')
    pad.setProperty('draft','1234');pad.setProperty('cursor',2);pad.setProperty('replaceDraft',False)
    tap('key9')
    check('Numpad inserts at visible cursor',pad.property('draft')=='12934' and pad.property('cursor')==3)
    tap('keyBackspace')
    check('Numpad backspace preserves cursor position',pad.property('draft')=='1234' and pad.property('cursor')==2)
    tap('keyMinus')
    check('Numpad sign change preserves cursor position',pad.property('draft')=='-1234' and pad.property('cursor')==3)
    check('Numpad uses focused native blinking cursor',editor.property('activeFocus') and editor.property('cursorVisible') and app.cursorFlashTime()==1000)
    shot('05-numpad-cursor')
    tap('keyEnter')
    check('Invalid edit is rejected without changing accepted value',pad.isVisible() and ctl.instrument.lasers[0].values['current']==240.)
    tap('keyCancel')

    plot=item('absorption0Renderer')
    start=center('absorption0');old=plot.xMinimum
    QTest.mousePress(window,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,start)
    QTest.mouseMove(window,start+QPoint(70,10),40)
    QTest.mouseRelease(window,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,start+QPoint(70,10))
    QTest.qWait(100)
    check('Short drag still pans and synchronizes v1 graphs',plot.xMinimum!=old and abs(plot.xMinimum-item('error0Renderer').xMinimum)<1e-6 and not item('graphDrag').isVisible())
    plot.resetView()
    tap('fullscreen1')
    check('Right fullscreen still selects Laser 2',item('fullscreenAbsorptionRenderer').channelIndex==1)
    shot('06-fullscreen')
    tap('exitFullscreen')
    device=QTest.createTouchDevice()
    touch=QTest.touchEvent(window,device,False)
    a,b=QPoint(380,280),QPoint(530,280)
    touch.press(0,a,window).press(1,b,window).commit()
    for delta in (10,25,40,60):
        QTest.qWait(40)
        touch.move(0,a-QPoint(delta,0),window).move(1,b+QPoint(delta,0),window).commit()
    touch.release(0,a-QPoint(60,0),window).release(1,b+QPoint(60,0),window).commit()
    QTest.qWait(100)
    check('Native pinch retains v1 zoom',plot.xMaximum-plot.xMinimum<19)
    touch=QTest.touchEvent(window,device,False)
    touch.press(0,start,window).commit();QTest.qWait(750)
    check('Touch hold opens preserved drag skeleton',item('graphDrag').isVisible())
    end=QPoint(1180,350)
    touch.move(0,end,window).commit();QTest.qWait(100)
    shot('07-drag-drop')
    touch.release(0,end,window).commit();QTest.qWait(100)
    check('Drop swaps the entire channel assignment',ctl.instrument.views==[1,0])
    ctl.moveGraph(0,1)

    for side in (0,1):
        tap('more'+str(side));QTest.qWait(250)
        angle=math.radians(-100+1.5*36.25)
        p=QPoint(round((63 if side==0 else 1537)+(1 if side==0 else -1)*270*math.cos(angle)),round(539+270*math.sin(angle)))
        QTest.mouseClick(window,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,p)
        QTest.qWait(250)
        check(f'More Settings on side {side+1} opens supplied Frame 58',host.window.isVisible() and host.window.variant==58 and not window.isVisible())
        if side==0:
            host.window.grab().save(str(previews/'08-settings-frame58.png'))
            settings_action('search')
            w=host.window
            check('Search has focused native blinking cursor',w.search.hasFocus() and w.overlay=='keyboard')
            for letter in 'screen':settings_action('key',letter)
            check('Attached keyboard enters text once per key',w.search.text()=='screen')
            w.search.setSelection(0,6)
            settings_action('key','d')
            check('Virtual keyboard retains native text selection',w.search.text()=='d')
            w.search.setText('display')
            w.grab().save(str(previews/'09-search-keyboard.png'))
            settings_action('key','enter');QTest.qWait(700)
            check('Search navigates wheel and saves actual history',w.content=='display' and w.store.history[0]=='display')
            settings_action('history')
            settings_action('clear_history')
            check('History clear persists',json.loads(w.store.path.read_text(encoding='utf8'))['history']==[])
            w.close_overlay()
        host.window.close();QTest.qWait(100)
        check(f'Closing settings restores existing v1 home from side {side+1}',window.isVisible() and not host.window.isVisible() and ctl.instrument.views==[0,1])
    errors=[m for m in messages if any(k in m for k in ('TypeError','ReferenceError','Cannot assign','Binding loop','failed to load','Error:'))]
    check('No application QML errors',not errors)
    (ROOT/'tests'/'validation.json').write_text(json.dumps({'checks':checks,'count':len(checks),'warnings':messages,'hardware_tested':False},indent=2),encoding='utf8')
    print(f'{len(checks)} checks passed')
finally:
    host.shutdown();ctl.timer.stop();window.close()
    engine.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
    temporary.cleanup()
