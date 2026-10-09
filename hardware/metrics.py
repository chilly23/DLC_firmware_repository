"""Bounded timing samples with cumulative counters; nanoseconds on one host clock."""
from collections import defaultdict, deque
from threading import Lock


class Metrics:
    def __init__(self):
        self.lock = Lock()
        self.samples = defaultdict(lambda: deque(maxlen=20000))
        self.counts = defaultdict(int)
        self.maximum = defaultdict(float)

    def count(self, name, amount=1):
        with self.lock:
            self.counts[name] += amount

    def observe(self, name, ns):
        value = max(0, ns) / 1e6
        with self.lock:
            self.samples[name].append(value)
            self.counts[name] += 1
            self.maximum[name] = max(self.maximum[name], value)

    def snapshot(self):
        with self.lock:
            timings = {}
            for name, samples in self.samples.items():
                ordered = sorted(samples)
                if not ordered:
                    continue
                timings[name] = dict(count=self.counts[name], retained=len(ordered),
                    p50_ms=ordered[int((len(ordered)-1)*.50)],
                    p95_ms=ordered[int((len(ordered)-1)*.95)],
                    p99_ms=ordered[int((len(ordered)-1)*.99)], max_ms=self.maximum[name])
            return dict(counts=dict(self.counts), timings=timings)
