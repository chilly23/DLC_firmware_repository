"""Reproduce a touch followed by the OS/Qt compatibility mouse event on v1.2."""
import os
import sys
import tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/'mock1.2-pyside6'))
os.environ['QT_QPA_PLATFORM']='offscreen'
os.environ['QT_QUICK_BACKEND']='software'
from PySide6.QtCore import QCoreApplication,QEvent,QPointF,Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from main import create_application

with tempfile.TemporaryDirectory() as data:
    app,engine,ctl,home=create_application(skip_boot=True,animate=False,data_dir=data)
    host=ctl.settings_host;host.open();w=host.window;w.open_search();QTest.qWait(150)
    rect=next(rect for rect,action in w.hits if action==('key','a'))
    p=rect.center()*w.scale+w.offset
    device=QTest.createTouchDevice()
    QTest.touchEvent(w,device).press(0,p.toPoint(),w)
    QTest.touchEvent(w,device).release(0,p.toPoint(),w)
    QTest.qWait(30)
    for kind,buttons in [(QEvent.Type.MouseButtonPress,Qt.MouseButton.LeftButton),(QEvent.Type.MouseButtonRelease,Qt.MouseButton.NoButton)]:
        event=QMouseEvent(kind,p,p,QPointF(w.mapToGlobal(p.toPoint())),Qt.MouseButton.LeftButton,buttons,Qt.KeyboardModifier.NoModifier,Qt.MouseEventSource.MouseEventSynthesizedByQt)
        QCoreApplication.sendEvent(w,event)
    print('v1.2 after one touch plus compatibility mouse:',repr(w.search.text()),flush=True)
    assert w.search.text()=='aa'
    host.shutdown();ctl.timer.stop();home.close();engine.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
