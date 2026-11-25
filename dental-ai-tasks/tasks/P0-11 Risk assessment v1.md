---
id: P0-11
title: Risk assessment v1
milestone: P0
epic: E0.2
size: M
labels: area:compliance, type:docs
depends_on: P0-10
status: approved
---

# P0-11: Risk assessment v1

## 1. Summary
Write version 1 of our HIPAA security risk assessment. It answers:
- where electronic PHI (ePHI) lives and flows in our system;
- what can go wrong (threats and vulnerabilities);
- how likely each problem is, and how bad it would be;
- which planned control reduces it, and which task owns that control.

It also covers AI and patient-safety risks that are not classic HIPAA risks, such as emergency under-triage and prompt injection.

The deliverables:
- `docs/compliance/risk/risk-assessment-v1.md`: scope, method, asset inventory and data flows;
- `docs/compliance/risk/risk-register.md`: about 33 scored risks, each with an owner task;
- a **gaps list**: risks that no task covers yet, each with a decision.

Done means: the compliance advisor has reviewed it, every High or Critical risk has a planned control with an owner task, every gap has a decision, and P5-12 and P5-14 have been notified.

## 2. Why this matters
The HIPAA Security Rule requires a business associate to perform an "accurate and thorough assessment" of risks to the ePHI it holds (45 CFR 164.308(a)(1)(ii)(A), risk analysis), and to reduce them to a reasonable level (164.308(a)(1)(ii)(B), risk management). **Verify with the compliance advisor:** the exact wording and current citations.

Without it:
- we can't show regulators or the clinic that our controls were chosen for a reason;
- risks that no task owns stay unowned until an incident;
- P5-12 (incident response) has no list of scenarios to plan for;
- P5-14 has nothing to finalize.

Doing it now, before any code, is cheap. A missing control found here becomes a task. Found after go-live, it becomes an incident.

Plan references: §6 (security & HIPAA plan, "Operations: risk assessment"), §3.3 (vendors), §8 Phase 0 deliverables ("risk assessment v1"), §15 (definition of done).

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P0, Discovery & Compliance Foundation**.
- **Method we follow:** HHS's Guidance on Risk Analysis lists the elements of a risk analysis:
  - scope;
  - data collection (where ePHI is);
  - threats and vulnerabilities;
  - current security measures;
  - likelihood;
  - impact;
  - risk level;
  - documentation;
  - periodic review and update.

  NIST SP 800-30 Rev. 1 describes the same process in more detail. HHS also offers an SRA Tool, but it is built for small healthcare providers' own offices, not for a SaaS business associate, so we don't use it (Proposed).

  Links are in §15. **Verify:** the list of elements against the current HHS page.
- **Possible rule change:** HHS published a proposed update to the Security Rule (NPRM, January 2025) that would, among other things, require a written technology asset inventory and network map. **Verify with the advisor:** whether it has been finalized and what applies to us. Our asset inventory (§6) is written so it can serve that purpose either way.
- **Inputs that already exist (approved specs):**
  - P0-09 Annex A: PHI categories, purposes, storage, retention;
  - P0-10 `vendors.yaml`: every vendor and whether PHI reaches it;
  - P0-06 `hipaa-controls.md`: guardrails and evidence;
  - P0-05: IAM model and break-glass;
  - P0-03: emergency tiers;
  - P0-04: state machine guards;
  - P0-07a / P0-08: messaging and email content rules.
- **Not yet available:** the final architecture and PHI data-flow diagram (P0-14). v1 uses a simple flow table (§6) and is updated when P0-14 lands.

## 4. Scope
**In scope**
- **The system:** all four Google Cloud projects. Real PHI is only in `<prefix>-prod`, but dev and staging are assessed for the risk of real data reaching them.
- The public widget, the admin console, the backend, the data stores, and the vendors from P0-10.
- **Team operations:** cloud access, GitHub, staff and engineer accounts, laptops, joiners and leavers.
- AI and patient-safety risks (category S).
- The legal review of the vendor BAA terms. P0-05 assigned it here, and it is recorded as risk R29.
- Gaps: risks with no owner task, each with a decision.

**Out of scope** (and which task covers it)
- Security of the clinic's own Open Dental server and network → the clinic's own risk analysis (stated in the clinic BAA, P0-09)
- The final architecture diagram → P0-14 (v1 is updated from it)
- Writing the incident response plan → P5-12 (uses the R-list as scenarios)
- The final risk assessment and advisor sign-off before go-live → P5-14
- Penetration testing → P5-11; OWASP review → P5-10

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P0-10 Vendor matrix (approved spec) | Vendor list, PHI flags, environments | Use the initial rows in the P0-10 spec §6. Re-check them against `vendors.yaml` before the review. |
| P0-09, P0-06, P0-05, P0-03, P0-04 (approved specs, soft) | Annex A, guardrails, IAM, safety design | Use the specs' contents. Controls that don't exist yet are listed as **planned** with their task ID. |
| P0-14 Architecture (later) | Final data-flow diagram | Use the flow table in §6. Add "Update from P0-14" to the review triggers. |
| Compliance advisor (external) | Review | Book the review when the register draft is done (step 7). |

## 6. Interface contract

### Files
| Path | Content |
|---|---|
| `docs/compliance/risk/risk-assessment-v1.md` | Sections: 1 Scope, 2 Method and scales, 3 Asset inventory, 4 Data flows, 5 Summary of results (heat map counts, top risks), 6 Gaps and decisions, 7 Review triggers, 8 Sign-off |
| `docs/compliance/risk/risk-register.md` | The register (format below), one row per risk |
| `docs/compliance/risk/safeguard-coverage.md` | Security Rule safeguards → risks and controls (below) |
| `docs/compliance/risk/accepted-risks.md` | Sponsor-signed acceptances (if any) |

### Scales (Proposed)
**Likelihood (L), over the next 12 months, with the planned controls not yet in place:**
| L | Meaning |
|---|---|
| 1 Rare | Not expected; would need several unlikely failures |
| 2 Unlikely | Could happen; no known cases in similar systems |
| 3 Possible | Known to happen in similar systems |
| 4 Likely | Expected at least once without the control |
| 5 Almost certain | Will happen, or is happening |

**Impact (I):**
| I | Meaning |
|---|---|
| 1 Minimal | No PHI exposed; no patient effect; short inconvenience |
| 2 Minor | Limited non-sensitive data of one patient; easy to correct |
| 3 Moderate | PHI of a few patients exposed or wrong, or the service is down for hours; callback recovers it |
| 4 Major | PHI of many patients, or a reportable breach; wrong clinical scheduling with possible harm |
| 5 Severe | Large breach (500+ patients, HHS and media notice); or a patient harmed (e.g. a missed emergency) |

**Score = L × I.** Bands:
- **Low** 1–4: accept and monitor;
- **Medium** 5–9: control planned within the MVP;
- **High** 10–16: control required before real PHI (the PHI gate);
- **Critical** 20–25: control required before any further work on the affected part.

The **residual** score is re-scored assuming the planned controls are in place. The target is Medium or lower for every risk, unless a sponsor acceptance exists.

### Asset inventory (section 3; Proposed initial list)
| Asset | Type | ePHI? | Environment | Owner task |
|---|---|---|---|---|
| Patient widget (Next.js) | Web app (browser) | In transit / in memory | all | P2-25 |
| Admin console | Web app | Displays PHI | all | P4-09 |
| Backend API + orchestrator | Cloud Run service | Processes | all | P1-08, P2-01 |
| Cloud SQL Postgres | Database (CMEK) | Stores (encrypted fields) | all (real only in prod) | P1-03, P1-09 |
| Memorystore Redis | Session / slot memory | Stores (TTL, encrypted) | all | P1-04, P2-02 |
| Cloud Tasks / Scheduler | Queues (reminders, emails) | Task payloads: IDs only (Proposed) | all | P1-04, P4-04 |
| Cloud Logging / Monitoring | Logs | Must not contain PHI | all | P1-07, P1-11 |
| Secret Manager + KMS | Secrets and keys | Keys that protect PHI | all | P1-05 |
| Vertex AI (Gemini) | LLM | Processes (prompts) | all | P2-03, P0-13 |
| Speech-to-Text / Text-to-Speech | Speech | Processes audio/text | all | P3-03, P3-05 |
| Gmail (`callbacks@`) | Email | Only in `full_details` mode | prod | P2-23, P0-08 |
| Messaging provider | SMS/WhatsApp | Minimal message content | staging, prod | P4-01, P0-07 |
| Open Dental API + eConnector | Clinic's system of record | Source of all PHI | test DB in dev/staging | P1-15 |
| GitHub | Code, CI | Must not contain PHI | team | P1-01, P1-06 |
| Staff and engineer accounts and laptops | People and devices | Access to the console and cloud | team | P0-05, P1-13 |
| Terraform state bucket (`<prefix>-ops-tfstate`) | Infra state | No PHI; contains resource config | ops | P0-06 |

### Data flows (section 4; v1, replaced by the P0-14 diagram later)
| # | From → To | PHI elements (Annex A) | Protection |
|---|---|---|---|
| F1 | Patient browser → backend | Voice audio, chat text, identifiers | TLS 1.2+; session token (P1-14) |
| F2 | Backend → Vertex AI | Compact context with PHI masked where possible (P2-04) | Private access within the VPC-SC perimeter; BAA |
| F3 | Backend → STT / TTS | Audio / reply text | Same as F2; STT data logging off (P0-06) |
| F4 | Backend ↔ Open Dental API | Search identifiers, patient and appointment data | TLS; API keys in Secret Manager (P1-15) |
| F5 | Backend → Cloud SQL / Redis | IDs, encrypted fields, callback cases, consent | CMEK + field encryption (P1-10) |
| F6 | Backend → Gmail → clinic admin | Link only (default) or full details | TLS compliance rule (P0-08) |
| F7 | Backend → messaging provider → patient | Name, clinic, date, time (per P0-07a) | Provider BAA; consent (P4-02) |
| F8 | Backend → Cloud Logging | **None allowed** | Redaction (P1-11); scans (P5-08) |
| F9 | Staff browser ↔ admin console | Callback cases, activity log | MFA, RBAC (P1-13) |

### Register format (`risk-register.md`)
| Column | Content |
|---|---|
| ID | `R01`… (never reused; a retired risk keeps its ID with the status `closed`) |
| Cat | C confidentiality · I integrity · A availability · S AI/patient safety · V vendor/legal · O operations/people |
| Risk | "Threat → vulnerability → consequence" in one sentence |
| Assets / flows | From the inventory and the flow table |
| L, I, Score, Band | Inherent, before the planned controls |
| Controls | Existing (`done`) or planned, each with its task ID |
| Residual L, I, Score | After the controls |
| Owner | The role accountable for the control (tech lead, compliance owner, sponsor) |
| Decision | `mitigate` / `accept` (link to `accepted-risks.md`) / `transfer` (e.g. BAA) / `avoid` |
| Status | `open` / `controls planned` / `controls in place` / `closed` |

### Initial register (Proposed scores; the team and advisor adjust them)
| ID | Cat | Risk | L | I | Score | Planned controls (tasks) | Residual |
|---|---|---|---|---|---|---|---|
| R01 | C | Exceptions, debug output or request dumps write PHI to Cloud Logging | 4 | 4 | 16 High | PHI-redacting logger (P1-11), debug off in prod (P1-08), log scan (P5-08) | 2×4=8 |
| R02 | C | A caller impersonates a patient and learns their appointments or details | 3 | 5 | 15 High | ≥2 identifiers, never phone alone, no record leaks before verification (P2-14), session scoping (P2-09) | 2×4=8 |
| R03 | C | Prompt injection makes the LLM reveal other patients' data or misuse tools | 3 | 5 | 15 High | Tool gateway allow-list + preconditions + session scoping (P2-08, P2-09), injection defences (P2-11), red teaming (P5-09) | 1×5=5 |
| R04 | C | Broken access control (IDOR) in the console or API exposes other cases | 3 | 5 | 15 High | RBAC (P1-13, P4-09), authz tests and OWASP review (P5-10), pen test (P5-11) | 1×5=5 |
| R05 | C | A staff account is phished and used to read callback cases | 3 | 4 | 12 High | MFA required (P1-13), idle timeout (P1-14), audit log (P1-12) | 2×3=6 |
| R06 | C | A compromised or over-privileged cloud identity reads prod data | 2 | 5 | 10 High | IAM via groups and break-glass (P0-05), no service-account keys (P0-06), least-privilege SAs (P1-05), WIF in CI (P1-06) | 1×5=5 |
| R07 | C | PHI goes to a vendor without a BAA (new SaaS, AI Studio key, preview model) | 3 | 5 | 15 High | Service allow-list, Gemini Developer API denied (P0-06), vendor matrix + PR check (P0-10), GA models only (P0-13) | 1×5=5 |
| R08 | C | A callback email with PHI is intercepted or sent to the wrong address | 3 | 4 | 12 High | `link_only` default, TLS rule, recipient readiness check (P0-08), sender (P2-23) | 1×4=4 |
| R09 | C | A confirmation/reminder reveals PHI on a shared phone or to a wrong number | 3 | 3 | 9 Medium | Minimal content (P0-07a), consent (P4-02), opt-out (P4-07), number read-back (P3-09) | 2×2=4 |
| R10 | C | Database, cache or backup data is exfiltrated | 2 | 5 | 10 High | VPC-SC (P0-06), CMEK (P1-03), field encryption (P1-10), Redis TTL + encryption (P2-02) | 1×5=5 |
| R11 | C | Real patient data is used in dev, staging, GitHub or tests | 3 | 4 | 12 High | PHI gate (DECISIONS #25), synthetic test DB (P0-12), PR check (P0-10), scans (P5-08) | 1×4=4 |
| R12 | C | Open Dental API keys leak, giving access to the whole clinic database | 2 | 5 | 10 High | Secret Manager (P1-05), client never exposes keys to the LLM (P1-15), credential scan (P5-08); least-privilege key **Verify** with Open Dental (P0-12) | 1×5=5 |
| R13 | C | A vendor keeps or uses PHI for training (e.g. STT data logging, model training) | 2 | 4 | 8 Medium | STT logging off check (P0-06), Vertex AI data-use settings **Verify** (P0-13), BAA term P3 (P0-09) | 1×4=4 |
| R14 | C | Transcripts or callback data kept longer than needed | 3 | 3 | 9 Medium | Retention decision P0-01 Q9, deletion jobs (P5-13) | 1×3=3 |
| R15 | C | PHI leaks through URLs, browser storage or third-party scripts on the widget | 3 | 4 | 12 High | No PHI in URLs (plan §6), widget shell rules (P2-25), session tokens (P1-14), review (P5-10) | 1×4=4 |
| R16 | I | Booking for the wrong patient, or a duplicate patient is created | 3 | 4 | 12 High | Matching and scoring (P2-13), verification (P2-14), registration duplicate check (P2-15), scenarios (P5-02) | 1×4=4 |
| R17 | I | Double booking or booking a slot that is no longer free | 3 | 3 | 9 Medium | Slot lock + booking sequence (P1-21), `fresh_availability` guard (P2-09), idempotency (P2-10), race tests (P5-04) | 1×3=3 |
| R18 | I | The LLM tells the patient "you're booked" when nothing was booked | 3 | 4 | 12 High | Deterministic code acts, the LLM only phrases results (P0-04, P2-07); confirmations from tool results only (P2-09); evals (P5-01) | 1×4=4 |
| R19 | I | A reminder is sent for a cancelled or moved appointment, or at the wrong time | 3 | 3 | 9 Medium | Pre-send re-fetch (P4-05), DST-aware scheduler (P4-04), tests (P5-05) | 1×3=3 |
| R20 | I | Audit log entries are missing or altered | 2 | 4 | 8 Medium | Append-only audit service (P1-12), restricted DB roles (P1-03) | 1×4=4 |
| R21 | A | Open Dental API or the clinic's eConnector is down, so nothing can be booked | 4 | 3 | 12 High | Callback fallback (P2-22, P2-24), retries (P1-15), outage runbook (P5-12) | 4×2=8 |
| R22 | A | Vertex AI, STT or TTS outage or quota exhaustion | 3 | 3 | 9 Medium | Model router fallback (P2-06), text-only mode (P2-28), load tests (P5-06), runbook (P5-12) | 2×2=4 |
| R23 | A | Callback emails are not delivered, so cases are lost | 3 | 4 | 12 High | Retry + unsent alerts (P2-23), console case list (P4-14) | 1×3=3 |
| R24 | A | Database data loss | 2 | 4 | 8 Medium | Backups and PITR (P1-03), restore drill (P5-13) | 1×3=3 |
| R25 | A | Bots or abuse flood the public widget (cost, availability, fake bookings) | 4 | 3 | 12 High | Bot protection (P2-29), rate limiting (P1-14), load tests (P5-06) | 2×3=6 |
| R26 | S | A Tier 1 emergency is not recognized (under-triage) | 2 | 5 | 10 High | Rules-first detector (P0-03, P2-20), scripts (P2-21), test set 100% Tier 1 (P5-02), clinic sign-off (P5-15) | 1×5=5 |
| R27 | S | The AI gives medical advice or a diagnosis | 3 | 4 | 12 High | System prompt rules (P2-07), never-diagnose policy (P0-03), red teaming (P5-09) | 1×4=4 |
| R28 | S | A caller in crisis (self-harm) is not given the 988 script | 2 | 5 | 10 High | Crisis tier (P0-03, P2-20, P2-21), tests (P5-02) | 1×5=5 |
| R29 | V | Vendor BAA terms are signed without legal review and have gaps | 3 | 4 | 12 High | Counsel/advisor review of the Google Cloud, Workspace and messaging BAAs, recorded in each BAA record (this task, step 5), final check (P5-14) | 1×4=4 |
| R30 | V | We can't keep a promise in the clinic BAA (e.g. the breach-notice deadline) | 2 | 4 | 8 Medium | Commitments table (P0-09), incident process (P5-12) | 1×4=4 |
| R31 | O | A breach is detected late or not reported on time | 3 | 5 | 15 High | Incident response plan and breach runbook (P5-12), audit log + alerts (P1-07, P1-12) | 2×4=8 |
| R32 | O | A departed team member or clinic staffer keeps access | 3 | 4 | 12 High | Group-based IAM (P0-05), console user deactivation (P1-13); **periodic access review: no task (gap G2)** | 2×4=8 (with G2) |
| R33 | O | A lost or stolen laptop exposes credentials or data | 3 | 3 | 9 Medium | No PHI on laptops (policy), MFA, short-lived credentials (P0-05, P1-06); **device policy: no task (gap G3)** | 2×3=6 (with G3) |

### Gaps (section 6; each needs a decision before the advisor review)
| Gap | What is missing | Proposed resolution |
|---|---|---|
| G1 | Workforce security policies, HIPAA training and a sanctions policy (Security Rule administrative safeguards, 164.308(a)(1), (a)(5); **Verify**) | A new task in P5 (proposed name "Security policies and workforce training", S), or add it to P5-14. Decided by the sponsor and logged in DECISIONS.md. |
| G2 | Periodic access reviews (cloud, GitHub, console, Open Dental keys) | Same new task, which also defines a quarterly review |
| G3 | Device and endpoint policy for staff and engineers (disk encryption, screen lock, updates) | Same new task |
| G4 | Contingency plan as a whole (data backup, disaster recovery, emergency mode; 164.308(a)(7); **Verify**) | Split between P5-12 (runbooks) and P5-13 (backup/restore). Confirm with the advisor that together they are sufficient. |

### Safeguard coverage (`safeguard-coverage.md`)
A table with one row per Security Rule standard:
- **administrative** (164.308): risk analysis, workforce security, information access management, awareness and training, incident procedures, contingency plan, evaluation, BA contracts;
- **physical** (164.310): mostly inherited from Google under the BAA; for our team, devices only;
- **technical** (164.312): access control, audit controls, integrity, authentication, transmission security.

For each row, list the risks and the controls/tasks that address it. **Verify** the list of standards with the advisor.

## 7. Implementation guide
1. **Collect inputs:** P0-09 Annex A, P0-10 `vendors.yaml`, P0-06 `hipaa-controls.md`, P0-05 IAM, P0-03, P0-04, P0-07a and P0-08 rules.
2. **Write the scope, method and scales** (§6) in `risk-assessment-v1.md`.
3. **Asset inventory and data flows.** Start from §6. Add anything the inputs show that is missing. Every asset with "ePHI: yes" must appear in at least one flow and at least one risk.
4. **Register.** Start from the initial register in §6:
   - hold a 1–2 hour session with the tech lead and one backend engineer to review each row, adjust scores and add risks;
   - every High or Critical risk must name planned controls with task IDs that exist in the task list;
   - check the IDs with `python tools/build_pdf.py --status` or `plan/initial_task_list.md`.
5. **BAA legal review (R29).** Ask the advisor/counsel to review the accepted vendor BAAs (Google Cloud, Workspace, messaging). Record "Legal review of terms: done YYYY-MM-DD by <name>" in each BAA record (`docs/compliance/baa-*.md`), replacing "pending".
6. **Gaps.** For each gap, the sponsor decides between a new task, adding it to an existing task, or accepting the risk. Log the decision in DECISIONS.md. A new task gets a new ID per CLAUDE.md (never a reused one).
7. **Advisor review.** Send the folder to the compliance advisor. Record the comments and the changes made, and fill in the sign-off section (name, date, version).
8. **Notify:**
   - P5-12: the scenarios R01–R33, especially R31, R21–R23 and the breach-related C risks;
   - P5-14: the register to finalize;
   - the owners of the High-risk controls (the issues of P1-11, P2-14, P2-09, P2-11, P1-13, P0-12 and so on), so they know their task closes a High risk;
   - P0-14: the flow table to replace.
9. **Review triggers** (written in section 7 of the assessment):
   - P0-14 lands;
   - a new vendor or Google API is added (P0-10 change);
   - a new PHI field is added (Annex A change);
   - before go-live (P5-14);
   - after any security incident;
   - at least once a year.

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| A High risk has no existing task that can control it | Becomes a gap; the sponsor decides (new task / extend a task / accept). It can't stay "open" without a decision. |
| The team disagrees on a score | Use the higher score in v1, and note the disagreement in the row. The advisor decides at review. |
| A control's task is later descoped or removed | The risk's status goes back to `open`, and the residual score is recalculated. Whoever removes or descopes a task searches the register for its ID and notes the affected risks in the DECISIONS.md entry for the removal. |
| The sponsor wants to accept a High risk | Allowed only with a written entry in `accepted-risks.md`: the risk, the reason, an expiry or review date, and the sponsor's name. Critical risks can't be accepted before real PHI. |
| The advisor isn't available | v1 stays draft. Real PHI can't enter prod without the reviewed assessment (it is evidence for P5-14). Escalate to the sponsor. |
| A real incident happens later | It is a review trigger. Add or re-score the risk and record the incident reference (no PHI). |
| The Security Rule update is finalized with new requirements | Re-check the asset inventory, the network map (P0-14) and the safeguard coverage against it; log any changes in DECISIONS.md. |

## 9. Security, HIPAA and PHI
- **No PHI is handled.** The assessment describes data categories, systems and scenarios, never real patients.
- **Sensitivity:** the register lists our weaknesses. Keep it in the private repo with access limited to the team (CODEOWNERS `compliance-owners`, P0-10), and don't paste it into tickets or chat tools that aren't in the vendor matrix.
- This task is the documented basis for the controls in P1 to P5. It is required evidence for the HIPAA readiness review (P5-14) before go-live.
- **Audit:** git history of the files plus the signed-off version in section 8 of the assessment.

## 10. Testing
No application code. Checks the reviewer performs:
- Every asset with ePHI appears in at least one flow and at least one risk.
- Every vendor in `vendors.yaml` with `phi: yes` or `conditional` appears in at least one risk.
- Every High or Critical risk has planned controls with task IDs that exist, and a residual score of Medium or lower (or an acceptance entry).
- Every gap has a decision logged in DECISIONS.md.
- Every Security Rule standard in `safeguard-coverage.md` has at least one risk or control, or a written "Not applicable because…".
- The BAA records show the legal review done (R29).

## 11. Acceptance criteria
- [ ] `risk-assessment-v1.md`, `risk-register.md` and `safeguard-coverage.md` are committed, with all sections filled
- [ ] The register has at least the 33 initial risks, reviewed with the tech lead; scores use the §6 scales
- [ ] Every High or Critical risk has planned controls with existing task IDs and a residual score of Medium or lower, or a sponsor-signed acceptance
- [ ] Gaps G1–G4 each have a decision logged in DECISIONS.md
- [ ] The legal review of the accepted vendor BAAs is recorded in their BAA records
- [ ] The compliance advisor has reviewed it; the sign-off section is filled in
- [ ] The P5-12, P5-14, P0-14 and High-risk control owners' issues are notified

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI: not applicable (no code); the §10 checks are recorded in the PR
- [ ] PR reviewed (HIPAA review if labelled `phi`): reviewed by the compliance owner and the advisor; no `phi` label (no PHI handled)
- [ ] No PHI in logs: none exists
- [ ] Docs / README updated: `docs/compliance/README.md` links the risk folder

## 13. Hand-off
| Task | Can rely on |
|---|---|
| P5-12 Incident response | The risk scenarios (especially R31, R21–R23, the C risks) to build runbooks and the tabletop exercise |
| P5-14 HIPAA readiness | The register, gaps decisions and safeguard coverage to finalize |
| P0-14 Architecture | The asset inventory and flow table to turn into the PHI data-flow diagram |
| High-risk control owners (P1-11, P1-13, P2-09, P2-11, P2-14, P2-20, P0-12 and others) | Their risk IDs, to reference in their specs and tests |
| P5-09, P5-10, P5-11 | The C and S risks as test targets |

## 14. Open questions
| Question | Owner | Needed by |
|---|---|---|
| Has the 2025 Security Rule update been finalized, and does it change what this assessment must contain? | Compliance advisor | Step 7 |
| How should gaps G1–G3 be covered: a new P5 task or an extension of P5-14? | Project sponsor | Step 6 |
| Who signs risk acceptances (the sponsor alone, or the sponsor + advisor)? | Project sponsor | Step 6 |
| Does Open Dental offer API keys with limited permissions (R12)? | Tech lead, via P0-12 | Step 4 |

## 15. References
- Plan §6, §3.3, §8 Phase 0, §15
- HHS Guidance on Risk Analysis: https://www.hhs.gov/hipaa/for-professionals/security/guidance/guidance-risk-analysis/index.html
- HHS Security Risk Assessment Tool: https://www.healthit.gov/topic/privacy-security-and-hipaa/security-risk-assessment-tool
- NIST SP 800-30 Rev. 1, Guide for Conducting Risk Assessments: https://csrc.nist.gov/pubs/sp/800/30/r1/final
- 45 CFR Part 164 Subpart C (Security Rule), eCFR: https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164/subpart-C
- Related tasks: P0-03, P0-04, P0-05, P0-06, P0-07, P0-07a, P0-08, P0-09, P0-10, P0-12, P0-13, P0-14, P1-03 to P1-15, P2-02 to P2-29, P4-02 to P4-14, P5-01 to P5-14
