"""Pure electrical decoder, adapted from the working RKJXT demo.

Inputs are raw electrical levels after pull-up requests. Idle gpioget output
before a request is not a direction or polarity configuration.
"""
from .config import CONTACTS

class Quadrature:
    DELTA={(3,1):1,(1,0):1,(0,2):1,(2,3):1,(1,3):-1,(0,1):-1,(2,0):-1,(3,2):-1}
    def __init__(self,a,b,transitions=2):
        self.previous=a*2+b;self.partial=0;self.transitions=transitions;self.invalid=0
    def reset(self,a,b):self.previous=a*2+b;self.partial=0
    def feed(self,a,b):
        state=a*2+b
        if state==self.previous:return 0
        delta=self.DELTA.get((self.previous,state));self.previous=state
        if delta is None:self.partial=0;self.invalid+=1;return 0
        self.partial+=delta
        if (self.transitions==1 or state in (0,3)) and abs(self.partial)>=self.transitions:
            step=1 if self.partial>0 else -1;self.partial-=step*self.transitions;return step
        return 0

class Decoder:
    def __init__(self,cfg,levels,now):
        self.raw=dict(levels);self.released=cfg['released'];self.stable={k:levels[k]!=self.released[k] for k in CONTACTS}
        self.changed_at=dict.fromkeys(CONTACTS,now);self.debounce=int(cfg['switch_debounce_ms']*1_000_000)
        self.encoder=Quadrature(levels['encoder_a'],levels['encoder_b'],cfg['transitions_per_detent'])
        self.events=[];self.event_times=[];self.count=0;self.lost=0;self.now=now
    def settle(self,now):
        self.now=now
        for name in CONTACTS:
            active=self.raw[name]!=self.released[name]
            if active!=self.stable[name] and now-self.changed_at[name]>=self.debounce:
                self.stable[name]=active;self.events.append((name,int(active)));self.event_times.append(self.changed_at[name]+self.debounce)
    def edge(self,name,level,now):
        self.settle(now)
        if level==self.raw[name]:return
        self.raw[name]=level
        if name.startswith('encoder_'):
            delta=self.encoder.feed(self.raw['encoder_a'],self.raw['encoder_b'])
            if delta:self.count+=delta;self.events.append(('rotation',delta));self.event_times.append(now)
        else:self.changed_at[name]=now
    def resync(self,levels,now):
        self.raw=dict(levels);self.encoder.reset(levels['encoder_a'],levels['encoder_b'])
        self.stable={k:levels[k]!=self.released[k] for k in CONTACTS}
        self.changed_at=dict.fromkeys(CONTACTS,now);self.events=[];self.event_times=[];self.lost+=1;self.now=now
    def snapshot(self):
        ordered=sorted(zip(self.events,self.event_times),key=lambda pair:pair[1])
        self.events=[p[0] for p in ordered];self.event_times=[p[1] for p in ordered]
        result=dict(levels=dict(self.raw),switches=dict(self.stable),count=self.count,
                    invalid=self.encoder.invalid,lost=self.lost,events=self.events[:],event_times=self.event_times[:],captured_ns=self.now,released=dict(self.released))
        self.events.clear();self.event_times.clear();return result
