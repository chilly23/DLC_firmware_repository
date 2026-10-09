"""Explicit benchmark-only electrical source. Never imported by the real driver.

Uses the production decoders, timestamps, IPC, mailbox and application router.
No GPIO device is opened and generated samples are labelled synthetic.
"""
from copy import deepcopy
import time
from .decoder import Decoder
from .panel import PanelDecoder
from .metrics import Metrics


def replay_process(connection,config):
    metrics=Metrics();epoch=0;active=False;rate=400.;steps=0;phase=0;last={}
    decoders={};panel=None;next_edge=time.monotonic();heartbeat=0.;next_button=0.;pressed=False
    def send(kind,**kw):connection.send(dict(kind=kind,epoch=epoch,**kw))
    def configure(config):
        nonlocal decoders,panel,epoch,phase,pressed,last
        epoch+=1;phase=0;pressed=False;last={}
        now=time.monotonic_ns()
        decoders={i:Decoder(k,dict.fromkeys(k['pins'],1),now)
                  for i,k in enumerate(config['knobs']) if k['enabled'] and k['pins']}
        contacts={k:v for k,v in config['panel'].items() if v['enabled']}
        levels={k:1-v['active_level'] for k,v in contacts.items()}
        panel=PanelDecoder(contacts,levels,now)
        send('reset');send('status',online=True,text='Synthetic benchmark inputs · no GPIO hardware',issues={})
        for i,d in decoders.items():send('input',group=f'knob:{i}',frame=d.snapshot(),initial=True)
        for key in contacts:
            f=panel.snapshot();f['active']={key:f['active'][key]};f['levels']={key:f['levels'][key]}
            send('input',group='panel:'+key,frame=f,initial=True)
    def flush(now,force=False):
        groups={}
        for i,d in decoders.items():
            d.settle(now)
            if d.events:
                metrics.count('accepted_rotation_steps',sum(abs(v) for n,v in d.events if n=='rotation'))
                groups[f'knob:{i}']=d.snapshot()
            elif force:send('input',group=f'knob:{i}',frame=d.snapshot(),initial=False)
        panel.settle(now)
        if panel.events:
            frame=panel.snapshot()
            metrics.count('accepted_button_presses',sum(1 for n,v in frame['events'] if v))
            for key in panel.config:
                positions=[i for i,e in enumerate(frame['events']) if e[0]==key]
                if positions:
                    groups['panel:'+key]=dict(frame,levels={key:frame['levels'][key]},active={key:frame['active'][key]},
                        events=[frame['events'][i] for i in positions],event_times=[frame['event_times'][i] for i in positions])
        if groups:send('batch',groups=groups)
    configure(config)
    try:
        running=True
        while running:
            now=time.monotonic()
            due=min(heartbeat,next_edge if active else now+.1)
            if connection.poll(max(0,due-now)):
                msg=connection.recv();name=msg['command'];started=time.monotonic_ns();ok=True;error=''
                metrics.observe('command_to_worker',started-msg['sent_ns'])
                if name=='stop':running=False
                elif name=='configure':config=deepcopy(msg['config']);configure(config)
                elif name in ('probe','retry'):pass
                elif name=='start_input':
                    active=True;rate=max(10,min(10000,float(msg.get('rate',400))))
                    next_edge=next_button=time.monotonic()
                elif name=='stop_input':active=False
                elif name=='fault_test':
                    active=False
                    send('fault',group='synthetic',message='Injected disconnect; reconnect via Retry GPIO.',recoverable=True)
                    send('status',online=False,text='Injected synthetic disconnect',issues={})
                else:ok=False;error='Unsupported synthetic command'
                if name=='retry':configure(config)
                send('ack',id=msg['id'],command=name,ok=ok,error=error,sent_ns=msg['sent_ns'],started_ns=started,completed_ns=time.monotonic_ns())
            now=time.monotonic()
            if active:
                # Replay every due transition; no resampling to a final level.
                budget=0
                while next_edge<=now and budget<10000:
                    stamp=int(next_edge*1e9)
                    signal,level=(('encoder_a',0),('encoder_b',0),('encoder_a',1),('encoder_b',1))[phase]
                    for i,d in decoders.items():
                        d.edge(signal,level,stamp);metrics.count('generated_encoder_edges')
                    phase=(phase+1)%4;next_edge+=1/rate;budget+=1
                # One 40ms valid press / 40ms release, independently of encoder.
                while next_button<=now:
                    pressed=not pressed
                    for key in ('left_shortcut','right_shortcut'):
                        if key in panel.config:
                            level=panel.config[key]['active_level'] if pressed else 1-panel.config[key]['active_level']
                            panel.edge(key,level,int(next_button*1e9));metrics.count('generated_button_edges')
                    next_button+=.04
            flush(time.monotonic_ns())
            if now>=heartbeat:
                flush(time.monotonic_ns(),True)
                heartbeat=now+.1
                send('metrics',data=metrics.snapshot())
    except (EOFError,BrokenPipeError,ConnectionResetError):pass
    finally:connection.close()
