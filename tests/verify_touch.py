"""Exercise event dispatch, scroll/slider distinction and custom keyboard input."""
import os, sys, tempfile, time, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tests'))
os.environ.setdefault('QT_QPA_PLATFORM','offscreen');os.environ.setdefault('QT_QUICK_BACKEND','software')
from PySide6.QtCore import Qt,QPoint,QPointF,QCoreApplication,QEvent
from PySide6.QtTest import QTest
from main import create_application
from verify_v17 import TestDevice

data=tempfile.TemporaryDirectory();device=TestDevice()
app,engine,ctl,home=create_application(skip_boot=True,data_dir=data.name,device=device)
sw=ctl.settings_host.window;system=ctl.system_settings;checks=[]
def check(name,ok):
    assert ok,name
    checks.append(name);print('PASS',name,flush=True)
def wait():
    end=time.monotonic()+5
    while system.busy and time.monotonic()<end:QTest.qWait(25)
    assert not system.busy
def pos(x,y):return QPoint(round(sw.offset.x()+x*sw.scale),round(sw.offset.y()+y*sw.scale))
def action(name):
    sw.repaint()
    return next((r,a) for r,a in sw.hits if a[:len(name)]==name)
def tap(name):
    r,a=action(name);p=pos(r.center().x(),r.center().y())
    QTest.mouseClick(sw,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,p);QTest.qWait(340)
def page(key):
    sw.select(sw.order.index(key));sw.motion.position=sw.selected;sw.last_index=sw.selected;QTest.qWait(350)
try:
    QTest.qWait(1600);ctl.openSettings();wait();page('display')
    tap(('choose_setting','Accent color'))
    check('Touch opens inline accent dropdown',sw.dropdown['key']=='accent' and sw.route=='')
    sw.drop_scroll=250;sw.repaint()
    tap(('dropdown_value','Blue'))
    check('Touch selection commits accent and returns',ctl.theme.get('accent')=='Blue' and sw.route=='')
    before=len(device.calls)
    QTest.mousePress(sw,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,pos(1250,228))
    QTest.mouseMove(sw,pos(1420,228),30);QTest.mouseMove(sw,pos(1460,228),30)
    check('Hardware slider preview does not repeatedly write',len(device.calls)==before)
    QTest.mouseRelease(sw,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,pos(1460,228));wait()
    check('Hardware slider commits once on release',len(device.calls)==before+1 and device.calls[-1][0]=='brightness' and device.brightness>70)
    page('system')
    QTest.mousePress(sw,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,pos(950,615))
    for y in (580,540,500,450,400):QTest.mouseMove(sw,pos(950,y),25)
    QTest.mouseRelease(sw,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,pos(950,400))
    check('Swipe scrolls content without opening a row',sw.scroll>150 and sw.route=='')
    old=sw.scroll;QTest.qWait(100);check('Content continues with inertia after release',sw.scroll>old)
    page('function');sw.scroll=350;sw.repaint();tap(('table',0,'number','X minimum'))
    tap(('inline_key','5'));tap(('inline_key','0'));tap(('inline_key','.'));tap(('inline_key','2'))
    check('Touch numeric keys replace selection exactly once',sw.editor.text()=='50.2')
    r,_=action(('inline_key','backspace'));p=pos(r.center().x(),r.center().y())
    QTest.mousePress(sw,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,p);QTest.qWait(740)
    QTest.mouseRelease(sw,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,p)
    check('Numeric hold backspace clears whole field',sw.editor.text()=='')
    tap(('inline_key','Cancel'));page('about');sw.open_search();QTest.qWait(100);sw.search.clear()
    touch=QTest.createTouchDevice()
    def finger(key,hold=50):
        r,_=action(('key',key));p=pos(r.center().x(),r.center().y())
        QTest.touchEvent(sw,touch).press(0,p,sw).commit();QTest.qWait(hold)
        QTest.touchEvent(sw,touch).release(0,p,sw).commit();QTest.qWait(80)
    finger('a');finger('b');finger('c')
    check('Native touch keyboard enters each letter once',sw.search.text()=='abc')
    finger('backspace');check('Short touch backspace removes one letter',sw.search.text()=='ab')
    finger('backspace',740);check('Touch hold backspace clears all search text',sw.search.text()=='')
    sw.search.setFocus();QTest.keyClicks(sw.search,'graph')
    check('Physical keyboard also enters once',sw.search.text()=='graph')
    QTest.mouseClick(sw,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,pos(50,50));QTest.qWait(100)
    check('Tap dim area closes keyboard and saves history',not sw.overlay and sw.store.history[0]=='graph')
    tap(('history',));check('History icon opens actual query list',sw.overlay=='history')
    tap(('clear_history',));check('History clear is reachable by touch',sw.store.history==[])
    sw.close_overlay();ctl.theme.apply('language','Français');ctl.theme.apply('appearance','Light')
    ctl.theme.apply('font_scale',1.2);ctl.theme.apply('ui_scale',1.2);page('help');tap(('page_nav','help:Graphs'))
    out=ROOT/'tests/v17-screenshots';out.mkdir(exist_ok=True)
    sw.grab().save(str(out/'16-large-french-help.png'))
    check('Large translated help remains scrollable',sw.content_height>487 and ctl.theme.trText('Graphs')!='Graphs')
    page('display');sw.grab().save(str(out/'17-large-display.png'))
    (ROOT/'tests/v17-touch-validation.json').write_text(json.dumps(checks,indent=2),encoding='utf8')
    print(len(checks),'checks passed')
finally:
    system.shutdown();ctl.settings_host.shutdown();ctl.timer.stop();home.close();engine.deleteLater()
    QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);data.cleanup()
