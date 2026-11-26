# Security Rule safeguard coverage (v1)

> Draft v1, 2026-11-26. One row per standard in 45 CFR 164.308, 164.310, 164.312, 164.314 and 164.316, as listed in eCFR on 2026-11-24 (sources K1–K4, L2). Tasks are survivor IDs. "Planned" means no control is in place yet (no product code exists).

## Administrative safeguards (164.308)
| Standard | Risks | Controls (tasks) |
|---|---|---|
| (a)(1) Security management process: risk analysis, risk management, sanction policy, information system activity review | All | This assessment (P0-11), final review (P5-14); sanction policy (G1 → P5-14); activity review via audit log and alerts (P1-07) |
| (a)(2) Assigned security responsibility | R31 | Compliance owner named by the sponsor (P0-10 open question); incident commander role (P5-12) |
| (a)(3) Workforce security (authorization, clearance, termination) | R32, R33 | Group-based IAM (P0-05), console roles (P1-13), clearance and offboarding policy (G1/G2 → P5-14) |
| (a)(4) Information access management | R04, R06, R12 | Least-privilege service accounts (P1-05), RBAC (P1-13), least-privilege Open Dental key (P0-12) |
| (a)(5) Security awareness and training | R05, R11, R33 | Training and acceptable-use policy (G1 → P5-14) |
| (a)(6) Security incident procedures | R31 | Incident response plan and breach runbook (P5-12) |
| (a)(7) Contingency plan | R21–R24 | Runbooks, backup and restore drill, retention (P5-12, absorbed P5-13; G4); backups and PITR (P1-03) |
| (a)(8) Evaluation | All | Review triggers (assessment §7), HIPAA readiness review (P5-14), pen test (P5-11) |
| (b)(1) Business associate contracts | R07, R29, R35, R36 | Vendor BAAs and records (P0-05, P0-07, P0-08), vendor matrix and gate (P0-10), clinic BAA (P0-09) |

## Physical safeguards (164.310)
Data-centre facilities are Google's, covered under the Google Cloud BAA (once accepted, R29). Our part is the team's own devices.

| Standard | Risks | Controls (tasks) |
|---|---|---|
| (a)(1) Facility access controls | R10 | Google data centres under the Google Cloud BAA (P0-05). We have no facility holding ePHI: **not applicable** to our office |
| (b) Workstation use | R33, R38 | Acceptable-use and device policy (G1/G3 → P5-14); no PHI on laptops |
| (c) Workstation security | R33, R38 | Device policy: disk encryption, screen lock, updates (G3 → P5-14) |
| (d)(1) Device and media controls (disposal, re-use, accountability, backup) | R24, R33, R38 | Device policy (G3 → P5-14); backups managed by Cloud SQL (P1-03); return/destroy with certificate (P5-12, clinic BAA C13) |

## Technical safeguards (164.312)
| Standard | Risks | Controls (tasks) |
|---|---|---|
| (a)(1) Access control (unique user ID, emergency access, automatic logoff, encryption) | R04, R05, R06, R10 | Staff auth with MFA and idle timeout (P1-13), break-glass (P0-05), CMEK and field encryption (P1-03, P1-05) |
| (b) Audit controls | R20, R31 | Append-only audit log (P1-07, was P1-12), Data Access audit logs (P1-07) |
| (c)(1) Integrity | R16–R20 | Deterministic code acts (P0-04, P2-04), idempotency and re-check (P2-08, P1-20), append-only audit (P1-07) |
| (d) Person or entity authentication | R02, R05 | Patient verification with ≥2 identifiers (P2-12), staff MFA (P1-13) |
| (e)(1) Transmission security | R08, R09, R15 | TLS everywhere (P1-02), TLS compliance rule for email (P0-08), minimal message content (P0-07a) |

## Organizational requirements (164.314)
| Standard | Risks | Controls (tasks) |
|---|---|---|
| (a)(1) Business associate contracts or other arrangements | R29, R30, R35, R36 | Clinic BAA template with required terms (P0-09), vendor BAAs (P0-05, P0-07, P0-08) |
| (b)(1) Requirements for group health plans | - | **Not applicable:** we are not a group health plan or a plan sponsor |

## Policies, procedures and documentation (164.316)
| Standard | Risks | Controls (tasks) |
|---|---|---|
| (a) Policies and procedures | All | Policies (G1 → P5-14); runbooks (P5-12) |
| (b)(1) Documentation (written, kept 6 years, reviewed periodically) | R30 | This folder, DECISIONS.md and git history; 6-year audit retention (P1-07); review triggers (assessment §7) |

22 standards, each with risks and controls or a reason it doesn't apply.
