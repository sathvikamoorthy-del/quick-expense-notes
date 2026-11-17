# REQ-275: Sign in to a personal account

Feature: FEAT-1055 User can sign in to their own account · Decision: DEC-309
Order: 1 of 7
Depends on: none
Goal: enabling (no goal directly; every later story needs a signed-in user)

## Purpose
Each person keeps their own expenses. The user signs in with email and password, and from then on sees and changes only their own entries.

## Behaviour
- **Signed out:** a user who is not signed in sees the Sign in screen. The entry box, the saved entries and the summary cannot be opened, and the API refuses their requests (HTTP 401).
- **Sign-in method:** email and password only. There is no Google or other provider.
- **Email:** not case-sensitive (`Asha@Example.com` and `asha@example.com` are the same account).
- **Password:** at least 8 characters. Passwords are stored only as a bcrypt hash, never in plain text.
- **Wrong details:** a wrong email or a wrong password gives the same message, `Invalid email or password.`, with HTTP 401. The message does not say which one was wrong.
- **Signed in:** after signing in, the user reaches the entry box (`/entries`).
- **Token:** a successful sign-in returns a JWT. Every request after that sends it. The token expires 60 minutes after sign-in. After that the API refuses it (HTTP 401) and the user has to sign in again.
- **Session not remembered:** the web app keeps the token in memory only, not in local storage or a cookie. Refreshing or reopening the page brings the user back to the Sign in screen.
- **Sign out:** a Sign out button forgets the token and returns the user to the Sign in screen.
- **Ownership:** every saved entry belongs to the user who saved it. A user sees and changes only their own entries. Each account belongs to exactly one user, and there are no organisations or tenants.
- **Accounts:** there is no self sign-up in this story. A seed script creates the accounts, for now one demo user, and stores the password hashed.

## Acceptance criteria
- A user who is not signed in cannot open the entry box, the saved entries or the summary. They see the Sign in screen instead.
- A request to the API without a token, or with an expired or wrongly signed token, gets HTTP 401.
- Signing in with the demo user's correct email and password takes the user to the entry box.
- Signing in with the demo user's email in different upper and lower case, and the correct password, succeeds.
- A wrong password gives `Invalid email or password.` (HTTP 401).
- An email with no account gives the same `Invalid email or password.` (HTTP 401).
- A token stops working 60 minutes after sign-in (HTTP 401), and the user has to sign in again.
- After a page refresh, the user is back at the Sign in screen.
- After Sign out, the user is at the Sign in screen and cannot open the entry box without signing in again.
- Entries saved by one user are never shown to another user.
- Each account belongs to exactly one user; there are no organisations or tenants.
- The database holds only a bcrypt hash of each password, never the password itself.

## Out of scope
- Sign-up (a later story)
- Forgot password
- Account lockout
- Google or any other sign-in provider

## Answered questions
Answered by the product owner on 17 Nov 2026:
- How does the user sign in? With email and password only, and no Google or other providers. The email is not case-sensitive. The password must be at least 8 characters. A wrong email or a wrong password gives the same message, "Invalid email or password." (HTTP 401). The draft assumption of email and password, a bcrypt hash and a JWT is confirmed.
- How does a new user get an account? There is no self sign-up in this story, which comes later. For now a seed script creates the accounts (one demo user). Passwords are stored hashed, never in plain text.
- Is there sign-out, and is the session remembered? There is a Sign out button. The session is not remembered: the token is kept in memory only, so a page refresh asks the user to sign in again. The token expires after 60 minutes.

## Source documents
- docs/project/source/01-project-brief.md (What the user does, step 1; Notes)
- docs/project/intent.md (Not goals: no sharing between users)
- docs/project/db_design.md (users table; auth by email and password with JWT)
- Product owner answers, 17 Nov 2026 (above)
