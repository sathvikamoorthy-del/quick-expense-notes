# REQ-281: Delete a saved entry

Feature: FEAT-1061 User can delete a saved entry · Decision: DEC-315
Order: 7 of 7
Depends on: User can see a monthly summary by category (the totals must follow the delete)
Goal: G3 (monthly totals always match the saved entries)

## Purpose
Let the user remove an entry that should not have been saved.

## Behaviour
- The user picks one of their saved entries and deletes it.
- The entry is no longer a record and is no longer counted in the monthly summary.

## Acceptance criteria
- After deleting, the entry no longer appears among the saved entries.
- The monthly summary of its month no longer includes its amount, and a category left with no entries disappears from the summary.
- A user can delete only their own entries.

## Source documents
- docs/project/source/01-project-brief.md (step 4: "Edits or deletes an entry that is wrong"; goal "totals always match")
- docs/project/source/02-abbreviation-rules.md (Monthly summary: only categories that have entries)

## Open questions
- Is the user asked to confirm before deleting? Can a delete be undone?
- Where does the user find the entry to delete? No list of saved entries is described.
