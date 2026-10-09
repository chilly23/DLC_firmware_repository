"""Dedicated panel contacts share the GPIO request with the knobs."""
from copy import deepcopy

PANEL_DEFAULTS=dict(
    lock=dict(pin=20,enabled=True,active_level=0,debounce_ms=30,calibrated=True),
    right_emission=dict(pin=12,enabled=True,active_level=0,debounce_ms=25,calibrated=True),
    left_emission=dict(pin=1,enabled=True,active_level=0,debounce_ms=25,calibrated=True),
    right_shortcut=dict(pin=7,enabled=True,active_level=0,debounce_ms=25,calibrated=True),
    left_shortcut=dict(pin=8,enabled=False,active_level=0,debounce_ms=25,calibrated=False))
PANEL_LABELS=dict(lock='System lock switch',right_emission='Button 1 - right emission',left_emission='Button 2 - left emission',
                  right_shortcut='Button 3 - right shortcut',left_shortcut='Button 4 - left shortcut')

class PanelDecoder:
    def __init__(self,config,levels,now):
        self.config=deepcopy(config);self.raw=dict(levels);self.changed=dict.fromkeys(levels,now)
        self.stable={k:bool(v==config[k]['active_level']) for k,v in levels.items()};self.events=[]
    def edge(self,key,value,now):
        self.settle(now)
        if value!=self.raw[key]:self.raw[key]=value;self.changed[key]=now
    def settle(self,now):
        for key,value in self.raw.items():
            active=value==self.config[key]['active_level']
            if active!=self.stable[key] and now-self.changed[key]>=self.config[key]['debounce_ms']*1_000_000:
                self.stable[key]=active;self.events.append((key,active))
    def snapshot(self):
        result=dict(levels=dict(self.raw),active=dict(self.stable),events=self.events[:]);self.events.clear();return result

