"""Bounded, persistent operator journal; independent from transient notices."""
import csv,json,sqlite3
from collections import deque
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import QObject,Signal

class Journal(QObject):
    changed=Signal()
    storageFailed=Signal(str)
    LIMIT=10000
    def __init__(self,path,parent=None):
        super().__init__(parent);self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.row_factory=sqlite3.Row
            db.execute('PRAGMA journal_mode=WAL');db.execute('PRAGMA synchronous=NORMAL')
            db.execute('CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, timestamp TEXT, description TEXT, status TEXT, level TEXT, source TEXT, details TEXT)')
            self.cache=deque(dict(row) for row in db.execute('SELECT * FROM events ORDER BY id DESC LIMIT ?',(self.LIMIT,)))
        db.close()
        self.serial=self.cache[0]['id'] if self.cache else 0
        self.last_error='';self.last_signature=None;self.closed=False
        self.storageFailed.connect(self.storage_failed)
        from .journal_io import JournalWriter
        self.writer=JournalWriter(self.path,self.storageFailed.emit)
    def storage_failed(self,message):
        self.last_error=message
        import logging
        logging.getLogger('nexatom').error('Operator journal persistence failed: %s',message)
    def record(self,description,status='Passed',level='default',source='Operator',details=None):
        if self.closed:return
        if level=='normal':level='default'
        if level not in ('default','warning','critical'):level='default'
        if status not in ('Passed','Failed','Requested','Cancelled'):status='Passed'
        self.serial+=1
        record=dict(id=self.serial,timestamp=datetime.now().astimezone().isoformat(timespec='milliseconds'),description=str(description),status=status,level=level,source=str(source),details=json.dumps(details or {},ensure_ascii=False))
        self.cache.appendleft(record)
        while len(self.cache)>self.LIMIT:self.cache.pop()
        self.writer.put('insert',record,self.LIMIT);self.changed.emit()
    def count(self,level='all'):
        return len(self.cache) if level=='all' else sum(r['level']==level for r in self.cache)
    def rows(self,level='all',offset=0,limit=100):
        rows=[r for r in self.cache if level=='all' or r['level']==level]
        start=max(0,int(offset));return [dict(r) for r in rows[start:start+max(0,int(limit))]]
    def clear(self):
        self.cache.clear();self.writer.put('clear',limit=self.LIMIT)
        self.record('User logs cleared',source='Logs')
    def export(self,folder):
        folder=Path(folder);folder.mkdir(parents=True,exist_ok=True);rows=self.rows(limit=self.LIMIT)
        csvpath=folder/'logs.csv';mdpath=folder/'logs.md'
        fields=('timestamp','description','status','level','source','details')
        with csvpath.open('w',newline='',encoding='utf-8-sig') as stream:
            writer=csv.DictWriter(stream,fieldnames=fields,extrasaction='ignore');writer.writeheader()
            for row in reversed(rows):
                # Spreadsheet exports must not execute operator-entered strings.
                safe={k:("'"+str(row[k]) if str(row[k]).startswith(('=','+','-','@','\t','\r')) else row[k]) for k in fields};writer.writerow(safe)
        lines=['# Nexatom user logs','',f'Exported {datetime.now().astimezone().isoformat(timespec="seconds")}',f'{len(rows)} records. Newest first.','']
        for row in rows:lines.extend([f'## {row["timestamp"]} — {row["status"]} / {row["level"]}',f'Source: {row["source"]}',row['description'],''])
        mdpath.write_text('\n'.join(lines),encoding='utf8');self.record('User logs exported',source='Logs',details={'csv':str(csvpath),'markdown':str(mdpath)})
        return csvpath,mdpath
    def close(self):
        if not self.closed:
            self.closed=True
            try:self.writer.close()
            except RuntimeError as exc:self.storage_failed(str(exc));raise
