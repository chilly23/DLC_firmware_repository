"""A decoded rotation batch must survive the service/frontend boundary intact."""
import sys,tempfile,unittest
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parent)]
from test_knobs import APP
from hardware.service import KnobService

class StepDeliveryTests(unittest.TestCase):
    def test_navigation_on_left_does_not_repeat_right_side_toggle(self):
        with tempfile.TemporaryDirectory() as tmp:
            service=KnobService(Path(tmp)/'controls.json',autostart=False);calls=[]
            service.command.connect(lambda *v:calls.append(v))
            try:
                service.connected=True;service.navigation=True;service.navigation_sides={0}
                service.store.config['knobs'][3]['mapping']['up']='graph.lock'
                service.snapshots[3]={'switches':{'A':True}}
                service.held[(3,'up')]=0
                service.tick()
                self.assertEqual(calls,[])
            finally:service.shutdown()
    def test_large_rotation_batch_is_not_truncated(self):
        with tempfile.TemporaryDirectory() as tmp:
            service=KnobService(Path(tmp)/'controls.json',autostart=False);calls=[]
            service.command.connect(lambda *v:calls.append(v))
            try:
                service.dispatch(0,'clockwise',73)
                self.assertEqual(calls,[(0,'value.increase',73)])
            finally:service.shutdown()
if __name__=='__main__':unittest.main(verbosity=2)
