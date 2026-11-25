---
id: P5-11
title: External penetration test and fixes
milestone: P5
epic: E5.2
size: M
labels: area:security, type:test
depends_on: P5-08
status: approved
---

# P5-11: External penetration test and fixes

## 1. Summary
Hire a qualified third-party firm to penetration-test the system on **staging** (prod-like, synthetic data). Then fix the findings and have the firm retest them.

**Who does what:**
- **The firm** tests every surface we own:
  - the public chat widget and voice WebSocket;
  - the admin console with each role;
  - the public and internal APIs;
  - AI prompt injection;
  - a light review of the Google Cloud configuration.
- **We** fix every Critical and High finding before go-live.
- **The firm** retests those fixes.
- **Mediums** are fixed within 30 days of go-live, or accepted in writing by two people: the tech lead and the compliance advisor.

Done means the firm's retest letter shows no open Critical or High finding.

## 2. Why this matters
The plan's Definition of Done (§15) says: "Security review and penetration test are complete, with critical findings fixed". P0-11 names the pentest as a control for broken access control (R04) and other confidentiality risks.

Our own tests (P5-08) find what we thought to look for. An outside tester brings attackers' habits we don't have. Clinics and their insurers also increasingly ask for a pentest letter before allowing a vendor near patient data.

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P5, Hardening, Testing & Security Review**.
- **Penetration test (pentest):** an authorized, time-boxed attack by professionals, ending in a report of weaknesses with severity and reproduction steps.
- **Rules of engagement (RoE):** the signed document that says what may be attacked, when, from which IPs, what is forbidden (for example denial-of-service), and who to call if something breaks.
- **Grey-box test:** the testers get accounts and documentation, not source code. It finds more in limited time than a black-box test.
- **Frozen release candidate (RC):** a specific container digest deployed to staging that does not change during the test window, so findings and fixes refer to known code.
- **Google Cloud penetration testing policy:** Google does not require notification for testing your own projects, but you must follow its Acceptable Use Policy. **Verify** the current policy page before the test.
- **What already exists:**
  - **P5-08:** internal security report, findings register `docs/security/findings.yaml`, authz matrix, ZAP and Semgrep jobs, test users.
  - **P4-17 / P5-08:** console test users with TOTP secrets.
  - **P0-14:** architecture and data-flow docs, used as tester documentation.

## 4. Scope
**In scope**
- Vendor selection, contract, NDA and RoE.
- Tester accounts and staging preparation.
- The test window, daily check-ins, the report.
- Fixes, retest, the final letter.
- Updates to the findings register and the risk register.

**In the test scope** (DECISIONS #277):
| Target | Detail |
|---|---|
| Chat widget `web` | `https://app.staging.<domain>/widget?clinic=pentest-clinic`, embed script, session handshake, bot protection |
| WebSocket API | Text and voice protocol v2 on `wss://api.staging.<domain>` (crafted messages, session hijack, replay) |
| Admin console | All routes with FRONT_DESK, ADMIN and a second clinic's ADMIN (tenant isolation) |
| Public/internal HTTP API | Including Cloud Tasks and webhook endpoints (signature checks) |
| AI behaviour | Prompt injection, cross-patient access, tool misuse, prompt leakage |
| Cloud configuration (light) | Read-only review with a viewer role: IAM, public exposure, storage buckets, Cloud Run ingress, VPC-SC perimeter |

**Not in the test scope:**
- **Open Dental**, the clinic's systems, the **WhatsApp BSP / Meta**, Google's own services, and Google Workspace. These are third-party systems that we are not authorized to attack. Traffic toward them goes to fakes or test accounts.
- Denial-of-service and volumetric tests; social engineering of staff.

**Out of scope** (and which task covers it)
- Internal scans and red teaming → P5-08
- Incident response if a real issue is exploited → P5-12

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P5-08 | Internal findings fixed, register up to date | Vendor selection and contract can run in parallel |
| Staging (P1-02) | Stable RC | Freeze a digest and record it in the RoE |
| Budget approval | Sponsor sign-off | Get 2–3 quotes early (**Verify** typical cost; estimate $8k–25k) |

## 6. Interface contract

### Vendor criteria (DECISIONS #277)
| Criterion | Requirement |
|---|---|
| Tester qualifications | At least one lead tester with OSCP, CREST CRT/CCT or equivalent |
| Experience | Web apps, APIs, WebSockets; healthcare or HIPAA clients; LLM application testing preferred |
| Method | Grey-box; OWASP WSTG and OWASP Top 10 for LLM Applications as references |
| Deliverables | Draft report, final report (executive summary, findings with CVSS 3.1, reproduction, fix advice), retest letter |
| Retest | Included in the price, within 30 days of fixes |
| Legal | NDA; RoE signed by both sides; insurance (professional liability) |
| Data | No PHI exposure: staging with synthetic data only, so **no BAA is needed**. If the vendor needs prod access at any point, stop and get a BAA first (P0-10) |

Selection is made by the tech lead and the compliance advisor; the sponsor signs the order.

### Rules of engagement (`docs/security/pentest/roe-<date>.md`)
- Window: 10 working days. The RC digest is frozen; only Critical fixes may be deployed during the window, and they are announced to the testers.
- Source IPs of the testers. Staging `RATE_LIMIT_OVERRIDES` relax rate limits for those IPs only where the testers ask, so testing isn't throttled; brute-force tests run with the limits **on**.
- Accounts: `pentest-front-desk-1`, `pentest-admin-1`, `pentest-admin-otherclinic` (TOTP), and patient-side `ZZPEN` personas on `pentest-clinic` and `pentest-clinic-2`.
- Viewer role on `<prefix>-staging` for the cloud review, through a temporary group (expires at the window end).
- Forbidden: DoS, attacks on out-of-scope systems, social engineering, data exfiltration beyond proof (for example 1 record), changing other testers' data.
- Contacts: tech lead (primary), on-call engineer (secondary); a stop-test phone number.
- Daily 15-minute check-in; Criticals reported within 24 hours, not at the end.

### Severity and fix policy (DECISIONS #277)
| Severity | Before go-live | After go-live |
|---|---|---|
| Critical | Fix + vendor retest | - |
| High | Fix + vendor retest | - |
| Medium | Fix or plan | Fixed ≤ 30 days, or accepted in writing by **tech lead + compliance advisor** |
| Low / Info | Backlog | Review in the pilot report |

Risk acceptance is recorded in `docs/security/findings.yaml` (`status: accepted`, `accepted_by: [tech-lead, compliance-advisor]`, reason, review date) and in the P0-11 register. One person can never accept a risk alone.

### Findings intake
Each vendor finding becomes an entry in `docs/security/findings.yaml` with `source: pentest` and a GitHub issue labelled `security`, `pentest`, `sev:<level>`. Issue text never contains secrets or real data.

## 7. Implementation guide
1. Collect 2–3 quotes against the criteria; select; sign the NDA and the order.
2. Write and sign the RoE; schedule the window after P5-08's Critical/High fixes are done.
3. Prepare staging: freeze the RC, create `pentest-clinic` and `pentest-clinic-2` with synthetic data, create the accounts, the temporary viewer group and the rate-limit overrides (release PR, reverted afterwards).
4. Send the tester pack: architecture overview (P0-14, without secrets), API docs, the WebSocket protocol doc, accounts (through a secure channel), and the known accepted risks.
5. Run the window with daily check-ins; triage Criticals at once.
6. Receive the draft report; check the facts; get the final report.
7. Fix Critical/High findings with tests (regression cases go to P5-08 suites); deploy to staging; request the retest.
8. Get the retest letter; update the register; remove the accounts, group and overrides.
9. Store the reports in `docs/security/pentest/` (private repo + compliance drive). Notify P5-14 and P6-01.

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| Testers break staging (for example fill the DB) | Stop-test call; restore staging; extend the window by the lost time |
| A Critical is found on day 2 | Hot-fix allowed during the window, announced to testers; they retest it before the report |
| Finding in an out-of-scope third party (for example a BSP issue) | Recorded as `third_party`; reported to that vendor through its channel; not our fix |
| Vendor needs prod to reproduce something | Not allowed without a BAA and a new RoE; reproduce on staging instead |
| Retest shows a fix incomplete | Back to the fix loop; go-live waits |
| Budget too low for full scope | Keep widget, WebSocket, console and AI; drop the cloud review (P5-08 covers some of it) |

## 9. Security, HIPAA and PHI
- **No PHI:** staging, synthetic data only (DECISIONS #25), so the vendor is not a business associate. The RoE forbids any prod access.
- Tester credentials are sent through a secure channel (shared vault item), not email, and are revoked at the end.
- Reports are confidential company documents (they describe weaknesses), stored with restricted access.
- Audit: account creation and removal, the temporary IAM group, and rate-limit override PRs.

## 10. Testing
Not a code task; verification steps:
| # | Check | Expected |
|---|---|---|
| T1 | RoE signed and the RC digest recorded | Yes, before day 1 |
| T2 | Every Critical/High has a fix PR with a regression test | Yes |
| T3 | Vendor retest letter | No open Critical/High |
| T4 | Pentest accounts, group and overrides removed | Verified in IAM, console users and config |

## 11. Acceptance criteria
- [ ] A qualified vendor tested every in-scope target listed in §4 on a frozen RC (T1)
- [ ] All Critical and High findings fixed, with regression tests, and retested by the vendor (T2, T3)
- [ ] Mediums have a fix date ≤ 30 days after go-live or a two-person acceptance in the register
- [ ] Test access removed after the retest (T4)

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Fix PRs reviewed by a second engineer
- [ ] No PHI exposed to the vendor
- [ ] Reports stored; findings register and P0-11 register updated; P5-14 and P6-01 notified

## 13. Hand-off
| Consumer | What they can rely on |
|---|---|
| P5-14 HIPAA review | Final report and retest letter as evidence |
| P6-01 Go-live | Gate item "pentest retest: 0 open Critical/High" |
| P6-07 Pilot report | Medium/Low status |

## 14. Open questions
| # | Question | Recommended answer | Owner |
|---|---|---|---|
| 1 | Do we repeat the pentest yearly? | Yes, and after major changes (for example a second clinic or a new channel). | Sponsor |

## 15. References
- Plan: §15 (Definition of Done), §6, §8 Phase 5
- DECISIONS: #25, #122, #277
- Related tasks: P0-10, P0-11, P0-14, P1-02, P4-17, P5-08, P5-12, P5-14, P6-01, P6-07
- OWASP WSTG: <https://owasp.org/www-project-web-security-testing-guide/> · OWASP Top 10 for LLM Applications: <https://owasp.org/www-project-top-10-for-large-language-model-applications/>
- Google Cloud penetration testing / AUP: **Verify** the current page before the test
