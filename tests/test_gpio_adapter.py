"""GPIO adapter contract updated for the v1.17 single-process owner."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_owner import Driver,Connection,Selector
from hardware.capture import Reactor
from hardware.config import DEFAULTS
from copy import deepcopy
from PySide6.QtCore import QCoreApplication
APP=QCoreApplication.instance() or QCoreApplication([])

class AdapterTests(unittest.TestCase):
    def test_one_owner_requests_exact_wiring_as_independent_controls(self):
        d=Driver();c=Connection();cfg=deepcopy(DEFAULTS);cfg['chip']='/dev/gpiochip4'
        r=Reactor(c,cfg,module=d,line=d.line,selector=Selector())
        try:
            r.configure(cfg)
            self.assertEqual(d.used,{0,1,2,3,4,5,6,7,8,10,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27})
            self.assertEqual(len([g for g in r.groups if g.startswith('knob:')]),3)
            self.assertTrue(all(req.settings['consumer']=='nexatom-controls' for req in d.live))
        finally:r.close()
        self.assertFalse(d.used)

if __name__=='__main__':unittest.main()
