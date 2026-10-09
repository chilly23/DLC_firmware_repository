"""State, persistence, browsing and notification contracts for the v1.16 Lobby."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from PySide6.QtCore import QCoreApplication
from controller.bridge import Controller
from controller.parameters import ParameterCatalog
from settings_ui.model import SettingsStore
from settings_ui.preferences import Appearance
from interaction.journal import Journal
from interaction.notifications import Notifications
from interaction.workspace import Workspace

APP = QCoreApplication.instance() or QCoreApplication([])


class LobbyContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.data = Path(self.temp.name)
        self.store = SettingsStore(self.data/'settings.json')
        self.theme = Appearance(self.store)
        self.ctl = Controller(animate=False)
        self.ctl.theme = self.theme
        self.ctl.journal = Journal(self.data/'events.db')
        self.ctl.notifications = Notifications(self.data/'notifications.json')
        self.ctl.configure(self.store.values)
        self.catalog = ParameterCatalog(self.ctl, self.store)
        self.ctl.parameters = self.catalog
        self.workspace = Workspace(self.ctl, self.theme)

    def tearDown(self):
        self.workspace.shutdown()
        self.catalog.shutdown()
        self.ctl.notifications.timer.stop()
        self.ctl.journal.close()
        self.temp.cleanup()

    def test_reference_catalogs_and_readonly_values(self):
        cc = self.catalog.controlRows(0, 'CC')
        tc = self.catalog.controlRows(0, 'TC')
        self.assertEqual(len(cc), 8)
        self.assertEqual(len(tc), 8)
        self.assertEqual(next(r for r in cc if r['key']=='umax')['kind'], 'read')
        self.assertEqual(next(r for r in tc if r['key']=='actual_temperature')['kind'], 'read')
        self.assertEqual([r['key'] for r in self.catalog.laserRows(1)], ['maximum_current','current','umax','positive','temperature'])

    def test_limit_rejection_is_transactional_and_shared_with_home(self):
        self.assertEqual(self.ctl.setValue(0, 'current', '250'), '')
        self.assertTrue(self.ctl.setValue(0, 'maximum_current', '200'))
        self.assertEqual(self.ctl.value(0, 'maximum_current'), 300)
        self.assertTrue(self.ctl.setValue(0, 'current', '301'))
        self.assertEqual(self.ctl.value(0, 'current'), 250)
        self.assertTrue(self.ctl.setValue(0, 'temperature', '33'))
        self.assertTrue(self.ctl.setValue(0, 'pid_i', 'nan'))
        self.assertEqual(self.ctl.value(1, 'current'), 229.547)

    def test_lower_limit_setpoint_assignment_and_flags_survive_restart(self):
        self.ctl.setValue(0, 'current', '100')
        self.ctl.setValue(0, 'maximum_current', '150')
        self.ctl.selectField(0, True, 'pid_i')
        self.catalog.toggleControl(0, 'tc_enabled')
        self.catalog.save()
        store = SettingsStore(self.data/'settings.json')
        other = Controller(animate=False)
        catalog = ParameterCatalog(other, store)
        try:
            self.assertEqual(other.value(0, 'current'), 100)
            self.assertEqual(other.value(0, 'maximum_current'), 150)
            self.assertEqual(other.instrument.lasers[0].bottom_field(), 'pid_i')
            self.assertFalse(catalog.flags[0]['tc_enabled'])
        finally:
            catalog.shutdown()

    def test_hierarchy_reaches_shared_editable_module_leaves(self):
        root = self.catalog.treeRows('')
        self.assertIn('laser2', [r['path'] for r in root])
        self.assertIn('laser2/cc', [r['path'] for r in self.catalog.treeRows('laser2')])
        self.ctl.setValue(1, 'current', '180')
        row = next(r for r in self.catalog.treeRows('laser2/cc') if r['key']=='current')
        self.assertEqual(row['value'], '180.000')
        self.assertEqual(self.catalog.treeRows('invalid'), [])

    def test_feedforward_and_temperature_enable_affect_simulation_targets(self):
        self.ctl.startAcquisition()
        self.ctl.setValue(0, 'feedforward', '8')
        self.catalog.toggleControl(0, 'feedforward_enabled')
        self.catalog.toggleControl(0, 'tc_enabled')
        self.ctl.setValue(0, 'temperature', '30')
        self.ctl.step(1)
        self.assertEqual(self.ctl.instrument.lasers[0].signal.live['feedforward'], 0)
        self.assertEqual(self.ctl.instrument.lasers[0].signal.live['temperature'], 24)

    def test_file_categories_preview_and_sort(self):
        self.workspace.browse('recordings')
        self.assertEqual(Path(self.workspace.folder).resolve(), (self.data/'recordings').resolve())
        self.workspace.browse('screenshots')
        self.assertEqual(Path(self.workspace.folder), self.data/'screenshots')
        (self.data/'b.txt').write_text('content')
        (self.data/'a.json').write_text('{"value":1}')
        self.workspace.browse('data')
        self.workspace.sortFiles('Name')
        self.assertEqual([r['name'] for r in self.workspace.files if not r['directory']][:2], ['a.json','b.txt'])
        self.workspace.openFile(str(self.data/'a.json'))
        self.assertEqual(self.workspace.preview['kind'], 'text')
        self.assertEqual(json.loads(self.workspace.preview['text']), {'value':1})
        self.workspace.closePreview()
        self.assertFalse(self.workspace.preview)

    def test_text_preview_is_bounded_and_missing_file_is_reported(self):
        text=self.data/'large.log';text.write_text('x'*300000)
        self.workspace.openFile(str(text))
        self.assertIn('Preview limited', self.workspace.preview['text'])
        self.assertLess(len(self.workspace.preview['text']), 263000)
        self.workspace.openFile(str(self.data/'missing.png'))
        self.assertIn('no longer available', self.workspace.message)

    def test_log_exports_are_in_the_file_manager_export_directory(self):
        self.workspace.exportLogs()
        self.workspace.browse('exports')
        self.assertEqual({r['name'] for r in self.workspace.files}, {'logs.csv','logs.md'})

    def test_four_log_status_colours(self):
        for description,status,level,source in [('failure','Failed','critical','GPIO'),('warn','Failed','warning','GPIO'),('done','Passed','default','Parameter'),('info','Requested','default','System')]:
            self.ctl.journal.record(description,status,level,source)
        self.workspace.refresh_logs()
        self.assertEqual({r['color'] for r in self.workspace.logRows}, {'#FF453A','#FF9F0A','#32D74B','#D9D9D9'})

    def test_duplicates_do_not_restart_notification_timer(self):
        notices=self.ctl.notifications
        with patch('interaction.notifications.time.monotonic',return_value=100):
            notices.post('Saved')
        identifier=notices.cards[0]['id']
        deadline=notices.cards[0]['deadline']
        with patch('interaction.notifications.time.monotonic',return_value=101):
            notices.post('Saved');notices.tick()
        self.assertEqual(len(notices.history),1)
        self.assertEqual(notices.cards[0]['id'],identifier)
        self.assertEqual(notices.cards[0]['deadline'],deadline)
        self.assertTrue(0<notices.cards[0]['remaining']<1)

    def test_critical_and_consent_do_not_expire_or_show_countdown(self):
        n=self.ctl.notifications
        n.post('Attention','critical');n.post('Confirm?',decision=lambda:None)
        self.assertTrue(all(not row['timed'] for row in n.cards))
        with patch('interaction.notifications.time.monotonic',return_value=1e12):n.tick()
        self.assertEqual(len(n.cards),2)

    def test_graph_gestures_are_logged_without_transient_spam(self):
        self.ctl.action_notice('Laser 1 chart panned','graph-gesture-0')
        self.ctl.action_notice('Laser 1 graph locked','graph-lock-0')
        self.assertFalse(self.ctl.notifications.cards)
        self.assertEqual(self.ctl.journal.count(),2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
