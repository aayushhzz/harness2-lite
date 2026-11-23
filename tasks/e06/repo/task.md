Symptom: the invoicing report says a billing period from 2024-01-01 to 2024-01-03 is 2 days long, and when the dates are typed the other way round the report shows a negative number.

Function contract: `days_between(a, b)` in `daterange.py` takes two ISO dates as "YYYY-MM-DD" strings. It returns the number of calendar days in the range counted inclusively, so both end dates count. The order of the two arguments does not matter. The same day returns 1. Invalid date text raises ValueError.

There are no tests in this repository. Verify your fix yourself.
