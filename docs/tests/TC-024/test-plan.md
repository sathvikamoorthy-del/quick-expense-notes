# TC-024: Sign in, sign out and protected pages (REQ-275 acceptance)

Requirement: REQ-275 (approved) · Work item: WI-039 (implemented) · Applications: api (primary), web

## Scope
Every acceptance criterion of REQ-275: email and password sign-in through `POST /auth/sign-in`, the 401 boundary of the protected API routes, the 60-minute token, the in-memory session in the web app (Sign in screen, route guard, Sign out, refresh), password storage and the demo user seed. Out of scope (REQ-275): sign-up, forgot password, account lockout, Google or other providers.

## Setup
- **Database:** a SQLite file built from `apps/api/migrations/0001` to `0003_users.sql`, then seeded with `apps/api/scripts/seed_users.py`, with `DEMO_USER_PASSWORD=correct-horse-1`. This gives one user: `asha@example.com`, display name Asha.
- **API:** `JWT_SECRET` set to at least 32 characters.
- **Sign in:** `POST /auth/sign-in` with `{"email": "...", "password": "..."}`.
  - Success is `200 {"token", "expires_in": 3600, "user": {"id", "email", "display_name"}}`.
  - Failure is `401 {"error": "Invalid email or password."}`.
- **Protected route:** `POST /entries/expand` with `{"text": "SWG 340 yd"}`, which is the only protected route that exists today. It returns `401 {"error": "unauthorized"}` without a valid token.

## A. Sign in (API)
| # | Request | Expected |
|---|---|---|
| A1 | `asha@example.com` / `correct-horse-1` | 200. `expires_in` is 3600, `user.email` is `asha@example.com`, `user.display_name` is `Asha`, and the response does not contain the password. |
| A2 | The A1 token on `/entries/expand` | 200 with `ok: true` (the token opens the entry box API) |
| A3 | `ASHA@Example.com` / `correct-horse-1` | 200, the same user as A1 (email is not case-sensitive) |
| A4 | `  asha@example.com  ` / `correct-horse-1` | 200 (spaces around the email are trimmed) |
| A5 | `asha@example.com` / `wrong-password` | 401 `{"error": "Invalid email or password."}` |
| A6 | `nobody@example.com` / `correct-horse-1` | 401 with exactly the same body as A5 |
| A7 | email `""`, password `""`, both empty, or both only spaces | 401 with exactly the same body as A5, not 422 |
| A8 | `asha@example.com` / `Correct-horse-1` | 401 as in A5 (the password is case-sensitive) |

## B. Protected routes and token lifetime (API)
| # | Request to `/entries/expand` | Expected |
|---|---|---|
| B1 | No Authorization header | 401 `{"error": "unauthorized"}` |
| B2 | A token signed with a different secret | 401 |
| B3 | A token issued 59 minutes ago | 200 |
| B4 | A token issued 61 minutes ago | 401 (the token expires 60 minutes after sign-in) |
| B5 | A token from A1: decode its claims | `exp` − `iat` = 3600 seconds; `sub` = the user's id |

## C. Password storage and accounts
| # | Check | Expected |
|---|---|---|
| C1 | Read `users.password_hash` for the demo user | It starts with `$2b$` (bcrypt) and does not contain `correct-horse-1`. No column holds the password. |
| C2 | Hash a 7-character password through the service (`hash_password`) or the seed | Refused: no account is created or changed |
| C3 | Run the seed twice with different `DEMO_USER_PASSWORD` values | Still one `asha@example.com` row. Only the second password signs in. |
| C4 | Run `python -m scripts.seed_users` without `DEMO_USER_PASSWORD` (environment or `.env`) | Exit code 2 and `DEMO_USER_PASSWORD is not set`. No account is created, and no plain password is committed in the repository. |
| C5 | Look at the `users` table schema | One row per account and a unique email. There is no organisation or tenant column. |

## D. Web app
Precondition: the API from Setup is running, and the web app runs with `API_PROXY_TARGET` pointing at it.

| # | Steps | Expected |
|---|---|---|
| D1 | Signed out, open `/sign-in`. | Screen S01 with Email, Password (at least 8 characters) and Sign in. There is no sign-up, forgot-password or Google option. |
| D2 | Signed out, open `/entries`. | The Sign in screen is shown, not the entry box. |
| D3 | Type `asha@example.com` / `correct-horse-1`, press Sign in. | The app goes to `/entries`. The header shows `asha@example.com` and a Sign out button above the entry box. |
| D4 | Sign in with a wrong password. | `Invalid email or password.` is shown and the user stays on Sign in. |
| D5 | Sign in with an unknown email. | Exactly the same message as D4. |
| D6 | Leave the email or the password empty and press Sign in. | `Invalid email or password.` is shown and no request is sent (check the network tab). |
| D7 | Signed in at `/entries`, refresh the page. | Back at the Sign in screen. Local storage, session storage and cookies hold no token. |
| D8 | Signed in, press Sign out. | The Sign in screen is shown. Opening `/entries` again shows Sign in. |
| D9 | Signed in, let the token expire (or replace it with one older than 60 minutes), then press Expand. | The API answers 401, and the app signs the user out and shows Sign in. |
| D10 | Open `/`. | "Page not found", not a redirect (react-vite contract, WI-029). |

## E. Entries of one user are not shown to another
The saved entries and summary do not exist yet: there is no expenses table, and they come with REQ-278 to REQ-281. For now, this criterion can only be tested at its boundary.
| # | Check | Expected |
|---|---|---|
| E1 | A request without a valid token | 401 (B1, B2, B4). Nobody's data is reachable signed out. |
| E2 | A token's `sub` | It is the signed-in user's id (B5). Later stories filter by this id. |

**Deferred:** "Entries saved by one user are never shown to another user" needs two users, A and B, each saving entries, where each sees only their own in the saved entries and the summary. This test belongs to the test cases of REQ-278 and REQ-279 and is not run here.

## Automated coverage
| Rows | Automated in | Gap |
|---|---|---|
| A1, A2 | `apps/api/tests/auth/test_routes.py::test_correct_details_return_a_token_that_opens_the_entry_box` | |
| A3 | `test_routes.py::test_email_in_different_case_signs_in`, `test_service.py::test_sign_in_ignores_email_case` | |
| A4 | `test_service.py::test_email_is_trimmed_and_lower_cased` | Covered at the service level only, not through the route. |
| A5, A6 | `test_routes.py::test_wrong_password_is_401_with_the_shared_message`, `test_unknown_email_is_401_with_the_same_message`, `test_service.py::test_bad_details_all_raise_the_same_error` | |
| A7 | `test_routes.py::test_sign_in_empty_email_or_password_is_401` | |
| A8 | | Not automated; manual. |
| B1, B2 | `test_routes.py::test_no_token_is_401`, `test_wrongly_signed_token_is_401` | |
| B3, B4 | `test_routes.py::test_token_stops_working_60_minutes_after_sign_in` | |
| B5 | `test_service.py::test_token_expires_60_minutes_after_issue` | |
| C1 | `test_service.py::test_hash_is_bcrypt_and_never_the_password`, `test_database_holds_only_the_hash` | |
| C2 | `test_service.py::test_password_shorter_than_8_characters_is_refused` | |
| C3 | `test_service.py::test_upsert_updates_an_existing_account`, `test_seed_script_creates_the_demo_user` | |
| C4, C5 | | Not automated; manual. |
| D1, D3 to D6 | `apps/web/tests/auth/SignIn.test.tsx`, `useSession.test.ts` (fake client, plus the real client in node) | Not run against a live API. D1 to D9 are also run by hand. |
| D2, D8, D9 | `apps/web/tests/auth/RequireAuth.test.tsx`, `useSession.test.ts` | |
| D7 | `useSession.test.ts`: "a fresh page (module reload) starts signed out" | |
| D10 | `RequireAuth.test.tsx` (routes), `apps/web/tests/modules/react-vite/contract/app.test.tsx` | |

- api: `.venv\Scripts\python -m pytest -q` (in `apps/api`)
- web: `npx jest --ci` (in `apps/web`)

**Pass:** every row in A to E gives the expected result, both suites pass, and the api coverage gate (80%) holds. The deferred cross-user check is tracked in the REQ-278 and REQ-279 test cases.
