"""Existing on-device configuration upgrades without losing Knob 1/2 settings."""
import sys,json,tempfile,unittest
from pathlib import Path
from copy import deepcopy
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from hardware.config import DEFAULTS,ControlStore,validate

class WiringMigrationTests(unittest.TestCase):
    def test_stock_left_shortcut_moves_to_gpio16_and_stays_migrated(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'controls.json';old=deepcopy(DEFAULTS);old['wiring_revision']=2
            old['panel']['left_shortcut'].update(pin=8,enabled=False,calibrated=False)
            old['knobs'][0]['calibrated']=True;path.write_text(json.dumps(old))
            store=ControlStore(path);self.assertFalse(store.error)
            self.assertEqual(store.config['knobs'],old['knobs'])
            self.assertEqual(store.config['panel']['right_shortcut']['pin'],7)
            left=store.config['panel']['left_shortcut']
            self.assertEqual(left['pin'],16);self.assertTrue(left['enabled']);self.assertTrue(left['calibrated'])
            self.assertEqual(left['active_level'],0)
            self.assertEqual(store.config,ControlStore(path).config)
    def test_custom_panel_assignment_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'controls.json';old=deepcopy(DEFAULTS);old['wiring_revision']=2
            old['panel']['left_shortcut'].update(pin=11,enabled=False,active_level=1)
            path.write_text(json.dumps(old));store=ControlStore(path)
            self.assertFalse(store.error);self.assertEqual(store.config['panel'],old['panel'])
    def old_config(self):
        cfg=deepcopy(DEFAULTS);cfg.pop('wiring_revision')
        cfg['knobs'][2]['pins']=cfg['knobs'][3]['pins'];cfg['knobs'][2]['enabled']=True;cfg['knobs'][2]['calibrated']=True
        cfg['knobs'][3]['pins']={};cfg['knobs'][3]['enabled']=False
        cfg['knobs'][0]['calibrated']=True;cfg['knobs'][0]['directions'].update(left='D',right='B')
        cfg['knobs'][1]['mapping']['push']='settings.open'
        return validate(cfg)
    def test_migration_is_persistent_idempotent_and_preserves_other_knobs(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'controls.json';old=self.old_config();path.write_text(json.dumps(old))
            store=ControlStore(path);self.assertFalse(store.error);new=store.config
            self.assertEqual(old['knobs'][:2],new['knobs'][:2])
            self.assertFalse(new['knobs'][2]['enabled']);self.assertEqual(new['knobs'][2]['pins'],{})
            fourth=new['knobs'][3];self.assertTrue(fourth['enabled']);self.assertFalse(fourth['calibrated'])
            self.assertEqual(fourth['pins'],old['knobs'][2]['pins']);self.assertEqual(fourth['target'],3)
            self.assertEqual(fourth['name'],'Knob 4');self.assertEqual(fourth['location'],'Bottom right')
            self.assertEqual(new,ControlStore(path).config);self.assertEqual(json.loads(path.read_text()),new)
    def test_custom_wiring_is_not_silently_reassigned(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'controls.json';old=self.old_config()
            p=old['knobs'][2]['pins'];p['A'],p['B']=p['B'],p['A'];path.write_text(json.dumps(old))
            self.assertEqual(ControlStore(path).config['knobs'],old['knobs'])
if __name__=='__main__':unittest.main(verbosity=2)
