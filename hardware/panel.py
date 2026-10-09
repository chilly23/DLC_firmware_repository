"""Debounce dedicated panel contacts; each contact has its own owner request."""
from copy import deepcopy

PANEL_DEFAULTS=dict(
    lock=dict(pin=20,enabled=True,active_level=0,debounce_ms=30,calibrated=True),
    right_emission=dict(pin=12,enabled=True,active_level=0,debounce_ms=25,calibrated=True),
    left_emission=dict(pin=1,enabled=True,active_level=0,debounce_ms=25,calibrated=True),
    right_shortcut=dict(pin=7,enabled=True,active_level=0,debounce_ms=25,calibrated=True),
    left_shortcut=dict(pin=16,enabled=True,active_level=0,debounce_ms=25,calibrated=True))
PANEL_LABELS=dict(lock='System lock switch',right_emission='Button 1 - right emission',left_emission='Button 2 - left emission',
                  right_shortcut='Button 3 - right shortcut',left_shortcut='Button 4 - left shortcut')

class PanelDecoder:
    def __init__(self,config,levels,now):
        self.config=deepcopy(config);self.raw=dict(levels);self.changed=dict.fromkeys(levels,now)
        self.stable={k:bool(v==config[k]['active_level']) for k,v in levels.items()};self.events=[];self.event_times=[];self.now=now
    def edge(self,key,value,now):
        self.settle(now)
        if value!=self.raw[key]:self.raw[key]=value;self.changed[key]=now
    def settle(self,now):
        self.now=now
        for key,value in self.raw.items():
            active=value==self.config[key]['active_level']
            if active!=self.stable[key] and now-self.changed[key]>=self.config[key]['debounce_ms']*1_000_000:
                self.stable[key]=active;self.events.append((key,active));self.event_times.append(self.changed[key]+self.config[key]['debounce_ms']*1_000_000)
    def snapshot(self):
        ordered=sorted(zip(self.events,self.event_times),key=lambda pair:pair[1])
        self.events=[p[0] for p in ordered];self.event_times=[p[1] for p in ordered]
        result=dict(levels=dict(self.raw),active=dict(self.stable),events=self.events[:],event_times=self.event_times[:],captured_ns=self.now,released={k:1-v['active_level'] for k,v in self.config.items()});self.events.clear();self.event_times.clear();return result
