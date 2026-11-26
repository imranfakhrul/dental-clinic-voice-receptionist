# Clinic decision log: Example Dental Clinic
- Version: 1.2 (Q4a-r2 and Q8-r1 added 2026-11-26)
- Workshop date: 2026-11-25   (format: remote)
- Attendees:
  - Alex Sample, office manager, Example Dental Clinic
  - Jordan Example, Open Dental administrator, Example Dental Clinic
  - Dr. Casey Example, dentist/owner, Example Dental Clinic
  - Riley Tech, tech lead, our company
  - Sam Comply, compliance advisor, our company
- Clinic SME: Alex Sample, office manager, alex.sample@example.com, (555) 010-0101
- Open Dental admin: Jordan Example, jordan.example@example.com
- Dentist/owner (clinical and emergency questions): Dr. Casey Example
- BAA signatory: Dr. Casey Example, owner
- Approved by SME: Alex Sample on 2026-11-25, see [signoff-2026-11-25.pdf](signoff-2026-11-25.pdf)
- Version 1.1 approved by SME: Alex Sample on 2026-11-26 (Q4a-r2), recorded in [emergency-protocol-feedback-2026-11-26.md](emergency-protocol-feedback-2026-11-26.md)
- Version 1.2 approved by SME: Alex Sample on 2026-11-26 (Q8-r1), recorded in [patient-messaging-decision.md §6.3](../compliance/patient-messaging-decision.md#63-clinic-informed-p0-01-q8)

> *Sample values: replace them with the real workshop answers. Keep the IDs and format unchanged.*

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
| Q1 | Which identifiers are required to verify a returning patient? | Full name + DOB, plus mobile phone or home ZIP code. Never phone alone. | Agreed default | Alex Sample, office manager | 2026-11-25 | P2-13, P2-14 | Review before pilot (P6-04) |
| Q2 | New-patient AI bookings: auto-confirmed or flagged for staff review? | Flagged for staff review with an "AI-booked" note in Open Dental. | Agreed default | Alex Sample, office manager | 2026-11-25 | P1-17, P2-15, P2-16 | Review before pilot (P6-04) |
| Q3 | Which appointment types may the AI book, and which need staff? | New-patient exam, recall/cleaning and limited (emergency) exam only. Everything else goes to a callback. | Agreed default | Alex Sample, office manager | 2026-11-25 | P0-02, P1-20 | Review before pilot (P6-04); full table in [appointment-type-mapping.md](appointment-type-mapping.md) (P0-02) |
| Q4a | Approved emergency protocol, and its owner at the clinic? | Tier 1: call 911. Tier 2: urgent slot today, else URGENT callback. Never diagnose. Owner: Dr. Casey Example. | Agreed default | Dr. Casey Example, dentist/owner | 2026-11-25 | P0-03, P2-20, P2-21, P5-15 | Review before pilot (P6-04); details in P0-03 |
| Q4b | Admin email address(es) for callback requests, including after hours? | One shared mailbox for all hours: frontdesk@example.com. | Answered | Alex Sample, office manager | 2026-11-25 | P0-08, P2-23 | Matches the default (shared mailbox) |
| Q5 | Cancellation policy, and may the AI cancel/reschedule inside the window? | 24-hour notice. Inside the window the AI doesn't cancel; it creates a callback. | Agreed default | Alex Sample, office manager | 2026-11-25 | P1-19, P2-18 | Review before pilot (P6-04) |
| Q6 | Insurance details in MVP scope, or routed to staff? | Out of scope; insurance questions go to a callback. The AI may list accepted insurers (FAQ). | Agreed default | Alex Sample, office manager | 2026-11-25 | P1-24, P2-19, P2-24 | Review before pilot (P6-04) |
| Q7 | Google Workspace with a BAA already in use? | Yes. The clinic uses Google Workspace, and the Workspace BAA has been accepted. | Answered | Dr. Casey Example, dentist/owner | 2026-11-25 | P0-08 | Fact recorded; P0-08 can use Gmail |
| Q8 | Messaging channel for confirmations and reminders: SMS, WhatsApp, or both? | SMS through a provider that signs a BAA. Most patients use SMS; WhatsApp only if the compliance advisor approves it later. | Agreed default | Alex Sample, office manager | 2026-11-25 | P0-07a, P0-07, P4-01 | Review after P0-07a memo |
| Q9 | Transcript retention policy? | No transcripts stored. Raw audio never stored. | Agreed default | Alex Sample, office manager | 2026-11-25 | P1-09, P5-13 | Review before pilot (P6-04) |
| Q10 | Single or multi-location from day one? | Single location. | Agreed default | Dr. Casey Example, dentist/owner | 2026-11-25 | P1-16, P1-19, P1-20 | Review before pilot (P6-04) |
| Q11 | Where will the widget live? | Embedded on the clinic website, with a standalone page as backup. | Agreed default | Alex Sample, office manager | 2026-11-25 | P2-25, P2-29 | Review before pilot (P6-04) |

## Part B: technical addendum
| ID | Question | Answer | Status | Decided by | Date | Feeds tasks | Notes |
|---|---|---|---|---|---|---|---|
| B1 | Open Dental version, hosting, eConnector running? | Open Dental 24.3 on a local server at the clinic; the eConnector is running. | Answered | Jordan Example, OD admin | 2026-11-25 | P0-12, P1-15, P1-16 | Verify the minimum API version in P0-12 |
| B2 | Will the clinic enable Open Dental API access, and who does it? | Yes. Jordan Example enables API access and issues the customer key. | Agreed default | Jordan Example, OD admin | 2026-11-25 | P0-12 | Review in P0-12; **Verify:** the setup steps in the Open Dental API setup docs |
| B3 | Which patient statuses count as "existing patient"? | Patient and Inactive count as existing; others go to a callback. | Agreed default | Alex Sample, office manager | 2026-11-25 | P1-16, P2-13 | Review before pilot (P6-04) |
| B4 | May the AI create a new patient record immediately when there's no duplicate risk? | Yes, immediately. If there's any doubt, it creates a callback and staff create the record. | Agreed default | Alex Sample, office manager | 2026-11-25 | P2-15 | Review before pilot (P6-04) |
| B5 | Time zone, opening hours, holidays (12 months), reserved slots? | America/New_York. Mon–Thu 08:00–17:00, Fri 08:00–14:00, closed weekends. US federal holidays. Daily emergency block 11:00–12:00. New-patient block Tue/Thu 08:00–10:00. | Answered | Alex Sample, office manager | 2026-11-25 | P1-19, P1-20 | Fact recorded; first values for clinic config |
| B6 | Callback response-time promise (business hours / after hours)? | "The team will call you back within one business day"; URGENT cases the same business day. | Agreed default | Alex Sample, office manager | 2026-11-25 | P2-24, P0-03 | Review before pilot (P6-04) |
| B7 | Admin emails: full details, or case ID + link only? | Case ID + link to the admin console only. | Agreed default | Alex Sample, office manager | 2026-11-25 | P0-08, P2-23 | Review before pilot (P6-04) |
| B8 | Where is the mobile number stored in Open Dental; does the clinic text patients today? | Mobile in Wireless phone. The clinic sends appointment texts today through Open Dental's built-in texting. | Answered | Jordan Example, OD admin | 2026-11-25 | P1-16, P4-02 | Matches the default (Wireless phone) |

## Requests outside MVP
Requests the clinic raised that are outside the MVP. Nothing is promised; the tech lead decides and records the decision in `dental-ai-tasks/DECISIONS.md`.

| # | Request | Raised by | Passed to tech lead (date) | Decision (DECISIONS #) |
|---|---|---|---|---|
| 1 | Spanish-language conversations | Alex Sample, office manager | 2026-11-25 | Pending |
| 2 | Insurance eligibility checks before booking | Alex Sample, office manager | 2026-11-25 | Pending |

## Revisions after sign-off
Never edit an approved row in place. Add a row here with the same ID and a suffix (`Q5-r2`), bump the version to 1.1, get SME approval again, and notify the affected tasks again.

| ID | Question | Answer | Status | Decided by | Date | Feeds tasks | Notes |
|---|---|---|---|---|---|---|---|
| Q4a-r2 | Approved emergency protocol, and its owner at the clinic? | Unchanged except: Tier 2 → urgent slot **within 24 hours** (not only "today"), else URGENT callback. Owner: Dr. Casey Example. Full protocol: [emergency-protocol.md](emergency-protocol.md). | Answered | Dr. Casey Example, dentist/owner | 2026-11-26 | P0-03, P2-20, P2-21, P5-15 | Clarifies "today" so evening requests get a next-morning slot; differs from default wording; DECISIONS #291 |
| Q8-r1 | Messaging channel for confirmations and reminders: SMS, WhatsApp, or both? | **Now:** WhatsApp, for testing with synthetic data and our own test numbers. **Go-live:** the clinic chooses SMS or WhatsApp. SMS goes through a provider with a BAA. WhatsApp carries real patient details only after BAAs with Meta and the WhatsApp provider are signed; until then it's SMS. Our clinic said at the workshop that most patients use SMS; it confirms its choice at go-live. Messages carry only first name, clinic name, date, time and clinic phone, and only with the patient's consent. | Final | Sam Comply (advisor), Morgan Lead (sponsor); clinic informed, SME agreed | 2026-11-26 | P0-07, P0-15, P4-01, P4-02, P4-03, P4-04, P4-07, P4-08 | Closes "Review after P0-07a memo"; memo [patient-messaging-decision.md](../compliance/patient-messaging-decision.md), DECISIONS #297–#299 |

## Pending notifications
Answers for tasks whose GitHub issues don't exist yet. Post each one as a comment when that phase's issues are created. Surviving tasks come from `dental-ai-tasks/tasks/_CONSOLIDATION.md`. Phase 0 tasks (P0-02, P0-03, P0-07a, P0-07, P0-08, P0-12) are notified directly on their issues.

| Answer IDs | Seed task(s) | Survivor task | Posted on issue (date) |
|---|---|---|---|
| Q1, B3 | P2-13, P2-14 | P2-12 | - |
| Q2, B1, B3, B8, Q10 | P1-16, P1-17 | P1-16 | - |
| Q2, B4 | P2-15 | P2-15 | - |
| Q2 | P2-16 | P2-16 | - |
| Q3, Q10, B5 | P1-20 | P1-20 | - |
| Q4a | P2-20, P2-21 | P2-20 | - |
| Q4a | P5-15 | P5-07 | - |
| Q4b, B7, Q6, B6 | P2-23, P2-24 | P2-22 | - |
| Q5, Q10, B5 | P1-19 | P1-19 | - |
| Q5, Q6 | P2-18, P2-19 | P2-18 | - |
| Q6 | P1-24 | P1-22 | - |
| Q8 | P4-01 | P4-01 | - |
| Q9 | P1-09 | P1-03 | - |
| Q9 | P5-13 | P5-12 | - |
| Q11 | P2-25, P2-29 | P2-25 | - |
| B1 | P1-15 | P1-15 | - |
| B8 | P4-02 | P4-02 | - |
