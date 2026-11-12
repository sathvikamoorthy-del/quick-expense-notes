# Gaps: note-to-summary (From short notes to the monthly summary)

Spec: docs/project/context.md (intent, source documents 01-03, REQ-275 to REQ-281, all draft except sources and intent).
Each gap: what the spec says, what it leaves out, what the walkthrough shows instead.

## Spec gaps

1. **Sign-in method** (S01, step `open-app`; REQ-275). Says: the user signs in first. Leaves out: the method, how a new user gets an account, sign-out, remembered sessions. Shows: a single "Sign in as Asha" button; the method button and "Get an account" link show a Not defined alert.
2. **Screen codes** (all screens). The spec has no screen codes or screen list. The walkthrough made S01 Sign in, S02 Entry box, S03 Saved entries, S04 Edit entry, S05 Monthly summary.
3. **Layout of every screen** (REQ-276 to REQ-281 mocks say "layout is not described"). Shows: plain cards and tables with only the fields the spec defines (typed, merchant, category, amount, date, note).
4. **When results are shown** (S02, step `type-entries`; REQ-277). Leaves out: as the user types, or on a review action. Shows: a Review button (assumption); "When are results shown?" shows a Not defined alert.
5. **Text box after saving** (S02, step `after-save`; REQ-278). Leaves out: cleared or failed lines kept. Shows: a result card (3 saved, 1 not saved with its error) and a Not defined alert.
6. **Saving with errors present** (step `review`; REQ-278). The sample says 3 saved and 1 error shown; REQ-278 asks to confirm. Shows: saving is allowed; the invalid line is not saved.
7. **Duplicate saves** (REQ-278). Leaves out: whether saving the same text twice creates duplicates. Shown only in the `after-save` alert.
8. **Month selection and default month** (S05; REQ-279). Leaves out: how the month is picked, the default, and what an empty month shows. Shows: November 2026 fixed; "Change month" shows a Not defined alert.
9. **Category order in the summary** (S05; REQ-279). Leaves out: the order. Shows: the order of the sample summary (Food, Travel, Rent, Entertainment, Health, Shopping), then Utilities and Other (assumption).
10. **Saved-entries list** (S03, step `entries-gap`; REQ-278/280/281). The spec describes no list, but edit and delete need one. Shows: a plain list reached from the summary and the "Entries" tab; "About this list" shows a Not defined alert.
11. **Edit form** (S04, step `edit-gap`; REQ-280). Leaves out: short form or field by field; whether the rules and errors apply to edits; relative dates in an edit. Shows: the short form, pre-filled with a sample correction; the field shows a Not defined alert. A refused (invalid) edit is not shown.
12. **Landing after an edit** (step `edit`; REQ-280). Leaves out: where the user lands. Shows: back to the saved-entries list (assumption).
13. **Delete confirmation and undo** (S03, step `deleted`; REQ-281). Leaves out: confirm, undo. Shows: the entry is removed at once, with a Not defined alert.
14. **Open questions of REQ-276 not shown in the tour**: case of codes, timezone of "today", more than 2 decimals, `5/11` without leading zero, extra spaces, empty parts (`;;`), entry limit. The tour uses only the sample entries, which the spec defines.

## Walkthrough notes (not spec gaps)

- Entries r1-r5 (R 1.5k, NFX 649, APL 420 td fever tablets, S 2k td shoes, AMZ 799.50) start as already saved, so after the tour saves the 3-line sample box the November summary equals the spec sample (grand total 6138.50).
- The edit (Uber 180.00 to 220.00, `UBR 220 12/11 airport`) and the delete (Netflix) are sample choices. After them the summary is Food 590.00, Travel 220.00, Rent 1500.00, Health 420.00, Shopping 2799.50, grand total 5529.50; Entertainment disappears (REQ-281 acceptance).
- The summary screen computes its totals from the saved records; the info-panel grand total is a value kept in the seed for display and set to the same numbers.
- The shell is the template's bottom tab bar (Enter, Entries, Summary), although the app is desktop; a sidebar was not asked for. Sign-out is not shown.
- Amounts are shown with 2 decimals and no currency symbol, as in the sample tables.
