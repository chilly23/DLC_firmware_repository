"""Independent notification lifetimes, a newest-first stack, and persisted history."""
import json,time
from pathlib import Path
from PySide6.QtCore import QObject,Property,Signal,Slot,QTimer,QAbstractListModel,QModelIndex,Qt

class CardModel(QAbstractListModel):
    FIELDS=('noticeId','text','level','decision','alpha','blurStep','revision')
    def __init__(self,parent):super().__init__(parent);self.rows=[]
    def roleNames(self):return {Qt.UserRole+i+1:key.encode() for i,key in enumerate(self.FIELDS)}
    def rowCount(self,parent=QModelIndex()):return 0 if parent.isValid() else len(self.rows)
    def data(self,index,role):
        n=role-Qt.UserRole-1
        if not index.isValid() or not 0<=index.row()<len(self.rows) or not 0<=n<len(self.FIELDS):return None
        return self.rows[index.row()].get(self.FIELDS[n])
    def insert(self,entry):
        self.beginInsertRows(QModelIndex(),0,0);self.rows.insert(0,entry);self.endInsertRows()
    def remove(self,index):
        self.beginRemoveRows(QModelIndex(),index,index);entry=self.rows.pop(index);self.endRemoveRows();return entry
    def refresh(self,index):self.dataChanged.emit(self.index(index),self.index(index),list(self.roleNames()))
    def promote(self,index):
        if index:
            self.beginMoveRows(QModelIndex(),index,index,QModelIndex(),0)
            self.rows.insert(0,self.rows.pop(index));self.endMoveRows()
        self.refresh(0)

class Notifications(QObject):
    changed=Signal()
    MAX_CARDS=4
    FADE_SECONDS=.65
    def __init__(self,path,parent=None):
        super().__init__(parent);self.path=Path(path);self.entries=[];self.pending={};self.serial=0
        self._model=CardModel(self);self.waiting=[];self.renderer=None
        try:
            loaded=json.loads(self.path.read_text(encoding='utf8'))
            self.entries=[e for e in loaded if isinstance(e,dict) and all(k in e for k in ('id','text','level','time','key'))][-200:]
            self.serial=max((e['id'] for e in self.entries),default=0)
        except (OSError,ValueError,TypeError):pass
        self.timer=QTimer(self);self.timer.setInterval(16);self.timer.timeout.connect(self.tick);self.timer.start()
    @Property(QObject,constant=True)
    def model(self):return self._model
    @property
    def cards(self):return self._model.rows
    @Property('QVariantMap',notify=changed)
    def toast(self):
        # Legacy callers/knob Back address the current consent first. Visual order
        # is always newest first and does not depend on this convenience property.
        return next((e for e in self.cards if e['decision']),self.cards[0] if self.cards else dict(id=0,text='',level='normal',decision=False))
    @Property('QVariantList',notify=changed)
    def history(self):return list(reversed(self.entries))
    def find(self,identifier):return next((e for e in self.cards if e['id']==identifier),None)
    def save(self):
        try:
            self.path.parent.mkdir(parents=True,exist_ok=True);temp=self.path.with_suffix('.tmp')
            temp.write_text(json.dumps(self.entries,indent=2)+'\n',encoding='utf8');temp.replace(self.path)
        except OSError:pass
    def post(self,text,level='normal',key='',decision=None):
        if not text:return
        if getattr(self,'journal',None):self.journal.record(text,'Requested' if decision else 'Failed' if level=='critical' else 'Passed',level,'Notification')
        if level not in ('normal','warning','critical'):level='normal'
        text=str(text);key=key or text;now=time.time();self.serial+=1
        record=dict(id=self.serial,text=text,level=level,time=now,key=key,decision=decision is not None)
        if self.entries and self.entries[-1]['key']==key and self.entries[-1]['text']==text and now-self.entries[-1]['time']<2:self.entries[-1]=record
        else:self.entries.append(record);self.entries=self.entries[-200:]
        self.save()
        for i,old in enumerate(self.cards):
            if decision is None and not old['decision'] and old['key']==key and old['text']==text and now-old['time']<2:
                old.update(time=now,level=level,deadline=self.deadline(level,False),fading=None,alpha=1.,blurStep=0,revision=old['revision']+1)
                self._model.promote(i);self.changed.emit();return
        entry=dict(record,noticeId=record['id'],alpha=1.,blurStep=0,revision=0,deadline=0.,fading=None)
        if decision is not None:self.pending[entry['id']]=decision
        if len(self.cards)<self.MAX_CARDS:self.show(entry)
        else:
            # Bound the HMI stack. Overflow is queued, never silently discarded.
            self.waiting.append(entry)
            oldest=next((e for e in reversed(self.cards) if not e['decision'] and e['level']!='critical' and e['fading'] is None),None)
            if oldest:oldest['fading']=time.monotonic()
        self.changed.emit()
    @staticmethod
    def deadline(level,decision):return 0. if decision or level=='critical' else time.monotonic()+(6 if level=='warning' else 3.2)
    def show(self,entry):
        entry['deadline']=self.deadline(entry['level'],entry['decision']);self._model.insert(entry)
    def drain(self):
        while self.waiting and len(self.cards)<self.MAX_CARDS:self.show(self.waiting.pop(0))
    def remove(self,index):
        entry=self._model.remove(index);self.pending.pop(entry['id'],None)
        if self.renderer:self.renderer.discard(entry['id'])
    @Slot(int)
    def dismissId(self,identifier):
        i=next((i for i,e in enumerate(self.cards) if e['id']==identifier),None)
        if i is None:return
        if identifier in self.pending and getattr(self,'journal',None):self.journal.record('Cancelled: '+self.cards[i]['text'],'Cancelled','default','Consent')
        self.remove(i);self.drain();self.changed.emit()
    @Slot()
    def dismiss(self):self.dismissId(self.toast['id'])
    @Slot(int)
    def acceptId(self,identifier):
        entry=self.find(identifier)
        if not entry or not entry['decision']:return
        callback=self.pending.pop(identifier,None);self.dismissId(identifier)
        if callback:
            try:
                callback()
                if getattr(self,'journal',None):self.journal.record('Confirmed: '+entry['text'],source='Consent')
            except Exception:
                import logging
                logging.getLogger('nexatom').exception('Confirmed action failed: %s',entry['text'])
                if getattr(self,'journal',None):self.journal.record('Confirmed action failed: '+entry['text'],'Failed','critical','Consent')
                self.post('Action failed. See Logs for details.','critical')
    @Slot()
    def accept(self):self.acceptId(self.toast['id'])
    @Slot()
    def clear(self):self.entries=[];self.save();self.changed.emit()
    def tick(self):
        now=time.monotonic();dirty=False
        for i in range(len(self.cards)-1,-1,-1):
            entry=self.cards[i]
            if entry['fading'] is None and entry['deadline'] and now>=entry['deadline']:entry['fading']=now
            if entry['fading'] is None:continue
            progress=min(1,max(0,(now-entry['fading'])/self.FADE_SECONDS));dirty=True
            if progress>=1:self.remove(i);continue
            entry.update(alpha=1-progress*progress*(3-2*progress),blurStep=min(10,round(progress*10)))
            self._model.refresh(i)
        if dirty:self.drain();self.changed.emit()
