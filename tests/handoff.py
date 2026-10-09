"""Actual Windows fullscreen Settings handoff; isolated settings and host adapter."""
import os, sys, tempfile, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
os.environ['QT_QUICK_BACKEND']='software'
from PySide6.QtCore import QObject,QEvent,QCoreApplication
from PySide6.QtTest import QTest
from main import create_application
from verify_v17 import TestDevice
os.environ['QT_QPA_PLATFORM']='windows'

tmp=tempfile.TemporaryDirectory()
app,engine,ctl,home=create_application(skip_boot=True,animate=False,data_dir=tmp.name,device=TestDevice(),gpio_autostart=False)
settings=ctl.settings_host.window
out=ROOT/'tests/handoff';out.mkdir(exist_ok=True)
class PaintSpy(QObject):
    def __init__(self):super().__init__();self.pages=[]
    def eventFilter(self,obj,event):
        if event.type()==QEvent.Paint:self.pages.append(obj.content)
        return False
spy=PaintSpy();settings.installEventFilter(spy);results=[];visibility=[]
try:
    assert app.platformName()=='windows'
    home.showFullScreen();QTest.qWait(200)
    home.visibilityChanged.connect(lambda v:visibility.append(v))
    for section in ('control','display','function','logs'):
        spy.pages=[]
        ctl.openSection(section);QTest.qWait(120)
        assert home.isVisible() and settings.isVisible()
        assert home.visibility()==home.Visibility.FullScreen and settings.isFullScreen()
        assert spy.pages and all(p==section for p in spy.pages),(section,spy.pages)
        assert settings.windowHandle().transientParent()==home
        assert settings.geometry()==home.geometry(),(settings.geometry(),home.geometry())
        results.append({'section':section,'correct_first_paint':True,'fullscreen':True})
        if section=='control':settings.grab().save(str(out/'settings.png'))
        ctl.closeSettings();QTest.qWait(50)
        assert home.isVisible() and not settings.isVisible()
    assert home.Visibility.Hidden not in visibility
    home.grabWindow().save(str(out/'home.png'))
    (out/'results.json').write_text(json.dumps(dict(platform=app.platformName(),checks=results,home_hidden=False),indent=2))
    print('PASS',app.platformName(),'fullscreen handoff: four first paints, no home unmapping, no frame changes',flush=True)
finally:
    settings.removeEventFilter(spy)
    ctl.session_lock.shutdown();ctl.knobs.shutdown();ctl.navigation.shutdown();ctl.system_settings.shutdown()
    ctl.notifications.timer.stop();ctl.settings_host.shutdown();ctl.timer.stop();home.close()
    engine.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete);tmp.cleanup()
