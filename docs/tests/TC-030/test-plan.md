# TC-030: Save reviewed entries as expense records (REQ-278 acceptance)

Requirement: REQ-278 (approved) · Work item: WI-048 (implemented) · Applications: api (primary), web

## Scope
Every acceptance criterion of REQ-278 and every product-owner answer recorded in WI-048's impl.md (22 Nov 2026). Tested through `POST /entries/save`, the `expenses` table (migration 0004) and the Save flow of the web entry box.

Out of scope:
- Expanding and splitting entries: TC-014 and TC-029 cover them.
- A list of saved entries (q3: it comes with REQ-280/REQ-281).
- The monthly summary (REQ-279).

## Setup
- **Database:** a SQLite file built from every migration in `apps/api/migrations` (0001 to 0004), with two users: Asha `11111111-1111-1111-1111-111111111111` and Ravi `22222222-2222-2222-2222-222222222222`. Foreign keys are on (`PRAGMA foreign_keys = ON`), as on every app connection.
- **Today:** 12 Nov 2026 in IST. The API's clock (`today_ist`) is pinned to this date, except where a row says otherwise.
- **Signed in:** each request carries `Authorization: Bearer <token>`, an HS256 token signed with `JWT_SECRET` whose `sub` is the user's id. In the browser, sign in at `/sign-in`.
- **Review:** `POST /entries/expand-all {"text": T}` returns `results` (TC-029). A save sends that list back unchanged unless a row says otherwise: `POST /entries/save {"text": T, "reviewed": results}`.
- **Save answer:** `200 {"ok", "error", "saved", "ids", "failed"}`. `failed` lists the entries not saved, each with its error. A refused save is `ok: false` with `saved: 0` and nothing written.
- **Records:** read with `SELECT typed_text, merchant_code, category_code, amount_paise, spent_on, note FROM expenses WHERE user_id = ?`.

`REVIEW_CHANGED` below stands for the exact message `The entries changed since the review. Press Expand to review them again.`

## A. The sample text box (REQ-278 acceptance 1 and 2)
Text box T:
```
F 250; SWG 340 yd
X 100
UBR 180 12/11 airport
```
Asha reviews T and saves it.

| # | Check | Expected |
|---|---|---|
| A1 | Save answer | `ok: true`, `saved: 3`, three 36-character ids, `failed: [{"typed": "X 100", "ok": false, "entry": null, "error": "Unknown code \"X\"."}]` |
| A2 | Asha's records | exactly the three rows below, and no row for `X 100` |

| typed_text | merchant_code | category_code | amount_paise | spent_on | note |
|---|---|---|---|---|---|
| `F 250` | NULL | F | 25000 | 2026-11-12 | NULL |
| `SWG 340 yd` | SWG | F | 34000 | 2026-11-11 | NULL |
| `UBR 180 12/11 airport` | UBR | T | 18000 | 2026-11-12 | airport |

These are the values the review showed: merchant, category, amount (250.00 = 25000 paise), date and note.

| # | Check | Expected |
|---|---|---|
| A3 | `created_at`, `updated_at` of each row | set by the database, ISO UTC ending in `Z`, equal on a new row |

## B. Errors and partial saves (q1)
| # | Text box (reviewed, then saved) | Expected |
|---|---|---|
| B1 | `X 1; F` (only errors) | `ok: true`, `saved: 0`, `failed` = `X 1` (`Unknown code "X".`), `F` (`Amount is missing.`); no rows |
| B2 | `R 1.5k` (no errors) | `ok: true`, `saved: 1`, `failed: []`; one row R, 150000, 2026-11-12 |

## C. Ownership (REQ-278 acceptance 3)
| # | Steps | Expected |
|---|---|---|
| C1 | Asha saves `F 250`; Ravi saves `R 1.5k` | Asha's rows: only `F 250`. Ravi's rows: only `R 1.5k`. |
| C2 | Save with a valid token whose `sub` has no users row | 401 `{"error": "unauthorized"}`; no rows |
| C3 | Save without an Authorization header | 401 |

## D. Nothing is saved before Save (REQ-278 acceptance 4)
| # | Steps | Expected |
|---|---|---|
| D1 | `POST /entries/expand-all` with T, then `POST /entries/expand` with `F 250` | the `expenses` table stays empty |

## E. The review is checked again at save time (q5)
Each row saves T with a changed `reviewed` list.

| # | Change to `reviewed` | Expected |
|---|---|---|
| E1 | first entry `amount_paise` 25000 → 26000 | `ok: false`, `error: REVIEW_CHANGED`, `saved: 0`; no rows |
| E2 | first entry `date` → 2026-11-10 | same as E1 |
| E3 | first entry `note` → `lunch` | same as E1 |
| E4 | last entry left out | same as E1 |
| E5 | first two entries swapped | same as E1 |
| E6 | the `X 100` error changed to `Amount is missing.` | same as E1 |
| E7 | `SWG 340 yd\nF 100 td` reviewed on 12 Nov, saved with the clock on 13 Nov (after midnight IST) | same as E1: the dates have shifted |
| E8 | 21 entries `F 1` with an empty review | `ok: false`, `error: "Too many entries (max 20)."`; no rows |

## F. Duplicates (q4)
| # | Steps | Expected |
|---|---|---|
| F1 | Asha reviews and saves T twice | six rows: two of each saved entry. No duplicate check. |

## G. The expenses table (q6, migration 0004)
Insert rows directly with foreign keys on.

| # | Insert | Expected |
|---|---|---|
| G1 | category F with merchant SWG; category F with no merchant | accepted |
| G2 | category T with merchant SWG (a merchant with another category) | rejected (IntegrityError) |
| G3 | unknown category `Z` | rejected |
| G4 | `amount_paise` 0, or 1.5 | rejected |
| G5 | `spent_on` `2026-02-30`, or `12/11/2026` | rejected |
| G6 | unknown `user_id` | rejected |
| G7 | delete Asha's users row | her expenses are deleted too (cascade) |

## H. Guards (API)
| # | Request (signed in) | Expected |
|---|---|---|
| H1 | `{"text": "F 250"}` (no `reviewed`) | 422, `error: "validation-error"` |
| H2 | `{"text": "", "reviewed": []}` or `{"text": " ; ", "reviewed": []}` | 422 |
| H3 | a text over 10,500 characters | 422 |

## I. Save in the entry box (web, `/entries`)
Precondition: the web app runs with `API_PROXY_TARGET` pointing at the API, the local database has migration 0004, and the tester is signed in at `/sign-in` (demo user from `python -m scripts.seed_users`). Today is the real IST date. If today is before 12 Nov of the current year, `UBR 180 12/11 airport` is an error, and the counts in I3 change to 2 saved, 2 not saved.

| # | Steps | Expected |
|---|---|---|
| I1 | Open `/entries` and type T. | Save is disabled: there is no review yet. Nothing is posted to `/entries/save`. |
| I2 | Press Expand. | The review table shows four rows (TC-029). Save is enabled. |
| I3 | Press Save. | Save shows "Saving" and is disabled while it runs. Then `3 entries saved, 1 not saved.` appears, with `X 100: Error: Unknown code "X".` under it. The text box holds only `X 100`, the review table is gone, and Save is disabled. |
| I4 | Replace the box with `F 250; R 1.5k`, Expand, Save. | `2 entries saved.` and the text box is empty. |
| I5 | Expand T, then add a line `F 10` without pressing Expand. | Save is disabled: the text no longer matches the review. |
| I6 | Expand `X 100` alone. | Save is disabled: no entry is valid. |
| I7 | Expand a text before midnight IST and press Save after it (or use the component test). | `Error: The entries changed since the review. Press Expand to review them again.` The review and the text stay. Pressing Expand fetches a fresh review, and the message goes away. |
| I8 | Press Save while signed out (expired token). | `Could not save the entries: unauthorized` (or the sign-in redirect of REQ-275). |

## Automated coverage
| Rows | Automated in | Gap |
|---|---|---|
| A1, A2, A3, B1, C1, E1 to E8, F1, G1 to G7 | `apps/api/tests/entries/test_save.py` (service and migration, database built from 0001 to 0004) | B2 is covered by A2's per-entry values, not by its own test. |
| A1, C2, C3, D1, E1, H1 to H3 through the API | `apps/api/tests/entries/test_routes.py` (`test_save_*`, `test_expanding_saves_nothing`) | |
| Code table with category codes | `apps/api/tests/entries/test_codes.py` | |
| I1 to I8 | `apps/web/tests/entries/EntryBox.test.tsx` (`saving (REQ-278)`) and `useExpand.test.ts` (`saveEntries`), with a fake API client | I3 and I4 against a live API are manual steps. I7 live needs a midnight crossing, so the component test stands in for it. |

- api: `.venv\Scripts\python -m pytest -q` (in `apps/api`)
- web: `npx jest --ci` (in `apps/web`)

**Pass:** every row gives the expected result, both suites pass, and the api coverage gate (80%) holds.
