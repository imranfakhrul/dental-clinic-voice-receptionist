# Decision log review checklist

A reviewer who is **not** the author completes this checklist before the decision log goes to the SME for approval.
This is the "testing" for P0-01, which produces documents rather than code. Record the result on GitHub issue #1.

Log version reviewed: ____  Reviewer: ____  Date: YYYY-MM-DD

## Completeness
- [ ] Every ID Q1–Q11, Q4a, Q4b and B1–B8 has exactly one row, plus any `-r2` revision rows.
- [ ] No Part A row (Q1–Q11, Q4a, Q4b) is `Blocked`.
- [ ] Every `Agreed default` row has a review date in Notes.
- [ ] Every `Blocked` row has an owner, a due date and at least one task in `Feeds tasks`.
- [ ] The header is complete: Clinic SME, Open Dental admin, dentist/owner and BAA signatory are all named (or marked "same as SME").

## Consistency
- [ ] Every answer that differs from the Proposed default in [questionnaire.md](questionnaire.md) says "differs from default" in Notes.
- [ ] No accepted answer breaks a plan principle: verifying on phone alone, giving treatment advice, live transfer, or booking without the patient's confirmation. Any such answer must be `Blocked` and escalated.
- [ ] Requests outside the MVP are listed in "Requests outside MVP", and none is promised.
- [ ] If Q10 is "multi-location", the number of locations and their Open Dental clinic names are recorded, and the tech lead has been told.

## No PHI (spec §9)
- [ ] There are no patient names, dates of birth, phone numbers, addresses, appointment details or descriptions of real cases anywhere in the log.
- [ ] Every example uses made-up data (e.g. "Jane Test, born 1985-03-14").
- [ ] If the workshop was recorded, every attendee consented, and the recording is scheduled for deletion once the log is approved.

Result: ☐ Approved for SME review  ☐ Changes needed: ____
