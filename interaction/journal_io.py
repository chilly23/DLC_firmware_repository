"""One ordered SQLite writer. Disk waits never run in an input handler."""
from concurrent.futures import Future
from queue import Queue, Empty
import sqlite3
from threading import Thread


class JournalWriter:
    def __init__(self,path,failed):
        self.path,self.failed=path,failed
        self.queue=Queue();self.error=None
        self.thread=Thread(target=self.run,name='NexatomJournal',daemon=True)
        self.thread.start()

    def put(self,operation,record=None,limit=10000):
        self.queue.put((operation,record,limit))

    def close(self):
        done=Future();self.put('stop',done);done.result(timeout=15)
        self.thread.join(timeout=1)
        if self.thread.is_alive():raise RuntimeError('Journal writer did not stop')
        if self.error:raise RuntimeError('Journal could not save all records') from self.error

    def run(self):
        db=None
        try:
            db=sqlite3.connect(self.path)
            db.execute('PRAGMA journal_mode=WAL');db.execute('PRAGMA synchronous=NORMAL')
            running=True
            while running:
                batch=[self.queue.get()]
                for _ in range(255):
                    if batch[-1][0]=='stop':break
                    try:batch.append(self.queue.get_nowait())
                    except Empty:break
                stop=next((r for op,r,n in batch if op=='stop'),None)
                try:
                    with db:
                        for operation,record,limit in batch:
                            if operation=='clear':db.execute('DELETE FROM events')
                            elif operation=='insert':
                                db.execute('INSERT INTO events(id,timestamp,description,status,level,source,details) VALUES(?,?,?,?,?,?,?)',tuple(record[k] for k in ('id','timestamp','description','status','level','source','details')))
                        db.execute('DELETE FROM events WHERE id <= (SELECT id FROM events ORDER BY id DESC LIMIT 1 OFFSET ?)',(batch[-1][2],))
                except sqlite3.Error as exc:
                    self.error=exc;self.failed(str(exc))
                    # Keep in-memory records/export usable; report durability
                    # failure explicitly. Never replay an uncertain audit write.
                if stop is not None:
                    stop.set_result(None);running=False
        except Exception as exc:
            self.error=exc;self.failed(str(exc))
            # Startup failure still lets shutdown synchronize without deadlock.
            while True:
                operation,record,limit=self.queue.get()
                if operation=='stop':record.set_result(None);break
        finally:
            if db is not None:db.close()
