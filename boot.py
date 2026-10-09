"""Idempotent boot pin configuration for the supplied RKJXT wiring."""
from pathlib import Path
import os,re,sys
BEGIN='# Nexatom GPIO';END='# Nexatom GPIO end'
BLOCK=BEGIN+'\n[all]\ndtparam=i2c_arm=off\ndtparam=spi=off\nenable_uart=0\n'+END+'\n'
def rewrite(path,transform):
    path=Path(path);old=path.read_text(encoding='utf8');new=transform(old)
    if old==new:return False
    backup=path.with_suffix(path.suffix+'.previous')
    if not backup.exists():backup.write_text(old,encoding='utf8')
    path.write_text(new,encoding='utf8');return True
def configure(folder):
    folder=Path(folder)
    def config(text):
        pattern=re.escape(BEGIN)+r'\n.*?'+re.escape(END)+r'\n?'
        return re.sub(pattern,'',text,flags=re.S).rstrip()+'\n\n'+BLOCK
    changed=rewrite(folder/'config.txt',config)
    cmdline=folder/'cmdline.txt'
    if cmdline.exists():
        changed=rewrite(cmdline,lambda text:' '.join(t for t in text.split() if not re.match(r'console=(serial\d|ttyAMA\d|ttyS\d)(,|$)',t))+'\n') or changed
    return changed
if __name__=='__main__':
    if os.geteuid()!=0:raise SystemExit('Setup helper requires administrator access.')
    folder=Path('/boot/firmware') if Path('/boot/firmware/config.txt').exists() else Path('/boot')
    if not (folder/'config.txt').exists():raise SystemExit('Raspberry Pi boot configuration was not found.')
    changed=configure(folder)
    if changed:(Path(__file__).resolve().parent/'.reboot').write_text('GPIO boot configuration changed. Restart to apply.\n')
