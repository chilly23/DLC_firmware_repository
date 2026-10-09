"""Verify the actual two Windows one-click launchers and their three-second boot."""
import json
import subprocess
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
for name in ('Start Nexatom v1.2.cmd','Start Fullscreen v1.2.cmd'):
    report=ROOT/'tests'/('desktop-fullscreen.json' if 'Fullscreen' in name else 'desktop-window.json')
    if report.exists():report.unlink()
    subprocess.run(f'call "{ROOT/name}" --verify-startup "{report}"',shell=True,cwd=ROOT,check=True)
    deadline=time.monotonic()+30
    while not report.exists() and time.monotonic()<deadline:time.sleep(.2)
    assert report.exists(),f'{name} did not start; see logs/startup.log'
    result=json.loads(report.read_text(encoding='utf8'))
    assert result['visible'] and result['exposed'] and not result['booting'] and result['platform']=='windows',result
    print('PASS',name,result,flush=True)
    time.sleep(.5)
