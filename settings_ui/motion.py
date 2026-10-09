"""Frame-rate-independent, unbounded wheel motion in units of menu items."""

import math


class WheelMotion:
    def __init__(self, position=3.0):
        self.position = float(position)
        self.velocity = 0.0
        self.target = None
        self.dragging = False

    def begin(self):
        self.dragging = True
        self.velocity = 0.0
        self.target = None

    def drag(self, items):
        self.position += items

    def release(self, velocity):
        self.dragging = False
        self.velocity = max(-20.0, min(20.0, velocity))
        if abs(self.velocity) < 0.35:
            self.target = round(self.position)

    def move_to(self, absolute_index):
        self.target = float(absolute_index)
        self.velocity = 0.0
        self.dragging = False

    def nearest(self, index, count):
        return index + round((self.position - index) / count) * count

    def tick(self, dt):
        if self.dragging:
            return False
        dt = min(max(dt, 0), 0.05)
        old = self.position
        if self.target is None:
            if abs(self.velocity) > 0.35:
                decay = math.exp(-2.6 * dt)
                self.position += self.velocity * (1 - decay) / 2.6
                self.velocity *= decay
            else:
                self.target = round(self.position)
                self.velocity = 0
        if self.target is not None:
            self.position += (self.target - self.position) * (1 - math.exp(-15 * dt))
            if abs(self.target - self.position) < 0.0008:
                self.position = self.target
                self.target = None
                self.velocity = 0
        return abs(self.position - old) > 0.00001
