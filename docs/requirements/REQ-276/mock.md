# REQ-276 mock: one entry expanded

The layout is not described in the documents. This shows only the information they define (today = 12 Nov 2026, IST).

```
+--------------------------------------------------------------+
| swg 340 yd                                                   |
+--------------------------------------------------------------+
  Merchant   Category   Amount    Date          Note
  Swiggy     Food       340.00    11 Nov 2026

+--------------------------------------------------------------+
| F 100 5/11 groceries                                         |
+--------------------------------------------------------------+
  Merchant   Category   Amount    Date          Note
  -          Food       100.00    5 Nov 2026    groceries

+--------------------------------------------------------------+
| X 100                                                        |
+--------------------------------------------------------------+
  Error: Unknown code "X".

+--------------------------------------------------------------+
| F 250.555                                                    |
+--------------------------------------------------------------+
  Error: Amount must have at most 2 decimals.

Checks, first failure wins:
  code -> amount missing -> amount > 0 -> at most 2 decimals
       -> date valid -> date not in the future (IST)
```
