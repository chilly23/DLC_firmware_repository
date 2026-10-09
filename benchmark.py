"""Isolated performance profile and operator controls; never loaded in normal mode."""
from copy import deepcopy
from datetime import datetime, timezone
import ctypes
import json
import os
from pathlib import Path
import platform
import shutil
import sys
import time

from PySide6.QtCore import Qt,QTimer
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QSlider,QPushButton,QCheckBox
from hardware.metrics import Metrics


def memory_bytes():
    if sys.platform=='linux':
        return int(Path('/proc/self/statm').read_text().split()[1])*os.sysconf('SC_PAGE_SIZE')
    if sys.platform=='win32':
        class Counters(ctypes.Structure):
            _fields_=[('cb',ctypes.c_ulong),('faults',ctypes.c_ulong)]+[(n,ctypes.c_size_t) for n in
                ('peak','rss','peakpaged','paged','peaknonpaged','nonpaged','pagefile','peakpagefile')]
        c=Counters();c.cb=ctypes.sizeof(c)
        kernel=ctypes.WinDLL('kernel32');kernel.GetCurrentProcess.restype=ctypes.c_void_p
        psapi=ctypes.WinDLL('psapi')
        psapi.GetProcessMemoryInfo.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_ulong]
        if psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(),ctypes.byref(c),c.cb):return int(c.rss)
    return None


def prepare(root,physical=False):
    folder=Path(root)/'benchmark'/('hardware' if physical else 'replay')/'data';folder.mkdir(parents=True,exist_ok=True)
    for name in ('settings.json','controls.json'):
        source=Path(root)/'data'/name
        if source.exists() and not (folder/name).exists():shutil.copy2(source,folder/name)
    if not physical:
        from hardware.config import ControlStore
        store=ControlStore(folder/'controls.json');cfg=deepcopy(store.config)
        for knob in cfg['knobs']:knob['calibrated']=True
        store.commit(cfg)
    return folder


class Benchmark(QWidget):
    def __init__(self,ctl,window,*,physical=False,visible=True):
        super().__init__()
        self.ctl,self.window,self.physical=ctl,window,physical
        self.metrics=Metrics();self.history=[];self.points=1001
        self.started=time.monotonic();self.last_beat=self.started;self.last_sample=self.started
        self.last_cpu=time.process_time();self.swaps=0;self.last_swaps=0;self.running=False
        self.setWindowTitle('Nexatom v1.17 · Benchmark configuration')
        self.setWindowFlags(Qt.WindowType.Tool|Qt.WindowType.WindowStaysOnTopHint)
        self.setMinimumSize(640,460)
        self.setStyleSheet('QWidget {background:#222;color:#D9D9D9;font:16px Roboto;} QPushButton {padding:12px;background:#444;border-radius:5px;}')
        box=QVBoxLayout(self)
        self.heading=QLabel('Performance test · '+('PHYSICAL GPIO' if physical else 'SYNTHETIC INPUTS · NO GPIO ACCESS'));box.addWidget(self.heading)
        self.value=QLabel();box.addWidget(self.value)
        self.slider=QSlider(Qt.Orientation.Horizontal);self.slider.setObjectName('benchmarkPoints')
        self.slider.setRange(100,10000);self.slider.setValue(1001);self.slider.setSingleStep(100)
        self.slider.valueChanged.connect(self.set_points);box.addWidget(self.slider)
        self.full=QCheckBox('Stress raster: draw every point (may reduce frame rate)');self.full.setChecked(False)
        self.full.toggled.connect(lambda v:setattr(ctl,'benchmark_full_detail',v));box.addWidget(self.full)
        row=QHBoxLayout();box.addLayout(row)
        self.input=QPushButton('Start synthetic input');self.input.setEnabled(not physical)
        self.input.clicked.connect(self.toggle_input);row.addWidget(self.input)
        probe=QPushButton('Probe owner');probe.clicked.connect(self.probe);row.addWidget(probe)
        export=QPushButton('Save report');export.clicked.connect(self.export);row.addWidget(export)
        self.readout=QLabel('Collecting measurements…');self.readout.setWordWrap(True);self.readout.setMinimumHeight(96);box.addWidget(self.readout)
        self.result=QLabel('Reports: benchmark/reports · normal preferences are untouched');self.result.setWordWrap(True);box.addWidget(self.result)
        window.frameSwapped.connect(self.frame_swapped)
        self.beat=QTimer(self);self.beat.setTimerType(Qt.TimerType.PreciseTimer);self.beat.setInterval(10)
        self.beat.timeout.connect(self.heartbeat);self.beat.start()
        self.sample=QTimer(self);self.sample.setInterval(1000);self.sample.timeout.connect(self.collect);self.sample.start()
        ctl.benchmark_full_detail=False
        self.set_points(1001)
        if visible:self.show()

    def frame_swapped(self):self.swaps+=1

    def heartbeat(self):
        now=time.monotonic();self.metrics.observe('ui_heartbeat_lateness',max(0,now-self.last_beat-.01)*1e9);self.last_beat=now

    def set_points(self,value):
        self.points=max(100,min(10000,int(value)))
        self.ctl.benchmark_points=self.points
        values=deepcopy(self.ctl.preferences)
        for i in (1,2):values['graph'+str(i)]['max_points']=self.points
        self.ctl.configure(values)
        self.value.setText(f'Points per signal: {self.points:,}   (100 – 10,000)')

    def toggle_input(self):
        worker=self.ctl.knobs.worker
        if not worker:return
        self.running=not self.running
        worker.submit('start_input' if self.running else 'stop_input',rate=200)
        self.input.setText('Stop synthetic input' if self.running else 'Start synthetic input')

    def probe(self):
        worker=self.ctl.knobs.worker
        if worker and hasattr(worker,'submit'):worker.submit('probe')

    def collect(self):
        now=time.monotonic();cpu=time.process_time();dt=now-self.last_sample
        row=dict(elapsed_s=now-self.started,points=self.points,
            cpu_one_core_percent=100*(cpu-self.last_cpu)/dt,rss_bytes=memory_bytes(),
            presented_fps=(self.swaps-self.last_swaps)/dt)
        self.last_sample,self.last_cpu,self.last_swaps=now,cpu,self.swaps
        self.history.append(row)
        if len(self.history)>36000:del self.history[:18000]
        perf=self.ctl.performance.snapshot()['timings'];inp=self.ctl.knobs.metrics();queue=inp.get('queue',{})
        p95=lambda name:perf.get(name,{}).get('p95_ms',0)
        latency=inp.get('delivery',{}).get('timings',{}).get('knob_to_application',{}).get('p95_ms',0)
        self.readout.setText(f"Presented {row['presented_fps']:.1f} fps · CPU {row['cpu_one_core_percent']:.1f}% of one core\n"
            f"App RSS {(row['rss_bytes'] or 0)/2**20:.1f} MiB · queue {queue.get('pending',0)} / peak {queue.get('high_water',0)}\n"
            f"Simulation p95 {p95('simulation_step'):.2f} ms · plot paint p95 {p95('plot_paint'):.2f} ms\n"
            f"Knob → application p95 {latency:.2f} ms")

    def report(self):
        return dict(version='1.17.0',source='physical GPIO' if self.physical else 'synthetic electrical replay',
            os=platform.platform(),machine=platform.machine(),python=sys.version,qt_platform=self.ctl.settings_host.app.platformName() if hasattr(self.ctl.settings_host,'app') else os.environ.get('QT_QPA_PLATFORM','native'),
            renderer=os.environ.get('QT_QUICK_BACKEND','platform default'),points=self.points,
            full_detail=self.ctl.benchmark_full_detail,duration_s=time.monotonic()-self.started,
            rows=self.history,ui=self.metrics.snapshot(),graph=self.ctl.performance.snapshot(),gpio=self.ctl.knobs.metrics(),
            notes=['CPU and RSS refer to the application process; child driver timing is in gpio.capture.',
                   'Plot paint is CPU paint time; presented_fps is the Qt frameSwapped rate, not panel scanout.',
                   'Button timings start at debounce completion; add configured stable interval for contact-to-app latency.',
                   'GPIO is input-only. Driver command ACK means completed userspace/libgpiod work, not laser/MCU acknowledgement.',
                   'No hard realtime or unmeasured physical GPIO latency claim.'])

    def export(self):
        folder=Path(__file__).resolve().parent/'benchmark'/'reports';folder.mkdir(parents=True,exist_ok=True)
        path=folder/('report-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json')
        path.write_text(json.dumps(self.report(),indent=2),encoding='utf8');self.result.setText('Saved: benchmark/reports/\n'+path.name);return path

    def shutdown(self):self.beat.stop();self.sample.stop();self.close()
