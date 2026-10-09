"""Single-owner GPIO reactor, executed in a separate process (no Qt imports).

Kernel edge buffers -> electrical decoders -> IPC -> GUI mailbox. Commands
arrive on the same selectable IPC connection, waking an idle reactor. Every
request and its selector registration are created/released on this owner.
"""
from copy import deepcopy
from dataclasses import dataclass
import errno
import logging
import selectors
import time

from .config import validate
from .decoder import Decoder
from .panel import PanelDecoder
from .discovery import gpio_module, select_chip, short_error
from .metrics import Metrics

LOG = logging.getLogger('nexatom.gpio')
RECOVERABLE = {errno.EBUSY, errno.ENODEV, errno.ENOENT, errno.EIO, errno.ENXIO}


@dataclass
class Group:
    key: str
    pins: dict
    config: dict
    request: object = None
    decoder: object = None
    polled: tuple = ()
    last_seq: int = 0
    discard_before: int = 0
    attempt: int = 0
    retry_at: float = float('inf')
    issue: str = ''


class Reactor:
    def __init__(self, connection, config, *, module=None, line=None, selector=None):
        self.connection = connection
        self.config = deepcopy(validate(config))
        self.module = module
        self.line = line
        self.selector = selector or selectors.DefaultSelector()
        self.groups = {}
        self.metrics = Metrics()
        self.path = None
        self.running = True
        self.epoch = 0
        self.heartbeat = 0.
        self.next_poll = 0.
        self.last_state = None
        self.dirty = set()
        self.global_retry = float('inf')
        self.global_attempt = 0

    def send(self, kind, **values):
        self.connection.send(dict(kind=kind, epoch=self.epoch, **values))

    def close_group(self, group):
        if group.request is not None:
            request, group.request = group.request, None
            try:
                self.selector.unregister(request.fd)
            except (KeyError, ValueError):
                pass
            finally:
                request.release()
        group.decoder = None
        self.dirty.discard(group.key)

    def close(self):
        failures=[]
        for group in self.groups.values():
            try:self.close_group(group)
            except Exception as exc:failures.append(exc)
        self.groups.clear()
        if failures:raise RuntimeError('GPIO release failed; owner must restart') from failures[0]

    def fail_group(self, group, exc):
        self.flush()
        self.close_group(group)
        group.issue = short_error(exc)
        group.attempt += 1
        group.retry_at = (time.monotonic() + min(8., .25*2**min(5,group.attempt-1))
                          if getattr(exc,'errno',None) in RECOVERABLE or 'No GPIO device' in str(exc) else float('inf'))
        self.metrics.count('request_failures')
        self.send('fault', group=group.key, message=group.issue, recoverable=group.retry_at!=float('inf'))
        LOG.warning('%s: %s', group.key, group.issue)

    def retry_failed(self, now, force=False):
        due=[g for g in self.groups.values() if g.request is None and (force or now>=g.retry_at)]
        if not due:return
        # A removed/re-enumerated chip can return under a different device name.
        # Discovery is read-only and only runs once all old requests are closed.
        if self.config['chip']=='auto' and not any(g.request for g in self.groups.values()):
            try:self.path=select_chip(self.module,'auto')
            except (OSError,RuntimeError) as exc:
                for group in due:self.fail_group(group,exc)
                return
        for group in due:self.open_group(group)

    def values(self, group):
        return {name:int(value == self.line.Value.ACTIVE)
                for name,value in zip(group.pins,group.request.get_values(list(group.pins.values())))}

    def open_group(self, group):
        gpiod, line = self.module, self.line
        # Never preflight line.used then assume ownership: request_lines is the
        # atomic arbiter. EBUSY is isolated to this control, not every input.
        try:
            settings = {tuple(group.pins.values()): gpiod.LineSettings(
                direction=line.Direction.INPUT, edge_detection=line.Edge.BOTH,
                bias=line.Bias.PULL_UP, active_low=False)}
            polled = ()
            try:
                request = gpiod.request_lines(self.path, consumer='nexatom-controls',
                    config=settings, event_buffer_size=4096)
            except OSError as exc:
                if exc.errno != errno.ENXIO:
                    raise
                # Readable contacts without interrupts are an explicitly
                # degraded mode. Encoders never silently fall back to polling.
                settings = {}
                encoder = tuple(pin for name,pin in group.pins.items() if name.startswith('encoder_'))
                polled = tuple(name for name in group.pins if not name.startswith('encoder_'))
                for pins,edge in ((encoder,line.Edge.BOTH),
                                  (tuple(group.pins[n] for n in polled),line.Edge.NONE)):
                    if pins:
                        settings[pins] = gpiod.LineSettings(direction=line.Direction.INPUT,
                            edge_detection=edge,bias=line.Bias.PULL_UP,active_low=False)
                request = gpiod.request_lines(self.path,consumer='nexatom-controls',
                    config=settings,event_buffer_size=4096)
            # Assign ownership BEFORE any operation which can throw.
            group.request = request
            group.polled = polled
            group.last_seq = 0
            levels = self.values(group)
            now = time.monotonic_ns()
            group.discard_before = now
            if group.key.startswith('knob:'):
                group.decoder = Decoder(group.config,levels,now)
            else:
                group.decoder = PanelDecoder({group.key[6:]:group.config},levels,now)
            if len(polled) < len(group.pins):
                self.selector.register(request.fd,selectors.EVENT_READ,group)
            group.attempt = 0
            group.retry_at = float('inf')
            group.issue = 'Contact polling fallback (4 ms); interrupts unavailable' if polled else ''
            self.metrics.count('requests_opened')
            self.publish(group, initial=True)
        except (OSError,RuntimeError) as exc:
            self.fail_group(group,exc)

    def configure(self, config):
        config = deepcopy(validate(config))  # Invalid configuration leaves ownership intact.
        self.flush()
        self.close()
        self.epoch += 1
        self.config = config
        self.global_retry = float('inf')
        try:
            if self.module is None:
                self.module = gpio_module()
                from gpiod import line
                self.line = line
            self.path = select_chip(self.module,config['chip'])
            for i,cfg in enumerate(config['knobs']):
                if cfg['enabled'] and cfg['pins']:
                    key=f'knob:{i}';self.groups[key]=Group(key,dict(cfg['pins']),cfg)
            for key,cfg in config.get('panel',{}).items():
                if cfg['enabled']:
                    self.groups['panel:'+key]=Group('panel:'+key,{key:cfg['pin']},cfg)
            # Status precedes snapshots, allowing UI to handle an initial lock.
            self.send('reset')
            for group in self.groups.values():
                self.open_group(group)
            self.global_attempt = 0
            self.report_state()
        except (OSError,RuntimeError,ImportError) as exc:
            self.close()
            self.global_attempt += 1
            if getattr(exc,'errno',None) in RECOVERABLE or 'No GPIO device' in str(exc):
                self.global_retry=time.monotonic()+min(8.,.25*2**min(5,self.global_attempt-1))
            self.send('status', online=False, text=short_error(exc), issues={})
            self.send('fault',group='device',message=short_error(exc),recoverable=self.global_retry!=float('inf'))

    def report_state(self):
        issues={key:g.issue for key,g in self.groups.items() if g.issue}
        knobs=sum(g.request is not None for key,g in self.groups.items() if key.startswith('knob:'))
        panel=sum(g.request is not None for key,g in self.groups.items() if key.startswith('panel:'))
        text=f'{knobs} knobs / {panel} buttons & lock ready'
        if issues:text+=f' · {len(issues)} degraded/unavailable; see Control settings'
        if not self.groups:text='All wired inputs are disabled.'
        state=(knobs,panel,tuple(issues.items()))
        if state!=self.last_state:
            self.last_state=state
            self.send('status',online=bool(knobs+panel),text=text,issues=issues)

    def publish(self, group, initial=False, resync=False):
        if initial or resync:
            self.send('input',group=group.key,frame=group.decoder.snapshot(),initial=initial,resync=resync)
        elif group.decoder.events:self.dirty.add(group.key)

    def flush(self):
        frames={key:self.groups[key].decoder.snapshot() for key in self.dirty if self.groups[key].decoder}
        self.dirty.clear()
        if frames:self.send('batch',groups=frames)

    def read_edges(self, ready):
        events=[]
        failed=set()
        for group in ready:
            if group.request is None:continue
            try:
                # Drain all buffered batches. Never settle at wall-clock time
                # while historical edges for the same request remain unread.
                budget=0
                while group.request.wait_edge_events(timeout=0):
                    batch=group.request.read_edge_events(max_events=1024)
                    if not batch:break
                    for edge in batch:
                        if edge.global_seqno!=((group.last_seq+1)&0xffffffff):
                            self.metrics.count('kernel_missing_edges',max(1,(edge.global_seqno-group.last_seq-1)&0xffffffff))
                            failed.add(group.key)
                        group.last_seq=edge.global_seqno
                        if edge.timestamp_ns >= group.discard_before:
                            events.append((edge.timestamp_ns,group,edge))
                    budget+=len(batch)
                    if budget>=16384:
                        # Control commands get a scheduling point during a
                        # sustained flood. The next select is immediately ready.
                        break
            except OSError as exc:
                self.fail_group(group,exc)
        for key in failed:
            group=self.groups[key]
            if group.request is None:continue
            try:
                fresh=self.values(group);now=time.monotonic_ns()
                group.discard_before=now
                if key.startswith('knob:'):group.decoder.resync(fresh,now)
                else:group.decoder=PanelDecoder({key[6:]:group.config},fresh,now)
                self.send('fault',group=key,message='Kernel edge overflow: release this control to re-arm.',recoverable=True)
                self.publish(group,resync=True)
            except OSError as exc:self.fail_group(group,exc)
        for stamp,group,edge in sorted(events,key=lambda item:item[0]):
            if group.request is None or group.key in failed:continue
            name=next(name for name,pin in group.pins.items() if pin==edge.line_offset)
            value=int(edge.event_type==self.module.EdgeEvent.Type.RISING_EDGE)
            group.decoder.edge(name,value,stamp)
            self.metrics.observe('kernel_edge_to_worker',time.monotonic_ns()-stamp)
            self.metrics.count('raw_edges')
        for group in ready:
            if group.decoder:self.publish(group)

    def command(self, message):
        started=time.monotonic_ns()
        name=message['command']
        self.metrics.observe('command_to_worker',started-message['sent_ns'])
        ok=True;error=''
        try:
            if name=='stop':self.running=False
            elif name=='configure':self.configure(message['config'])
            elif name=='retry':
                # A retry of a partly working system opens ONLY failed groups.
                if not self.groups:self.configure(self.config)
                else:
                    self.retry_failed(time.monotonic(),force=True)
                    self.report_state()
            elif name=='probe':
                for group in self.groups.values():
                    if group.request is not None:
                        try:self.values(group)
                        except OSError as exc:self.fail_group(group,exc);raise
                if not any(g.request is not None for g in self.groups.values()):
                    raise RuntimeError('No active GPIO request')
            else:raise ValueError('Unsupported hardware command: '+str(name))
        except (ValueError,RuntimeError,OSError) as exc:
            ok=False;error=short_error(exc)
        ended=time.monotonic_ns()
        if name in ('configure','retry') and not any(g.request for g in self.groups.values()):
            ok=False;error=error or 'No active GPIO request; see status'
        self.send('ack',id=message['id'],command=name,ok=ok,error=error,
                  sent_ns=message['sent_ns'],started_ns=started,completed_ns=ended)

    def run(self):
        try:
            self.selector.register(self.connection.fileno(),selectors.EVENT_READ,'command')
            self.configure(self.config)
            while self.running:
                now=time.monotonic()
                deadlines=[now+.25,self.heartbeat,self.global_retry]
                for group in self.groups.values():
                    deadlines.append(group.retry_at)
                    if group.decoder:
                        d=group.decoder
                        for name in d.stable:
                            raw=d.raw[name] != d.released[name] if isinstance(d,Decoder) else d.raw[name]==d.config[name]['active_level']
                            if raw!=d.stable[name]:
                                changed=d.changed_at[name] if isinstance(d,Decoder) else d.changed[name]
                                delay=d.debounce if isinstance(d,Decoder) else d.config[name]['debounce_ms']*1_000_000
                                deadlines.append((changed+delay)/1e9)
                        if group.polled:deadlines.append(self.next_poll)
                ready=self.selector.select(max(0,min(deadlines)-now))
                if any(key.data=='command' for key,mask in ready):
                    # FIFO command serialization. Stop interrupts waiting and
                    # never creates a second owner to replace a live request.
                    while self.connection.poll():
                        self.command(self.connection.recv())
                        if not self.running:break
                if not self.running:break
                edge_groups=[key.data for key,mask in ready if key.data!='command' and key.data.request is not None]
                self.read_edges(edge_groups)
                now=time.monotonic();stamp=time.monotonic_ns()
                if now>=self.global_retry:self.configure(self.config)
                self.retry_failed(now)
                heartbeats=[]
                for group in self.groups.values():
                    if group.request is None:continue
                    try:
                        # If a flood exhausted the fairness budget, drain before
                        # advancing debounce deadlines to the current clock.
                        pending=(len(group.polled)<len(group.pins) and group.request.wait_edge_events(timeout=0))
                        if pending:continue
                        if group.polled and now>=self.next_poll:
                            for name,value in self.values(group).items():
                                if name in group.polled:group.decoder.edge(name,value,stamp)
                        group.decoder.settle(stamp)
                        self.publish(group)
                        if now>=self.heartbeat:
                            self.values(group)  # Health read, not replacement encoder states.
                            heartbeats.append(group)
                    except OSError as exc:self.fail_group(group,exc)
                self.flush()
                for group in heartbeats:
                    if group.decoder:self.send('input',group=group.key,frame=group.decoder.snapshot(),initial=False,resync=False)
                if now>=self.next_poll:self.next_poll=now+.004
                if now>=self.heartbeat:
                    self.heartbeat=now+.10
                    self.send('metrics',data=self.metrics.snapshot())
                self.report_state()
        except (EOFError,BrokenPipeError,ConnectionResetError):
            pass  # Parent died; finally releases all requests.
        finally:
            try:self.close()
            finally:
                try:self.selector.close()
                finally:self.connection.close()


def capture_process(connection, config):
    Reactor(connection,config).run()
