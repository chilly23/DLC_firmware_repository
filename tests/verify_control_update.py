"""Real Qt input paths with a recording power/display backend; no host shutdown."""
import os,sys,tempfile,time,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
os.environ['QT_QPA_PLATFORM']='offscreen';os.environ['QT_QUICK_BACKEND']='software'
from PySide6.QtCore import QPoint,QPointF,Qt,QCoreApplication,QEvent,qInstallMessageHandler
from PySide6.QtTest import QTest
from main import create_application
from verify_v17 import TestDevice
from hardware.decoder import Decoder
from hardware.config import CONTACTS
messages=[];qInstallMessageHandler(lambda t,c,m:messages.append(m));tmp=tempfile.TemporaryDirectory();device=TestDevice()
app,engine,ctl,w=create_application(skip_boot=True,animate=False,data_dir=tmp.name,device=device,gpio_autostart=False)
nav=ctl.navigation;knobs=ctl.knobs;sw=ctl.settings_host.window;checks=[]
out=ROOT/'tests/control-update-screenshots';out.mkdir(exist_ok=True)
def check(label,value):
    assert value,label
    print('PASS',label,flush=True);checks.append(label)
def item(name):return nav.find(name)
def tap(name):
    o=item(name);p=o.mapToScene(QPointF(o.width()/2,o.height()/2)).toPoint();QTest.mouseClick(w,Qt.LeftButton,Qt.NoModifier,p);QTest.qWait(60)
def quiet_notices():
    while ctl.notifications.cards:ctl.notifications.dismissId(ctl.notifications.cards[0]['id'])

def shot(name):QTest.qWait(60);w.grabWindow().save(str(out/(name+'.png')))
try:
    QTest.qWait(250)
    for _ in range(35):ctl.step(.05)
    for name in ('lock1','emission1','stabilise1','shortcut1','more1'):
        rect=item(name).mapRectToScene(item(name).boundingRect());check(name+' fully inside screen',rect.right()<=w.width()-6)
    cfg=knobs.store.config['knobs'][0];cfg['calibrated']=True
    levels=dict.fromkeys(('encoder_a','encoder_b',*CONTACTS),1);decoder=Decoder(cfg,levels,0)
    knobs.set_status(True,'Recorded edges');knobs.armed.add(0);start=ctl.value(0,'current');clock=0
    for _ in range(80):
        for a,b in ((0,1),(0,0),(1,0),(1,1)):
            clock+=1_000_000;decoder.edge('encoder_a',a,clock);decoder.edge('encoder_b',b,clock)
    frame=decoder.snapshot();knobs.receive({0:frame})
    check('160 decoded fast rotation steps reach the big number',frame['count']==160 and round(ctl.value(0,'current')-start,3)==.16)
    check('Burst dispatch counter keeps all steps',knobs.delivery[0]==160)
    quiet_notices();nav.clear_focus();nav.set_side(0)
    check('Left focus targets stay on left',all(r.center().x()<800 for o,r,l in nav.targets()))
    nav.set_side(3);check('Right focus targets stay on right',all(r.center().x()>=800 for o,r,l in nav.targets()))
    entries=nav.targets();nav.move_focus(1,7);check('First focus batch preserves seven steps',nav.target==entries[6%len(entries)][0]);nav.clear_focus()
    # Knob 2 default push opens More; rotary operations override its normal focus mapping.
    knobs.dispatch(1,'push');QTest.qWait(880);radial=item('radialMenu')
    check('Push opens restored sector wheel',radial.isVisible() and radial.property('expansion')>.99)
    knobs.dispatch(1,'clockwise',12);QTest.qWait(270)
    check('Sector selection wraps and preserves every knob step',radial.property('targetPosition')==12 and radial.property('selectedIndex')==0)
    shot('more-left');knobs.dispatch(3,'clockwise',2)
    check('Opposite-side knob cannot move left wheel',radial.property('targetPosition')==12)
    knobs.dispatch(1,'right');QTest.qWait(820);check('Joystick right opens the highlighted Alarms',item('alarmPanel').isVisible())
    knobs.dispatch(1,'clockwise');check('Same knob navigates opened panel',nav.target is not None)
    knobs.dispatch(1,'left');nav.clear_focus()
    signals=item('signalsPanel');signals.open(0,0);tap('tabYAxis');QTest.qWait(280);tap('scaleInput')
    pad=item('keypad');draft=pad.property('draft');knobs.dispatch(0,'clockwise',2)
    check('Left knob owns axis numpad even when it appears on the right',pad.property('side')==1 and pad.property('draft')!=draft)
    draft=pad.property('draft');knobs.dispatch(3,'clockwise',2)
    check('Right knob cannot edit a left-owned axis numpad',pad.property('draft')==draft)
    pad.key('close');signals.setVisible(False);nav.clear_focus()
    before=ctl.instrument.lasers[0].emission;tap('emission0');confirm=item('emissionConfirm')
    check('Tapping emission only asks for confirmation',confirm.isVisible() and ctl.instrument.lasers[0].emission==before)
    track=item('emissionTrack');a=track.mapToScene(QPointF(40,39)).toPoint();b=track.mapToScene(QPointF(598,39)).toPoint()
    touch=QTest.createTouchDevice();QTest.touchEvent(w,touch).press(0,a,w).commit()
    for i in range(1,8):QTest.touchEvent(w,touch).move(0,a+(b-a)*i/7,w).commit();QTest.qWait(20)
    QTest.touchEvent(w,touch).release(0,b,w).commit();QTest.qWait(300)
    check('Complete touch slide commits emission once',ctl.instrument.lasers[0].emission!=before and not confirm.isVisible())
    tap('emission0');knobs.dispatch(0,'clockwise',10);knobs.dispatch(0,'push');QTest.qWait(300)
    check('Knob can complete emission confirmation without touch',ctl.instrument.lasers[0].emission==before)
    ctl.theme.apply('corner_number_color','#FFD60A');ctl.theme.apply('corner_detail_color','#FFFFFF')
    check('Separate number and label colors apply',item('topParameter0').property('tileInk').name()=='#ffd60a' and item('topParameter0').property('detailInk').name()=='#ffffff')
    ctl.theme.apply('corner_number_color','Automatic');ctl.theme.apply('corner_detail_color','Automatic')
    for preset in ('Classic','Lab Light','Ion Cyber','Porcelain','Orchid','Clay'):
        ctl.theme.apply('theme_preset',preset);quiet_notices();QTest.qWait(750);shot('theme-'+preset.lower().replace(' ','-'))
    ctl.theme.apply('theme_preset','Classic')
    for side in (0,1):
        radial.open(side,side);QTest.qWait(880);shot('more-'+str(side));radial.dismiss('');QTest.qWait(880)
    # Lock both Qt surfaces and semantic GPIO commands; cancel before expiry.
    guard=ctl.session_lock;before=ctl.value(0,'current');guard.set_locked(True)
    check('Physical switch locks system',guard.locked and guard.window.isVisible())
    guard.window.grab().save(str(out/'system-lock.png'));knobs.dispatch(0,'clockwise',15);nav.handle(0,'value.increase',5)
    check('Locked knobs cannot edit parameters',ctl.value(0,'current')==before)
    event=QEvent(QEvent.Type.TouchBegin);check('Lock blocks touch and keyboard globally',guard.eventFilter(w,event) and guard.eventFilter(sw,QEvent(QEvent.Type.KeyPress)))
    guard.set_locked(False);guard.deadline=time.monotonic()-1;guard.tick()
    check('Unlock cancels shutdown',not any(k=='power' for k,v in device.calls))
    stale_epoch=guard.epoch-1;guard.set_locked(True);guard.sent=True
    guard.power_if_still_locked(stale_epoch)
    check('A stale queued shutdown cannot run after unlock and relock',not any(k=='power' for k,v in device.calls))
    guard.set_locked(False)
    guard.set_locked(True);guard.deadline=time.monotonic()-1;guard.tick()
    until=time.monotonic()+3
    while ctl.system_settings.busy and time.monotonic()<until:QTest.qWait(20)
    guard.tick();check('Expiry sends exactly one real backend shutdown request',device.calls.count(('power','shutdown'))==1)
    guard.set_locked(False)
    # Dedicated physical buttons follow the displayed side, including duplicated views.
    knobs.receive_panel(dict(levels={},active={'left_emission':False,'lock':False},events=[]))
    knobs.receive_panel(dict(levels={},active={'left_emission':True,'lock':False},events=[('left_emission',True)]))
    check('Dedicated GPIO emission button opens same confirmation',confirm.isVisible() and confirm.property('side')==0)
    confirm.cancel();QTest.qWait(300)
    ctl.openSection('notifications');QTest.qWait(250);sw.repaint()
    check('Notification inbox shows real action history',len(ctl.notifications.history)>3 and sw.content=='notifications')
    sw.activate(('notice_clear',));check('Clear-history permission request is compact',ctl.notifications.toast['decision'])
    knobs.dispatch(0,'clockwise');sw.repaint()
    sw.grab().save(str(out/'notifications.png'))
    ctl.notifications.accept();check('Confirm clears actual persisted notification history',not ctl.notifications.history and json.loads(ctl.notifications.path.read_text(encoding='utf8'))==[])
    ctl.openSection('control');sw.last_content='control';sw.navigate('panel');QTest.qWait(350);sw.repaint()
    check('Panel controls and shutdown settings exposed',any(r[2]=='lock_shutdown_seconds' for r in sw.rows()))
    sw.grab().save(str(out/'panel-inputs.png'))
    sw.close();QTest.qWait(80)
    errors=[m for m in messages if any(x in m for x in ('ReferenceError','TypeError','is not a function','Cannot assign','not defined'))]
    check('No Qt/QML runtime errors',not errors)
    (ROOT/'tests/control-update-validation.json').write_text(json.dumps(checks,indent=2)+'\n')
finally:
    print('\n'.join(m for m in messages if 'support raise' not in m),flush=True)
    ctl.session_lock.shutdown();ctl.notifications.timer.stop();knobs.shutdown();nav.shutdown();ctl.system_settings.shutdown();ctl.settings_host.shutdown();ctl.timer.stop();w.close();engine.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);tmp.cleanup()
