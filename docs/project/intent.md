# Intent

## Purpose
Let a person note an expense in a few characters (such as `SWG 340 yd`) and get a clean expense record and a monthly summary by category. Primary user: a working professional tracking daily spending on a laptop.

## Goals
- G1: Every short entry expands exactly as the abbreviation rules say.
- G2: Entering many expenses is fast.
- G3: Monthly totals always match the saved entries.
- G4: An expense written in plain words, not in code form, can be entered too with AI help, and is saved only after the user reviews it.

## Not goals
- Bank or UPI sync.
- Receipt upload.
- Budgets or alerts.
- Sharing between users; one user per account, no organisations or tenants.
- Guessing codes: an unknown code stays the error `Unknown code "X".` Only lines that are not in code form go to AI.

## Success
- Every entry in `03-sample-entries.md` expands, or fails, exactly as shown there.
- The monthly summary totals match the saved entries (November 2026 sample: grand total 6138.50).
- A plain-words line such as "paid 450 to zomato yesterday for dinner" is shown for review like any other entry, and nothing is saved until the user presses Save.
