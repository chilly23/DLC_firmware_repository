"""Native benchmark controls, isolation and report export."""
import os,sys,tempfile,json
from copy import deepcopy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
os.environ['QT_QUICK_BACKEND']='software'
if sys.platform=='win32':os.environ['QT_QPA_PLATFORM']='windows'
from PySide6.QtCore import QCoreApplication,QEvent
from PySide6.QtTest import QTest
from main import create_application
from benchmark import Benchmark
from verify_v17 import TestDevice

def main():
    tmp=tempfile.TemporaryDirectory();checks=[]
    app,engine,ctl,w=create_application(skip_boot=True,data_dir=tmp.name,device=TestDevice(),gpio_autostart=False)
    saved=deepcopy(ctl.theme.store.values)
    bench=Benchmark(ctl,w)
    def check(name,valid):
        assert valid,name
        checks.append(name);print('PASS '+name)
    try:
        QTest.qWait(100)
        check('Separate benchmark window is visible',bench.isVisible())
        for n in (100,1000,10000):
            bench.slider.setValue(n);QTest.qWait(80)
            check(f'Slider configures {n} points on both lasers',all(len(l.signal.x_values)==n for l in ctl.instrument.lasers))
        bench.full.setChecked(True);check('Optional all-point raster is enabled',ctl.benchmark_full_detail)
        bench.full.setChecked(False);check('Peak-preserving default is restored',not ctl.benchmark_full_detail)
        check('Benchmark point overrides do not change normal preferences',ctl.theme.store.values==saved)
        QTest.qWait(200);bench.collect();path=bench.export();report=json.loads(path.read_text())
        check('Report includes CPU, RSS, frames, UI and graph timings',all(k in report for k in ('rows','ui','graph','gpio')) and report['rows'][-1]['rss_bytes']>0)
        bench.grab().save(str(ROOT/'tests/v117/benchmark.png'))
        (ROOT/'tests/v117/benchmark-ui.json').write_text(json.dumps(dict(passed=len(checks),checks=checks),indent=2))
    finally:
        bench.shutdown();ctl.timer.stop();ctl.parameters.shutdown();ctl.workspace.shutdown();ctl.workspace.diagnostics.shutdown()
        ctl.notifications.timer.stop();ctl.knobs.shutdown();ctl.navigation.shutdown();ctl.session_lock.shutdown()
        ctl.settings_host.shutdown();ctl.system_settings.shutdown();ctl.journal.close();w.hide();engine.deleteLater()
        QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete);tmp.cleanup()

if __name__=='__main__':main()
