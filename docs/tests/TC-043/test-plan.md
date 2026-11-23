# TC-043: Delete a saved entry (REQ-281 acceptance)

Requirement: REQ-281 (approved) · Work item: WI-061 (implemented) · Applications: api (primary), web

## Scope
Every acceptance criterion of REQ-281 and every product-owner answer recorded in WI-061's impl.md (23 Nov 2026). Tested through `DELETE /entries/{id}`, the saved-entries list and the monthly summary after a delete, and the Delete flow of `/saved-entries`.

Out of scope:
- Saving entries (TC-030), the summary's own rules (TC-031), and editing entries (TC-033).

## Setup
- **Database:** a SQLite file built from every migration in `apps/api/migrations` (0001 to 0004), with two users: Asha `11111111-1111-1111-1111-111111111111` and Ravi `22222222-2222-2222-2222-222222222222`.
- **Today:** 12 Nov 2026 in IST, unless a row says otherwise. The API's clock (`today_ist`) is pinned.
- **Signed in:** each request carries `Authorization: Bearer <token>` with the user's id as `sub`. In the browser, sign in at `/sign-in`.
- **Asha's November entries**, inserted directly or saved through the app (TC-030):
  - **UBR:** `UBR 180 12/11 airport` (Uber, Travel, 18000 paise, 2026-11-12, note `airport`)
  - **SWG:** `SWG 340 yd` (Swiggy, Food, 34000, 2026-11-11)
  - **NFX:** `NFX 649` (Netflix, Entertainment, 64900, 2026-11-12)
- **Delete:** `DELETE /entries/{id}`. The answer is `204` with no body, or `404 {"error": "not-found"}`.
- **List and summary:** `GET /entries?month=2026-11` and `GET /summary?month=2026-11`.
- **Stored row:** `SELECT count(*) FROM expenses WHERE id = ?`.

## A. A delete removes the entry (REQ-281 acceptance 1; q2)
| # | Steps | Expected |
|---|---|---|
| A1 | Asha deletes UBR | `204` with an empty body |
| A2 | The stored row after A1 | gone: count 0. It is a hard delete, with no soft-delete flag (db_design). |
| A3 | `GET /entries?month=2026-11` after A1 | SWG and NFX only. UBR is no longer among the saved entries. |
| A4 | Delete UBR again | `404 not-found`. There is nothing to undo or restore. |

## B. The summary no longer counts it (REQ-281 acceptance 2)
| # | Steps | Expected |
|---|---|---|
| B1 | Before any delete, Asha opens November | Food 340.00, Travel 180.00, Entertainment 649.00. Grand total 1169.00. |
| B2 | Delete NFX, then open November again at once | Food 340.00, Travel 180.00. Grand total 520.00. Entertainment is no longer listed, because it has no entries left. |
| B3 | Delete UBR as well | Food 340.00 only. Grand total 340.00. Travel disappears. |
| B4 | Delete SWG as well | `categories: []`, grand total 0.00. The page shows `No expenses in this month.` (WI-049 q3). |

B1 to B3 follow the walkthrough's note-to-summary example, where deleting Netflix makes Entertainment disappear.

## C. Own entries only (REQ-281 acceptance 3)
| # | Steps | Expected |
|---|---|---|
| C1 | Ravi deletes Asha's UBR | `404 not-found`; Asha's row is still there, and her list and summary are unchanged |
| C2 | Asha deletes an id that does not exist | `404 not-found` |
| C3 | `DELETE /entries/{id}` without a token | `401` |

## D. The Delete flow on `/saved-entries` (web; q1, q3)
Precondition: the web app runs with `API_PROXY_TARGET` pointing at the API, the local database has migration 0004, and the tester is signed in with at least three saved entries in the current month.

| # | Steps | Expected |
|---|---|---|
| D1 | Open `/saved-entries`. | Every row has Edit and Delete. |
| D2 | Click Delete on a row. | That row shows its typed text and `Delete this entry?`, with Delete and Cancel. The other rows' Edit and Delete buttons are disabled. Nothing is deleted yet. |
| D3 | Press Cancel. | The row is back unchanged, and no delete request is sent. |
| D4 | Delete, then Delete in the confirmation. | Delete shows "Deleting" while running. The row disappears, the note `Entry deleted.` is shown, and the other rows stay. |
| D5 | Open `/summary` for the same month. | The deleted amount is no longer counted. A category with no entries left is gone. |
| D6 | A delete that fails (e.g. signed out in another tab). | The confirmation stays, with `Could not delete the entry: <error>` under it. |
| D7 | Open Edit on one row. | The Delete buttons of the other rows are disabled: only one row is open at a time. |
| D8 | After a delete. | There is no Undo anywhere (q2). |

## Automated coverage
| Rows | Automated in | Gap |
|---|---|---|
| A1 to A4, B2 (through the API), C1 to C3 | `apps/api/tests/entries/test_routes.py` (`test_deleting_*`, database built from 0001 to 0004) | B2 through the API uses F 250 and NFX 649; the totals 1169.00 and 520.00 come from the service test. |
| A2, A3, B1, B2, C1, C2 (service) | `apps/api/tests/entries/test_edit.py` (`test_a_delete_*`, `test_another_users_entry_*`, `test_deleting_the_only_entertainment_entry_*`) | B3 and B4 are not automated. |
| D1 to D4, D6, D7 | `apps/web/tests/saved/SavedEntries.test.tsx` (`deleting (REQ-281)`), `useSavedEntries.test.ts` (`deleteEntry`), with a fake API client | D4 and D5 against a live API are manual steps. D8 is checked by reading the page: there is no Undo control. |

- api: `.venv\Scripts\python -m pytest -q` (in `apps/api`)
- web: `npx jest --ci` (in `apps/web`)

**Pass:** every row gives the expected result, both suites pass, and the api coverage gate (80%) holds.
