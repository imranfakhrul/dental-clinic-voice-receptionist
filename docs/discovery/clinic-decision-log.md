# Clinic decision log: <Clinic name>
- Version: 0.1 (draft, set to 1.0 when the SME approves)
- Workshop date: YYYY-MM-DD   (format: remote | on site)
- Attendees: <name, role, organisation> per line
- Clinic SME: <name>, <role>, <work email>, <work phone>
- Open Dental admin: <name>, <work email>
- Dentist/owner (clinical and emergency questions): <name>
- BAA signatory: <name>, <role>
- Approved by SME: <name> on YYYY-MM-DD, see signoff-YYYY-MM-DD.pdf

> **No PHI in this document.** No patient names, birth dates, phone numbers, appointment details or descriptions of real cases. Only clinic staff's work contacts appear above.
> Questions and Proposed defaults are in [questionnaire.md](questionnaire.md). Before this log goes to the SME, a second team member completes [review-checklist.md](review-checklist.md).

## Status values
| Status | Meaning |
|---|---|
| `Answered` | The clinic gave its own answer. If it differs from the Proposed default, write "differs from default" in Notes. |
| `Agreed default` | The clinic accepted our Proposed value. Add a review date in Notes. |
| `Blocked` | No answer yet. Add an owner and a due date in Notes. Not allowed for Part A. |

## Part A: plan §13 questions
| ID | Question | Answer | Status | Decided by | Date | Feeds tasks | Notes |
|---|---|---|---|---|---|---|---|
| Q1 | Which identifiers are required to verify a returning patient? | | | | | P2-13, P2-14 | |
| Q2 | New-patient AI bookings: auto-confirmed or flagged for staff review? | | | | | P1-17, P2-15, P2-16 | |
| Q3 | Which appointment types may the AI book, and which need staff? | | | | | P0-02, P1-20 | |
| Q4a | Approved emergency protocol, and its owner at the clinic? | | | | | P0-03, P2-20, P2-21, P5-15 | |
| Q4b | Admin email address(es) for callback requests, including after hours? | | | | | P0-08, P2-23 | |
| Q5 | Cancellation policy, and may the AI cancel/reschedule inside the window? | | | | | P1-19, P2-18 | |
| Q6 | Insurance details in MVP scope, or routed to staff? | | | | | P1-24, P2-19, P2-24 | |
| Q7 | Google Workspace with a BAA already in use? | | | | | P0-08 | |
| Q8 | Messaging channel for confirmations and reminders: SMS, WhatsApp, or both? | | | | | P0-07a, P0-07, P4-01 | |
| Q9 | Transcript retention policy? | | | | | P1-09, P5-13 | |
| Q10 | Single or multi-location from day one? | | | | | P1-16, P1-19, P1-20 | |
| Q11 | Where will the widget live? | | | | | P2-25, P2-29 | |

## Part B: technical addendum
| ID | Question | Answer | Status | Decided by | Date | Feeds tasks | Notes |
|---|---|---|---|---|---|---|---|
| B1 | Open Dental version, hosting, eConnector running? | | | | | P0-12, P1-15, P1-16 | |
| B2 | Will the clinic enable Open Dental API access, and who does it? | | | | | P0-12 | |
| B3 | Which patient statuses count as "existing patient"? | | | | | P1-16, P2-13 | |
| B4 | May the AI create a new patient record immediately when there's no duplicate risk? | | | | | P2-15 | |
| B5 | Time zone, opening hours, holidays (12 months), reserved slots? | | | | | P1-19, P1-20 | |
| B6 | Callback response-time promise (business hours / after hours)? | | | | | P2-24, P0-03 | |
| B7 | Admin emails: full details, or case ID + link only? | | | | | P0-08, P2-23 | |
| B8 | Where is the mobile number stored in Open Dental; does the clinic text patients today? | | | | | P1-16, P4-02 | |

## Requests outside MVP
Requests the clinic raised that are outside the MVP. Nothing is promised; the tech lead decides and records the decision in `dental-ai-tasks/DECISIONS.md`.

| # | Request | Raised by | Passed to tech lead (date) | Decision (DECISIONS #) |
|---|---|---|---|---|
| | | | | |

## Revisions after sign-off
Never edit an approved row in place. Add a row here with the same ID and a suffix (`Q5-r2`), bump the version to 1.1, get SME approval again, and notify the affected tasks again.

| ID | Question | Answer | Status | Decided by | Date | Feeds tasks | Notes |
|---|---|---|---|---|---|---|---|
| | | | | | | | |

## Pending notifications
Answers for tasks whose GitHub issues don't exist yet. Post each one as a comment when that phase's issues are created. Use `dental-ai-tasks/tasks/_CONSOLIDATION.md` to find the surviving task: for example, P2-14 is now part of P2-12, and P1-17 is part of P1-16.

| Answer ID | Seed task | Survivor task | Posted on issue (date) |
|---|---|---|---|
| | | | |
