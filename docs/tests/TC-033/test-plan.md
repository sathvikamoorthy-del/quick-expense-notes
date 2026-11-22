# TC-033: Edit a saved entry (REQ-280 acceptance)

Requirement: REQ-280 (approved) · Work item: WI-052 (implemented) · Applications: api (primary), web

## Scope
Every acceptance criterion of REQ-280 and every product-owner answer recorded in WI-052's impl.md (22 Nov 2026, including the two saved-day details). Tested through `GET /entries`, `PUT /entries/{id}`, the monthly summary after an edit, and the `/saved-entries` page.

Out of scope:
- Saving new entries (TC-030).
- The summary's own rules (TC-031).
- Deleting entries (REQ-281).

## Setup
- **Database:** a SQLite file built from every migration in `apps/api/migrations` (0001 to 0004), with two users: Asha `11111111-1111-1111-1111-111111111111` and Ravi `22222222-2222-2222-2222-222222222222`.
- **Today:** 12 Nov 2026 in IST, unless a row says otherwise. The API's clock (`today_ist`) is pinned.
- **Signed in:** each request carries `Authorization: Bearer <token>` with the user's id as `sub`. In the browser, sign in at `/sign-in`.
- **Saved entries:** inserted directly with a known `created_at` (ISO UTC), or saved through the app (TC-030).
  - **UBR:** typed `UBR 180 12/11 airport`, saved 12 Nov 2026 at 10:00 IST (`2026-11-12T04:30:00.000Z`). Stored as Uber, Travel, 18000 paise, `2026-11-12`, note `airport`.
  - **SWG:** typed `SWG 340 yd`, saved at the same time. Stored as Swiggy, Food, 34000, `2026-11-11`.
- **Edit:** `PUT /entries/{id}` with `{"text": "<short entry>"}`. The answer is `200 {ok, error, entry}`; `entry` holds `{id, typed, code, merchant, category, amount, amount_paise, date, note}`.
- **List:** `GET /entries?month=YYYY-MM`, or no `month` for the current IST month. The answer is `{month, current_month, entries}`.
- **Stored row:** read with `SELECT typed_text, merchant_code, category_code, amount_paise, spent_on, note, created_at, updated_at, user_id FROM expenses WHERE id = ?`.

## A. An edit replaces the entry (REQ-280 acceptance 1; q1, q6, q7)
| # | Steps | Expected |
|---|---|---|
| A1 | Edit UBR to `UBR 220 12/11 airport` | `ok: true`; `entry.amount` `"220.00"`, with the same `id`. The stored row has `typed_text` `UBR 220 12/11 airport`, UBR, T, 22000, `2026-11-12`, note `airport`. |
| A2 | Same row after A1 | The same `id`, `user_id` and `created_at`. `updated_at` is later than `created_at`, ISO UTC ending in `Z`. |
| A3 | `GET /entries` after A1 | The UBR entry shows `typed` `UBR 220 12/11 airport` and `amount` `220.00` at once. The list has the header `Cache-Control: no-store`. |
| A4 | Edit a category entry `F 250` to `AMZ 250` | merchant_code `AMZ`, category_code `S` |
| A5 | Then edit it to `T 250 cab` | merchant_code NULL, category_code `T`, note `cab` |

## B. Dates in an edit (q3, 3a, 3b)
| # | Entry and edit | Today | Expected stored `spent_on` |
|---|---|---|---|
| B1 | SWG: edit to `SWG 360 yd` | 19 Nov 2026 | `2026-11-11`. `yd` counts from the saved day (12 Nov), so the date is kept. |
| B2 | SWG: edit to `F 99` (no date) | 19 Nov 2026 | `2026-11-12`, the saved day |
| B3 | An entry saved 5 Nov (`2026-11-05T04:30:00.000Z`): edit to `F 100 10/11` | 12 Nov 2026 | `2026-11-10`. It is after the saved day but not after today, so it is accepted. |
| B4 | Same entry: edit to `F 100 20/11` | 12 Nov 2026 | refused, `Date cannot be in the future.`; the row is unchanged |
| B5 | An entry saved at `2026-11-12T19:00:00.000Z` (00:30 IST on 13 Nov): edit to `F 1 td` | 13 Nov 2026 | `2026-11-13`. The saved day is the IST date. |
| B6 | An entry saved on 31 Dec 2025: edit to `F 1 30/12` | 12 Nov 2026 | `2025-12-30`. `dd/mm` takes the saved day's year. |

## C. An invalid edit is refused and changes nothing (REQ-280 acceptance 3; q2)
Each row edits UBR. Expected: `200 {"ok": false, "error": "<message>", "entry": null}`, and the stored row is exactly as before.

| # | Edit text | `error` |
|---|---|---|
| C1 | `X 100` | Unknown code "X". |
| C2 | `F` | Amount is missing. |
| C3 | `F -5` | Amount must be greater than 0. |
| C4 | `F 1.555` | Amount must have at most 2 decimals. |
| C5 | `F 100 32/13` | Date is not valid. |
| C6 | `F 1; F 2` or `F 1` + new line + `F 2` | Type one entry only. |
| C7 | `""` or `"   "` | 422, `error: "validation-error"` (not a rule answer) |

## D. Own entries only (REQ-280 acceptance 4)
| # | Steps | Expected |
|---|---|---|
| D1 | Ravi edits Asha's UBR | 404 `{"error": "not-found"}`; Asha's row is unchanged |
| D2 | Asha edits an id that does not exist | 404 `not-found` |
| D3 | Ravi lists November | only Ravi's entries; Asha's are not shown |
| D4 | `GET /entries` or `PUT /entries/{id}` without a token | 401 |

## E. The summary follows the edit (REQ-280 acceptance 2)
| # | Steps | Expected |
|---|---|---|
| E1 | Asha has UBR and SWG. Open `/summary?month=2026-11`. | grand total 520.00 |
| E2 | Edit UBR to `UBR 220 12/11 airport`, then open November again at once | grand total 560.00 (Travel 220.00) |
| E3 | Edit UBR to `UBR 180 30/10 airport` (moves it to October) | November: Food 340.00 only, grand total 340.00. October: Travel 180.00. |

## F. The saved-entries list (q4, q5)
| # | Request | Expected |
|---|---|---|
| F1 | Entries dated 31 Oct, 1 Nov, 12 Nov (saved 10:00) and 12 Nov (saved 11:00), and 1 Dec; `GET /entries?month=2026-11` | Only November, in the order: 12 Nov (11:00), 12 Nov (10:00), 1 Nov |
| F2 | `GET /entries` with no `month` | `month` and `current_month` are `"2026-11"` |
| F3 | `month=2026-12`, `2026-13`, `nov` | 422 `validation-error` |

## G. The `/saved-entries` page (web)
Precondition: the web app runs with `API_PROXY_TARGET` pointing at the API, the local database has migration 0004, and the tester is signed in with some saved entries. Today is the real IST date.

| # | Steps | Expected |
|---|---|---|
| G1 | On `/entries` or `/summary`, click "Saved entries". | `/saved-entries` opens on the current month, headed like `November 2026`. The table has `Typed · Merchant · Category · Amount · Date · Note` and an Edit button per row, newest date first. |
| G2 | Click Edit on a row. | The row becomes a text box pre-filled with what was typed, with Save and Cancel. The other Edit buttons are disabled. |
| G3 | Change the amount and press Save. | The row shows the new values, and the text box is gone. |
| G4 | Edit to `X 100`, press Save. | `Error: Unknown code "X".` under the text box. The text stays, and the entry is unchanged. |
| G5 | Edit, change the text, press Cancel. | The row is back unchanged, and nothing is sent. |
| G6 | Edit a row to a `dd/mm` date in the previous month, press Save. | `The entry moved to <Month Year>.` and the row leaves this month's list. Previous shows it. |
| G7 | Previous and Next. | They work as on the summary page. Next is disabled on the current month, and an empty month shows `No saved entries in this month.` |
| G8 | Links. | "Enter expenses" goes to `/entries`, and "Monthly summary" to `/summary`. |
| G9 | Sign out, open `/saved-entries`. | The sign-in screen. |

## Automated coverage
| Rows | Automated in | Gap |
|---|---|---|
| A1, A2, A4, A5, B1 to B4, C1 to C6, D1, D2, E3, F1 | `apps/api/tests/entries/test_edit.py` (database built from 0001 to 0004) | E1 and E2 are covered through the routes, E3 in the service. |
| B5, B6 | `test_edit.py` (`saved_day`), `apps/api/tests/entries/test_expand.py` (reference-day cases) | B5 and B6 are not run end to end as edits. |
| A1, A3, C1, C7, D1 to D4, E2, F2, F3 through the API | `apps/api/tests/entries/test_routes.py` | |
| G1 to G8 | `apps/web/tests/saved/SavedEntries.test.tsx`, `useSavedEntries.test.ts`, and the link checks in `EntryBox.test.tsx` and `MonthlySummary.test.tsx` (fake API client) | G3 and G6 against a live API are manual steps. |
| G9 | `apps/web/tests/auth/RequireAuth.test.tsx` (`/saved-entries` is wrapped in `RequireAuth`) | |

- api: `.venv\Scripts\python -m pytest -q` (in `apps/api`)
- web: `npx jest --ci` (in `apps/web`)

**Pass:** every row gives the expected result, both suites pass, and the api coverage gate (80%) holds.
