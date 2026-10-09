"""A readable contact without edge support must not disable the encoders."""
import sys,types,errno,unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parent)]
import test_gpio_adapter as gpio_fixture
from hardware.config import DEFAULTS
from hardware.gpio import GPIOWorker,select_chip,short_error

class InputsTests(unittest.TestCase):
    def test_readable_panel_pin_without_interrupts_keeps_knobs_live(self):
        fixture=gpio_fixture.AdapterTests();module,line=fixture.fixture();real=module.request_lines
        line.Edge.NONE='none'
        def request(path,**kw):
            for pins,settings in kw['config'].items():
                if 20 in pins and settings.get('edge_detection')=='both':raise OSError(errno.ENXIO,'GPIO20 does not support interrupts')
            return real(path,**kw)
        module.request_lines=request;cfg=deepcopy(DEFAULTS);cfg['chip']='/dev/gpiochip0';w=GPIOWorker(cfg);frames=[]
        w.frames.connect(frames.append)
        with patch('hardware.gpio.gpio_module',return_value=module),patch.dict(sys.modules,{'gpiod.line':line}):w.run()
        self.assertTrue(frames,'One contact edge-request failure disables all readable controls')
        self.assertEqual(set(frames[0]),{0,1,3})

    def test_request_rejection_is_isolated_to_its_contact(self):
        fixture=gpio_fixture.AdapterTests();module,line=fixture.fixture();real=module.request_lines
        def request(path,**kw):
            if any(20 in pins for pins in kw['config']):raise OSError(errno.EINVAL,'GPIO20 rejects this configuration')
            return real(path,**kw)
        module.request_lines=request;cfg=deepcopy(DEFAULTS);cfg['chip']='/dev/gpiochip0';w=GPIOWorker(cfg)
        frames=[];panels=[];issues=[];w.frames.connect(frames.append);w.panelFrames.connect(panels.append);w.availability.connect(issues.append)
        with patch('hardware.gpio.gpio_module',return_value=module),patch.dict(sys.modules,{'gpiod.line':line}):w.run()
        self.assertEqual(set(frames[0]),{0,1,3})
        self.assertEqual(set(panels[0]['levels']),{'left_emission','right_emission','left_shortcut','right_shortcut'})
        self.assertEqual(set(issues[-1]),{'panel:lock'})
        self.assertTrue(fixture.closed)

    def test_encoder_edges_and_polled_contacts_reach_decoders(self):
        fixture=gpio_fixture.AdapterTests();module,line=fixture.fixture()
        module.EdgeEvent=types.SimpleNamespace(Type=types.SimpleNamespace(RISING_EDGE='rise'))
        clock=[0];frames=[];panels=[]
        class Request:
            def __enter__(self):return self
            def __exit__(self,*a):pass
            def get_values(self,pins):
                return [0 if (p in (17,27) and 8<=clock[0]<18) or (p==12 and 8<=clock[0]<22) else 1 for p in pins]
            def wait_edge_events(self,timeout):clock[0]+=1;return clock[0] in (1,2)
            def read_edge_events(self,max_events):
                # 11 -> 01 -> 00 -> 10 -> 11, two detents per cycle.
                return [types.SimpleNamespace(line_offset=p,event_type=t,timestamp_ns=clock[0]*4_000_000+j,
                    global_seqno=(clock[0]-1)*4+j+1) for j,(p,t) in enumerate(((4,'fall'),(22,'fall'),(4,'rise'),(22,'rise')))]
        module.request_lines=lambda *a,**k:Request()
        cfg=deepcopy(DEFAULTS);cfg['chip']='/dev/gpiochip0';w=GPIOWorker(cfg)
        w.isInterruptionRequested=lambda:clock[0]>=35
        w.frames.connect(frames.append);w.panelFrames.connect(panels.append)
        with patch('hardware.gpio.gpio_module',return_value=module),patch.dict(sys.modules,{'gpiod.line':line}),patch('hardware.gpio.time.monotonic',side_effect=lambda:clock[0]*.004),patch('hardware.gpio.time.monotonic_ns',side_effect=lambda:clock[0]*4_000_000):w.run()
        self.assertEqual(sum(v for f in frames for name,v in f[0]['events'] if name=='rotation'),4)
        self.assertEqual([v for f in frames for name,v in f[0]['events'] if name=='A'],[1,0])
        self.assertEqual([v for f in frames for name,v in f[0]['events'] if name=='push'],[1,0])
        self.assertEqual([v for f in panels for name,v in f['events'] if name=='right_emission'],[True,False])

    def test_chip_number_may_change_and_line_names_are_verified(self):
        fixture=gpio_fixture.AdapterTests();module,_=fixture.fixture()
        chips=[dict(path='/dev/gpiochip4',label='pinctrl-rp1',lines=54)]
        with patch('hardware.gpio.discover',return_value=chips):self.assertEqual(select_chip(module,'auto'),'/dev/gpiochip4')
        class Chip:
            def __init__(self,path):pass
            def __enter__(self):return self
            def __exit__(self,*a):pass
            def get_line_info(self,pin):return types.SimpleNamespace(name=f'GPIO{pin}')
        module.Chip=Chip;chips[0]['label']='new-kernel-label'
        with patch('hardware.gpio.discover',return_value=chips):self.assertEqual(select_chip(module,'auto'),'/dev/gpiochip4')
        with patch('hardware.gpio.discover',return_value=chips*2):
            with self.assertRaises(RuntimeError):select_chip(module,'auto')

    def test_operator_errors_are_single_line_and_actionable(self):
        self.assertIn('Repair',short_error(PermissionError(errno.EACCES,'denied')))
        self.assertIn('Close other',short_error(OSError(errno.EBUSY,'busy')))
        error=short_error(RuntimeError('long\ntrace\n'*30))
        self.assertNotIn('\n',error);self.assertLessEqual(len(error),108)

if __name__=='__main__':unittest.main()
