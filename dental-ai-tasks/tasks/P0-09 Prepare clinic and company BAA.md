---
id: P0-09
title: Prepare clinic <-> company BAA
milestone: P0
epic: E0.2
size: S
labels: area:compliance, type:docs
depends_on: P0-01
status: approved
---

# P0-09: Prepare clinic <-> company BAA

## 1. Summary
Prepare the Business Associate Agreement (BAA) between our company (business associate) and the pilot clinic (covered entity). The team produces four things; **legal counsel writes the final legal text**:
1. a **requirements checklist** of what any BAA we sign must contain;
2. **Annex A:** exactly which PHI we handle, for what purposes, and where it goes;
3. **Annex B:** our subcontractors and their BAAs;
4. a **commitments table** that links every promise in the BAA to the task that implements it.

We offer a reusable, versioned template based on HHS's sample provisions, and we accept the clinic's own template if it passes the checklist. Done means: counsel and the compliance advisor have reviewed it, both parties have signed, the signed copy and record are saved, and the tasks affected by the commitments are notified.

## 2. Why this matters
Under HIPAA, the clinic may only let us create, receive, keep or transmit its patients' PHI if a BAA is in place. Until it is signed:
- no real patient data may reach our system;
- we may not connect to the clinic's real Open Dental database;
- the pilot can't start.

This is the last item of the PHI gate in DECISIONS #25, together with the Google Cloud BAA (P0-05), the guardrails (P0-06), the messaging and email BAAs (P0-07, P0-08) and the vendor matrix (P0-10).

A BAA is also a set of **operational promises**: breach-notice deadlines, deleting data at the end of the contract, subcontractor control. Signing a promise the system can't keep (e.g. "notify within 24 hours" with no incident process) is itself a compliance risk. The commitments table makes every promise someone's task.

Plan references: §3.3 (BAA strategy, compliance gate), §5 (data model, retention), §6 (security & HIPAA plan), §10 (compliance advisor), §12.

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P0, Discovery & Compliance Foundation**.
- **Covered entity / business associate:** the clinic is a covered entity under HIPAA. We are its business associate, because our system handles its PHI on its behalf. Our vendors that handle that PHI (Google, the messaging provider) are **subcontractors**, and each must have a BAA with us.
- **What a BAA must contain:** HIPAA lists required contract terms in 45 CFR 164.504(e) (Privacy Rule) and 164.314(a) (Security Rule). Breach notification by a business associate is in 164.410. HHS publishes sample provisions: https://www.hhs.gov/hipaa/for-professionals/covered-entities/sample-business-associate-agreement-provisions/index.html. **Verify with counsel:** the current wording and citations; this spec is not legal advice.
- **Breach notification (164.410):** a business associate must notify the covered entity of a breach of unsecured PHI without unreasonable delay and no later than 60 calendar days after discovery. BAAs often set a shorter deadline. **Verify with counsel.**
- **Signed so far (approved specs):** Google Cloud BAA (P0-05), Google Workspace BAA (P0-08), messaging provider BAA (P0-07, after the P0-07a decision).
- **Who signs for the clinic:** the BAA signatory named in the P0-01 decision log.
- **What PHI we handle:** the PHI slots in the P0-04 state machine (`docs/flows/overview.md`): name, DOB, phone, email, address, ZIP, WhatsApp number, visit-reason text, situation description, plus PatNum/AptNum and the consent and callback records (plan §5).

## 4. Scope
**In scope**
- The requirements checklist (required HIPAA terms + our proposed additional terms).
- Annex A (data, purposes, systems, retention) and Annex B (subcontractors).
- The commitments table with owner tasks.
- A draft template v1 based on the HHS sample provisions, for counsel to finalize.
- Reviewing the clinic's own template against the checklist, if they send one.
- Review by counsel and the compliance advisor, sending to the clinic, tracking negotiation, signature, and record.
- Recording the gate: the clinic's production Open Dental key and any real PHI only after signature.

**Out of scope** (and which task covers it)
- The main service / pilot agreement (commercial terms, liability, fees) → not in the task list; owner is the sponsor + counsel (§14)
- Vendor matrix document → P0-10 (imports this record)
- Incident response process behind the breach-notice promise → P5-12
- Deletion and retention jobs behind the return/destroy promise → P5-13
- Risk assessment → P0-11; final HIPAA readiness review → P5-14
- Open Dental API keys and test DB → P0-12 (production key gated by this task)

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P0-01 Discovery workshop (approved spec) | The clinic's BAA signatory; Q9 transcript retention; Q8 messaging channel | Write the checklist, annexes and commitments now with the P0-01 Proposed defaults, marked `(P0-01 Qn)`, and update them after the workshop. |
| P0-04, P0-05, P0-07, P0-07a, P0-08 (approved specs, soft) | PHI slots; subcontractors and their BAA records | Use the specs' contents. Annex B lists each subcontractor's BAA as "pending" until its record exists. |
| Counsel / compliance advisor (external) | Legal drafting and review | Book them as soon as the checklist and annexes are drafted (§7 step 1). |

## 6. Interface contract

### Files
| Path | Content |
|---|---|
| `docs/compliance/baa/requirements-checklist.md` | Required and proposed terms (below), each with pass/fail when reviewing a draft |
| `docs/compliance/baa/annex-a-data-and-purposes.md` | Annex A |
| `docs/compliance/baa/annex-b-subcontractors.md` | Annex B |
| `docs/compliance/baa/commitments.md` | Commitments → owner tasks |
| `docs/compliance/baa/clinic-baa-template-v1.md` | Draft template (counsel finalizes; version in the file name) |
| `docs/compliance/agreements/clinic-<clinic_slug>-baa-YYYY-MM-DD.pdf` | Signed copy |
| `docs/compliance/baa-clinic-<clinic_slug>.md` | Record, P0-05 format plus template version, counterparty signatory, annex versions |

### Requirements checklist
**Required terms** (from 45 CFR 164.504(e), 164.314(a), 164.410; **Verify with counsel**):
| # | Term |
|---|---|
| R1 | Permitted and required uses and disclosures of PHI (= the services in Annex A); no use or disclosure that would violate the Privacy Rule if done by the clinic |
| R2 | No use or disclosure other than permitted by the agreement or required by law |
| R3 | Appropriate safeguards; comply with the Security Rule for electronic PHI |
| R4 | Report any use or disclosure not provided for, including breaches of unsecured PHI (164.410) and security incidents |
| R5 | Subcontractors that handle the PHI agree in writing to the same restrictions and conditions |
| R6 | Make PHI available for the patient's access requests, as the clinic needs (164.524) |
| R7 | Make PHI available for amendment (164.526) and provide information for an accounting of disclosures (164.528) |
| R8 | Where we carry out a clinic obligation under the Privacy Rule, comply with the requirements that apply to it |
| R9 | Make internal practices, books and records available to HHS |
| R10 | At termination, return or destroy all PHI; if not feasible, extend protections and limit further use |
| R11 | The clinic may terminate if we violate a material term |

**Our proposed terms** (Proposed; the sponsor and counsel decide):
| # | Term | Proposed value |
|---|---|---|
| P1 | Breach-notice deadline to the clinic | Within **5 business days** of discovery, with the details known then; updates as the investigation continues |
| P2 | Security incidents that didn't succeed (pings, blocked scans) | Reported in aggregate on request, not one by one |
| P3 | No use of PHI to train or improve AI models, and no sale of PHI | Explicitly prohibited |
| P4 | Data location | Stored and processed in the US only (enforced by P0-06) |
| P5 | Minimum necessary | Only the PHI listed in Annex A |
| P6 | Access from outside the US | Disclosed in Annex B; **open question** (§14) |
| P7 | Subcontractor changes | The clinic is notified at least 30 days before a new subcontractor handles PHI |
| P8 | Return/destroy at termination | Within 30 days; written certificate of destruction; backups expire on their normal schedule |
| P9 | De-identified data | Not used for any purpose without the clinic's written consent |

### Annex A: data and purposes (structure; filled from P0-04, P0-07a, P0-08)
| Data category | Examples | Purpose | Where stored | Sent to (subcontractor) | Retention |
|---|---|---|---|---|---|
| Identifiers | name, DOB, phone, email, address, ZIP | Identify/register patients, callbacks | Cloud SQL (encrypted fields), Redis session (TTL) | Google Cloud (Gemini, STT, TTS processing) | Session TTL; callback cases per P5-13 |
| Open Dental references | PatNum, AptNum | Link to the clinic's records | Cloud SQL | Google Cloud | Life of the contract |
| Visit reason / situation | reason text, callback situation | Book the right type, callbacks, emergencies | Cloud SQL (encrypted) | Google Cloud | Per P5-13 |
| Contact & consent | messaging number, consent records | Confirmations, reminders | Cloud SQL (encrypted) | Messaging provider (per `messaging_policy.yaml`) | Per P5-13 |
| Callback emails | link only by default; full details only if approved | Notify clinic admin | Google Workspace (Sent folder if full details) | Google Workspace | Per P0-08 |
| Audio | voice audio | Speech recognition | **Not stored** (streamed) | Google Cloud STT | None |
| Transcripts | conversation text | Quality review | Only if P0-01 Q9 allows | Google Cloud | Per Q9 (max 30 days proposed) |
| Audit log | actions with object references, no free-text PHI | Security, compliance | Cloud SQL | Google Cloud | Proposed 6 years (Verify with counsel) |

### Annex B: subcontractors
| Subcontractor | Services | PHI? | BAA | Record |
|---|---|---|---|---|
| Google Cloud | Hosting, DB, Gemini, STT, TTS, logging | Yes | Google Cloud HIPAA BAA | `docs/compliance/baa-google-cloud.md` (P0-05) |
| Google Workspace | Admin callback emails | Yes (full-details mode only) | Workspace HIPAA BAA | `docs/compliance/baa-google-workspace.md` (P0-08) |
| Messaging provider (from P0-07) | Confirmations, reminders | Yes (minimal, per P0-07a) | Provider BAA | `docs/compliance/baa-<vendor>.md` (P0-07) |

**Verify with counsel:** whether Open Dental's API relay (requests pass through Open Dental's servers to the clinic's database) is covered by the clinic's own arrangement with Open Dental, or must appear in Annex B.

### Commitments table (`commitments.md`)
| Commitment (BAA term) | Proposed value | Implemented by | Checked in |
|---|---|---|---|
| Breach notice (R4, P1) | 5 business days | P5-12 incident response plan and breach runbook | P5-12 tabletop, P5-14 |
| Safeguards (R3) | Encryption, access control, PHI-free logs, audit | P0-06, P1-03, P1-10, P1-11, P1-12, P1-13 | P5-10, P5-14 |
| Subcontractor BAAs (R5) | Before any PHI | P0-05, P0-07, P0-08, P0-10 | P5-14 |
| Patient access/amendment requests (R6, R7) | Forward to the clinic within 5 business days; help retrieve data | P5-12 runbook | P5-14 |
| Return/destroy (R10, P8) | 30 days + certificate | P5-13 deletion jobs + runbook | P5-13 drill |
| No model training (P3) | Prohibited | P0-13 (Vertex AI data-use settings; Verify), P2-03 | P5-14 |
| US-only (P4) | US locations | P0-06 | P0-06 tests |
| Transcript retention | Per P0-01 Q9 | P5-13 | P5-13 |
| Audit log retention | Proposed 6 years | P1-12 | P5-14 |

**Rule:** no term goes into the BAA unless its row exists here with an owner task, and the tech lead has confirmed it's feasible.

## 7. Implementation guide
1. **Engage counsel.** Confirm who our counsel / HIPAA advisor is (§14). The team does not write final legal language.
2. **Write the checklist** (§6), with citations. Ask counsel to confirm the required terms.
3. **Fill in Annex A** from the P0-04 PHI slot list, the P0-07a messaging policy, the P0-08 email mode and P0-01 Q9. Fill in **Annex B** from the BAA records.
4. **Write the commitments table.** The tech lead confirms each promise is achievable with the planned tasks. If not, change the proposed value, not the task list.
5. **Draft template v1** from the HHS sample provisions plus our proposed terms and annexes. Counsel finalizes it and the compliance advisor reviews it.
6. **Send to the clinic's signatory** (P0-01), with copies to the SME and our advisor. If the clinic sends its own BAA, review it against the checklist and commitments, and send the gaps to counsel.
7. **Negotiate.** Every change the clinic asks for goes through the commitments table first (is it feasible? which task?). Log agreed changes in DECISIONS.md and notify the owner tasks.
8. **Sign.** Both parties sign, by people with authority. Save the PDF and write `baa-clinic-<clinic_slug>.md`.
9. **Open the gate.** Notify:
   - P0-10, to update the matrix;
   - P0-12: the clinic's **production** Open Dental key may now be requested;
   - P5-12, P5-13 and P1-12 with their commitments;
   - the sponsor, that the PHI gate's clinic item is closed.
10. **Keep it current.** When a subcontractor is added or changed, update Annex B and notify the clinic per P7 before any PHI flows.

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| The clinic insists on its own BAA template | Accept it if it passes the checklist and every promise fits the commitments table; counsel reviews the gaps. |
| The clinic wants a 24-hour breach-notice deadline | Only if P5-12 can deliver it (e.g. an on-call process); otherwise counter-propose. Never sign a deadline we can't meet. |
| The clinic forbids any subcontractor processing | Not possible for this product (Gemini, STT, TTS run on Google Cloud). Explain, show Annex B and the BAAs; escalate to the sponsor. |
| The clinic requires US-only staff access to PHI | See the P6 open question. If agreed, production access controls must enforce it (P1-13 / P1-05); record it as a commitment. |
| A subcontractor BAA isn't signed yet (e.g. messaging) | Sign the clinic BAA with that row marked pending, but no PHI flows to that subcontractor until its BAA exists (the gate). |
| The clinic wants to sign before counsel has reviewed it | Don't. Counsel review is mandatory. |
| The clinic never signs | The pilot can't use real data. Development continues on synthetic data; escalate to the sponsor. |
| The plan changes and Annex A is no longer accurate (e.g. transcripts are now kept) | Update Annex A, check with counsel whether an amendment is needed, and notify the clinic before the change goes live. |
| Someone shares real patient data "just to test" before signature | Refuse and delete it; tell the compliance advisor (possible incident). |

## 9. Security, HIPAA and PHI
- **No PHI is handled.** The annexes describe data **categories**, never real data.
- **This task defines the gate:** before signature, no real PHI and no access to the clinic's production Open Dental database, only synthetic data and the test DB (P0-12).
- The signed agreement and the negotiation emails are confidential company documents (private repo / drive), not PHI.
- **Audit:** not applicable. The signed record is the evidence for P0-10, P0-11 and P5-14.

## 10. Testing
No application code. Checks:
- Reviewer (compliance advisor): every required term R1–R11 is present in the final text (checklist marked pass), and every term in the signed text has a row in `commitments.md`.
- Annex A matches the P0-04 PHI slot list and `messaging_policy.yaml`: no data category is missing, none is invented.
- Annex B matches the BAA records that exist; nothing is listed as signed without a record.
- The tech lead signs off that every commitment is feasible.

## 11. Acceptance criteria
- [ ] Checklist, Annex A, Annex B and the commitments table are committed and reviewed by the compliance advisor
- [ ] Draft template v1 is finalized by counsel (or the clinic's template is reviewed against the checklist with gaps resolved)
- [ ] Every BAA promise has a commitments row with an owner task, confirmed feasible by the tech lead
- [ ] The BAA is sent to the clinic's signatory (P0-01), with the SME and advisor copied
- [ ] The BAA is signed by both parties; PDF saved; `baa-clinic-<clinic_slug>.md` written
- [ ] The P0-10, P0-12, P1-12, P5-12, P5-13 and P5-14 issues are notified; the sponsor confirms the clinic item of the PHI gate is closed

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI: not applicable (no code); the §10 reviews are recorded
- [ ] PR reviewed (HIPAA review if labelled `phi`): reviewed by the compliance advisor and counsel; no `phi` label because no PHI is handled
- [ ] No PHI in logs: none exists
- [ ] Docs / README updated: `docs/compliance/baa/` linked from `docs/compliance/`

## 13. Hand-off
| Task | Can rely on |
|---|---|
| P0-10 Vendor matrix | The clinic BAA record and Annex B |
| P0-11 Risk assessment | Annex A (data flows) and the commitments |
| P0-12 Open Dental keys | Permission to request the clinic's production key only after signature |
| P1-12 Audit log | The audit-log retention commitment |
| P5-12 Incident response | Breach-notice deadline, content, and the access/amendment request process |
| P5-13 Retention jobs | Return/destroy deadline, certificate, transcript retention |
| P5-14 HIPAA readiness | The signed BAA, checklist and commitments as evidence |

## 14. Open questions
| Question | Owner | Needed by |
|---|---|---|
| Who is our counsel / HIPAA advisor, and are they engaged? | Project sponsor | Step 1 |
| Who owns the main service / pilot agreement that the BAA attaches to? | Project sponsor + counsel | Step 6 |
| Will anyone access production PHI from outside the US (e.g. support or engineering)? If yes, it must be disclosed and agreed (P6). | Project sponsor + tech lead | Step 5 |
| Is Open Dental's API relay covered by the clinic's own arrangement, or must it be in Annex B? | Counsel | Step 3 |
| Breach-notice deadline: are 5 business days achievable with P5-12's planned process? | Tech lead | Step 4 |

## 15. References
- Plan §3.3 (BAA strategy, compliance gate), §5 (data model, retention), §6 (security & HIPAA plan), §10, §12
- HHS sample BAA provisions: https://www.hhs.gov/hipaa/for-professionals/covered-entities/sample-business-associate-agreement-provisions/index.html
- HHS business associates guidance: https://www.hhs.gov/hipaa/for-professionals/privacy/guidance/business-associates/index.html
- 45 CFR 164.504(e), 164.314(a), 164.410 (eCFR): https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164
- Related tasks: P0-01, P0-04, P0-05, P0-06, P0-07, P0-07a, P0-08, P0-10, P0-11, P0-12, P0-13, P1-12, P1-13, P5-12, P5-13, P5-14
