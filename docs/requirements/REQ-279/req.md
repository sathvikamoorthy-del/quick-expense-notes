# REQ-279: Monthly summary by category

Feature: FEAT-1059 User can see a monthly summary by category · Decision: DEC-313
Order: 5 of 7
Depends on: User can save the reviewed entries
Goal: G3 (monthly totals always match the saved entries)

## Purpose
Show where the month's money went, one total per category, always in line with the saved entries.

## Behaviour
- The user opens the summary of one month.
- The saved entries of that month (of the signed-in user) are grouped by category.
- One total is shown for each category that has entries, plus one grand total. Amounts have 2 decimals.

## Acceptance criteria
- With the 8 working entries of 03-sample-entries.md saved, the November 2026 summary is:

  | Category | Total |
  |---|---|
  | Food | 590.00 |
  | Travel | 180.00 |
  | Rent | 1500.00 |
  | Entertainment | 649.00 |
  | Health | 420.00 |
  | Shopping | 2799.50 |
  | **Grand total** | **6138.50** |
- Categories without entries in that month are not shown.
- Only entries dated in that month, of the signed-in user, are counted.
- The totals equal the sum of the saved entries at the moment the summary is opened.

## Source documents
- docs/project/source/01-project-brief.md (Purpose; step 5; goal "monthly totals that always match")
- docs/project/source/02-abbreviation-rules.md (Monthly summary)
- docs/project/source/03-sample-entries.md (Monthly summary)

## Open questions
- How does the user pick the month, and which month is shown by default?
- What is shown for a month with no entries?
- In which order are the categories listed? The sample order is neither the code-table order nor alphabetical.
