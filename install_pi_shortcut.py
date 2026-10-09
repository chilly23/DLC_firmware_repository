"""Create a desktop/app-menu launcher at this folder's real path; no autostart."""
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parent

def quote(value):
    # Desktop Entry Exec quoting, separate from shell quoting.
    return '"'+str(value).replace('\\','\\\\').replace('"','\\"').replace('`','\\`').replace('$','\\$').replace('%','%%')+'"'

def install():
    content='\n'.join(['[Desktop Entry]','Version=1.0','Type=Application','Name=Nexatom v1.9',
        'Comment=Dual laser HMI with calibrated RKJXT inputs','Exec=/bin/bash '+quote(ROOT/'run.sh'),
        'Icon='+str(ROOT/'assets/logo.png'),'Terminal=false','Categories=Science;Education;',''])
    menu=Path.home()/'.local/share/applications';menu.mkdir(parents=True,exist_ok=True)
    locations=[menu]
    try:
        desktop=Path(subprocess.check_output(['xdg-user-dir','DESKTOP'],text=True).strip())
        if desktop.is_dir():locations.append(desktop)
    except (OSError,subprocess.SubprocessError):pass
    for folder in locations:
        path=folder/'nexatom-v18.desktop';path.write_text(content,encoding='utf8');path.chmod(0o755)
        try:subprocess.run(['gio','set',str(path),'metadata::trusted','true'],capture_output=True,timeout=3)
        except (OSError,subprocess.SubprocessError):pass
if __name__=='__main__':install()
