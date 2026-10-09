"""Exercise the real Qt UI; an injected device records host writes safely."""
import os,sys,tempfile,time,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
os.environ.setdefault('QT_QPA_PLATFORM','offscreen');os.environ.setdefault('QT_QUICK_BACKEND','software')
from PySide6.QtCore import QPointF,QPoint,Qt,QCoreApplication,QEvent,qInstallMessageHandler
from PySide6.QtTest import QTest
from main import create_application
from settings_ui.model import SettingsStore
from settings_ui.layout import SEARCH_GROUP,KEYBOARD_RECT


class TestDevice:
    def __init__(self):self.calls=[];self.mode=[1600,720,60];self.brightness=70;self.contrast=50;self.fail=False
    def probe(self):return dict(platform='Test host',target='Injected test display',modes=[[1600,720,60],[1920,1080,60],[1920,1080,75]],current=self.mode[:],brightness=self.brightness,contrast=self.contrast,reasons={})
    def set_level(self,key,value):
        self.calls.append((key,value))
        if self.fail:raise RuntimeError('Permission denied by test device')
        setattr(self,key,value);return value
    def set_mode(self,mode):self.calls.append(('mode',mode));self.mode=list(mode);return self.mode[:]
    def set_time(self,value):self.calls.append(('time',value));return value
    def power(self,action):self.calls.append(('power',action));return action


if __name__=='__main__':
    messages=[];qInstallMessageHandler(lambda kind,ctx,msg:messages.append(msg));data=tempfile.TemporaryDirectory();device=TestDevice()
    app,engine,ctl,w=create_application(skip_boot=True,data_dir=data.name,device=device)
    syssettings=ctl.system_settings;theme=ctl.theme;sw=ctl.settings_host.window;checks=[]
    out=ROOT/'tests'/'v17-screenshots';out.mkdir(exist_ok=True)
    def check(name,value):assert value,name;checks.append(name);print('PASS',name,flush=True)
    def wait(predicate,ms=5000):
        end=time.monotonic()+ms/1000
        while not predicate() and time.monotonic()<end:QTest.qWait(25)
        assert predicate(),'Timed out'
    def item(name):
        stack=[w.contentItem()]
        while stack:
            obj=stack.pop()
            if obj.objectName()==name:return obj
            stack.extend(obj.childItems())
        raise AssertionError(name)
    def tap(name):
        o=item(name);p=o.mapToScene(QPointF(o.width()/2,o.height()/2)).toPoint();QTest.mouseClick(w,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,p);QTest.qWait(100)
    def screenshot(name,settings=False):
        QTest.qWait(150);im=sw.grab() if settings else w.grabWindow();assert im.save(str(out/(name+'.png')))
    def page(key):sw.select(sw.order.index(key));sw.motion.position=sw.selected;sw.last_index=sw.selected;QTest.qWait(350);sw.repaint()
    try:
        QTest.qWait(1800);check('Application v1.11 starts',w.isVisible() and app.applicationVersion()=='1.11.0');screenshot('01-home')
        tap('more0');QTest.qWait(300);check('Restored ring reveal completes',item('radialMenu').property('expansion')==1);screenshot('02-ring');tap('radialCancel');QTest.qWait(300)
        ctl.openSettings();wait(lambda:not syssettings.busy);QTest.qWait(150)
        check('Fixed settings navigation order',sw.order==['display','function','control','system','storage','help','upgrade','about'])
        check('Search and history centered together',abs(SEARCH_GROUP.center().x()-800)<.01)
        check('Keyboard is taller with 36px clearance',KEYBOARD_RECT.height()==456 and KEYBOARD_RECT.bottom()==684)
        check('Supplied QR copied exactly',hashlib.sha256((ROOT/'assets/qr.png').read_bytes()).digest()==hashlib.sha256((ROOT.parents[1]/'qr.png').read_bytes()).digest())
        page('about');screenshot('03-about',True)
        page('display');screenshot('04-display',True)
        syssettings.set_level('brightness',44);wait(lambda:not syssettings.busy)
        check('Brightness writes host and uses readback',device.calls[-1]==('brightness',44) and syssettings.caps['brightness']==44)
        device.fail=True;syssettings.set_level('contrast',77);wait(lambda:not syssettings.busy)
        check('Failed hardware write preserves accepted value',syssettings.caps['contrast']==50 and 'Permission denied' in syssettings.status);device.fail=False
        syssettings.change_mode([1920,1080,75]);wait(lambda:not syssettings.busy)
        check('Resolution and refresh sent together to host',device.mode==[1920,1080,75] and syssettings.modeSeconds>0)
        syssettings.mode_deadline=time.monotonic()-.1;syssettings.tick();wait(lambda:not syssettings.busy)
        check('Unconfirmed display mode rolls back',device.mode==[1600,720,60])
        syssettings.change_mode([1920,1080,60]);wait(lambda:not syssettings.busy);syssettings.keep_mode();check('Keep cancels rollback',syssettings.modeSeconds==0 and syssettings.mode_before is None)
        theme.apply('accent','Purple');QTest.qWait(100);check('Accent updates supplied palette tile',item('topParameter0').property('color').name()=='#bf5af2')
        theme.apply('appearance','Light');QTest.qWait(100);screenshot('05-light-display',True)
        sw.close();QTest.qWait(150);screenshot('06-light-home');check('Home background follows appearance',w.property('color').name()=='#edf0e9')
        theme.apply('button_labels',True);check('Side captions update',item('lock0').property('caption')=='Lock');screenshot('07-side-labels')
        theme.apply('language','Français');QTest.qWait(100);check('Home labels translate live',item('lock0').property('caption')=='Verrou')
        theme.apply('font_scale',1.1);theme.apply('ui_scale',1.1);check('Font and UI scaling are active',abs(theme.textScale-1.21)<.001)
        theme.apply('language','English');theme.apply('appearance','Dark');theme.apply('font_scale',1.);theme.apply('ui_scale',1.)
        ctl.openSettings();page('help');screenshot('08-help',True);sw.activate(('page_nav','help:Graphs'));QTest.qWait(350);sw.repaint()
        check('Help opens document inside right panel',sw.route=='help:Graphs' and sw.content_height>487)
        sw.scroll=sw.clamp_scroll(200);screenshot('09-help-document',True);check('Help document scrolls',sw.scroll==200)
        sw.back();check('Help Back restores topic list',sw.route=='')
        page('function');sw.activate(('page_nav','processing'));QTest.qWait(350);screenshot('10-processing',True)
        other=ctl.instrument.lasers[1].signal.config.copy()
        syssettings.set_graph(0,'max_points',512);QTest.qWait(150);check('Maximum points changes actual sample buffers',len(ctl.instrument.lasers[0].signal.raw_s)==512)
        theme.apply('sampling_rate',30);check('Sampling rate changes actual timer',ctl.timer.interval()==33)
        syssettings.set_graph(0,'auto_bandwidth',True);check('Bandwidth changes signal processing',ctl.instrument.lasers[0].signal.config['auto_bandwidth'])
        QTest.qWait(300);syssettings.calibrate(0);check('Baseline captures current signal median',abs(theme.store.values['graph1']['baseline_main'])>.1)
        syssettings.calibrate(0,True);check('Baseline reset removes offset',theme.store.values['graph1']['baseline_main']==0)
        syssettings.set_graph(0,'x_min',49.);check('X limit changes acquired domain',ctl.instrument.lasers[0].signal.x_values[0]==49.)
        check('Invalid graph span rejected',not syssettings.set_graph(0,'x_max',48.))
        syssettings.set_graph(0,'main_max',12.);check('Y limits update actual chart bounds',ctl.instrument.lasers[0].chart.bounds(False)==(-1.,12.))
        syssettings.set_graph(0,'line_width',3.);syssettings.set_graph(0,'graph_color','#F17DAD');check('Graph styling stored per laser',ctl.preferences['graph1']['line_width']==3. and ctl.preferences['graph2']['line_width']==1.7)
        check('Other laser keeps independent graph settings',ctl.instrument.lasers[1].signal.config['max_points']==1001 and not ctl.instrument.lasers[1].signal.config['auto_bandwidth'])
        page('function');sw.activate(('page_nav','limits'));QTest.qWait(350);sw.activate(('edit_setting','X minimum','x_min'));QTest.qWait(350)
        sw.editor.setText('50.2');sw.commit_editor();check('Settings numeric editor commits to graph',theme.store.values['graph1']['x_min']==50.2)
        page('system');screenshot('11-system',True);syssettings.change_time('2026-09-25 12:00:00');wait(lambda:not syssettings.busy);check('Clock operation delegates to host',device.calls[-1]==('time','2026-09-25 12:00:00'))
        theme.apply('idle_minutes',1);syssettings.idle_since=time.monotonic()-61;syssettings.tick();check('Idle action has cancellable countdown',syssettings.powerSeconds>0)
        syssettings.cancel_power();check('Power cancel resets idle timer',syssettings.powerSeconds==0)
        syssettings.power_deadline=time.monotonic()-.1;syssettings.tick();wait(lambda:not syssettings.busy);check('Expired countdown invokes host action',device.calls[-1]==('power','sleep'));theme.apply('idle_minutes',0)
        page('storage');screenshot('12-storage',True)
        path=syssettings.export(True);check('Graph export contains actual samples',path.exists() and 'spectroscopy_V' in path.read_text())
        path.unlink()
        check('Search indexes the new processing controls',sw.store.search('baseline')[0][0]=='function')
        sw.open_search();sw.search.setText('baseline');sw.close_overlay();sw.activate(('history',));check('Actual history remains persistent',SettingsStore(sw.store.path).history[0]=='baseline');sw.activate(('clear_history',));check('Clear removes history on disk',SettingsStore(sw.store.path).history==[]);sw.close_overlay()
        sw.open_search();screenshot('13-keyboard',True);sw.close_overlay()
        syssettings.startTour();syssettings.tourPause();QTest.qWait(350);check('Tour opens on actual home',w.isVisible() and syssettings.tourIndex==0);screenshot('14-tour-home')
        for _ in range(5):syssettings.tourNext()
        QTest.qWait(350);check('Tour opens real Signals panel',item('signalsPanel').isVisible())
        syssettings.tourNext();check('Tour opens fullscreen',w.property('fullscreenSide')==0)
        syssettings.tourNext();QTest.qWait(150);check('Tour covers More controls',syssettings.tourIndex==7)
        syssettings.tourNext();QTest.qWait(350);check('Tour navigates actual Settings section',sw.isVisible() and sw.content=='display');screenshot('15-tour-settings',True)
        syssettings.stopTour();check('Skip ends tour',syssettings.tourIndex==-1)
        syssettings.restore();check('Restore resets graph and appearance',theme.get('accent')=='Green' and theme.get('graph1')['max_points']==1001)
        errors=[m for m in messages if any(s in m for s in ('TypeError','ReferenceError','Cannot assign','Unable to assign','Binding loop','failed to load','Error:'))]
        check('No Qt/QML runtime errors',not errors)
        (ROOT/'tests/v17-validation.json').write_text(json.dumps(dict(checks=checks,messages=messages,host_commands=device.calls,physical_hardware_tested=False),indent=2),encoding='utf8')
        print(len(checks),'checks passed')
    finally:
        print('\n'.join(messages));syssettings.shutdown();ctl.settings_host.shutdown();ctl.timer.stop();w.close();engine.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);data.cleanup()
