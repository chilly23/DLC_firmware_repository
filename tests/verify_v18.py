"""End-to-end commands against real QML/widgets; isolated display and data."""
import os,sys,tempfile,time,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
os.environ['QT_QPA_PLATFORM']='offscreen';os.environ['QT_QUICK_BACKEND']='software'
from PySide6.QtCore import QCoreApplication,QEvent,QPoint,QPointF,Qt,qInstallMessageHandler
from PySide6.QtTest import QTest
from main import create_application
from verify_v17 import TestDevice
from hardware.config import ControlStore
from settings_ui.tour import TOUR
from settings_ui.model import SettingsStore
messages=[];qInstallMessageHandler(lambda t,c,m:messages.append(m))
tmp=tempfile.TemporaryDirectory();dev=TestDevice()
app,engine,ctl,w=create_application(skip_boot=True,animate=False,data_dir=tmp.name,device=dev,gpio_autostart=False)
nav=ctl.navigation;knobs=ctl.knobs;sw=ctl.settings_host.window;system=ctl.system_settings;checks=[]
out=ROOT/'tests/v18-screenshots';out.mkdir(exist_ok=True)
def check(name,condition):
    assert condition,name
    checks.append(name);print('PASS',name,flush=True)
def item(name):return nav.find(name)
def command(index,action,amount=1):knobs.command.emit(index,action,amount);QTest.qWait(50)
def page(key):
    sw.select(sw.order.index(key));sw.motion.position=sw.selected;sw.motion.target=None;sw.last_index=sw.selected;QTest.qWait(80);sw.repaint()
def find_hit(prefix):
    sw.repaint();return next((r,a) for r,a in reversed(sw.hits) if a[:len(prefix)]==prefix)
def tap(prefix):
    r,a=find_hit(prefix);p=QPoint(round(sw.offset.x()+r.center().x()*sw.scale),round(sw.offset.y()+r.center().y()*sw.scale))
    QTest.mouseClick(sw,Qt.LeftButton,Qt.NoModifier,p);QTest.qWait(90)
def finish_jobs():
    end=time.monotonic()+6
    while system.busy and time.monotonic()<end:QTest.qWait(20)
    assert not system.busy
try:
    QTest.qWait(250);check('v1.11 loads without GPIO dependency on desktop',w.isVisible() and app.applicationVersion()=='1.11.0')
    check('Default home values are white',ctl.theme.parameterInk.upper()=='#FFFFFF')
    ctl.theme.apply('accent','Cyan');check('Light accents use dark numeric ink',ctl.theme.parameterInk.upper()=='#111111');ctl.theme.apply('accent','Green')
    check('Earlier Green is restored exactly',ctl.theme.accent.upper()=='#008622')
    for accent,expected in [('Green','#ffffff'),('Orange','#ffffff'),('Cyan','#111111')]:
        ctl.theme.apply('accent',accent);QTest.qWait(40)
        foreground=[]
        for name in ('topParameter0','bottomParameter0','topParameter1','bottomParameter1'):
            stack=list(item(name).childItems())
            while stack:
                obj=stack.pop();stack.extend(obj.childItems())
                if obj.property('text') is not None:foreground.append(obj.property('color').name())
                elif obj.property('ink') is not None:foreground.append(obj.property('ink').name())
        check('Every corner label, unit, value and icon uses consistent '+accent+' ink',len(foreground)==20 and all(c==expected for c in foreground))
    ctl.theme.apply('accent','Green')
    check('Knob 3 disabled and Knob 4 targets bottom right',not knobs.knobs[2]['enabled'] and knobs.knobs[3]['enabled'] and knobs.knobs[3]['target']==3)
    before=ctl.value(0,'current');command(0,'value.increase');check('Rotation updates top-left real parameter',round(ctl.value(0,'current')-before,3)==.001)
    command(0,'cursor.left',1);command(0,'value.increase');check('Cursor chooses next decimal digit',round(ctl.value(0,'current')-before,3)==.011)
    check('Selected digit underline is visible',nav.editCorner==0 and nav.powerFor(0)==-2)
    ctl.selectField(0,False,'umax');nav._power[0]=-3;command(0,'value.increase')
    check('Changing field clamps digit precision',ctl.value(0,'umax')==2.82 and nav.powerFor(0)==-2);ctl.selectField(0,False,'current')
    knobs.set_target(3,2);command(3,'value.increase');check('Knob 4 can target the top-right laser independently',ctl.value(1,'temperature')==24.001);knobs.set_target(3,3)
    ctl.switchView(0);command(0,'value.increase');check('Corner assignment follows displayed laser',ctl.value(1,'temperature')==24.011);ctl.switchView(0)
    command(0,'editor.open');pad=item('keypad');accepted=ctl.value(0,'current')
    command(0,'value.increase');check('Rotation edits active numpad draft',round(float(pad.property('draft'))-accepted,3)==.001 and ctl.value(0,'current')==accepted)
    pad.key('enter');check('Numpad Apply validates and commits',round(ctl.value(0,'current')-accepted,3)==.001)
    renderer=item('absorption0Renderer');renderer.setRange(51.,64.);old=renderer.xMinimum
    command(1,'graph.left');check('Joystick left moves the trace left',renderer.xMinimum>old)
    old_y=ctl.instrument.lasers[0].chart.axes['main_position'];command(1,'graph.up')
    check('Joystick up moves the trace up',ctl.instrument.lasers[0].chart.axes['main_position']<old_y)
    width=renderer.xMaximum-renderer.xMinimum;command(1,'graph.zoom_in');check('Knob zoom updates graph range',renderer.xMaximum-renderer.xMinimum<width)
    command(0,'graph.lock');old=renderer.xMinimum;command(1,'graph.left');check('Lock blocks knob pan',renderer.xMinimum==old);command(0,'graph.lock')
    command(0,'view.fullscreen');full=item('fullscreenAbsorptionRenderer');old=full.xMaximum-full.xMinimum
    command(0,'graph.zoom_in');check('Fullscreen knob zoom works',full.xMaximum-full.xMinimum<old);command(0,'view.fullscreen')
    command(3,'view.fullscreen');command(1,'graph.left');check('Graph shortcut reveals its assigned fullscreen side',w.property('fullscreenSide')==0);command(0,'view.fullscreen')
    command(1,'more.open');QTest.qWait(780)
    radial=item('radialMenu');knobs.dispatch(1,'clockwise',2);QTest.qWait(250)
    check('More wheel rotates to Alarms',radial.property('selectedIndex')==2)
    knobs.dispatch(1,'push');QTest.qWait(780)
    check('Physical activation opens real alarm panel',item('alarmPanel').isVisible());nav.back()
    command(0,'signals.open');check('Chart Signals opens by shortcut',item('signalsPanel').isVisible())
    nav.target=item('signalsCombined');
    if nav.target:nav.activate()
    nav.back();w.dismissKnobPanel()
    command(0,'settings.open');finish_jobs();page('control')
    from PySide6.QtCore import QRectF
    sw.knob_focus=(QRectF(15,306,577,108),('knob_menu',));sw.activate_knob();origin=sw.motion.position
    for _ in range(5):sw.navigate_knob(1)
    check('Fast rotation accumulates Settings wheel steps',sw.motion.target==origin+5)
    sw.back_knob();page('control')
    check('Control home has three configure buttons',sum(a[0]=='knob_open' for r,a in sw.hits)==3)
    tap(('knob_open',0));check('Configure opens own knob page',sw.route=='knob:0')
    QTest.qWait(350);sw.scroll=220;sw.repaint();tap(('choose_setting','Rotate clockwise'))
    for _ in range(30):sw.navigate_knob(1)
    check('Knob focus scrolls through every mapping option',sw.drop_scroll>0 and sw.knob_focus[1][0]=='dropdown_value')
    sw.knob_focus=(sw.drop_rect,('dropdown_value','graph.zoom_in'));sw.activate_knob()
    check('Mapping persists on selection',ControlStore(Path(tmp.name)/'controls.json').config['knobs'][0]['mapping']['clockwise']=='graph.zoom_in')
    sw.controls.restore_mapping(0);sw.back();page('display')
    # Hardware changes are previewed during adjustment and committed once.
    sw.knob_focus=find_hit(('hardware_slider','brightness'));sw.activate_knob();count=len(dev.calls)
    sw.navigate_knob(-1,10);check('Knob hardware slider has no writes while turning',len(dev.calls)==count and sw.display_preview['brightness']==60)
    sw.activate_knob();finish_jobs();check('Finishing slider sends one hardware write',dev.calls[count:]==[('brightness',60)] and system.caps['brightness']==60)
    sw.open_search();sw.repaint();keys=[a for r,a in sw.navigation_hits()];check('Keyboard is navigable without touch',('key','q') in keys and ('key','enter') in keys)
    sw.knob_focus=next((r,a) for r,a in sw.navigation_hits() if a==('key','q'));sw.activate_knob();check('One knob press types one character',sw.search.text()=='q')
    sw.close_overlay();sw.activate(('history',));check('History persists real keyboard query',sw.store.history[0]=='q');sw.activate(('clear_history',));check('Clear history persists',not SettingsStore(sw.store.path).history);sw.close_overlay()
    page('control');tap(('screen_check',));sc=sw.screen_test;touch=QTest.createTouchDevice()
    for pos in sc.targets:
        p=pos.toPoint();QTest.touchEvent(sc,touch).press(0,p,sc).commit();QTest.qWait(20);QTest.touchEvent(sc,touch).release(0,p,sc).commit();QTest.qWait(20)
    check('Native touch covers four diagnostic corners',sc.checks['corners']);sc.advance()
    points=sc.trace_points;QTest.touchEvent(sc,touch).press(0,points[0].toPoint(),sc).commit()
    for pos in points[1:]:QTest.touchEvent(sc,touch).move(0,pos.toPoint(),sc).commit();QTest.qWait(25)
    QTest.touchEvent(sc,touch).release(0,points[-1].toPoint(),sc).commit();check('Continuous native touch trace completes',sc.checks['trace'])
    sc.advance();QTest.touchEvent(sc,touch).press(0,sc.puck.toPoint(),sc).commit()
    for pos in sc.targets:QTest.touchEvent(sc,touch).move(0,pos.toPoint(),sc).commit();QTest.qWait(25)
    QTest.touchEvent(sc,touch).release(0,sc.targets[-1].toPoint(),sc).commit();check('Native touch drag hits all targets',sc.checks['drag']);sc.close()
    check('Screen result returns to Control Settings',all(sw.touch_results.values()) and sw.isVisible())
    tap(('panel_open',));sw.scroll=300;sw.repaint();tap(('settings_action','knob_guide'));check('Knob guide starts paused with focused content',system.tour.get('knob_intro') and not system.tourPlaying)
    for _ in range(11):system.tourNext();QTest.qWait(30);sw.repaint()
    check('Knob guide covers mapping, calibration and screen check','Check touchscreen' in system.tour['title']);system.stopTour()
    check('Guide has detailed control coverage',len(TOUR)>=85)
    # Inspect calibration UI with explicitly injected electrical observations.
    from hardware.calibration import Calibration
    from hardware.config import CONTACTS
    knobs.calibration=Calibration(0,knobs.store.config['knobs'][0]);knobs.snapshots[0]=dict(levels=dict.fromkeys(('encoder_a','encoder_b',*CONTACTS),1),count=0)
    page('control');knobs.calibration=Calibration(0,knobs.store.config['knobs'][0]);sw.navigate('calibrate:0');QTest.qWait(350);sw.repaint();sw.grab().save(str(out/'calibration.png'))
    check('Calibration UI shows capture action',any(a[0]=='calibration_next' for r,a in sw.hits));sw.back();check('Leaving calibration discards incomplete changes',knobs.calibration is None and not knobs.store.config['knobs'][0]['calibrated'])
    errors=[m for m in messages if any(x in m for x in ('TypeError','AttributeError','ReferenceError','Cannot assign','Unable to assign','Binding loop','failed to load','Error:'))]
    check('No Qt or QML runtime errors',not errors)
    (ROOT/'tests/v18-validation.json').write_text(json.dumps(dict(checks=checks,qt_messages=messages,physical_pi_tested=False),indent=2),encoding='utf8')
    print(len(checks),'checks passed')
finally:
    print('\n'.join(messages));knobs.shutdown();nav.shutdown();system.shutdown();ctl.settings_host.shutdown();ctl.timer.stop();w.close();engine.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);tmp.cleanup()
