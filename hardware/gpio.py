"""Qt bridge for the isolated GPIO owner. UI never calls libgpiod.

The bridge drains IPC even while the GUI event loop is busy. Only the main
thread drains the explicit mailbox and interprets application gestures.
"""
from collections import deque
from copy import deepcopy
import multiprocessing as mp
from multiprocessing.connection import wait
from threading import Lock
import time

from PySide6.QtCore import QThread, Signal, QTimer
from .capture import capture_process
from .discovery import gpio_module, discover, select_chip, short_error
from .mailbox import Mailbox
from .metrics import Metrics
from .events import ordered_frames


class GPIOWorker(QThread):
    frames=Signal(object)
    panelFrames=Signal(object)
    status=Signal(bool,str)
    availability=Signal(object)
    acknowledgement=Signal(object)
    fault=Signal(object)
    reset=Signal()

    def __init__(self,config,*,process_target=capture_process):
        super().__init__()
        self.config=deepcopy(config)
        self._initial_config=deepcopy(config)
        self.process_target=process_target
        self.mailbox=Mailbox()
        self.metrics=Metrics()
        self.worker_metrics={}
        self.commands=deque()
        self.command_lock=Lock()
        self.next_id=0
        self.pending={}
        self.epoch=-1
        self.process=None
        self.stopping=False
        self._closed=False
        self._overloaded=False
        self._context=mp.get_context('spawn')
        self.wake_read,self.wake_write=self._context.Pipe(duplex=False)
        self.drain_timer=QTimer(self)
        self.drain_timer.setInterval(4)
        self.drain_timer.timeout.connect(self.drain)
        self.drain_timer.start()

    def submit(self,command,**values):
        """Non-blocking from the UI. The bridge is the sole IPC writer."""
        with self.command_lock:
            if self.stopping and command!='stop':
                raise RuntimeError('GPIO owner is stopping')
            self.next_id+=1
            message=dict(id=self.next_id,command=command,sent_ns=time.monotonic_ns(),**deepcopy(values))
            wake=not self.commands
            self.commands.append(message)
            self.pending[message['id']]=message
            if wake:self.wake_write.send_bytes(b'c')
            return message['id']

    def reconfigure(self,config):
        self.config=deepcopy(config)
        return self.submit('configure',config=config)

    def enqueue(self,message):
        if message['kind']=='ack':
            with self.command_lock:
                pending=self.pending.get(message['id'])
                if pending is not None:pending['acknowledged']=True
        if message['kind']=='batch':
            for group,frame in ordered_frames(message['groups']):
                self.mailbox.put(dict(kind='input',group=group,frame=frame,epoch=message['epoch']))
        else:self.mailbox.put(message)

    def run(self):
        parent,child=self._context.Pipe(duplex=True)
        process=self._context.Process(target=self.process_target,args=(child,self._initial_config),name='NexatomGPIO')
        self.process=process
        try:
            process.start();child.close()
            stop_deadline=None
            outstanding=None
            while True:
                # One in-flight driver command avoids both ends filling their
                # pipe while trying to send. Event reads continue until its ACK.
                if outstanding is None:
                    with self.command_lock:
                        message=self.commands.popleft() if self.commands else None
                        if message is not None:message['dispatched_ns']=time.monotonic_ns()
                    if message is not None:
                        self.metrics.observe('command_queue_wait',message['dispatched_ns']-message['sent_ns'])
                        parent.send(message);outstanding=message['id']
                if self.stopping and stop_deadline is None:stop_deadline=time.monotonic()+3.
                ready=wait([parent,self.wake_read,process.sentinel],timeout=.25 if self.stopping else None)
                if stop_deadline is not None and time.monotonic()>stop_deadline and process.is_alive():
                    process.terminate()
                    stop_deadline=time.monotonic()+3.
                    self.mailbox.put(dict(kind='fault',group='process',message='GPIO shutdown deadline exceeded; owner terminated.',recoverable=False))
                if self.wake_read in ready:
                    self.wake_read.recv_bytes()
                if parent in ready:
                    # Bounded turn, then re-check commands/process sentinel.
                    for _ in range(256):
                        if not parent.poll():break
                        message=parent.recv()
                        self.enqueue(message)
                        if message['kind']=='ack' and message['id']==outstanding:outstanding=None
                if process.sentinel in ready:
                    while parent.poll():
                        try:self.enqueue(parent.recv())
                        except EOFError:break
                    break
        except (EOFError,BrokenPipeError,OSError) as exc:
            if not self.stopping:self.mailbox.put(dict(kind='fault',group='process',message=short_error(exc),recoverable=True))
        except Exception as exc:
            self.mailbox.put(dict(kind='fault',group='process',message=short_error(exc),recoverable=False))
        finally:
            parent.close();child.close()
            if process.pid:
                process.join(5.)
                if process.is_alive():
                    # Shutdown-only last resort, never a duplicate owner/retry.
                    process.terminate();process.join(2.)
                    self.mailbox.put(dict(kind='fault',group='process',message='GPIO owner required termination during shutdown.',recoverable=False))
                if process.is_alive():
                    process.kill();process.join()
                exitcode=process.exitcode
                process.close()
            else:exitcode=None
            self.process=None
            if not self.stopping:
                self.mailbox.put(dict(kind='status',online=False,text=f'GPIO owner exited ({exitcode}); Retry GPIO.',issues={}))
            with self.command_lock:
                for command in self.pending.values():
                    self.mailbox.put(dict(kind='ack',id=command['id'],command=command['command'],ok=False,
                        error='Owner stopped before acknowledgement',sent_ns=command['sent_ns'],started_ns=0,completed_ns=time.monotonic_ns()))

    def drain(self):
        """A time budget yields to Qt, without discarding the remaining events."""
        start=time.monotonic_ns()
        # A fixed small slice can starve behind a slow software-rendered frame.
        # Give a growing backlog a larger, still bounded scheduling slice.
        depth=self.mailbox.snapshot()['pending']
        budget=64_000_000 if depth>100 else 32_000_000 if depth>24 else 8_000_000
        while time.monotonic_ns()-start<budget:
            message=self.mailbox.take()
            if message is None:break
            kind=message['kind']
            if kind=='input':
                stamp=time.monotonic_ns()
                frame=message['frame'];group=message['group']
                if message.get('initial'):frame['initial']=True
                for (name,value),event_ns in zip(frame['events'],frame.get('event_times',[])):
                    self.metrics.observe('knob_to_application' if name=='rotation' else 'button_to_application',stamp-event_ns)
                    self.metrics.count('delivered_transitions')
                self.metrics.observe('snapshot_to_application',stamp-frame.get('captured_ns',stamp))
                if group.startswith('knob:'):self.frames.emit({int(group[5:]):frame})
                else:
                    if message.get('resync'):frame['resync']=True
                    self.panelFrames.emit(frame)
                finished=time.monotonic_ns()
                self.metrics.observe('application_handler',finished-stamp)
                for (name,value),event_ns in zip(frame['events'],frame.get('event_times',[])):
                    self.metrics.observe('knob_to_handler_complete' if name=='rotation' else 'button_to_handler_complete',finished-event_ns)
            elif kind=='status':
                self.availability.emit(message.get('issues',{}))
                self.status.emit(message['online'],message['text'])
            elif kind=='reset':
                self.epoch=message['epoch'];self.reset.emit()
            elif kind=='fault':self.fault.emit(message)
            elif kind=='metrics':self.worker_metrics=message['data']
            elif kind=='ack':
                with self.command_lock:
                    command=self.pending.pop(message['id'],None)
                if command is None:continue
                now=time.monotonic_ns()
                self.metrics.observe('command_roundtrip',now-message['sent_ns'])
                if message['started_ns']:
                    self.metrics.observe('command_to_worker',message['started_ns']-message['sent_ns'])
                    self.metrics.observe('driver_operation',message['completed_ns']-message['started_ns'])
                self.acknowledgement.emit(message)
        state=self.mailbox.snapshot()
        interval=1 if state['pending'] else 4
        if self.drain_timer.interval()!=interval:self.drain_timer.setInterval(interval)
        if state['pending']>2000 and not self._overloaded:
            self._overloaded=True
            self.fault.emit(dict(group='queue',message='Input backlog exceeds 2000 batches; events retained. Reduce graph load.',recoverable=True))
        elif state['pending']<100:self._overloaded=False
        now=time.monotonic_ns()
        with self.command_lock:
            overdue=[c for c in self.pending.values() if c.get('dispatched_ns') and now-c['dispatched_ns']>5_000_000_000 and not c.get('reported') and not c.get('acknowledged')]
            for c in overdue:c['reported']=True
        if overdue:
            names=', '.join(dict.fromkeys(c['command'] for c in overdue))
            self.fault.emit(dict(group='command',message=f"GPIO acknowledgement overdue ({len(overdue)}: {names}); commands not replayed.",recoverable=False))

    def snapshot(self):
        return dict(queue=self.mailbox.snapshot(),delivery=self.metrics.snapshot(),capture=self.worker_metrics)

    def stop(self):
        if self._closed:return
        self.stopping=True;self.drain_timer.stop()
        if self.isRunning():
            self.submit('stop')
            if not self.wait(5000):
                if not self.wait(3000):raise RuntimeError('GPIO bridge did not stop; replacement owner refused')
        self.drain()
        self.wake_read.close();self.wake_write.close();self._closed=True
