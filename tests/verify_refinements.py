"""Event-level acceptance of v1.7 refinements with an isolated host adapter."""
import os,sys,time,tempfile,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
os.environ.setdefault('QT_QPA_PLATFORM','offscreen');os.environ.setdefault('QT_QUICK_BACKEND','software')
from PySide6.QtCore import Qt,QPointF,QPoint,QEvent,QCoreApplication,qInstallMessageHandler
from PySide6.QtTest import QTest
from main import create_application
from verify_v17 import TestDevice
from settings_ui.refined import FUNCTION_ROWS
from settings_ui.preferences import ACCENTS
from settings_ui.tour import TOUR
from settings_ui.locales import CATALOGS
from controller.alarms import AlarmMonitor

class SlowDevice(TestDevice):
    def set_level(self,key,value):time.sleep(.25);return super().set_level(key,value)

if __name__=='__main__':
    messages=[];qInstallMessageHandler(lambda kind,ctx,msg:messages.append(msg))
    tmp=tempfile.TemporaryDirectory();device=SlowDevice()
    app,engine,ctl,home=create_application(skip_boot=True,data_dir=tmp.name,device=device)
    sw=ctl.settings_host.window;system=ctl.system_settings;theme=ctl.theme;checks=[]
    out=ROOT/'tests/refinement-screenshots';out.mkdir(exist_ok=True)
    def check(name,condition):
        assert condition,name
        checks.append(name);print('PASS',name,flush=True)
    def wait_job():
        until=time.monotonic()+5
        while system.busy and time.monotonic()<until:QTest.qWait(20)
        assert not system.busy
    def page(key):
        sw.select(sw.order.index(key));sw.motion.position=sw.selected;sw.motion.target=None;sw.last_index=sw.selected
        QTest.qWait(60);sw.repaint()
    def pos(p):return QPoint(round(sw.offset.x()+p.x()*sw.scale),round(sw.offset.y()+p.y()*sw.scale))
    def hit(prefix):
        sw.repaint()
        return next((r,a) for r,a in reversed(sw.hits) if a[:len(prefix)]==prefix)
    def tap(prefix):
        # This suite tests the form controls; stacked-notice hit handling has
        # its own integration suite. Close prior feedback before targeting them.
        while ctl.notifications.cards:ctl.notifications.dismissId(ctl.notifications.cards[0]['id'])
        r,a=hit(prefix);QTest.mouseClick(sw,Qt.LeftButton,Qt.NoModifier,pos(r.center()));QTest.qWait(45)
    def item(name):
        stack=[home.contentItem()]
        while stack:
            o=stack.pop()
            if o.objectName()==name:return o
            stack.extend(o.childItems())
        raise AssertionError(name)
    def qtap(name):
        o=item(name);p=o.mapToScene(QPointF(o.width()/2,o.height()/2)).toPoint()
        QTest.mouseClick(home,Qt.LeftButton,Qt.NoModifier,p);QTest.qWait(60)
    def shot(name,settings=False):
        QTest.qWait(100);image=sw.grab() if settings else home.grabWindow();assert image.save(str(out/(name+'.png')))
    try:
        QTest.qWait(1400);shot('01-home')
        ctl.openSettings();wait_job();page('function');shot('02-function-table',True)
        check('Both laser columns have independent live controls',all(any(a[:3]==('table',i,'toggle') for r,a in sw.hits) for i in (0,1)))
        tap(('table',1,'toggle'))
        check('Table changes Laser 2 without changing Laser 1',theme.get('graph2')['auto_bandwidth'] and not theme.get('graph1')['auto_bandwidth'])
        sw.scroll=400;sw.repaint()
        tap(('table',1,'number','X minimum'))
        check('Numeric dropdown stays in the table',sw.number_drop and sw.route=='')
        sw.editor.setText('49.7');tap(('inline_key','Apply'))
        check('Inline numeric input changes the correct acquisition domain',ctl.instrument.lasers[1].signal.x_values[0]==49.7 and ctl.instrument.lasers[0].signal.x_values[0]==48.2)
        tap(('table',1,'number','X minimum'));sw.editor.setText('999');tap(('inline_key','Apply'))
        check('Invalid numeric span is rejected without closing the editor',sw.number_drop and bool(sw.numeric_error))
        tap(('inline_key','Cancel'));check('Cancel keeps the accepted value',theme.get('graph2')['x_min']==49.7)
        page('display');tap(('choose_setting','Accent color'))
        r=sw.drop_rect;old_scroll=sw.scroll
        start=pos(QPointF(r.center().x(),r.bottom()-35))
        QTest.mousePress(sw,Qt.LeftButton,Qt.NoModifier,start)
        for y in (r.bottom()-80,r.bottom()-140,r.bottom()-200,r.top()+30):QTest.mouseMove(sw,pos(QPointF(r.center().x(),y)),20)
        QTest.mouseRelease(sw,Qt.LeftButton,Qt.NoModifier,pos(QPointF(r.center().x(),r.top()+30)))
        QTest.qWait(180)
        check('Dropdown swipes scroll choices without scrolling the settings page',sw.drop_scroll>100 and sw.scroll==old_scroll and sw.dropdown is not None)
        sw.drop_velocity=0;sw.drop_scroll=999;sw.repaint();shot('03-palette-end',True)
        tap(('dropdown_value','White'));check('Last of all fifteen colors is reachable',theme.get('accent')=='White' and len(ACCENTS)==15)
        check('White and black accents retain contrasting ink',theme.accentInk=='#111111')
        theme.apply('accent','Black');check('Black accent has white text',theme.accentInk=='#FFFFFF');theme.apply('accent','Blue')
        page('display');r,a=hit(('hardware_slider','brightness'));p=pos(r.center())
        QTest.mousePress(sw,Qt.LeftButton,Qt.NoModifier,p)
        end=pos(QPointF(r.right()-50,r.center().y()));QTest.mouseMove(sw,end,30)
        before=sw.scroll;requested=sw.display_preview['brightness'];QTest.mouseRelease(sw,Qt.LeftButton,Qt.NoModifier,end)
        check('Slider preview survives pending hardware readback',sw.display_preview.get('brightness')==requested and system.busy)
        wait_job();check('One host write and no content scroll on slider gesture',device.calls[-1]==('brightness',requested) and len(device.calls)==1 and sw.scroll==before and 'brightness' not in sw.display_preview)
        shot('04-display',True)
        for language,catalog in CATALOGS.items():
            theme.apply('language',language)
            check(language+' has working translated navigation',theme.trText('Brightness')==catalog['Brightness'] and theme.trText('Brightness')!='Brightness')
        theme.apply('language','English')
        sw.close();QTest.qWait(80)
        locked=ctl.instrument.lasers[0].locked;o=item('lock0');p=o.mapToScene(QPointF(o.width()/2,o.height()/2)).toPoint()
        QTest.mousePress(home,Qt.LeftButton,Qt.NoModifier,p);QTest.qWait(920);QTest.mouseRelease(home,Qt.LeftButton,Qt.NoModifier,p);shot('05-tooltip')
        check('Long press shows tooltip without toggling the control',item('tooltipOverlay').isVisible() and ctl.instrument.lasers[0].locked==locked)
        QTest.mouseClick(home,Qt.LeftButton,Qt.NoModifier,QPoint(650,650));QTest.qWait(80)
        labels=item('chartLabels0');qtap('chartLabels0');qtap('tabYAxis');QTest.qWait(280)
        slider=item('heightRatio');p=slider.mapToScene(QPointF(slider.width()-5,30)).toPoint();QTest.mouseClick(home,Qt.LeftButton,Qt.NoModifier,p)
        check('Reference ratio slider controls the real chart',abs(ctl.instrument.lasers[0].chart.main_ratio-.8)<.001);shot('06-signals-axis')
        qtap('signalsClose');alarm=item('alarmPanel');alarm.open(0,0);QTest.qWait(70)
        home.openEditor(0,'alarm_main_high',0,False);QTest.qWait(70)
        check('Alarm numpad stacks above its panel',item('keypad').z()>alarm.z())
        qtap('key1');qtap('keyEnter');check('Alarm numpad touch commits a threshold',ctl.alarm(0)['main_high']==1)
        ctl.toggleAlarm(0);QTest.qWait(600)
        check('Live acquisition actually raises a trace alarm',ctl.alarm(0)['active'] and len(ctl.alarm(0)['events'])>0)
        ctl.acknowledgeAlarm(0);QTest.qWait(140);check('Acknowledgement preserves active condition',ctl.alarm(0)['active'] and ctl.alarm(0)['acknowledged'])
        shot('07-alarm')
        ctl.toggleEmission(0);QTest.qWait(200);check('Emission off suspends alarm evaluation',not ctl.alarm(0)['active'] and ctl.alarm(0)['status']=='Emission off')
        ctl.clearAlarmHistory(0);check('Alarm history clears independently',ctl.alarm(0)['events']==[])
        check('Negative absolute-error limit is rejected',bool(ctl.setValue(0,'alarm_error_high','-1')))
        monitor=AlarmMonitor();cfg=dict(enabled=True,main_high=10.,error_high=2.)
        monitor.update(cfg,True,11.,0.,.1)
        check('Alarm dwell rejects a brief spike',not monitor.active)
        monitor.update(cfg,True,11.,0.,.2);monitor.update(cfg,True,9.9,0.,.1)
        check('Alarm release margin prevents threshold chatter',monitor.active)
        monitor.update(cfg,True,9.7,0.,.1)
        check('Alarm clears after a genuine recovery',not monitor.active and 'Returned within limits' in monitor.events[0])
        alarm.setVisible(False)
        original=[l.chart.snapshot() for l in ctl.instrument.lasers]
        system.startTour();system.tourPause()
        for i,entry in enumerate(TOUR):
            system._tour=i;system.route_tour();QTest.qWait(18)
            if entry['section']:assert sw.content==entry['section'],(i,entry)
            if entry.get('row') is not None:assert 185<=sw.guide_focus.top()<672,(i,sw.guide_focus)
        check('Every guide step routes to its actual screen',len(TOUR)>65)
        i=next(i for i,t in enumerate(TOUR) if t['section']=='function' and t.get('row')==6)
        system._tour=i;system.route_tour();shot('08-tour-table',True)
        system.stopTour();check('Guide restores chart state and ends cleanly',original==[l.chart.snapshot() for l in ctl.instrument.lasers] and system.tourIndex==-1)
        errors=[m for m in messages if any(x in m for x in ('TypeError','ReferenceError','Cannot assign','Unable to assign','Binding loop','Error:'))]
        check('No Qt runtime errors across new controls and entire tour',not errors)
        (ROOT/'tests/refinement-validation.json').write_text(json.dumps(dict(checks=checks,tour_steps=len(TOUR),messages=messages,physical_hardware_tested=False),indent=2),encoding='utf8')
        print(len(checks),'checks passed')
    finally:
        print('\n'.join(messages));system.shutdown();ctl.settings_host.shutdown();ctl.timer.stop();home.close();engine.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete);tmp.cleanup()
