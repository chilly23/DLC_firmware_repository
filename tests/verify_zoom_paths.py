"""Native touch zoom in one trace, across traces, and after holding one finger."""
import os,sys,tempfile,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
os.environ['QT_QPA_PLATFORM']='offscreen';os.environ['QT_QUICK_BACKEND']='software'
from PySide6.QtCore import QPoint,Qt,QCoreApplication,QEvent
from PySide6.QtTest import QTest
from main import create_application
from verify_v17 import TestDevice
tmp=tempfile.TemporaryDirectory();app,engine,ctl,w=create_application(skip_boot=True,animate=False,data_dir=tmp.name,device=TestDevice(),gpio_autostart=False)
touch=QTest.createTouchDevice();checks=[]
def pinch(label,side=0,y1=300,y2=300,delay=0,reverse=False,locked=False,fullscreen=False):
    main_name='fullscreenAbsorptionRenderer' if fullscreen else f'absorption{side}Renderer'
    error_name='fullscreenErrorRenderer' if fullscreen else f'error{side}Renderer'
    plot=ctl.navigation.find(main_name);error=ctl.navigation.find(error_name)
    other=ctl.navigation.find(f'absorption{1-side}Renderer');other_before=(other.xMinimum,other.xMaximum)
    plot.setRange(51.,64.);before=plot.xMaximum-plot.xMinimum
    offset=0 if fullscreen else side*693;x1,x2=350+offset,500+offset
    sign=-1 if reverse else 1
    if delay:
        QTest.touchEvent(w,touch).press(0,QPoint(x1,y1),w).commit();QTest.qWait(delay)
        assert ctl.navigation.find('graphDrag').isVisible(),'The long-press path was not exercised'
        QTest.touchEvent(w,touch).stationary(0).press(1,QPoint(x2,y2),w).commit()
    else:QTest.touchEvent(w,touch).press(0,QPoint(x1,y1),w).press(1,QPoint(x2,y2),w).commit()
    QTest.qWait(60)
    for d in (10,20,30,40,50):
        QTest.touchEvent(w,touch).move(0,QPoint(x1-sign*d,y1),w).move(1,QPoint(x2+sign*d,y2),w).commit();QTest.qWait(25)
    QTest.touchEvent(w,touch).release(0,QPoint(x1-sign*50,y1),w).release(1,QPoint(x2+sign*50,y2),w).commit();QTest.qWait(50)
    after=plot.xMaximum-plot.xMinimum
    if locked:assert abs(after-before)<1e-7,(label,before,after)
    else:assert (after>before+.5 if reverse else after<before-.5),(label,before,after)
    assert abs(error.xMinimum-plot.xMinimum)<1e-7 and abs(error.xMaximum-plot.xMaximum)<1e-7,label+' shared X axis'
    assert not ctl.navigation.find('graphDrag').isVisible(),label+' drag remains active'
    assert (other.xMinimum,other.xMaximum)==other_before,label+' changed the other laser'
    checks.append(dict(case=label,before=before,after=after));print('PASS',label,before,after,flush=True)
try:
    QTest.qWait(200)
    pinch('same plot');pinch('split plots',y2=515);pinch('held finger',delay=650)
    pinch('right laser split plots',side=1,y2=515);pinch('zoom out',reverse=True)
    ctl.toggleLock(0);pinch('locked view',y2=515,locked=True);ctl.toggleLock(0)
    ctl.swapLocal(0);pinch('swapped local plots',y2=515);ctl.swapLocal(0)
    ctl.setChartMode(0,'combined');pinch('combined plots',y2=515);ctl.setChartMode(0,'split')
    w.openFullscreen(1);QTest.qWait(80);pinch('fullscreen right laser',side=1,y2=600,fullscreen=True)
    w.closeFullscreen();assert ctl.instrument.views==[0,1]
    (ROOT/'tests/zoom-validation.json').write_text(json.dumps(checks,indent=2)+'\n')
finally:
    ctl.knobs.shutdown();ctl.navigation.shutdown();ctl.system_settings.shutdown();ctl.settings_host.shutdown();ctl.timer.stop();w.close();engine.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);tmp.cleanup()
