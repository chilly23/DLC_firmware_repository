"""Stage a USB/download copy into the desktop user's writable home directory."""
from pathlib import Path
import json,shutil
ROOT=Path(__file__).resolve().parent
OMIT={'runtime','packages','tests','logs','exports','previews','__pycache__','.venv','.git'}
def stage(source=ROOT,home=None):
    source=Path(source).resolve();home=Path(home) if home else Path.home();target=home/'nexatom'
    if source==target.resolve():return target
    target.mkdir(parents=True,exist_ok=True);had_data=(target/'data/controls.json').exists()
    for item in source.iterdir():
        if item.name in OMIT or item.name.startswith('.') or (item.name=='data' and had_data):continue
        dest=target/item.name
        if item.is_dir():shutil.copytree(item,dest,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        else:shutil.copy2(item,dest)
    if not had_data:
        previous=[home/'mock1.8-pyside6/data',home/'Nexatom/Versions/mock1.8-pyside6/data',home/'Nexatom/mock1.8-pyside6/data']
        for candidate in previous:
            try:
                controls=json.loads((candidate/'controls.json').read_text(encoding='utf8'))
                if not any(k.get('calibrated') for k in controls.get('knobs',[])):continue
                for name in ('controls.json','settings.json','notifications.json'):
                    if (candidate/name).exists():shutil.copy2(candidate/name,target/'data'/name)
                break
            except (OSError,ValueError,AttributeError):continue
    return target
if __name__=='__main__':print(stage())
