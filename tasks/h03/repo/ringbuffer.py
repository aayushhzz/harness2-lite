class RingBuffer:
    def __init__(self, capacity):
        if capacity < 1:
            raise ValueError("capacity must be >= 1")
        self.capacity = capacity
        self._items = [None] * capacity
        self._next = 0
        self._count = 0

    def __len__(self):
        return self._count

    def push(self, x):
        if self._count < self.capacity:
            self._items[self._count] = x
            self._count += 1
        else:
            self._items[self._next - 1] = x
        self._next = (self._next + 1) % self.capacity

    def to_list(self):
        if self._count < self.capacity:
            return self._items[:self._count]
        start = self._next - 1
        return self._items[start:] + self._items[:start]
