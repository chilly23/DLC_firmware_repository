"""Regression for visual symmetry, bounded notices, settings handoff and idle controls."""
import os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
os.environ['QT_QPA_PLATFORM']='offscreen';os.environ['QT_QUICK_BACKEND']='software'
from PySide6.QtCore import QPointF,QCoreApplication,QEvent,QObject,Qt
from PySide6.QtTest import QTest
from main import create_application
from verify_v17 import TestDevice
tmp=tempfile.TemporaryDirectory();app,engine,ctl,w=create_application(skip_boot=True,animate=False,data_dir=tmp.name,device=TestDevice(),gpio_autostart=False)
failed=[]
def check(name,value):
    print(('PASS ' if value else 'FAIL ')+name,flush=True)
    if not value:failed.append(name)
def item(name):return ctl.navigation.find(name)
def rect(name):
    obj=item(name);return obj.mapRectToScene(obj.boundingRect())
try:
    QTest.qWait(200)
    a,b=rect('charts0'),rect('charts1')
    check('Chart frames mirror about screen center',abs(a.left()+b.right()-1600)<.1 and abs(a.right()+b.left()-1600)<.1)
    for name in ('lock','emission','stabilise','shortcut','more','switch','fullscreen','topParameter','bottomParameter','chartLabels'):
        a,b=rect(name+'0'),rect(name+'1')
        check(name+' positions and dimensions mirror',abs(a.left()+b.right()-1600)<.1 and abs(a.width()-b.width())<.1 and abs(a.top()-b.top())<.1)
    check('Right chart uses an outer right Y axis',item('absorption1Renderer').property('rightAxis') is True and item('error1Renderer').property('rightAxis') is True)
    ctl.setEmission(0,False);before=ctl.channel(0);ctl.toggleLock(0);ctl.toggleStabilisation(0)
    check('Off laser rejects Lock and Stabilise in controller',ctl.channel(0)['locked']==before['locked'] and ctl.channel(0)['stabilised']==before['stabilised'])
    check('Off laser disables both touch controls',not item('lock0').isEnabled() and not item('stabilise0').isEnabled())
    for name in ('lock0','stabilise0'):
        QTest.mouseClick(w,Qt.LeftButton,Qt.NoModifier,rect(name).center().toPoint())
    ctl.navigation.handle(0,'graph.lock',1);ctl.navigation.handle(0,'stabilise.toggle',1)
    check('Off laser ignores actual touches and mapped knob actions',ctl.channel(0)['locked']==before['locked'] and ctl.channel(0)['stabilised']==before['stabilised'])
    ctl.setEmission(0,True)
    check('Emission restores access to both controls',item('lock0').isEnabled() and item('stabilise0').isEnabled())
    a,b=rect('dropPanel0'),rect('dropPanel1')
    check('Drag skeleton is mirrored too',abs(a.left()+b.right()-1600)<.1 and abs(a.width()-b.width())<.1)
    for n in range(12):ctl.notifications.post('Action '+str(n))
    check('No more than two notices visible',len(ctl.notifications.cards)<=2)
    ctl.openSettings();QTest.qWait(80)
    check('Home surface stays mapped behind Settings',w.isVisible() and ctl.settings_host.window.isVisible())
    ctl.closeSettings();QTest.qWait(60)
    check('Closing Settings reveals home immediately',w.isVisible() and not ctl.settings_host.window.isVisible())
    class PaintRecorder(QObject):
        def eventFilter(self,obj,event):
            if event.type()==QEvent.Paint:self.pages.append(obj.content)
            return False
    spy=PaintRecorder();spy.pages=[];sw=ctl.settings_host.window;sw.installEventFilter(spy)
    ctl.openSection('control');QTest.qWait(30)
    check('Requested Settings section is ready on its first paint',bool(spy.pages) and all(p=='control' for p in spy.pages))
    sw.removeEventFilter(spy);ctl.closeSettings()
finally:
    ctl.session_lock.shutdown();ctl.knobs.shutdown();ctl.navigation.shutdown();ctl.system_settings.shutdown();ctl.notifications.timer.stop();ctl.settings_host.shutdown();ctl.timer.stop();w.close();engine.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete);tmp.cleanup()
if failed:raise SystemExit(1)
