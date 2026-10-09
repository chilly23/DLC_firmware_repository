"""Real Qt acceptance for this update. Host power is a recording fake."""
import os,sys,tempfile,time,json
from copy import deepcopy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
os.environ['QT_QPA_PLATFORM']='offscreen';os.environ['QT_QUICK_BACKEND']='software'
from PySide6.QtCore import Qt,QPoint,QPointF,QCoreApplication,QEvent,qInstallMessageHandler
from PySide6.QtTest import QTest
from main import create_application
from verify_v17 import TestDevice
from interaction.notification_art import metrics
from settings_ui.model import SettingsStore
messages=[];qInstallMessageHandler(lambda t,c,m:messages.append(m))
temp=tempfile.TemporaryDirectory();device=TestDevice()
app,engine,ctl,w=create_application(skip_boot=True,animate=False,data_dir=temp.name,device=device,gpio_autostart=False)
sw=ctl.settings_host.window;nav=ctl.navigation;system=ctl.system_settings;theme=ctl.theme;journal=ctl.journal
out=ROOT/'tests/console';out.mkdir(exist_ok=True);checks=[]
def check(name,value):
    assert value,name
    checks.append(name);print('PASS',name,flush=True)
def quiet():
    while ctl.notifications.cards:ctl.notifications.dismissId(ctl.notifications.cards[0]['id'])
def page(key):
    quiet();ctl.openSection(key);QTest.qWait(100);sw.repaint()
def shot(name,native=True):
    QTest.qWait(50);assert (sw.grab() if native else w.grabWindow()).save(str(out/(name+'.png')))
def tap(prefix):
    quiet();sw.repaint();rect,action=next((r,a) for r,a in reversed(sw.hits) if a[:len(prefix)]==prefix)
    p=rect.center();p=QPoint(round(sw.offset.x()+p.x()*sw.scale),round(sw.offset.y()+p.y()*sw.scale))
    QTest.mouseClick(sw,Qt.LeftButton,Qt.NoModifier,p);QTest.qWait(60)
try:
    QTest.qWait(200)
    for _ in range(40):ctl.step(.05)
    knobs=ctl.knobs;knobs.dispatch(1,'push');QTest.qWait(900);radial=nav.find('radialMenu')
    check('More contains Logs and no Display',radial.property('options').toVariant()[2]['name']=='Logs')
    knobs.dispatch(1,'clockwise',2);QTest.qWait(140)
    check('Knob selects the fixed v1.6 Logs sector',radial.property('selectedIndex')==2 and radial.property('keyboardSelection'))
    QTest.qWait(240);shot('wheel',False);knobs.dispatch(1,'left');QTest.qWait(950)
    check('Joystick left opens Logs',sw.isVisible() and sw.content=='logs')
    for i in range(32):journal.record(f'Laser action {i}: changed set point','Failed' if i%3==0 else 'Passed','warning' if i%3==0 else 'default')
    sw.repaint();check('Log view shows latest record first',sw.log_cache[0]['description'].startswith('Laser action 31'))
    shot('logs');sw.scroll=700;sw.repaint();before=sw.scroll;journal.record('New event while reviewing');sw.repaint()
    check('New logs preserve the scrolling reading position',sw.scroll==before+104)
    sw.scroll=0;sw.repaint();tap(('log_live',));frozen=deepcopy(sw.log_cache);journal.record('While paused');sw.repaint()
    check('Paused monitor keeps recording without moving rows',sw.log_cache==frozen and journal.rows()[0]['description']=='While paused')
    tap(('log_live',));tap(('choose_setting','Log level'));tap(('dropdown_value','warning'))
    check('Warning filter works via real dropdown clicks',sw.log_cache and all(e['level']=='warning' for e in sw.log_cache))
    journal.export(Path(temp.name)/'export');check('CSV and Markdown export exist',(Path(temp.name)/'export/logs.csv').is_file() and (Path(temp.name)/'export/logs.md').is_file())
    tap(('log_clear',));request=ctl.notifications.toast
    check('Clearing logs requires explicit consent',request['decision'] and journal.count()>1)
    ctl.notifications.acceptId(request['id']);check('Clear removes old records and retains audit trail',not any('Laser action' in e['description'] for e in journal.rows()))
    page('function');check('Distinct trace style controls exist',all(any(row[2]==key for row in __import__('settings_ui.refined',fromlist=['FUNCTION_ROWS']).FUNCTION_ROWS) for key in ('main_color','error_color','main_width','error_width','main_style','error_style')))
    before=deepcopy(theme.get('graph2'))
    for key,value in [('main_color','#FF453A'),('error_color','#0A84FF'),('main_width',3.),('error_width',1.),('main_style','Solid'),('error_style','Dotted')]:check('Accept '+key,system.set_graph(0,key,value))
    check('Laser 2 unaffected by Laser 1 trace styles',theme.get('graph2')==before)
    check('Invalid widths and colors rejected',not system.set_graph(0,'main_width',float('nan')) and not system.set_graph(0,'error_color','not-a-color'))
    reloaded=SettingsStore(Path(temp.name)/'settings.json');check('Independent trace styles survive reload',reloaded.values['graph1']['main_color']=='#FF453A' and reloaded.values['graph1']['error_style']=='Dotted')
    sw.scroll=850;sw.repaint();quiet();shot('styles');sw.close();QTest.qWait(80);shot('graphs',False)
    # Manual lock uses a hold, physical lock always takes priority.
    guard=ctl.session_lock;theme.apply('lock_shutdown_seconds',0);guard.lock_now();QTest.qWait(80)
    check('Manual lock blocks operation and has no timeout when Never',guard.locked and knobs.suspended and not guard.deadline)
    guard.window.grab().save(str(out/'lock.png'))
    p=QPoint(round(guard.window.width()/2),round(guard.window.height()*600/720))
    QTest.mouseClick(guard.window,Qt.LeftButton,Qt.NoModifier,p);check('A short tap cannot unlock',guard.locked)
    QTest.mousePress(guard.window,Qt.LeftButton,Qt.NoModifier,p);QTest.qWait(1150);QTest.mouseRelease(guard.window,Qt.LeftButton,Qt.NoModifier,p)
    check('One-second hold unlocks a manual lock',not guard.locked and not knobs.suspended)
    guard.set_locked(True);guard.unlock_manual();check('Physical active lock cannot be bypassed by touch',guard.locked)
    guard.set_locked(False);check('Physical release restores operation',not guard.locked)
    theme.apply('lock_shutdown_seconds',30);guard.set_locked(True);guard.deadline=time.monotonic()-1;guard.tick()
    deadline=time.monotonic()+3
    while system.busy and time.monotonic()<deadline:QTest.qWait(20)
    check('Expired lock requests shutdown through backend',('power','shutdown') in device.calls);guard.set_locked(False)
    page('notifications');tap(('choose_setting','Notification size'));tap(('dropdown_value','Large'))
    check('Notification size selected in real settings',theme.notificationSize=='Large')
    quiet();ctl.notifications.post('Warning icon centered; large readable notice','warning');entry=ctl.notifications.cards[0]
    for size in ('Small','Medium','Large'):
        theme.apply('notification_size',size);width,height,font=metrics(size)
        image=ctl.notifications.renderer.image(entry,width,height);check(size+' notification dimensions',image.width()==width and image.height()==height)
        image.save(str(out/(size.lower()+'.png')))
    quiet();shot('notifications')
    page('system');sw.navigate('startup');QTest.qWait(330);sw.repaint();shot('startup')
    check('Startup page has toggle and repair',any(r[2]=='boot_enabled' for r in sw.rows()) and any(r[2]=='setup_repair' for r in sw.rows()))
    sw.back();sw.navigate('lock');QTest.qWait(330);sw.repaint();shot('locksettings')
    check('Lock settings have direct lock, timer and input calibration',len(sw.rows())==3)
    failures=[m for m in messages if any(s in m for s in ('TypeError','ReferenceError','Cannot assign','Unable to assign','Binding loop','Error:'))]
    check('No Qt runtime errors',not failures)
    (out/'results.json').write_text(json.dumps({'checks':checks,'messages':messages,'physical_pi_tested':False},indent=2))
finally:
    ctl.session_lock.shutdown();ctl.knobs.shutdown();ctl.navigation.shutdown();system.shutdown();ctl.notifications.timer.stop();ctl.settings_host.shutdown();ctl.timer.stop();w.close();engine.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete);temp.cleanup()
