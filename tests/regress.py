"""Real Qt regressions for menu push and non-mutating guide navigation."""
import os,sys,tempfile
from pathlib import Path
from copy import deepcopy
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
os.environ['QT_QPA_PLATFORM']='offscreen';os.environ['QT_QUICK_BACKEND']='software'
from PySide6.QtTest import QTest
from PySide6.QtCore import QCoreApplication,QEvent
from main import create_application
from verify_v17 import TestDevice
from settings_ui.tour import TOUR
temp=tempfile.TemporaryDirectory();app,engine,ctl,w=create_application(skip_boot=True,animate=False,data_dir=temp.name,device=TestDevice(),gpio_autostart=False)
fail=[]
def check(name,ok):
    print(('PASS ' if ok else 'FAIL ')+name,flush=True)
    if not ok:fail.append(name)
try:
    QTest.qWait(200);menu=ctl.navigation.find('radialMenu')
    ctl.knobs.dispatch(1,'push');QTest.qWait(900);ctl.knobs.dispatch(1,'push');QTest.qWait(900)
    check('Same knob push closes More without opening a window',not menu.isVisible() and not ctl.navigation.find('alarmPanel').isVisible())
    ctl.navigation.find('alarmPanel').setVisible(False)
    ctl.theme.apply('theme_preset','Orchid');ctl.instrument.lasers[0].chart.main_ratio=.72
    ctl.instrument.lasers[0].chart.axes['main_scale']=3.4
    before=deepcopy(ctl.instrument.lasers[0].chart.snapshot());colors=deepcopy(ctl.theme.store.values)
    w.openFullscreen(1);system=ctl.system_settings;system.startTour();system.tourPause()
    system._tour=next(i for i,t in enumerate(TOUR) if t.get('action')=='combined');system.route_tour();QTest.qWait(50)
    check('Guide does not mutate live chart mode or axes',ctl.instrument.lasers[0].chart.snapshot()==before)
    system.stopTour();QTest.qWait(60)
    check('Guide returns to prior fullscreen view',w.property('fullscreenSide')==1)
    check('Guide preserves selected theme',ctl.theme.store.values['theme_preset']==colors['theme_preset'])
finally:
    ctl.session_lock.shutdown();ctl.knobs.shutdown();ctl.navigation.shutdown();ctl.system_settings.shutdown();ctl.notifications.timer.stop();ctl.settings_host.shutdown();ctl.timer.stop();w.close();engine.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete);temp.cleanup()
if fail:raise SystemExit(1)
