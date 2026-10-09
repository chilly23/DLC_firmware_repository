"""Run with runtime/python.exe. Exercises the actual Qt scene and controller."""
import json
import os
import sys
import tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('QT_QUICK_BACKEND','software')
from PySide6.QtCore import QObject,QPoint,QPointF,Qt,QEvent,QCoreApplication,qInstallMessageHandler
from PySide6.QtTest import QTest
from main import create_application

messages=[]
qInstallMessageHandler(lambda kind,context,message: messages.append(message))
data=tempfile.TemporaryDirectory()
app,engine,ctl,w=create_application(skip_boot=True,animate=False,data_dir=data.name)
checks=[]
shots=ROOT/'tests'/'chart-screenshots';shots.mkdir(exist_ok=True)
def check(name,value):
    assert value,name
    checks.append(name);print('PASS',name,flush=True)
def item(name):
    stack=[w.contentItem()]
    while stack:
        obj=stack.pop()
        if obj.objectName()==name:return obj
        stack.extend(obj.childItems())
    raise AssertionError('Missing '+name)
def center(name):
    a=item(name);return a.mapToScene(QPointF(a.width()/2,a.height()/2)).toPoint()
def tap(name):
    QTest.mouseClick(w,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,center(name));QTest.qWait(70)
def shot(name):
    QTest.qWait(100);check('Capture '+name,w.grabWindow().save(str(shots/(name+'.png'))))
def drag_signal(name,end):
    while ctl.notifications.cards:ctl.notifications.dismissId(ctl.notifications.cards[0]['id'])
    start=center(name)
    QTest.mousePress(w,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,start);QTest.qWait(650)
    check('Long press opens drag overlay',item('graphDrag').isVisible())
    QTest.mouseMove(w,end,80);QTest.qWait(80)
    return start
def release(end):
    QTest.mouseRelease(w,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,end);QTest.qWait(100)
try:
    QTest.qWait(300)
    for _ in range(40):ctl.step(.05)
    check('Main window is 1600 by 720',w.width()==1600 and w.height()==720)
    a,b=ctl.instrument.lasers
    usable=ctl.workspace.graphLayout['height']-ctl.workspace.graphLayout['gap']
    check('Large Home graphs preserve the split ratio and enlarge both traces',abs(item('absorption0').height()-usable*341/493)<.01 and abs(item('error0').height()-usable*152/493)<.01)
    shot('01-home')
    tap('chartLabels0');check('Left chart labels open Signals',item('signalsPanel').isVisible() and item('signalsPanel').property('side')==0)
    shot('02-signals-split')
    tap('mainLower');check('Manual position swap is complementary and per laser',not a.chart.main_upper and b.chart.main_upper and item('absorption0').y()>item('error0').y())
    check('Bottom spectroscopy alone draws shared x labels after swap',item('absorption0Renderer').showXAxis and not item('error0Renderer').showXAxis)
    tap('mainUpper');tap('tabCombined')
    check('Combined selection immediately overlays both signals',a.chart.mode=='combined' and item('absorption0Renderer').combined and not item('error0').isVisible())
    shot('03-signals-combined')
    tap('visibleMain');tap('visibleError');check('Visibility controls independently hide both signals',not a.chart.main_visible and not a.chart.error_visible)
    tap('visibleMain');tap('visibleError');tap('signalsClose')
    check('Closing retains combined mode without applying another option',a.chart.mode=='combined' and item('absorption0').height()==ctl.workspace.graphLayout['height'])
    shot('04-combined')
    tap('chartLabels0');tap('tabSplit');tap('tabYAxis');QTest.qWait(300)
    check('Y-axis subpage is shown',item('signalsPanel').property('axisPage'))
    shot('05-y-axis')
    tap('scalePlus');check('Main V/div changes immediately',a.chart.axes['main_scale']==5)
    tap('scaleMinus');check('Scale decrement restores previous division',a.chart.axes['main_scale']==2.75)
    tap('positionPlus');check('Position changes by one division',a.chart.axes['main_position']==7.25)
    tap('scaleInput');check('Axis input opens existing numpad',item('keypad').isVisible() and item('keypad').property('fieldKey')=='chart_main_scale')
    tap('key2');tap('keyDecimal');tap('key5');tap('keyEnter')
    check('Numpad edits actual chart scale and returns to Y-axis page',a.chart.axes['main_scale']==2.5 and not item('keypad').isVisible() and item('signalsPanel').isVisible())
    tap('axisError');tap('positionInput');tap('key1');tap('keyMinus');tap('keyEnter')
    check('Error axis has independent negative position',a.chart.axes['error_position']==-1 and a.chart.axes['main_position']==7.25)
    tap('scaleInput');tap('key0');tap('keyEnter')
    check('Invalid zero V/div is rejected',item('keypad').isVisible() and a.chart.axes['error_scale']==1.25)
    tap('keyCancel')
    slider=item('heightRatio');start=slider.mapToScene(QPointF(18,30)).toPoint();end=slider.mapToScene(QPointF(666,30)).toPoint()
    QTest.mousePress(w,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,start);QTest.qWait(80)
    check('Height slider minimum is 20/80',a.chart.main_ratio==.2 and abs(item('absorption0').height()-(ctl.workspace.graphLayout['height']-ctl.workspace.graphLayout['gap'])*.2)<.01)
    QTest.mouseMove(w,end,70);QTest.qWait(80)
    check('Height updates live before slider release at 80/20',a.chart.main_ratio==.8 and abs(item('error0').height()-(ctl.workspace.graphLayout['height']-ctl.workspace.graphLayout['gap'])*.2)<.01)
    QTest.mouseRelease(w,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,end)
    shot('06-height-adjustment')
    check('Axis/layout editing does not change Laser 2',b.chart.main_ratio==341/493 and b.chart.axes['main_scale']==2.75 and b.chart.axes['error_position']==0)
    tap('restoreAxes');check('Restore resets both scales, positions and split height',a.chart.axes==b.chart.axes and a.chart.main_ratio==341/493)
    tap('axisBack');QTest.qWait(300);check('Back returns to Signals',not item('signalsPanel').property('axisPage'))
    tap('signalsClose')
    end=QPoint(470,535);drag_signal('absorption0',end)
    check('Within-half drag previews only the grabbed signal',not item('graphDrag').property('wholeChannel'))
    shot('07-local-drag');release(end)
    check('Local drag swaps only Laser 1 plots',not a.chart.main_upper and b.chart.main_upper and ctl.instrument.views==[0,1])
    end=QPoint(1140,350);drag_signal('absorption0',end)
    check('Crossing centre upgrades drag to the whole channel',item('graphDrag').property('wholeChannel'))
    shot('08-channel-drag');release(end)
    check('Cross-half drop swaps lasers and carries native plot order',ctl.instrument.views==[1,0] and not ctl.instrument.lasers[ctl.rightChannel].chart.main_upper)
    ctl.moveGraph(0,1);ctl.swapLocal(0)
    while ctl.notifications.cards:ctl.notifications.dismissId(ctl.notifications.cards[0]['id'])
    QTest.qWait(350)
    device=QTest.createTouchDevice()
    start=center('error0');end=QPoint(500,260)
    touch=QTest.touchEvent(w,device,False)
    touch.press(0,start,w).commit();QTest.qWait(650)
    check('Native touch hold selects the error signal',item('graphDrag').isVisible() and item('graphDrag').property('errorSignal'))
    touch.move(0,QPoint(1140,350),w).commit();QTest.qWait(80)
    check('Native touch crossing the divider selects the whole pair',item('graphDrag').property('wholeChannel'))
    touch.move(0,end,w).commit();QTest.qWait(80)
    check('Returning to the source half restores local drag',not item('graphDrag').property('wholeChannel'))
    touch.release(0,end,w).commit();QTest.qWait(100)
    check('Native error-to-upper drop swaps locally without swapping lasers',not a.chart.main_upper and b.chart.main_upper and ctl.instrument.views==[0,1])
    ctl.swapLocal(0)
    tap('chartLabels1');tap('mainLower');tap('tabYAxis');QTest.qWait(300)
    tap('scalePlus');tap('signalsClose')
    check('Right panel edits stay with Laser 2',not b.chart.main_upper and b.chart.axes['main_scale']==5 and a.chart.axes['main_scale']==2.75)
    ctl.restoreChartAxes(1);ctl.placeSignal(1,False,True)
    end=QPoint(470,45);drag_signal('absorption0',end);release(end)
    check('Outside drop cancels without changing order',a.chart.main_upper and ctl.instrument.views==[0,1])
    ctl.toggleLock(1);end=QPoint(1140,350);drag_signal('absorption0',end)
    check('Locked destination is indicated',item('graphDrag').property('destinationLocked'))
    release(end);check('Locked destination blocks channel swap',ctl.instrument.views==[0,1]);ctl.toggleLock(1)
    tap('fullscreen1');tap('chartLabelsFullscreen');check('Fullscreen labels open correct channel panel',item('signalsPanel').property('channelIndex')==1)
    tap('tabCombined');tap('signalsClose');check('Fullscreen shares chart state',item('fullscreenAbsorptionRenderer').combined and b.chart.mode=='combined')
    shot('09-fullscreen-combined');tap('exitFullscreen')
    tap('chartLabels1');tap('tabSplit');tap('signalsClose')
    ctl.switchView(1);ctl.swapLocal(0);QTest.qWait(80)
    check('Duplicate views follow native laser chart state',item('absorption0').y()==item('absorption1').y() and not a.chart.main_upper)
    ctl.swapLocal(0);ctl.switchView(1)
    plot=item('absorption0Renderer');err=item('error0Renderer');plot.zoom(1.2,350)
    check('Shared x coordinates remain synchronized',plot.xMinimum==err.xMinimum and plot.area().left()==err.area().left())
    ctl.toggleLock(0);old=(plot.xMinimum,plot.xMaximum,a.chart.axes.copy());plot.pan(70,20);plot.zoom(2,300);plot.resetView()
    check('Graph lock still prevents view gestures',old==(plot.xMinimum,plot.xMaximum,a.chart.axes))
    ctl.toggleLock(0);plot.resetView()
    ctl.toggleEmission(0)
    for _ in range(31):ctl.step(.05)
    check('Emission off still reaches exact zero',a.sample(53,0)==(0.,0.))
    ctl.toggleEmission(0);ctl.toggleStabilisation(0)
    for _ in range(31):ctl.step(.05)
    check('Emission and stabilisation still run',a.signal.level==1 and a.signal.smoothing>.99)
    errors=[m for m in messages if any(s in m for s in ['TypeError','ReferenceError','Cannot assign','Binding loop','failed to load','Error:'])]
    check('No QML errors',not errors)
    (ROOT/'tests'/'chart-validation.json').write_text(json.dumps({'checks':checks,'warnings':messages},indent=2),encoding='utf8')
    print(f'{len(checks)} checks passed',flush=True)
finally:
    ctl.journal.close()
    print('\n'.join(messages),flush=True)
    ctl.settings_host.shutdown();ctl.timer.stop();w.close();engine.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);data.cleanup()
