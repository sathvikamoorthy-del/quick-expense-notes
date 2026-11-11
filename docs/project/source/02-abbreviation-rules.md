# Quick Expense Notes: abbreviation rules

## Entry format
```
<code> <amount> [date] [note]
```
- Separate entries with a new line or a semicolon.
- Fields are separated by single spaces.
- Everything after the date is the note. If there is no date, everything after the amount is the note.

## Category codes
| Code | Category |
|---|---|
| F | Food |
| T | Travel |
| R | Rent |
| U | Utilities |
| S | Shopping |
| H | Health |
| E | Entertainment |
| O | Other |

## Merchant codes
A merchant code sets both the merchant and its category.

| Code | Merchant | Category |
|---|---|---|
| SWG | Swiggy | Food |
| ZMT | Zomato | Food |
| UBR | Uber | Travel |
| OLA | Ola | Travel |
| AMZ | Amazon | Shopping |
| NFX | Netflix | Entertainment |
| APL | Apollo Pharmacy | Health |
| BSN | BSNL | Utilities |

## Amount
- A positive number with up to 2 decimals, for example `250` or `799.50`.
- A `k` suffix means thousand: `1.5k` is 1500.00 and `2k` is 2000.00.
- Amounts are in rupees and are shown with 2 decimals.

## Date
| Written as | Meaning |
|---|---|
| (no date) | Today |
| `td` | Today |
| `yd` | Yesterday |
| `dd/mm` | That day in the current year, for example `12/11` |

A date in the future is not allowed.

## Errors
Each error stops only that entry. The other entries in the same text box are still expanded.

| Situation | Error message |
|---|---|
| The code is not in the tables | Unknown code "X". |
| There is no amount | Amount is missing. |
| The amount is zero, negative or not a number | Amount must be greater than 0. |
| The date is not `td`, `yd` or a real `dd/mm` | Date is not valid. |
| The date is in the future | Date cannot be in the future. |

## Monthly summary
- Group the saved entries of one month by category.
- Show the total for each category that has entries, and one grand total.
- Show amounts with 2 decimals.
