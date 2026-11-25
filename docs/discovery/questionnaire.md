# Discovery questionnaire

Each question comes with our **Proposed default**. In the workshop you can confirm it ("Agreed default"), change it ("Answered") or leave it open with an owner and a due date ("Blocked").
**The IDs are fixed and are never renumbered**, because later tasks cite them (e.g. "P0-01 Q10").
"Feeds tasks" lists the project tasks that use each answer.

Source: `dental-ai-tasks/tasks/P0-01 Run discovery workshop with pilot clinic.md` §6. Answers are recorded in [clinic-decision-log.md](clinic-decision-log.md).

## Part A: plan §13 questions
Every Part A question must end as `Answered` or `Agreed default`.

| ID | Question | Proposed default to offer | Feeds tasks |
|---|---|---|---|
| Q1 | Which identifiers does the clinic require to verify a returning patient (DOB + phone? address?) | Full name + DOB + one of: mobile phone or ZIP code. Never phone alone (§4.5). | P2-13, P2-14 |
| Q2 | Should AI-booked appointments for **new** patients be auto-confirmed or flagged for staff review? | Flagged for staff review through an "AI-booked" note/status in Open Dental (§4.6). | P1-17, P2-15, P2-16 |
| Q3 | Which appointment types may the AI book, and which need staff? | AI books new-patient exam, recall/cleaning and limited (emergency) exam only. Everything else → callback. Full table in P0-02. | P0-02, P1-20 |
| Q4a | What is the approved emergency protocol, and who at the clinic owns it? | Tier 1 → tell the patient to call 911; Tier 2 → urgent slot today, else URGENT callback; never diagnose (§4.8). Owner: the dentist. Details in P0-03. | P0-03, P2-20, P2-21, P5-15 |
| Q4b | Which admin email address(es) receive callback requests, including after hours? | One shared clinic mailbox for all hours; no personal inboxes. | P0-08, P2-23 |
| Q5 | Cancellation policy (minimum notice), and may the AI cancel or reschedule inside that window? | 24-hour notice. Inside the window the AI does not cancel; it creates a callback. | P1-19, P2-18 |
| Q6 | Is collecting insurance details in scope for the MVP, or routed to staff? | Out of scope; insurance questions go to a callback. The AI may still say which insurers the clinic accepts (FAQ). | P1-24, P2-19, P2-24 |
| Q7 | Does the clinic already use Google Workspace with a BAA, so Gmail can send admin emails? | No default: record the fact. | P0-08 |
| Q8 | Which messaging channel should confirmations and reminders use: SMS, WhatsApp, or both? | Explain first: Meta states the WhatsApp Business Platform is not HIPAA compliant, so the compliance advisor decides what WhatsApp may carry (P0-07a). Proposed: SMS through a provider that signs a BAA; WhatsApp only if the advisor approves. Record the clinic's preference and what its patients use. | P0-07a, P0-07, P4-01 |
| Q9 | Transcript retention policy (none / short-term for QA)? | No transcripts stored. If the clinic wants QA review: at most 30 days (§5). Raw audio never stored. | P1-09, P5-13 |
| Q10 | Single location or multi-location from day one? | Single location for the pilot. | P1-16, P1-19, P1-20 |
| Q11 | Where will the widget live (clinic website, standalone page, kiosk)? | Embedded on the clinic website, with a standalone page as backup. | P2-25, P2-29 |

## Part B: technical addendum
Each Part B question must be `Answered`, `Agreed default`, or `Blocked` with an owner, a due date and the task that needs it.
The Open Dental administrator may want to look up B1, B5 and B8 before the workshop.

| ID | Question | Proposed default to offer | Feeds tasks |
|---|---|---|---|
| B1 | Which Open Dental version is installed (Help → About), is it on a local server or cloud-hosted, and is the eConnector running? | No default: record the facts. | P0-12, P1-15, P1-16 |
| B2 | Will the clinic enable Open Dental API access for us, and who does it? | The clinic's Open Dental admin enables it in P0-12. **Verify:** the exact steps the clinic must take to issue a customer key, in https://www.opendental.com/site/apisetup.html | P0-12 |
| B3 | Which Open Dental patient statuses count as "existing patient" (Patient, Inactive, NonPatient, Prospective)? | Patient and Inactive count as existing; others go to a callback. | P1-16, P2-13 |
| B4 | May the AI create a new patient record in Open Dental immediately when there is no duplicate risk, or should staff create it from the callback case? (§4.9) | AI creates it immediately; any doubt → callback, staff create it. | P2-15 |
| B5 | Clinic time zone, opening hours, holidays for the next 12 months, and any reserved slots (new-patient blocks, emergency blocks)? | No default: record the facts. | P1-19, P1-20 |
| B6 | When the AI creates a callback, what should it promise the patient about response time (business hours and after hours)? | "The team will call you back within one business day"; URGENT cases the same business day. | P2-24, P0-03 |
| B7 | Should admin emails contain the full details (name, phone, DOB, situation) or only a case ID and a link to the admin console? (§4.9) | Case ID + link only. | P0-08, P2-23 |
| B8 | Where do staff store a patient's mobile number in Open Dental (Wireless phone, Home phone…), and does the clinic already text patients today? | Mobile in Wireless phone. | P1-16, P4-02 |

Section references (§4.5, §4.6, …) point to `dental-ai-tasks/plan/AI_Dental_Receptionist_Project_Plan.md`.
