---
id: P0-01
title: Run discovery workshop with pilot clinic
milestone: P0
epic: E0.1
size: M
labels: area:compliance, type:docs
depends_on: none
status: approved
---

# P0-01: Run discovery workshop with pilot clinic

## 1. Summary
Prepare and run a discovery workshop with the pilot dental clinic. Get written, signed-off answers to the 11 open questions in plan §13 (Part A) and to 8 technical questions that later tasks need (Part B). The output is a **clinic decision log** (`docs/discovery/clinic-decision-log.md`) plus a named clinic contact (the **Clinic SME**) who signs off decisions for the rest of the project. Done means: every Part A question is `Answered` or `Agreed default`, every Part B question has an answer or a named owner and due date, the SME has approved the log in writing, and the log contains no PHI.

## 2. Why this matters
This is the root of the task graph. The product's rules come from the clinic, not from us: who counts as verified (§4.5), what the AI may book (§4.6), how emergencies are handled (§4.8), where callback emails go (§4.9), how long transcripts are kept (§5). Without these answers, seven Phase 0 tasks are blocked (P0-02, P0-03, P0-04, P0-07, P0-08, P0-09, P0-12), and Phase 1–2 tasks would hard-code guesses that are expensive to undo, for example the verification policy in P2-14 or the Open Dental phone-search mode in P1-16.

No patient sees this task directly. Clinic staff see its effect everywhere: the AI follows **their** policies, and the SME named here signs off emergency scripts later (P5-15).

Plan references: §13 (open questions), §8 Phase 0, §4.5, §4.6, §4.8, §4.9, §5.

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P0, Discovery & Compliance Foundation**.
- **Before the workshop:** read plan §1 and §2 (about 2 pages).
- **Pilot clinic:** the first real clinic that will use the system (Phase 6). Its answers set the defaults for every later clinic.
- **Clinic SME:** subject-matter expert at the clinic, usually the office manager. Answers workflow questions and signs off decisions. See plan §10.
- **Open Dental:** the clinic's practice-management software and our source of truth for patients and appointments. We talk to it through the Open Dental API, which reaches the clinic's database through a program called the **eConnector** running at the clinic. Docs: https://www.opendental.com/site/apispecification.html
- **PHI and BAA:** PHI (Protected Health Information) is anything that identifies a patient together with care data. Under HIPAA, a vendor may only receive PHI after a **BAA** (Business Associate Agreement) is signed. The clinic ↔ company BAA is prepared in P0-09, **after** this task, so **no PHI may be shared with us during this workshop**. See GLOSSARY.md.
- **Proposed vs Verify:** our own design choices are marked "Proposed:" until approved; unconfirmed facts about external systems are marked "Verify:". The workshop is where many "Proposed" defaults become clinic decisions.

## 4. Scope
**In scope**
- Identifying the clinic contacts: SME, Open Dental administrator, dentist/owner (for clinical and emergency questions), and the person who can sign BAAs.
- A pre-read for the clinic and a questionnaire with our Proposed default for every question.
- Running the workshop (remote or on site) and recording answers live.
- Creating the clinic decision log in the format in §6, and getting written SME approval.
- Telling the owners of downstream tasks which answers affect them.

**Out of scope** (and which task covers it)
- The full appointment-type mapping table (reason → type → duration → providers) → P0-02. P0-01 records only which kinds of appointments the AI may book.
- Emergency trigger phrases and fixed scripts → P0-03 (draft) and P5-15 (final sign-off). P0-01 records only the protocol owner and the Tier 1/2 headline rules.
- Conversation flow diagrams → P0-04
- Choosing and signing the WhatsApp BSP → P0-07
- Choosing the admin email route and signing its BAA → P0-08
- Drafting the clinic ↔ company BAA → P0-09
- Getting Open Dental API keys and the test database → P0-12
- Turning answers into clinic configuration (hours, holidays, rules) → P1-19
- Any scope change the clinic asks for (insurance verification, SMS, other languages, phone calls) → not decided here; logged as a request for the tech lead (see §8)

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| None | - | This task can start immediately. |
| Pilot clinic availability (external, not a task) | A confirmed clinic and an SME willing to attend | If no clinic is confirmed yet, prepare the pre-read and questionnaire (steps 1–3 in §7) and record "Pilot clinic not confirmed" in §14 with the project sponsor as owner. |
| Product repo (created in P1-01) | A place for `docs/discovery/` | Proposed: until P1-01 exists, keep the log in a shared document with the same structure, and record its link in this task. P1-01 moves it into the repo unchanged. |

## 6. Interface contract
This task produces documents, not code. The "interface" is the structure of the decision log, because other tasks cite it as "P0-01 Q10" or "P0-01 B3". **The IDs Q1–Q11 (with Q4a/Q4b) and B1–B8 are fixed and must not be renumbered.**

**Files** (Proposed):
| Path | Content |
|---|---|
| `docs/discovery/clinic-decision-log.md` | The decision log (format below) |
| `docs/discovery/pre-read.md` | Plain-language product summary sent to the clinic |
| `docs/discovery/signoff-YYYY-MM-DD.pdf` | The SME's approval email, exported to PDF |
| `README.md` (repo root) | One line linking to the decision log |

**Log header**
```markdown
# Clinic decision log: <Clinic name>
- Version: 1.0
- Workshop date: YYYY-MM-DD   (format: remote | on site)
- Attendees: <name, role, organisation> per line
- Clinic SME: <name>, <role>, <work email>, <work phone>
- Open Dental admin: <name>, <work email>
- BAA signatory: <name>, <role>
- Approved by SME: <name> on YYYY-MM-DD, see signoff-YYYY-MM-DD.pdf
```

**One row per question**
| Field | Meaning |
|---|---|
| `ID` | Q1–Q11, Q4a, Q4b, B1–B8. Fixed. |
| `Question` | Text from the questionnaire below |
| `Answer` | The clinic's answer in one or two plain sentences |
| `Status` | `Answered` · `Agreed default` (the clinic accepted our Proposed value; add a review date) · `Blocked` (add owner and due date) |
| `Decided by` | Name and role of the person who answered |
| `Date` | YYYY-MM-DD |
| `Feeds tasks` | Task IDs that consume this answer |
| `Notes` | Review date, owner/due date, conflicts, follow-ups |

**Example rows**
| ID | Question | Answer | Status | Decided by | Date | Feeds tasks | Notes |
|---|---|---|---|---|---|---|---|
| Q1 | Which identifiers are required to verify a patient? | Full name + DOB, plus mobile phone or home ZIP code. Never phone alone. | Answered | J. Doe, office manager | 2026-12-03 | P2-13, P2-14 | - |
| Q9 | Transcript retention? | No transcripts stored. | Agreed default | J. Doe, office manager | 2026-12-03 | P5-13, P1-09 | Review before pilot (P6-04) |
| B1 | Open Dental version and eConnector? | Unknown on the day | Blocked | - | 2026-12-03 | P0-12, P1-15, P1-16 | Owner: clinic OD admin, due 2026-12-10 |

### Questionnaire with Proposed defaults

**Part A: plan §13 questions.** All must end `Answered` or `Agreed default`.

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

**Part B: technical addendum.** Each must be `Answered`, `Agreed default`, or `Blocked` with an owner, a due date and the task that needs it.

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

## 7. Implementation guide
1. **Find the people.** With the project sponsor, confirm the pilot clinic and name four people: SME, Open Dental admin, dentist/owner, BAA signatory (one person may hold several roles). Write their names into the log header. Work contact details of staff are not PHI, but still keep the log in a private repo or private shared doc.
2. **Write the pre-read** (`docs/discovery/pre-read.md`, at most 2 pages, no jargon): what the AI does and does not do (use plan §2), what "no live transfer" means, the callback flow, and the rule "please don't show or tell us about real patients until the BAA is signed".
3. **Prepare the questionnaire** from §6, with our Proposed default for each question, so the clinic can confirm a default instead of starting from nothing. Proposed: send the pre-read and questionnaire at least 3 business days before the workshop, so the Open Dental admin can look up B1, B5 and B8 in advance.
4. **Run the workshop.** Proposed agenda (90 minutes): product walkthrough (15) → Part A (45) → Part B with the Open Dental admin (20) → recap of `Blocked` items, with owners and dates (10). Fill in the log live and read each answer back before moving on. Rules:
   - Use only made-up examples ("Jane Test, born 1985-03-14").
   - Don't screen-share live Open Dental patient screens.
   - Don't record the meeting unless every attendee agrees. If it is recorded, store the recording with the same access rules as the log, and delete it once the log is approved.
5. **Handle conflicts on the spot** using the rules in §8. Never accept an answer that breaks a plan principle; mark it `Blocked` and escalate.
6. **Send the log for approval.** Proposed: within 2 business days, send version 1.0 to the SME and ask for a reply that says "I approve version 1.0 of the clinic decision log". Save the reply as `docs/discovery/signoff-YYYY-MM-DD.pdf`.
7. **Publish.** Commit the log, pre-read and sign-off under `docs/discovery/` and link the log from the repo `README.md`. If the repo doesn't exist yet, put them in the shared doc and note this in the P1-01 issue.
8. **Notify downstream owners.** For each row, comment on the GitHub issue of every task in `Feeds tasks` with the answer. If an answer contradicts a task spec's Proposed default (for example B3 vs P1-16's `OD_SEARCH_STATUSES`), say so explicitly in the comment.
9. **Changes after sign-off.** Never edit an approved row in place. Add a new row with the same ID and the suffix `-r2` (e.g. `Q5-r2`), bump the version to 1.1, get SME approval again, and repeat step 8.

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| The clinic can't answer a question on the day | Offer the Proposed default. If they accept it → `Agreed default` with a review date. If not → `Blocked` with an owner and a due date. |
| An answer breaks a plan principle: verify on phone alone, give treatment advice, live transfer, book without confirming with the patient | Don't accept it. Explain the reason (§1 principle 4, §4.5). Mark it `Blocked` and escalate to the tech lead and compliance advisor. |
| The clinic asks for something outside the MVP (insurance verification, SMS, other languages, phone calls, intake forms) | Record it in a "Requests outside MVP" section at the end of the log. Don't promise anything. The tech lead decides and records the decision in DECISIONS.md. |
| Q10 answer is "multi-location" | Record the number of locations and their Open Dental clinic names. Tell the tech lead the same day: P1-16, P1-19 and P1-20 need re-sizing. |
| The clinic shows or mentions real patient data (a screen-share, a real case) | Stop the share, don't write it down, and remind everyone that no BAA exists yet. If anything was written down, delete it before the log is shared. Tell the compliance advisor. |
| No SME can be named | The task can't be finished. Mark it blocked and escalate to the project sponsor. All P0 tasks that depend on this one stay blocked. |
| Open Dental is too old for the API, or the eConnector isn't running (B1) | Record the facts as `Blocked`. Raise it as a project risk with the tech lead, because P0-12 and all of E1.3 depend on API access. **Verify:** the minimum supported version and eConnector requirement in the Open Dental API docs. |
| The clinic doesn't use Google Workspace (Q7) | Record "No". P0-08 must then pick a transactional email service with a BAA. |
| The SME changes an answer after sign-off | New row and new version, following step 9 in §7. |
| Attendees disagree (for example the dentist and the office manager) | Record both views in Notes. Mark it `Blocked`, with the clinic owner/dentist as decision owner. |

## 9. Security, HIPAA and PHI
- **No PHI.** No BAA exists between the clinic and our company yet (P0-09), so no PHI may be shared, written down or recorded in this task. All examples are synthetic.
- **Personal data that is not PHI:** names, roles, work emails and work phones of clinic staff in the log header. Keep the log in a private repository or private shared document. Don't post it in public channels.
- **Recording:** only with every attendee's consent, and deleted once the log is approved (§7 step 4).
- **Review:** before approval, a second team member reads the log and confirms it contains no patient names, DOBs, phone numbers, appointment details or descriptions of real cases.
- **Audit events:** not applicable. No system exists yet. The SME sign-off PDF is the record of who decided what.

## 10. Testing
Not applicable as automated tests: this task produces documents, not code. Instead, a reviewer (not the author) checks the log against this list before it goes to the SME:
- Every ID Q1–Q11, Q4a, Q4b and B1–B8 has exactly one row (plus any `-r2` rows).
- No Part A row is `Blocked`.
- Every `Agreed default` row has a review date; every `Blocked` row has an owner, a due date and at least one task in `Feeds tasks`.
- The header is complete, with all four named roles (or "same as SME").
- The log contains no PHI (§9).
- Every answer that differs from the Proposed default in §6 is marked in Notes ("differs from default").

## 11. Acceptance criteria
- [ ] `docs/discovery/clinic-decision-log.md` (or the interim shared doc) exists, with the header and row format from §6
- [ ] Q1–Q11 (with Q4a and Q4b) each have a row with status `Answered` or `Agreed default`; none is `Blocked`
- [ ] B1–B8 each have a row; every `Blocked` row names an owner, a due date and the task that needs it
- [ ] A Clinic SME is named with role and work contact, and has approved version 1.0 in writing (`signoff-YYYY-MM-DD.pdf` saved)
- [ ] The log is linked from the repo `README.md`, or the shared-doc link is recorded in the P1-01 issue
- [ ] A second team member confirmed in writing (PR review or comment) that the log contains no PHI
- [ ] The GitHub issue of every task listed in a `Feeds tasks` column has a comment with the relevant answer(s)
- [ ] Any requests outside the MVP are listed in the log and passed to the tech lead

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI: not applicable (no code); the reviewer checklist in §10 is completed instead
- [ ] PR reviewed (HIPAA review if labelled `phi`): the log PR is reviewed; no `phi` label because no PHI is handled
- [ ] No PHI in logs: no PHI in the decision log, pre-read or meeting notes
- [ ] Docs / README updated: README links the decision log

## 13. Hand-off
After this task, downstream tasks can rely on a signed-off answer, or a named owner and date, for every question they need:

| Task | Can rely on |
|---|---|
| P0-02 Appointment-type mapping | Q3: which kinds of appointments the AI may book; B5: hours and reserved blocks |
| P0-03 Emergency protocol | Q4a: headline protocol and its clinical owner; B6: callback response-time promise |
| P0-04 Conversation flows | Q1, Q2, Q5, Q6, B4, B6 |
| P0-07a / P0-07 Messaging channel and provider | Q8: the clinic's channel preference (SMS / WhatsApp) |
| P0-08 Admin email route | Q4b: addresses; Q7: Workspace yes/no; B7: full details vs link-only |
| P0-09 Clinic ↔ company BAA | The BAA signatory's name and role |
| P0-12 Open Dental keys | B1: version, hosting, eConnector; B2: who enables API access |
| P1-16 Patient adapter | B1 (phone-search mode), B3 (statuses), B8 (phone field), Q10 (locations) |
| P1-19 Clinic config | Q5, B5: the first real values for configuration |
| P2-14 / P2-15 Verification and registration | Q1: identifiers; Q2 and B4: new-patient handling |
| P5-15 Clinic sign-off | The SME who signs off the final emergency scripts and policies |

## 14. Open questions
| Question | Owner | Needed by |
|---|---|---|
| Which clinic is the pilot clinic, and is it confirmed? | Project sponsor | Before step 1 |
| Who on our team runs the workshop (tech lead alone, or tech lead + compliance advisor)? Proposed: both. | Tech lead | Before scheduling |
| Remote or on site? Proposed: remote video call, with the Open Dental admin at a clinic computer so they can look up B1, B5 and B8. | Tech lead, with SME | Before scheduling |
| Does the product repo (P1-01) exist yet, or do we start in a shared doc? | Tech lead | Before step 7 |

## 15. References
- Plan §1 (principles), §2 (functional scope), §4.5 (identification), §4.6 (scheduling), §4.8 (emergencies), §4.9 (callback + admin email), §5 (data model and retention), §8 Phase 0, §10 (roles), §13 (open questions)
- Open Dental API overview: https://www.opendental.com/site/apispecification.html
- Open Dental API setup: https://www.opendental.com/site/apisetup.html
- Related tasks: P0-02, P0-03, P0-04, P0-07, P0-08, P0-09, P0-12, P1-01, P1-16, P1-19, P2-14, P2-15, P5-15
