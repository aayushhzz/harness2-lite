Symptom: our weekly sales chart is missing its most recent point. With a 2-day average over the values [1, 2, 3, 4] the chart shows only two points, and a window of 0 crashes the job with a ZeroDivisionError instead of a clear message.

Function contract: `moving_average(xs, window)` in `stats.py` returns a list with one float per full window of consecutive items, in order: the mean of xs[i:i+window] for every i where the window fits entirely inside xs. If window is larger than the list the result is []. If window is less than 1 raise ValueError. An empty list with window 1 returns [].

There are no tests in this repository. Verify your fix yourself.
