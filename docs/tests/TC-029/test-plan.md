# TC-029: Expand several entries from one text box (REQ-277 acceptance)

Requirement: REQ-277 (approved) · Work item: WI-047 (implemented) · Applications: api (primary), web

## Scope
Every acceptance criterion of REQ-277 and every product-owner answer recorded in WI-047's impl.md (22 Nov 2026), tested through `POST /entries/expand-all` and the web entry box that shows the results.

Out of scope:
- The expansion rules of one entry. TC-014 covers them (REQ-276); here they're only checked through the sample text box.
- Saving (REQ-278).
- Sign-in itself (REQ-275).

## Setup
- **Database:** a SQLite file built from `apps/api/migrations/0001_db_design.sql` and `0002_seed_reference.sql` (8 categories, 8 merchants).
- **Today:** 12 Nov 2026 in IST. The API's clock (`today_ist`) is pinned to this date.
- **Signed in:** each request carries `Authorization: Bearer <token>`, an HS256 token signed with the API's `JWT_SECRET`, with `sub` and `exp`. In the browser, sign in at `/sign-in` (REQ-275).
- **Request:** `POST /entries/expand-all` with body `{"text": "<text box>"}`. In the text box, `\n` is a new line.
- **Accepted answer:** `200 {"ok": true, "error": null, "results": [...]}`, with one item per entry in typed order. Each item is `{typed, ok, entry, error}`:
  - `typed` is the entry trimmed, with inner spaces as typed.
  - `entry` has the REQ-276 fields `{code, merchant, category, amount, amount_paise, date, note}`, or `null` for an entry with an error.
- **Rejected answer:** `200 {"ok": false, "error": "Too many entries (max 20).", "results": []}`.

In the tables, merchant "-" means `null`, an empty note means `null`, and ␣ is a space.

## A. The sample text box (03-sample-entries.md, REQ-277 acceptance 1)
Text box:
```
F 250; SWG 340 yd
X 100
UBR 180 12/11 airport
```
| # | typed | ok | Merchant | Category | Amount | amount_paise | Date | Note | error |
|---|---|---|---|---|---|---|---|---|---|
| A1 | `F 250` | true | - | Food | 250.00 | 25000 | 2026-11-12 | | |
| A2 | `SWG 340 yd` | true | Swiggy | Food | 340.00 | 34000 | 2026-11-11 | | |
| A3 | `X 100` | false | | | | | | | Unknown code "X". |
| A4 | `UBR 180 12/11 airport` | true | Uber | Travel | 180.00 | 18000 | 2026-11-12 | airport | |

Expected: `ok: true` and exactly four results in this order: three expanded entries and one error. A3 has `entry: null` and the message exactly as shown, including the quotes and the full stop.

## B. Separators (REQ-277 acceptance 2)
| # | Text box | Expected `typed` values, in order |
|---|---|---|
| B1 | `F 250\nR 1.5k\nNFX 649` (new lines only) | `F 250`, `R 1.5k`, `NFX 649` |
| B2 | `F 250;R 1.5k;NFX 649` (semicolons only) | the same |
| B3 | `F 250; R 1.5k\nNFX 649` (mixed) | the same |
| B4 | `F 250\r\nR 1.5k\r\nNFX 649` (Windows line ends) | the same |
| B5 | `F 100 lunch; with team` | `F 100 lunch` (note `lunch`), then `with team` with error `Unknown code "with".`. A `;` always separates entries, even inside a note. |

## C. Errors stop only their own entry (REQ-277 acceptance 3)
| # | Text box | Expected results, in order |
|---|---|---|
| C1 | `X 1\nF 250\nF\nSWG 340\nF 100 20/11` | error `Unknown code "X".`; 250.00; error `Amount is missing.`; 340.00; error `Date cannot be in the future.` |
| C2 | `F 250\nX 100` (error last) | 250.00; error `Unknown code "X".` |

Expected: each entry has its own single REQ-276 error, and the entries before and after it are still expanded.

## D. Empty parts are skipped (product owner, q1)
| # | Text box | Expected |
|---|---|---|
| D1 | `F 250;;` | one result, `F 250` |
| D2 | `;F 250` | one result, `F 250` |
| D3 | `\n\nF 250\n\n` | one result, `F 250` |
| D4 | `␣␣;␣␣F 250␣␣;␣␣\n␣␣` | one result, `F 250` |
| D5 | `␣␣APL 420 td␣␣fever tablets␣;␣` | one result, `typed` = `APL 420 td␣␣fever tablets` (trimmed; inner spaces kept) |

No result row appears for an empty part, and no error.

## E. The 20-entry limit (product owner, q2)
| # | Text box | Expected |
|---|---|---|
| E1 | 20 entries `F 1`, separated by `;` | `ok: true`, 20 results |
| E2 | 21 entries `F 1`, separated by new lines | `ok: false`, `error: "Too many entries (max 20)."`, `results: []`. No entry is expanded. |
| E3 | 20 entries `F 1` with `;;\n` between them and `;;;\n\n` at the end | `ok: true`, 20 results: empty parts don't count toward the limit |
| E4 | 21 entries, one of them `X 100` | `ok: false`, the too-many message: the limit is checked before any entry is expanded |

## F. Guards (API)
| # | Request | Expected |
|---|---|---|
| F1 | `{"text": "F 250"}` without an Authorization header | 401 `{"error": "unauthorized"}` |
| F2 | the same, with an expired or wrongly signed token | 401 `{"error": "unauthorized"}` |
| F3 | `{}`, `{"text": ""}`, or `{"text": "␣␣\n␣;␣;;␣"}` (no entries) | 422, `error: "validation-error"` |
| F4 | a text over 10,500 characters (e.g. `F 1;` × 3000) | 422, `error: "validation-error"`. This is a technical cap, not the too-many message. |
| F5 | `POST /entries/expand` with `{"text": "SWG 340 yd"}` | unchanged single-entry answer (q4: the old endpoint is kept) |

## G. Entry box (web, `/entries`)
Precondition: the web app runs with `API_PROXY_TARGET` pointing at the API, and the tester is signed in at `/sign-in` (demo user seeded by `python -m scripts.seed_users`). Today is the real IST date, so dates in G2 follow today rather than 12 Nov 2026.

| # | Steps | Expected |
|---|---|---|
| G1 | Open `/entries`. | A multi-line "Short entries" box and an "Expand" button. The button is disabled while the box is empty or holds only spaces, new lines and `;`. |
| G2 | Type the section A text box. Don't press anything yet. | Nothing is sent and no results show: results appear only on Expand (q3). |
| G3 | Press Expand. | "Expanding…" while waiting, then a table with columns `# · Typed · Merchant · Category · Amount · Date · Note` and four rows in typed order: 1 `F 250` - Food 250.00; 2 `SWG 340 yd` Swiggy Food 340.00 (yesterday); 3 `X 100` `Error: Unknown code "X".`; 4 `UBR 180 12/11 airport` Uber Travel 180.00 airport. Row 4's date is 12 Nov 2026; if today is earlier in the year than 12 Nov, row 4 shows `Error: Date cannot be in the future.` instead. |
| G4 | Type 21 lines of `F 1`, press Expand. | `Error: Too many entries (max 20).` as an alert, and no table. |
| G5 | Sign out, open `/entries`. | Redirected to sign-in (REQ-275). The entry box isn't reachable without a session. |

## Automated coverage
| Rows | Automated in | Gap |
|---|---|---|
| A, B1 to B4, C1, D1 to D5, E1 to E3 | `apps/api/tests/entries/test_batch.py` (pure, today pinned) | B5, C2 and E4 are not automated. |
| A, E2, F1, F3, F4 through the API | `apps/api/tests/entries/test_routes.py` (`test_expand_all_*`), with the database built from the migrations | |
| F2 | `apps/api/tests/modules/jwt-auth/contract/test_middleware.py`: bad tokens are rejected on every route | Not repeated on `/entries/expand-all` itself. |
| F5 | `apps/api/tests/entries/test_routes.py` (existing `/entries/expand` tests) | |
| G1 to G4 | `apps/web/tests/entries/EntryBox.test.tsx` and `useExpand.test.ts` (fake API client) | G3 against a live API is a manual step. |
| G5 | `apps/web/tests/auth/RequireAuth.test.tsx` | |

- api: `.venv\Scripts\python -m pytest -q` (in `apps/api`)
- web: `npx jest --ci` (in `apps/web`)

**Pass:** every row gives the expected result, both suites pass, and the api coverage gate (80%) holds.
