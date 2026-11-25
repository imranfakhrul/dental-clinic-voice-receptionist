---
id: P5-14
title: HIPAA readiness review (BAAs, policies, risk assessment final)
milestone: P5
epic: E5.2
size: M
labels: area:compliance, type:docs
depends_on: P5-11, P5-12, P5-07, P5-08, P0-10, P0-11, P0-09, P1-05, P1-13
status: approved
---

# P5-14: HIPAA readiness review (BAAs, policies, risk assessment final)

## 1. Summary
This is the final compliance gate before real patients. It has six parts:
- confirm that every PHI vendor has an executed BAA;
- finalize the risk assessment (P0-11 v1 → v2);
- name the HIPAA Security Official and Privacy Official;
- close the gaps P0-11 found with no owner (DECISIONS #76): **G1** workforce security policies, training and sanctions, **G2** periodic access reviews, **G3** a device policy;
- collect the evidence from P0 to P5 into one index;
- get the compliance advisor's review and sign-off.

Done means the **compliance checklist is signed by the compliance advisor and the sponsor**, with no open item in the "never waived" group.

## 2. Why this matters
Plan §8 Phase 5 lists the "HIPAA readiness review: BAAs executed, policies, risk assessment final, incident response plan". Plan §15 says "every vendor that processes PHI has an executed BAA".

The PHI gate (DECISIONS #25) is about the system. This task is about the **organization**: people, policies and proof. If an auditor or the clinic asks "who is your security official?", "when did you last review who has prod access?", or "show me your staff's HIPAA training", the answers and the evidence must exist before John's first real booking.

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P5, Hardening, Testing & Security Review**.
- **Security Official / Privacy Official:** the Security Rule requires a business associate to assign one person responsible for its security policies (45 CFR 164.308(a)(2)). A Privacy Official is required for covered entities, and is good practice for us because the BAA passes us privacy duties such as access requests. **Verify** both with the advisor.
- **Administrative safeguards (Security Rule 164.308):**
  - risk analysis and management;
  - sanction policy;
  - information system activity review;
  - workforce security;
  - security awareness training;
  - incident procedures;
  - contingency plan;
  - evaluation.

  **Verify** the list against the current rule text.
- **Access review:** a periodic check that every account with access to systems holding PHI still needs it, at the right level.
- **BYOD (bring your own device):** staff use their own laptops for work.
- **What already exists (approved):**
  - **P0-10:** the vendor-BAA matrix and `check_vendors.py --gate`.
  - **P0-09:** the clinic BAA and its commitments table.
  - **P0-05 / P0-06:** the Google Cloud BAA record and `docs/compliance/hipaa-controls.md`.
  - **P0-07a:** the messaging compliance memo (to re-check before go-live).
  - **P0-11:** risk register R01–R33, gaps G1–G4.
  - **P0-13:** Vertex AI data-use settings (no training).
  - **P0-14:** the PHI data-flow table.
  - **P1-05:** PAM entitlements and their logs; `iam_audit.py` (DECISIONS #101).
  - **P1-13:** staff accounts, MFA, deactivation.
  - **P1-02:** the NGFW fallback (accepted risk to revisit).
  - **DECISIONS #98:** no row-level security until a second clinic.
  - **P5-07:** the signed emergency rules PDF and the UAT form.
  - **P5-08:** the internal security report. **P5-11:** the pentest report and retest letter.
  - **P5-12:** the IR plan, runbooks, restore drill, tabletops and retention policy.

## 4. Scope
**In scope**
- Designation letters for the Security Official and the Privacy Official.
- Policies (G1): information security policy, acceptable use, sanctions, workforce clearance and termination, and a security awareness training program with records.
- Access review procedure and the first review (G2), plus the offboarding rule.
- Device policy and the first attestations (G3).
- BAA verification (all `signed` in the matrix, re-check of P0-07a sources), the final risk assessment v2, and the evaluation of P0-11 controls with evidence.
- Evidence index `docs/compliance/evidence-index.md`.
- Readiness checklist and its signatures; the exceptions process.

**Out of scope** (and which task covers it)
- Technical tests → P5-08 / P5-11
- IR plan and runbooks → P5-12
- Go-live switch → P6-01

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P5-11 / P5-08 | Reports | Policies, training and access review can start at once |
| P5-12 | IR plan, drill, tabletops | Link the evidence when ready |
| P5-07 | Signed emergency PDF, UAT form | Same |
| Advisor availability | Review and signature | Book review dates when this task starts |

## 6. Interface contract

### Officials (DECISIONS #279)
| Role | Who | Duties |
|---|---|---|
| Security Official | Tech lead | Owns the security policies, access reviews, incident response (with P5-12), risk management |
| Privacy Official | Sponsor (company owner) | Owns privacy duties under the BAA: patient requests forwarded to the clinic, minimum necessary, retention policy, breach notices |
| Compliance advisor (external, part-time) | - | Reviews; signs the readiness checklist; does not hold either role |
Designation letters in `docs/compliance/designations.md`, signed and dated.

### Policies (G1) in `docs/compliance/policies/`
| Policy | Key content |
|---|---|
| `information-security.md` | Scope, roles, PHI handling rules (PHI gate, synthetic data outside prod, PAM for prod), logging rules, review once a year |
| `acceptable-use.md` | No PHI in chat tools, email or tickets; no copying PHI to local files; MFA everywhere; report incidents at once |
| `sanctions.md` | Warning → access removal → termination, by severity; applied consistently; records kept 6 years |
| `workforce-security.md` | Access granted by role, approved by the Security Official; background check per company practice (**Verify** with the advisor whether one is needed); offboarding within **24 h** (all accounts: Google, GitHub, console, PAM, vault) |
| `training.md` | See below |
| `device.md` | See below (G3) |

### Training (DECISIONS #279)
- **Baseline:** a purchased HIPAA workforce course with a certificate (**Verify** the vendor and price, around $30 per person), within 30 days of joining and then once a year.
- **Project module:** an in-house 30-minute slide deck (`docs/compliance/training/project-module.md`) on the PHI gate, synthetic data only outside prod, PAM requests, no PHI in tickets or chats, the incident process, the console's no-export rule, plus a 10-question quiz with a pass mark of ≥ 80%.
- **Records:** `docs/compliance/training/records.csv` (name, course, date, score, certificate link). Kept 6 years.
- Nobody gets prod access (PAM) without a current training record. The access review checks this.

### Access reviews (G2) (DECISIONS #279)
| Scope | Frequency | Reviewer |
|---|---|---|
| GCP IAM on `<prefix>-prod` and the org (incl. PAM entitlement eligibility) | Every 3 months | Security Official; a second reviewer for the Security Official's own access |
| PAM grants actually used in prod (from Cloud Audit Logs) | Monthly during the pilot | Security Official + one other engineer |
| GitHub org (owners, `prod-approvers`, CODEOWNERS teams) | Every 3 months | Security Official |
| Console ADMIN and FRONT_DESK accounts (clinic staff) | Every 3 months, with Sarah | Office manager confirms each person; we remove the rest |
| Workspace / vault / BSP and messaging accounts | Every 3 months | Security Official |
Rule: a reviewer never approves their own account. Procedure: `scripts/compliance/access_review.py` exports current members (from IAM, GitHub API, the console `staff_users` table, PAM logs) into `docs/compliance/access-reviews/<yyyy-qN>.md`, with a keep/remove column. Removals are done within 5 business days and linked.

### Device policy (G3) (DECISIONS #279)
BYOD is allowed with mandatory controls:
- full-disk encryption on;
- screen lock ≤ 5 minutes;
- OS and browser updates within 14 days;
- current anti-malware where the OS supports it;
- no PHI downloads (PHI is only viewed in the console or the GCP console in the browser);
- no shared user accounts on the device;
- a lost or stolen device is reported within 24 hours, triggering a session revoke and password and key rotation.

Each person signs a quarterly attestation (`docs/compliance/device-attestations/<yyyy-qN>.csv`). Company-managed laptops with MDM are revisited when the team or the number of clinics grows (logged in the risk register).

### BAA verification
- `python tools/compliance/check_vendors.py --gate` prints `GATE OPEN`, and every PHI vendor row is `signed` with a link to the executed BAA (P0-10).
- Re-check the P0-07a sources (Meta / BSP terms) and the P0-13 Vertex AI data-use settings. Record the date and the result in the matrix.
- Confirm that the clinic BAA commitments table rows all point to existing evidence (P5-12 now provides IR and retention).

### Risk assessment v2
`docs/compliance/risk-assessment-v2.md`:
- every risk from R01–R33 is re-scored using test evidence (P5-01/03/04/07/08/11);
- the controls are linked to evidence;
- new risks are added (for example findings accepted in P5-11);
- the gap decisions are recorded (G1–G3 closed here, G4 closed by P5-12);
- accepted risks are listed, for example: no RLS (#98), the NGFW fallback if used (P1-02), Binary Authorization if not covered (P5-08), BYOD;
- each accepted risk has an owner and a review date.

### Evidence index (`docs/compliance/evidence-index.md`)
| Safeguard / requirement | Evidence | Location |
|---|---|---|
| Risk analysis | Risk assessment v1, v2 | P0-11, this task |
| BAAs | Matrix + executed BAAs | P0-10, P0-05, P0-07, P0-08, P0-09 |
| Access control | RBAC/MFA tests, authz matrix, PAM config | P1-13, P5-08, P1-05 |
| Audit controls | Audit log, mirror check | P1-12, P1-07 |
| Integrity / transmission | CMEK, TLS, field encryption | P1-03, P1-05, P1-02 |
| Contingency | Restore drill, runbooks | P5-12 |
| Incident procedures | IR plan, tabletops | P5-12 |
| Evaluation | Internal report, pentest + retest | P5-08, P5-11 |
| Workforce (training, sanctions, clearance) | Policies, records | This task |
| Device and media | Device policy, attestations; retention and destruction | This task, P5-12 |
| Clinic approval of safety rules | Signed emergency PDF, UAT form | P5-07 |

### Readiness checklist and exceptions (DECISIONS #279)
`docs/compliance/readiness-checklist.md` has two groups:
- **Never waived:**
  - all PHI vendor BAAs executed;
  - risk assessment v2 reviewed;
  - IR plan and breach procedure in place;
  - restore drill done;
  - pentest retest with 0 open Critical/High;
  - emergency rules approved;
  - officials designated;
  - every person with prod access trained.
- **Can have a time-boxed exception:** for example one policy document still in review, or a training record pending for a person **without** prod access. An exception needs a written plan with a date ≤ 30 days, signed by the compliance advisor **and** the sponsor, and is listed in the checklist and in the P6-07 report.

Signatures: compliance advisor and sponsor. The Security Official countersigns.

## 7. Implementation guide
1. Designation letters.
2. Draft the policies (templates adapted to our size; the advisor reviews).
3. Buy the training course; write the project module and quiz; train everyone; record.
4. Write `access_review.py`; run the first full review; act on removals.
5. Device attestations for everyone.
6. BAA verification and the re-checks.
7. Risk assessment v2 with evidence links; accepted risks with owners.
8. Evidence index.
9. Advisor review meeting; fix what they find; sign the checklist.
10. Notify P6-01 (gate) and P6-07 (exceptions to report). Put the recurring items (quarterly reviews, yearly training, yearly policy review) in the team calendar with owners.

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| A vendor BAA is still pending (for example a messaging provider) | That vendor's feature stays off (P0-10 rule); the checklist item is "signed for every **enabled** PHI vendor" |
| The advisor finds a gap the week before go-live | Never-waived gap → go-live moves; other gap → exception process |
| A team member hasn't finished training | No prod access until they have; not a go-live blocker if they have none |
| A clinic staff member left but still has a console account | Removed at once; logged as a finding; the quarterly review with Sarah adds an "anyone left?" question |
| Device lost | `device.md` steps; P5-12 incident log entry |

## 9. Security, HIPAA and PHI
- **No PHI handled:** documents, records and lists of accounts (names of workforce members are personal data, kept in the private repo or compliance drive).
- Compliance records are kept 6 years (**Verify** with the advisor; 164.316(b)(2)).
- The access-review script reads IAM, GitHub and the console's staff table through `ops-read` PAM. Its output holds usernames and roles only.

## 10. Testing
Not a code task (except the access-review script):
```bash
pytest tools/compliance/tests -q          # access_review export with fixtures
python tools/compliance/check_vendors.py --gate
```
| # | Check | Expected |
|---|---|---|
| T1 | `check_vendors.py --gate` | `GATE OPEN` |
| T2 | Access review export | Every account listed with a keep/remove decision |
| T3 | Training records | Everyone with prod access has a current record |
| T4 | Evidence index links | All resolve |
| T5 | Checklist | Signed; no open never-waived item |

## 11. Acceptance criteria
- [ ] Security Official and Privacy Official designated in writing
- [ ] G1 policies approved and training completed by everyone with access to PHI systems (T3)
- [ ] G2 first access review done and removals completed (T2)
- [ ] G3 device policy published and attestations collected
- [ ] Every enabled PHI vendor has an executed BAA (T1); risk assessment v2 reviewed by the advisor
- [ ] Readiness checklist signed by the compliance advisor and the sponsor, with no open never-waived item (T4, T5)

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Access-review script tested
- [ ] Documents reviewed by the compliance advisor
- [ ] No PHI in any document
- [ ] Evidence index complete; recurring items scheduled; P6-01 and P6-07 notified

## 13. Hand-off
| Consumer | What they can rely on |
|---|---|
| P6-01 Go-live | Signed checklist as the compliance gate |
| P6-04 Pilot | Monthly PAM review during the pilot |
| P6-07 Pilot report | Exceptions and accepted risks with dates |
| Second clinic (future) | Policies and review cadence ready; revisit RLS and MDM |

## 14. Open questions
| # | Question | Recommended answer | Owner |
|---|---|---|---|
| 1 | Is a background check required for engineers with prod access? | Follow the advisor; if required, only for people with PAM eligibility. | Compliance advisor |
| 2 | Which training vendor? | Any reputable HIPAA workforce course with certificates; pick by price. **Verify**. | Sponsor |

## 15. References
- Plan: §6, §8 Phase 5, §15
- DECISIONS: #25, #59, #76, #98, #101, #102, #279
- Related tasks: P0-05, P0-06, P0-07a, P0-09, P0-10, P0-11, P0-13, P0-14, P1-02, P1-05, P1-12, P1-13, P5-07, P5-08, P5-11, P5-12, P6-01, P6-07
- HHS Security Rule guidance: <https://www.hhs.gov/hipaa/for-professionals/security/index.html>
