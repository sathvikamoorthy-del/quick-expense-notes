# WI-066: Plain-words entries read by AI (Claude API) in the entry box

Applications: api (primary), web

Requirement: REQ-438 (approved) · Decision: DEC-473 · Feature: FEAT-1401 · Intent: G4 and the Not goals (validated 23 Nov 2026)

## Decisions (product owner, 23 Nov 2026)
From the REQ-438 Q&A:
- **Code form (q1):** a line is in code form or goes to AI (refined by WI-066 q1 below).
- **Merchants (q2):** only merchants in the merchant table. Any other merchant makes the line an error.
- **AI mark (q3):** an AI-read row is marked `AI` in the review table.
- **Save (q4):** Save stores exactly what the review showed, without asking the AI again.
- **Edit (q5):** the edit box shows the entry in short code form (e.g. `ZMT 450 11/11 dinner`), and the rules apply.
- **Data sent (q6):** only the typed line, today's date, and the category and merchant tables. No user id, name, email or other entries.
- **Limit (q7):** at most 5 plain-words lines per text box. They still count toward the 20 entries. Extra plain-words lines get `Too many plain-words lines (max 5).` There is no daily limit.
- **Messages (q8):**
  - AI unavailable: `AI help is not available right now. Type the entry in code form or try again.`
  - Answer not valid: `The AI could not read this line. Type it in code form.`

From the WI-066 Q&A:
- **q1, code form:** a line is in code form when its first word is 1 to 3 letters, whatever follows. Every other line goes to AI. All of today's errors stay exactly as now: `X 100`, `F`, `F -50`, `F abc` and `F 100 32/13` give the same messages as before.
- **q2, dates:** an AI-read date must be between 1 January of the current year (IST) and today, the same range as typed entries. An earlier date is an error for that line.

In chat:
- **Model:** the AI call uses Claude Haiku 5.5 (`claude-haiku-5-5`), changeable by the `ANTHROPIC_MODEL` setting.

## Approach

### 1. Split (pure, `app/entries/ai_read.py`)
- `is_code_form(entry)` is true when the first word matches `[A-Za-z]{1,3}`.
- In `expand_all`, every entry is still trimmed, split and counted as now (`MAX_ENTRIES` = 20, `TOO_MANY_ENTRIES`).
- Code-form entries are expanded by `expand()` exactly as today.
- The first 5 plain-words entries, in typed order, are marked for AI.
- Any further plain-words entry gets `TOO_MANY_PLAIN = "Too many plain-words lines (max 5)."` without being sent.

### 2. What the AI returns, and the rule check (pure, `app/entries/ai_read.py`)
- **The reply** is a pydantic model, `AiAnswer`:
  - `readable: bool`
  - `merchant_code: str | None`, a code from the merchant table
  - `other_merchant: str | None`, a merchant named in the line but not in the table
  - `category_code: str | None`
  - `amount: str`, a decimal string, never a float
  - `date: str`, in `YYYY-MM-DD` format
  - `note: str | None`
- **`check_answer(answer, today, codes)`** applies the same rules as a typed entry and returns `Expanded` or `EntryError`:
  - `readable` false, an `other_merchant`, an unknown `merchant_code`, or an unknown `category_code`: `The AI could not read this line. Type it in code form.` (`AI_UNREADABLE`).
  - A merchant code sets the merchant and its category (rules: "A merchant code sets both the merchant and its category"); otherwise the category code alone.
  - Amount: reuse `_parse_amount` (greater than 0, at most 2 decimals), so the same messages apply. It is stored in integer paise.
  - Date: a date that can't be parsed gives `Date is not valid.` A date after today gives `Date cannot be in the future.` A date before 1 January of the current year gives `Date is not valid.`
  - `Expanded.code` is the merchant code when there is one, otherwise the category code. `note` is trimmed, and empty becomes `None`.

### 3. The AI call (`app/entries/ai_client.py`)
- **`AiReader` protocol:** `async def read(line: str, today: date, codes) -> AiAnswer | AiFailure`.
- **`ClaudeReader`** uses `anthropic.AsyncAnthropic()`. The key comes from `ANTHROPIC_API_KEY` in the environment; it is never logged.
  - **Request:** `client.messages.parse(model=settings.anthropic_model, max_tokens=1024, output_config={"effort": "low"}, output_format=AiAnswer, system=..., messages=[...])`. Thinking stays adaptive (the default on Haiku 5.5). There is no `temperature` and no prefill.
  - **System prompt:** fixed text with the category and merchant tables, sorted. It tells the model to:
    - pick only codes from the tables;
    - fill `other_merchant` when the line names a merchant that isn't in the table;
    - never invent an amount;
    - write relative dates against the given today;
    - set `readable` to false when the line is not an expense.
  - **User message:** `Today: <YYYY-MM-DD>` and the line. Nothing else is sent (q6).
  - **Settings** (`app/entries/ai_settings.py`, pydantic `BaseSettings`):
    - `ANTHROPIC_MODEL`, default `claude-haiku-5-5`;
    - `AI_TIMEOUT_SECONDS`, default 20;
    - `AI_MAX_RETRIES`, default 1.
  - **Errors, as a chain from most to least specific** (`AiFailure.UNAVAILABLE` or `.UNREADABLE`):
    - a missing key, `AuthenticationError`, `PermissionDeniedError`, `RateLimitError`, `APIStatusError` with a 5xx status, `APIConnectionError` or `APITimeoutError`: unavailable;
    - a `stop_reason` of `refusal` or `max_tokens`, or a `parsed_output` that is missing or not valid: unreadable.
  - Haiku 5.5 has no server-side refusal fallback; a refusal counts as unreadable.
- **`get_ai_reader()`** is a FastAPI dependency returning one cached `ClaudeReader`. Tests override it with a fake reader, so no test calls the real API.

### 4. Service and routes
- **`expand_all_with_ai(text, today, codes, reader)`** (async, `app/entries/batch.py`) runs the split.
  - It reads the AI lines concurrently with `asyncio.gather` and checks each answer with `check_answer`.
  - The result is one result per entry in typed order. Each `EntryResult` gets `ai: bool`.
  - `UNAVAILABLE` and `UNREADABLE` become `AI_UNAVAILABLE` and `AI_UNREADABLE` errors for that line only.
- **`POST /entries/expand-all`** calls it, with `ai` added to `ExpandResult`. `POST /entries/expand` (one entry) stays rules-only.
- **`POST /entries/save`** follows q4 and is implemented in `save.py`:
  - The text is split again. Each reviewed item must match the fresh split:
    - the same `typed`, in the same order;
    - `ai` equals not-code-form;
    - the same over-limit errors.
  - Code-form lines are re-expanded and must equal the review, as today.
  - AI lines are not sent to the AI again. If the review showed them `ok`, their reviewed values are checked again with `check_answer`'s rules against today and the code table. If they fail, the whole save is refused with `REVIEW_CHANGED`. AI lines that showed an error are returned as failed.
  - Any mismatch refuses the save with `REVIEW_CHANGED`, as today. Valid lines are saved in one transaction, as today.
- **Stored row:** `typed_text` is the sentence as typed. `merchant_code` and `category_code` are as checked, `amount_paise` and `spent_on` are as reviewed. The database is unchanged: there are no new columns and no migration.
- **`GET /entries`:** `SavedEntry` gets `edit_text`.
  - For a code-form `typed_text`, it is `typed_text` itself.
  - Otherwise it is the short code form: `<code> <amount> <d/m> [note]`, e.g. `ZMT 450 11/11 dinner`. Whole rupees have no decimals.
  - This is valid because AI dates are always in the saved year (q2), and `dd/mm` in an edit counts from the saved day (WI-052).
- **`PUT /entries/{id}`** is unchanged: the rules apply (q5).

### 5. Web (`apps/web`)
- `node scripts/generate-client.cjs` after `openapi.json` is regenerated.
- **`EntryBox.tsx`:** an `AI` badge (Chakra `Badge`) next to the typed text of an AI-read row. There is no other change to the review or Save flow.
- **`SavedEntries.tsx`:** the edit box is prefilled with `entry.edit_text` instead of `entry.typed`.

## Files likely affected
- api:
  - new files: `app/entries/ai_read.py`, `app/entries/ai_client.py`, `app/entries/ai_settings.py`;
  - changed: `app/entries/batch.py`, `app/entries/save.py`, `app/entries/edit.py` (`edit_text`), `app/entries/routes.py`, `openapi.json`, `requirements.in` / `requirements.txt` (adds `anthropic`), `.env.example` if present.
- api tests: new `tests/entries/test_ai_read.py` and `tests/entries/test_ai_client.py`; changes to `test_batch.py`, `test_save.py`, `test_edit.py` and `test_routes.py`.
- web: `src/api/schema.d.ts`, `src/entries/EntryBox.tsx`, `src/saved/SavedEntries.tsx`, and their tests.

## Tests
- **`is_code_form`:**
  - In code form: `X 100`, `F`, `F -50`, `F abc`, `swg 340`. They give exactly today's results.
  - Going to AI: `paid 450 to zomato yesterday for dinner`, `450 zomato`, `Uber 180`.
- **`check_answer`:**
  - the sample sentence gives Zomato, Food, 45000 paise, 2026-11-11, `dinner`;
  - an unknown merchant or category gives `AI_UNREADABLE`;
  - an amount of 0 or 3 decimals gives the rule messages;
  - a future date and 31 Dec of last year give their errors.
- **Limit:** 6 plain-words lines: the 6th gets `Too many plain-words lines (max 5).` and the fake reader is called 5 times. 21 entries still give `Too many entries (max 20).`
- **`ClaudeReader`:** with a fake `AsyncAnthropic`, these map to `UNAVAILABLE` or `UNREADABLE`: a connection error, a timeout, a 429, a 5xx, a missing key, a refusal, `max_tokens`, and an output that is not valid. The test also asserts that the request carries only the line, today's date and the tables (q6).
- **Routes:**
  - `expand-all` with a fake reader marks `ai: true`;
  - a failing reader gives the right message on that line only, and the other lines are still expanded;
  - `save` stores the reviewed AI values without calling the reader;
  - a tampered AI value, or an `ai` flag on a code-form line, gives `REVIEW_CHANGED`;
  - `GET /entries` shows the `edit_text` of an AI-read entry, and that `edit_text` passes `PUT` unchanged.
- **Web:** the `AI` badge is shown on AI rows only, and the edit box is prefilled with `edit_text`.
- Both suites pass, and API coverage stays at or above 80%.

## Risks and assumptions
- **Cost and latency:** one Haiku 5.5 call per plain-words line, at most 5 per box, run concurrently. The timeout is 20 s, with 1 retry.
- **AI accuracy:** the review is the safeguard. Nothing is saved without Save, and every value is checked against the rules.
- **No key in development:** every plain-words line shows the unavailable message, and code-form entries work as before.
- **New dependency:** `anthropic` (1.x, on `httpx2`). It is added through `requirements.in` and `pip-compile`. `httpx` stays for the test client.
- **Message wording I chose:** no message was given for these two cases, so I reused existing ones. The product owner can change them.
  - A date before 1 January of the current year gives `Date is not valid.`
  - A merchant that is not in the table gives `The AI could not read this line. Type it in code form.`
- **Semicolons in a sentence split it into entries,** as for every line (REQ-277).
