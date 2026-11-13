# WI-029: Expand one short entry

Applications: api (primary), web
Requirement: REQ-276 (approved) · Decision: DEC-310 · Feature: FEAT-1056

## Approach
The expansion rules live in one place, the API, so that what the user sees is exactly what REQ-278 later saves. The web app sends the typed text and shows the result.

### api (APP-025, Python / FastAPI)
1. **Pure parser** `app/entries/expand.py`: `expand(text, today, codes) -> Expanded | EntryError`. It does no I/O, which makes every REQ-276 case a plain unit test.
   - Trim leading and trailing spaces. Split code, amount and date on runs of spaces. The note is the rest of the text, kept as typed.
   - Look up the code case-insensitively. Keep the upper-case code in the result.
   - Amount: an optional `k`/`K` suffix, then a positive decimal with at most 2 decimals as typed. Multiply after checking the decimals. Use `Decimal` (no floats), and return paise (an integer) plus a 2-decimal display string.
   - Date: none, `td` or `yd` (any case), or `d/m` with 1 or 2 digits each in the current IST year. It must be a real calendar date and not after today in IST.
   - Errors in the REQ-276 order. The first failure wins, with the exact message text: unknown code, amount missing, amount must be greater than 0, at most 2 decimals, date not valid, date in the future.
2. **Today in IST** `app/entries/clock.py`: `today_ist()` uses `zoneinfo.ZoneInfo("Asia/Kolkata")`. Tests inject the date.
3. **Code lookup** `app/entries/codes.py`: loads the category and merchant codes from the `categories` and `merchants` tables (DB design) into a `{CODE: (merchant | None, category)}` map, cached in-process. These are reference data that only change with a release.
4. **Endpoint** `app/entries/routes.py`: `POST /entries/expand` with body `{"text": "SWG 340 yd"}`. It returns 200 with `{"ok": true, "entry": {code, merchant, category, amount, amount_paise, date, note}}` or `{"ok": false, "error": "<exact message>"}`. A rules error is a normal 200 result, not an HTTP error. The endpoint requires a signed-in user (jwt-auth guard, REQ-275). It is registered in `app/glue/routes.py` at the `knm:entries` marker.
5. **Tests** `tests/entries/`: every acceptance case in REQ-276 (the 8 working samples, the 5 failing samples and the 7 answered-question cases), the error order (`F -1.555`), and the IST midnight case (00:30 IST on 13 Nov 2026). Plus endpoint tests: signed in, not signed in (401), and an empty body.

### web (APP-024, React 18)
1. Regenerate the typed client from the API's OpenAPI document (`python scripts/tasks.py openapi` in api, then `node scripts/generate-client.cjs` in web).
2. **Entry box** `src/entries/EntryBox.tsx` (Chakra): one text input. On submit it calls `POST /entries/expand` and shows Merchant, Category, Amount, Date and Note, or `Error: <message>`, as in the REQ-276 mock. REQ-277 (several entries) and REQ-278 (save) build on this component.
3. **State** `src/entries/useExpand.ts` with zustand-state's `useAsync`.
4. **Route** registered through the router glue. It needs a signed-in user once REQ-275 exists.
5. **Tests**: rendering of a success, an error and a loading state, with a mocked client.

## Areas and files likely affected
- api: `app/entries/*` (new), `app/glue/routes.py` (one registration line), `app/db/models.py` (Category and Merchant models, from the DB design), `requirements.in` / `requirements.txt` (`tzdata`), `tests/entries/*`.
- web: `src/entries/*` (new), `src/api/schema.d.ts` (regenerated), the router glue, `tests/entries/*`.

## Dependencies
- **DB design:** the `categories` and `merchants` tables are still `New` in `docs/project/db_design_tables.csv`. They must be `Final` and created (`/knm:implement-db-design`) before step 3. Their seed rows are the 8 categories and 8 merchants of 02-abbreviation-rules.md.
- **REQ-275 (sign-in):** not implemented yet. Until it is, the endpoint tests sign their own test tokens with jwt-auth's helpers, and the web route has no sign-in screen in front of it.

## Risks
- **Time zone data on Windows:** `zoneinfo` has no built-in time zone database on Windows, so the `tzdata` package must be a dependency, or `Asia/Kolkata` fails to load.
- **Decimal handling:** checking decimals as typed (before `k`) means parsing the text, not the number. `1.2345k` must fail even though it equals 1234.50, and floats would hide this.
- **Error order:** a different check order changes the visible message. The order test locks it.
- **Shared rules for REQ-277 and REQ-278:** splitting several entries and saving must reuse this parser, not copy it.

## Assumptions
- `X` in `Unknown code "X".` is the code exactly as typed (REQ-276 behaviour).
- The note keeps its inner spaces as typed. Only leading and trailing spaces and the spaces between fields collapse (REQ-276, as written; confirm at approval).
- The amount is returned both as paise (an integer, matching the DB design's `amount_paise`) and as a 2-decimal display string.
