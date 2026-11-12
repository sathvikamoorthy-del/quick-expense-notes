# REQ-276: Expand one short entry by the abbreviation rules

Feature: FEAT-1056 User can see a short entry expanded · Decision: DEC-310
Order: 2 of 7
Depends on: User can sign in to their own account
Goal: G1 (every short entry expands exactly as the abbreviation rules say)

## Purpose
The user types an expense in a few characters and sees the clean expense it stands for, or exactly why it cannot be read.

## Behaviour
Format: `<code> <amount> [date] [note]`, fields separated by single spaces.

- **Code:** a category code (F Food, T Travel, R Rent, U Utilities, S Shopping, H Health, E Entertainment, O Other) sets the category, and the merchant is none. A merchant code (SWG Swiggy/Food, ZMT Zomato/Food, UBR Uber/Travel, OLA Ola/Travel, AMZ Amazon/Shopping, NFX Netflix/Entertainment, APL Apollo Pharmacy/Health, BSN BSNL/Utilities) sets both the merchant and its category.
- **Amount:** a positive number with up to 2 decimals. A `k` suffix means thousand (`1.5k` = 1500.00). The amount is in rupees and shown with 2 decimals.
- **Date:** none or `td` = today; `yd` = yesterday; `dd/mm` = that day in the current year. A future date is not allowed.
- **Note:** everything after the date. With no date, everything after the amount.
- **Errors** (exact messages):

| Situation | Message |
|---|---|
| Code not in the tables | Unknown code "X". |
| No amount | Amount is missing. |
| Zero, negative or not a number | Amount must be greater than 0. |
| Date not `td`, `yd` or a real `dd/mm` | Date is not valid. |
| Date in the future | Date cannot be in the future. |

- An unknown code is an error, never a suggestion.

## Acceptance criteria
With today = 12 November 2026:
- `F 250` gives no merchant, Food, 250.00, 12 Nov 2026, no note.
- `SWG 340 yd` gives Swiggy, Food, 340.00, 11 Nov 2026.
- `UBR 180 12/11 airport` gives Uber, Travel, 180.00, 12 Nov 2026, note "airport".
- `R 1.5k` gives no merchant, Rent, 1500.00, 12 Nov 2026.
- `NFX 649` gives Netflix, Entertainment, 649.00, 12 Nov 2026.
- `APL 420 td fever tablets` gives Apollo Pharmacy, Health, 420.00, 12 Nov 2026, note "fever tablets".
- `S 2k td shoes` gives no merchant, Shopping, 2000.00, 12 Nov 2026, note "shoes".
- `AMZ 799.50` gives Amazon, Shopping, 799.50, 12 Nov 2026.
- `X 100` gives Unknown code "X".; `F` gives Amount is missing.; `F -50` gives Amount must be greater than 0.; `F 100 32/13` gives Date is not valid.; `F 100 20/11` gives Date cannot be in the future.

## Source documents
- docs/project/source/02-abbreviation-rules.md
- docs/project/source/03-sample-entries.md (Entries that work, Entries that fail)
- docs/project/source/01-project-brief.md (Purpose, Goals, Non-goals: no guessing)

## Open questions
- Are codes case-sensitive (is `swg 340` valid)?
- Which timezone defines "today" and "yesterday"?
- Is an amount with more than 2 decimals (`250.555`, `1.2345k`) an error, and which message does it get?
- Is `dd/mm` with a missing leading zero (`5/11`) valid?
- How are extra spaces between fields handled? The rules say single spaces.
