"""A busy audit database must not stall a knob command on the GUI thread."""
import sqlite3
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from interaction.journal import Journal


class JournalLatencyTests(unittest.TestCase):
    def test_external_write_lock_does_not_block_record(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'events.db';journal=Journal(path)
            other=sqlite3.connect(path);other.execute('BEGIN IMMEDIATE')
            try:
                start=time.monotonic()
                journal.record('Captured input while storage is busy')
                self.assertLess(time.monotonic()-start,.1)
                self.assertEqual(journal.rows()[0]['description'],'Captured input while storage is busy')
            finally:
                other.rollback();other.close();journal.close()
            restored=Journal(path)
            try:self.assertEqual(restored.count(),1)
            finally:restored.close()

if __name__=='__main__':unittest.main()
