# TC-031: Monthly summary by category (REQ-279 acceptance)

Requirement: REQ-279 (approved) · Work item: WI-049 (implemented) · Applications: api (primary), web

## Scope
Every acceptance criterion of REQ-279 and every product-owner answer recorded in WI-049's impl.md (22 Nov 2026). Tested through `GET /summary` and the `/summary` page.

Out of scope:
- Saving entries: TC-030 covers it. Here, saving is only used to set up data.
- Editing and deleting entries (REQ-280, REQ-281).

## Setup
- **Database:** a SQLite file built from every migration in `apps/api/migrations` (0001 to 0004), with two users: Asha `11111111-1111-1111-1111-111111111111` and Ravi `22222222-2222-2222-2222-222222222222`.
- **Today:** 12 Nov 2026 in IST. The API's clock (`today_ist`) is pinned to this date, except where a row says otherwise.
- **Signed in:** each request carries `Authorization: Bearer <token>` with the user's id as `sub`. In the browser, sign in at `/sign-in`.
- **The sample entries:** the 8 working entries of 03-sample-entries.md, saved for Asha (review, then save, as in TC-030):
  ```
  F 250
  SWG 340 yd
  UBR 180 12/11 airport
  R 1.5k
  NFX 649
  APL 420 td fever tablets
  S 2k td shoes
  AMZ 799.50
  ```
- **Request:** `GET /summary?month=YYYY-MM`, or no `month` for the current IST month.
- **Answer:** `200 {month, current_month, categories: [{code, category, total, total_paise}], grand_total, grand_total_paise}`. Totals are rupees with 2 decimals; `*_paise` is the same amount in integer paise.

## A. The sample month (REQ-279 acceptance 1)
Asha has the sample entries saved, and opens `month=2026-11`.

| # | Category | total | total_paise |
|---|---|---|---|
| A1 | Food | 590.00 | 59000 |
| A2 | Travel | 180.00 | 18000 |
| A3 | Rent | 1500.00 | 150000 |
| A4 | Entertainment | 649.00 | 64900 |
| A5 | Health | 420.00 | 42000 |
| A6 | Shopping | 2799.50 | 279950 |
| A7 | **Grand total** | 6138.50 | 613850 |

Expected: exactly these six categories in this order, then `grand_total: "6138.50"`, with `month` and `current_month` both `"2026-11"`.

## B. Category order (q4)
| # | Entries of the month | Expected order |
|---|---|---|
| B1 | `O 5`, `BSN 10`, `F 1` (typed in this order) | Food, Utilities, Other |
| B2 | One entry in every category | Food, Travel, Rent, Entertainment, Health, Shopping, Utilities, Other |

## C. Only what counts (REQ-279 acceptance 2 and 3)
| # | Setup | Expected |
|---|---|---|
| C1 | The sample entries (A) | Utilities and Other are not listed: categories with no entries are not shown |
| C2 | Food entries dated 31 Oct, 1 Nov, 30 Nov and 1 Dec 2026 (100, 200, 300, 400 paise) | November: Food 5.00 (1 Nov and 30 Nov only). October: Food 1.00. December: Food 4.00. |
| C3 | Asha has the sample entries; Ravi has `R 9k` dated 5 Nov | Asha's November grand total stays 6138.50. Ravi's November is Rent 9000.00 only. |

## D. Month selection (q1, q2, q5)
| # | Request | Expected |
|---|---|---|
| D1 | `GET /summary` with no `month` | the current IST month: `month: "2026-11"`, `current_month: "2026-11"` |
| D2 | `month=2026-10` | `month: "2026-10"`, `current_month: "2026-11"` |
| D3 | `month=2026-12` or `month=2027-01` (future) | 422, `error: "validation-error"` |
| D4 | `month=2026-13`, `2026-1`, `nov` | 422, `error: "validation-error"` |
| D5 | `month=2025-12` (across the year) | 200, the December 2025 summary |

## E. A month with no entries (q3)
| # | Request | Expected |
|---|---|---|
| E1 | `month=2026-09` for Asha (no September entries) | `categories: []`, `grand_total: "0.00"` |

The page then shows the no-entries text (G3).

## F. Totals at the moment of opening (REQ-279 acceptance 4)
| # | Steps | Expected |
|---|---|---|
| F1 | Open `month=2026-11` with no entries | `grand_total: "0.00"`, and the header `Cache-Control: no-store` |
| F2 | Save `F 250`, then open `month=2026-11` again within 30 seconds | `grand_total: "250.00"` at once. There is no `x-cache` header: the answer is never served from the response cache. |
| F3 | `GET /summary` without an Authorization header | 401 |

## G. The summary page (web, `/summary`)
Precondition: the web app runs with `API_PROXY_TARGET` pointing at the API, the local database has migration 0004, and the tester is signed in. Today is the real IST date (the current month is whatever it is now).

| # | Steps | Expected |
|---|---|---|
| G1 | On `/entries`, click "Monthly summary". | `/summary` opens on the current month, with a heading like `November 2026`. |
| G2 | Save the sample entries (all dated in the current month if today is 12 Nov or later in November 2026), then open `/summary`. | A `Category · Total` table with the categories in the q4 order and a bold `Grand total` row. With the sample entries in that month, it matches section A. |
| G3 | Press Previous to reach a month with no entries. | `No expenses in this month.`, with no table and no grand total. The heading shows that month. |
| G4 | On the current month. | Next is disabled. |
| G5 | Press Previous, then Next. | Next is enabled on the earlier month and brings back the current month, where it is disabled again. |
| G6 | Press Previous from January. | December of the year before. |
| G7 | Click "Enter expenses". | Back to `/entries`. |
| G8 | Sign out, open `/summary`. | The sign-in screen: the summary needs a session. |
| G9 | Save an entry on `/entries`. | No link to the summary appears after Save (q6). The "Monthly summary" link is always there. |

## Automated coverage
| Rows | Automated in | Gap |
|---|---|---|
| A, B1, C1 to C3, E1 (service) | `apps/api/tests/entries/test_summary.py` (database built from 0001 to 0004) | B2 is covered by the fixed order test, not by an eight-category data test. |
| A, D1, D3, D4, F1 to F3 (API) | `apps/api/tests/entries/test_routes.py` (`test_summary_*`) | D2 and D5 are covered by the service month tests and `parse_month`, not through the route. |
| G1 to G7 | `apps/web/tests/summary/MonthlySummary.test.tsx`, `useSummary.test.ts`, `apps/web/tests/entries/EntryBox.test.tsx` (link) | G2 against a live API is a manual step. |
| G8 | `apps/web/tests/auth/RequireAuth.test.tsx` (`/summary` is wrapped in `RequireAuth`) | |
| G9 | `apps/web/tests/entries/EntryBox.test.tsx` (saving: the saved message has no link) | Checked by reading the page, not by its own assertion. |

- api: `.venv\Scripts\python -m pytest -q` (in `apps/api`)
- web: `npx jest --ci` (in `apps/web`)

**Pass:** every row gives the expected result, both suites pass, and the api coverage gate (80%) holds.
