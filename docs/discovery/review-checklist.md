# Decision log review checklist

A reviewer who is **not** the author completes this checklist before the decision log goes to the SME for approval.
This is the "testing" for P0-01, which produces documents rather than code. Record the result on GitHub issue #1.

> *Sample values: replace them with the real review.*

Log version reviewed: 1.0  Reviewer: Sam Comply, compliance advisor  Date: 2026-11-25

## Completeness
- [x] Every ID Q1–Q11, Q4a, Q4b and B1–B8 has exactly one row, plus any `-r2` revision rows.
- [x] No Part A row (Q1–Q11, Q4a, Q4b) is `Blocked`.
- [x] Every `Agreed default` row has a review date in Notes.
- [x] Every `Blocked` row has an owner, a due date and at least one task in `Feeds tasks`.
- [x] The header is complete: Clinic SME, Open Dental admin, dentist/owner and BAA signatory are all named (or marked "same as SME").

## Consistency
- [x] Every answer that differs from the Proposed default in [questionnaire.md](questionnaire.md) says "differs from default" in Notes.
- [x] No accepted answer breaks a plan principle: verifying on phone alone, giving treatment advice, live transfer, or booking without the patient's confirmation. Any such answer must be `Blocked` and escalated.
- [x] Requests outside the MVP are listed in "Requests outside MVP", and none is promised.
- [x] (not applicable: Q10 is single location) If Q10 is "multi-location", the number of locations and their Open Dental clinic names are recorded, and the tech lead has been told.

## No PHI (spec §9)
- [x] There are no patient names, dates of birth, phone numbers, addresses, appointment details or descriptions of real cases anywhere in the log.
- [x] Every example uses made-up data (e.g. "Jane Test, born 1985-03-14").
- [x] (not applicable: not recorded) If the workshop was recorded, every attendee consented, and the recording is scheduled for deletion once the log is approved.

Result: ☒ Approved for SME review  ☐ Changes needed: -
