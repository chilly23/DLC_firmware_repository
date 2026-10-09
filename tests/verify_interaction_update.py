"""Real Qt frames: restored wheel, notification stack, software blur and close."""
import os,sys,tempfile,time,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
os.environ['QT_QPA_PLATFORM']='offscreen';os.environ['QT_QUICK_BACKEND']='software'
from PySide6.QtCore import QPointF,QRectF,Qt,QCoreApplication,QEvent,qInstallMessageHandler
from PySide6.QtTest import QTest
from main import create_application
from verify_v17 import TestDevice
messages=[];qInstallMessageHandler(lambda t,c,m:messages.append(m));temp=tempfile.TemporaryDirectory()
app,engine,ctl,w=create_application(skip_boot=True,animate=False,data_dir=temp.name,device=TestDevice(),gpio_autostart=False)
n=ctl.notifications;nav=ctl.navigation;sw=ctl.settings_host.window;checks=[]
out=ROOT/'tests/interaction-update-screenshots';out.mkdir(exist_ok=True)
def check(label,value):
    assert value,label
    print('PASS',label,flush=True);checks.append(label)
def quiet():
    while n.cards:n.dismissId(n.cards[0]['id'])
def shot(name,native=False):
    QTest.qWait(30);(sw.grab() if native else w.grabWindow()).save(str(out/(name+'.png')))
try:
    QTest.qWait(200)
    for _ in range(30):ctl.step(.05)
    radial=nav.find('radialMenu');radial.open(0,0);QTest.qWait(260)
    check('Wheel has visible intermediate opening frames',.03<radial.property('expansion')<.9)
    shot('wheel-opening');QTest.qWait(650)
    check('v1.6 sectors expand around the aligned More button',radial.property('centerY')==556 and radial.property('expansion')>.99)
    shot('wheel-left');radial.dismiss('');QTest.qWait(260)
    check('Closing reverses the radius animation',radial.isVisible() and .1<radial.property('expansion')<.99)
    shot('wheel-closing');QTest.qWait(650);check('Wheel disappears only after closing completes',not radial.isVisible())
    radial.open(1,1);QTest.qWait(880);shot('wheel-right')
    ctl.knobs.dispatch(3,'clockwise',5);check('Knob selection still wraps through restored sectors',radial.property('selectedIndex')==1)
    radial.dismiss('');QTest.qWait(880);quiet()
    n.post('Graph locked');first=n.cards[0]['id'];n.post('Emission enabled');n.post('Channel switched')
    check('Overflow never exceeds two cards',len(n.cards)==2)
    QTest.qWait(750)
    check('Newest notice is first after old card fades',[e['text'] for e in n.cards]==['Channel switched','Emission enabled'])
    first=n.cards[-1]['id']
    cards=[nav.find('noticeCard'+str(e['id'])) for e in n.cards]
    check('Newest notification is physically above the older card',cards[0].y()<cards[1].y())
    shot('notification-stack')
    old=n.find(first);old['deadline']=time.monotonic()-.01;n.tick();QTest.qWait(290)
    check('Automatic expiry retains the card while blurring and fading',old in n.cards and old['blurStep']>0 and 0<old['alpha']<1)
    plain=n.renderer.image(dict(old,blurStep=0));blurred=n.renderer.image(old)
    check('Software renderer produces actual blurred pixels',plain!=blurred)
    shot('notification-blur');QTest.qWait(430)
    check('Only the expired notification is removed',len(n.cards)==1 and n.find(first) is None)
    newest=n.cards[0]['id'];card=nav.find('noticeCard'+str(newest));point=card.mapToScene(QPointF(686,39)).toPoint()
    QTest.mouseClick(w,Qt.LeftButton,Qt.NoModifier,point)
    check('Touch close removes only its card immediately',n.find(newest) is None and len(n.cards)==0)
    n.post('Another action');survivor=n.cards[0];survivor['deadline']=time.monotonic()-.01;n.tick();QTest.qWait(150)
    card=nav.find('noticeCard'+str(survivor['id']));point=card.mapToScene(QPointF(686,39)).toPoint()
    QTest.mouseClick(w,Qt.LeftButton,Qt.NoModifier,point)
    check('Touch close stays immediate during automatic blur-out',n.find(survivor['id']) is None)
    ctl.openSection('notifications');QTest.qWait(300);quiet()
    n.post('Left view locked');n.post('Right view stabilised');n.post('Panel inputs ready');QTest.qWait(750);sw.repaint();shot('settings-notification-stack',True)
    check('Native Settings exposes independent close targets',len([a for r,a in sw.hits if a[0]=='notice_close'])==2)
    body=next(r for r,a in reversed(sw.hits) if a[0]=='notice_body');start=body.topLeft()+QPointF(150,30);old_scroll=sw.scroll
    sw.pointer_down(start);sw.pointer_move(start-QPointF(0,90));sw.pointer_up(start-QPointF(0,90))
    check('Dragging a notification never scrolls Settings underneath',sw.scroll==old_scroll)
    check('Notification body is excluded from knob focus',all(a[0]!='notice_body' for r,a in sw.navigation_hits()))
    # Deliberately overlap an editor with the cards; it must receive the touch.
    sw.dropdown=dict(label='Test choice',key='appearance',items=[('Dark','Dark'),('Light','Light')])
    sw.drop_rect=QRectF(1200,440,300,150);sw.number_drop=False
    sw.register(QRectF(1210,450,270,50),('dropdown_value','Light'))
    sw.pointer_down(QPointF(1250,470))
    check('Open Settings dropdown receives touches above routine notices',sw.pending and sw.pending[1]==('dropdown_value','Light') and not sw._notice_press)
    sw.pending=None;sw.drop_drag=False;sw.close_dropdown()
    calls=[];n.post('Clear saved settings?','warning',decision=lambda:calls.append(True));sw.activate(('notice_close',n.cards[-1]['id']));decision=n.toast['id'];sw.repaint()
    sw.activate(('notice_close',n.cards[-1]['id']));check('Closing another notice preserves pending consent',decision in n.pending)
    n.acceptId(decision);check('Confirmation executes its own callback once',calls==[True]);n.acceptId(decision);check('Dismissed confirmations cannot replay',calls==[True])
    errors=[m for m in messages if any(v in m for v in ('ReferenceError','TypeError','is not a function','Cannot assign','failed to load','Error:'))]
    check('No Qt/QML errors',not errors)
    (ROOT/'tests/interaction-update-validation.json').write_text(json.dumps(checks,indent=2),encoding='utf8')
finally:
    print('\n'.join(m for m in messages if 'support raise' not in m),flush=True)
    ctl.session_lock.shutdown();n.timer.stop();ctl.knobs.shutdown();nav.shutdown();ctl.system_settings.shutdown();ctl.settings_host.shutdown();ctl.timer.stop();w.close();engine.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);temp.cleanup()
