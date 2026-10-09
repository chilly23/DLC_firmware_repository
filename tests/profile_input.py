"""Profile the actual frontend command path, without GPIO or wall-clock waits."""
import os,sys,tempfile,time,cProfile,pstats
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
os.environ['QT_QPA_PLATFORM']='offscreen';os.environ['QT_QUICK_BACKEND']='software'
from main import create_application
from verify_v17 import TestDevice
from PySide6.QtCore import QCoreApplication,QEvent
from PySide6.QtTest import QTest
with tempfile.TemporaryDirectory() as temp:
    app,engine,ctl,w=create_application(skip_boot=True,animate=False,data_dir=temp,device=TestDevice(),gpio_autostart=False)
    QTest.qWait(200)
    profiler=cProfile.Profile();profiler.enable();start=time.perf_counter()
    for _ in range(30):
        for i in (0,1,3):ctl.knobs.dispatch(i,'clockwise',1)
    elapsed=time.perf_counter()-start;profiler.disable()
    print('90 input operations seconds:',elapsed,flush=True)
    pstats.Stats(profiler).sort_stats('cumtime').print_stats(20)
    ctl.timer.stop();ctl.parameters.shutdown();ctl.workspace.shutdown();ctl.workspace.diagnostics.shutdown()
    ctl.notifications.timer.stop();ctl.knobs.shutdown();ctl.navigation.shutdown();ctl.session_lock.shutdown()
    ctl.settings_host.shutdown();ctl.system_settings.shutdown();ctl.journal.close();w.hide();engine.deleteLater()
    QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)
