# WI-052: Edit a saved entry

Applications: api (primary), web
Requirement: REQ-280 · Decision: DEC-314 · Feature: FEAT-1060
Builds on: WI-048 (`expenses`, save), WI-049 (`/summary`, month helpers), WI-047 (`EntryBox`), WI-039 (`RequireAuth`)

## Answered questions
Answered by the product owner on 22 Nov 2026 (KNM Q&A on WI-052; the two q3 details in chat the same day):
1. **How an entry is edited:** by re-typing the short form, pre-filled with the saved typed text (e.g. `UBR 180 12/11 airport`).
2. **Rules for edits:** yes. The abbreviation rules and their exact messages apply. An invalid edit is refused with the rule's message and the entry stays unchanged.
3. **`td`, `yd` and `dd/mm` in an edit:** relative to the entry's saved date.
   - **3a.** The saved date is the day the entry was saved: the IST date of `created_at`, not the expense date. Re-saving the pre-filled `SWG 340 yd` therefore keeps the same date.
   - **3b.** "Date cannot be in the future." is still judged against today (IST, the day of the edit), as for a new entry.
4. **The list:** one month at a time with Previous and Next, like the summary. It opens on the current month, newest date first.
5. **Where the list is:** a page at `/saved-entries`, with links from the entry box and the summary.
6. **The edit:** inline in the list. Edit turns the row into a text box with Save and Cancel. After Save, the row shows the new values.
7. **No review step:** an edit is saved at once. Only a rule error is shown, and the entry is then left unchanged.

## Behaviour to implement
1. `/saved-entries` (signed in only) opens on the current IST month, headed like `November 2026`, with Previous and Next. Next is disabled on the current month, as in `/summary`.
   - Columns: `Typed · Merchant · Category · Amount · Date · Note · (Edit)`.
   - Rows are the user's entries dated in that month, newest date first. Entries on the same date are ordered newest saved first (`created_at`).
   - A month with no entries shows `No saved entries in this month.`
2. **Edit** on a row replaces it with a text box pre-filled with the saved typed text, plus **Save** and **Cancel**. Only one row is in edit mode at a time. Cancel restores the row unchanged.
3. Save sends the text. The API expands it as one entry with the REQ-276 rules:
   - Codes, amounts and errors are the same as for a new entry.
   - `td` is the saved day, `yd` the day before it, and `dd/mm` that day in the saved day's year (3, 3a).
   - A resulting date after today (IST) is refused with `Date cannot be in the future.` (3b).
4. **Valid:** the record is updated in place: `typed_text`, `category_code`, `merchant_code`, `amount_paise`, `spent_on`, `note`, and `updated_at` set to now. Its `id`, `created_at` and owner do not change. The row then shows the new values (q6).
   - If the new date moves the entry to another month, it leaves this month's list. A note says `The entry moved to October 2026.`
5. **Invalid:** nothing changes. The row stays in edit mode, showing the text as typed and `Error: <rule message>` under it (q2).
6. The text must be one entry. A new line or `;` in the edit text is refused with `Type one entry only.`, and nothing changes.
7. Users can see and edit only their own entries. Another user's entry id, or an unknown id, gives 404 `not-found`, so it does not reveal whether the entry exists.
8. The monthly summary reflects the edit at once, including a move to another month. `/summary` is never cached (WI-049), and the list is not cached either.
9. **Links:**
   - the entry box gets a "Saved entries" link next to "Monthly summary";
   - the summary gets a "Saved entries" link next to "Enter expenses";
   - the list links to the entry box ("Enter expenses") and the summary ("Monthly summary").

## Approach

### API (primary): apps/api
- `app/entries/expand.py`: `expand(text, today, codes, reference=None)` gains an optional `reference` day.
  - `td`, `yd` and the `dd/mm` year use `reference or today`. The future check always uses `today`.
  - Existing calls pass no reference, so their behaviour is unchanged.
- **New service** `app/entries/edit.py` holds the business rules:
  - `ONE_ENTRY_ONLY = "Type one entry only."`
  - `saved_day(created_at: str) -> date`: the IST date of an ISO UTC `created_at` (`2026-11-12T19:00:00.000Z` gives 13 Nov).
  - `async list_month(session, user_id, start, next_start) -> list[Expenses]`: the user's rows with `spent_on` in the month, ordered `spent_on DESC, created_at DESC`. It uses the `(user_id, spent_on)` index.
  - `async edit_entry(session, user_id, expense_id, text, today, codes) -> Edited | Refused | None`:
    - `None` when no row has that id and user.
    - `split_entries(text)` must give exactly one entry, else `Refused(ONE_ENTRY_ONLY)`.
    - It expands with `reference=saved_day(row.created_at)`. A rule error gives `Refused(message)` with no change.
    - Otherwise it updates the row's fields and `updated_at` (`strftime('%Y-%m-%dT%H:%M:%fZ','now')` via SQL, the same format as the default), flushes, and returns the updated row.
- **New routes** in `app/entries/routes.py`, thin, with `require_auth` and `get_session`:
  - `GET /entries?month=YYYY-MM` (default: the current IST month; a future or bad month gives 422).
    - Answer: `SavedEntriesResponse { month, current_month, entries: [SavedEntry] }`.
    - `SavedEntry { id, typed, code, merchant, category, amount, amount_paise, date, note }`. Merchant and category names come from the cached code table.
    - It sets `Cache-Control: no-store`.
  - `PUT /entries/{id}` with `EditRequest { text }` (same not-blank validator, max 500 characters).
    - 200 `EditResponse { ok, error, entry: SavedEntry | None }`. 404 `not-found` for an unknown or foreign id.
    - A rule error and one-entry-only are normal answers (`ok: false`), as everywhere else.
- Regenerate `apps/api/openapi.json`.

### Web: apps/web
- Regenerate `src/api/schema.d.ts`.
- **New** `src/saved/useSavedEntries.ts`:
  - `fetchSavedEntries(month | null, client)` calls `GET /entries`, and `editEntry(id, text, client)` calls `PUT /entries/{id}`.
  - `useSavedEntries(month, client)` uses `useAsync`, with `reload`.
- **New** `src/saved/SavedEntries.tsx`:
  - The month heading, and Previous and Next, reuse `monthLabel` and `shiftMonth` from `src/summary/MonthlySummary.tsx`.
  - The table and the inline edit row (a Chakra `Input` pre-filled with `typed`, Save, Cancel, and the error under it). Save is disabled while saving or when the text is blank.
  - On `ok: true` it reloads the month: the row shows the new values, or it is gone, with the move note when `entry.date` is in another month.
  - On `ok: false` it keeps edit mode and shows `Error: <message>`. A failed request shows `Could not save the edit: <error>`.
  - Loading and error states follow `MonthlySummary`. Dates use `formatDate` from `EntryBox` (`5 Nov 2026`).
- `src/app/router.tsx`: add `{ id: 'saved-entries', path: '/saved-entries', element: <RequireAuth><SavedEntries /></RequireAuth> }`, outside the `knm:` markers.
- `src/entries/EntryBox.tsx` and `src/summary/MonthlySummary.tsx`: add the "Saved entries" link.

## Tests
API:
- `tests/entries/test_expand.py`: with `reference`, `td`, `yd` and `dd/mm` count from the reference day while the future check uses today. Without `reference`, nothing changes; the existing cases still pass.
- `tests/entries/test_edit.py` (service, database built from 0001 to 0004, two users, today pinned):
  - Editing `UBR 180 12/11 airport` to `UBR 220 12/11 airport` updates the amount to 22000, keeps the id and `created_at`, and sets a later `updated_at`.
  - Re-saving the pre-filled `SWG 340 yd` a week after it was saved keeps 11 Nov (3a).
  - An entry saved on 5 Nov and edited on 12 Nov to `F 100 10/11` is accepted (3b). `F 100 20/11` on 12 Nov gives `Date cannot be in the future.`
  - `X 100`, `F` and `F -5` give their exact messages, with the row unchanged (q2).
  - `F 1; F 2` and `F 1\nF 2` give `Type one entry only.`
  - A category code becomes a merchant code and back (merchant_code set and cleared, category_code follows).
  - Another user's id, or an unknown id, gives None, with nothing changed.
  - `list_month`: only the month and only the user's rows, newest date first, with `created_at` breaking ties.
  - The summary after an edit that moves an entry from November to October shows the amount moved between the two months (acceptance 2).
- `tests/entries/test_routes.py`:
  - `GET /entries`: 401, the default current month, the order, no-store, and 422 for a future or bad month.
  - `PUT /entries/{id}`: 200 with the updated entry, `ok: false` with the rule message, 404 for a foreign or unknown id, and 422 for blank text.

Web:
- `tests/saved/useSavedEntries.test.ts` (node, real client with a fake fetch): the list URL with and without `month`, `PUT /entries/{id}` with `{text}`, a refusal returned as data, and a failed request that throws.
- `tests/saved/SavedEntries.test.tsx` (fake client):
  - The month table renders in order. Edit pre-fills the typed text. Cancel restores the row.
  - Save shows the new values after the reload.
  - A rule error keeps edit mode and shows the message.
  - A move to another month shows the move note, and the row is gone.
  - Only one row is edited at a time. The empty month shows its text.
  - Previous and Next behave as in the summary. The links are there.
- `tests/entries/EntryBox.test.tsx` and `tests/summary/MonthlySummary.test.tsx`: the "Saved entries" link.
- `tests/auth/RequireAuth.test.tsx`: the routes are `['/sign-in', '/entries', '/summary', '/saved-entries']`, and `/saved-entries` is wrapped in `RequireAuth`.

Run `pytest -q` in apps/api (all tests must pass before commit), plus `npx jest --ci` in apps/web.

## Files likely affected
- apps/api/app/entries/expand.py, apps/api/app/entries/edit.py (new), apps/api/app/entries/routes.py
- apps/api/openapi.json
- apps/api/tests/entries/test_expand.py, test_edit.py (new), test_routes.py
- apps/web/src/api/schema.d.ts
- apps/web/src/saved/useSavedEntries.ts (new), apps/web/src/saved/SavedEntries.tsx (new)
- apps/web/src/app/router.tsx, apps/web/src/entries/EntryBox.tsx, apps/web/src/summary/MonthlySummary.tsx
- apps/web/tests/saved/useSavedEntries.test.ts (new), apps/web/tests/saved/SavedEntries.test.tsx (new)
- apps/web/tests/entries/EntryBox.test.tsx, apps/web/tests/summary/MonthlySummary.test.tsx, apps/web/tests/auth/RequireAuth.test.tsx

## Risks
- **`created_at` in UTC:** the saved day is its IST date. An entry saved at 00:30 IST has a `created_at` on the previous UTC day. `saved_day` converts with `Asia/Kolkata` and is unit-tested for that case.
- **`GET /entries` and the cache:** the memory cache would otherwise keep the list for 30 s. `no-store` prevents it, and a route test guards it.
- **Route clash:** `POST /entries/expand`, `/entries/expand-all` and `/entries/save` stay as they are. `PUT /entries/{id}` is a different method, and `GET /entries` has no sub-path. FastAPI routes them apart, and the tests cover all of them.
- **Editing a row that another tab already changed:** the last edit wins. There is no version check, and none is asked for.

## Assumptions
- **New texts:** `No saved entries in this month.`, `Type one entry only.`, `The entry moved to <Month Year>.`, `Could not save the edit: <error>`, and the link label "Saved entries". The documents do not give them; they are plain labels and can be renamed without changing behaviour.
- **`dd/mm` in an edit:** it uses the saved day's year, as `td` and `yd` use the saved day (3). The future check still uses today (3b).
- **404 for another user's entry:** the API answers as if the entry did not exist, so ids of other users cannot be probed.
