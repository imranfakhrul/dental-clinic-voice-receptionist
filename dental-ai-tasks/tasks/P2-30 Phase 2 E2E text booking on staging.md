---
id: P2-30
title: "Phase 2 E2E: text booking on staging"
milestone: P2
epic: E2.6
size: M
labels: area:qa, type:test
depends_on: P0-12, P1-06, P2-16, P2-18, P2-20, P2-22, P2-25, P2-27
status: approved
---

# P2-30: Phase 2 E2E: text booking on staging

## 1. Summary
Build an automated Playwright suite that acts like a patient in the real widget on **staging** — real WebSocket, real Gemini on Vertex AI, real Open Dental test database (B) — and checks the results where they land: the chat window, Open Dental, the app database and the audit log. Eight scenarios cover the Phase 2 promise: new and existing patient booking, reschedule, cancel (outside and inside the notice window), callback, emergency (Tier 1 and Tier 2), FAQ and a double-booking race.

Done means:
- the suite is green on staging with the Open Dental test DB;
- it runs nightly;
- it is a required gate before a release is promoted from staging to prod;
- every run produces a PHI-free report with pass/fail per scenario, retries, first-chunk latency and Playwright traces.

## 2. Why this matters
Plan §8 Phase 2's deliverable is "end-to-end booking via text chat on staging with the Open Dental test DB". Unit and integration tests use fakes (`od_fake`, `FakeLlmProvider`); only this suite proves the pieces work together on the real stack: Cloud Run WebSockets, Redis state across instances, Gemini output passing the guardrails, Open Dental's throttle and local-time behaviour, Cloud Tasks and the Gmail route. It is the go/no-go check for Phase 2 and the base for P5-01's conversation evals. Pilot KPIs it protects: 0 double bookings, 100% emergency escalation, ≥ 70% bookings without callback, 100% callback emails delivered.

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P2, Text Chat Receptionist**.
- **Playwright:** browser automation for end-to-end tests; traces record each step for debugging. <https://playwright.dev/docs/intro>.
- **What already exists:**
  - **P0-12** (approved): test DB (B), our Open Dental + eConnector VM with synthetic seed data, resettable from a snapshot; customer key `od-customer-key-testdb` (dev and staging only); tests create their own patients with the prefix `ZZTEST` and clean up by breaking their appointments.
  - **P1-06** (approved): `nightly.yml` (environment `nightly`, SA `sa-ci-tests`), `promote.yml` with release PRs for staging and prod.
  - **P2-25** (approved): widget, protocol v1, Playwright harness, test clinic page, staging latency check; bot protection with reCAPTCHA Enterprise.
  - **P2-27** (approved): stable `data-testid`s on slot cards, chips, the confirmation card's Yes and Change buttons, info cards, emergency banner.
  - **P2-16 / P2-18 / P2-20 / P2-22** (approved): the flows under test, each with its own staging smoke script (`booking_e2e.py`, `change_e2e.py`, `callback_e2e.py`); this suite drives them through the browser instead.

## 4. Scope
**In scope**
- Playwright suite `frontend/e2e/staging/` with the 8 scenarios in §6.
- A small read-only **verification client** that checks Open Dental test DB (B) and the staging app DB.
- The staging-only bot-protection bypass for tests.
- Test-data factory, run IDs, cleanup.
- Report (JSON + HTML) and its upload as a CI artifact; nightly job; promote gate.

**Out of scope** (and which task covers it)
- 100+ conversation scenarios and LLM-quality evals → P5-01 (absorbed P5-02)
- Voice E2E → P3 phase test
- WhatsApp confirmations and reminders → P4 phase test
- Load and race tests at scale → P5-03

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P2-25 / P2-27 (approved) | Widget and test IDs | Write scenarios against the local stack (`docker compose` + `od_fake` + `FakeLlmProvider`) with `E2E_TARGET=local` |
| P0-12 (approved) | Test DB (B) | Local runs use `od_fake` loaded with the same seed |
| P1-06 (approved) | Nightly and promote workflows | Run by hand with `pnpm e2e:staging` |
| Flows (approved) | Behaviour | Scenarios are written from the specs; local runs catch mismatches early |

## 6. Interface contract

### Scenarios (DECISIONS #218)
| ID | Scenario | Patient actions (abridged) | Checks |
|---|---|---|---|
| S1 | New patient booking | "I'd like a cleaning" → New patient → name, DOB, phone, email → registration card Yes → tap a slot card → confirmation card Yes | Registration card rows; booked card; **Open Dental:** new patient `ZZTEST…` exists once, appointment at the chosen time with AI marker; app DB `appointment_refs` row; audit `patient.create`, `appointment.book` |
| S2 | Existing patient booking | Seeded `ZZTEST` patient: name, DOB, phone → verified → reason → asks "Tuesday at 3" → nearest-after offer → Yes → card Yes | Nearest-after reply names the requested time (DECISIONS #195); booked; one appointment; audit `patient.verify` |
| S3 | Reschedule | Verified S2 patient → "When is my appointment?" → list card → tap Reschedule → pick a new slot → card shows Current and New → Yes | **Open Dental:** same AptNum, new time; audit `appointment.reschedule` |
| S4 | Cancel outside and inside the notice window | (a) cancel the S3 appointment (> 24 h away) with reason chip → Yes → rebook offer "No, thanks"; (b) appointment created by the setup 3 h ahead → "cancel it" | (a) Open Dental `Broken` + Unscheduled list, note with reason; (b) inside-notice reply, **no** Open Dental change, audit `appointment.change_refused` |
| S5 | Callback | (a) "Can I talk to a person?" → name, phone, DOB, best time → callback card Yes; (b) a reason whose test-clinic config is `when_not_bookable: callback` | Case `OPEN` with the right category and detail, contact encrypted (no plaintext in the row), `case_ref` shown; `email_status = SENT` within 60 s; one case per session even after repeating the request |
| S6 | Emergency | (a) "I can't breathe and my face is swelling" mid-booking; (b) new session "my face is really swollen and it hurts so much" | (a) emergency banner with `tel:911`, Tier 1 script text exactly from config, URGENT case created with no card, booking controls stale, later "just book me" gets the handoff reply; (b) earliest urgent opening offered before identification, then booked (or URGENT case when none) |
| S7 | FAQ | "What are your hours?" then "Do you take Delta Dental?" mid-booking | Answers equal the test-clinic config strings exactly; flow resumes to the pending question |
| S8 | Double-booking race | Two browser contexts, two `ZZTEST` patients, same slot, both tap Yes within 100 ms | Exactly one appointment in Open Dental for that slot; the other session gets the slot-taken apology with alternatives |

### Assertion rules (DECISIONS #219)
- **Exact:** template and script text (P2-04 templates, P0-03 scripts, FAQ config strings), card rows, info cards, choice labels built by code.
- **Structural** for LLM-phrased replies: state reached (`data-state` attribute exposed only when `E2E_EXPOSE_STATE=1` in dev/staging), presence of expected choices, no guardrail fallback counted as failure only when the scenario says so.
- **Ground truth:** Open Dental and app-DB records via the verification client, never the chat text alone.
- **Retry:** each scenario may retry once (new run ID, new patient); a retried pass is reported as `flaky`; two failures fail the suite. More than 2 flaky scenarios in 3 consecutive nights opens an issue automatically.

### Verification client (`frontend/e2e/staging/verify/`, read-only)
```ts
interface Verify {
  odPatientsByLastName(prefix: string): Promise<{ patNum: number; lName: string; fName: string; birthdate: string }[]>;
  odAppointment(aptNum: number): Promise<{ aptNum: number; patNum: number; aptDateTime: string; aptStatus: string; note: string }>;
  odAppointmentsForPatient(patNum: number): Promise<{ aptNum: number; aptDateTime: string; aptStatus: string }[]>;
  appCase(sessionId: string): Promise<{ status: string; urgency: string; reasonCode: string; reasonDetail: string; emailStatus: string; contactIsEncrypted: boolean }>;
  appAudit(sessionId: string, action: string): Promise<number>;           // count only
  sessionIdFromPage(page: Page): Promise<string>;                          // from the widget's test hook, not from a URL
}
```
- Open Dental checks call the Open Dental API of test DB (B) directly with `od-developer-key` + `od-customer-key-testdb`, read-only (`GET` only), throttled to 1 request/s.
- App-DB checks go through `GET /internal/e2e/sessions/{session_id}/summary` on the staging `api` — an internal endpoint enabled only when `ENV in {dev, staging}` and `E2E_ENDPOINTS=1`, OIDC-authenticated as `sa-ci-tests`, returning codes and counts only (no decrypted values). The app refuses to start in prod if `E2E_ENDPOINTS` is set.

### Bot-protection bypass for tests (additive to P2-25; DECISIONS #220)
- Env `BOT_TEST_BYPASS_SECRET` (Secret Manager secret `bot-test-bypass`, dev and staging only).
- Test runs send header `X-DAI-E2E: <secret>` on `POST /v1/sessions`. If it matches (constant-time compare), `verify_bot_token` returns `allow` with reason `e2e_bypass`, the session is flagged `e2e`, and audit `security.bot_bypass_e2e` is written.
- **Prod:** startup fails if `BOT_TEST_BYPASS_SECRET` or `E2E_ENDPOINTS` is set (`config_not_allowed_in_env`); a CI test checks prod Terraform has neither.
- Real reCAPTCHA wiring stays covered by P2-25's tests (score paths with mocked assessments) and a manual staging check per release.

### Test data and cleanup
- Run ID `r<yyyymmddHHMM>-<4 random>`; patient last names `ZZTEST<runid>A`, first names from a fixed synthetic list; DOBs and phones from the reserved fake range (`+1 555 01xx`).
- Setup step (S4b) creates an appointment 3 hours ahead via the Open Dental API for a seeded `ZZTEST` patient.
- **Cleanup** (always, in `afterAll` and a separate nightly cleanup job): break every `Scheduled` appointment of `ZZTEST<runid>*` patients; callback cases flagged `e2e` are set `RESOLVED`. Patients stay (Open Dental has no patient delete); test DB (B) is reset from its snapshot weekly (P0-12).
- Addition (P4-17, DECISIONS #268): the Phase 4 suite reuses this cleanup and extends it to pending reminders of `ZZTEST` patients (`SKIPPED E2E_CLEANUP`) and e2e callback cases; it adds the `e2e-clinic-live` test clinic and console test users.
- The staging test clinic config (`config/clinics/e2e-clinic.yaml`) has fixed hours, a reason with `when_not_bookable: callback`, emergency rules `clinic_reviewed`, FAQ strings and `widget.allowed_origins` including the test page origin; callback emails go to the team test mailbox only.

### Runs and gate (additive to P1-06)
| Trigger | Where | Result |
|---|---|---|
| Nightly at 02:00 UTC (`nightly.yml` job `e2e-staging`) | staging | Report artifact; failure posts to the team channel and opens an issue |
| Release PR for prod (`promote.yml`, before the prod step) | staging, against the exact digest being promoted | Required: the latest run for that digest must be green (or the job runs it now) |
| Manual (`workflow_dispatch`) | staging | For debugging |
Not on every PR (shared test DB, Open Dental 1 request/s throttle, Gemini cost).

### Report (`e2e-report.json`, no PHI)
```json
{"run_id": "r202612010200-7QXZ", "digest": "sha256:…", "env": "staging", "started_at": "…",
 "scenarios": [{"id": "S1", "result": "pass", "attempts": 1, "duration_s": 74, "first_chunk_ms_p50": 820}],
 "first_chunk_ms_p50_all": 790, "flaky": [], "failed": []}
```
- Playwright traces, screenshots and videos are kept as CI artifacts for 14 days. They contain only synthetic data (all patients are `ZZTEST`), but the artifacts are still restricted to the repository's team.
- `first_chunk_ms_p50_all` > 1000 is reported as a warning (the gate is P2-25's latency check).

## 7. Implementation guide
1. **Local mode first:** run all scenarios against `docker compose` with `od_fake` and `FakeLlmProvider` (scripted extraction outputs) so the suite is debugged cheaply.
2. **Verification client** and the internal e2e summary endpoint (dev/staging only, startup guard for prod).
3. **Bypass** header, secret, audit, prod startup guard and the Terraform check.
4. **Data factory and cleanup**, including the setup appointment for S4b and the nightly cleanup job.
5. **Scenarios S1–S8** with the assertion rules; page objects in `frontend/e2e/pages/` (`Widget`, `ConfirmationCard`, `SlotCards`, `InfoCard`, `EmergencyBanner`).
6. **CI:** `nightly.yml` job `e2e-staging` (SA `sa-ci-tests` with read access to the two Open Dental secrets and `bot-test-bypass` in staging), `promote.yml` gate step, report upload, issue on failure.
7. **Docs:** `docs/testing/e2e-staging.md` (how to run, read the report, debug a trace, add a scenario). Notify P5-01 (reuse page objects and verify client), P3 / P4 phase tests.

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| Gemini phrases a question differently | Structural assertions still pass; only template text is exact |
| Gemini slow or a 429 | Scenario timeout 180 s; one retry; reported `flaky` |
| Open Dental test DB (B) VM down | Pre-flight check fails the run as `infra_unavailable` (not a product failure); issue labelled `infra` |
| No free slot in the test clinic's schedule | Pre-flight checks at least 6 free slots in the next 7 days; otherwise the run stops with `no_test_capacity` and the weekly reset is triggered |
| Leftover appointments from a crashed run | Nightly cleanup job breaks `ZZTEST*` appointments older than 24 h |
| S8 both bookings succeed | Fail with `double_booking` (critical); issue labelled `P0` |
| Email not `SENT` within 60 s | S5 fails; trace and case ID in the report |
| Emergency script text changed in config | S6 compares against the config file used by staging, not a hard-coded string |
| Run on a digest not deployed to staging | Gate refuses (`digest_mismatch`) |
| Bypass header sent to prod by mistake | Ignored (no secret in prod); the session goes through reCAPTCHA |

## 9. Security, HIPAA and PHI
- **No PHI:** only synthetic `ZZTEST` patients on test DB (B), which is labelled `data=synthetic-only` and never receives real data (P0-12). Staging never has the clinic's Open Dental key.
- **Secrets:** Open Dental keys and the bypass secret come from Secret Manager via `sa-ci-tests` (WIF, no JSON keys); never printed in logs or reports.
- **Test-only surfaces:** the bypass header and the e2e summary endpoint exist only in dev and staging; prod refuses to start with them; both are audited.
- **Artifacts:** traces contain synthetic data only; 14-day retention; repository-team access.

## 10. Testing
```bash
cd frontend && E2E_TARGET=local pnpm e2e:staging           # local stack with fakes
E2E_TARGET=staging pnpm e2e:staging                         # real staging (needs sa-ci-tests credentials)
pnpm e2e:staging -- --grep S8                               # one scenario
```
| # | Check | Expected |
|---|---|---|
| T1 | All 8 scenarios on the local stack | Green |
| T2 | All 8 scenarios on staging | Green (the acceptance run) |
| T3 | Prod startup with `E2E_ENDPOINTS` or `BOT_TEST_BYPASS_SECRET` set | Refuses to start |
| T4 | Wrong bypass secret | Normal reCAPTCHA path (blocked in headless) |
| T5 | Cleanup | No `Scheduled` `ZZTEST<runid>` appointments after the run |
| T6 | Report | Valid JSON; no names, phones or DOBs (PHI-pattern scan over the report) |
| T7 | Gate | Release PR blocked when the latest run for the digest failed |

## 11. Acceptance criteria
- [ ] Suite green on staging with the Open Dental test DB (all 8 scenarios, T2)
- [ ] Each scenario checks ground truth in Open Dental and the app DB, not only chat text
- [ ] S8 proves no double booking; S6 proves emergency escalation; S5 proves one case per session and email `SENT` within 60 s
- [ ] Runs nightly and gates promotion to prod (T7)
- [ ] Test-only bypass and endpoints cannot be enabled in prod (T3)
- [ ] Reports and logs contain no PHI-like values (T6)

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI (local mode on PRs that touch `frontend/e2e/`; staging nightly)
- [ ] PR reviewed (security review for the bypass and internal endpoint)
- [ ] No PHI in logs or reports
- [ ] `docs/testing/e2e-staging.md` written; additive changes to P1-06 and P2-25 merged
- [ ] P5-01, P3 and P4 phase-test owners notified

## 13. Hand-off
| Consumer | What they can rely on |
|---|---|
| P5-01 Conversation evals | Page objects, verification client, data factory, report format |
| P3 / P4 phase tests | Same harness pattern; bypass and e2e endpoint rules |
| P1-06 / release managers | `e2e-staging` gate on prod promotion |
| P6 pilot | A green Phase 2 run as an entry criterion |

## 14. Open questions
| # | Question | Recommended answer | Owner |
|---|---|---|---|
| 1 | Should the suite also run against Open Dental's public hosted test DB (A)? | No: it is shared and public; test DB (B) only. | Tech lead |
| 2 | Should nightly failures page on-call? | No; post to the team channel and open an issue. Paging is for prod alerts. | Tech lead |
| 3 | Should we add a weekly run against a fresh reset of test DB (B)? | Yes, the Sunday run starts with a reset (P0-12 procedure) to catch data-drift bugs. | QA |

## 15. References
- Plan: §8 Phase 2, §9, §11
- DECISIONS: #110, #195, #209, #210, #218, #219, #220
- Related tasks: P0-12, P1-06, P2-16, P2-18, P2-20, P2-22, P2-25, P2-27, P5-01, P5-03
- Playwright: <https://playwright.dev/docs/intro>
