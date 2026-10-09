"""Input-only libgpiod v2 acquisition; no hardware work runs on the UI thread.

Encoder transitions use buffered kernel edge events. Joystick/button contacts
are sampled every 4 ms and debounced by the existing electrical decoders. A
contact therefore does not need interrupt support merely to be read.
"""
from contextlib import ExitStack
from copy import deepcopy
from datetime import timedelta
from glob import glob
import errno
import logging
import time

from PySide6.QtCore import QThread, Signal
from .decoder import Decoder
from .panel import PanelDecoder

LOG = logging.getLogger('nexatom.gpio')


def gpio_module():
    import gpiod
    if not hasattr(gpiod, 'request_lines'):
        raise RuntimeError('GPIO library needs updating. Run Repair setup.')
    return gpiod


def discover(gpiod):
    result = []
    for path in sorted(glob('/dev/gpiochip*')):
        try:
            with gpiod.Chip(path) as chip:
                info = chip.get_info()
                result.append(dict(path=path, label=info.label, lines=info.num_lines))
        except OSError as exc:
            result.append(dict(path=path, label=str(exc), lines=0, error=exc.errno))
    return result


def select_chip(gpiod, configured):
    if configured != 'auto':
        return configured
    chips = discover(gpiod)
    LOG.debug('GPIO chip inventory: %s', chips)
    candidates = [c['path'] for c in chips if 'rp1' in c['label'].lower() and c['lines'] >= 28]
    if len(candidates) == 1:
        return candidates[0]
    # Kernel chip numbering/labels can change. Verify BCM line names rather
    # than guessing chip0 or accidentally requesting an unrelated GPIO bank.
    if not candidates:
        for entry in chips:
            if entry['lines'] < 28:
                continue
            with gpiod.Chip(entry['path']) as chip:
                if all(chip.get_line_info(pin).name == f'GPIO{pin}' for pin in (2, 3, 4, 17, 27)):
                    candidates.append(entry['path'])
    if len(candidates) == 1:
        return candidates[0]
    if any(c.get('error') in (errno.EACCES, errno.EPERM) for c in chips):
        raise PermissionError(errno.EACCES, 'GPIO chip access denied')
    if not chips:
        raise RuntimeError('No GPIO device found. Check Raspberry Pi OS.')
    LOG.error('GPIO chip selection failed: %s', chips)
    raise RuntimeError('GPIO chip not identified. Check logs/controls.log.')


def short_error(exc):
    """Actionable single-line operator text; full exceptions go to controls.log."""
    code = getattr(exc, 'errno', None)
    if isinstance(exc, ImportError):
        return 'GPIO library missing. Run Repair setup.'
    if isinstance(exc, PermissionError) or code in (errno.EACCES, errno.EPERM):
        return 'GPIO access denied. Run Repair setup.'
    if code == errno.EBUSY:
        return 'GPIO in use. Close other GPIO apps, then Retry GPIO.'
    if code in (errno.ENOENT, errno.ENODEV):
        return 'GPIO device missing. Check the selected chip.'
    if code in (errno.ENXIO, errno.EINVAL, errno.EOPNOTSUPP):
        return 'GPIO request unsupported. See Control settings and logs.'
    text = ' '.join(str(exc).split())
    return text if len(text) <= 108 else text[:105] + '...'


class GPIOWorker(QThread):
    frames = Signal(object)
    status = Signal(bool, str)
    panelFrames = Signal(object)
    availability = Signal(object)

    def __init__(self, config):
        super().__init__()
        self.config = deepcopy(config)

    def run(self):
        try:
            self.capture()
        except Exception as exc:
            LOG.exception('GPIO connection failed')
            self.status.emit(False, short_error(exc))

    def capture(self):
        gpiod = gpio_module()
        from gpiod.line import Direction, Edge, Bias, Value
        path = select_chip(gpiod, self.config['chip'])
        knobs = {i: k for i, k in enumerate(self.config['knobs']) if k['enabled'] and k['pins']}
        panel = {k: v for k, v in self.config.get('panel', {}).items() if v['enabled']}
        groups = [('knob:' + str(i), k['pins']) for i, k in knobs.items()]
        groups += [('panel:' + key, {key: v['pin']}) for key, v in panel.items()]
        if not groups:
            self.status.emit(False, 'All wired inputs are disabled.')
            return
        issues, busy = {}, {}
        with gpiod.Chip(path) as chip:
            for key, mapping in groups:
                for pin in mapping.values():
                    line = chip.get_line_info(pin)
                    if line.used:
                        busy[pin] = f'GPIO{pin}: {line.consumer or "kernel driver"}'
                        issues.setdefault(key, busy[pin])
        for owner in busy.values():
            LOG.warning('Input occupied: %s', owner)
        available = [(key, mapping) for key, mapping in groups if key not in issues]
        self.availability.emit(dict(issues))
        if not available:
            raise OSError(errno.EBUSY, 'All configured controls are occupied')

        def acquire(stack, mappings):
            pins = [pin for _, mapping in mappings for pin in mapping.values()]
            encoder_pins = [pin for _, mapping in mappings for name, pin in mapping.items() if name.startswith('encoder_')]
            contacts = [pin for pin in pins if pin not in encoder_pins]
            config = {}
            for subset, edges in ((encoder_pins, Edge.BOTH), (contacts, Edge.NONE)):
                if subset:
                    config[tuple(subset)] = gpiod.LineSettings(direction=Direction.INPUT,
                        edge_detection=edges, bias=Bias.PULL_UP, active_low=False)
            request = stack.enter_context(gpiod.request_lines(path, consumer='nexatom-controls',
                config=config, event_buffer_size=4096))
            return request, pins, bool(encoder_pins)

        with ExitStack() as stack:
            try:
                requests = [acquire(stack, available)]
            except OSError as bulk_error:
                if bulk_error.errno in (errno.EACCES, errno.EPERM, errno.ENOENT, errno.ENODEV):
                    raise
                # A late owner or one driver-rejected line must not take down
                # every knob/button. Failed groups remain visible in Settings.
                LOG.warning('Combined GPIO request failed; isolating controls: %s', bulk_error)
                requests = []
                for key, mapping in available:
                    try:
                        requests.append(acquire(stack, [(key, mapping)]))
                    except OSError as exc:
                        LOG.warning('%s request failed: %s', key, exc, exc_info=True)
                        issues[key] = short_error(exc)
                        with gpiod.Chip(path) as chip:
                            for pin in mapping.values():
                                line = chip.get_line_info(pin)
                                if line.used:
                                    busy[pin] = f'GPIO{pin}: {line.consumer or "kernel driver"}'
                                    issues[key] = busy[pin]
                if not requests:
                    self.availability.emit(dict(issues))
                    raise bulk_error
            knobs = {i: k for i, k in knobs.items() if 'knob:' + str(i) not in issues}
            panel = {k: v for k, v in panel.items() if 'panel:' + k not in issues}
            self.availability.emit(dict(issues))
            reverse = {p: (i, name) for i, k in knobs.items() for name, p in k['pins'].items()}
            reverse.update({v['pin']: ('panel', k) for k, v in panel.items()})

            def levels():
                result = {i: {} for i in knobs}
                result['panel'] = {}
                for request, pins, _ in requests:
                    for pin, value in zip(pins, request.get_values(pins)):
                        i, name = reverse[pin]
                        result[i][name] = int(value == Value.ACTIVE)
                return result

            initial = levels()
            now = time.monotonic_ns()
            decoders = {i: Decoder(k, initial[i], now) for i, k in knobs.items()}
            panel_decoder = PanelDecoder(panel, initial['panel'], now)
            summary = f'{len(knobs)} knobs / {len(panel)} buttons & lock ready'
            if issues:
                summary += f' · {len(issues)} unavailable; see controls below'
            self.status.emit(True, summary)
            self.frames.emit({i: d.snapshot() for i, d in decoders.items()})
            self.panelFrames.emit(panel_decoder.snapshot())
            last_seq, discard_before = {}, 0
            published = time.monotonic()
            next_owner_check = published + 2
            edge_requests = [r for r, _, has_edges in requests if has_edges]
            while not self.isInterruptionRequested():
                if busy and time.monotonic() >= next_owner_check:
                    next_owner_check = time.monotonic() + 2
                    with gpiod.Chip(path) as chip:
                        freed = any(not chip.get_line_info(pin).used for pin in busy)
                    if freed:
                        self.status.emit(False, 'GPIO released; reconnecting inputs.')
                        return
                events = []
                if not edge_requests:
                    time.sleep(.004)
                for i, request in enumerate(edge_requests):
                    if request.wait_edge_events(timeout=timedelta(milliseconds=4 if i == 0 else 0)):
                        events.extend((event, i) for event in request.read_edge_events(max_events=512))
                for event, stream in sorted(events, key=lambda pair: pair[0].timestamp_ns):
                    previous = last_seq.get(stream)
                    last_seq[stream] = event.global_seqno
                    if event.timestamp_ns < discard_before:
                        continue
                    if previous is not None and event.global_seqno != previous + 1:
                        fresh = levels()
                        discard_before = time.monotonic_ns()
                        for i, decoder in decoders.items():
                            decoder.resync(fresh[i], discard_before)
                        panel_decoder = PanelDecoder(panel, fresh['panel'], discard_before)
                        continue
                    index, name = reverse[event.line_offset]
                    decoders[index].edge(name, int(event.event_type == gpiod.EdgeEvent.Type.RISING_EDGE), event.timestamp_ns)
                # Never poll encoder states into the decoder: buffered edges
                # are authoritative and must not be replaced by a later level.
                now = time.monotonic_ns()
                fresh = levels()
                for i, decoder in decoders.items():
                    for name, value in fresh[i].items():
                        if not name.startswith('encoder_'):
                            decoder.edge(name, value, now)
                    decoder.settle(now)
                for key, value in fresh['panel'].items():
                    panel_decoder.edge(key, value, now)
                panel_decoder.settle(now)
                if time.monotonic() - published >= 1 / 60:
                    self.frames.emit({i: d.snapshot() for i, d in decoders.items()})
                    self.panelFrames.emit(panel_decoder.snapshot())
                    published = time.monotonic()

    def stop(self):
        self.requestInterruption()
        self.wait()
