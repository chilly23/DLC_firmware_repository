"""Windows primary-display control through Win32, DXVA2 and WMI."""
import ctypes as C
from ctypes import wintypes as W
import datetime
import json
import platform
from .platform import command, DeviceError


class DEVMODE(C.Structure):
    _fields_=[('dmDeviceName',W.WCHAR*32),('dmSpecVersion',W.WORD),('dmDriverVersion',W.WORD),
              ('dmSize',W.WORD),('dmDriverExtra',W.WORD),('dmFields',W.DWORD),
              ('dmPositionX',W.LONG),('dmPositionY',W.LONG),('dmDisplayOrientation',W.DWORD),('dmDisplayFixedOutput',W.DWORD),
              ('dmColor',W.SHORT),('dmDuplex',W.SHORT),('dmYResolution',W.SHORT),('dmTTOption',W.SHORT),('dmCollate',W.SHORT),
              ('dmFormName',W.WCHAR*32),('dmLogPixels',W.WORD),('dmBitsPerPel',W.DWORD),('dmPelsWidth',W.DWORD),
              ('dmPelsHeight',W.DWORD),('dmDisplayFlags',W.DWORD),('dmDisplayFrequency',W.DWORD),
              ('dmICMMethod',W.DWORD),('dmICMIntent',W.DWORD),('dmMediaType',W.DWORD),('dmDitherType',W.DWORD),
              ('dmReserved1',W.DWORD),('dmReserved2',W.DWORD),('dmPanningWidth',W.DWORD),('dmPanningHeight',W.DWORD)]


class PHYSICAL(C.Structure):
    _fields_=[('handle',W.HANDLE),('description',W.WCHAR*128)]


class WindowsDevice:
    def __init__(self):
        self.user=C.WinDLL('user32',use_last_error=True);self.dx=C.WinDLL('dxva2',use_last_error=True)
        self.user.MonitorFromPoint.argtypes=[W.POINT,W.DWORD];self.user.MonitorFromPoint.restype=W.HANDLE
        self.user.EnumDisplaySettingsW.argtypes=[W.LPCWSTR,W.DWORD,C.POINTER(DEVMODE)];self.user.EnumDisplaySettingsW.restype=W.BOOL
        self.user.ChangeDisplaySettingsExW.argtypes=[W.LPCWSTR,C.POINTER(DEVMODE),W.HWND,W.DWORD,C.c_void_p];self.user.ChangeDisplaySettingsExW.restype=W.LONG
        self.dx.GetNumberOfPhysicalMonitorsFromHMONITOR.argtypes=[W.HANDLE,C.POINTER(W.DWORD)]
        self.dx.GetPhysicalMonitorsFromHMONITOR.argtypes=[W.HANDLE,W.DWORD,C.POINTER(PHYSICAL)]
        self.dx.DestroyPhysicalMonitors.argtypes=[W.DWORD,C.POINTER(PHYSICAL)]
        for key in ('Brightness','Contrast'):
            getattr(self.dx,'GetMonitor'+key).argtypes=[W.HANDLE,C.POINTER(W.DWORD),C.POINTER(W.DWORD),C.POINTER(W.DWORD)]
            getattr(self.dx,'SetMonitor'+key).argtypes=[W.HANDLE,W.DWORD]
        self.level_backends={}

    def physical(self,callback):
        monitor=self.user.MonitorFromPoint(W.POINT(0,0),1);count=W.DWORD()
        if not self.dx.GetNumberOfPhysicalMonitorsFromHMONITOR(monitor,C.byref(count)) or not count.value:
            raise DeviceError('No physical monitor control handle available.')
        monitors=(PHYSICAL*count.value)()
        if not self.dx.GetPhysicalMonitorsFromHMONITOR(monitor,count,monitors):raise DeviceError('Physical monitor enumeration failed.')
        try:return callback(monitors[0].handle)
        finally:self.dx.DestroyPhysicalMonitors(count,monitors)

    def level(self,key,value=None):
        def operation(handle):
            lo,current,hi=W.DWORD(),W.DWORD(),W.DWORD()
            get=getattr(self.dx,'GetMonitor'+key.title());put=getattr(self.dx,'SetMonitor'+key.title())
            if not get(handle,C.byref(lo),C.byref(current),C.byref(hi)):raise DeviceError('Monitor does not expose '+key+' through DDC/CI.')
            if value is not None:
                target=lo.value+round((hi.value-lo.value)*value/100)
                if not put(handle,target):raise DeviceError('Monitor rejected '+key+' command.')
                if not get(handle,C.byref(lo),C.byref(current),C.byref(hi)):raise DeviceError('Monitor readback failed.')
            return round((current.value-lo.value)/max(1,hi.value-lo.value)*100)
        return self.physical(operation)

    def ps(self,script):
        return command(['powershell.exe','-NoProfile','-NonInteractive','-Command',"$ErrorActionPreference='Stop'; "+script],20)

    def mode(self,index):
        m=DEVMODE();m.dmSize=C.sizeof(m)
        return m if self.user.EnumDisplaySettingsW(None,index,C.byref(m)) else None

    def probe(self):
        self.level_backends.clear()
        result=dict(platform=platform.platform(),target='Windows primary display',modes=[],current=None,brightness=None,contrast=None,reasons={})
        for key in ('brightness','contrast'):
            try:result[key]=self.level(key);self.level_backends[key]='ddc'
            except DeviceError as exc:result['reasons'][key]=str(exc)
        if result['brightness'] is None:
            try:
                raw=self.ps("Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightness | Where-Object Active | Select-Object -First 1 -ExpandProperty CurrentBrightness")
                result['brightness']=int(raw);self.level_backends['brightness']='wmi';result['reasons'].pop('brightness',None)
                result['target']='Windows internal panel brightness / primary display modes'
            except Exception:pass
        current=self.mode(0xFFFFFFFF)
        if current:result['current']=[current.dmPelsWidth,current.dmPelsHeight,current.dmDisplayFrequency]
        index=0
        while True:
            mode=self.mode(index)
            if mode is None:break
            value=[mode.dmPelsWidth,mode.dmPelsHeight,mode.dmDisplayFrequency]
            if mode.dmBitsPerPel==32 and value not in result['modes'] and value[0]>=800 and value[1]>=360:result['modes'].append(value)
            index+=1
        return result

    def set_level(self,key,value):
        value=max(1,min(100,int(value)))
        if self.level_backends.get(key)=='wmi':
            self.ps("$m=Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightnessMethods | Where-Object Active | Select-Object -First 1; if(!$m){throw 'No active WMI backlight'}; $r=Invoke-CimMethod -InputObject $m -MethodName WmiSetBrightness -Arguments @{Timeout=[uint32]0;Brightness=[byte]"+str(value)+"}; if($null -ne $r.ReturnValue -and $r.ReturnValue -ne 0){throw 'Brightness request rejected'}")
            return int(self.ps("Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightness | Where-Object Active | Select-Object -First 1 -ExpandProperty CurrentBrightness"))
        return self.level(key,value)

    def set_mode(self,value):
        current=self.mode(0xFFFFFFFF)
        if current is None:raise DeviceError('Current display mode unavailable.')
        current.dmPelsWidth,current.dmPelsHeight,current.dmDisplayFrequency=map(int,value)
        current.dmFields=0x00080000|0x00100000|0x00400000
        status=self.user.ChangeDisplaySettingsExW(None,C.byref(current),None,2,None)
        if status!=0:raise DeviceError(f'Display mode test failed ({status}).')
        status=self.user.ChangeDisplaySettingsExW(None,C.byref(current),None,0,None)
        if status!=0:raise DeviceError(f'Display mode change failed ({status}).')
        readback=self.mode(0xFFFFFFFF)
        actual=[readback.dmPelsWidth,readback.dmPelsHeight,readback.dmDisplayFrequency]
        if actual!=list(map(int,value)):raise DeviceError('Requested display mode was not confirmed.')
        return actual

    def set_time(self,iso):
        dt=datetime.datetime.fromisoformat(iso)
        class SYSTEMTIME(C.Structure):
            _fields_=[(name,W.WORD) for name in ('year','month','dayOfWeek','day','hour','minute','second','millisecond')]
        value=SYSTEMTIME(dt.year,dt.month,0,dt.day,dt.hour,dt.minute,dt.second,0)
        kernel=C.WinDLL('kernel32',use_last_error=True)
        if not kernel.SetLocalTime(C.byref(value)):raise DeviceError('Windows denied clock update. This operation requires system-time permission.')
        return datetime.datetime.now().isoformat(timespec='seconds')

    def power(self,action):
        if action=='shutdown':command(['shutdown.exe','/s','/t','0'])
        elif action=='sleep':
            power=C.WinDLL('powrprof',use_last_error=True)
            power.SetSuspendState.argtypes=[W.BOOLEAN,W.BOOLEAN,W.BOOLEAN]
            if not power.SetSuspendState(False,False,False):raise DeviceError('Windows denied sleep request.')
        else:raise DeviceError('Unknown power action')
        return action
