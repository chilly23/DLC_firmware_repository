import sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QCoreApplication
from interaction.notifications import Notifications
APP=QCoreApplication.instance() or QCoreApplication([])

class NoticeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.n=Notifications(Path(self.temp.name)/'notifications.json');self.n.timer.stop()
    def tearDown(self):self.n.deleteLater();self.temp.cleanup()
    def test_newest_is_above_existing_and_ids_address_individual_cards(self):
        self.n.post('First');first=self.n.cards[0]['id'];self.n.post('Second');self.n.post('Third')
        self.assertEqual([c['text'] for c in self.n.cards],['Third','Second','First'])
        self.n.dismissId(first);self.assertEqual([c['text'] for c in self.n.cards],['Third','Second'])
    def test_expiry_blurs_and_fades_before_removal(self):
        with patch('interaction.notifications.time.monotonic',return_value=100):self.n.post('Timed')
        with patch('interaction.notifications.time.monotonic',return_value=103.3):self.n.tick()
        with patch('interaction.notifications.time.monotonic',return_value=103.6):self.n.tick()
        self.assertEqual(len(self.n.cards),1);self.assertGreater(self.n.cards[0]['blurStep'],0)
        self.assertTrue(0<self.n.cards[0]['alpha']<1)
        with patch('interaction.notifications.time.monotonic',return_value=104):self.n.tick()
        self.assertFalse(self.n.cards)
    def test_new_arrival_does_not_restart_old_timer_or_discard_consent(self):
        calls=[]
        self.n.post('Confirm?','warning',decision=lambda:calls.append('accepted'));decision=self.n.cards[0]['id']
        with patch('interaction.notifications.time.monotonic',return_value=10):self.n.post('First')
        deadline=self.n.cards[0]['deadline'];self.n.post('Latest')
        self.assertEqual(self.n.cards[1]['deadline'],deadline)
        self.assertTrue(self.n.toast['decision']);self.n.acceptId(decision);self.assertEqual(calls,['accepted'])
        self.n.acceptId(decision);self.assertEqual(calls,['accepted'])
    def test_critical_persists_and_manual_close_is_immediate(self):
        self.n.post('Critical','critical');identifier=self.n.cards[0]['id']
        with patch('interaction.notifications.time.monotonic',return_value=1e12):self.n.tick()
        self.assertEqual(len(self.n.cards),1);self.n.dismissId(identifier);self.assertFalse(self.n.cards)
    def test_stack_overflow_queues_then_enters_without_losing_history(self):
        for i in range(6):self.n.post(str(i))
        self.assertEqual(len(self.n.cards),4);self.assertEqual(len(self.n.waiting),2)
        self.n.dismissId(self.n.cards[-1]['id'])
        self.assertEqual(self.n.cards[0]['text'],'4');self.assertEqual(len(self.n.history),6)

if __name__=='__main__':unittest.main(verbosity=2)
