"""Reproduce input loss when one GPIO is busy or the first connection fails."""
import sys,tempfile,unittest,types
from copy import deepcopy
from unittest.mock import patch
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parent)]
from PySide6.QtCore import QObject,Signal
from PySide6.QtTest import QTest
import test_gpio_adapter as gpio_fixture
from hardware.service import KnobService
from hardware.config import DEFAULTS
from hardware.gpio import GPIOWorker

class RecoveryTests(unittest.TestCase):
    def test_busy_button_must_not_disconnect_all_knobs(self):
        fixture=gpio_fixture.AdapterTests();frames,states=fixture.run_fixture(1)
        self.assertTrue(frames,'A busy button currently disconnects all three knobs')
        self.assertEqual(set(frames[0]),{0,1,3})
        self.assertIn('1 unavailable',states[0][1])
    def test_busy_pin_release_requests_reconnect_without_stopping_good_inputs_first(self):
        fixture=gpio_fixture.AdapterTests();module,line=fixture.fixture();pin_checks=[]
        class Chip:
            def __init__(self,path):pass
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def get_line_info(self,pin):
                if pin==1:pin_checks.append(pin)
                busy=pin==1 and len(pin_checks)==1
                return types.SimpleNamespace(used=busy,consumer='other-reader' if busy else None)
        module.Chip=Chip;config=deepcopy(DEFAULTS);config['chip']='/dev/gpiochip0'
        worker=GPIOWorker(config);frames=[];states=[]
        worker.frames.connect(frames.append);worker.status.connect(lambda *a:states.append(a))
        with patch('hardware.gpio.gpio_module',return_value=module),patch.dict(sys.modules,{'gpiod.line':line}),patch('hardware.gpio.time.monotonic',side_effect=[0,3,3]):worker.run()
        self.assertEqual(set(frames[0]),{0,1,3});self.assertTrue(states[0][0])
        self.assertEqual(states[-1],(False,'GPIO released; reconnecting inputs.'))
        self.assertTrue(fixture.closed)
    def test_missing_lock_sample_does_not_unlock_on_partial_gpio_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            service=KnobService(Path(temp)/'controls.json',autostart=False);states=[]
            service.lockChanged.connect(states.append)
            try:
                service.receive_panel(dict(levels={},active={'lock':True},events=[]))
                service.receive_panel(dict(levels={},active={'left_emission':False},events=[]))
                self.assertEqual(states,[True])
            finally:service.shutdown()
    def test_failed_connection_retries_and_receives_frames(self):
        class Worker(QObject):
            frames=Signal(object);status=Signal(bool,str);panelFrames=Signal(object)
            def __init__(self,config,number):super().__init__();self.number=number
            def start(self):
                if self.number==1:self.status.emit(False,'GPIO device temporarily unavailable')
                else:self.status.emit(True,'Recovered GPIO');self.frames.emit({0:{'levels':{},'switches':{},'events':[],'count':0}})
            def stop(self):pass
        workers=[]
        def factory(config):
            w=Worker(config,len(workers)+1);workers.append(w);return w
        with tempfile.TemporaryDirectory() as temp:
            service=KnobService(Path(temp)/'controls.json',worker_factory=factory,autostart=False)
            try:
                service.retry();QTest.qWait(1200)
                self.assertTrue(service.connected,'Reconnect must happen without another app restart')
                self.assertIn(0,service.snapshots)
            finally:service.shutdown()

if __name__=='__main__':unittest.main(verbosity=2)
