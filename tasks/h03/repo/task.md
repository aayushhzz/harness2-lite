Symptom: the dashboard log panel shows the last few log lines in the wrong order, and once the buffer is full the newest line seems to replace the line before it instead of the oldest one.

Function contract: `ringbuffer.py` defines `RingBuffer(capacity)`. `push(x)` adds an item; when the buffer is full the OLDEST item is overwritten. `to_list()` returns the items from oldest to newest. `len(rb)` is the number of items held, at most the capacity. A capacity below 1 raises ValueError.

There are no tests in this repository. Verify your fix yourself.
