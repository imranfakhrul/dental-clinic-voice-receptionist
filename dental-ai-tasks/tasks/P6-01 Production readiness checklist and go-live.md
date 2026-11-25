---
id: P6-01
title: Production readiness checklist and go-live
milestone: P6
epic: E6.1
size: M
labels: area:infra, area:admin, type:chore
depends_on: P5-14, P5-07, P5-03, P5-04, P5-08, P5-11, P5-12, P1-06, P1-19, P4-17
status: approved
---

# P6-01: Production readiness checklist and go-live

## 1. Summary
Prepare production for the pilot clinic and switch it on safely. The work has eight parts:
1. Onboard the clinic in prod: secrets, config, Open Dental checks, staff accounts, the WhatsApp number, the embed.
2. Add **pilot flags**, including a per-channel **kill switch**.
3. Run 2–3 days of **staff-only** use in prod.
4. Test rollback.
5. Go through the **production readiness checklist**.
6. Hold a go/no-go meeting with four people.
7. Set `PHI_ENABLED=true`.
8. Hand over to the soft launch (P6-04).

Bookings are made normally and reviewed by staff afterwards: John gets his confirmation at once, and Sarah reviews AI bookings in the console within one business day.

Done means:
- the checklist is complete and signed;
- rollback was tested in prod;
- the kill switch was tested in prod;
- the widget works for staff in prod.

## 2. Why this matters
Plan §8 Phase 6 starts with "prod deploy, alerts, on-call, feature flags (limited hours, new bookings flagged for review)". All earlier work was proven on staging with synthetic data. This task is where real PHI first enters the system, so it is the riskiest moment of the project.

Several approved specs left onboarding items here:
- P1-06: `PHI_ENABLED` and the PHI gate;
- P1-15: minimum Open Dental version 22.4.10 and a running eConnector;
- P1-16: the AI marker text, the staff guide and the "Confirmed" status;
- P1-19 / P1-20: the config import, lead times and blockouts;
- P1-13: the first ADMIN account and unique staff accounts;
- P0-15: the WhatsApp registration;
- P2-01: the "not understood" limit;
- P4-13: the test email to every admin address;
- P4-17 / P5-04: the release gates.

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P6, Pilot Launch & Iteration**.
- **`PHI_ENABLED` (P1-06):** a repository variable. When it is `true`, prod promotion first runs the PHI gate (`check_vendors.py --gate` must print `GATE OPEN`).
- **Kill switch:** a flag that turns a channel off at once without a deploy. The widget then shows a short message with the clinic's phone number.
- **Staff-only period:** the widget is live in prod but reachable only on an unlisted URL. Clinic staff use it for themselves or for a clinic-created test patient, with real Open Dental.
- **AI-booked review (P4-13a):** the console list of appointments the AI made, with `reviewed_at` / `reviewed_by`.
- **What already exists (approved):**
  - `promote.yml` / `rollback.yml` and the prod approvers (P1-06);
  - the config CLI `validate` / `import` (P1-19);
  - `create_admin.py` (P1-13);
  - the AI marker (DECISIONS #134);
  - the console settings (P4-11, P4-13);
  - `notification_targets.yaml` (alerts by email, P1-07 / DECISIONS #117);
  - the runbooks and alert-watcher rotation (P5-12);
  - the gates from P5-01, P5-03, P5-04, P5-08, P5-11 and P5-14.

## 4. Scope
**In scope**
- Pilot flags and the kill switch (backend, widget, console toggle, audit), and the AI-hours window.
- The prod onboarding runbook and its execution for the pilot clinic.
- The readiness checklist (`docs/golive/checklist.md`), the go/no-go meeting and its record.
- Prod rollback test, kill-switch test, restore drill on prod before PHI (P5-12), staff-only period.
- Staff guide (console, AI marker, review list, callbacks) and short training for clinic staff.

**Out of scope** (and which task covers it)
- KPI dashboard → P6-02
- Public launch stages, weekly reviews, tuning → P6-04
- The go/no-go for **wider rollout** → P6-07 (this task is the go/no-go for the **pilot**)

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P5-14 signed checklist | Compliance gate | Build flags and onboarding runbook first |
| P5-07 | UAT sign-off, approved emergency rules | Same |
| P5-03 | Prod sizing values, quota | Use P1-02 placeholders until the PRs land |
| Clinic | Open Dental customer key (after BAA), staff list, website access | Request 2 weeks ahead |

## 6. Interface contract

### Pilot flags (DECISIONS #280)
Clinic config section `pilot` (P1-19, console-editable for the listed roles):
```yaml
pilot:
  chat_enabled: true
  voice_enabled: false          # P6-04 stages turn it on
  reminders_enabled: false      # P6-04 stages turn it on (in addition to reminders.enabled)
  ai_hours: null                # null = clinic hours; else a narrower window like hours: {mon: [["09:00","16:00"]], ...}
  unlisted_only: true           # staff-only period: the widget renders only with ?k=<unlisted_key>
  closed_message_key: pilot_closed   # template: "Our online assistant is unavailable right now. Please call us at {clinic_phone}."
```
| Flag change | Who | How many people |
|---|---|---|
| Any `*_enabled` → `false` (switch **off**) | ADMIN (clinic) or on-call engineer (`pilot:kill` permission) | **One** (fast) |
| Any `*_enabled` → `true` (switch **on**) | Tech lead **and** clinic ADMIN | **Two**: a pending change that a second person approves in the console (`config_change_requests` kind `pilot_enable`) |
| `ai_hours`, `unlisted_only` | ADMIN + tech lead | Two (same mechanism) |

New permission `PILOT_KILL = "pilot:kill"` (P1-13 additive) for ADMIN and the ops role. Every change writes audit `pilot.flag_changed {flag, from, to, actor, approver}`. The change takes effect within 10 s: the config cache is invalidated through P1-19's version bump. Sessions already in progress get the closed message at their next turn. A booking that is mid-confirm finishes first, so a half-done write is never left behind.

**Widget behaviour when a channel is off:** chat off → the widget shows the closed message and the clinic phone; voice off → no mic button (text still works); reminders off → the planner stops creating reminders (existing `PENDING` ones are `CANCELLED` with reason `PILOT_DISABLED`); outside `ai_hours` → the closed message.

**Console:** `/admin/settings/pilot` shows the current flags. Each `*_enabled` row has an **Off** button (one click + confirm) and, when off, a "Request turn on" button.

### Booking review (DECISIONS #280)
- Bookings are normal. The patient gets a confirmation at once (no "tentative" state).
- The P4-13a AI-booked list is the review tool. Target: every AI booking reviewed within 1 business day.
- A console badge counts unreviewed AI bookings older than 1 business day. A daily 09:00 email to the callback admins lists the count (no PHI). P6-02 shows the review lag as a KPI.

### Onboarding runbook (`docs/golive/onboarding.md`)
1. **BAA and gate:** the clinic BAA is executed; `check_vendors.py --gate` → `GATE OPEN`.
2. **Open Dental:**
   - the customer key is enabled by the clinic after the BAA;
   - its first version is stored in `od-customer-key-<slug>` by `key-admin` through PAM (P1-05);
   - the version is ≥ 22.4.10 and the eConnector is running (P1-15 health check);
   - the `clinic_num` and version are set in the config.
3. **Config:**
   - `validate` and then `import` the confirmed pilot config from P5-07's policy checklist, including lead times, blockouts, the AI window and the "not understood" limit;
   - the emergency rules must be the `approved` version.
4. **Accounts:**
   - the first ADMIN is created with `create_admin.py` (prod, by ops through PAM);
   - one account per staff member, invited from the console with MFA;
   - no shared logins.
5. **Messaging:** the WhatsApp number is registered and the templates are approved (P0-15); the LIVE check is green within 7 days (P4-17).
6. **Email:** a test email is sent to and received by every callback admin address (P4-13).
7. **Embed:** `embed.js` goes on the clinic site with `allow="microphone"`; `allowed_origins` is set; the clinic's Permissions-Policy is checked.
8. **Alerts:** prod alert emails go to the team; the alert-watcher rotation is staffed (P5-12).
9. **Sizing:** the P5-03 values are applied; the Vertex AI quota is confirmed.

### Readiness checklist (`docs/golive/checklist.md`)
| Area | Item | Evidence |
|---|---|---|
| Compliance | P5-14 checklist signed | Link |
| Compliance | `PHI_ENABLED=true` set only after the go decision | Repo variable history |
| Safety | Emergency rules `approved`, signed PDF hash matches | P5-07 |
| Quality | Full eval run green ≤ 72 h for the release (P5-01) | Run link |
| Quality | Voice quality and load reports green (P5-03) | Report |
| Quality | S2 + S5 green for the digest (P5-04); Phase 4 suite green, LIVE ≤ 7 days (P4-17) | Run links |
| Security | Canary scan clean; 0 open Critical/High (P5-08); pentest retest letter (P5-11) | Reports |
| Operations | Runbooks linked; watcher rotation staffed; restore drill on prod done (P5-12) | Links |
| Operations | Rollback tested in prod (below) | Record |
| Operations | Kill switch tested in prod (below) | Record |
| Clinic | UAT sign-off; staff trained; staff guide delivered; AI marker text confirmed | P5-07, attendance |
| Clinic | Onboarding runbook steps 1–9 done | Record |
| Pilot | Staff-only period done with no Blocker open | Notes |

### Rollback and kill-switch tests (in prod, before PHI)
- **Rollback:** deploy the release candidate, then run `rollback.yml` to the previous revision, verify the health checks and a staff-only chat, then roll forward again. Time each step. Migrations must be expand/contract (P1-06), so rollback never needs a schema downgrade.
- **Kill switch:** an ADMIN turns chat off; the widget shows the closed message within 10 s; the audit row exists; turning it back on needs the second approver.

### Staff-only period (DECISIONS #280)
- 2–3 clinic days with `unlisted_only: true`.
- Staff book, reschedule and cancel real appointments for a clinic-created test patient (for example "ZZPilot Test", created by the clinic in Open Dental) or for themselves, then cancel them.
- Watch: AI markers in Open Dental, confirmations on the staff's own WhatsApp, callback emails, console lists.
- Issues are triaged with the UAT severity rules (P5-07).

### Go/no-go (pilot)
Meeting with the **tech lead, compliance advisor, sponsor and office manager**. All four must say "go", and any one can block. The record goes in `docs/golive/decision-<date>.md` with the checklist link and any conditions. After "go": set `PHI_ENABLED=true` (repo variable change by a prod approver), set `unlisted_only: false` (two-person), and hand over to P6-04.

## 7. Implementation guide
1. Add the `pilot` section to P1-19's model (additive), the `PILOT_KILL` permission (P1-13 additive), the two-person enable flow through `config_change_requests` (P4-11 additive kind `pilot_enable`), the audit action, the widget closed state and the reminder planner check.
2. Add the console page `/admin/settings/pilot` (P4-09 NAV additive).
3. Write the onboarding runbook, the checklist, the staff guide (`docs/golive/staff-guide.md`: console tour, the AI marker, the review list, callbacks, the kill switch, who to call) and a 45-minute training session.
4. Run onboarding in prod (steps 1–9) with PHI still disabled for public traffic.
5. Restore drill on prod (P5-12), rollback test, kill-switch test.
6. Staff-only period, then the go/no-go meeting.
7. Go: set the flags, then notify P6-02 and P6-04.

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| Kill switch pressed during a booking confirmation | The confirmation finishes; the next turn gets the closed message |
| Second approver unavailable to turn a channel back on | It stays off; that is the intended safe default |
| Clinic Open Dental below 22.4.10 | Go-live blocked; clinic upgrades first |
| WhatsApp template rejected late | Go-live allowed with `reminders_enabled: false`; P6-04 stage B waits |
| Staff-only booking left in Open Dental by mistake | Staff guide: cancel test appointments the same day; the review list shows them |
| Any go/no-go participant says no | No go; the record lists what must change; new meeting |
| `PHI_ENABLED=true` set by mistake before the decision | Revert at once; incident log entry (P5-12); no public traffic because `unlisted_only` is still true |

## 9. Security, HIPAA and PHI
- From the staff-only period on, real PHI flows (staff's own data or the clinic's test patient). Every BAA must be in place before step 1 of the staff-only period, and the gate enforces it.
- Secrets for the clinic are created through PAM by `key-admin`; no person keeps a copy.
- Kill-switch and flag changes are audited. The closed message contains no PHI.
- Staff accounts are personal, with MFA; the P5-14 access review includes them.

## 10. Testing
```bash
pytest backend/tests/unit/pilot backend/tests/integration/pilot -q
cd frontend && pnpm test -- pilot && pnpm e2e -- --grep pilot-flags
```
| # | Case | Expected |
|---|---|---|
| T1 | ADMIN switches chat off | Closed message within 10 s; audit row |
| T2 | ADMIN tries to switch chat on alone | Pending request; on only after the tech lead approves |
| T3 | Outside `ai_hours` | Closed message; console unaffected |
| T4 | `reminders_enabled` off | New reminders not created; pending ones cancelled with `PILOT_DISABLED` |
| T5 | `unlisted_only` true without the key | Widget refuses to render (generic message) |
| T6 | Mid-confirm kill | Booking completes; next turn closed |
| T7 | Prod rollback test | Previous revision serving; health green; roll forward OK |
| T8 | FRONT_DESK tries the kill switch | 403 |

## 11. Acceptance criteria
- [ ] Pilot flags and the kill switch work as specified, including the two-person turn-on (T1–T6, T8)
- [ ] Onboarding runbook steps 1–9 completed for the pilot clinic
- [ ] Rollback and the kill switch tested in prod and recorded (T7)
- [ ] Staff-only period completed with no open Blocker
- [ ] Readiness checklist complete; go/no-go record signed by all four participants
- [ ] `PHI_ENABLED=true` only after the go decision

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI
- [ ] PR reviewed (HIPAA review for the flag and widget changes)
- [ ] No PHI in logs (canary scan for the release)
- [ ] Onboarding runbook, checklist, staff guide written; P6-02 and P6-04 notified

## 13. Hand-off
| Consumer | What they can rely on |
|---|---|
| P6-04 Soft launch | Flags per channel, `ai_hours`, the kill switch and its runbook, trained staff |
| P6-02 KPIs | Review lag source (P4-13a), flag history for stage dates |
| P5-12 Runbooks | `kill-switch.md` matches this behaviour |
| P6-07 Report | Go-live record and checklist |

## 14. Open questions
| # | Question | Recommended answer | Owner |
|---|---|---|---|
| 1 | Should `ai_hours` start narrower than clinic hours? | Start with clinic hours (staff are there to handle callbacks); narrow only if the alert watcher can't cover. | Office manager + tech lead |

## 15. References
- Plan: §8 Phase 6, §15
- DECISIONS: #25, #117, #134, #139, #280
- Related tasks: P0-15, P1-05, P1-06, P1-13, P1-15, P1-16, P1-19, P1-20, P2-01, P4-09, P4-11, P4-13, P4-13a, P4-17, P5-01, P5-03, P5-04, P5-07, P5-08, P5-11, P5-12, P5-14, P6-02, P6-04
