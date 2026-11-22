# WI-047: Expand several entries from one text box

Applications: api (primary), web
Requirement: REQ-277 · Decision: DEC-311 · Feature: FEAT-1057
Builds on: REQ-276 (one entry, `app.entries.expand`, `EntryBox`)

## Answered questions
Answered by the product owner on 22 Nov 2026 (KNM Q&A on WI-047, q2 details in chat):
- **Empty parts** (blank lines, `;;`, a trailing `;`, a part with only spaces): ignored silently, with no result row.
- **Limit:** at most 20 entries in one text box. With more than 20, the whole text box is rejected with `Too many entries (max 20).` and no entry is expanded. Skipped empty parts do not count toward the maximum.
- **When results show:** on an explicit action (the Expand button), as today for one entry. Not live.
- **Endpoint:** `POST /entries/expand` is kept unchanged. A new endpoint takes the whole text box.

## Behaviour to implement
1. Split the text on `\n` and `;` (mixed freely; `\r\n` is treated as a new line).
2. Trim each part and drop parts that are empty after trimming.
3. If more than 20 parts remain: reject the text box with `Too many entries (max 20).`
4. Otherwise expand each part with the REQ-276 rules (`expand()`), in typed order. One result per part: the expanded entry, or its single REQ-276 error. An error never stops the other parts.
5. A text box with no entries at all (empty, or only separators and spaces) is a bad request (422), like an empty single entry today. The Expand button stays disabled for it.

## Approach

### API (primary): apps/api
- **New service** `app/entries/batch.py` holds the business rules: `split_entries(text) -> list[str]` (steps 1-2) and `expand_all(text, today, codes) -> list[Expanded | EntryError] | TooMany` (steps 3-4). It is pure like `expand.py`: no I/O and no clock. `MAX_ENTRIES = 20` and `TOO_MANY_ENTRIES = "Too many entries (max 20)."` are constants. `TooMany` is a small frozen dataclass that carries the message.
- **New route** `POST /entries/expand-all` goes in `app/entries/routes.py`. It stays thin: it validates the body, loads `today_ist()` and `load_codes(session)` once, calls `expand_all`, and maps the result. It uses the same `require_auth` and `get_session` dependencies as `/entries/expand`.
  - Request: `ExpandAllRequest { text: str }`. `max_length` is 10,500 (20 entries x 500 characters, plus separators), so a very large paste fails with 422 before any splitting. A validator rejects text with no non-blank part (422).
  - Response (200): `ExpandAllResponse { ok: bool, error: str | None, results: list[ExpandResult] }`. `ok=false` with `error="Too many entries (max 20)."` and `results=[]` means the text box was rejected. Otherwise `ok=true` and `results` lists one item per entry in typed order.
  - `ExpandResult { typed: str, ok: bool, entry: ExpandedEntry | None, error: str | None }`, where `typed` is the trimmed part as typed. The existing `ExpandedEntry` model is reused. The mapping from `Expanded` to `ExpandedEntry` moves into a small helper shared by both routes.
  - As with REQ-276, rule errors (per entry, or too many entries) are normal answers (200), not HTTP errors.
- `/entries/expand` and its request/response models stay as they are.
- Regenerate `apps/api/openapi.json` (`scripts/export_openapi.py`).
- Amounts stay integer paise inside, as in `Expanded.amount_paise`. Nothing is written to the database (saving is REQ-278).

### Web: apps/web
- Regenerate `src/api/schema.d.ts` from the new openapi.json (`scripts/generate-client.cjs`).
- `src/entries/useExpand.ts`: add `expandAll(text, client)` and `useExpandAll(text | null, client)`, which call `POST /entries/expand-all`. They follow the same pattern as `expandEntry`/`useExpand`: a rule error is data, and only a failed request throws. The hook only sends the text as typed. No splitting or rules in the UI.
- `src/entries/EntryBox.tsx`:
  - The `Input` becomes a `Textarea` (label "Short entries", placeholder `F 250; SWG 340 yd`). Enter adds a new line. The Expand button submits and stays disabled while the text is blank.
  - The result table follows mock.md: columns `# · Typed · Merchant · Category · Amount · Date · Note`, one row per result in typed order. An error row shows `#`, `Typed` and `Error: <message>` across the remaining columns (`colSpan`).
  - With `ok=false` (too many entries), it shows `Error: Too many entries (max 20).` as an alert, with no table.
  - The loading and request-failure states stay as they are today.
  - `formatDate` stays. The single-entry `EntryTable` is replaced by the multi-row table. The page uses only `useExpandAll`; `useExpand`/`expandEntry` stay for API parity and existing tests.

## Tests
API (`apps/api/tests/entries/`):
- `test_batch.py` (pure, today = 12 Nov 2026):
  - The REQ-277 sample (`F 250; SWG 340 yd\nX 100\nUBR 180 12/11 airport`) gives four results in order: three expanded exactly as in 03-sample-entries.md, and `Unknown code "X".` for `X 100`.
  - New lines only, semicolons only, mixed, and `\r\n`.
  - Empty parts are skipped and get no row: `F 250;;`, `;F 250`, blank lines, `  ;  `.
  - 20 entries are accepted. 21 entries give `Too many entries (max 20).` 20 entries plus several empty parts are accepted (empty parts don't count).
  - An error in the first and last entries still expands the middle ones. Each entry keeps its own single REQ-276 error.
- `test_routes.py`:
  - `/entries/expand-all` needs auth (401).
  - The sample gives 200 with the expected JSON, including `typed` and `amount` as `"250.00"`.
  - 21 entries give 200 with `ok=false` and the message.
  - Blank text or only separators give 422. Text over 10,500 characters gives 422.
  - `/entries/expand` is unchanged (its existing tests still pass).

Web (`apps/web/tests/entries/`):
- `useExpand.test.ts`: `expandAll` posts the text unchanged, returns the data, and throws on a failed request.
- `EntryBox.test.tsx`:
  - Multi-line typing and Expand render four rows (three entries, one error row) with mock client data.
  - The too-many message shows as an alert.
  - The button is disabled for blank text.
  - Nothing is sent before Expand is pressed.

Run `pytest -q` in apps/api (all tests must pass before commit), plus the web jest suite.

## Files likely affected
- apps/api/app/entries/batch.py (new)
- apps/api/app/entries/routes.py
- apps/api/openapi.json
- apps/api/tests/entries/test_batch.py (new), apps/api/tests/entries/test_routes.py
- apps/web/src/api/schema.d.ts
- apps/web/src/entries/useExpand.ts, apps/web/src/entries/EntryBox.tsx
- apps/web/tests/entries/useExpand.test.ts, apps/web/tests/entries/EntryBox.test.tsx

## Risks
- **Unique codes per page load:** `load_codes` runs once per request, not once per entry. This keeps 20 entries to one query.
- **Note containing `;`:** a `;` always separates entries, so `F 100 lunch; with team` gives two entries, the second being `with team` (`Unknown code "with".`). This follows the source rule "Separate entries with a new line or a semicolon".
- **REQ-278 (save)** will need the reviewed list. The `results` shape (typed order, `typed` text, `ExpandedEntry`) is meant to be reused there.
- **Response cache:** check that `app/cache/middleware.py` does not cache POST responses. The result depends on today's IST date.

## Assumptions
- The 10,500-character request cap is a technical guard, not a product rule. Text under it but with more than 20 entries gets the product message.
- An over-long single part (over 500 characters) is expanded like any other entry (REQ-276 has no length rule). Only the whole-request cap applies.
- `Typed` in the result is the trimmed part. Inner spaces are kept as typed.
