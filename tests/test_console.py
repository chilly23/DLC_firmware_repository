"""Persistence, installation and export contracts; never writes host configuration."""
import csv,json,sys,tempfile,unittest,shlex,subprocess
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from interaction.journal import Journal
from boot import configure as boot
from startup import configure,enabled
from install import stage

class Contracts(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def test_journal_survives_restart_filters_and_clears(self):
        path=self.root/'events.db';j=Journal(path)
        j.record('Gain changed');j.record('Rejected limit','Failed','warning');j.record('Driver failed','Failed','critical');j.close()
        j=Journal(path)
        try:
            self.assertEqual(j.count(),3);self.assertEqual(j.rows('warning')[0]['status'],'Failed')
            self.assertIn('+',j.rows()[0]['timestamp'][19:])
            j.clear();self.assertEqual(j.count(),1);self.assertEqual(j.rows()[0]['description'],'User logs cleared')
        finally:j.close()
    def test_journal_bounded_and_csv_safe(self):
        j=Journal(self.root/'events.db');j.LIMIT=5
        try:
            for n in range(9):j.record(str(n))
            self.assertEqual([x['description'] for x in j.rows()],['8','7','6','5','4'])
            j.record('=HYPERLINK("unsafe")','Failed','warning');paths=j.export(self.root/'exports')
            with paths[0].open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
            self.assertEqual(len(rows),5);self.assertTrue(rows[-1]['description'].startswith("'="))
            self.assertIn('Failed / warning',paths[1].read_text(encoding='utf8'))
        finally:j.close()
    def test_boot_changes_are_idempotent_and_backed_up(self):
        config=self.root/'config.txt';line=self.root/'cmdline.txt'
        original='[all]\ndtparam=audio=on\ndtparam=i2c_arm=on\n';config.write_text(original)
        line.write_text('console=serial0,115200 console=tty1 root=PARTUUID=demo quiet\n')
        self.assertTrue(boot(self.root));self.assertFalse(boot(self.root))
        self.assertEqual(config.with_suffix('.txt.previous').read_text(),original)
        self.assertIn('dtparam=audio=on',config.read_text());self.assertIn('dtparam=i2c_arm=off',config.read_text())
        self.assertEqual(line.read_text(),'console=tty1 root=PARTUUID=demo quiet\n')
    def test_startup_preserves_other_commands_and_can_disable(self):
        file=self.root/'.config/labwc/autostart';file.parent.mkdir(parents=True);file.write_text('#!/bin/sh\npanel &\n')
        target=self.root/'space dir';configure(True,self.root,target);configure(True,self.root,target)
        self.assertTrue(enabled(self.root));self.assertEqual(file.read_text().count('# Nexatom start'),1)
        self.assertIn('panel &',file.read_text())
        command=next(line[5:] for line in (self.root/'.config/autostart/nexatom.desktop').read_text().splitlines() if line.startswith('Exec='))
        self.assertEqual(shlex.split(command)[1],str(target/'start.sh'))
        configure(False,self.root,target);self.assertFalse(enabled(self.root));self.assertIn('panel &',file.read_text());self.assertNotIn('start.sh',file.read_text())
    def test_upgrade_keeps_calibration_and_user_settings(self):
        source=self.root/'usb';home=self.root/'home';source.mkdir();(source/'data').mkdir()
        (source/'data/controls.json').write_text('{"knobs":[]}');(source/'main.py').write_text('# new code')
        target=home/'nexatom';(target/'data').mkdir(parents=True)
        (target/'data/controls.json').write_text('{"calibration":"saved"}');(target/'data/settings.json').write_text('{"accent":"Pink"}')
        stage(source,home)
        self.assertEqual(json.loads((target/'data/controls.json').read_text()),{'calibration':'saved'})
        self.assertEqual(json.loads((target/'data/settings.json').read_text()),{'accent':'Pink'})
        self.assertEqual((target/'main.py').read_text(),'# new code')
    def test_unhandled_error_is_written_to_text_report(self):
        program='import sys; from interaction.faults import install; install(sys.argv[1]); raise RuntimeError("recorded failure for verification")'
        result=subprocess.run([sys.executable,'-c',program,str(self.root)],cwd=ROOT,capture_output=True)
        self.assertNotEqual(result.returncode,0)
        report=(self.root/'errors.txt').read_text(encoding='utf8')
        self.assertIn('recorded failure for verification',report);self.assertIn('Traceback',report);self.assertIn('Python',report)

if __name__=='__main__':unittest.main()
