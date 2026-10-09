"""Input delivery regressions. Run against a base with NEXATOM_TEST_BASE."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(os.environ.get('NEXATOM_TEST_BASE', Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(ROOT))
from PySide6.QtCore import QCoreApplication
from hardware.service import KnobService
from hardware.panel import PanelDecoder, PANEL_DEFAULTS
from hardware.decoder import Decoder
from hardware.config import DEFAULTS, CONTACTS

APP = QCoreApplication.instance() or QCoreApplication([])


class DeliveryRegression(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.service = KnobService(Path(self.temp.name) / 'controls.json', autostart=False)
        self.service.connected = True
        self.service.store.config['knobs'][0]['calibrated'] = True
        self.service.armed.add(0)
        self.calls = []
        self.service.command.connect(lambda *args: self.calls.append(args))

    def tearDown(self):
        self.service.shutdown()
        self.temp.cleanup()

    def test_two_panel_presses_in_one_delayed_batch(self):
        key = 'left_shortcut'
        decoder = PanelDecoder({key: PANEL_DEFAULTS[key]}, {key: 1}, 0)
        self.service.receive_panel(decoder.snapshot())
        calls = []
        self.service.panelAction.connect(calls.append)
        for level, ms in ((0, 10), (1, 50), (0, 90), (1, 130)):
            decoder.edge(key, level, ms * 1_000_000)
        decoder.settle(170_000_000)
        self.service.receive_panel(decoder.snapshot())
        self.assertEqual(calls, [key, key], 'Both debounced presses must reach the application')

    def test_long_push_retains_capture_time_when_ui_is_busy(self):
        cfg = self.service.store.config['knobs'][0]
        levels = dict.fromkeys(('encoder_a', 'encoder_b', *CONTACTS), 1)
        decoder = Decoder(cfg, levels, 0)
        decoder.edge('push', 0, 10_000_000)
        decoder.edge('push', 1, 900_000_000)
        decoder.settle(920_000_000)
        # Both press and release arrive after a busy UI, not 890 ms apart.
        with patch('hardware.service.time.monotonic', return_value=2.):
            self.service.receive({0: decoder.snapshot()})
        self.assertEqual(self.calls, [(0, 'navigation.enter', 1)])

    def test_short_push_then_tilt_in_same_batch_are_distinct_gestures(self):
        cfg = self.service.store.config['knobs'][0]
        decoder = Decoder(cfg, dict.fromkeys(('encoder_a', 'encoder_b', *CONTACTS), 1), 0)
        for name, level, ms in (('push',0,10),('push',1,60),('push',0,120),
                                ('A',0,125),('A',1,180),('push',1,185)):
            decoder.edge(name, level, ms * 1_000_000)
        decoder.settle(210_000_000)
        self.service.receive({0: decoder.snapshot()})
        self.assertEqual(self.calls, [(0,'graph.lock',1),(0,'focus.previous',1)])

    def test_partial_disconnect_cancels_held_repeat_without_disabling_other_knobs(self):
        self.service.snapshots[0]={'switches':{'A':True}}
        self.service.held[(0,'up')]=0
        self.service.hardware_fault(dict(group='knob:0',message='Injected disconnect'))
        self.service.tick()
        self.assertFalse(self.calls)
        self.assertFalse(self.service.held)
        self.assertTrue(self.service.connected)

if __name__ == '__main__':
    unittest.main(verbosity=2)
