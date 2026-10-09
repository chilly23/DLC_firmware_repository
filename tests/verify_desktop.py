"""Launch both actual Windows shortcuts and verify boot plus live acquisition."""
import json
import subprocess
import time
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
for name in ('start.cmd',):
    report=ROOT/'tests'/('desktop-fullscreen.json' if 'Fullscreen' in name else 'desktop-window.json')
    if report.exists():report.unlink()
    isolated=tempfile.TemporaryDirectory()
    subprocess.run(f'call "{ROOT/name}" --data-dir "{isolated.name}" --verify-startup "{report}"',shell=True,cwd=ROOT,check=True)
    deadline=time.monotonic()+30
    while not report.exists() and time.monotonic()<deadline:time.sleep(.2)
    assert report.exists(),f'{name} did not start; see logs/startup.txt'
    result=json.loads(report.read_text(encoding='utf8'))
    assert result['visible'] and result['exposed'] and not result['booting'] and result['platform']=='windows',result
    assert result['fullscreen'],result
    assert result['acquiring'] and result['timer_active'] and result['elapsed']>0,result
    assert all(0<level<=1 for level in result['signal_levels']),result
    print('PASS',name,result,flush=True)
    time.sleep(.5)
    isolated.cleanup()
