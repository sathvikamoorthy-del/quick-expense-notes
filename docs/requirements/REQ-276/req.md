# REQ-276: Expand one short entry by the abbreviation rules

Feature: FEAT-1056 User can see a short entry expanded · Decision: DEC-310
Order: 2 of 7
Depends on: User can sign in to their own account
Goal: G1 (every short entry expands exactly as the abbreviation rules say)

## Purpose
The user types an expense in a few characters and sees the clean expense it stands for, or exactly why it cannot be read.

## Behaviour
Format: `<code> <amount> [date] [note]`.

- **Spaces:** leading and trailing spaces are trimmed. One or more spaces separate the fields (`  SWG   340   yd  ` reads as `SWG 340 yd`). The note is the rest of the entry after its separating spaces, kept as typed.
- **Upper and lower case:** codes, the date words `td` / `yd` and the `k` suffix are not case-sensitive (`swg 340`, `F 1.5K YD` are valid). Codes are stored in upper case.
- **Code:** a category code (F Food, T Travel, R Rent, U Utilities, S Shopping, H Health, E Entertainment, O Other) sets the category, and the merchant is none. A merchant code (SWG Swiggy/Food, ZMT Zomato/Food, UBR Uber/Travel, OLA Ola/Travel, AMZ Amazon/Shopping, NFX Netflix/Entertainment, APL Apollo Pharmacy/Health, BSN BSNL/Utilities) sets both the merchant and its category.
- **Amount:** a positive number with at most 2 decimals, counted as typed (before the `k` suffix). A `k` suffix means thousand (`1.5k` = 1500.00, `2k` = 2000.00). The amount is in rupees and shown with 2 decimals.
- **Date:** none or `td` = today; `yd` = yesterday; `dd/mm` = that day in the current year. Day and month may be written with one or two digits (`5/11` = `05/11`). A future date is not allowed.
- **Time zone:** "today", "yesterday", "the current year" and "the future" are all reckoned in IST (Asia/Kolkata), for every user.
- **Note:** everything after the date. With no date, everything after the amount.
- **Errors** (exact messages). Each entry shows one error: the checks run in this order and the first one that fails is shown.

| # | Situation | Message |
|---|---|---|
| 1 | Code not in the tables | Unknown code "X". |
| 2 | No amount | Amount is missing. |
| 3 | Zero, negative or not a number | Amount must be greater than 0. |
| 4 | More than 2 decimals (as typed, before `k`) | Amount must have at most 2 decimals. |
| 5 | Date not `td`, `yd` or a real `dd/mm` | Date is not valid. |
| 6 | Date in the future (IST) | Date cannot be in the future. |

- An unknown code is an error, never a suggestion. In `Unknown code "X".`, X is the code as the user typed it.

## Acceptance criteria
With today = 12 November 2026 (IST):
- `F 250` gives no merchant, Food, 250.00, 12 Nov 2026, no note.
- `SWG 340 yd` gives Swiggy, Food, 340.00, 11 Nov 2026.
- `UBR 180 12/11 airport` gives Uber, Travel, 180.00, 12 Nov 2026, note "airport".
- `R 1.5k` gives no merchant, Rent, 1500.00, 12 Nov 2026.
- `NFX 649` gives Netflix, Entertainment, 649.00, 12 Nov 2026.
- `APL 420 td fever tablets` gives Apollo Pharmacy, Health, 420.00, 12 Nov 2026, note "fever tablets".
- `S 2k td shoes` gives no merchant, Shopping, 2000.00, 12 Nov 2026, note "shoes".
- `AMZ 799.50` gives Amazon, Shopping, 799.50, 12 Nov 2026.
- `X 100` gives Unknown code "X".; `F` gives Amount is missing.; `F -50` gives Amount must be greater than 0.; `F 100 32/13` gives Date is not valid.; `F 100 20/11` gives Date cannot be in the future.
- `swg 340` gives Swiggy, Food, 340.00, 12 Nov 2026 (code stored as SWG).
- `F 1.5K YD` gives no merchant, Food, 1500.00, 11 Nov 2026.
- `F 100 5/11` gives no merchant, Food, 100.00, 5 Nov 2026.
- `  SWG   340   yd  ` gives the same result as `SWG 340 yd`.
- `F 250.555` and `F 1.2345k` give Amount must have at most 2 decimals.
- `F -1.555` gives Amount must be greater than 0. (check 3 runs before check 4).
- At 00:30 IST on 13 Nov 2026, `F 100 td` is dated 13 Nov 2026, whatever the user's own time zone.

## Answered questions
Answered by the product owner on 13 Nov 2026:
- Are codes case-sensitive? No: `swg 340` is valid; codes are stored in upper case.
- Which time zone defines "today" and "yesterday"? IST (Asia/Kolkata) for all users.
- Is an amount with more than 2 decimals an error? Yes: "Amount must have at most 2 decimals." (`250.555`, `1.2345k`).
- Is `dd/mm` without a leading zero (`5/11`) valid? Yes.
- How are extra spaces handled? Extra spaces between fields count as one; leading and trailing spaces are trimmed.
- Which error wins when an amount breaks two rules (`F -1.555`)? "Amount must be greater than 0." (checks run in the order of the table).
- Are `td`, `yd` and `k` case-insensitive too? Yes, like codes.

## Source documents
- docs/project/source/02-abbreviation-rules.md
- docs/project/source/03-sample-entries.md (Entries that work, Entries that fail)
- docs/project/source/01-project-brief.md (Purpose, Goals, Non-goals: no guessing)
- Product owner answers, 13 Nov 2026 (above)
