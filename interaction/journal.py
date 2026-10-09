"""Bounded, persistent operator journal; independent from transient notices."""
import csv,json,sqlite3
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import QObject,Signal

class Journal(QObject):
    changed=Signal()
    LIMIT=10000
    def __init__(self,path,parent=None):
        super().__init__(parent);self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(self.path);self.db.row_factory=sqlite3.Row
        self.db.execute('PRAGMA journal_mode=WAL');self.db.execute('PRAGMA synchronous=NORMAL')
        self.db.execute('CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, timestamp TEXT, description TEXT, status TEXT, level TEXT, source TEXT, details TEXT)')
        self.db.commit();self.last_error='';self.last_signature=None
    def record(self,description,status='Passed',level='default',source='Operator',details=None):
        if self.db is None:return
        if level=='normal':level='default'
        if level not in ('default','warning','critical'):level='default'
        if status not in ('Passed','Failed','Requested','Cancelled'):status='Passed'
        try:
            with self.db:
                self.db.execute('INSERT INTO events(timestamp,description,status,level,source,details) VALUES(?,?,?,?,?,?)',
                    (datetime.now().astimezone().isoformat(timespec='milliseconds'),str(description),status,level,str(source),json.dumps(details or {},ensure_ascii=False)))
                self.db.execute('DELETE FROM events WHERE id <= (SELECT id FROM events ORDER BY id DESC LIMIT 1 OFFSET ?)',(self.LIMIT,))
            self.last_error='';self.changed.emit()
        except sqlite3.Error as exc:
            self.last_error=str(exc)
            import logging
            logging.getLogger('nexatom').exception('Operator journal write failed')
    def count(self,level='all'):
        return self.db.execute('SELECT COUNT(*) FROM events'+(' WHERE level=?' if level!='all' else ''),(() if level=='all' else (level,))).fetchone()[0]
    def rows(self,level='all',offset=0,limit=100):
        sql='SELECT * FROM events'+(' WHERE level=?' if level!='all' else '')+' ORDER BY id DESC LIMIT ? OFFSET ?'
        args=(() if level=='all' else (level,))+(int(limit),max(0,int(offset)))
        return [dict(row) for row in self.db.execute(sql,args)]
    def clear(self):
        with self.db:self.db.execute('DELETE FROM events')
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
        if self.db is not None:self.db.close();self.db=None
