# TC-045: Plain-words entries read by AI (REQ-438 acceptance)

Requirement: REQ-438 (approved) · Work item: WI-066 (implemented) · Applications: api (primary), web

## Scope
Every acceptance criterion of REQ-438, and every product-owner answer recorded in WI-066's impl.md (23 Nov 2026):
- REQ-438 q1 to q8;
- WI-066 q1 (code form) and q2 (dates);
- the model choice (Claude Haiku 5.5, set by `ANTHROPIC_MODEL`);
- the fix of 24 Nov 2026: a missing key or a missing package gives the unavailable message.

Tested through `POST /entries/expand-all`, `POST /entries/save`, `GET /entries` and `PUT /entries/{id}`, the entry box and `/saved-entries`.

Out of scope:
- The rules of code-form entries (TC-014 to TC-033). Here they are only checked to be unchanged.
- How good the AI's reading is beyond the sample sentence. Every AI answer is checked by the rules, and the user reviews it before Save.

## Setup
- **Database:** a SQLite file built from every migration in `apps/api/migrations` (0001 to 0004), with user Asha `11111111-1111-1111-1111-111111111111`.
- **Today:** 12 Nov 2026 in IST. The API's clock (`today_ist`) is pinned.
- **Signed in:** `Authorization: Bearer <token>`, with Asha's id as `sub`.
- **The AI:** every automated row uses a fake AI reader that answers from a table. No automated test calls the Claude API.
  - The fake reader answers the sample sentence `paid 450 to zomato yesterday for dinner` with: merchant `ZMT`, amount `450`, date `2026-11-11`, note `dinner`.
  - It answers any other line as unreadable, unless a row says otherwise.
- **The live rows (G):** `ANTHROPIC_API_KEY` set in `apps/api/.env`, and `ANTHROPIC_MODEL` unset (default `claude-haiku-5-5`).
- **Messages:**
  - unavailable: `AI help is not available right now. Type the entry in code form or try again.`
  - unreadable: `The AI could not read this line. Type it in code form.`
  - limit: `Too many plain-words lines (max 5).`

## A. Code-form lines are unchanged and never sent to AI (acceptance 1; WI-066 q1)
| # | Steps | Expected |
|---|---|---|
| A1 | Expand `X 100` | `Unknown code "X".`, `ai` false, and the AI is not asked |
| A2 | Expand `F`, `F -50`, `F abc` and `F 100 32/13` | `Amount is missing.`, `Amount must be greater than 0.`, `Amount must be greater than 0.` and `Date is not valid.`: the same as before WI-066, and the AI is not asked |
| A3 | Expand `swg 340 yd`, `SWG 340` and `  ola 90  ` | Expanded by the rules (Swiggy 340.00 on 11 Nov; Swiggy 340.00 on 12 Nov; Ola 90.00 on 12 Nov), `ai` false |
| A4 | Expand the 03-sample-entries.md text box `F 250; SWG 340 yd\nX 100\nUBR 180 12/11 airport` | 3 entries and 1 error, as in TC-029. The AI is not asked. |
| A5 | Which lines go to AI | The sample sentence, `Uber 180`, `450 zomato`, `spent 200 on groceries`, `F1 100` and `₹450 tea` go to AI: their first word is not 1 to 3 letters. |

## B. A plain-words line is read and marked AI (acceptance 2; q3)
| # | Steps | Expected |
|---|---|---|
| B1 | Expand `F 250\npaid 450 to zomato yesterday for dinner` | Line 2: `ok`, `ai` true, entry Zomato, Food, 450.00 (45000 paise), 2026-11-11, note `dinner`. Line 1: `ai` false. |
| B2 | Answer with category `F` and no merchant, with the code in lower case (`f`) | Food with no merchant; codes are not case-sensitive |
| B3 | Answer with merchant `ZMT` and category `S` | Food: the merchant sets its category |
| B4 | The review table in the entry box | An `AI` badge next to the typed text of AI rows only, including an AI row that shows an error |

## C. The AI answer follows the rules (acceptance 3; REQ-438 q2; WI-066 q2)
| # | AI answers | Expected error for that line |
|---|---|---|
| C1 | `readable` false; a merchant not in the table (`other_merchant` Dominos, or code `DOM`); no code; a category code given as a merchant, or the reverse; category `Q` | `The AI could not read this line. Type it in code form.` |
| C2 | Amount `0`, `-5`, empty, or `four fifty` | `Amount must be greater than 0.` |
| C3 | Amount `4.505` | `Amount must have at most 2 decimals.` |
| C4 | Amounts `1.5k`, `799.50` and ` 450 ` | Allowed: 150000, 79950 and 45000 paise |
| C5 | Date `2026-11-13` | `Date cannot be in the future.` |
| C6 | Date `2025-12-31` (before 1 January), `yesterday` (not a date), or `2026-02-30` | `Date is not valid.` |
| C7 | Dates `2026-01-01` and `2026-11-12` | Allowed |
| C8 | Note `tea; snacks\nlate` | Stored as `tea snacks late`: a note never holds an entry separator |

## D. AI failures stop only that line (acceptance 4; q8; fix of 24 Nov 2026)
| # | Steps | Expected |
|---|---|---|
| D1 | The AI cannot be reached: a connection error, a timeout, 401, 403, 429, 500 or 529 | The unavailable message on that line. The other lines are still expanded. |
| D2 | The AI's answer can't be used: no parsed output, `refusal`, `max_tokens`, output that isn't JSON, or an answer that fails validation | The unreadable message on that line |
| D3 | **No `ANTHROPIC_API_KEY`** anywhere (settings, `.env` or environment), or an empty or blank key, with the real reader | `200`. The plain-words line gets the unavailable message, with `ai` true. `F 250` in the same box is expanded. The SDK is not called. No `500 internal-error`. |
| D4 | **The `anthropic` package is missing** (a fresh interpreter where `import anthropic` fails) | The API starts. `F 250` expands, and the plain-words line gets the unavailable message (`200`). |
| D5 | The SDK raises a plain `TypeError` ("Could not resolve authentication method"), or the reader raises any error | The unavailable message on that line only |
| D6 | In the browser, with no key: type `F 250` and the sample sentence, then Expand | Row 1 is expanded. Row 2 shows `AI` and `Error: AI help is not available right now. Type the entry in code form or try again.` Save stores 1 entry. |

## E. Limits (q7)
| # | Steps | Expected |
|---|---|---|
| E1 | Six plain-words lines in one box | The AI is asked for the first 5 only. The 6th gets `Too many plain-words lines (max 5).`, with `ai` true. |
| E2 | 18 code-form lines and 3 plain-words lines (21 entries) | `Too many entries (max 20).` for the whole box: plain-words lines count toward the 20. |
| E3 | Save the six-line box | 5 saved. The 6th is returned as failed with the limit message. |

## F. Save, edit and the data sent (acceptance 5; q4, q5, q6)
| # | Steps | Expected |
|---|---|---|
| F1 | Expand `F 250` and the sample sentence, then Save the review unchanged | 2 saved. The AI is not asked again. Stored row: `typed_text` is the sentence, merchant `ZMT`, category `F`, 45000 paise, 2026-11-11, note `dinner`. |
| F2 | Save a review whose AI line showed the unavailable message | Only `F 250` is saved. The AI line is returned as failed with its message. |
| F3 | Change the reviewed AI line before Save: amount 0, a future date, a date before 1 January, merchant `DOM`, category Travel for Zomato, merchant Swiggy for `ZMT`, no code, a changed sentence, `ai` false on the AI line, or `ai` true on a code-form line | `The entries changed since the review. Press Expand to review them again.` Nothing is saved. |
| F4 | Review on 31 Dec 2026 a line dated 1 Jan 2026, then save on 1 Jan 2027 | Refused (`REVIEW_CHANGED`): the date is now before 1 January |
| F5 | Save a reviewed AI value changed to another value that is still valid (e.g. 45.00 instead of 450.00) | Saved as sent. q4 says Save stores what the review showed, and the server keeps no copy of the AI answer. This row records the agreed behaviour. |
| F6 | `GET /entries` after F1 | The sentence entry has `typed` set to the sentence and `edit_text` `ZMT 450 11/11 dinner`. A code-form entry has `edit_text` equal to `typed`. A category entry gives e.g. `S 799.50 5/1`. |
| F7 | `PUT /entries/{id}` with that `edit_text`, unchanged | `ok`. The values stay ZMT, 450.00, 2026-11-11, `dinner`, and `typed` becomes `ZMT 450 11/11 dinner`. |
| F8 | On `/saved-entries`, press Edit on the sentence entry | The row shows the sentence. The edit box is prefilled with `ZMT 450 11/11 dinner`. |
| F9 | The request to Claude for the sample sentence | Model `claude-haiku-5-5`, effort `low`, structured output `AiAnswer`. The system prompt has the instructions and the sorted code tables. The user message is exactly `Today: 2026-11-12\nLine: paid 450 to zomato yesterday for dinner`. Nothing else is sent: no user id, name, email or other entries. |
| F10 | Set `ANTHROPIC_MODEL=claude-sonnet-5-5` | That model is used in the request |

## G. Live check with the real Claude API (manual, needs a key; a few cents)
Precondition: `ANTHROPIC_API_KEY` set in `apps/api/.env`, the API and web app running, and signed in as Asha. The real today is used, so dates count from the day of the test.

| # | Steps | Expected |
|---|---|---|
| G1 | Expand `paid 450 to zomato yesterday for dinner` | Zomato, Food, 450.00, yesterday's date, note `dinner` (or a close note such as `for dinner`), marked `AI` |
| G2 | Expand `X 100` and `paid 450 to dominos for pizza` in one box | `X 100` gives `Unknown code "X".` and is not marked AI. The Dominos line gives the unreadable message. |
| G3 | Save G1, then open `/summary` | Food increases by 450.00 |

G is not required to pass the test case when no key is available. Record the date and result when it is run.

## Automated coverage
| Rows | Automated in |
|---|---|
| A1 to A5 | `apps/api/tests/entries/test_ai_read.py` (`test_lines_whose_first_word_is_*`, `test_every_other_line_goes_to_ai`), `test_batch.py` (`test_code_form_lines_are_planned_*`, `test_a_code_form_line_is_never_sent_to_ai`, and the existing REQ-277 tests), `test_routes.py` (the existing expand-all tests) |
| B1 to B3 | `test_ai_read.py` (`test_the_sample_sentence_*`, `test_a_category_answer_*`, `test_a_merchant_sets_its_category_*`), `test_batch.py` (`test_plain_words_lines_are_read_by_ai_and_marked`), `test_routes.py` (`test_expand_all_reads_a_plain_words_line_with_ai_and_marks_it`) |
| B4 | `apps/web/tests/entries/EntryBox.test.tsx` (`marks a plain-words line read with AI help, and only that line`) |
| C1 to C8 | `test_ai_read.py` (`test_an_unknown_merchant_*`, `test_the_amount_follows_the_rules`, `test_valid_amounts_*`, `test_the_date_must_lie_*`, `test_1_january_and_today_*`, `test_a_note_never_holds_*`) |
| D1, D2 | `test_ai_client.py` (`test_the_ai_is_unavailable_when_it_cannot_be_reached`, `test_an_answer_that_cannot_be_used_is_unreadable`), `test_batch.py` (`test_an_ai_failure_stops_only_that_line`), `test_routes.py` (`test_an_ai_failure_shows_on_that_line_only`) |
| D3 | `test_routes.py` (`test_a_plain_words_line_without_an_api_key_gets_the_unavailable_message`), `test_ai_client.py` (`test_without_an_api_key_*`, `test_an_empty_api_key_counts_as_none`, `test_an_api_key_in_the_environment_*`) |
| D4 | `test_ai_client.py` (`test_without_the_anthropic_package_*`, `test_the_api_starts_and_answers_without_the_anthropic_package`, which runs in a separate interpreter) |
| D5 | `test_ai_client.py` (`test_the_sdk_refusing_to_authenticate_is_unavailable`), `test_batch.py` (`test_a_reader_that_raises_*`) |
| E1 to E3 | `test_batch.py` (`test_at_most_five_*`, `test_plain_words_lines_still_count_*`), `test_save.py` (`test_the_sixth_plain_words_line_is_not_saved`) |
| F1 to F4 | `test_save.py` (`test_an_ai_read_line_is_saved_*`, `test_an_ai_read_category_entry_*`, `test_an_ai_failure_the_user_saw_*`, `test_an_ai_review_that_does_not_hold_saves_nothing`, `test_an_ai_read_line_reviewed_yesterday_*`), `test_routes.py` (`test_save_stores_the_reviewed_ai_line_*`, `test_save_refuses_an_ai_flag_on_a_code_form_line`) |
| F6, F7 | `test_edit.py` (`test_edit_text_is_*`, `test_saving_the_edit_text_*`), `test_routes.py` (`test_the_list_gives_the_edit_text_*`) |
| F8 | `apps/web/tests/saved/SavedEntries.test.tsx` (`pre-fills the edit of an entry read with AI help *`) |
| F9, F10 | `test_ai_client.py` (`test_the_request_carries_only_*`, `test_the_system_prompt_*`, `test_the_model_can_be_changed_*`, `test_a_model_set_by_the_setting_is_used`) |

Gaps:
- **F5** is checked by a script, by saving a changed valid value through the API.
- **D6** is a manual browser step with no key.
- **G** needs a real key and is manual.

How to run:
- api: `.venv\Scripts\python -m pytest -q` (in `apps/api`)
- web: `npx jest --ci` (in `apps/web`)

**Pass:** rows A to F give the expected results, both suites pass, and the API coverage gate (80%) holds. G is recorded when a key is available.
