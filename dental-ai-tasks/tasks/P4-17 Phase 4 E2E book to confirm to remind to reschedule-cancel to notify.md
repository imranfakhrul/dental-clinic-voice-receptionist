---
id: P4-17
title: "Phase 4 E2E: book -> confirm -> remind -> reschedule/cancel -> notify"
milestone: P4
epic: E4.2
size: M
labels: area:qa, area:messaging, type:test
depends_on: P2-30, P4-01, P4-02, P4-03, P4-04, P4-13a, P4-09, P0-12, P1-06
status: approved
---

# P4-17: Phase 4 E2E: book -> confirm -> remind -> reschedule/cancel -> notify

## 1. Summary
Extend the Phase 2 staging suite (P2-30) with an automated **Phase 4 lifecycle suite** that drives the messaging journey end to end:

1. a patient books in the real widget and agrees to WhatsApp messages;
2. a confirmation is sent;
3. the reminder is planned for start − offset and then sent after a fresh check in Open Dental;
4. the patient reschedules or cancels and gets a notice;
5. the old reminder is never sent;
6. failures, STOP replies and callbacks reach the clinic staff in the admin console.

The suite has **ten scenarios**: L1–L9 run against the test clinic `e2e-clinic` with the fake messaging provider, and **LIVE** runs against `e2e-clinic-live` with the real WhatsApp Cloud API and the team's test phone.

**Time simulation:** the suite never waits for the reminder time. A staging-only endpoint runs the **real** reminder task handler now ("run now"), with the Open Dental check and every send rule; only the "is it time yet" check is skipped. The exact timing (start − offset, DST) is already proven with a fake clock in P4-04's integration tests. This suite checks that each reminder row was planned for the right time and that the send path behaves correctly.

**When it runs** (DECISIONS #268; the user is the only developer, so there is no shared-environment contention and feedback should be immediate):
- automatically **after every promotion to staging**, against that digest;
- **manually** at any time (`workflow_dispatch`);
- as a **required gate before prod promotion** (the latest run for the digest must be green).

There is no nightly schedule.

The seed acceptance criterion is **"suite green on staging"**.

## 2. Why this matters
Phase 4's deliverable (plan §8) is confirmation and reminder messages that patients can trust. Each piece has its own unit and integration tests with fakes (P4-01 to P4-04, P4-13a). Only an end-to-end run proves that they work together on the real stack:
- Cloud Tasks queues and the Scheduler sweep;
- Redis events from the booking flow to the notification publisher;
- the Open Dental test database's real appointment states;
- the webhook path;
- the console pages that staff use.

Two pilot targets depend on this lifecycle:
- **0 reminders for cancelled appointments.** Proven by L4 (patient cancels) and L5 (staff cancel in Open Dental, which the AI never sees).
- **Staff learn about every failed message and every callback.** Proven by L6 and L9 through the console.

The LIVE scenario is the only automated proof that the Meta connection (credentials, template approval, webhook delivery) still works after a deploy.

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P4, WhatsApp, Reminders & Admin Console**.
- **P2-30 (approved), reused as-is:**
  - Playwright suite in `frontend/e2e/staging/` with page objects (`Widget`, `ConfirmationCard`, `SlotCards`, …);
  - the read-only verification client (Open Dental test DB (B) via `GET`, app DB via `GET /internal/e2e/sessions/{id}/summary`);
  - the bot-protection bypass header `X-DAI-E2E`;
  - `ZZTEST<runid>` patients, the data factory and cleanup;
  - assertion rules (exact for templates, structural for LLM text, ground truth from records);
  - one retry per scenario (`flaky`);
  - the PHI-free JSON report.
  - Internal e2e endpoints exist only when `ENV in {dev, staging}` and `E2E_ENDPOINTS=1`. They use OIDC as `sa-ci-tests`, and the app refuses to start in prod with that flag.
- **Messaging (P4-01):**
  - `MessagingProvider` with `WhatsAppCloudProvider` and `FakeProvider`, chosen by env `MESSAGING_PROVIDER`;
  - `MessageSender` policy gate;
  - table `outbound_messages`: type, template ID, status `QUEUED` / `SENDING` / `SENT` / `DELIVERED` / `READ` / `FAILED` / `SKIPPED`, reason, provider error code, `reminder_id`;
  - webhook `/v1/webhooks/messaging/whatsapp` with `X-Hub-Signature-256`;
  - STOP / START / HELP keywords;
  - `FakeProvider` can script errors and build signed status and inbound webhooks (`make_status_webhook`, `make_inbound_webhook`).
- **Consent (P4-02):** after the slot is chosen, the AI asks for the WhatsApp number and consent. The confirmation card shows the WhatsApp row with "Please check this number carefully". `consents` and `current_consents` hold the state.
- **Notices (P4-03):** `AppointmentChanged` (`booked`, `rescheduled`, `cancelled`) → `/internal/tasks/notifications`. That handler re-fetches the appointment and either sends or skips (`APPT_CHANGED`, `TOO_LATE`, `VERIFY_FAILED`, `NO_CONTACT`). Staff-made changes in Open Dental produce no notice.
- **Reminders (P4-04):**
  - `reminders` rows (`aptnum`, `scheduled_for`, `offset_minutes`, `status`);
  - hourly sweep with a 48 h enqueue horizon;
  - task `/internal/tasks/reminders` with pre-send verification:
    - appointment gone or not `Scheduled` → `SKIPPED APPT_CANCELLED`;
    - start moved → `SKIPPED APPT_MOVED` plus a new reminder row;
    - Open Dental unreachable → retry, then `FAILED VERIFY_FAILED`.
  - Nothing is sent later than 15 min before the start.
- **Console (P4-09, P4-13a):** staff login with MFA (TOTP); **Callbacks** list and detail with status, attempts and resolve; **Failed messages** list with Acknowledge.
- **WhatsApp test numbers:** **Verify** in Meta's Cloud API docs:
  - whether a test business phone number is available for the app;
  - how many recipient numbers can be registered for it;
  - whether templates can be sent from it.

  If test numbers can't send our templates, LIVE uses the staging production-like number with the team phone as the only recipient.

New glossary terms: run-now (reminder), lifecycle suite, live messaging check.

## 4. Scope
**In scope**
- Ten scenarios (§6.2) in `frontend/e2e/staging/phase4/`.
- New staging-only internal endpoints (§6.3): reminder run-now, messaging simulation, lifecycle summary.
- Per-clinic messaging provider override, allowed only outside prod (§6.4, additive to P4-01).
- Two staging test clinics: `e2e-clinic` (existing, P2-30) gets messaging enabled with `fake`; new `e2e-clinic-live` uses the real provider.
- Console test staff accounts (FRONT_DESK) with a TOTP secret in Secret Manager (staging only).
- CI wiring (§6.6): run after staging promotion, manual run, prod gate.
- Cleanup additions (reminders, outbound messages, consents, cases for `ZZTEST` patients).
- `docs/testing/e2e-phase4.md`.

**Out of scope** (and which task covers it)
- Exact reminder timing, DST and the sweep schedule → P4-04 integration tests (fake clock)
- Reminder edge cases at scale (races, retries, opt-out combinations) → P5-04 (absorbed P5-05)
- Voice booking with consent → P3 tests; this suite uses chat only
- Load tests → P5-03
- Changing P2-30's own schedule → a separate decision (P2-30 keeps its nightly job until changed)

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P2-30 (approved spec) | Suite, page objects, verification client, bypass, data factory | Build L1–L9 in local mode first (`E2E_TARGET=local`, `docker compose`, `od_fake`, `FakeLlmProvider`, `FakeProvider`) |
| P4-01 – P4-04 (approved specs) | Messaging, consent, notices, reminders | Local mode with the same internal endpoints |
| P4-09 / P4-13a (approved specs) | Console login, Callbacks, Failed messages | MSW-backed console in local mode |
| P0-12 (approved spec) | Open Dental test DB (B) | `od_fake` |
| P1-06 (approved spec) | Promote workflow | Manual `workflow_dispatch` only |
| P0-07 / P0-15 | WhatsApp sender and approved templates for LIVE | LIVE is skipped (`skipped: live_not_configured`) until the staging number and templates exist |

## 6. Interface contract

### 6.1 Test clinics (staging config)
| Clinic | `messaging.provider_override` | Reminders | Purpose |
|---|---|---|---|
| `e2e-clinic` (existing, P2-30) | `fake` | `enabled: true`, `confirmation_enabled: true`, `offset_minutes: 60` | L1–L9: deterministic, scriptable failures |
| `e2e-clinic-live` (new) | none (env provider `whatsapp_cloud`) | same | LIVE: real Meta delivery to the team test phone |

- Both clinics use `docs/compliance/messaging_policy.test.yaml` (P4-01; dev and staging only).
- `e2e-clinic-live`'s WhatsApp numbers come from secret `e2e-live-recipient` (the team test phone, E.164). It is never in the repo or the report.

### 6.2 Scenarios
All scenarios start in the patient widget with a new `ZZTEST<runid>` patient (or a seeded one where noted) and verify results in the database and Open Dental, not in chat text.

| ID | Story | Steps (abridged) | Checks |
|---|---|---|---|
| L1 | Book with consent | New patient books a cleaning ≥ 2 h ahead → WhatsApp number `+1 555 01xx` → "Yes" to messages → card shows the WhatsApp row and "Please check this number carefully" → Yes | `consents` GRANTED (source chat); `outbound_messages` confirmation `SENT` within 60 s with the confirmation template ID; one `reminders` row with `scheduled_for = start_utc − 60 min` (± 0 s) and `offset_minutes = 60` |
| L2 | Reminder sent | Simulate `delivered` for the confirmation → run-now on L1's reminder | Confirmation `DELIVERED`; reminder row `SENT`; reminder `outbound_messages` row `SENT` with the reminder template; audit `message.send`; Open Dental read happened (summary `verify_reads ≥ 1`) |
| L3 | Patient reschedules | Same patient (new session, verified) moves the appointment to another slot | Reschedule notice `SENT`; original reminder `SKIPPED` (`APPT_MOVED` or cancelled by the planner); a **new** reminder row for the new start; run-now on the old one → still no message; run-now on the new one → `SENT` |
| L4 | Patient cancels | Same patient cancels with a reason chip | Cancel notice `SENT`; run-now on the reminder → `SKIPPED APPT_CANCELLED`; **no reminder message exists for that AptNum** |
| L5 | Staff cancel in Open Dental | Book as L1, then the test sets the appointment to `Broken` directly in Open Dental (test-DB write helper, §6.5) | **No** notice; run-now → `SKIPPED APPT_CANCELLED`; no reminder message; no failed-message entry for staff (skips for cancelled appointments are not staff-actionable) |
| L6 | Delivery failure reaches staff | Book as L1 → simulate `failed` with error code `131026` for the confirmation | Message `FAILED` with the mapped reason; console (FRONT_DESK test user) **Failed messages** shows the row with the plain reason and patient name → Acknowledge → `acknowledged_at` set, audit `message.acknowledge` |
| L7 | Patient replies STOP | Book as L1 → simulate inbound "STOP" from the patient's number | Consent `REVOKED` (source `WHATSAPP_STOP`); one STOP acknowledgement sent (P4-01 auto-reply); run-now on the reminder → `SKIPPED` (no consent); no reminder message |
| L8 | No consent | Book; answer "No" to WhatsApp messages | No confirmation, no reminder row (or reminder `SKIPPED` per P4-02/P4-04 rule); the card has no WhatsApp row |
| L9 | Callback reaches staff | Reason configured `when_not_bookable: callback` → callback flow → case created | Console **Callbacks** shows the case (contact visible to FRONT_DESK) → record attempt `APPOINTMENT_MADE` → Resolve; DB status `RESOLVED`, one `callback_attempts` row, audits present |
| LIVE | Real WhatsApp | On `e2e-clinic-live`: book with the team test phone and consent | Confirmation `outbound_messages` reaches `DELIVERED` from Meta's real webhook within 120 s; no simulation used |

Order and data: L1 → L2 → L3 → L4 share one patient and appointment (a chain); L5–L9 and LIVE are independent. If a chain step fails, the later chain steps are reported `blocked`, not `failed`.

### 6.3 Staging-only internal endpoints (additive; `ENV in {dev, staging}` and `E2E_ENDPOINTS=1`; OIDC `sa-ci-tests`)
```
POST /internal/e2e/reminders/{reminder_id}/run-now
  Runs the same code path as the Cloud Tasks handler /internal/tasks/reminders, with ignore_schedule=True:
  pre-send verification, consent and policy gate, send, status updates and audit all run unchanged.
  Refuses (409 not_e2e) unless the reminder's clinic is an e2e clinic and its patient's last name starts with ZZTEST.
  200 {"status": "SENT" | "SKIPPED" | "FAILED", "reason": "APPT_CANCELLED" | null, "outbound_message_id": "uuid" | null}

POST /internal/e2e/messaging/simulate
  {"kind": "status", "outbound_message_id": "uuid", "status": "delivered" | "read" | "failed", "error_code": 131026}
  {"kind": "inbound", "clinic": "e2e-clinic", "from_session_id": "uuid", "text": "STOP"}
  Builds the payload with FakeProvider.make_status_webhook / make_inbound_webhook, signs it with the webhook secret
  in-process, and passes it through the real webhook handler (signature check included). The test runner never sees
  the secret or the phone number (inbound uses the number stored for that session's consent).
  Allowed only for clinics whose provider override is "fake". 202

GET  /internal/e2e/lifecycle/{aptnum}
  200 {"aptnum": 48213, "consent": "GRANTED" | "REVOKED" | "NONE",
       "reminders": [{"id": "uuid", "scheduled_for": "...", "offset_minutes": 60, "status": "SENT", "reason": null}],
       "messages": [{"id": "uuid", "type": "confirmation" | "reschedule_notice" | "cancel_notice" | "reminder" | "stop_ack",
                     "template_id": "...", "status": "DELIVERED", "reason": null, "error_code": null,
                     "acknowledged": false}],
       "verify_reads": 2}
  Codes, IDs and timestamps only; no phone numbers or names.
```

### 6.4 Per-clinic provider override (additive to P4-01 and P1-19)
```yaml
messaging:
  provider_override: null    # null | fake; allowed only when ENV != prod (startup check S3 extended: any clinic with an override in prod → refuse to start)
```
`get_provider(channel, clinic)` returns `FakeProvider` for clinics with `provider_override: fake`, and the env provider otherwise. On staging, `FakeProvider` sends are recorded in `outbound_messages` like real ones, with `provider_msg_id = "fake-<uuid>"` and no network call.

### 6.5 Test helpers
- **Open Dental write helper** (L5 only): `odBreakAppointment(aptNum)` calls the test DB (B) API with the test keys (`PUT` appointment status `Broken`), only for `ZZTEST` patients. It is the same kind of write P2-30's setup and cleanup already do.
- **Console login:**
  - staff user `e2e-frontdesk@<team domain>` (FRONT_DESK) on both test clinics;
  - password and TOTP seed in secrets `e2e-console-password` and `e2e-console-totp` (staging only);
  - the test computes the code with `otplib`.
  - The P1-13 lockout still applies, so one retry at most.
- **Page objects:** `ConsoleLogin`, `CallbacksPage`, `CaseDetail`, `FailedMessagesPage` in `frontend/e2e/pages/console/`.

### 6.6 Runs and gate (replaces a schedule; additive to P1-06)
| Trigger | Where | Result |
|---|---|---|
| After `promote.yml` finishes deploying a digest to staging (`workflow_run`, job `e2e-phase4`) | staging | Report artifact. A failure marks the digest red and opens an issue. LIVE failure alone → issue labelled `messaging-live`, digest stays green |
| Manual (`workflow_dispatch`, optional `scenarios=L1,L4`) | staging | Debugging |
| Prod promotion (`promote.yml`, before the prod step) | — | Required: the latest `e2e-phase4` run for this digest is green (L1–L9). If none exists, the gate runs it now |

Runtime budget: about 20–30 minutes (Open Dental test DB throttle of 1 request/s, chained scenarios). Scenarios L5–L9 run in parallel browser contexts where they don't share data.

### 6.7 Report additions (`e2e-report.json`, no PHI)
```json
{"suite": "phase4", "run_id": "r202612081530-K2QF", "digest": "sha256:…", "trigger": "staging_deploy",
 "scenarios": [{"id": "L4", "result": "pass", "attempts": 1, "duration_s": 95},
               {"id": "LIVE", "result": "pass", "delivered_after_s": 7}],
 "invariants": {"reminders_sent_for_cancelled": 0, "notices_for_staff_changes": 0}}
```
`invariants` are computed over every AptNum the run touched. Any non-zero value fails the run, whatever the scenario results.

## 7. Implementation guide
1. **Local mode first.** Add the provider override, the three internal endpoints and the lifecycle summary, then build L1–L9 against `docker compose` with `od_fake`, `FakeLlmProvider` and `FakeProvider`.
2. **Run-now:** refactor the reminder task handler so the schedule check is a parameter (`ignore_schedule`). Add one P4-04 unit test that run-now and the queued path produce identical results for the same reminder.
3. **Simulation endpoint** through the real webhook handler (signature verified), with the e2e-clinic guard.
4. **Staging config:** enable messaging on `e2e-clinic`, add `e2e-clinic-live`, secrets (`e2e-live-recipient`, `e2e-console-password`, `e2e-console-totp`), and console test users.
5. **Scenarios** L1–L9, then LIVE (skipped with `live_not_configured` until P0-07/P0-15 provide the number and templates).
6. **Invariants and report.**
7. **CI:** `workflow_run` trigger after staging deploy, manual dispatch, prod gate in `promote.yml`.
8. **Cleanup:** extend P2-30's cleanup. Break `ZZTEST` appointments, set their pending reminders to `SKIPPED` with reason `E2E_CLEANUP` (new reason, staging only), and resolve e2e cases.
9. **Docs:** `docs/testing/e2e-phase4.md` (how to run one scenario, read the lifecycle summary, set up the team test phone for LIVE).

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| Confirmation not `SENT` within 60 s | L1 fails; the report includes the outbound message status and reason |
| Run-now called on a reminder of a non-e2e clinic | 409 `not_e2e`; nothing runs |
| Run-now when the appointment is less than 15 min away | Same result as production (`SKIPPED` / `FAILED` per P4-04); the setup books ≥ 2 h ahead so this doesn't happen normally |
| Open Dental test DB unreachable | Pre-flight fails the run as `infra_unavailable` (P2-30 rule), not a product failure |
| Simulated webhook signature check fails | Product bug: the run fails (the endpoint uses the real handler) |
| Meta test number unavailable or template not approved | LIVE `skipped: live_not_configured`; issue labelled `messaging-live` |
| LIVE: delivered webhook doesn't arrive in 120 s | LIVE fails; digest stays green; issue opened |
| Console login hits lockout | Scenario fails with `console_locked`; the doc explains how to unlock the test user |
| A reminder message exists for a cancelled AptNum | Invariant violation; run fails with `reminder_for_cancelled` (critical); issue labelled `P0` |
| Chain step L3 fails | L4 reported `blocked`; the rest continue |
| Run interrupted | Cleanup runs in `afterAll`; leftovers are swept by the next run's pre-clean of `ZZTEST` appointments older than 2 h |

## 9. Security, HIPAA and PHI
- **No real patient data.** All patients are synthetic `ZZTEST` records in test DB (B). Phone numbers are from the reserved fake range, except LIVE's team test phone, which is a team-owned device.
- **Internal endpoints** exist only in dev and staging behind `E2E_ENDPOINTS=1` and OIDC (`sa-ci-tests`). They are guarded to e2e clinics and `ZZTEST` patients and return codes and IDs only. Prod refuses to start with the flag or with any `provider_override` (startup checks).
- **Secrets** (team test phone, console password, TOTP seed) are in Secret Manager in staging only. They are never written to logs, reports or traces; Playwright masks the password and TOTP fields.
- **LIVE messages** use the approved templates and the test messaging policy. Content is synthetic.
- **Reports and traces:** synthetic data only, CI artifacts for 14 days, restricted to the repository.
- **Audit:** the endpoints use the same code paths, so the usual audits (`message.send`, `consent.revoke`, `callback.status_change`, …) are written for test actions, marked with `e2e` session flags.

## 10. Testing
This task *is* tests. Its own checks:

| # | Check | Expected |
|---|---|---|
| T1 | Local mode: all L1–L9 pass on `docker compose` | Green |
| T2 | P4-04 unit test: run-now and queued handler give identical results (sent, moved, cancelled, verify failed) | Pass |
| T3 | Startup in `ENV=prod` with `E2E_ENDPOINTS=1` or a clinic `provider_override` | Refuses to start |
| T4 | Run-now on a non-e2e clinic reminder | 409 |
| T5 | Simulation on `e2e-clinic-live` (real provider) | 403/409; nothing posted |
| T6 | Lifecycle summary JSON contains no phone or name keys (schema check) | Pass |
| T7 | Invariant check: inject a fake "reminder for cancelled" row in local mode | Run fails with `reminder_for_cancelled` |
| T8 | Staging: full suite after a deploy | Green; report uploaded |

```bash
cd frontend && E2E_TARGET=local pnpm e2e:phase4
cd frontend && E2E_TARGET=staging pnpm e2e:phase4 -- --scenarios=L1,L2
cd backend && pytest tests/unit/reminders/test_run_now_parity.py tests/unit/startup -q
```

## 11. Acceptance criteria
- [ ] The Phase 4 suite (L1–L9) is green on staging (seed criterion) (T8)
- [ ] It runs automatically after every staging deploy and on demand; the prod promotion requires a green run for the same digest
- [ ] No reminder message is sent for a cancelled appointment, whether the patient or the staff cancelled (L4, L5, invariant)
- [ ] Staff-made changes in Open Dental produce no patient notice (L5)
- [ ] Reschedule produces a notice and moves the reminder; the old reminder never sends (L3)
- [ ] Failed messages and callback cases are visible and actionable in the console (L6, L9)
- [ ] STOP and declined consent stop all messages (L7, L8)
- [ ] LIVE proves real WhatsApp delivery, or is reported as skipped/failed without blocking the release
- [ ] Internal test endpoints and provider overrides cannot run in prod (T3)
- [ ] Reports contain no PHI (T6)

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI
- [ ] PR reviewed
- [ ] No PHI in logs
- [ ] Docs / README updated (`docs/testing/e2e-phase4.md`)
- [ ] Additive edits merged: P4-01 (`provider_override`, startup check), P4-04 (`ignore_schedule` parameter, run-now parity test), P1-06 (post-deploy trigger and prod gate), P2-30 (shared cleanup)

## 13. Hand-off
| Consumer | What it can rely on |
|---|---|
| P5-04 Scheduling and reminder edge cases | Run-now and simulation endpoints, lifecycle summary, `e2e-clinic` |
| P5-07 UAT | Console test users and the scenario list as a UAT script basis |
| P6-01 Go-live checklist | "Phase 4 suite green for the release digest" and "LIVE green within the last 7 days" |
| P6 pilot | The invariants as ongoing checks on staging after every deploy |

## 14. Open questions
| Question | Owner | Needed by |
|---|---|---|
| Can Meta's test business number send our approved templates to a registered team phone, and how many recipients can it have? | Developer (Verify, with P0-07) | Step 5 |
| Should P2-30 also switch from nightly to "after each staging deploy" for the same reason (single developer)? Proposed: yes, as a separate decision on P2-30 | User | Before P5 |

## 15. References
- Plan §8 (Phase 4), §4.7 (messages), §4.9 (callbacks), §9 (testing)
- DECISIONS #218, #219, #220, #252, #253, #256, #258, #260, #266, #268
- Related tasks: P0-07, P0-12, P0-15, P1-06, P1-13, P1-19, P2-30, P4-01, P4-02, P4-03, P4-04, P4-09, P4-13a, P5-04, P5-07, P6-01
