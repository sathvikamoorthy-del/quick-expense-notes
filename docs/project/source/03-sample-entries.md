# Quick Expense Notes: sample entries

Assume today is 12 November 2026.

## Entries that work
| Typed | Merchant | Category | Amount | Date | Note |
|---|---|---|---|---|---|
| `F 250` | (none) | Food | 250.00 | 12 Nov 2026 | |
| `SWG 340 yd` | Swiggy | Food | 340.00 | 11 Nov 2026 | |
| `UBR 180 12/11 airport` | Uber | Travel | 180.00 | 12 Nov 2026 | airport |
| `R 1.5k` | (none) | Rent | 1500.00 | 12 Nov 2026 | |
| `NFX 649` | Netflix | Entertainment | 649.00 | 12 Nov 2026 | |
| `APL 420 td fever tablets` | Apollo Pharmacy | Health | 420.00 | 12 Nov 2026 | fever tablets |
| `S 2k td shoes` | (none) | Shopping | 2000.00 | 12 Nov 2026 | shoes |
| `AMZ 799.50` | Amazon | Shopping | 799.50 | 12 Nov 2026 | |

## Entries that fail
| Typed | Result |
|---|---|
| `X 100` | Unknown code "X". |
| `F` | Amount is missing. |
| `F -50` | Amount must be greater than 0. |
| `F 100 32/13` | Date is not valid. |
| `F 100 20/11` | Date cannot be in the future. |

## Several entries in one text box
Typed:
```
F 250; SWG 340 yd
X 100
UBR 180 12/11 airport
```
Result: three entries are saved (`F 250`, `SWG 340 yd`, `UBR 180 12/11 airport`) and one error is shown for `X 100`.

## Monthly summary
If all eight working entries above are saved, the summary for November 2026 is:

| Category | Total |
|---|---|
| Food | 590.00 |
| Travel | 180.00 |
| Rent | 1500.00 |
| Entertainment | 649.00 |
| Health | 420.00 |
| Shopping | 2799.50 |
| **Grand total** | **6138.50** |
