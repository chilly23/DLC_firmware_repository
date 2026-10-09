"""Replay the reported RKJXT direction + push electrical contact pattern."""
import sys,unittest,tempfile,itertools
from pathlib import Path
from unittest.mock import patch
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parent)]
from hardware.calibration import Calibration
from hardware.config import DEFAULTS
from hardware.service import KnobService
from test_knobs import APP,idle,frame

class SharedContactTests(unittest.TestCase):
    def test_tilt_edge_order_never_dispatches_push(self):
        # Both press/release orders, across frames or in one fast event batch.
        for push_contact,direction in [('push','A'),('C','push')]:
            for pressed in itertools.permutations((push_contact,direction)):
                for released in itertools.permutations((push_contact,direction)):
                    for batched in (False,True):
                        with self.subTest(push=push_contact,pressed=pressed,released=released,batched=batched),tempfile.TemporaryDirectory() as tmp:
                            s=KnobService(Path(tmp)/'controls.json',autostart=False);calls=[]
                            s.command.connect(lambda *v:calls.append(v));s.set_status(True,'fixture')
                            cfg=s.store.config['knobs'][0];cfg['calibrated']=True
                            if push_contact=='C':cfg.update(push_contact='C',directions=dict(up='push',right='D',down='A',left='B'))
                            s.armed.add(0);active=set();events=[]
                            try:
                                for name,value in [(c,1) for c in pressed]+[(c,0) for c in released]:
                                    active.add(name) if value else active.discard(name);events.append((name,value))
                                    if not batched:s.receive({0:frame([(name,value)],active)})
                                if batched:s.receive({0:frame(events)})
                                self.assertEqual([a for _,a,_ in calls],['focus.previous'])
                                self.assertFalse(s.pushes);self.assertFalse(s.direction_gestures)
                            finally:s.shutdown()

    def test_calibration_rejects_two_directions_and_waits_for_full_release(self):
        cal=Calibration(0,DEFAULTS['knobs'][0]);cal.feed(idle(),0,0);cal.next(.4)
        clock=1.
        def feed(active):
            nonlocal clock
            levels=idle();levels.update({c:0 for c in active})
            cal.feed(levels,0,clock);cal.feed(levels,0,clock+.06);clock+=.2
        feed(['push']);feed([]);self.assertEqual(cal.stage,2)
        feed(['A','push']);feed(['push']);self.assertEqual(cal.stage,2)
        feed([]);self.assertEqual(cal.stage,3)
        feed(['B','C','push']);self.assertIn('More than one direction',cal.error)
        feed(['B','push']);feed([]);self.assertEqual(cal.stage,3)
        feed(['D','push']);feed([]);self.assertEqual(cal.stage,4)

    def test_calibration_accepts_direction_plus_push(self):
        cal=Calibration(0,DEFAULTS['knobs'][0]);clock=1.;levels=idle()
        cal.feed(levels,0,clock);cal.next(clock+.4)
        # Replay movements requested by the real wizard; no stage assumptions.
        physical={'Move up':('A','push'),'Move right':('D','push'),'Move down':('C','push'),
                  'Move left':('B','push'),'Press the centre':('push',)}
        for _ in range(5):
            requested=cal.title;contacts=physical[requested];before=cal.stage;clock+=1
            levels=idle();levels.update({k:0 for k in contacts});cal.feed(levels,0,clock);cal.feed(levels,0,clock+.06)
            levels=idle();cal.feed(levels,0,clock+.2);cal.feed(levels,0,clock+.26)
            self.assertEqual(cal.stage,before+1,cal.error or requested)
        cal.feed(levels,2,clock+1);cal.next(clock+1.1);cal.feed(levels,0,clock+2);cal.next(clock+2.1)
        cfg=cal.result();self.assertEqual(cfg['directions'],dict(up='A',right='D',down='C',left='B'))
        self.assertEqual(cfg['push_contact'],'push')
    def test_tilting_does_not_fire_push_or_hold_shortcut(self):
        with tempfile.TemporaryDirectory() as tmp,patch('hardware.service.time.monotonic',return_value=1.) as clock:
            s=KnobService(Path(tmp)/'controls.json',autostart=False);calls=[];s.command.connect(lambda *v:calls.append(v))
            try:
                s.set_status(True,'fixture');s.store.config['knobs'][0]['calibrated']=True
                s.receive({0:frame()});clock.return_value=1.3;s.receive({0:frame()})
                s.receive({0:frame([('push',1)],['push'])});clock.return_value=1.32
                s.receive({0:frame([('A',1)],['A','push'])});clock.return_value=2.2;s.tick()
                self.assertFalse(s.navigation,'Tilt incorrectly triggers the long-push navigation shortcut')
                s.receive({0:frame([('A',0)],['push'])});s.receive({0:frame([('push',0)])})
                self.assertFalse(any(a in ('graph.lock','navigation.enter') for _,a,_ in calls),calls)
                s.receive({0:frame([('push',1)],['push'])});clock.return_value=2.3;s.receive({0:frame([('push',0)])})
                self.assertEqual(calls[-1],(0,'graph.lock',1),'A genuine centre push must still work')
            finally:s.shutdown()
if __name__=='__main__':unittest.main(verbosity=2)
