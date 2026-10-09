"""Behavior checks for v1.6 using the actual Qt scene and native touch events."""
import os,sys,json,tempfile,time,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('QT_QUICK_BACKEND','software')
from PySide6.QtCore import QObject,QPoint,QPointF,QCoreApplication,QEvent,Qt,qInstallMessageHandler
from PySide6.QtGui import QMouseEvent,QImage
from PySide6.QtTest import QTest
from main import create_application
from controller.plot import axis_label
from settings_ui.layout import KEYBOARD_RECT,KEYBOARD_INPUT_RECT,INPUT_RECT
from settings_ui.model import SettingsStore
messages=[]
qInstallMessageHandler(lambda kind,context,message:messages.append(message))
temporary=tempfile.TemporaryDirectory()
app,engine,ctl,w=create_application(skip_boot=True,animate=True,data_dir=temporary.name)
checks=[];out=ROOT/'tests'/'screenshots';out.mkdir(exist_ok=True)
def check(name,condition):
    assert condition,name
    checks.append(name);print('PASS',name,flush=True)
def item(name):
    stack=[w.contentItem()]
    while stack:
        obj=stack.pop()
        if obj.objectName()==name:return obj
        stack.extend(obj.childItems())
    raise AssertionError('Missing '+name)
def center(name):
    obj=item(name);return obj.mapToScene(QPointF(obj.width()/2,obj.height()/2)).toPoint()
def tap(name):
    QTest.mouseClick(w,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,center(name));QTest.qWait(80)
def shot(name,widget=None):
    QTest.qWait(80)
    image=widget.grab() if widget else w.grabWindow()
    assert image.save(str(out/(name+'.png')))
def action(kind,value=None,touch=False):
    sw.repaint()
    for rect,a in sw.hits:
        if a[0]==kind and (value is None or a[1]==value):
            point=(rect.center()*sw.scale+sw.offset).toPoint()
            if touch:
                QTest.touchEvent(sw,device).press(0,point,sw)
                QTest.touchEvent(sw,device).release(0,point,sw)
            else:QTest.mouseClick(sw,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,point)
            QTest.qWait(40);return point
    raise AssertionError(f'Missing {kind} {value}')
device=QTest.createTouchDevice()
try:
    QTest.qWait(1800);shot('01-home')
    tap('chartLabels0');surface=item('signalsSurface');scrim=item('signalsScrim')
    check('Left chart panel is centred in right half',surface.x()==830 and surface.y()==60 and surface.width()==740 and surface.height()==600)
    check('Only opposite half is dimmed',scrim.x()==800 and scrim.width()==800 and scrim.height()==720 and scrim.opacity()>.7)
    check('Signal selection uses home active white',item('tabSplit').property('normalColor').name()==item('emission0').property('normalColor').name())
    shot('02-signals-centred');tap('signalsClose');tap('chartLabels1')
    check('Right chart panel and dim mask mirror correctly',surface.x()==30 and scrim.x()==0)
    tap('signalsClose');tap('emission0');QTest.qWait(1800)
    check('Idle graph and controls fade',abs(item('charts0').opacity()-.48)<.01 and abs(item('lock0').opacity()-.48)<.01 and abs(item('more0').opacity()-.48)<.01)
    check('Idle status becomes grey',item('channelStatus0').property('color').name()=='#7e877f')
    check('Emission button and green readouts stay undimmed',item('emission0').opacity()==1 and item('topParameter0').opacity()==1 and item('bottomParameter0').opacity()==1 and item('topParameter0').property('color').name()=='#008622')
    check('Idle traces remain exact zero',ctl.instrument.lasers[0].sample(53,0)==(0.,0.))
    shot('03-idle');tap('emission0');QTest.qWait(800)
    check('Re-enabling restores normal brightness',item('charts0').opacity()==1 and item('lock0').opacity()==1)
    radial=item('radialMenu');frames=[]
    def record():
        if radial.property('animating'):frames.append(time.perf_counter())
    w.frameSwapped.connect(record)
    tap('more0');values=[]
    for _ in range(90):
        values.append(radial.property('expansion'));QTest.qWait(10)
    w.frameSwapped.disconnect(record)
    check('Radial reveal is monotonic and completes',values==sorted(values) and values[-1]==1 and not radial.property('animating'))
    check('Radial reveal has many intermediate frames over 800ms',radial.property('transitionMs')==800 and len(set(v for v in values if 0<v<1))>20)
    check('Live acquisition and chart refresh resume after reveal',ctl.elapsed>0 and not ctl.presentation_busy)
    check('Radial artwork is cached for animation',item('radialFan').width()==720 and item('radialFan').scale()==1)
    shot('04-radial');tap('radialCancel')
    retract=[]
    for _ in range(90):
        retract.append(radial.property('expansion'));QTest.qWait(10)
    check('Closing visibly retracts before hiding',retract==sorted(retract,reverse=True) and len(set(v for v in retract if 0<v<1))>20 and not radial.isVisible())
    tap('more1');QTest.qWait(850);check('Radial menu reopens on opposite side',radial.property('side')==1 and radial.property('expansion')==1);tap('radialCancel');QTest.qWait(850)
    tap('more0');QTest.qWait(160);tap('radialCancel');QTest.qWait(850)
    check('Cancelling during expansion finishes cleanly',not radial.isVisible() and not ctl.presentation_busy)
    tap('more0');QTest.qWait(850)
    QTest.mouseClick(w,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,QPoint(147,282));QTest.qWait(180)
    check('Choosing Signals retracts menu before opening the panel',radial.isVisible() and radial.property('closing') and 0<radial.property('expansion')<1 and not item('signalsPanel').isVisible())
    QTest.qWait(800)
    check('Deferred radial action opens the correct Signals panel',not radial.isVisible() and item('signalsPanel').isVisible() and item('signalsPanel').property('side')==0 and not ctl.presentation_busy)
    tap('signalsClose')
    check('Axis labels never exceed two decimals or use scientific notation',all('e' not in axis_label(n).lower() and ('.' not in axis_label(n) or len(axis_label(n).split('.')[1])<=2) for n in [0,-.0001,1.234567,-18.88888,1200,48.236475]))
    check('Axis formatting removes negative zero',axis_label(-.001)=='0')
    plot=item('absorption0Renderer');plot.pan(12.345,15.678);plot.zoom(1.2345,345);shot('05-axis-labels');plot.resetView()
    for factor in [1,10,.01]:
        plot.zoom(factor,345)
        for direction in [-1,1]:
            plot.pan(direction*1e6,direction*1e6)
            lo,hi=plot.xMinimum,plot.xMaximum
            check(f'Pan retains acquired X domain at zoom {factor} direction {direction}',lo<68.2 and hi>48.2)
            a,b=max(48.2,lo),min(68.2,hi)
            samples=[ctl.instrument.lasers[0].signal.sample(a+(b-a)*i/256)[0] for i in range(257)]
            bottom,top=ctl.instrument.lasers[0].chart.bounds(False)
            check(f'Pan retains visible trace at zoom {factor} direction {direction}',min(samples)<top and max(samples)>bottom)
    plot.resetView()
    tap('topParameter0');tap('key1');tap('key2');tap('key3');tap('keyBackspace')
    check('Short numeric backspace deletes one character',item('keypadDraft').property('text')=='12')
    p=center('keyBackspace');QTest.touchEvent(w,device).press(0,p,w);QTest.qWait(100)
    check('Native touch press reaches numeric backspace',item('keyBackspacePointer').property('pressed'))
    QTest.qWait(800)
    check('Holding numeric backspace clears input before release',item('keypadDraft').property('text')=='')
    QTest.touchEvent(w,device).release(0,p,w);QTest.qWait(80);tap('keyCancel')
    icon=QImage(str(ROOT/'assets'/'dragndrop-white.png'))
    check('Supplied drag artwork is present and transparent',not icon.isNull() and icon.hasAlphaChannel())
    original=ROOT.parent.parent/'Nexatom - Copy'/'settings panel'/'dragndrop-white.png'
    if original.exists():check('Drag artwork is the unmodified supplied image',hashlib.sha256(original.read_bytes()).digest()==hashlib.sha256((ROOT/'assets'/'dragndrop-white.png').read_bytes()).digest())
    start=center('absorption0');QTest.mousePress(w,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,start);QTest.qWait(650)
    check('Drag targets use the supplied image',item('dropArtwork').property('source').toString().endswith('dragndrop-white.png'))
    shot('06-drag-artwork');QTest.mouseRelease(w,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,QPoint(400,30));QTest.qWait(80)
    ctl.openSettings();QTest.qWait(180);sw=ctl.settings_host.window
    check('Settings retains Frame 58 wheel',sw.variant==58 and sw.isVisible())
    check('Settings has no native window outline',bool(sw.windowFlags() & Qt.WindowType.FramelessWindowHint))
    check('Settings close button is top right',next(r for r,a in sw.hits if a==('close',)).x()==1501)
    check('Settings wheel now uses top and bottom of screen',min(r.center().y() for r,_ in sw.menu_hits)<100 and max(r.center().y() for r,_ in sw.menu_hits)>650)
    shot('07-settings-full-height',sw)
    action('search')
    check('Letter keyboard is bottom centred at 65% width',KEYBOARD_RECT.width()==1040 and KEYBOARD_RECT.center().x()==800 and KEYBOARD_RECT.bottom()==700)
    check('Native input moves into custom keyboard header',sw.search.geometry().x()==332 and sw.search.geometry().y()==307 and sw.search.hasFocus())
    check('Search uses the same Roboto family as the app',sw.search.font().family()=='Roboto' and app.font().family()=='Roboto')
    keys={a[1] for _,a in sw.hits if a[0]=='key'}
    check('Keyboard contains all letters without numeric mode or suggestions',set('abcdefghijklmnopqrstuvwxyz').issubset(keys) and not any(k.isdigit() for k in keys) and 'mode' not in keys and not any(a[0]=='suggest' for _,a in sw.hits))
    shot('08-custom-keyboard',sw)
    p=action('key','a',touch=True);fp=QPointF(p)
    for kind,buttons in [(QEvent.Type.MouseButtonPress,Qt.MouseButton.LeftButton),(QEvent.Type.MouseButtonRelease,Qt.MouseButton.NoButton)]:
        QCoreApplication.sendEvent(sw,QMouseEvent(kind,fp,fp,QPointF(sw.mapToGlobal(p)),Qt.MouseButton.LeftButton,buttons,Qt.KeyboardModifier.NoModifier,Qt.MouseEventSource.MouseEventSynthesizedByQt))
    check('Touch plus compatibility mouse enters once',sw.search.text()=='a')
    action('key','a');action('key','a');check('Fast repeated letters are not dropped',sw.search.text()=='aaa')
    sw.search.selectAll();action('key','d');action('key','shift');action('key','a')
    check('Selection replacement and shift work',sw.search.text()=='dA')
    action('key','left');action('key','x');check('Caret movement and insertion work',sw.search.text()=='dxA')
    action('key','backspace');action('key','right');action('key','space');check('Backspace and space work',sw.search.text()=='dA ')
    QTest.keyClicks(sw.search,'z');check('Physical keyboard still enters once',sw.search.text()=='dA z')
    selected=sw.selected;QTest.mouseClick(sw,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,QPoint(180,180));QTest.qWait(80)
    check('Tapping dim background closes keyboard without activating underlying settings',sw.overlay is None and sw.selected==selected and not sw.search.hasFocus())
    check('Search editor returns to search bar after dismissal',sw.search.geometry().x()==round(INPUT_RECT.x()))
    action('search');sw.search.selectAll()
    for letter in 'display':action('key',letter)
    action('key','enter');QTest.qWait(650)
    check('Custom return and keyboard dismissal save actual search history',sw.content=='display' and sw.store.history==['display','dA z'] and sw.overlay is None)
    action('history');check('History viewer remains functional',sw.overlay=='history')
    check('History survives reopening its store',SettingsStore(sw.store.path).history==['display','dA z'])
    shot('09-history',sw)
    action('clear_history');check('Clear history persists',SettingsStore(sw.store.path).history==[])
    sw.close_overlay();action('search');sw.search.setText('clear this entire search')
    sw.repaint();r=next(r for r,a in sw.hits if a==('key','backspace'));p=(r.center()*sw.scale+sw.offset).toPoint()
    QTest.touchEvent(sw,device).press(0,p,sw);QTest.qWait(750)
    check('Holding search backspace clears entire input before release',sw.search.text()=='')
    QTest.touchEvent(sw,device).release(0,p,sw);QTest.qWait(80)
    sw.close_overlay();action('history')
    check('Cleared history stays empty after empty search dismissal',sw.store.history==[])
    sw.close_overlay();sw.close();QTest.qWait(100)
    check('Closing settings restores home',w.isVisible())
    errors=[m for m in messages if any(k in m for k in ('TypeError','ReferenceError','Cannot assign','Unable to assign','Binding loop','failed to load','Error:'))]
    check('No Qt/QML errors',not errors)
    gaps=[round((b-a)*1000,2) for a,b in zip(frames,frames[1:])]
    (ROOT/'tests'/'validation.json').write_text(json.dumps({'checks':checks,'warnings':messages,'radial_frame_gaps_ms':gaps,'physical_touchscreen_tested':False},indent=2),encoding='utf8')
    print(f'{len(checks)} checks passed',flush=True)
finally:
    print('\n'.join(messages),flush=True)
    ctl.settings_host.shutdown();ctl.timer.stop();w.close();engine.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);temporary.cleanup()
