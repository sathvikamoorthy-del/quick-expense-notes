# REQ-280: Edit a saved entry

Feature: FEAT-1060 User can edit a saved entry · Decision: DEC-314
Order: 6 of 7
Depends on: User can see a monthly summary by category (the totals must follow the edit)
Goal: G3 (monthly totals always match the saved entries)

## Purpose
Let the user correct an entry that was saved wrong, so the records and totals are right.

## Behaviour
- The user picks one of their saved entries and changes it.
- The corrected entry replaces the old one.
- The monthly summary reflects the change, including when the new date moves the entry to another month.

## Acceptance criteria
- After an edit, the saved entry shows the new values.
- The monthly summary totals change to match the edited entry, also when the date moves it to another month.
- An edit that breaks the abbreviation rules is refused with the rule's error message (to confirm).
- A user can edit only their own entries.

## Source documents
- docs/project/source/01-project-brief.md (step 4: "Edits or deletes an entry that is wrong"; goal "totals always match")

## Open questions
- How is an entry edited: by re-typing the short form (`SWG 340 yd`) or field by field (merchant, category, amount, date, note)?
- Do the abbreviation rules and error messages apply to edits too?
- Where does the user find the entry to edit? No list of saved entries is described.
- For a relative date (`yd`) in an edit, is it relative to the day of the edit?
