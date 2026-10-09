"""Request fallback, partial ownership, discovery and operator diagnostics."""
import sys,types,errno,unittest
from pathlib import Path
from copy import deepcopy
from unittest.mock import patch
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parent)]
from test_owner import Driver,Connection,Selector
from hardware.capture import Reactor
from hardware.config import DEFAULTS
from hardware.discovery import select_chip,short_error

class InputsTests(unittest.TestCase):
    def fixture(self):
        d=Driver();cfg=deepcopy(DEFAULTS);cfg['chip']='/dev/gpiochip4'
        return d,Reactor(Connection(),cfg,module=d,line=d.line,selector=Selector()),cfg
    def test_readable_panel_pin_without_interrupts_is_explicitly_degraded(self):
        d,r,cfg=self.fixture();original=d.request_lines
        def request(path,**kw):
            if any(20 in pins and settings['edge_detection']=='both' for pins,settings in kw['config'].items()):
                raise OSError(errno.ENXIO,'No interrupts')
            return original(path,**kw)
        d.request_lines=request
        try:
            r.configure(cfg)
            self.assertEqual(r.groups['panel:lock'].polled,('lock',))
            self.assertIn('fallback',r.groups['panel:lock'].issue)
            self.assertTrue(r.groups['knob:0'].request)
        finally:r.close()
    def test_request_rejection_is_isolated_to_its_contact(self):
        d,r,cfg=self.fixture();d.fail[20]=errno.EINVAL
        try:
            r.configure(cfg)
            self.assertEqual([k for k,g in r.groups.items() if g.request is None],['panel:lock'])
            self.assertEqual(r.groups['panel:lock'].retry_at,float('inf'))
        finally:r.close()
    def test_busy_control_is_retried_without_releasing_other_controls(self):
        d,r,cfg=self.fixture();d.fail[4]=errno.EBUSY
        try:
            r.configure(cfg);good=r.groups['knob:1'].request
            self.assertTrue(r.groups['knob:0'].retry_at<float('inf'))
            d.fail.clear();r.command(dict(command='retry',id=1,sent_ns=1))
            self.assertIs(r.groups['knob:1'].request,good)
            self.assertTrue(r.groups['knob:0'].request)
        finally:r.close()
    def test_chip_number_changes_and_ambiguity_is_rejected(self):
        module=types.SimpleNamespace()
        chips=[dict(path='/dev/gpiochip4',label='pinctrl-rp1',lines=54)]
        with patch('hardware.discovery.discover',return_value=chips):self.assertEqual(select_chip(module,'auto'),'/dev/gpiochip4')
        with patch('hardware.discovery.discover',return_value=chips*2):
            with self.assertRaises(RuntimeError):select_chip(module,'auto')
    def test_errors_are_single_line_and_actionable(self):
        self.assertIn('Repair',short_error(PermissionError(errno.EACCES,'denied')))
        self.assertIn('Close other',short_error(OSError(errno.EBUSY,'busy')))
        text=short_error(RuntimeError('long\ntrace\n'*30));self.assertNotIn('\n',text);self.assertLessEqual(len(text),108)

if __name__=='__main__':unittest.main()
