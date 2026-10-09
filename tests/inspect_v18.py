import os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
os.environ['QT_QPA_PLATFORM']='offscreen';os.environ['QT_QUICK_BACKEND']='software'
from PySide6.QtCore import QCoreApplication,QEvent
from PySide6.QtTest import QTest
from main import create_application
from verify_v17 import TestDevice
tmp=tempfile.TemporaryDirectory();app,engine,ctl,w=create_application(skip_boot=True,data_dir=tmp.name,device=TestDevice(),gpio_autostart=False)
out=ROOT/'tests/v18-screenshots';out.mkdir(exist_ok=True)
sw=ctl.settings_host.window
try:
    QTest.qWait(1600);w.grabWindow().save(str(out/'home.png'))
    ctl.openSettings();QTest.qWait(200)
    sw.select(sw.order.index('control'));sw.motion.position=sw.selected;sw.last_index=sw.selected;QTest.qWait(450);sw.repaint()
    sw.grab().save(str(out/'controls.png'))
    sw.activate(('knob_open',0));QTest.qWait(400);sw.repaint();sw.grab().save(str(out/'knob1.png'))
    row=sw.control_rows(0)[4];sw.activate(('choose_setting',row[1],row[2],row[3]));sw.repaint();sw.grab().save(str(out/'mapping.png'))
    sw.close_dropdown();ctl.system_settings.startKnobTour();QTest.qWait(150);sw.grab().save(str(out/'guide.png'));ctl.system_settings.stopTour()
    sw.activate(('screen_check',));QTest.qWait(150);sw.screen_test.grab().save(str(out/'screen-check.png'));sw.screen_test.close()
finally:
    ctl.knobs.shutdown();ctl.navigation.shutdown();ctl.system_settings.shutdown();ctl.settings_host.shutdown();ctl.timer.stop();w.close();engine.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);tmp.cleanup()
