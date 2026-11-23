Symptom: the latency dashboard reports a median that is higher than the real middle value when the number of samples is even, and sometimes the raw sample list the dashboard keeps is shuffled after the call.

Function contract: `median(xs)` in `stats2.py` returns the median of a list of numbers. For an odd count it returns the middle value. For an even count it returns the mean of the two middle values. The input list is not changed. Empty input raises ValueError.

There are no tests in this repository. Verify your fix yourself.
