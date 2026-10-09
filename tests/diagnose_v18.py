"""Small, real-input repro for graph gestures and retrying display detection."""
import os,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
os.environ['QT_QPA_PLATFORM']='offscreen';os.environ['QT_QUICK_BACKEND']='software'
from PySide6.QtCore import Qt,QPoint,QPointF,QCoreApplication,QEvent
from PySide6.QtTest import QTest
from main import create_application
from verify_v17 import TestDevice
class RecoveringDevice(TestDevice):
    def __init__(self):super().__init__();self.probes=0
    def probe(self):
        self.probes+=1;d=super().probe()
        if self.probes==1:d.update(brightness=None,contrast=None,reasons={'brightness':'Display temporarily unavailable'})
        return d
tmp=tempfile.TemporaryDirectory();device=RecoveringDevice()
app,engine,ctl,w=create_application(skip_boot=True,animate=False,data_dir=tmp.name,device=device)
def item(name):
    stack=[w.contentItem()]
    while stack:
        o=stack.pop()
        if o.objectName()==name:return o
        stack.extend(o.childItems())
    raise AssertionError(name)
def wait_job():
    until=time.monotonic()+5
    while ctl.system_settings.busy and time.monotonic()<until:QTest.qWait(20)
try:
    QTest.qWait(150);p=item('absorption0Renderer');p.setRange(51.,64.)
    before=p.xMinimum
    touch=QTest.createTouchDevice();start=QPoint(390,280)
    QTest.touchEvent(w,touch).press(0,start,w).commit();QTest.qWait(35)
    for x in (400,420,450,480):QTest.touchEvent(w,touch).move(0,QPoint(x,280),w).commit();QTest.qWait(25)
    QTest.touchEvent(w,touch).release(0,QPoint(480,280),w).commit();QTest.qWait(60)
    print('PAN',before,p.xMinimum,flush=True);assert abs(p.xMinimum-before)>.2,'Native touch pan does not change range'
    p.setRange(51.,64.);width=p.xMaximum-p.xMinimum
    QTest.touchEvent(w,touch).press(0,QPoint(350,300),w).press(1,QPoint(500,300),w).commit();QTest.qWait(80)
    for delta in (10,20,35,50,70):
        QTest.touchEvent(w,touch).move(0,QPoint(350-delta,300),w).move(1,QPoint(500+delta,300),w).commit();QTest.qWait(45)
    QTest.touchEvent(w,touch).release(0,QPoint(280,300),w).release(1,QPoint(570,300),w).commit();QTest.qWait(100)
    print('PINCH',width,p.xMaximum-p.xMinimum,flush=True);assert p.xMaximum-p.xMinimum<width-1,'Native pinch does not zoom'
    ctl.system_settings.probe();wait_job();print('FIRST PROBE',ctl.system_settings.caps['brightness'],flush=True)
    ctl.system_settings.probe();wait_job();print('RETRY',ctl.system_settings.caps['brightness'],flush=True)
    assert ctl.system_settings.caps['brightness']==70,'Display remains unavailable after the hardware recovers'
finally:
    ctl.system_settings.shutdown();ctl.settings_host.shutdown();ctl.timer.stop();w.close();engine.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete);tmp.cleanup()
