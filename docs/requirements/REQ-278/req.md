# REQ-278: Save reviewed entries as expense records

Feature: FEAT-1058 User can save the reviewed entries · Decision: DEC-312
Order: 4 of 7
Depends on: User can type many entries at once
Goal: G1, G3 (saved records are exactly the expansion; totals are built from them)

## Purpose
Turn the reviewed entries into the user's clean expense records.

## Behaviour
- The user reviews the expanded entries, then chooses to save.
- Each valid entry is saved as a record of the signed-in user, with merchant, category, amount, date and note exactly as shown in the review.
- Entries with an error are not saved, and their errors stay shown.

## Acceptance criteria
- After saving, every valid reviewed entry exists as a record with the same merchant, category, amount, date and note.
- For the text box in 03-sample-entries.md, three entries are saved and `X 100` is not saved; its error stays shown.
- Saved records belong to the signed-in user only.
- Nothing is saved before the user chooses to save.

## Source documents
- docs/project/source/01-project-brief.md (step 3; Purpose "a clean expense record")
- docs/project/source/03-sample-entries.md (Several entries in one text box: "three entries are saved")

## Open questions
- Can the user save while some entries still have errors? The sample suggests yes (3 saved, 1 error shown); please confirm.
- After saving, what happens to the text box: is it cleared, or are the failed lines kept for fixing?
- Where does the user see the saved entries? The documents describe no list; edit and delete (REQ-280, REQ-281) need one.
- If the user saves the same text twice, are duplicate records created?
