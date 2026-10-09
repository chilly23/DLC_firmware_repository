"""Full-application benchmark. Separate preferences; synthetic inputs only.

runtime/python.exe tests/stress.py --native --seconds 10
Use --seconds 600 for an extended 30-minute, three-load soak.
"""
import argparse
import json
import os
import sys
import tempfile
import time
from copy import deepcopy
from pathlib import Path
from threading import Event

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--native',action='store_true')
    parser.add_argument('--seconds',type=float,default=10);parser.add_argument('--profile',action='store_true');args=parser.parse_args()
    if not args.native:os.environ['QT_QPA_PLATFORM']='offscreen'
    elif sys.platform=='win32':os.environ['QT_QPA_PLATFORM']='windows'
    os.environ['QT_QUICK_BACKEND']='software'
    from PySide6.QtCore import QCoreApplication,QEvent,qInstallMessageHandler
    from PySide6.QtTest import QTest
    from main import create_application
    from benchmark import Benchmark
    from hardware.gpio import GPIOWorker
    from hardware.replay import replay_process
    from hardware.config import ControlStore
    from hardware.metrics import Metrics
    from verify_v17 import TestDevice
    messages=[];qInstallMessageHandler(lambda kind,context,text:messages.append(text))
    tmp=tempfile.TemporaryDirectory();store=ControlStore(Path(tmp.name)/'controls.json')
    cfg=deepcopy(store.config)
    for knob in cfg['knobs']:knob['calibrated']=True
    store.commit(cfg)
    app,engine,ctl,w=create_application(skip_boot=True,data_dir=tmp.name,device=TestDevice(),
        gpio_factory=lambda config:GPIOWorker(config,process_target=replay_process))
    monitor=Benchmark(ctl,w,visible=False);results=[];actions=[];acks=[]
    ctl.knobs.panelAction.connect(actions.append)
    def until(condition,seconds=20):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            if condition():return
            QTest.qWait(10)
        raise AssertionError('Timed out waiting for input pipeline')
    output=ROOT/'tests/v117';output.mkdir(exist_ok=True)
    if args.profile:
        import cProfile
        profiler=cProfile.Profile();profiler.enable()
    try:
        w.resize(1600,720);until(lambda:ctl.knobs.armed=={0,1,3})
        worker=ctl.knobs.worker;worker.acknowledgement.connect(acks.append)
        QTest.qWait(300)
        for points in (100,1000,10000):
            monitor.set_points(points);ctl.performance=Metrics();monitor.metrics=Metrics();monitor.history=[]
            worker.metrics=Metrics()
            monitor.started=monitor.last_sample=monitor.last_beat=time.monotonic();monitor.last_cpu=time.process_time();monitor.last_swaps=monitor.swaps
            base_delivery=sum(ctl.knobs.delivery.values());base_button=len(actions)
            worker.submit('start_input',rate=200)
            started=time.monotonic();last_gesture=started;stalled=False
            while time.monotonic()-started<args.seconds:
                QTest.qWait(10)
                now=time.monotonic()
                if now-last_gesture>.5:
                    plot=ctl.navigation.find('absorption0Renderer')
                    plot.pan(3 if int(now)%2 else -3,0)
                    plot.zoom(1.01 if int(now)%2 else 1/1.01,350)
                    worker.submit('probe');last_gesture=now
                if not stalled and now-started>args.seconds/2:
                    Event().wait(.25);stalled=True
            stopid=worker.submit('stop_input')
            until(lambda:any(a['id']==stopid for a in acks))
            QTest.qWait(250);until(lambda:worker.mailbox.snapshot()['pending']==0)
            monitor.collect()
            report=monitor.report();report['points']=points
            expected=sum(f['count'] for f in ctl.knobs.snapshots.values())
            delivered=sum(ctl.knobs.delivery.values())
            report['exact_delivery']=dict(expected_rotation_steps=expected,delivered_rotation_steps=delivered,
                decoded_button_presses=worker.worker_metrics.get('counts',{}).get('accepted_button_presses',0),delivered_button_presses=len(actions))
            assert delivered==expected,report['exact_delivery']
            assert len(actions)==report['exact_delivery']['decoded_button_presses'],report['exact_delivery']
            assert all(a['ok'] for a in acks),acks
            results.append(report)
            w.grabWindow().save(str(output/f'home-{points}.png'))
            print(json.dumps(dict(points=points,delivery=report['exact_delivery'],rows=report['rows'][-1],queue=report['gpio']['queue'])),flush=True)
        errors=[m for m in messages if any(t in m for t in ('TypeError','ReferenceError','Binding loop','Cannot assign','Error:'))]
        assert not errors,errors
        (output/'stress.json').write_text(json.dumps(dict(results=results,warnings=messages),indent=2),encoding='utf8')
        print('PASS complete application, all three loads, concurrent input, UI gestures, forced stalls',flush=True)
    finally:
        if args.profile:
            import pstats
            profiler.disable()
            with (output/'input-runtime-profile.txt').open('w') as stream:pstats.Stats(profiler,stream=stream).sort_stats('cumtime').print_stats(35)
        (output/'last-runtime.json').write_text(json.dumps(monitor.report(),indent=2),encoding='utf8')
        monitor.shutdown();ctl.timer.stop();ctl.parameters.shutdown();ctl.workspace.shutdown();ctl.workspace.diagnostics.shutdown()
        ctl.notifications.timer.stop();ctl.knobs.shutdown();ctl.navigation.shutdown();ctl.session_lock.shutdown()
        ctl.settings_host.shutdown();ctl.system_settings.shutdown();ctl.journal.close();w.hide();engine.deleteLater()
        QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);tmp.cleanup()

if __name__=='__main__':main()
