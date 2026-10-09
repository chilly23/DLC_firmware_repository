"""Real process/IPC/thread/Qt delivery under blocked GUI and burst input."""
import sys
import os
import tempfile
import time
import unittest
from pathlib import Path
from threading import Event

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QCoreApplication
from PySide6.QtTest import QTest
from hardware.gpio import GPIOWorker
from hardware.replay import replay_process
from hardware.service import KnobService

APP=None


def until(condition, timeout=15):
    # Hosted Windows runners have variable scheduling; this is a completion
    # deadline, not a realtime latency measurement. Exact event counts remain checked.
    timeout *= 3 if os.environ.get('CI') == 'true' else 1
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        if condition():return
        QTest.qWait(10)
    raise AssertionError('Deadline exceeded')


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global APP
        APP=QCoreApplication.instance() or QCoreApplication([])
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.service=KnobService(Path(self.temp.name)/'controls.json',autostart=False,
            worker_factory=lambda config:GPIOWorker(config,process_target=replay_process))
        for k in self.service.store.config['knobs']:k['calibrated']=True
        self.calls=[];self.buttons=[];self.acks=[]
        self.service.command.connect(lambda *a:self.calls.append(a))
        self.service.panelAction.connect(self.buttons.append)
        self.addCleanup(self.service.shutdown)
        self.addCleanup(self.temp.cleanup)
        self.service.retry();self.worker=self.service.worker
        self.worker.acknowledgement.connect(self.acks.append)
        until(lambda:self.service.armed=={0,1,3})
    def tearDown(self):
        self.service.shutdown();self.temp.cleanup()
        self.assertFalse(self.worker.isRunning())
        self.assertIsNone(self.worker.process)
    def test_ui_stall_does_not_drop_rotation_or_button_events(self):
        self.worker.submit('start_input',rate=1200)
        until(lambda:any(a['command']=='start_input' for a in self.acks))
        Event().wait(.65)  # Deliberate test fault: GUI event loop cannot run.
        self.worker.submit('stop_input')
        until(lambda:any(a['command']=='stop_input' for a in self.acks))
        QTest.qWait(200)
        until(lambda:self.worker.mailbox.snapshot()['pending']==0)
        expected={i:f['count'] for i,f in self.service.snapshots.items()}
        actual={i:sum(n for k,action,n in self.calls if k==i) for i in expected}
        self.assertEqual(actual,expected)
        self.assertGreater(sum(actual.values()),900)
        self.assertGreaterEqual(len(self.buttons),14)
        self.assertGreater(self.worker.mailbox.snapshot()['high_water'],100)
    def test_commands_are_acknowledged_once_in_fifo_order(self):
        ids=[self.worker.submit('probe') for _ in range(100)]
        until(lambda:len([a for a in self.acks if a['id'] in ids])==100)
        self.assertEqual([a['id'] for a in self.acks if a['id'] in ids],ids)
        self.assertTrue(all(a['ok'] for a in self.acks))
    def test_large_command_burst_with_inputs_cannot_deadlock_full_duplex_ipc(self):
        self.worker.submit('start_input',rate=1000)
        ids=[self.worker.submit('probe') for _ in range(2000)]
        until(lambda:len([a for a in self.acks if a['id'] in ids])==len(ids),timeout=30)
        self.assertEqual([a['id'] for a in self.acks if a['id'] in ids],ids)
        self.assertTrue(self.calls)
    def test_live_reconfigure_keeps_same_owner_process(self):
        old=self.worker
        pid=old.process.pid
        for step in (1,4,2):
            self.service.set_encoder_steps(0,step)
            until(lambda:any(a['command']=='configure' and a['ok'] for a in self.acks))
            self.acks.clear()
            until(lambda:self.service.armed=={0,1,3})
            self.assertIs(self.service.worker,old)
            self.assertEqual(old.process.pid,pid)
    def test_explicit_fault_and_retry_restore_operation(self):
        self.worker.submit('fault_test')
        until(lambda:not self.service.connected)
        self.service.retry()
        until(lambda:self.service.connected and self.service.armed=={0,1,3})
        self.worker.submit('start_input',rate=100)
        until(lambda:len(self.calls)>=9)
        self.assertTrue(self.service.online)
    def test_unexpected_owner_exit_recovers_without_restarting_application(self):
        old=self.service.worker
        old.process.terminate()  # Fault injection, never a production retry path.
        until(lambda:self.service.worker is not old and self.service.armed=={0,1,3})
        self.worker=self.service.worker
        self.worker.submit('start_input',rate=100)
        until(lambda:len(self.calls)>=9)
        self.assertTrue(self.service.online)

if __name__=='__main__':unittest.main(verbosity=2)
