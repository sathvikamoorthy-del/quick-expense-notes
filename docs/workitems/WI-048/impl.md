# WI-048: Save reviewed entries as expense records

Applications: api (primary), web
Requirement: REQ-278 · Decision: DEC-312 · Feature: FEAT-1058
Builds on: WI-047 (`POST /entries/expand-all`, `app.entries.batch`, `EntryBox`), WI-039 (sign-in, `users` table)

## Answered questions
Answered by the product owner on 22 Nov 2026 (in chat, for the questions on WI-048):
1. **Saving with errors present:** yes. Valid entries are saved even when other entries have errors. Entries with errors are not saved, and the result says how many were saved and how many failed.
2. **Text box after Save:** it keeps only the lines that failed, so they can be fixed. If every entry was saved, the box is cleared.
3. **Saved-entries list:** not part of WI-048. It comes with edit and delete (REQ-280, REQ-281). After Save, a short message such as "3 entries saved" is shown.
4. **Duplicates:** allowed. Saving the same text twice creates two sets of records. There is no duplicate check.
5. **What is saved:** the API expands the typed text again at save time and saves that result. It refuses the save if the result differs from what was reviewed (for example, a `td`/`yd` date that shifted after midnight IST).
6. **`expenses` table:** the design in docs/project/db_design.md is accepted. This work item adds its migration and moves its status to Final.

## Behaviour to implement
1. The user presses Expand (WI-047) and sees the review. **Save** is enabled only when:
   - a review is shown,
   - the text box has not changed since that review, and
   - the review has at least one valid entry.
   Nothing is saved before Save is pressed (REQ-278 acceptance 4).
2. Save sends the text box and the review the user saw.
3. The API expands the text again with today's IST date (the same `expand_all` as the review) and compares the fresh results with the reviewed ones: same entries, same order, the same `typed`, `ok` and `error`, and the same entry fields (`code`, `merchant`, `category`, `amount_paise`, `date`, `note`).
   - Any difference: nothing is saved. The answer is `ok: false` with the error `The entries changed since the review. Press Expand to review them again.`
   - More than 20 entries at save time (only possible if the request was altered): nothing is saved, with the error `Too many entries (max 20).`
4. Otherwise every valid entry is inserted into `expenses` for the signed-in user, in one transaction. Entries with an error are not saved. Order and count follow the review, and a repeated save creates new rows (q4).
5. The answer gives the number saved and the failed entries (`typed` and `error`), so their errors stay shown (REQ-278 acceptance 2).
6. The web app shows:
   - `3 entries saved.` when nothing failed, or `3 entries saved, 1 not saved.` when some failed (`1 entry saved` in the singular).
   - Each failed entry with its error, under that message.
   - The text box then holds only the failed lines (their `typed` text, one per line), or is cleared when all were saved (q2). The old review table is removed, since it no longer matches the box.

## Approach

### Database (apps/api)
- **New migration** `apps/api/migrations/0004_expenses.sql` creates `expenses` exactly as in db_design.md, in the style of 0001 and 0003:
  - `id` TEXT NOT NULL PK, `CHECK (length(id) = 36)`.
  - `user_id` TEXT NOT NULL, references `users(id)` ON DELETE CASCADE.
  - `typed_text` TEXT NOT NULL, `CHECK (length > 0)`.
  - `category_code` TEXT NOT NULL, references `categories(code)` ON DELETE RESTRICT.
  - `merchant_code` TEXT NULL, references `merchants(code)` ON DELETE RESTRICT. A composite FK on `(merchant_code, category_code)` references `merchants(code, category_code)`; the unique index already exists in 0001.
  - `amount_paise` INTEGER NOT NULL, `CHECK (typeof(amount_paise) = 'integer' AND amount_paise > 0)`.
  - `spent_on` TEXT NOT NULL, `CHECK (spent_on IS date(spent_on))`. "Not in the future" is checked by the app (expand).
  - `note` TEXT NULL.
  - `created_at` and `updated_at` TEXT NOT NULL, default `strftime('%Y-%m-%dT%H:%M:%fZ','now')`, as the design says.
  - Indexes: `(user_id, spent_on)`, `category_code`, `merchant_code`.
- Apply it to the local `apps/api/data/app.db` by hand with Python `sqlite3` inside BEGIN/COMMIT, as was done for 0003 (the machine has no `sqlite3` program).
- **New model** `apps/api/app/models/expenses.py` (`Expenses`), exported from `app/models/__init__.py`, with columns matching the migration as in `users.py`.
- In `docs/project/db_design_tables.csv`, the `expenses` status moves from New to Final (q6).

### API (primary)
- **Category codes:** `CodeInfo` gains `category_code`, and `read_codes` in `app/entries/codes.py` fills it: the category's own code, or the merchant's `category_code`. `Expanded` gains `category_code` too, so a save never maps names back to codes.
  - The public `ExpandedEntry` response is unchanged, so `/entries/expand` and `/entries/expand-all` keep their contracts.
  - The `CODES` table in `tests/entries/test_expand.py` is updated.
- **New service** `apps/api/app/entries/save.py` holds the business rules, with the database work in one function:
  - `compare(reviewed, fresh) -> bool`: steps 3 and 4. It is pure and compares `typed`, `ok`, `error`, `code`, `merchant`, `category`, `amount_paise`, `date` and `note`.
  - `async save_reviewed(session, user_id, text, reviewed, today, codes) -> SaveOutcome`:
    - It runs `expand_all`, refuses on too-many or a mismatch, then inserts one `Expenses` row per valid entry with a new `uuid4` id.
    - Each row gets `typed_text` = the trimmed entry, `category_code`, `merchant_code` (the code when the entry has a merchant, else NULL), `amount_paise`, `spent_on` = ISO date, and `note`. Everything is in one transaction.
    - It returns the saved count, the ids, and the failed entries.
  - The messages are constants: `REVIEW_CHANGED = "The entries changed since the review. Press Expand to review them again."` The too-many message is reused from `batch.TOO_MANY_ENTRIES`.
- **New route** `POST /entries/save` in `app/entries/routes.py`. It stays thin, with the same `require_auth` and `get_session` dependencies.
  - The user id is `AuthClaims.user_id` (the JWT `sub`, the `users.id` set at sign-in, WI-039).
  - Request: `SaveRequest { text: str (same limits and validator as ExpandAllRequest), reviewed: list[ExpandResult] }`. The `reviewed` list is exactly the `results` of the `/entries/expand-all` answer the user saw.
  - Response (200): `SaveResponse { ok: bool, error: str | None, saved: int, ids: list[str], failed: list[ExpandResult] }`. With `ok=false`, `error` says why and `saved` is 0.
  - As before, a refused save is a normal answer (200), not an HTTP error.
- Regenerate `apps/api/openapi.json`.

### Web
- Regenerate `src/api/schema.d.ts`.
- `src/entries/useExpand.ts`: add `saveEntries(text, reviewed, client)`, which calls `POST /entries/save`. It follows the `expandAll` pattern: a refusal is data, and only a failed request throws.
- `src/entries/EntryBox.tsx`:
  - It keeps the text that was reviewed. A **Save** button sits next to Expand and is enabled under the conditions in Behaviour step 1.
  - While a save is running, Save and Expand are disabled, so a double click does not save twice.
  - On `ok: true`: it shows the saved message from Behaviour step 6 (`role="status"`) and lists the failed entries with their errors. The text box is set to the failed `typed` lines joined by `\n`, or cleared, and the review is cleared.
  - On `ok: false`: it shows `Error: <message>` as an alert. The review and the text stay, so the user can press Expand again.
  - On a failed request: `Could not save the entries: <error>`.
  - The UI holds no rules: it only compares its own text with the reviewed text and counts `ok` results to enable Save.

## Tests
API:
- `tests/entries/test_save.py` (service, today pinned to 12 Nov 2026, a SQLite database built from migrations 0001 to 0004 with one user):
  - The sample text box saves three rows and not `X 100`. The rows have exactly the reviewed merchant code, category code, amount_paise (25000, 34000, 18000), spent_on, note and typed_text (acceptance 1 and 2).
  - The failed list holds `X 100` with `Unknown code "X".`.
  - A changed review (other amount, other date, one entry removed, a different order) saves nothing and gives `REVIEW_CHANGED`.
  - The same `yd` review is refused when "today" moves from 12 to 13 Nov (the midnight case of q5).
  - Saving the same text twice gives six rows (q4).
  - Rows belong to the given user only. A second user's save does not touch the first user's rows (acceptance 3).
  - A review with only errors saves nothing and returns all of them as failed.
- `tests/entries/test_routes.py`:
  - `/entries/save` needs auth (401). The sample gives 200 with `saved: 3` and one failed entry.
  - A mismatch gives 200 with `ok: false` and the message. Blank or too-long text gives 422.
  - Nothing is written by `/entries/expand-all` (acceptance 4).
  - The route fixture builds the database with 0003 and 0004 and inserts the token's user.
- `tests/entries/test_codes.py`: `category_code` is read for category and merchant codes (SWG gives F).
- The migration is checked with `PRAGMA foreign_keys=ON`:
  - Rejected: a merchant with the wrong category, `amount_paise` 0 or 1.5, `spent_on` `2026-02-30`, and an unknown `user_id`.
  - Deleting a user deletes their expenses.

Web:
- `useExpand.test.ts`: `saveEntries` posts `{text, reviewed}` and returns refusals as data.
- `EntryBox.test.tsx`:
  - Save is disabled before a review, after the text changes, and when every entry has an error.
  - Saving the sample shows `3 entries saved, 1 not saved.` and `X 100` with its error, and the text box becomes `X 100`.
  - When everything is saved, the box is cleared and the message is `3 entries saved.`
  - A refused save shows the message, and the review stays.
  - Nothing is posted to `/entries/save` before Save is pressed.

Run `pytest -q` in apps/api (all tests must pass before commit), plus `npx jest --ci` in apps/web.

## Files likely affected
- apps/api/migrations/0004_expenses.sql (new)
- apps/api/app/models/expenses.py (new), apps/api/app/models/__init__.py
- apps/api/app/entries/save.py (new), apps/api/app/entries/routes.py
- apps/api/app/entries/expand.py, apps/api/app/entries/codes.py (`category_code`)
- apps/api/openapi.json
- apps/api/tests/entries/test_save.py (new), test_routes.py, test_codes.py, test_expand.py (CODES)
- apps/web/src/api/schema.d.ts, apps/web/src/entries/useExpand.ts, apps/web/src/entries/EntryBox.tsx
- apps/web/tests/entries/useExpand.test.ts, apps/web/tests/entries/EntryBox.test.tsx
- docs/project/db_design_tables.csv (expenses: Final)

## Risks
- **Token for a user with no row:** a `sub` that has no `users` row fails the `user_id` FK. Real tokens come from sign-in, so this happens only with hand-made tokens. The service turns it into 401 `unauthorized` instead of a 500.
- **Midnight:** a review made at 23:59 IST and saved at 00:00 is refused by design (q5). The user presses Expand again.
- **Double submit:** duplicates are allowed (q4), so the only guard against an accidental double click is the disabled button while saving.
- **Existing local database:** `data/app.db` needs 0004 applied by hand (see Database). The test databases are built from the migration files.
- **Changing `CodeInfo` and `Expanded`:** these are internal types. The response models do not change, and the WI-047 tests must still pass.

## Assumptions
- **Messages:** the refused-save text `The entries changed since the review. Press Expand to review them again.` was proposed in this plan and confirmed by the product owner on 22 Nov 2026 (in chat). The saved message follows the q3 example: `N entries saved.`, plus `, M not saved` when some failed.
- **Stored values:** `typed_text` is the trimmed entry as typed, the same value as `typed` in the review. Codes are stored in upper case (REQ-276).
- **Saved ids:** the API returns them for later work (REQ-280/281), but the web app does not use them yet.
