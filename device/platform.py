"""One interface for host display, clock and power operations.

All methods are blocking and run on the settings worker, never the Qt UI thread.
No command uses a shell or elevates privileges automatically.
"""
import datetime
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess


class DeviceError(RuntimeError):
    pass


def command(args, timeout=12):
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout,
                            creationflags=0x08000000 if os.name == 'nt' else 0)
    if result.returncode:
        raise DeviceError((result.stderr or result.stdout or f'Command failed ({result.returncode})').strip()[:350])
    return result.stdout.strip()


class LinuxDevice:
    def __init__(self, backlight_root='/sys/class/backlight', runner=command):
        self.root = Path(backlight_root)
        self.run = runner
        self.output = None
        self.backend = None
        self.ddc_display = None
        self.backlight = None

    def probe(self):
        self.backend=None;self.output=None;self.ddc_display=None
        result = dict(platform=platform.platform(), target='Primary active display', modes=[], current=None,
                      brightness=None, contrast=None, reasons={})
        self.backlight = next((p for p in sorted(self.root.glob('*')) if (p/'max_brightness').exists()), None)
        if self.backlight:
            try:
                maximum = int((self.backlight/'max_brightness').read_text())
                result['brightness'] = round(int((self.backlight/'brightness').read_text())/max(1,maximum)*100)
                result['target'] = self.backlight.name
            except (OSError,ValueError) as exc:
                result['reasons']['brightness']=str(exc);self.backlight=None
        if shutil.which('ddcutil'):
            try:
                found = self.run(['ddcutil','detect','--brief'])
                match = re.search(r'Display\s+(\d+)',found)
                if match:self.ddc_display=match[1]
            except (DeviceError,subprocess.TimeoutExpired) as exc:
                result['reasons']['contrast']=str(exc)
            for key,code in [('brightness','10'),('contrast','12')]:
                if result[key] is None and self.ddc_display is not None:
                    try:result[key]=self.read_ddc(code)
                    except (DeviceError,subprocess.TimeoutExpired) as exc:result['reasons'][key]=str(exc)
            if self.ddc_display:result['target']+=' / DDC display '+self.ddc_display
        for key in ('brightness','contrast'):
            if result[key] is None:
                fallback=('ddcutil is missing. Run the v1.12 Pi setup to install DDC/I2C support.' if not shutil.which('ddcutil') else
                          'No accessible DDC display was detected. Check i2c-dev, I2C permissions and the monitor DDC/CI setting.' if self.ddc_display is None else
                          'The detected monitor did not report this control. Use Retry display after reconnecting it.')
                result['reasons'].setdefault(key,fallback)
        try:
            if os.environ.get('WAYLAND_DISPLAY') and shutil.which('wlr-randr'):
                outputs=json.loads(self.run(['wlr-randr','--json']))
                output=next(o for o in outputs if o.get('enabled') and o.get('modes'))
                self.backend='wlr';self.output=output['name']
                for m in output['modes']:
                    mode=[int(m['width']),int(m['height']),round(float(m['refresh'])/1000,3)]
                    result['modes'].append(mode)
                    if m.get('current'):result['current']=mode
            elif os.environ.get('DISPLAY') and not os.environ.get('WAYLAND_DISPLAY') and shutil.which('xrandr'):
                lines=self.run(['xrandr','--query']).splitlines()
                outputs=[];current=None
                for line in lines:
                    m=re.match(r'^(\S+) connected(?: (primary))? (\d+)x(\d+)\+',line)
                    if m:
                        current={'name':m[1],'primary':bool(m[2]),'modes':[]};outputs.append(current)
                    elif line and not line.startswith(' '):current=None
                    elif current:
                        m=re.match(r'\s+(\d+)x(\d+)\s+(.+)',line)
                        if m:
                            for rate in m[3].split():
                                try:hz=float(rate.rstrip('*+'))
                                except ValueError:continue
                                mode=[int(m[1]),int(m[2]),hz];current['modes'].append(mode)
                                if '*' in rate:current['current']=mode
                output=next((o for o in outputs if o['primary']),outputs[0] if outputs else None)
                if output:
                    self.backend='xrandr';self.output=output['name'];result.update(modes=output['modes'],current=output.get('current'))
            if self.output:result['target'] += ' / '+self.output
        except (DeviceError,ValueError,KeyError,StopIteration,subprocess.TimeoutExpired) as exc:
            result['reasons']['mode']=str(exc)
        if not result['modes']:
            result['reasons'].setdefault('mode','This compositor does not expose runtime output configuration. Weston requires image-specific output management; no mode is faked.')
        return result

    def read_ddc(self, code):
        raw=self.run(['ddcutil','--display',self.ddc_display,'getvcp',code,'--terse'])
        match=re.search(r'VCP\s+\S+\s+C\s+(\d+)\s+(\d+)',raw)
        if not match:raise DeviceError('Monitor did not report a continuous DDC control.')
        return round(int(match[1])/max(1,int(match[2]))*100)

    def set_level(self,key,value):
        value=max(1,min(100,int(value)))
        if key=='brightness' and self.backlight:
            maximum=int((self.backlight/'max_brightness').read_text())
            try:(self.backlight/'brightness').write_text(str(max(1,round(value*maximum/100))))
            except PermissionError:raise DeviceError('Backlight write denied. Grant the device user access to this backlight in the image.')
            return round(int((self.backlight/'brightness').read_text())/maximum*100)
        if not self.ddc_display:raise DeviceError('No hardware control available for '+key)
        code='10' if key=='brightness' else '12'
        raw=self.run(['ddcutil','--display',self.ddc_display,'getvcp',code,'--terse'])
        match=re.search(r'VCP\s+\S+\s+C\s+(\d+)\s+(\d+)',raw)
        if not match:raise DeviceError('DDC readback unavailable')
        self.run(['ddcutil','--display',self.ddc_display,'setvcp',code,str(round(int(match[2])*value/100))])
        return self.read_ddc(code)

    def set_mode(self,mode):
        w,h,hz=mode
        if self.backend=='wlr':self.run(['wlr-randr','--output',self.output,'--mode',f'{w}x{h}@{hz:g}Hz'])
        elif self.backend=='xrandr':self.run(['xrandr','--output',self.output,'--mode',f'{w}x{h}','--rate',str(hz)])
        else:raise DeviceError('Runtime resolution changes are not supported by this compositor.')
        actual=self.probe().get('current')
        if not actual or actual[:2]!=list(mode[:2]) or abs(actual[2]-hz)>.2:raise DeviceError('Display did not confirm the requested mode.')
        return actual

    def set_time(self,iso):
        value=datetime.datetime.fromisoformat(iso)
        if not shutil.which('timedatectl'):raise DeviceError('timedatectl is not available in this image.')
        self.run(['timedatectl','set-time',value.strftime('%Y-%m-%d %H:%M:%S')])
        return datetime.datetime.now().isoformat(timespec='seconds')

    def power(self,action):
        if action not in ('sleep','shutdown'):raise DeviceError('Unknown power action')
        self.run(['systemctl','suspend' if action=='sleep' else 'poweroff'])
        return action


def make_device():
    if os.name=='nt':
        from .windows import WindowsDevice
        return WindowsDevice()
    return LinuxDevice()
