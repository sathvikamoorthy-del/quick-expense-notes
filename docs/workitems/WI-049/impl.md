# WI-049: Monthly summary by category

Applications: api (primary), web
Requirement: REQ-279 · Decision: DEC-313 · Feature: FEAT-1059
Builds on: WI-048 (`expenses` table, migration 0004), WI-039 (sign-in, `RequireAuth`), WI-047 (`EntryBox` at `/entries`)

## Answered questions
Answered by the product owner on 22 Nov 2026 (in chat, for the questions on WI-049):
1. **Picking the month:** Previous and Next buttons only. There is no month picker.
2. **First month shown:** the current month in IST.
3. **A month with no entries:** shows the text `No expenses in this month.`, with no table and no grand total.
4. **Category order:** the sample's order, then Utilities and Other: Food, Travel, Rent, Entertainment, Health, Shopping, Utilities, Other.
5. **Future months:** cannot be opened. Next is disabled on the current month.
6. **Reaching the summary:** a `/summary` page, with a link to it from the entry box and a link back to the entry box. There is no link after Save.

## Behaviour to implement
1. `/summary` (signed in only) opens the current IST month. The heading is the month name and year, e.g. `November 2026`.
2. The page shows the signed-in user's saved entries dated in that month (`spent_on` from the 1st to the last day), grouped by category:
   - one row per category that has entries, in the q4 order, with its total;
   - then a **Grand total** row.
   Amounts are rupees with 2 decimals (`2799.50`). Categories with no entries in that month are not shown.
3. A month with no entries shows `No expenses in this month.`, with no table and no grand total (q3).
4. **Previous** opens the month before, with no lower limit. **Next** opens the month after and is disabled on the current IST month (q5). A future month cannot be requested from the API either.
5. The totals are computed from `expenses` each time the summary is opened, and are never cached. They always equal the saved entries at that moment (REQ-279 acceptance 4; db_design: the summary is computed, there is no table).
6. Links: the entry box links to `/summary` ("Monthly summary"), and the summary links back to `/entries` ("Enter expenses"). After Save there is no link (q6).

## Approach

### API (primary): apps/api
- **New service** `app/entries/summary.py` holds the rules:
  - `CATEGORY_ORDER = ("F", "T", "R", "E", "H", "S", "U", "O")` (q4).
  - `parse_month("YYYY-MM") -> (first_day, first_day_of_next_month)`. Only `MM` from 01 to 12 and a 4-digit year are accepted; anything else is `None`.
  - `is_future(month, today)`.
  - `async monthly_summary(session, user_id, month_start, next_month_start, category_names) -> Summary`. It runs one query: `SELECT category_code, sum(amount_paise) FROM expenses WHERE user_id = :user AND spent_on >= :start AND spent_on < :next GROUP BY category_code`.
    - The range on `spent_on` uses the `(user_id, spent_on)` index. Dates are ISO text, so text comparison is date order.
    - The result is sorted by `CATEGORY_ORDER`, and the grand total is the sum of the rows. All sums stay in integer paise.
  - Category names come from the cached code table (`load_codes`), not from a second query.
- **Money formatting:** paise to `"2799.50"` uses the same rule as `Expanded.amount`. The formatting moves into one small function in `app/entries/expand.py` (`format_paise`), used by both.
- **New route** `GET /summary` in `app/entries/routes.py`. It stays thin: `require_auth`, `get_session`, and the user is `AuthClaims.user_id`.
  - Query `month` (optional, `YYYY-MM`). It defaults to the current IST month (`today_ist()`, q2).
  - A badly formed month, or a month after the current IST month (q5), gives 422 `validation-error`.
  - Response 200: `SummaryResponse { month: "2026-11", current_month: "2026-11", categories: [{code, category, total, total_paise}], grand_total: "6138.50", grand_total_paise: 613850 }`.
    - `categories` is empty for a month with no entries.
    - `current_month` comes from the server's IST clock, so the web app can disable Next without using the browser's time zone.
  - The response sets `Cache-Control: no-store`. The memory-cache middleware caches successful JSON GETs for 30 s, and skips responses marked `no-store` (`app/cache/middleware.py`, `NO_STORE`). Without it, a summary opened right after a save could show old totals.
- Regenerate `apps/api/openapi.json`.

### Web: apps/web
- Regenerate `src/api/schema.d.ts`.
- **New** `src/summary/useSummary.ts`:
  - `fetchSummary(month | null, client)` calls `GET /summary` with no `month` for the first load. Only a failed request throws.
  - `useSummary(month | null, client)` wraps it with `useAsync`.
- **New** `src/summary/MonthlySummary.tsx`:
  - The heading is the month name and year, built from `month` (`"2026-11"` gives `November 2026`). This is calendar arithmetic on `YYYY-MM` with no `Date`, so there are no time zone effects.
  - **Previous** and **Next** buttons. Previous and Next compute the month before or after with pure `YYYY-MM` arithmetic. Next is disabled when `month === current_month`.
  - The table has `Category · Total` and a bold **Grand total** row, as in mock.md, or the text `No expenses in this month.` when `categories` is empty.
  - Loading shows `Loading…`. A failed request shows `Could not load the summary: <error>`.
  - A link "Enter expenses" goes to `/entries`. The page holds no rules and no sums: totals come from the API.
- `src/app/router.tsx`: add `{ id: 'summary', path: '/summary', element: <RequireAuth><MonthlySummary /></RequireAuth> }` next to the `entries` route. It is an app route, not a module, so it goes outside the `knm:` markers, like `/entries`.
- `src/entries/EntryBox.tsx`: add a "Monthly summary" link to `/summary` (react-router `Link` rendered as a Chakra `Link`). There is no link after Save (q6).

## Tests
API:
- `tests/entries/test_summary.py` (service, database built from migrations 0001 to 0004, today pinned to 12 Nov 2026):
  - The 8 working sample entries saved for one user give, for 2026-11, exactly Food 590.00, Travel 180.00, Rent 1500.00, Entertainment 649.00, Health 420.00, Shopping 2799.50, in that order, with a grand total of 6138.50 / 613850 (acceptance 1).
  - Utilities and Other come last when present (q4).
  - Categories with no entries are absent (acceptance 2).
  - Only that month counts: entries on 31 Oct and 1 Dec are left out, and 1 Nov and 30 Nov are included. Another user's November entries are left out (acceptance 3).
  - A month with no entries gives empty `categories` and a grand total of 0.
  - `parse_month` accepts `2026-11` and `2026-01`, and gives December to January of the next year. It refuses `2026-13`, `2026-1`, `26-11` and `2026-11-01`.
- `tests/entries/test_routes.py`:
  - `GET /summary` needs auth (401). With no `month`, it gives the current IST month.
  - `month=2026-11` gives the sample totals.
  - A future month and a bad month give 422.
  - The response has `Cache-Control: no-store`. A summary opened, then a save, then the summary opened again shows the new totals at once (acceptance 4, no stale cache).

Web:
- `tests/summary/useSummary.test.ts` (node environment, real client with a fake fetch): no `month` on the first load, then `?month=2026-10`. A failed request throws.
- `tests/summary/MonthlySummary.test.tsx` (fake client):
  - The sample month renders the heading `November 2026`, the six rows in order and `Grand total 6138.50`.
  - An empty month shows `No expenses in this month.` with no table.
  - Previous requests `2026-10`, and January's Previous requests December of the year before.
  - Next is disabled on `current_month`. After Previous, Next is enabled and goes back.
  - The link back to `/entries` is there, as are the loading and error states.
- `tests/entries/EntryBox.test.tsx`: the "Monthly summary" link points to `/summary`.
- The react-vite contract tests must still pass: `/` stays "Page not found".

Run `pytest -q` in apps/api (all tests must pass before commit), plus `npx jest --ci` in apps/web.

## Files likely affected
- apps/api/app/entries/summary.py (new), apps/api/app/entries/routes.py, apps/api/app/entries/expand.py (`format_paise`)
- apps/api/openapi.json
- apps/api/tests/entries/test_summary.py (new), apps/api/tests/entries/test_routes.py
- apps/web/src/api/schema.d.ts
- apps/web/src/summary/useSummary.ts (new), apps/web/src/summary/MonthlySummary.tsx (new)
- apps/web/src/app/router.tsx, apps/web/src/entries/EntryBox.tsx
- apps/web/tests/summary/useSummary.test.ts (new), apps/web/tests/summary/MonthlySummary.test.tsx (new), apps/web/tests/entries/EntryBox.test.tsx

## Risks
- **Cache:** forgetting `no-store` would serve totals up to 30 s old after a save. A route test guards it.
- **Midnight at a month end:** the server's IST date decides `current_month`. A page left open across midnight on the last day still shows the old `current_month` until it is reloaded. Next stays disabled one month too early, which is harmless (q5 only forbids the future).
- **Router glue file:** `router.tsx` is scaffold-owned. The new route goes outside the `knm:` markers, as `/entries` and `/sign-in` did.

## Assumptions
- **Grand total row label:** `Grand total`, as in the mock and the sample. Category names come from the `categories` table (Food, Travel, ...).
- **Month heading:** English month names, the same as the entry box's date format (`5 Nov 2026`), written in full (`November 2026`) as in the mock.
- **No lower limit on Previous:** the documents set none. An old month just shows `No expenses in this month.`
- **Link texts** ("Monthly summary", "Enter expenses") are not given by the documents. They are plain labels and can be renamed without changing behaviour.
