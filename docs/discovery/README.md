# Discovery (P0-01)

This folder holds the clinic's decisions that the rest of the project depends on. Examples: who counts as a verified patient, what the AI may book, how emergencies are handled, where callback emails go, and how long transcripts are kept.
Task spec: `dental-ai-tasks/tasks/P0-01 Run discovery workshop with pilot clinic.md` (GitHub issue #1).

## Files
| File | Purpose |
|---|---|
| [pre-read.md](pre-read.md) | Plain-language product summary. Send it to the clinic with the questionnaire at least 3 business days before the workshop. |
| [questionnaire.md](questionnaire.md) | Questions Q1–Q11 (with Q4a/Q4b) and B1–B8, each with our Proposed default. The IDs are fixed. |
| [clinic-decision-log.md](clinic-decision-log.md) | The answers, filled in live during the workshop and approved by the clinic SME. Downstream tasks cite it as "P0-01 Q10". |
| [review-checklist.md](review-checklist.md) | Checks a second team member completes before the log goes to the SME. |
| `signoff-YYYY-MM-DD.pdf` | The SME's written approval ("I approve version 1.0 of the clinic decision log"), added after sign-off. |

## Workshop: 90 minutes
| Minutes | Part |
|---|---|
| 15 | Product walkthrough (using the pre-read) |
| 45 | Part A: questions Q1–Q11 |
| 20 | Part B with the Open Dental admin: questions B1–B8 |
| 10 | Recap of `Blocked` items, with owners and due dates |

Attendees from the clinic: the SME (usually the office manager), the Open Dental admin, the dentist/owner and the BAA signatory.

## Rules
- **No PHI.** No BAA exists yet between the clinic and our company. Use only made-up examples ("Jane Test, born 1985-03-14"). Don't screen-share live Open Dental patient screens.
- **Recording:** only if every attendee consents. Delete the recording once the log is approved.
- **Read back each answer** before moving to the next question.
- **Never accept an answer that breaks a plan principle** (verifying on phone alone, treatment advice, live transfer, booking without confirmation). Mark it `Blocked` and escalate.
- **After sign-off,** never edit an approved row. Add a revision row (`Q5-r2`), bump the version and get approval again.
- **Notify downstream tasks:** comment each answer on the GitHub issue of every task in "Feeds tasks", and state any conflict with that task's Proposed default.
