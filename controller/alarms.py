"""Trace-only alarm monitoring. No commands are sent to laser hardware."""
from collections import deque
from datetime import datetime


class AlarmMonitor:
    def __init__(self):
        self.active = False
        self.acknowledged = False
        self.pending = 0.
        self.status = 'Disabled'
        self.events = deque(maxlen=50)

    def record(self, message):
        self.events.appendleft(datetime.now().strftime('%H:%M:%S') + '  ' + message)

    def update(self, config, emission, main_peak, error_peak, dt):
        before = self.snapshot()
        if not config['enabled'] or not emission:
            self.status = 'Disabled' if not config['enabled'] else 'Emission off'
            if self.active:self.record('Monitoring suspended')
            self.active = False; self.pending = 0.; self.acknowledged = False
        else:
            # A 2% release margin and 250 ms dwell suppress threshold chatter.
            margin = .98 if self.active else 1.
            main = main_peak > config['main_high'] - (1-margin)*max(.01,abs(config['main_high']))
            error = error_peak > config['error_high']*margin
            exceeded = main or error
            self.pending = self.pending + dt if exceeded else 0.
            if exceeded and (self.active or self.pending >= .25):
                reason = 'Spectroscopy + error' if main and error else 'Spectroscopy' if main else 'Error'
                if not self.active:
                    self.record(reason+' limit exceeded'); self.acknowledged = False
                self.active = True
                self.status = reason + (' · acknowledged' if self.acknowledged else ' · limit exceeded')
            elif not exceeded:
                if self.active:self.record('Returned within limits')
                self.active = False; self.acknowledged = False; self.status = 'Within limits'
            else:self.status = 'Evaluating limits'
        return before != self.snapshot()

    def acknowledge(self):
        if self.active and not self.acknowledged:
            self.acknowledged = True; self.record('Alarm acknowledged')

    def snapshot(self):
        return dict(active=self.active, acknowledged=self.acknowledged,
                    status=self.status, events=list(self.events))
