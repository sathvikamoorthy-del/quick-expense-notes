# WI-061: Delete a saved entry

Applications: api (primary), web
Requirement: REQ-281 · Decision: DEC-315 · Feature: FEAT-1061
Builds on: WI-052 (`/saved-entries` list, `app.entries.edit`, `GET /entries`), WI-049 (`/summary`, never cached), WI-048 (`expenses`)

## Answered questions
Answered by the product owner on 23 Nov 2026 (KNM Q&A on WI-061):
1. **Confirmation:** yes, in place. Delete turns the row into a confirmation, `Delete this entry?`, with **Delete** and **Cancel**.
2. **Undo:** none. A delete is final, and the DB design uses hard delete.
3. **After a delete:** the row is gone and a short note says `Entry deleted.`

Settled before this work item, so not asked again:
- **Where the user deletes:** the saved-entries list at `/saved-entries` (WI-048 q3: the list comes with edit and delete; WI-052 built it).
- **What a delete does:** the row is removed from `expenses` (db_design.md: hard delete, no soft delete).

## Behaviour to implement
1. Each row of `/saved-entries` gets a **Delete** button next to Edit.
2. Delete turns that row into `Delete this entry?`, with **Delete** and **Cancel**. The row's typed text stays visible, so the user sees which entry it is.
   - Only one row is in edit or confirm mode at a time. While one is open, the other rows' Edit and Delete buttons are disabled, as for edits today.
   - Cancel restores the row, and nothing is sent.
3. Confirming sends the delete.
   - **Success:** the entry is no longer a record. The list reloads without it, and the note `Entry deleted.` is shown (q3).
   - **Failure:** the row stays in confirm mode with `Could not delete the entry: <error>` under it.
4. The monthly summary no longer counts the entry, and a category left with no entries in that month disappears (REQ-281 acceptance 2). `/summary` and `/entries` are never cached (WI-049, WI-052), so this shows at once.
5. Users can delete only their own entries. Another user's entry id, or an unknown id, gives 404 `not-found`, the same as edit (WI-052). Nothing is deleted.
6. There is no Undo (q2).

## Approach

### API (primary): apps/api
- `app/entries/edit.py` gains `async delete_entry(session, user_id, expense_id) -> bool`. It runs one `DELETE FROM expenses WHERE id = :id AND user_id = :user` and returns whether a row was removed. The module docstring is extended for REQ-281.
- **New route** `DELETE /entries/{expense_id}` in `app/entries/routes.py`. It stays thin, with `require_auth` and `get_session`.
  - 204 No Content when deleted.
  - 404 `not-found` when the user has no entry with that id.
- Regenerate `apps/api/openapi.json`.
- There is no database change: `expenses` already allows a hard delete, and nothing references an expense row.

### Web: apps/web
- Regenerate `src/api/schema.d.ts`.
- `src/saved/useSavedEntries.ts`: add `deleteEntry(id, client)`, which calls `DELETE /entries/{expense_id}`. It resolves on 204 and throws the API error code (or the status) otherwise.
- `src/saved/SavedEntries.tsx`:
  - a Delete button per row;
  - a confirm row showing the typed text, `Delete this entry?`, Delete (red), Cancel, and the error under it. Delete shows "Deleting" while running;
  - one open row at a time, shared with edit mode;
  - after a delete, the note `Entry deleted.` (`role="status"`) and a reload of the month.

  Starting an edit or a delete clears the note.

## Tests
API:
- `tests/entries/test_edit.py` (service):
  - Deleting removes the row, and `list_month` no longer shows it.
  - Deleting another user's entry or an unknown id returns False, and the row stays.
  - Deleting the only Entertainment entry removes Entertainment from that month's summary, and the grand total drops by its amount (REQ-281 acceptance 2, with the walkthrough's Netflix example).
- `tests/entries/test_routes.py`:
  - `DELETE /entries/{id}` gives 204, and the entry is gone from `GET /entries`. `GET /summary` drops it at once.
  - 404 for another user's or an unknown id, with nothing deleted.
  - 401 without a token.
  - A second delete of the same id gives 404.

Web:
- `tests/saved/useSavedEntries.test.ts`: `deleteEntry` sends `DELETE /entries/{id}`, resolves on 204, and throws `not-found` on 404 and the status on 500.
- `tests/saved/SavedEntries.test.tsx`:
  - Delete shows the confirmation for that row, and the other rows' buttons are disabled.
  - Cancel restores the row and sends nothing.
  - Confirming removes the row and shows `Entry deleted.`
  - A failed delete keeps the confirmation with the error.
  - An open edit disables the other rows' Delete buttons.

Run `pytest -q` in apps/api (all tests must pass before commit), plus `npx jest --ci` in apps/web.

## Files likely affected
- apps/api/app/entries/edit.py, apps/api/app/entries/routes.py
- apps/api/openapi.json
- apps/api/tests/entries/test_edit.py, apps/api/tests/entries/test_routes.py
- apps/web/src/api/schema.d.ts
- apps/web/src/saved/useSavedEntries.ts, apps/web/src/saved/SavedEntries.tsx
- apps/web/tests/saved/useSavedEntries.test.ts, apps/web/tests/saved/SavedEntries.test.tsx

## Risks
- **A delete is final (q2):** the confirmation step is the only guard against a mistaken click. It is in place and needs a second click.
- **Two tabs:** deleting an entry that another tab is editing makes that edit fail with `not-found`. The edit row then shows `Could not save the edit: not-found` (WI-052 behaviour), which is acceptable.

## Assumptions
- **New texts:** `Could not delete the entry: <error>` and the "Deleting" busy label. The documents do not give them; they are plain labels and can be renamed without changing behaviour. `Delete this entry?` and `Entry deleted.` come from the answers.
- **204 with no body for a successful delete:** nothing is left to return.
