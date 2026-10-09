"""libgpiod v2 edge capture. GPIO ownership and decoding stay off the UI thread."""
from copy import deepcopy
from datetime import timedelta
from glob import glob
import time
from PySide6.QtCore import QThread,Signal
from .decoder import Decoder
from .panel import PanelDecoder

def gpio_module():
    import gpiod
    if not hasattr(gpiod,'request_lines'):raise RuntimeError('libgpiod Python v2 is required. Run the v1.12 Pi launcher setup.')
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
    panelFrames=Signal(object)
    availability=Signal(object)
    def __init__(self,config):super().__init__();self.config=deepcopy(config)
    def run(self):
        try:
            gpiod=gpio_module()
            from gpiod.line import Direction,Edge,Bias,Value
            path=self.config['chip']
            if path=='auto':
                chips=discover(gpiod)
                candidates=[c['path'] for c in chips if 'rp1' in c['label'].lower() and c['lines']>=28]
                if len(candidates)!=1:
                    detail='; '.join(c['path']+': '+c['label'] for c in chips) or 'No /dev/gpiochip devices found'
                    raise RuntimeError('Cannot identify one RP1 GPIO chip. '+detail+'. Check GPIO access or select the chip in data/controls.json.')
                path=candidates[0]
            knobs={i:k for i,k in enumerate(self.config['knobs']) if k['enabled'] and k['pins']}
            reverse={pin:(i,name) for i,k in knobs.items() for name,pin in k['pins'].items()}
            panel={k:v for k,v in self.config.get('panel',{}).items() if v['enabled']}
            reverse.update({v['pin']:('panel',k) for k,v in panel.items()})
            if not reverse:self.status.emit(False,'All wired inputs are disabled.');return
            pins=list(reverse)
            with gpiod.Chip(path) as chip:
                info={p:chip.get_line_info(p) for p in pins}
                busy={p:f'GPIO{p}: {line.consumer or "kernel driver"}' for p,line in info.items() if line.used}
            issues={}
            # Skip only the affected control. Never take a line from another
            # process, and never decode a knob with an incomplete set of pins.
            for index,knob in list(knobs.items()):
                conflicts=[busy[p] for p in knob['pins'].values() if p in busy]
                if conflicts:issues['knob:'+str(index)]='; '.join(conflicts);del knobs[index]
            for key,contact in list(panel.items()):
                if contact['pin'] in busy:issues['panel:'+key]=busy[contact['pin']];del panel[key]
            self.availability.emit(issues)
            reverse={p:(i,name) for i,k in knobs.items() for name,p in k['pins'].items()}
            reverse.update({v['pin']:('panel',k) for k,v in panel.items()})
            pins=list(reverse)
            if not pins:raise RuntimeError('GPIO inputs busy: '+'; '.join(busy.values()))
            settings=gpiod.LineSettings(direction=Direction.INPUT,edge_detection=Edge.BOTH,bias=Bias.PULL_UP,active_low=False)
            with gpiod.request_lines(path,consumer='nexatom-v18-knobs',config={tuple(pins):settings},event_buffer_size=4096) as request:
                def levels():
                    values=request.get_values(pins);result={i:{} for i in knobs};result['panel']={}
                    for pin,value in zip(pins,values):
                        i,name=reverse[pin];result[i][name]=int(value==Value.ACTIVE)
                    return result
                initial=levels();now=time.monotonic_ns()
                decoders={i:Decoder(k,initial[i],now) for i,k in knobs.items()}
                panel_decoder=PanelDecoder(panel,initial['panel'],now)
                summary=f'{path} · reading {len(knobs)} knobs / {len(panel)} panel inputs'
                if busy:summary+=' · Unavailable: '+'; '.join(busy.values())
                self.status.emit(True,summary)
                self.frames.emit({i:d.snapshot() for i,d in decoders.items()})
                self.panelFrames.emit(panel_decoder.snapshot())
                last_seq=None;discard_before=0;published=time.monotonic();next_owner_check=published+2
                while not self.isInterruptionRequested():
                    if busy and time.monotonic()>=next_owner_check:
                        next_owner_check=time.monotonic()+2
                        with gpiod.Chip(path) as chip:
                            freed=any(not chip.get_line_info(pin).used for pin in busy)
                        if freed:
                            self.status.emit(False,'Previously busy GPIO released; reconnecting inputs')
                            return
                    if request.wait_edge_events(timeout=timedelta(milliseconds=4)):
                        for event in request.read_edge_events(max_events=512):
                            if event.timestamp_ns<discard_before:last_seq=event.global_seqno;continue
                            if last_seq is not None and event.global_seqno!=last_seq+1:
                                fresh=levels();discard_before=time.monotonic_ns()
                                for i,d in decoders.items():d.resync(fresh[i],discard_before)
                                panel_decoder=PanelDecoder(panel,fresh['panel'],discard_before)
                                last_seq=event.global_seqno;continue
                            last_seq=event.global_seqno;i,name=reverse[event.line_offset]
                            (panel_decoder if i=='panel' else decoders[i]).edge(name,int(event.event_type==gpiod.EdgeEvent.Type.RISING_EDGE),event.timestamp_ns)
                    now=time.monotonic_ns()
                    for d in decoders.values():d.settle(now)
                    panel_decoder.settle(now)
                    if time.monotonic()-published>=1/60:
                        self.frames.emit({i:d.snapshot() for i,d in decoders.items()});self.panelFrames.emit(panel_decoder.snapshot());published=time.monotonic()
        except PermissionError as exc:self.status.emit(False,f'GPIO permission denied: {exc}. Run bash run.sh --repair-setup in the Pi desktop.')
        except Exception as exc:self.status.emit(False,f'{type(exc).__name__}: {exc}')
    def stop(self):self.requestInterruption();self.wait()
