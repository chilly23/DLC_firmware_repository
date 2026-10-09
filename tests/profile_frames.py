"""Small reproducible GUI-thread profile for future HMI performance work."""
import os,sys,time,cProfile,pstats,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
os.environ['QT_QPA_PLATFORM']='offscreen';os.environ['QT_QUICK_BACKEND']='software'
from main import create_application
from PySide6.QtTest import QTest
from PySide6.QtCore import QCoreApplication,QEvent
with tempfile.TemporaryDirectory() as data:
    app,engine,ctl,w=create_application(skip_boot=True,animate=False,data_dir=data)
    QTest.qWait(200)
    profiler=cProfile.Profile();profiler.enable()
    for _ in range(15):ctl.step(.05);QTest.qWait(1)
    profiler.disable();pstats.Stats(profiler).sort_stats('cumtime').print_stats(16)
    ctl.journal.close();ctl.settings_host.shutdown();w.close();engine.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
