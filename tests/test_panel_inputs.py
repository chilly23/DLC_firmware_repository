"""Panel contacts, unique GPIO ownership and real calibration persistence."""
import sys,tempfile,unittest
from pathlib import Path
from copy import deepcopy
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parent)]
from test_knobs import APP
from hardware.panel import PANEL_DEFAULTS,PanelDecoder
from hardware.config import DEFAULTS,validate,ControlStore
from hardware.service import KnobService

class PanelTests(unittest.TestCase):
    def test_lock_still_reports_while_calibrating_another_button(self):
        with tempfile.TemporaryDirectory() as tmp:
            service=KnobService(Path(tmp)/'controls.json',autostart=False);locks=[]
            service.lockChanged.connect(locks.append)
            try:
                service.panel_calibration=dict(key='left_emission',released=1,pressed=None)
                service.receive_panel(dict(levels={'left_emission':1},active={'lock':True,'left_emission':False},events=[]))
                self.assertEqual(locks,[True])
            finally:service.shutdown()
    def test_gpio8_collision_is_rejected_without_breaking_other_inputs(self):
        config=deepcopy(DEFAULTS);config['panel']['left_shortcut']['enabled']=True
        with self.assertRaisesRegex(ValueError,'GPIO8 is already assigned'):validate(config)
        config['panel']['left_shortcut']['pin']=16;validate(config)
    def test_bounce_produces_one_press_and_one_release(self):
        cfg={'right_emission':deepcopy(PANEL_DEFAULTS['right_emission'])}
        d=PanelDecoder(cfg,{'right_emission':1},0)
        for level,now in [(0,1_000_000),(1,4_000_000),(0,7_000_000)]:d.edge('right_emission',level,now)
        d.settle(31_000_000);self.assertFalse(d.snapshot()['events'])
        d.settle(34_000_000);self.assertEqual(d.snapshot()['events'],[('right_emission',True)])
        d.settle(40_000_000);self.assertFalse(d.snapshot()['events'])
        d.edge('right_emission',1,50_000_000);d.settle(80_000_000);self.assertEqual(d.snapshot()['events'],[('right_emission',False)])
    def test_startup_held_button_is_silent_and_lock_is_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=KnobService(Path(tmp)/'controls.json',autostart=False);actions=[];locks=[]
            s.panelAction.connect(actions.append);s.lockChanged.connect(locks.append)
            try:
                s.receive_panel(dict(levels={},active={'right_emission':True,'lock':True},events=[('right_emission',True)]))
                self.assertEqual(actions,[]);self.assertEqual(locks,[True])
                s.receive_panel(dict(levels={},active={'right_emission':False,'lock':False},events=[]))
                s.receive_panel(dict(levels={},active={'right_emission':True,'lock':False},events=[('right_emission',True)]))
                self.assertEqual(actions,['right_emission'])
            finally:s.shutdown()
    def test_calibration_accepts_active_high_and_saves_only_after_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'controls.json';s=KnobService(path,autostart=False);s.connected=True
            try:
                s.panel_snapshot=dict(levels={'left_emission':0});s.calibrate_panel('left_emission')
                s.receive_panel(dict(levels={'left_emission':1},active={'left_emission':False},events=[]))
                self.assertEqual(s.store.config['panel']['left_emission']['active_level'],0)
                s.receive_panel(dict(levels={'left_emission':0},active={'left_emission':True},events=[]))
                self.assertIsNone(s.panel_calibration)
                self.assertEqual(ControlStore(path).config['panel']['left_emission']['active_level'],1)
            finally:s.shutdown()
if __name__=='__main__':unittest.main(verbosity=2)
