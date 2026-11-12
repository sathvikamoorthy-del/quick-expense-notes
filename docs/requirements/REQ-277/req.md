# REQ-277: Expand several entries from one text box

Feature: FEAT-1057 User can type many entries at once · Decision: DEC-311
Order: 3 of 7
Depends on: User can see a short entry expanded
Goal: G2 (entering many expenses is fast)

## Purpose
The user notes many expenses in one go instead of one at a time.

## Behaviour
- One text box takes one or more entries. Entries are separated by a new line or a semicolon, and both may be mixed.
- Each entry is expanded by the rules of REQ-276 and shown with its own result.
- An error stops only that entry; the other entries are still expanded.

## Acceptance criteria
- This text box (today = 12 Nov 2026):
  ```
  F 250; SWG 340 yd
  X 100
  UBR 180 12/11 airport
  ```
  shows three expanded entries (F 250, SWG 340 yd, UBR 180 12/11 airport) and one error, Unknown code "X"., for X 100.
- New lines and semicolons both separate entries, also mixed in one text box.
- An error in one entry does not stop the other entries from being expanded.

## Source documents
- docs/project/source/01-project-brief.md (step 2; goal "Make entering many expenses fast")
- docs/project/source/02-abbreviation-rules.md (Entry format, Errors)
- docs/project/source/03-sample-entries.md (Several entries in one text box)

## Open questions
- Are empty parts (blank lines, `;;`, trailing `;`) ignored or reported?
- Is there a limit on the number of entries in one text box?
- Are results shown as the user types, or on a "review" action?
