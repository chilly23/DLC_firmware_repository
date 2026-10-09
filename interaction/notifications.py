"""Shared compact notifications, bounded history and explicit decision callbacks."""
import json,time
from pathlib import Path
from PySide6.QtCore import QObject,Property,Signal,Slot,QTimer

class Notifications(QObject):
    changed=Signal()
    def __init__(self,path,parent=None):
        super().__init__(parent);self.path=Path(path);self.entries=[];self.current={};self.pending={};self.deadline=0;self.serial=0
        try:self.entries=json.loads(self.path.read_text(encoding='utf8'))[-200:]
        except (OSError,ValueError,TypeError):pass
        self.timer=QTimer(self);self.timer.setInterval(150);self.timer.timeout.connect(self.tick);self.timer.start()
    @Property('QVariantMap',notify=changed)
    def toast(self):return self.current or dict(id=0,text='',level='normal',decision=False)
    @Property('QVariantList',notify=changed)
    def history(self):return list(reversed(self.entries))
    def save(self):
        try:
            self.path.parent.mkdir(parents=True,exist_ok=True);temp=self.path.with_suffix('.tmp')
            temp.write_text(json.dumps(self.entries,indent=2)+'\n',encoding='utf8');temp.replace(self.path)
        except OSError:pass
    def post(self,text,level='normal',key='',decision=None):
        if not text:return
        if level not in ('normal','warning','critical'):level='normal'
        key=key or text;now=time.time()
        self.serial+=1;entry=dict(id=self.serial,text=str(text),level=level,time=now,key=key,decision=decision is not None)
        if self.entries and self.entries[-1]['key']==key and self.entries[-1]['text']==text and now-self.entries[-1]['time']<2:self.entries[-1]=entry
        else:self.entries.append(entry);self.entries=self.entries[-200:]
        self.save()
        # A routine action cannot cover a request for consent or a critical fault.
        if self.current and (self.current['decision'] or self.current['level']=='critical') and level=='normal' and decision is None:
            self.changed.emit();return
        if self.current:self.pending.pop(self.current['id'],None)
        self.current=entry
        if decision:self.pending[entry['id']]=decision
        self.deadline=0 if decision or level=='critical' else time.monotonic()+(6 if level=='warning' else 3.2)
        self.changed.emit()
    @Slot()
    def dismiss(self):
        if self.current:self.pending.pop(self.current['id'],None)
        self.current={};self.deadline=0;self.changed.emit()
    @Slot()
    def accept(self):
        if not self.current:return
        callback=self.pending.pop(self.current['id'],None);self.dismiss()
        if callback:callback()
    @Slot()
    def clear(self):self.entries=[];self.save();self.changed.emit()
    def tick(self):
        if self.deadline and time.monotonic()>=self.deadline:self.dismiss()
