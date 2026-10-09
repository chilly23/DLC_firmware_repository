"""Electrical decoding, calibration transactions, persistence and command semantics."""
import sys,tempfile,unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QCoreApplication
from hardware.config import DEFAULTS,PIN_MAPS,CONTACTS,ControlStore,validate
from hardware.decoder import Decoder,Quadrature
from hardware.calibration import Calibration
from hardware.service import KnobService
from interaction.numeric import step_value,digit_power,cursor_for_power

APP=QCoreApplication.instance() or QCoreApplication([])

def idle():return dict.fromkeys(('encoder_a','encoder_b',*CONTACTS),1)
def frame(events=(),active=(),lost=0):
    return dict(levels=idle(),switches={c:c in active for c in CONTACTS},count=0,events=list(events),lost=lost)

class DecoderTests(unittest.TestCase):
    def test_exact_unique_bcm_pins(self):
        self.assertEqual(PIN_MAPS[0],dict(C=2,D=3,encoder_a=4,A=17,push=27,encoder_b=22,B=10))
        self.assertEqual(PIN_MAPS[1],dict(C=14,B=15,encoder_b=18,push=23,A=24,encoder_a=25,D=8))
        self.assertEqual(PIN_MAPS[2],dict(B=26,encoder_b=19,C=13,D=6,encoder_a=5,A=0,push=21))
        pins=[p for k in PIN_MAPS for p in k.values()];self.assertEqual(len(set(pins)),21)
        self.assertFalse(DEFAULTS['knobs'][3]['enabled']);validate(DEFAULTS)
    def test_config_rejects_duplicate_lines_and_unknown_commands(self):
        cfg=deepcopy(DEFAULTS);cfg['knobs'][1]['pins']['C']=2
        with self.assertRaises(ValueError):validate(cfg)
        cfg=deepcopy(DEFAULTS);cfg['knobs'][0]['mapping']['push']='shell.execute'
        with self.assertRaises(ValueError):validate(cfg)
    def test_quadrature_direction_resolution_bounce_invalid(self):
        for transitions,expected in ((1,4),(2,2),(4,1)):
            q=Quadrature(1,1,transitions)
            self.assertEqual(sum(q.feed(a,b) for a,b in [(0,1),(0,0),(1,0),(1,1)]),expected)
            self.assertEqual(sum(q.feed(a,b) for a,b in [(1,0),(0,0),(0,1),(1,1)]),-expected)
        q=Quadrature(1,1,2)
        self.assertEqual(sum(q.feed(a,b) for a,b in [(0,1),(1,1)]),0)
        self.assertEqual(q.feed(0,0),0);self.assertEqual(q.invalid,1)
    def test_switch_bounce_does_not_double_trigger(self):
        d=Decoder(DEFAULTS['knobs'][0],idle(),0)
        d.edge('A',0,1_000_000);d.edge('A',1,3_000_000);d.edge('A',0,5_000_000)
        d.settle(12_000_000);self.assertEqual(d.snapshot()['events'],[])
        d.settle(14_000_000);self.assertEqual(d.snapshot()['events'],[('A',1)])
        d.settle(30_000_000);self.assertEqual(d.snapshot()['events'],[])
        d.edge('A',1,35_000_000);d.settle(44_000_000);self.assertEqual(d.snapshot()['events'],[('A',0)])
    def test_resync_never_fabricates_press(self):
        d=Decoder(DEFAULTS['knobs'][0],idle(),0);levels=idle();levels['push']=0
        d.edge('A',0,1);d.resync(levels,50_000_000)
        self.assertEqual(d.snapshot()['events'],[]);self.assertEqual(d.lost,1)
    def test_released_states_are_not_global_gpio_boot_assumptions(self):
        cfg=deepcopy(DEFAULTS['knobs'][0]);cfg['released']={k:int(cfg['pins'][k]<=8) for k in CONTACTS}
        levels=idle();levels.update(cfg['released']);d=Decoder(cfg,levels,0)
        self.assertFalse(any(d.snapshot()['switches'].values()))
        d.edge('A',1,1_000_000);d.settle(10_000_000);self.assertEqual(d.snapshot()['events'],[('A',1)])

class CalibrationTests(unittest.TestCase):
    def test_remap_push_and_reversed_encoder_transactionally(self):
        original=deepcopy(DEFAULTS['knobs'][0]);cal=Calibration(0,original);levels=idle();clock=1.;count=0
        cal.feed(levels,count,clock);self.assertFalse(cal.next(1.1));self.assertTrue(cal.next(1.4))
        for contact in ('D','B','push','A','C'):
            clock+=1;levels[contact]=0;cal.feed(levels,count,clock);cal.feed(levels,count,clock+.05)
            self.assertEqual(cal.candidate,contact)
            levels[contact]=1;cal.feed(levels,count,clock+.1);cal.feed(levels,count,clock+.16)
        self.assertEqual(cal.stage,6);self.assertFalse(original['calibrated'])
        cal.feed(levels,-2,clock+1);self.assertTrue(cal.next(clock+1.1))
        cal.feed(levels,0,clock+2);self.assertTrue(cal.next(clock+2.1))
        result=cal.result();self.assertTrue(result['calibrated']);self.assertTrue(result['reverse_encoder'])
        self.assertEqual(result['directions'],dict(up='D',right='B',down='push',left='A'));self.assertEqual(result['push_contact'],'C')
        cfg=deepcopy(DEFAULTS);cfg['knobs'][0]=result;validate(cfg)
    def test_duplicate_contact_and_same_rotation_rejected(self):
        cal=Calibration(0,DEFAULTS['knobs'][0]);cal.feed(idle(),0,0);cal.next(1)
        cal.contacts={'up':'A'};cal.stage=2;v=idle();v['A']=0;cal.feed(v,0,2);cal.feed(v,0,2.1)
        self.assertIn('already assigned',cal.error);self.assertEqual(cal.stage,2)
        cal.stage=7;cal.cw_sign=1;cal.rotation=3;self.assertFalse(cal.next(3));self.assertEqual(cal.stage,7)
        with self.assertRaises(ValueError):cal.result()
    def test_persistence_and_cancel_preserve_previous(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'controls.json';store=ControlStore(path);cfg=deepcopy(DEFAULTS)
            cfg['knobs'][1]['mapping']['push']='settings.open';store.commit(cfg)
            self.assertEqual(ControlStore(path).config,cfg);cal=Calibration(1,cfg['knobs'][1]);cal.stage=2
            self.assertEqual(ControlStore(path).config,cfg)
            path.write_text('{broken');fallback=ControlStore(path);self.assertTrue(fallback.error);self.assertEqual(fallback.config,DEFAULTS)

class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.s=KnobService(Path(self.tmp.name)/'controls.json',autostart=False)
        self.clock=patch('hardware.service.time.monotonic',return_value=10.);self.now=self.clock.start()
        self.calls=[];self.s.command.connect(lambda *a:self.calls.append(a));self.s.set_status(True,'test')
    def tearDown(self):self.s.shutdown();self.clock.stop();self.tmp.cleanup()
    def arm(self,index=0):
        self.s.store.config['knobs'][index]['calibrated']=True
        self.s.receive({index:frame()});self.now.return_value+=.3;self.s.receive({index:frame()})
    def test_uncalibrated_and_startup_held_are_silent(self):
        self.s.receive({0:frame([('push',1)],['push'])});self.assertFalse(self.calls)
        self.s.store.config['knobs'][0]['calibrated']=True;self.s.receive({0:frame([],['push'])})
        self.now.return_value+=1;self.s.receive({0:frame([('push',0)])});self.assertFalse(self.calls)
        self.now.return_value+=.3;self.s.receive({0:frame()});self.assertIn(0,self.s.armed)
    def test_independent_knobs_and_encoder_reverse(self):
        self.arm(0);self.arm(1);self.s.receive({0:frame([('rotation',1)]),1:frame([('rotation',1)])})
        self.assertEqual(self.calls,[(0,'value.increase',1),(1,'focus.next',1)])
        self.s.store.config['knobs'][0]['reverse_encoder']=True;self.s.receive({0:frame([('rotation',1)])})
        self.assertEqual(self.calls[-1],(0,'value.decrease',1))
    def test_short_push_once_and_long_push_navigation_only(self):
        self.arm();self.s.receive({0:frame([('push',1)],['push'])});self.now.return_value+=.1;self.s.receive({0:frame([('push',0)])})
        self.assertEqual(self.calls,[(0,'graph.lock',1)]);self.calls.clear()
        self.s.receive({0:frame([('push',1)],['push'])});self.now.return_value+=.71;self.s.tick();self.s.receive({0:frame([('push',0)])})
        self.assertEqual(self.calls,[(0,'navigation.enter',1)])
        self.s.receive({0:frame([('rotation',1)])});self.assertEqual(self.calls[-1],(0,'focus.next',1))
    def test_lost_edges_disarm_held_inputs(self):
        self.arm();self.s.receive({0:frame([('A',1)],['A'])});self.calls.clear()
        self.s.receive({0:frame([('rotation',1)],['A'],lost=1)});self.now.return_value+=2;self.s.tick()
        self.assertFalse(self.calls);self.assertNotIn(0,self.s.armed)
    def test_held_direction_repeats_but_stops_on_release(self):
        self.arm();self.s.receive({0:frame([('A',1)],['A'])});self.now.return_value+=.5;self.s.tick()
        self.assertEqual(len(self.calls),2);self.s.receive({0:frame([('A',0)])});self.now.return_value+=1;self.s.tick();self.assertEqual(len(self.calls),2)
    def test_calibration_suppresses_all_shortcuts_and_cancel_rearms(self):
        self.arm();self.s.start_calibration(0);self.s.receive({0:frame([('rotation',1)])});self.assertFalse(self.calls)
        self.s.cancel_calibration();self.assertFalse(self.s.armed)

class NumericTests(unittest.TestCase):
    def test_digit_and_cursor_are_decimal_exact(self):
        self.assertEqual(step_value('229.547',1,-3,0,500,3),'229.548')
        self.assertEqual(step_value('-0.100',1,-1,-80,20,3),'0.000')
        self.assertEqual(step_value('499.999',1,0,0,500,3),'500.000')
        self.assertEqual(step_value('-79.9',-1,1,-80,20,1),'-80.0')
        for power in (-3,-2,-1,0,1):
            text='-12.345';self.assertEqual(digit_power(text,cursor_for_power(text,power),3),power)
        with self.assertRaises(ValueError):step_value('NaN',1,0,0,500,3)

if __name__=='__main__':unittest.main(verbosity=2)
