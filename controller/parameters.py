"""Presentation catalogue over the existing simulated controller state.

No GPIO, transport, or driver calls belong here. Readbacks are explicitly
simulated; configuration edits share the Home numeric editor and validation.
"""
from copy import deepcopy
from math import isfinite
from PySide6.QtCore import QObject, Property, Signal, Slot, QTimer
from .model import PARAMETERS, MODULES


class ParameterCatalog(QObject):
    changed = Signal()

    def __init__(self, controller, store, parent=None):
        super().__init__(parent)
        self.ctl, self.store = controller, store
        self.flags = [dict(tc_enabled=True, feedforward_enabled=True, positive=True) for _ in range(2)]
        loaded = store.values.get('control_state', [])
        if isinstance(loaded, list):
            for index, saved in enumerate(loaded[:2]):
                if not isinstance(saved, dict):
                    continue
                laser = controller.instrument.lasers[index]
                values = saved.get('values', {})
                if isinstance(values, dict):
                    candidate = laser.values.copy()
                    for key, value in values.items():
                        if key not in PARAMETERS:
                            continue
                        spec = PARAMETERS[key]
                        try:
                            number = float(value)
                        except (TypeError, ValueError):
                            continue
                        if isfinite(number) and spec.minimum <= number <= spec.maximum:
                            candidate[key] = round(number, spec.decimals)
                    # A saved lower limit and lower setpoint must restore together.
                    if candidate['current'] <= candidate['maximum_current'] and candidate['minimum_temperature'] <= candidate['temperature'] <= candidate['maximum_temperature']:
                        laser.values.update(candidate)
                for key in ('top', 'bottom'):
                    if saved.get(key) in PARAMETERS:
                        setattr(laser, key, saved[key])
                for key in self.flags[index]:
                    if isinstance(saved.get(key), bool):
                        self.flags[index][key] = saved[key]
        self.save_timer = QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.setInterval(250)
        self.save_timer.timeout.connect(self.save)
        self.last_saved = self.snapshot()
        controller.changed.connect(self.state_changed)
        self.read_timer = QTimer(self)
        self.read_timer.setInterval(250)
        self.read_timer.timeout.connect(self.changed)

    def snapshot(self):
        return [dict(values=deepcopy(laser.values), top=laser.top_field(),
                     bottom=laser.bottom_field(), **self.flags[i])
                for i, laser in enumerate(self.ctl.instrument.lasers)]

    def state_changed(self):
        if self.snapshot() != self.last_saved:
            self.save_timer.start()
        if self.read_timer.isActive():self.changed.emit()

    def save(self):
        self.last_saved = self.snapshot()
        self.store.values['control_state'] = self.last_saved
        if not self.store.save():
            self.ctl.notifications.post('Control values could not be saved.', 'warning', 'control-save')

    @Slot(bool)
    def observe(self, active):
        self.read_timer.start() if active else self.read_timer.stop()
        if active:self.changed.emit()

    @Property('QVariantList', constant=True)
    def fields(self):
        return [dict(key=key, name=f'{spec.module} · {spec.label}', label=spec.label,
                     module=spec.module, unit=spec.unit) for key, spec in PARAMETERS.items()]

    def value_row(self, index, key, caption='', readonly=False, label=None):
        spec = PARAMETERS[key]
        return dict(key=key, label=label or spec.label, caption=caption,
                    value=f'{self.ctl.value(index, key):.{spec.decimals}f}', unit=spec.unit,
                    kind='read' if readonly else 'number', on=False, path='')

    @staticmethod
    def read(key, label, value, caption='', unit=''):
        return dict(key=key, label=label, value=str(value), caption=caption,
                    unit=unit, kind='read', on=False, path='')

    def toggle(self, index, key, label, caption):
        value = self.ctl.instrument.lasers[index].emission if key == 'cc_enabled' else self.flags[index][key]
        return dict(key=key, label=label, caption=caption, value='On' if value else 'Off',
                    unit='', kind='toggle', on=value, path='')

    @Slot(int, str)
    def toggleControl(self, index, key):
        if index not in (0, 1):
            return
        if key == 'cc_enabled':
            self.ctl.toggleEmission(index)
        elif key in ('tc_enabled', 'feedforward_enabled'):
            self.flags[index][key] = not self.flags[index][key]
            self.ctl.journal.record(f'Laser {index+1}: {key} '+('enabled' if self.flags[index][key] else 'disabled'), source='Control Parameters')
            self.state_changed()

    @Slot(int, str, result='QVariantList')
    def controlRows(self, index, module):
        if index not in (0, 1):
            return []
        laser = self.ctl.instrument.lasers[index]
        if module == 'CC':
            current = laser.signal.live['current'] * laser.signal.level
            return [self.toggle(index, 'cc_enabled', 'Enable CC', 'Turn current control on or off'),
                    self.value_row(index, 'current', 'Enter the CC set current'),
                    self.read('actual_current', 'Actual Current', f'{current:.3f}', 'Simulated current readback', 'mA'),
                    self.value_row(index, 'maximum_current', 'Upper bound for the set current'),
                    self.value_row(index, 'umax', 'CC maximum voltage · read only here', True, 'Maximum Voltage Umax'),
                    self.read('positive', 'Positive Polarity', 'Positive', 'Configured output polarity'),
                    self.toggle(index, 'feedforward_enabled', 'Enable Feed Forward', 'Enable feed-forward in the application model'),
                    self.value_row(index, 'feedforward', 'Current change per volt')]
        if module == 'TC':
            enabled = self.flags[index]['tc_enabled']
            return [self.toggle(index, 'tc_enabled', 'Enable TC', 'Turn temperature control on or off'),
                    self.value_row(index, 'temperature', 'Enter the TC set temperature', label='Set Temperature'),
                    self.read('actual_temperature', 'Actual Temperature', f'{laser.signal.live["temperature"]:.3f}' if enabled else '—', 'Simulated readback' if enabled else 'Temperature control disabled', '°C'),
                    self.value_row(index, 'minimum_temperature', 'Lower temperature limit', True),
                    self.value_row(index, 'maximum_temperature', 'Upper temperature limit', True),
                    self.value_row(index, 'pid', 'Proportional parameter', label='TC Regulator P Parameter'),
                    self.value_row(index, 'pid_i', 'Integral parameter'),
                    self.value_row(index, 'pid_d', 'Derivative parameter')]
        return [self.value_row(index, key, 'Piezo / scan configuration') for key in MODULES['PC']]

    @Slot(int, result='QVariantList')
    def laserRows(self, index):
        return [self.value_row(index, 'maximum_current', 'Enter CC maximum current'),
                self.value_row(index, 'current', 'Enter CC set current'),
                self.value_row(index, 'umax', 'CC maximum voltage', True, 'Maximum Voltage'),
                self.read('positive', 'Positive polarity', 'Positive', 'Configured output polarity'),
                self.value_row(index, 'temperature', 'Enter TC set temperature', label='Set temperature')]

    @staticmethod
    def branch(label, path, caption='Parameter group'):
        return dict(key=path, label=label, caption=caption, value='', unit='', kind='branch', on=False, path=path)

    @Slot(str, result='QVariantList')
    def treeRows(self, path):
        if not path:
            guard = getattr(self.ctl, 'session_lock', None)
            return [self.read('lock', 'frontkey-locked', '1' if guard and guard.locked else '0', 'Application lock state'),
                    self.read('emission', 'emission', '1' if any(l.emission for l in self.ctl.instrument.lasers) else '0', 'Any laser emission enabled'),
                    self.read('health', 'system-health-txt', 'Simulation', 'Laser transport is not connected in this version'),
                    self.branch('laser1', 'laser1', 'Laser 1 parameters'), self.branch('laser2', 'laser2', 'Laser 2 parameters')]
        pieces = path.split('/')
        if pieces[0] not in ('laser1', 'laser2'):
            return []
        index = int(pieces[0][-1])-1
        if len(pieces) == 1:
            return [self.read('type', 'type', 'Nexatom DLC'),
                    self.read('product', 'product-name', f'Laser {index+1}'),
                    self.read('emission', 'emission', '1' if self.ctl.instrument.lasers[index].emission else '0'),
                    self.read('health', 'health-txt', 'Simulation'),
                    self.branch('cc', path+'/cc', 'Current controller'),
                    self.branch('tc', path+'/tc', 'Temperature controller'),
                    self.branch('pc', path+'/pc', 'Piezo and scan')]
        return self.controlRows(index, pieces[1].upper())

    def shutdown(self):
        self.read_timer.stop()
        self.save_timer.stop()
        if self.snapshot() != self.last_saved:
            self.save()
