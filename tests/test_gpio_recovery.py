"""Service lifecycle fallback and lock preservation during partial failure."""
import sys,tempfile,unittest
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parent)]
from PySide6.QtCore import QObject,Signal
from PySide6.QtTest import QTest
from test_gpio_adapter import APP
from hardware.service import KnobService

class RecoveryTests(unittest.TestCase):
    def test_missing_lock_sample_does_not_unlock(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=KnobService(Path(tmp)/'controls.json',autostart=False);states=[]
            s.lockChanged.connect(states.append)
            try:
                s.receive_panel(dict(levels={},active={'lock':True},events=[]))
                s.receive_panel(dict(levels={},active={'left_emission':False},events=[]))
                self.assertEqual(states,[True])
            finally:s.shutdown()
    def test_released_and_pressed_lock_transitions_are_not_coalesced(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=KnobService(Path(tmp)/'controls.json',autostart=False);states=[]
            s.lockChanged.connect(states.append)
            try:
                s.receive_panel(dict(levels={},active={'lock':False},events=[('lock',True),('lock',False)]))
                self.assertEqual(states,[True,False])
            finally:s.shutdown()
    def test_failed_legacy_worker_retries_after_owner_stops(self):
        class Worker(QObject):
            frames=Signal(object);status=Signal(bool,str)
            def __init__(self,number):super().__init__();self.number=number
            def start(self):self.status.emit(self.number>1,'Recovered' if self.number>1 else 'Unavailable')
            def stop(self):pass
        workers=[]
        def factory(cfg):
            w=Worker(len(workers)+1);workers.append(w);return w
        with tempfile.TemporaryDirectory() as tmp:
            s=KnobService(Path(tmp)/'controls.json',worker_factory=factory,autostart=False)
            try:
                s.retry();QTest.qWait(1250);self.assertTrue(s.connected)
            finally:s.shutdown()

if __name__=='__main__':unittest.main()
