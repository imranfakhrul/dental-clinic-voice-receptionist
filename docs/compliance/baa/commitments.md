# Clinic BAA commitments (v1)

> Draft. Version v1, 2026-11-26, for [template v1](clinic-baa-template-v1.md).

**Rule:** no term goes into a clinic BAA unless it has a row here, with an owner task and the tech lead's confirmation that it's feasible. If a promise isn't feasible, change the proposed value, not the task list. Every agreed change during negotiation is logged in `DECISIONS.md` and the owner task is notified.

Owner tasks are the **survivor** tasks. Where the task spec named a merged task, the original is shown in brackets: P1-09 → P1-03, P1-10 → P1-05, P1-11 and P1-12 → P1-07, P5-10 → P5-08, P5-13 → P5-12.

| # | Commitment | Template | Proposed value | Implemented by | Checked in | Feasible? (Riley Tech, tech lead, 2026-11-26) |
|---|---|---|---|---|---|---|
| C1 | Use PHI only for the Services in Annex A; minimum necessary (R1, P5) | 4.1, 4.3, 4.4 | Only the Annex A categories | P0-04 PHI slot list, P2-04 PHI masking, `messaging_policy.yaml` field limits, P0-08 `link_only` | Annex A coverage check (re-run per change), P5-14 | Yes |
| C2 | No other use or disclosure (R2) | 3.1, 4.2 | - | P1-13 access control, P1-07 (P1-11 PHI-free logs) | P5-08 (P5-10 authorization tests, PHI-in-logs scan), P5-14 | Yes |
| C3 | Safeguards and Security Rule (R3) | 3.2 | Encryption at rest and in transit, access control, PHI-free logs, audit | P0-06, P1-03 (CMEK), P1-05 (P1-10 field encryption), P1-07 (P1-11, P1-12), P1-13 | P5-08, P0-11 risk assessment, P5-14 | Yes |
| C4 | Breach notice (R4, P1) | 3.3.2, 3.3.3 | 5 business days from discovery, then updates | P5-12 incident response plan and breach runbook (DECISIONS #278) | P5-12 tabletop, P5-14 | Yes, with P5-12's daily alert-watcher during clinic hours. A 24-hour deadline would need on-call outside hours (disabled today, DECISIONS #278): not feasible now |
| C5 | Report other non-permitted uses and security incidents; unsuccessful incidents in aggregate on request (R4, P2) | 3.3.1, 3.3.4 | Aggregate summary on written request | P5-12 incident log, P1-07 monitoring | P5-12 tabletop | Yes |
| C6 | Who notifies individuals | 3.3.5 | The clinic, unless agreed otherwise | P5-12 communication templates (support the clinic) | P5-12 | Yes (counsel to confirm) |
| C7 | Subcontractor BAAs before any PHI (R5) | 3.4.1, 3.4.3 | - | P0-05, P0-07, P0-08 records, P0-10 vendor matrix; `messaging_policy.yaml` gate | P0-10, P5-14 | Yes (all four still pending; gate stays closed) |
| C8 | 30-day notice of a new subcontractor (P7) | 3.4.2 | 30 days | P0-10 vendor matrix change process; [Annex B](annex-b-subcontractors.md#changes) | P5-14 | Yes |
| C9 | Patient access and amendment requests (R6, R7) | 3.5, 3.6 | Forward to the clinic within 5 business days; help retrieve data | P5-12 runbook "patient access requests" | P5-12, P5-14 | Yes (we keep no patient records; Open Dental is the record) |
| C10 | Accounting of disclosures (R7) | 3.7 | Information within 10 business days of the clinic's request | P1-07 audit log (actions, recipients by type), P5-12 runbook | P5-14 | Yes (audit log records each disclosure to a subcontractor by type; to add to the P5-12 runbook) |
| C11 | Carry out clinic obligations under the Privacy Rule (R8) | 3.8 | Applies only if we take on a clinic duty (none planned) | - (none planned) | P5-14 | Yes |
| C12 | Books and records to HHS (R9) | 3.9 | - | This folder, DECISIONS.md, P0-11, P5-12 incident log | P5-14 | Yes |
| C13 | Return or destroy at termination (R10, P8) | 5.3 | 30 days; written certificate; backups expire (at most 30 daily backups) under continued protection | P5-12 (P5-13 return/destroy procedure, certificate template, retention jobs) | P5-12 drill | Yes |
| C14 | Termination for cause (R11) | 5.2 | Optional cure period [30 days] | Contract only (sponsor) | - | Yes |
| C15 | No AI training, no sale (P3) | 4.5 | Prohibited, including at subcontractors | P0-13 (Vertex AI data settings: no training on customer data, durable caching off, request-response logging off; abuse-monitoring question open), P2-03 | P0-13, P5-14 | Yes, subject to P0-13 confirming Google's data-use terms |
| C16 | US-only storage and processing (P4) | 3.10 | US regions only | P0-06 guardrails (location policy, allowed services) | P0-06 tests, P5-14 | Yes on Google Cloud. If hosting changes (DECISIONS #302), re-check before PHI |
| C17 | Access from outside the US (P6) | 3.11 | **Open** | P1-13 / P1-05 access controls, if the sponsor chooses option 1 | P5-14 | Open question; not feasible to promise until decided |
| C18 | No de-identification without written consent (P9) | 4.6 | Prohibited without consent | No task produces de-identified data; P5-01 evals use synthetic data only | P5-14 | Yes |
| C19 | Transcript retention | Annex A A7 | 0 days (P0-01 Q9); at most 30 if the pilot enables it | P1-19 `privacy.transcript_retention_days`, P5-12 retention job | P5-12 | Yes |
| C20 | Audit log retention | Annex A A8 | 6 years (Proposed) | P1-07 (P1-12) `AUDIT_RETENTION_DAYS` = 2190 | P5-12, P5-14 | Yes (counsel to verify 6 years) |
| C21 | Notify the clinic before an Annex A change | 7.2 | Written agreement before a new category or purpose | Change process in this folder; P0-14 data-flow diagram | P5-14 | Yes |
| C22 | No use for our own management and administration; no data aggregation | 4.7 | Not permitted | No task uses clinic PHI for company administration or aggregates it across clinics (P1-19 keeps clinics separate by `clinic_id`) | P5-14 | Yes (counsel to confirm the choice) |

**Coverage:** every R1–R11 and P1–P9 term in the [checklist](requirements-checklist.md) has a row: R1 C1, R2 C2, R3 C3, R4 C4–C5, R5 C7, R6–R7 C9–C10, R8 C11, R9 C12, R10 C13, R11 C14, P1 C4, P2 C5, P3 C15, P4 C16, P5 C1, P6 C17, P7 C8, P8 C13, P9 C18. Template terms that aren't in the checklist have C6, C19–C22. Sections 3.3 and 3.4 are headings; their sub-sections are covered.
