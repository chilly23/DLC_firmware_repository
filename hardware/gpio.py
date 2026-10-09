"""libgpiod v2 edge capture. GPIO ownership and decoding stay off the UI thread."""
from copy import deepcopy
from datetime import timedelta
from glob import glob
import time
from PySide6.QtCore import QThread,Signal
from .decoder import Decoder

def gpio_module():
    import gpiod
    if not hasattr(gpiod,'request_lines'):raise RuntimeError('libgpiod Python v2 is required. Run the v1.9 Pi launcher setup.')
    return gpiod

def discover(gpiod):
    result=[]
    for path in sorted(glob('/dev/gpiochip*')):
        try:
            with gpiod.Chip(path) as chip:
                info=chip.get_info()
                result.append(dict(path=path,label=info.label,lines=info.num_lines))
        except OSError as exc:result.append(dict(path=path,label=str(exc),lines=0))
    return result

class GPIOWorker(QThread):
    frames=Signal(object)
    status=Signal(bool,str)
    def __init__(self,config):super().__init__();self.config=deepcopy(config)
    def run(self):
        try:
            gpiod=gpio_module()
            from gpiod.line import Direction,Edge,Bias,Value
            path=self.config['chip']
            if path=='auto':
                candidates=[c['path'] for c in discover(gpiod) if 'rp1' in c['label'].lower() and c['lines']>=28]
                if len(candidates)!=1:raise RuntimeError('Cannot identify one RP1 GPIO chip. Check GPIO access; select the chip in data/controls.json.')
                path=candidates[0]
            knobs={i:k for i,k in enumerate(self.config['knobs']) if k['enabled'] and k['pins']}
            if not knobs:self.status.emit(False,'All wired knobs are disabled.');return
            reverse={pin:(i,name) for i,k in knobs.items() for name,pin in k['pins'].items()}
            pins=list(reverse)
            with gpiod.Chip(path) as chip:
                busy=[f'GPIO{p}: {chip.get_line_info(p).consumer or "kernel driver"}' for p in pins if chip.get_line_info(p).used]
                if busy:raise RuntimeError('Pins already in use: '+'; '.join(busy)+'. Close the RKJXT demo or conflicting GPIO program.')
            settings=gpiod.LineSettings(direction=Direction.INPUT,edge_detection=Edge.BOTH,bias=Bias.PULL_UP,active_low=False)
            with gpiod.request_lines(path,consumer='nexatom-v18-knobs',config={tuple(pins):settings},event_buffer_size=4096) as request:
                def levels():
                    values=request.get_values(pins);result={i:{} for i in knobs}
                    for pin,value in zip(pins,values):
                        i,name=reverse[pin];result[i][name]=int(value==Value.ACTIVE)
                    return result
                initial=levels();now=time.monotonic_ns()
                decoders={i:Decoder(k,initial[i],now) for i,k in knobs.items()}
                self.status.emit(True,f'{path} · pull-ups · {len(knobs)} wired knobs')
                self.frames.emit({i:d.snapshot() for i,d in decoders.items()})
                last_seq=None;discard_before=0;published=time.monotonic()
                while not self.isInterruptionRequested():
                    if request.wait_edge_events(timeout=timedelta(milliseconds=4)):
                        for event in request.read_edge_events(max_events=512):
                            if event.timestamp_ns<discard_before:last_seq=event.global_seqno;continue
                            if last_seq is not None and event.global_seqno!=last_seq+1:
                                fresh=levels();discard_before=time.monotonic_ns()
                                for i,d in decoders.items():d.resync(fresh[i],discard_before)
                                last_seq=event.global_seqno;continue
                            last_seq=event.global_seqno;i,name=reverse[event.line_offset]
                            decoders[i].edge(name,int(event.event_type==gpiod.EdgeEvent.Type.RISING_EDGE),event.timestamp_ns)
                    now=time.monotonic_ns()
                    for d in decoders.values():d.settle(now)
                    if time.monotonic()-published>=1/60:
                        self.frames.emit({i:d.snapshot() for i,d in decoders.items()});published=time.monotonic()
        except Exception as exc:self.status.emit(False,f'{type(exc).__name__}: {exc}')
    def stop(self):self.requestInterruption();self.wait()
