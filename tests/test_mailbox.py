import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from hardware.mailbox import Mailbox

def rotation(n,group='knob:0',epoch=1):
    return dict(kind='input',group=group,epoch=epoch,frame=dict(events=[('rotation',n)],count=n,event_times=[1]))

class MailboxTests(unittest.TestCase):
    def test_only_adjacent_same_direction_steps_are_added(self):
        q=Mailbox()
        for n in (1,1,1,-1,-1,1):q.put(rotation(n))
        self.assertEqual([q.take()['frame']['events'][0][1] for _ in range(3)],[3,-2,1])
        self.assertEqual(q.snapshot()['delivered'],6)
        self.assertIsNone(q.take())
    def test_contact_configuration_epoch_and_other_knob_are_ordering_barriers(self):
        barriers=[dict(kind='reset',epoch=2),rotation(1,group='knob:1'),rotation(1,epoch=2),
                  dict(kind='input',group='knob:0',epoch=1,frame=dict(events=[('push',True)]))]
        for barrier in barriers:
            with self.subTest(barrier=barrier):
                q=Mailbox();q.put(rotation(1));q.put(barrier);q.put(rotation(1))
                self.assertEqual(q.take()['frame']['events'],[('rotation',1)])
                self.assertEqual(q.take(),barrier)
                self.assertEqual(q.take()['frame']['events'],[('rotation',1)])
    def test_ack_priority_does_not_reorder_inputs(self):
        q=Mailbox();q.put(rotation(1));q.put(rotation(-1));q.put(dict(kind='ack',id=42))
        self.assertEqual(q.take()['id'],42)
        self.assertEqual([q.take()['frame']['events'][0][1] for _ in range(2)],[1,-1])

if __name__=='__main__':unittest.main()
