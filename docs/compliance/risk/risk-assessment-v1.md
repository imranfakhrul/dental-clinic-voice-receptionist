# HIPAA security risk assessment v1

| | |
|---|---|
| Version | **v1 draft**, 2026-11-26 (P0-09 inputs, P0-10 vendor matrix) |
| Status | Reviewed by the compliance advisor (mock persona, §8). **Not final:** the final assessment and sign-off before go-live is P5-14 |
| Register | [risk-register.md](risk-register.md): 38 risks. Check: `python3 scripts/compliance/check_risk_register.py` |
| Safeguards | [safeguard-coverage.md](safeguard-coverage.md) · Acceptances: [accepted-risks.md](accepted-risks.md) |
| Sources | [sources/README.md](../sources/README.md#p0-11-risk-assessment-checked-2026-11-26) K1–K6 (eCFR as of 2026-11-24, HHS guidance, Federal Register) |

Basis: the Security Rule requires a business associate to "conduct an accurate and thorough assessment of the potential risks and vulnerabilities to the confidentiality, integrity, and availability of electronic protected health information" it holds, and to reduce them "to a reasonable and appropriate level" (45 CFR 164.308(a)(1)(ii)(A)–(B), K1).

Detail level: this repository is public, so risks are described by category, asset and planned control only. No hostnames, project numbers, keys or attack steps.

## 1. Scope
**In scope:**
- **The system:** all four Google Cloud projects (`dai-rcpt-dev`, `-staging`, `-prod`, `-ops`). Real PHI is only ever allowed in prod (DECISIONS #25), but dev and staging are assessed for the risk of real data reaching them.
- **Components:** the patient widget, the admin console, the backend, the data stores, the local development setup (local-first, DECISIONS #302), and every vendor in [vendors.yaml](../vendors.yaml).
- **Team operations:** cloud access, GitHub, staff and engineer accounts, laptops, joiners and leavers.
- **AI and patient-safety risks** (category S).
- **Legal review of the vendor BAA terms** (R29, DECISIONS #58).

**Out of scope:**
- The clinic's own Open Dental server and network: the clinic's own risk analysis (stated in the clinic BAA, P0-09).
- The final architecture diagram (P0-14), the incident plan (P5-12), penetration testing (P5-11) and the final review (P5-14).

**Situation on 2026-11-26** (this shapes the scores):
- No product code exists. Every control is **planned**, none in place.
- The Google Cloud projects sit in a personal account with no organization, so org policies and VPC-SC are written but **not applied** (DECISIONS #296).
- Every vendor BAA is NOT ACCEPTED and the clinic BAA is NOT SIGNED. The PHI gate is **CLOSED** ([vendor-matrix.md](../vendor-matrix.md)).
- Hosting is local-first until the client chooses (DECISIONS #302).

## 2. Method and scales
**Method (DECISIONS #55):** the HHS Guidance on Risk Analysis elements (K5), in NIST SP 800-30 Rev. 1 style:

| HHS element | Where |
|---|---|
| Scope of the analysis | §1 |
| Data collection (where ePHI is) | §3, §4 |
| Threats and vulnerabilities | Register, "Risk" column |
| Current security measures | Register, "Controls" (planned or in place) |
| Likelihood, impact, level of risk | Register, scores |
| Documentation | This folder and its git history |
| Periodic review and update | §7 |

The HHS SRA Tool is not used: it is built for a provider's own office, not a SaaS business associate.

**Likelihood (L)**, over the next 12 months, with the planned controls **not yet** in place:

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
- **Low** 1–4: accept and monitor.
- **Medium** 5–9: control planned within the MVP.
- **High** 10–16: control required before real PHI (the PHI gate).
- **Critical** 20–25: control required before any further work on the affected part.

**Residual** = re-scored assuming the planned controls are in place. Target: Medium or lower for every risk, unless a sponsor acceptance exists (DECISIONS #57). On a disagreement the higher score is used and noted in the row.

## 3. Asset inventory
Owner tasks are survivor IDs (merged IDs in brackets).

| # | Asset | Type | ePHI? | Environment | Owner task | Flows | Risks |
|---|---|---|---|---|---|---|---|
| A01 | Patient widget (Next.js) | Web app in the patient's browser | In transit / in memory | all | P2-25 | F1 | R02, R15, R25, R26, R28 |
| A02 | Admin console | Web app | Displays PHI | all | P4-09 | F9 | R04, R05, R32 |
| A03 | Backend API and orchestrator | Server service | Processes | all | P1-01 (was P1-08), P2-01 | F1–F9 | R02, R03, R16–R18, R26–R28 |
| A04 | Postgres database | Database (CMEK in cloud) | Stores (encrypted fields) | all; real data only in prod | P1-03 (was P1-09) | F5 | R10, R14, R20, R24 |
| A05 | Redis | Session and slot memory | Stores (TTL, encrypted) | all | P1-02 (was P1-04), P2-01 (was P2-02) | F5 | R10 |
| A06 | Cloud Tasks / Scheduler | Queues (reminders, emails) | Task payloads: IDs only (Proposed) | all | P1-02 (was P1-04), P4-04 | F5 | R19 |
| A07 | Cloud Logging / Monitoring | Logs | **Must not** contain PHI | all | P1-07 (was P1-11) | F8 | R01, R31 |
| A08 | Secret Manager and KMS | Secrets and keys | Keys that protect PHI | all | P1-05 | F4, F5 | R06, R12 |
| A09 | Vertex AI (Gemini) | LLM | Processes (prompts) | all | P2-03, P0-13 | F2 | R03, R07, R13, R18, R22, R27 |
| A10 | Speech-to-Text / Text-to-Speech | Speech | Processes audio and text | all | P3-03 (was P3-05) | F3 | R13, R22 |
| A11 | Gmail (`callbacks@`) | Email | Only in `full_details` mode | prod | P2-22 (was P2-23), P0-08 | F6 | R08, R23 |
| A12 | Twilio (SMS) / Meta (WhatsApp) | Messaging | Minimal message content | staging, prod (Meta also dev, synthetic) | P4-01, P0-07 | F7 | R09, R19, R35 |
| A13 | Open Dental API relay and the clinic's eConnector | Clinic's system of record | Source of all PHI | test DB only in dev/staging | P1-15 | F4 | R12, R16, R17, R21, R36 |
| A14 | GitHub | Code, issues, CI | **Must not** contain PHI | team | P1-01, P1-06 | - | R11, R32 |
| A15 | Staff and engineer accounts and laptops | People and devices | Access to the console and cloud | team | P0-05, P1-13 | F9 | R05, R06, R32, R33, R38 |
| A16 | Local development stack (docker compose: API, Postgres, Redis) | Developer machines | **Must not** contain PHI (synthetic only) | dev (local) | P1-01 | - | R38 |
| A17 | Terraform state bucket (`<prefix>-ops-tfstate`) | Infrastructure state | No PHI; contains resource config | ops | P0-05, P0-06 | - | R06 |
| A18 | Backups and point-in-time recovery | Database copies | Stores (encrypted) | prod | P1-03, P5-12 (was P5-13) | F5 | R10, R24 |

Every asset with ePHI (A01–A13, A18) appears in at least one flow and at least one risk. A14–A17 must never hold PHI; the risks that cover that are listed.

## 4. Data flows (v1; replaced by the P0-14 diagram)
PHI elements refer to [Annex A](../baa/annex-a-data-and-purposes.md) rows A1–A8.

| # | From → To | PHI elements | Protection (planned) | Risks |
|---|---|---|---|---|
| F1 | Patient browser → backend | Voice audio, chat text, identifiers (A1, A3, A6) | TLS 1.2+; session token (P1-13, was P1-14) | R02, R15, R25 |
| F2 | Backend → Vertex AI | Compact context, PHI masked where possible (P2-04) | Private access within the VPC-SC perimeter (not applied yet, R34); Google Cloud BAA | R03, R07, R13, R18 |
| F3 | Backend → Speech-to-Text / Text-to-Speech | Audio and reply text (A6) | As F2; STT data logging off (P0-06) | R13, R22 |
| F4 | Backend ↔ Open Dental API | Search identifiers, patient and appointment data (A1, A2) | TLS; keys in Secret Manager (P1-15) | R12, R16, R17, R21, R36 |
| F5 | Backend → Postgres / Redis | IDs, encrypted fields, callback cases, consent (A1–A4, A8) | CMEK and field encryption (P1-03, P1-05) | R10, R14, R24 |
| F6 | Backend → Gmail → clinic admin | Link only by default; full details only if approved (A5) | TLS compliance rule (P0-08) | R08, R23 |
| F7 | Backend → messaging provider → patient | First name, clinic, date, time (A4) | Provider BAA; consent (P4-02); `messaging_policy.yaml` | R09, R19, R35 |
| F8 | Backend → Cloud Logging | **None allowed** | Redaction (P1-07, was P1-11); scans (P5-08) | R01 |
| F9 | Staff browser ↔ admin console | Callback cases, activity log | MFA and RBAC (P1-13) | R04, R05 |

## 5. Results summary
38 risks: R01–R33 from the task spec, plus R34–R38 found in this review.

| Band | Inherent | Residual |
|---|---|---|
| Critical (20–25) | 0 | 0 |
| High (10–16) | 28 | 0 |
| Medium (5–9) | 10 | 18 |
| Low (1–4) | 0 | 20 |

By category: C 17 · I 5 · A 5 · S 3 · V 4 · O 4.

**Top inherent risks:**
- **R01, score 16:** PHI in logs.
- **Score 15:**
  - R02 impersonation;
  - R03 prompt injection;
  - R04 broken access control;
  - R07 PHI to a vendor without a BAA;
  - R31 late breach detection;
  - R34 real PHI before org guardrails exist.

**Every High risk has planned controls with survivor task IDs, and a residual of Medium or lower.** No risk needs acceptance in v1 ([accepted-risks.md](accepted-risks.md) is empty).

**Highest residuals** (score 8):
- R01 PHI in logs;
- R02 impersonation;
- R21 Open Dental outage (outside our control);
- R31 late breach detection;
- R32 leaver access;
- R37 hosting change.

**Scoring-session changes:**
- **R13:** likelihood raised from 2 to 3, because the abuse-monitoring logging question is still open in P0-13.
- **R17:** the control changed from "slot lock" to "re-check before booking", because there is no slot hold (CLAUDE.md rule 9).

**Open dependencies that keep residuals from being real yet:**
- **R29:** no counsel.
- **R34:** no organization.
- **R36:** counsel's answer on the Open Dental relay.

All three keep the PHI gate closed.

## 6. Gaps and decisions
Decided by Morgan Lead (sponsor, mock), 2026-11-26. Logged in DECISIONS #310, closing the pending decision in DECISIONS #59.

| Gap | What is missing | Decision |
|---|---|---|
| G1 | Workforce security policies, HIPAA training, sanctions policy (164.308(a)(1)(ii)(C), (a)(3), (a)(5), K1) | **P5-14**: its spec already delivers the policies and training in `docs/compliance/policies/`. No new task. |
| G2 | Periodic access reviews (cloud, GitHub, console, Open Dental keys) | **P5-14**: quarterly access review and offboarding rule (already in its spec). |
| G3 | Device and endpoint policy (disk encryption, screen lock, updates) | **P5-14**: device policy (already in its spec). Also covers local development (R38). |
| G4 | Contingency plan as a whole (164.308(a)(7)) | **P5-12**, which absorbed P5-13: runbooks, backup and restore drill, retention. The advisor confirms at P5-14 that together they meet the standard. |

## 7. Review triggers
Review and update this assessment when any of these happen:
- P0-14 lands (replace §4 with the data-flow diagram);
- the **hosting decision** is made (DECISIONS #302, R37);
- a vendor or Google API is added or changed (`vendors.yaml`, `allowed_services.yaml`);
- a PHI data category is added (Annex A change);
- an organization is created and the guardrails are applied (R34);
- a vendor BAA or the clinic BAA is signed;
- the 2025 Security Rule update is finalized (still a proposed rule on 2026-11-26, K6);
- before go-live (P5-14);
- after any security incident;
- and at least once a year.

## 8. Sign-off
| Role | Name | Date | Result |
|---|---|---|---|
| Tech lead (scoring session) | Riley Tech | 2026-11-26 | Scores reviewed; two changes (R13, R17); new risks R34–R38 |
| Sponsor (gap decisions) | Morgan Lead | 2026-11-26 | G1–G3 → P5-14, G4 → P5-12 |
| Compliance advisor (review) | Sam Comply | 2026-11-26 | v1 draft reviewed (checks below). **Not the final sign-off** (P5-14) |

**Reviewer checks (task spec §10):**

| Check | Result |
|---|---|
| Every asset with ePHI appears in at least one flow and one risk | **Pass**: A01–A13, A18 (§3 columns) |
| Every `vendors.yaml` vendor with `phi` yes or conditional appears in a risk | **Pass**: checker rule K5 (google-cloud, google-workspace, twilio, meta-whatsapp, open-dental) |
| Every High/Critical risk has existing survivor task IDs and a residual ≤ Medium or an acceptance | **Pass**: checker rules K3 and K4; 28 High, all residual ≤ 8 |
| Every gap has a decision logged in DECISIONS.md | **Pass**: G1–G4, DECISIONS #310 |
| Every Security Rule standard has a risk/control or a reason | **Pass**: [safeguard-coverage.md](safeguard-coverage.md), 22 rows |
| BAA records show the legal review done (R29) | **Not met**: pending in all five records (no counsel engaged). R29 stays open. |

Advisor's comments:
1. "The register is sound for a v1. The residuals assume controls that don't exist yet, which is correct for a plan, but the PHI gate must stay closed until P5-14 confirms they're in place."
2. "R29 and R36 need counsel. Don't let them slide to go-live week."
3. "Confirm the status of the 2025 Security Rule update before P5-14. If finalized, re-check the asset inventory and network map."
