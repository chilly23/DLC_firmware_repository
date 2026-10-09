"""Contract checks for Linux interfaces using isolated sysfs and command fixtures."""
import os,sys,tempfile,json
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from device.platform import LinuxDevice,DeviceError
checks=[]
def check(name,ok):
    assert ok,name
    checks.append(name);print('PASS',name)
with tempfile.TemporaryDirectory() as temp:
    panel=Path(temp)/'panel';panel.mkdir();(panel/'max_brightness').write_text('255');(panel/'brightness').write_text('128')
    with patch('device.platform.shutil.which',return_value=None),patch.dict(os.environ,{},clear=True):
        d=LinuxDevice(temp);caps=d.probe()
        check('Sysfs backlight detected and normalized',caps['brightness']==50)
        check('Sysfs writes actual driver value with readback',d.set_level('brightness',80)==80 and (panel/'brightness').read_text()=='204')
        check('Unsupported contrast is explicit',caps['contrast'] is None and 'contrast' in caps['reasons'])
        check('Weston without output protocol has no invented modes',caps['modes']==[] and 'Weston' in caps['reasons']['mode'])
        try:d.set_mode([1600,720,60]);raise AssertionError('Expected refusal')
        except DeviceError:checks.append('Unsupported mode refuses host write')
    calls=[];state={'mode':[1600,720,60.], 'contrast':40}
    def runner(args):
        calls.append(args)
        if args[:2]==['ddcutil','detect']:return 'Display 1\nI2C bus: /dev/i2c-1'
        if args[0]=='ddcutil':
            if args[3]=='getvcp':
                if args[4]=='10':raise DeviceError('Brightness unsupported')
                return f'VCP 12 C {state["contrast"]} 100'
            state['contrast']=int(args[5]);return ''
        if args==['wlr-randr','--json']:
            w,h,r=state['mode'];return json.dumps([{'name':'DSI-1','enabled':True,'modes':[{'width':w,'height':h,'refresh':r*1000,'current':True}]}])
        if args[0]=='wlr-randr':state['mode']=[1920,1080,75.];return ''
        if args[0] in ('timedatectl','systemctl'):return ''
        raise AssertionError(args)
    with patch('device.platform.shutil.which',side_effect=lambda name:name),patch.dict(os.environ,{'WAYLAND_DISPLAY':'wayland-0'},clear=True):
        d=LinuxDevice(Path(temp)/'absent',runner);caps=d.probe()
        check('One unsupported DDC control does not hide the other',caps['brightness'] is None and caps['contrast']==40)
        check('DDC contrast writes and reads back',d.set_level('contrast',65)==65 and state['contrast']==65)
        check('Wayland modes convert millihertz to hertz',caps['current']==[1600,720,60.])
        check('Wayland mode writes output and verifies readback',d.set_mode([1920,1080,75])==[1920,1080,75.])
        d.set_time('2026-09-25 12:30:00');d.power('sleep')
        check('Clock and power use argument arrays',calls[-2:]==[['timedatectl','set-time','2026-09-25 12:30:00'],['systemctl','suspend']])
    def xrunner(args):
        calls.append(args)
        if args==['xrandr','--query']:return 'HDMI-1 connected primary 1600x720+0+0\n   1600x720 60.00*+ 50.00\n   1920x1080 60.00\n'
        return ''
    with patch('device.platform.shutil.which',side_effect=lambda name:name if name=='xrandr' else None),patch.dict(os.environ,{'DISPLAY':':0'},clear=True):
        d=LinuxDevice(Path(temp)/'absent',xrunner);caps=d.probe()
        check('X11 parses current primary mode and alternatives',caps['current']==[1600,720,60.] and len(caps['modes'])==3)
        d.set_mode([1600,720,60]);check('X11 mode write targets detected output',['xrandr','--output','HDMI-1','--mode','1600x720','--rate','60'] in calls)
(ROOT/'tests/v17-linux-contracts.json').write_text(json.dumps(checks,indent=2),encoding='utf8')
print(len(checks),'checks passed; no physical Linux hardware was accessed')
