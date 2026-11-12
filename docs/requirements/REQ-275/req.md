# REQ-275: Sign in to a personal account

Feature: FEAT-1055 User can sign in to their own account · Decision: DEC-309
Order: 1 of 7
Depends on: none
Goal: enabling (no goal directly; every later story needs a signed-in user)

## Purpose
Each person keeps their own expenses. The user signs in, and from then on sees and changes only their own entries.

## Behaviour
- A user who is not signed in is asked to sign in before using the app.
- After signing in, the user reaches the entry box.
- Every saved entry belongs to the user who saved it. One user per account; there are no organisations or tenants.

## Acceptance criteria
- A user who is not signed in cannot open the entry box, the saved entries or the summary.
- After signing in, the user reaches the entry box.
- Entries saved by one user are never shown to another user.
- Each account belongs to exactly one user; there are no organisations or tenants.

## Source documents
- docs/project/source/01-project-brief.md (What the user does, step 1; Notes)
- docs/project/intent.md (Not goals: no sharing between users)

## Open questions
- How does the user sign in (email and password, Google, another provider)? The documents only say "Signs in".
- How does a new user get an account (self sign-up, invitation)?
- Is there sign-out, and is the session remembered on the laptop?
