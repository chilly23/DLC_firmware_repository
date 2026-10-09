"""Native navigation, layout and persistence regression for the v1.15 restructure."""
import json
import os
from pathlib import Path
import sys
import tempfile
import math
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'tests')]
os.environ['QT_QUICK_BACKEND'] = 'software'
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import QObject, QCoreApplication, QEvent, QPointF, QPoint, Qt, qInstallMessageHandler
from PySide6.QtGui import QMouseEvent, QImage
from PySide6.QtQml import QQmlExpression
from PySide6.QtTest import QTest
from main import create_application
from verify_v17 import TestDevice
from settings_ui.model import SettingsStore
os.environ['QT_QPA_PLATFORM']='windows' if '--native' in sys.argv else 'offscreen'

messages=[]
def qt_message(kind, context, message):
    messages.append(message)
    print(message, flush=True)
qInstallMessageHandler(qt_message)
data = tempfile.TemporaryDirectory()
app,engine,ctl,window = create_application(skip_boot=True,animate=False,data_dir=data.name,device=TestDevice(),gpio_autostart=False)
output = ROOT/'tests/lobby'
output.mkdir(exist_ok=True)
checks=[]


def js(code, obj=None):
    expr=QQmlExpression(engine.rootContext(),obj or window,code)
    value,undefined=expr.evaluate()
    assert not expr.hasError(),expr.error().toString()
    return value


def find(name, root=None):
    items=[root or window.contentItem()]
    while items:
        item=items.pop()
        if item.objectName()==name:return item
        items.extend(item.childItems())
    raise AssertionError('Missing '+name)


def click(name, surface=None):
    surface=surface or window
    item=find(name,surface.contentItem())
    position=item.mapToScene(QPointF(item.width()/2,item.height()/2)).toPoint()
    QTest.mouseClick(surface,Qt.LeftButton,pos=position)
    QTest.qWait(80)


def shot(name, surface=None):
    QTest.qWait(150)
    image=(surface or window).grabWindow()
    assert not image.isNull(),name
    image.save(str(output/(name+'.png')))


try:
    window.resize(1600,720);QTest.qWait(400)
    assert app.applicationVersion()=='1.15.0'
    original=(ROOT.parent/'v1.9/qml/RadialMenu.qml').read_text(encoding='utf8')
    expected=original.replace('{name:"Display",icon:"display"},{name:"Diagnostics",icon:"diagnostics"}', '{name:"Logs",icon:"logs"},{name:"Lobby",icon:"lobby"}').replace('["Alarms","Settings","Display","Diagnostics"]','["Alarms","Settings","Logs","Lobby"]')
    assert (ROOT/'qml/RadialMenu.qml').read_text(encoding='utf8')==expected
    checks.append('v1.9 More source identical except the two destination substitutions')
    shot('01-home-large')
    large=[find('charts0').width(),find('charts0').height()]
    left=find('charts0');right=find('charts1')
    gap=right.mapToScene(QPointF(0,0)).x()-left.mapToScene(QPointF(left.width(),0)).x()
    assert gap<=16,gap
    for size in ('Small','Medium','Large'):
        ctl.workspace.setGraphSize(size);QTest.qWait(30)
        assert ctl.workspace.graphSize==size
        assert find('dropPanel0').width()==find('charts0').width()
        assert find('dropPanel0').height()==find('charts0').height()
        if size=='Small':assert find('charts0').width()<large[0] and find('charts0').height()<large[1]
    checks.append('three graph sizes persist, with an enlarged default and narrow centre gap')
    click('more0');QTest.qWait(260)
    assert js('radial.visible')
    shot('02-more-v19')
    angle=math.radians(-100+3.5*36.25)
    QTest.mouseClick(window,Qt.LeftButton,pos=QPoint(round(63+270*math.cos(angle)),round(539+270*math.sin(angle))))
    QTest.qWait(280)
    assert find('lobby').isVisible()
    assert js('lobby.tiles.length')==20
    assert js('lobby.tiles.filter(tile=>!tile.placeholder).length')==17
    tiles=js('JSON.stringify(lobby.tiles)')
    cells=set()
    for tile in json.loads(tiles):
        assert find('lobbyTile_'+tile['key']).property('radius')==0
        for x in range(tile['col'],tile['col']+tile['cw']):
            for y in range(tile['row'],tile['row']+tile['rh']):
                assert (x,y) not in cells
                cells.add((x,y))
    assert cells=={(x,y) for x in range(8) for y in range(6)}
    shot('03-lobby')
    checks.append('packed square-corner Bento: 17 tools plus 3 placeholders, all 48 grid cells filled without overlap')
    click('lobbyTile_buttons');shot('04-buttons')
    click('shortcutAssignment0')
    # Keep the native pointer away from the popup while exercising keyboard
    # navigation; hover during an animated scroll can otherwise select a row.
    QTest.mouseMove(window,QPoint(20,20))
    QTest.qWait(250)
    target=next(i for i,a in enumerate(ctl.workspace.shortcutActions) if a['key']=='capture.screenshot')
    QTest.keyClick(window,Qt.Key_Home)
    for _ in range(target):
        QTest.keyClick(window,Qt.Key_Down);QTest.qWait(10)
    QTest.keyClick(window,Qt.Key_Return);QTest.qWait(60)
    assert ctl.workspace.shortcut(0)=='capture.screenshot',ctl.workspace.shortcut(0)
    for _ in range(30):
        ctl.navigation.move_focus(1)
        if ctl.navigation.target==find('shortcutAssignment0'):break
    assert ctl.navigation.target==find('shortcutAssignment0')
    ctl.navigation.activate();ctl.navigation.move_focus(1)
    assert ctl.workspace.shortcut(0)=='lobby.open'
    ctl.navigation.move_focus(-1);ctl.navigation.back()
    assert ctl.workspace.shortcut(0)=='capture.screenshot'
    ctl.navigation.clear_focus()
    click('orderUp_0_more')
    assert ctl.workspace.panelOrder(0)[3]=='more'
    assert find('more0').y()==415
    ctl.workspace.setShortcut(0,'capture.screenshot')
    assert SettingsStore(Path(data.name)/'settings.json').values['shortcut_left']=='capture.screenshot'
    assert SettingsStore(Path(data.name)/'settings.json').values['panel_order_left'][3]=='more'
    ctl.workspace.resetButtons()
    device=QTest.createTouchDevice()
    handle=find('reorderHandle_1_more')
    point=handle.mapToScene(QPointF(250,30)).toPoint()
    touch=QTest.touchEvent(window,device)
    touch.press(0,point,window).commit();QTest.qWait(30)
    for distance in (20,70,140,210,280):
        touch.move(0,point-QPoint(0,distance),window).commit();QTest.qWait(25)
    touch.release(0,point-QPoint(0,280),window).commit();QTest.qWait(50)
    assert ctl.workspace.panelOrder(1)[0]=='more',ctl.workspace.panelOrder(1)
    ctl.workspace.resetButtons()
    handle=find('reorderHandle_0_lock')
    point=handle.mapToScene(QPointF(250,30)).toPoint()
    QTest.mousePress(window,Qt.LeftButton,pos=point)
    for distance in (20,65,110,140):
        local=QPointF(point+QPoint(0,distance))
        event=QMouseEvent(QEvent.MouseMove,local,QPointF(window.mapToGlobal(local.toPoint())),Qt.NoButton,Qt.LeftButton,Qt.NoModifier)
        app.sendEvent(window,event);QTest.qWait(20)
    QTest.mouseRelease(window,Qt.LeftButton,pos=point+QPoint(0,140));QTest.qWait(50)
    assert ctl.workspace.panelOrder(0).index('lock')==2,ctl.workspace.panelOrder(0)
    ctl.workspace.resetButtons()
    checks.append('shortcut dropdown, mouse/touch reorder, immediate Home update and preference persistence')
    click('lobbyBack');click('lobbyTile_graphs');shot('05-graph-size')
    click('graphSize_Medium');assert ctl.workspace.graphSize=='Medium'
    click('graphSize_Large')
    click('lobbyBack');click('lobbyTile_monitor');QTest.qWait(1200);shot('06-monitor')
    assert len(ctl.workspace.metrics)==8
    click('lobbyBack');assert not ctl.workspace.monitor.isActive()
    click('lobbyTile_files');shot('07-files')
    assert ctl.workspace.folder==str(Path(data.name).resolve())
    click('lobbyBack');click('lobbyTile_laser');shot('08-laser')
    js('lobby.editParameter(0,"current")');QTest.qWait(50)
    assert find('keypad').isVisible()
    js('keypad.visible=false')
    click('lobbyBack');click('lobbyTile_sub');shot('09-sub-parameters')
    click('lobbyBack');click('lobbyTile_home');shot('10-home-controls')
    click('lobbyBack');click('lobbyTile_legal');shot('11-legal')
    click('lobbyBack');click('lobbyTile_dlc');shot('12-dlc')
    checks.append('File Manager, monitoring, graph sizing, parameter editors, Home Controls, Legal and DLC pages open')
    click('lobbyBack');click('lobbyTile_diagnostics');QTest.qWait(160)
    settings=ctl.settings_host.window
    assert settings.isVisible() and settings.content=='control'
    ctl.closeSettings();QTest.qWait(60)
    assert find('lobby').isVisible()
    checks.append('Diagnostics moved to Lobby and returns there from its existing interface')
    for key,section in [('manual','help'),('control','function'),('display','display'),('notifications','notifications'),('about','about')]:
        click('lobbyTile_'+key);QTest.qWait(100)
        assert settings.content==section,(key,settings.content)
        ctl.closeSettings();QTest.qWait(30)
    assert 'logs' not in settings.order
    settings.store.remember('brightness')
    ctl.openSettings();QTest.qWait(120);settings.activate(('history',));QTest.qWait(50);settings.repaint()
    hit=next(rect for rect,action in settings.hits if action==('history_item','brightness'))
    QTest.mouseClick(settings,Qt.LeftButton,pos=(settings.offset+hit.center()*settings.scale).toPoint())
    QTest.qWait(300)
    assert settings.search.text()=='brightness'
    assert settings.content=='display' and settings.overlay is None
    settings.store.remember('not-a-matching-setting')
    settings.activate(('history',));settings.activate(('history_item','not-a-matching-setting'))
    assert settings.overlay=='results'
    ctl.closeSettings()
    checks.append('history tap fills query and executes single-match or no-match search')
    click('lobbyTile_logs');QTest.qWait(200)
    logs=window.findChild(QObject,'logsWindow')
    assert logs.isVisible() and logs.visibility()==logs.Visibility.FullScreen
    assert not settings.isVisible()
    shot('13-logs-fullscreen',logs)
    ctl.workspace.setLogLevel('warning')
    ctl.journal.record('Lobby verification warning','Failed','warning','Test')
    QTest.qWait(200)
    assert any(r['description']=='Lobby verification warning' for r in ctl.workspace.logRows)
    ctl.workspace.toggleLogLive();count=len(ctl.workspace.logRows)
    ctl.journal.record('Paused warning','Failed','warning','Test');QTest.qWait(200)
    assert len(ctl.workspace.logRows)==count
    ctl.workspace.toggleLogLive();assert len(ctl.workspace.logRows)>count
    ctl.workspace.setLogLevel('all')
    for index in range(12):ctl.journal.record('Scroll anchor '+str(index))
    QTest.qWait(180)
    view=find('logList',logs.contentItem());view.setProperty('contentY',318.0)
    ctl.journal.record('A new log while reading older rows');QTest.qWait(200)
    assert abs(view.property('contentY')-424)<1,view.property('contentY')
    with patch('interaction.workspace.ROOT',Path(data.name)):
        ctl.workspace.exportLogs()
        assert (Path(data.name)/'exports/logs.csv').is_file()
    click('logsClear',logs);assert logs.property('confirmClear')
    before=ctl.journal.count();click('logsCancelClear',logs);assert ctl.journal.count()==before
    click('logsClear',logs);click('logsConfirmClear',logs);assert ctl.journal.count()==1
    ctl.navigation.move_focus(1);assert ctl.navigation.focus['active']
    ctl.navigation.back();QTest.qWait(50);assert not logs.isVisible()
    click('lobbyHome');click('more0');QTest.qWait(260)
    angle=math.radians(-100+2.5*36.25)
    QTest.mouseClick(window,Qt.LeftButton,pos=QPoint(round(63+270*math.cos(angle)),round(539+270*math.sin(angle))))
    QTest.qWait(300)
    assert logs.isVisible() and not settings.isVisible()
    click('logsClose',logs)
    ctl.workspace.openPage('lobby');QTest.qWait(80)
    checks.append('fullscreen Logs retains live/pause, level filter, reading position, export, confirmed clear and knob navigation')
    if '--native' in sys.argv:
        saved=[]
        ctl.workspace.screenshotSaved.connect(saved.append)
        click('lobbyTile_screenshot');QTest.qWait(800)
        assert saved,ctl.workspace.message
        image=QImage(saved[-1]);screen=window.screen()
        assert image.width()==round(screen.size().width()*screen.devicePixelRatio())
        assert image.height()==round(screen.size().height()*screen.devicePixelRatio())
        assert Path(saved[-1]).name.startswith('phototype_')
        image.save(str(output/'14-full-display-screenshot.png'))
        click('lobbyHome');click('shortcut0');QTest.qWait(800)
        assert len(saved)==2,ctl.workspace.message
        checks.append('real full-display PNG captured from Lobby and the assigned shortcut button')
    errors=[m for m in messages if any(k in m for k in ('ReferenceError','TypeError','Cannot assign','is not a type','Binding loop','Unable to assign'))]
    assert not errors,'\n'.join(errors)
    result=dict(passed=True,checks=checks,qml_messages=messages,graph_gap=gap)
    (output/'results.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    print(json.dumps(result,indent=2),flush=True)
finally:
    ctl.workspace.shutdown();ctl.session_lock.shutdown();ctl.knobs.shutdown();ctl.navigation.shutdown()
    ctl.system_settings.shutdown();ctl.notifications.timer.stop();ctl.timer.stop();ctl.settings_host.shutdown()
    window.close();engine.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)
    data.cleanup()
