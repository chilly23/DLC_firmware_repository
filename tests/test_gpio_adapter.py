"""GPIO request boundary, with libgpiod replaced by an in-memory contract fixture."""
import sys,types,unittest
from pathlib import Path
from copy import deepcopy
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QCoreApplication
from hardware.config import DEFAULTS
from hardware.gpio import GPIOWorker
APP=QCoreApplication.instance() or QCoreApplication([])

class AdapterTests(unittest.TestCase):
    def fixture(self,busy=None):
        self.requested=[];self.closed=False;self.worker=None
        owner=self
        class Chip:
            def __init__(self,path):self.path=path
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def get_line_info(self,p):return types.SimpleNamespace(used=p==busy,consumer='rkjxt-live' if p==busy else None)
        class Request:
            def __enter__(self):return self
            def __exit__(self,*args):owner.closed=True
            def get_values(self,pins):return [1]*len(pins)
            def wait_edge_events(self,timeout):raise OSError('fixture disconnected')
        def request_lines(path,**kwargs):owner.requested.append((path,kwargs));return Request()
        module=types.SimpleNamespace(Chip=Chip,LineSettings=lambda **kwargs:kwargs,request_lines=request_lines)
        line=types.SimpleNamespace(Direction=types.SimpleNamespace(INPUT='input'),Edge=types.SimpleNamespace(BOTH='both'),Bias=types.SimpleNamespace(PULL_UP='pullup'),Value=types.SimpleNamespace(ACTIVE=1))
        return module,line
    def run_fixture(self,busy=None):
        module,line=self.fixture(busy);cfg=deepcopy(DEFAULTS);cfg['chip']='/dev/gpiochip0';w=GPIOWorker(cfg)
        frames=[];states=[];w.frames.connect(frames.append);w.status.connect(lambda *a:states.append(a))
        with patch('hardware.gpio.gpio_module',return_value=module),patch.dict(sys.modules,{'gpiod.line':line}):w.run()
        return frames,states
    def test_single_input_only_request_for_three_knobs(self):
        frames,states=self.run_fixture();self.assertEqual(len(self.requested),1)
        path,args=self.requested[0];pins,settings=next(iter(args['config'].items()))
        self.assertEqual(len(set(pins)),21);self.assertEqual(settings,dict(direction='input',edge_detection='both',bias='pullup',active_low=False))
        self.assertEqual(set(frames[0]),{0,1,3});self.assertTrue(states[0][0]);self.assertFalse(states[-1][0]);self.assertTrue(self.closed)
    def test_busy_gpio_reports_owner_and_never_requests(self):
        frames,states=self.run_fixture(4);self.assertFalse(self.requested);self.assertFalse(frames)
        self.assertIn('GPIO4: rkjxt-live',states[-1][1]);self.assertFalse(states[-1][0])
if __name__=='__main__':unittest.main(verbosity=2)
