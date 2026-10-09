"""Exercise v1.17 through Qt, with isolated preferences and no physical GPIO writes."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
os.environ['QT_QUICK_BACKEND']='software'
os.environ['QT_QPA_PLATFORM']='windows' if '--native' in sys.argv else 'offscreen'
from PySide6.QtCore import QObject,QCoreApplication,QEvent,QPointF,QPoint,Qt,qInstallMessageHandler
from PySide6.QtTest import QTest
from PySide6.QtQml import QQmlExpression
from PySide6.QtGui import QImage,QMouseEvent
from verify_v17 import TestDevice
from main import create_application
from settings_ui.model import SettingsStore

messages=[]
qInstallMessageHandler(lambda kind,context,message:messages.append(message))
temporary=tempfile.TemporaryDirectory()
app,engine,ctl,window=create_application(skip_boot=True,data_dir=temporary.name,device=TestDevice(),gpio_autostart=False)
output=ROOT/'tests/v117';output.mkdir(exist_ok=True)
checks=[]

def check(label,condition):
    assert condition,label
    checks.append(label)
    print('PASS '+label,flush=True)

def js(code,obj=None):
    expression=QQmlExpression(engine.rootContext(),obj or window,code)
    result,undefined=expression.evaluate()
    assert not expression.hasError(),expression.error().toString()
    return result

def find(name,surface=None):
    stack=[(surface or window).contentItem()]
    while stack:
        item=stack.pop()
        if item.objectName()==name:return item
        stack.extend(item.childItems())
    raise AssertionError('Missing '+name)

def click(name,surface=None):
    target=find(name,surface)
    assert target.isVisible(),name+' hidden'
    point=target.mapToScene(QPointF(target.width()/2,target.height()/2)).toPoint()
    QTest.mouseClick(surface or window,Qt.LeftButton,pos=point)
    QTest.qWait(90)

def page(name):
    ctl.workspace.openPage(name);QTest.qWait(130)

def shot(name,surface=None):
    QTest.qWait(120)
    image=(surface or window).grabWindow()
    assert not image.isNull()
    image.save(str(output/(name+'.png')))

try:
    window.resize(1600,720);QTest.qWait(400)
    check('v1.17 starts at 1600 × 720',window.isVisible() and app.applicationVersion()=='1.17.0')
    check('Lobby and More wheel are unchanged from v1.16',all((ROOT/relative).read_bytes()==(ROOT.parent/'v1.16'/relative).read_bytes() for relative in ('qml/Lobby.qml','qml/RadialMenu.qml')))
    check('Device/display and installation logic are unchanged',all((ROOT/relative).read_bytes()==(ROOT.parent/'v1.16'/relative).read_bytes() for relative in [p.relative_to(ROOT.parent/'v1.16') for p in (ROOT.parent/'v1.16/device').rglob('*.py')]+[Path(n) for n in ('boot.py','install.py','setup.sh','startup.py','data/controls.json')]))
    page('lobby');shot('01-lobby')
    tiles=json.loads(js('JSON.stringify(lobby.tiles)'))
    cells=[]
    for tile in tiles:
        cells.extend((x,y) for x in range(tile['col'],tile['col']+tile['cw']) for y in range(tile['row'],tile['row']+tile['rh']))
    check('20 Bento cards fill 48 cells without overlap',len(tiles)==20 and len(cells)==len(set(cells))==48)
    click('lobbyTile_control');QTest.qWait(300);shot('02-control-parameters')
    check('Control Parameters opens its own page',js('lobby.page')=='control' and not ctl.settings_host.window.isVisible())
    row=find('control_0_current');point=row.mapToScene(QPointF(600,26)).toPoint()
    QTest.mousePress(window,Qt.LeftButton,pos=point);QTest.qWait(520);QTest.mouseRelease(window,Qt.LeftButton,pos=point);QTest.qWait(80)
    check('Live readback refresh does not interrupt a parameter press',find('keypad').isVisible())
    js('keypad.draft="250.125";keypad.key("enter")')
    check('Control edit updates the shared Home value',ctl.value(0,'current')==250.125)
    click('control_0_maximum_current');js('keypad.draft="200";keypad.key("enter")')
    check('Conflicting current limit is rejected in the numeric editor',bool(find('keypad').property('errorMessage')) and ctl.value(0,'maximum_current')==300)
    js('keypad.key("close")')
    click('controlLaser1');click('control_1_pid_i');js('keypad.draft="-48.2";keypad.key("enter")')
    check('Independent Laser 2 TC integral parameter is editable',ctl.value(1,'pid_i')==-48.2 and ctl.value(0,'pid_i')==-57)
    click('control_1_tc_enabled')
    check('Temperature enable toggle updates the model',not ctl.parameters.flags[1]['tc_enabled'])
    click('control_1_tc_enabled')
    click('control_0_cc_enabled');check('CC uses the existing emission confirmation',find('emissionConfirm').isVisible())
    js('cancel()',find('emissionConfirm'));QTest.qWait(600)
    check('Cancelling emission leaves the accepted state unchanged',ctl.instrument.lasers[1].emission)
    choice=find('controlModule0');click('controlModule0');QTest.qWait(250)
    check('Module dropdown opens all three visible rows',js('popup.visible && popup.height >= 140',choice))
    delegate=js('popup.contentItem.itemAtIndex(2)',choice)
    position=delegate.mapToScene(QPointF(delegate.width()/2,delegate.height()/2)).toPoint()
    QTest.mouseClick(delegate.window(),Qt.LeftButton,pos=position);QTest.qWait(250)
    check('Control module dropdown opens the PC fields',find('control_0_offset').isVisible())
    page('laser');shot('03-laser-config');click('laserConfig_1_temperature');js('keypad.draft="25.250";keypad.key("enter")')
    check('Laser Config edits use the same validated values',ctl.value(1,'temperature')==25.25)
    page('sub');shot('04-sub-parameters');click('sub_0_laser2');click('sub_1_laser2/cc');QTest.qWait(120)
    check('Parameter tree opens laser and module levels',find('sub_1_current').isVisible())
    click('sub_1_current');js('keypad.draft="190";keypad.key("enter")')
    check('Hierarchy leaf edits are synchronized',ctl.value(1,'current')==190)
    click('parameterEnter');click('parameterUp')
    check('Sub Parameters moves back one level',js('lobby.page')=='sub')
    page('home');shot('05-home-controls')
    choice=find('homeAssignment0');js('stepFromKnob(1)',choice);QTest.qWait(120)
    check('Home corner assignment updates immediately',ctl.instrument.lasers[0].top_field()=='temperature')
    ctl.selectField(0,False,'current');QTest.qWait(80)
    check('Knob selection preserves later external dropdown updates',find('homeAssignment0').property('currentValue')=='current')
    ctl.selectField(0,False,'temperature');QTest.qWait(80)
    click('homeEdit0');check('Corner Edit opens the assigned parameter',find('keypad').property('fieldKey')=='temperature');js('keypad.key("close")')
    ctl.parameters.save()
    check('Corner choices and control values persist',SettingsStore(Path(temporary.name)/'settings.json').values['control_state'][0]['top']=='temperature')
    page('buttons');shot('06-buttons')
    check('Screenshot is an available shortcut action',any(row['key']=='capture.screenshot' for row in ctl.workspace.shortcutActions))
    ctl.workspace.setShortcut(0,'capture.screenshot')
    click('orderUp_0_more')
    check('Button order updates Home',ctl.workspace.panelOrder(0)[3]=='more' and find('more0').y()==415)
    ctl.workspace.resetButtons()
    handle=find('reorderHandle_1_more');point=handle.mapToScene(QPointF(250,30)).toPoint()
    device=QTest.createTouchDevice();touch=QTest.touchEvent(window,device)
    touch.press(0,point,window).commit()
    for distance in (20,70,140,210,280):
        touch.move(0,point-QPoint(0,distance),window).commit();QTest.qWait(35)
    touch.release(0,point-QPoint(0,280),window).commit();QTest.qWait(100)
    check('Touch dragging reorders the side panel',ctl.workspace.panelOrder(1)[0]=='more')
    ctl.workspace.resetButtons()
    page('diagnostics');click('diagnoseSystem');QTest.qWait(250);shot('07-diagnostics')
    check('Diagnostics performs seven checks',len(ctl.workspace.diagnostics.rows)==7 and not ctl.workspace.diagnostics.busy)
    click('diagnosticsExport');check('Diagnostic reports are saved',bool(list((Path(temporary.name)/'exports').glob('diagnostics_*.json'))))
    click('screenCheck');screen=ctl.workspace.diagnostics.screen
    check('Screen Check opens independently of Settings',screen.isVisible() and not ctl.settings_host.window.isVisible())
    ctl.navigation.back();check('Screen Check returns to Diagnostics',not screen.isVisible() and js('lobby.page')=='diagnostics')
    page('monitor');QTest.qWait(1200);shot('08-system-monitoring')
    check('Monitoring exposes 12 live host/runtime values',len(ctl.workspace.metrics)==12 and ctl.workspace.metrics[0]['value']!='Collecting…')
    page('lobby');check('Monitoring polling stops when leaving its page',not ctl.workspace.monitor.isActive())
    for name in ('dlc','legal','manual'):
        click('lobbyTile_'+name);shot('09-'+name)
        check(name+' opens an honest placeholder',js('lobby.page')==name and not ctl.settings_host.window.isVisible())
        click('lobbyBack')
    page('graphs')
    for size in ('Small','Medium','Large'):
        click('graphSize_'+size);check(size+' graph size is applied',ctl.workspace.graphSize==size)
    if '--native' in sys.argv:
        page('lobby');saved=[];ctl.workspace.screenshotSaved.connect(saved.append)
        click('lobbyTile_screenshot')
        for _ in range(60):
            if saved:break
            QTest.qWait(100)
        check('Full-display PNG capture completes',bool(saved) and Path(saved[-1]).name.startswith('screenshot_'))
        capture=QImage(saved[-1]);screen=window.screen()
        check('Screenshot contains the full display dimensions',capture.width()==round(screen.size().width()*screen.devicePixelRatio()) and capture.height()==round(screen.size().height()*screen.devicePixelRatio()))
        js('lobby.visible=false');ctl.runShortcut(0)
        for _ in range(60):
            if len(saved)>1:break
            QTest.qWait(100)
        check('Assigned shortcut uses the same capture workflow',len(saved)==2)
    else:
        folder=Path(temporary.name)/'screenshots';folder.mkdir();image=QImage(400,200,QImage.Format_RGB32);image.fill(Qt.white);image.save(str(folder/'preview.png'))
    page('files');click('files_screenshots');shot('10-file-manager')
    images=[r for r in ctl.workspace.files if r['kind']=='image'];check('File Manager lists screenshots',bool(images))
    ctl.workspace.openFile(images[0]['path']);QTest.qWait(200);shot('11-screenshot-preview')
    check('Image opens inside the File Manager',find('filePreview').isVisible() and ctl.workspace.preview['kind']=='image')
    click('filePreviewClose');click('files_recordings');check('Recordings has a browsable folder',Path(ctl.workspace.folder).name=='recordings')
    for tag,status,level,source in [('Critical example','Failed','critical','Test'),('Warning example','Failed','warning','Test'),('Completed example','Passed','default','Parameter'),('Information example','Requested','default','System')]:ctl.journal.record(tag,status,level,source)
    ctl.workspace.openLogs();QTest.qWait(200);logs=window.findChild(QObject,'logsWindow');shot('12-logs',logs)
    check('Logs remains a separate fullscreen window',logs.isVisible() and logs.visibility()==logs.Visibility.FullScreen)
    check('Logs uses all four status colours',len({row['color'] for row in ctl.workspace.logRows})==4)
    click('logsExport',logs);click('logsClose',logs);click('files_exports');ctl.workspace.openFile(str(Path(temporary.name)/'exports/logs.md'))
    check('Exported logs are readable in File Manager',ctl.workspace.preview['kind']=='text' and 'Critical example' in ctl.workspace.preview['text'])
    ctl.workspace.closePreview()
    ctl.notifications.waiting.clear()
    for row in list(ctl.notifications.cards):ctl.notifications.dismissId(row['id'])
    ctl.notifications.post('Screenshot ready for review',key='test-progress');QTest.qWait(350)
    notice=next(e for e in ctl.notifications.cards if e['key']=='test-progress');ring=find('noticeProgress'+str(notice['id']))
    check('Dismiss control displays an advancing countdown ring',ring.isVisible() and 0<notice['remaining']<1)
    shot('13-countdown-notification')
    deadline=notice['deadline'];ctl.notifications.post('Screenshot ready for review',key='test-progress')
    check('Duplicate notice does not restart its timer',ctl.notifications.cards[0]['deadline']==deadline)
    for n in range(12):ctl.notifications.post('Burst '+str(n))
    check('Notification stack remains bounded to two cards',len(ctl.notifications.cards)<=2)
    ctl.theme.apply('appearance','Light');page('control');shot('14-control-light');page('lobby');shot('15-lobby-light');ctl.theme.apply('appearance','Dark')
    for name,section in [('display','display'),('notifications','notifications'),('system','system'),('function','function'),('help','help'),('about','about')]:
        page('lobby');click('lobbyTile_'+name);QTest.qWait(100)
        check('Lobby route '+name+' opens and returns',ctl.settings_host.window.isVisible() and ctl.settings_host.window.content==section)
        ctl.closeSettings();QTest.qWait(60)
    check('No runtime QML warnings',not messages)
    result=dict(passed=len(checks),checks=checks,native='--native' in sys.argv,qml_messages=messages)
    (output/'validation.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    print(json.dumps(dict(passed=len(checks),output=str(output)),indent=2),flush=True)
finally:
    ctl.timer.stop();ctl.parameters.shutdown();ctl.workspace.shutdown();ctl.workspace.diagnostics.shutdown();ctl.notifications.timer.stop()
    ctl.knobs.shutdown();ctl.navigation.shutdown();ctl.session_lock.shutdown();ctl.settings_host.shutdown();ctl.system_settings.shutdown()
    ctl.journal.close();window.hide();engine.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)
    temporary.cleanup()
