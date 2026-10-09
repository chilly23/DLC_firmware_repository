"""One explicit GUI ingress queue. No Qt signal per edge and no silent eviction."""
from collections import deque
from threading import Lock


class Mailbox:
    def __init__(self):
        self.lock = Lock()
        self.queue = deque()
        self.completions = deque()
        self.high_water = 0
        self.received = 0
        self.delivered = 0

    def put(self, item):
        with self.lock:
            # A completed driver command must not look timed out merely because
            # presentation is behind. Input/reset ordering stays FIFO.
            (self.completions if item.get('kind')=='ack' else self.queue).append(item)
            self.received += 1
            self.high_water = max(self.high_water, len(self.queue)+len(self.completions))

    def take(self):
        with self.lock:
            if not self.queue and not self.completions:
                return None
            self.delivered += 1
            if self.completions:return self.completions.popleft()
            item=self.queue.popleft()
            events=item.get('frame',{}).get('events',[])
            if item.get('kind')=='input' and len(events)==1 and events[0][0]=='rotation':
                amount=events[0][1]
                while self.queue and abs(amount)<128:
                    other=self.queue[0];next_events=other.get('frame',{}).get('events',[])
                    if (other.get('kind')!='input' or other.get('group')!=item.get('group') or
                            other.get('epoch')!=item.get('epoch') or len(next_events)!=1 or
                            next_events[0][0]!='rotation' or next_events[0][1]*amount<=0):break
                    self.queue.popleft();self.delivered+=1;amount+=next_events[0][1]
                    item['frame']['count']=other['frame']['count']
                item['frame']['events']=[('rotation',amount)]
            return item

    def snapshot(self):
        with self.lock:
            return dict(pending=len(self.queue)+len(self.completions), high_water=self.high_water,
                        received=self.received, delivered=self.delivered)
