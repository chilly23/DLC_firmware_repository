"""Desktop-session startup registration; never start Qt as root."""
import os,shlex,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
BEGIN='# Nexatom start';END='# Nexatom end'

def quote(value):return '"'+str(value).replace('\\','\\\\').replace('"','\\"').replace('`','\\`').replace('$','\\$').replace('%','%%')+'"'
def entry(root=ROOT,automatic=False):
    return '\n'.join(['[Desktop Entry]','Type=Application','Name=Nexatom','Comment=Laser controller interface',
        'Exec=/bin/bash '+quote(root/'start.sh')+(' --autostart' if automatic else ''),
        'Icon='+str(root/'assets/logo.png'),'Terminal=false','Categories=Science;',''])
def enabled(home=None):return ((Path(home) if home else Path.home())/'.config/autostart/nexatom.desktop').is_file()
def configure(on,home=None,root=ROOT):
    if sys.platform!='linux' and home is None:raise OSError('Automatic startup is configured on the Raspberry Pi.')
    home=Path(home) if home else Path.home();xdg=home/'.config/autostart/nexatom.desktop';xdg.parent.mkdir(parents=True,exist_ok=True)
    if on:xdg.write_text(entry(root,True),encoding='utf8')
    else:xdg.unlink(missing_ok=True)
    # Raspberry Pi OS labwc uses this documented session startup hook. Keep
    # existing commands; a process lock prevents duplicate XDG/labwc launches.
    path=home/'.config/labwc/autostart';path.parent.mkdir(parents=True,exist_ok=True)
    # A user autostart supersedes the system file in labwc. Preserve the
    # distribution's desktop/panel commands when creating it for the first time.
    system=Path('/etc/xdg/labwc/autostart')
    old=path.read_text(encoding='utf8') if path.exists() else (system.read_text(encoding='utf8') if system.exists() else '#!/bin/sh\n')
    if BEGIN in old:
        before,after=old.split(BEGIN,1);after=after.split(END,1)[1] if END in after else ''
        old=before+after.lstrip('\n')
    if on:old=old.rstrip()+'\n'+BEGIN+'\n/bin/bash '+shlex.quote(str(root/'start.sh'))+' --autostart &\n'+END+'\n'
    path.write_text(old,encoding='utf8');path.chmod(0o755)
def shortcuts(home=None,root=ROOT):
    home=Path(home) if home else Path.home()
    for folder in (home/'.local/share/applications',home/'Desktop'):
        folder.mkdir(parents=True,exist_ok=True);file=folder/'nexatom.desktop';file.write_text(entry(root),encoding='utf8');file.chmod(0o755)
        if sys.platform=='linux':
            try:subprocess.run(['gio','set',str(file),'metadata::trusted','true'],capture_output=True,check=False)
            except FileNotFoundError:pass
def repair():
    if sys.platform!='linux':raise OSError('Run setup on Raspberry Pi OS Desktop.')
    subprocess.Popen(['/bin/bash',str(ROOT/'start.sh'),'--repair'],start_new_session=True)
if __name__=='__main__':shortcuts();configure(True)
