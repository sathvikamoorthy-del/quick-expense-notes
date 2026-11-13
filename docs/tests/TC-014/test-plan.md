# TC-014: Expand one short entry (REQ-276 acceptance)

Requirement: REQ-276 (approved) · Work item: WI-029 (implemented) · Applications: api (primary), web

## Scope
Every acceptance criterion of REQ-276, through the API that holds the rules (`POST /entries/expand`), plus the guards around it and the web entry box that shows the result. Saving (REQ-278), several entries in one box (REQ-277) and sign-in itself (REQ-275) are out of scope.

## Setup
- **Database:** a SQLite file built from `apps/api/migrations/0001_db_design.sql` and `0002_seed_reference.sql` (8 categories, 8 merchants).
- **Today:** 12 Nov 2026 in IST. The API's clock (`today_ist`) is pinned to this date for A and B, and set as stated in C.
- **Signed in:** a request carries `Authorization: Bearer <token>`, an HS256 token signed with the API's `JWT_SECRET`, with `sub` and `exp`. REQ-275 has no sign-in screen yet, so the tester makes this token.
- **Request:** `POST /entries/expand` with body `{"text": "<typed>"}`. A success is `200 {"ok": true, "entry": {code, merchant, category, amount, amount_paise, date, note}, "error": null}`; a rule error is `200 {"ok": false, "entry": null, "error": "<message>"}`.

In the tables, merchant "-" means `null`, and an empty note means `null`. Dates are shown as the API returns them (`YYYY-MM-DD`).

## A. Sample entries that work (03-sample-entries.md)
| # | Typed | Merchant | Category | Amount | amount_paise | Date | Note |
|---|---|---|---|---|---|---|---|
| A1 | `F 250` | - | Food | 250.00 | 25000 | 2026-11-12 | |
| A2 | `SWG 340 yd` | Swiggy | Food | 340.00 | 34000 | 2026-11-11 | |
| A3 | `UBR 180 12/11 airport` | Uber | Travel | 180.00 | 18000 | 2026-11-12 | airport |
| A4 | `R 1.5k` | - | Rent | 1500.00 | 150000 | 2026-11-12 | |
| A5 | `NFX 649` | Netflix | Entertainment | 649.00 | 64900 | 2026-11-12 | |
| A6 | `APL 420 td fever tablets` | Apollo Pharmacy | Health | 420.00 | 42000 | 2026-11-12 | fever tablets |
| A7 | `S 2k td shoes` | - | Shopping | 2000.00 | 200000 | 2026-11-12 | shoes |
| A8 | `AMZ 799.50` | Amazon | Shopping | 799.50 | 79950 | 2026-11-12 | |

Expected: `ok: true` and every field exactly as in the row. `code` is the upper-case code (F, SWG, UBR, R, NFX, APL, S, AMZ).

## B. Sample entries that fail (03-sample-entries.md)
| # | Typed | Expected `error` (exact text) |
|---|---|---|
| B1 | `X 100` | Unknown code "X". |
| B2 | `F` | Amount is missing. |
| B3 | `F -50` | Amount must be greater than 0. |
| B4 | `F 100 32/13` | Date is not valid. |
| B5 | `F 100 20/11` | Date cannot be in the future. |

Expected: `ok: false`, `entry: null`, and the message exactly as shown, including the full stop and the quotes.

## C. Answered questions (REQ-276, product owner, 13 Nov 2026)
| # | Typed | Expected |
|---|---|---|
| C1 | `swg 340` | Swiggy, Food, 340.00, 2026-11-12; `code` is `SWG` |
| C2 | `F 1.5K YD` | -, Food, 1500.00, 2026-11-11 |
| C3 | `F 100 5/11` | -, Food, 100.00, 2026-11-05 |
| C4 | `␣␣SWG␣␣␣340␣␣␣yd␣␣` (␣ = space) | the same entry as A2 |
| C5 | `F 250.555` | error: Amount must have at most 2 decimals. |
| C6 | `F 1.2345k` | error: Amount must have at most 2 decimals. (decimals counted as typed, before `k`) |
| C7 | `F -1.555` | error: Amount must be greater than 0. (checked before the decimals) |
| C8 | `F 100 td`, with the clock at 00:30 IST on 13 Nov 2026 (19:00 UTC on 12 Nov) | date 2026-11-13, whatever the server's own time zone |
| C9 | `APL 420 td fever␣␣tablets` | note `fever␣␣tablets`: spaces inside the note are kept as typed |

## D. Error order (first failure wins)
| # | Typed | Expected `error` |
|---|---|---|
| D1 | `X -1 32/13` | Unknown code "X". |
| D2 | `F 0 32/13` | Amount must be greater than 0. |
| D3 | `F 1.555 32/13` | Amount must have at most 2 decimals. |
| D4 | `F 100 31/2` | Date is not valid. |

## E. Guards (API)
| # | Request | Expected |
|---|---|---|
| E1 | `{"text": "F 250"}` without an Authorization header | 401 `{"error": "unauthorized"}` |
| E2 | the same, with an expired or wrongly signed token | 401 `{"error": "unauthorized"}` |
| E3 | `{}`, `{"text": ""}`, `{"text": "   "}`, or a text over 500 characters (signed in) | 422 with `error: "validation-error"`; the input is not echoed back |

## F. Entry box (web, `/entries`)
Precondition: the web app runs with `API_PROXY_TARGET` pointing at the API, and the client holds a valid token (`setAuthToken`). Until REQ-275 exists, a tester sets the token in the browser console or uses the component tests.

| # | Steps | Expected |
|---|---|---|
| F1 | Open `/entries`. | One "Short entry" input and an "Expand" button, disabled while the input is empty or only spaces. |
| F2 | Type `F 100 5/11 groceries`, press Expand. | "Expanding…" while waiting, then a table: Merchant `-`, Category `Food`, Amount `100.00`, Date `5 Nov 2026`, Note `groceries`. |
| F3 | Type `X 100`, press Expand. | `Error: Unknown code "X".` and no table. |
| F4 | Press Expand with no token. | `Could not expand the entry: unauthorized`. |
| F5 | Open `/`. | "Page not found": the entry box lives at `/entries` (decision in WI-029). |

## Automated coverage
| Rows | Automated in | Gap |
|---|---|---|
| A, B, C, D | `apps/api/tests/entries/test_expand.py` (parser, today pinned); `amount_paise` of A1 to A8 in `test_sample_entries_that_work_in_paise` | |
| A, B through the API | `apps/api/tests/entries/test_routes.py`: one success, one rule error and a category code, with the database built from the migrations | |
| Code table | `apps/api/tests/entries/test_codes.py`: 16 codes read from the seeded tables | |
| E1, E3 | `apps/api/tests/entries/test_routes.py` | |
| E2 | `apps/api/tests/modules/jwt-auth/contract/test_middleware.py`: bad tokens are rejected for every route | Not repeated on `/entries/expand` itself. |
| F1 to F4 | `apps/web/tests/entries/EntryBox.test.tsx` and `useExpand.test.ts` (fake API client) | Not run against a live API until REQ-275 provides tokens. |
| F5 | `apps/web/tests/modules/react-vite/contract/app.test.tsx` and `main.test.tsx` | |

- api: `.venv\Scripts\python -m pytest -q` (in `apps/api`)
- web: `npx jest --ci` (in `apps/web`)

**Pass:** every row gives the expected result, both suites pass, and the api coverage gate (80%) holds.
