# WI-039: Email and password sign-in with JWT, sign-out and protected pages

Applications: api (primary), web
Requirement: REQ-275 Sign in to a personal account · Decision: DEC-309 · Feature: FEAT-1055

## Approach
Use the jwt-auth module that is already installed (`app/auth/jwt.py` verifies HS256 tokens, `app/auth/middleware.py` gives `require_auth`). Add what it lacks: a `users` table, a service that checks the password and issues the token, a sign-in route, and a seed for one demo user. In the web app, add a Sign in screen, keep the token in memory (the client already does this), and guard `/entries`.

## API (primary)
1. **Migration `apps/api/migrations/0003_users.sql`**: the `users` table exactly as in `docs/project/db_design.md` (id TEXT PK length 36 NOT NULL, email UNIQUE, password_hash, display_name, created_at, updated_at). Store email lower-cased, so the unique index makes the email case-insensitive. Mark `users` Final in `db_design_tables.csv` (or run `/knm:implement-db-design`).
2. **Model `apps/api/app/models/users.py`**, exported from `app/models/__init__.py`.
3. **Service `apps/api/app/auth/service.py`** (business rules live here, not in the route):
   - `normalise_email` (strip, lower case).
   - `hash_password` / `check_password` with bcrypt. Refuse passwords shorter than 8 characters when hashing.
   - `sign_in(session, email, password)`: looks up the lower-cased email and checks the hash. An unknown email and a wrong password raise the same `InvalidCredentials`. To avoid a timing difference, an unknown email is still checked against a dummy hash.
   - `issue_token(user_id)`: HS256 with `JWT_SECRET`, `sub` = user id, `iat`, `exp` = now + 60 minutes, plus `iss`/`aud` when they are configured. Add an `issue` side next to `verify_token` in `app/auth/jwt.py`, or keep it in the service; the module's contract tests must stay green.
4. **Route `apps/api/app/auth/routes.py`**: `POST /auth/sign-in` with `{email, password}`. It returns `{token, expires_in: 3600, user: {id, email, display_name}}` with 200, or 401 `{"error": "Invalid email or password."}`. The route stays thin. Register it in `app/glue/routes.py` the same way as entries.
5. **Protected routes**: `/entries/expand` already uses `require_auth`. Check that a missing, expired or wrongly signed token gives 401. Today the middleware sends 401 for bad tokens and `require_auth` handles a missing one. Later entry and summary routes (REQ-278/279/280/281) filter by `auth.user_id`; nothing to change here because the expenses table does not exist yet.
6. **Seed `apps/api/scripts/seed_users.py`**: creates (or updates) one demo user, `asha@example.com` / display name Asha. The password comes from the `DEMO_USER_PASSWORD` env var, so no plain password is committed, and only the bcrypt hash is stored. Document it in `.env.example` and `README.md`.
7. **Dependencies**: add `bcrypt` to `requirements.in`/`requirements.txt`. Regenerate `openapi.json` (scripts/export_openapi.py).
8. **Tests (pytest)**: correct sign-in; mixed-case email; wrong password and unknown email give the same message with 401; password shorter than 8 characters is refused at hashing; token `exp` is 60 minutes and an expired token gives 401 on `/entries/expand`; no token or a wrongly signed token gives 401; the DB holds a `$2b$` hash and not the password.

## Web (other)
1. Regenerate `src/api/schema.d.ts` from the new openapi.json.
2. **Auth store `src/auth/useSession.ts`** (zustand via `createStore`): `user`, `signIn(email, password)` calls `POST /auth/sign-in` and then `setAuthToken`; `signOut()` clears the token and the user. In memory only, with no localStorage or cookie, so a refresh signs the user out.
3. **`src/auth/SignIn.tsx`** (screen S01): Email, Password (at least 8 characters) and a Sign in button. A failed sign-in shows `Invalid email or password.`. There is no sign-up, forgot-password or Google button. On success it goes to `/entries`.
4. **`src/auth/RequireAuth.tsx`**: wraps `/entries` (and later the saved entries and summary pages). Signed out, it redirects to the Sign in page. Any API 401 (expired token) calls `signOut()` and goes back to Sign in (client middleware `onResponse`).
5. **Header (S02)**: shows the email and a Sign out button above the entry box.
6. **Router** (`src/app/router.tsx`): add `/sign-in`, wrap `/entries`. `/` stays "Page not found" (react-vite contract tests, decision in WI-029).
7. **Tests (Jest)**: sign-in success navigates to `/entries`; failure shows the message; `/entries` signed out shows Sign in; Sign out returns to Sign in; a fresh store (refresh) has no token; 401 from the API signs the user out. Use the fake-client pattern for component tests (jsdom has no `Request`).

## Risks
- `JWT_SECRET` must be set (at least 32 characters) or sign-in and auth fail closed with 500. Add it to `.env.example` and the test setup.
- bcrypt wheels on Windows: pin a version that has a wheel for the venv's Python.
- jwt-auth module contract tests could break if `jwt.py` is changed. If so, put token issuing in the service instead.
- The react-vite contract tests require `/` to stay not-found, so do not redirect `/` to sign-in.
- The users migration is applied with Python `sqlite3` (no `sqlite3` program on this machine).

## Assumptions
- Demo user email is `asha@example.com` (from the mock); its password is supplied through `DEMO_USER_PASSWORD` when seeding.
- No refresh token and no server-side session: a 60-minute expiry, then the user signs in again (db_design: tokens are not stored).
- "Entries never shown to another user" is enforced by this work item's `user_id` from the token. The per-user filtering of saved entries is implemented with the expenses table in the later stories; the tests here cover the 401 boundary.
- No sign-up, forgot password, lockout or other providers (out of scope).
