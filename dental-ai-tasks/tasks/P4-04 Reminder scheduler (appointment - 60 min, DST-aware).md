---
id: P4-04
title: Reminder scheduler (appointment minus offset, DST-aware) with pre-send verification
milestone: P4
epic: E4.1
size: L
labels: area:messaging, area:open-dental, type:feature, phi
depends_on: P4-03, P4-01, P4-02, P1-02, P1-03, P1-13, P1-16, P1-19
status: approved
---

# P4-04: Reminder scheduler (appointment minus offset, DST-aware) with pre-send verification

> Consolidated task (#53). It absorbs P4-05 "Pre-send verification (re-fetch appointment)" (see `tasks/_CONSOLIDATION.md`).

## 1. Summary
Send each AI-booked patient a WhatsApp reminder a configurable number of minutes before the appointment (default 60). The send time is computed correctly across daylight-saving changes. Just before sending, the appointment is re-read from Open Dental and the reminder goes out **only** if the appointment still exists at the same time.

This task builds four parts:

1. **`ReminderPlannerImpl`** (implements P4-03's `ReminderPlanner`):
   - `booked` creates a reminder row;
   - `rescheduled` cancels the old row and creates a new one;
   - `cancelled` cancels the row.
2. **Hourly sweep:** enqueues reminders due in the next 48 hours. Cloud Tasks can't schedule more than 30 days ahead, and bookings can be up to 365 days out.
3. **Reminder task handler with pre-send verification:**
   - the appointment is gone or no longer scheduled → skip (`APPT_CANCELLED`);
   - the time changed → skip (`APPT_MOVED`) and create a new reminder for the new time;
   - Open Dental can't be reached → retry, then `FAILED` (`VERIFY_FAILED`) and show it in the console;
   - only a verified, matching appointment is sent, through P4-01's `MessageSender`.
4. **Per-clinic offset** (`reminders.offset_minutes`, 30–240). Each row stores the offset it was created with, and an offset change applies only to new bookings.

The task is done when:
- the DST transition tests pass;
- the offset is configurable per clinic;
- tests show 0 reminders for cancelled appointments.

## 2. Why this matters
Plan §4.7: "Schedule a job at `appointment_time − 60 min` (clinic time zone, DST-aware). Before sending: re-fetch the appointment from Open Dental; if it's cancelled, moved or the patient opted out, cancel the job (and reschedule it if moved)."

One of the pilot targets is **0 reminders for cancelled appointments**. A reminder for a visit that no longer exists confuses patients and tells them the clinic's system is unreliable. A reminder at the wrong hour on a DST weekend is just as bad.

Staff also change appointments directly in Open Dental, which our system doesn't see (no polling; DECISIONS #258). The pre-send check is what keeps reminders correct in that case too.

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P4, WhatsApp, Reminders & Admin Console**.
- **`reminders` table (P1-03):**
  - columns `id`, `clinic_id`, `aptnum`, `patnum`, `kind` (`BEFORE_1H`), `scheduled_for` (UTC send time), `status`, `skip_reason`, `task_name`, `attempts`, `provider_msg_id`, `last_error_code`, `created_at`, `updated_at`;
  - status values `PENDING`, `ENQUEUED`, `SENT`, `SKIPPED`, `FAILED`, `CANCELLED`;
  - skip codes `NO_CONSENT`, `APPT_CANCELLED`, `APPT_MOVED`, `TOO_LATE`;
  - UNIQUE (`clinic_id`, `aptnum`, `kind`, `scheduled_for`), and an index (`status`, `scheduled_for`) for the sweep.

  This task adds the column `offset_minutes` and the skip code `VERIFY_FAILED` (§6.1).
- **Cloud Tasks and Scheduler (P1-02, DECISIONS #92):**
  - the `reminders` queue allows 2 dispatches/s, 5 concurrent, 5 attempts, backoff 30–600 s, and gives up after 3600 s;
  - Cloud Tasks can't schedule more than 30 days ahead (`enqueue()` raises `ScheduleTooFarError` beyond 29 days);
  - the `reminder-sweep` Scheduler job calls `POST /internal/jobs/reminder-sweep` every hour (`0 * * * *`);
  - task IDs are deterministic, so a second create with the same ID counts as success.
- **Internal auth (P1-13):** `/internal/*` accepts only OIDC tokens from `sa-scheduler` and `sa-tasks-invoker` (`require_internal_caller`).
- **Time zones and DST:** the clinic's IANA zone is `clinics.timezone` (e.g. `America/New_York`). We store UTC.
  - **Proposed:** send time = `appointment start (UTC) − offset`, computed in UTC. That is always exactly `offset` real minutes before the visit, even on DST days.
  - The time shown in the message (in `minimal_phi` mode) is converted to clinic local time with `zoneinfo`, so it reads correctly after the change.
  - Example: a 9:00 AM visit on Sunday 2027-03-14 in New York (clocks went forward at 2:00 AM) is 13:00 UTC, so the reminder goes at 12:00 UTC, which is 8:00 AM EDT.
- **Open Dental reads (P1-16):** `OpenDentalAppointments.get(ctx, apt_num, priority=Priority.BACKGROUND)` returns `Appointment` (`status`, `start_utc`, `pat_num`, …) or `None` on 404. Errors: `OpenDentalUnavailable`, timeouts, rate limits. The P1-15 pacer keeps background reads under the clinic's rate budget (1 request/s per clinic).
- **Event source (P4-03):** `ReminderPlanner.on_appointment_changed(event)` is called once per confirmed AI change. This task adds `start_utc` to the in-memory event (never to task payloads).
- **Sending (P4-01):** `MessageSender.send(MessageRequest(message_type=REMINDER, reminder_id=…, dedupe_key=f"reminder:{id}"), attempt, max_attempts)` applies the policy, consent and retry rules. `record()` writes a skip without sending (P4-03 addition).
- **Clinic config (P1-19):** `reminders.enabled`, `reminders.channel`, `reminders.confirmation_enabled`, `reminders.offset_minutes`.

New glossary terms: reminder sweep, pre-send verification, send-time offset.

## 4. Scope
**In scope**
- Migration: `reminders.offset_minutes` and the skip code `VERIFY_FAILED` (additive to P1-03).
- `ReminderPlannerImpl`: create, move and cancel rows; enqueue immediately when the send time is within 48 h.
- `POST /internal/jobs/reminder-sweep`: enqueue due rows; mark overdue never-enqueued rows `TOO_LATE`.
- `POST /internal/tasks/reminders`: pre-send verification and send.
- Re-planning when Open Dental shows a later time (staff moved the appointment).
- Config validation for `reminders.offset_minutes` (30–240), added to P1-19.
- Metrics, alerts A-R1 and A-R2, audit through P4-01.
- DST test suite.

**Out of scope** (and which task covers it)
- Reminders for appointments created by staff directly in Open Dental → not in the MVP (we don't know about them; DECISIONS #258, #260)
- Moving existing reminders when the clinic changes the offset → not done; new offset applies to new bookings (DECISIONS #260)
- Confirmation, reschedule and cancel notices → P4-03
- Sending, retries, delivery tracking, STOP → P4-01
- The console screen for the offset → P4-13 (shows "Applies to appointments booked from now on.")
- More reminder kinds (e.g. 24 h before) → post-MVP (`kind` already allows more)

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P4-03 (approved spec) | `ReminderPlanner` protocol, `AppointmentChanged` | Call the planner directly in tests with events. |
| P4-01 / P4-02 (approved specs) | `MessageSender`, `ConsentService`, `FakeProvider` | Use the fakes and the test policy. |
| P1-02 (approved spec) | `reminders` queue, Scheduler job, `enqueue()` | Fake `TasksClient` that records `(task_id, schedule_time)`. |
| P1-03 (approved spec) | `reminders` table | Add this task's migration. |
| P1-16 (approved spec) | `OpenDentalAppointments.get()` | `FakeOpenDental` with scripted appointments and errors. |
| P1-19 (approved spec) | `reminders.*` config | Config fixtures; add the validation rule here. |
| P1-13 (approved spec) | `require_internal_caller` | Tests override the dependency. |

## 6. Interface contract

### 6.1 DB changes (additive to P1-03)
```sql
ALTER TABLE app.reminders ADD COLUMN offset_minutes integer NOT NULL DEFAULT 60
    CHECK (offset_minutes BETWEEN 30 AND 240);
-- skip_reason codes: NO_CONSENT, APPT_CANCELLED, APPT_MOVED, TOO_LATE, + VERIFY_FAILED, REMINDERS_DISABLED
```
- `offset_minutes` is the offset in force **when the row was created**. The appointment start the reminder expects is `scheduled_for + offset_minutes`.
- `skip_reason` is set for `SKIPPED`, `CANCELLED` and `FAILED` rows.

### 6.2 Event field (additive to P2-18 / P4-03)
`AppointmentChanged.start_utc: datetime | None` is the appointment start after the change: set for `booked` and `rescheduled`, `None` for `cancelled`. It is an in-memory field only. `NotificationPublisher` never puts it into a task payload.

### 6.3 Planner (`backend/app/domain/reminders/planner.py`)
```python
MIN_LEAD = timedelta(minutes=5)          # don't create a reminder that would go out in < 5 min
ENQUEUE_HORIZON = timedelta(hours=48)

class ReminderPlannerImpl:               # implements P4-03 ReminderPlanner
    async def on_appointment_changed(self, event: AppointmentChanged) -> None:
        match event.kind:
            case "booked":      await self.plan(event.clinic_id, event.apt_num, event.pat_num, event.start_utc)
            case "rescheduled": await self.cancel_open(event.clinic_id, event.apt_num, "APPT_MOVED")
                                await self.plan(event.clinic_id, event.apt_num, event.pat_num, event.start_utc)
            case "cancelled":   await self.cancel_open(event.clinic_id, event.apt_num, "APPT_CANCELLED")

    async def plan(self, clinic_id, apt_num, pat_num, start_utc: datetime) -> Reminder | None:
        cfg = await clinic_config.active(clinic_id)
        if not cfg.reminders.enabled:
            return None                                   # nothing created; no row
        offset = cfg.reminders.offset_minutes
        send_at = start_utc - timedelta(minutes=offset)   # UTC arithmetic: exactly `offset` real minutes before
        if send_at < utcnow() + MIN_LEAD:
            await self.repo.insert_skipped(clinic_id, apt_num, pat_num, send_at, offset, "TOO_LATE")
            return None
        row = await self.repo.insert_pending(clinic_id, apt_num, pat_num, kind="BEFORE_1H",
                                             scheduled_for=send_at, offset_minutes=offset)   # ON CONFLICT DO NOTHING
        if row and send_at <= utcnow() + ENQUEUE_HORIZON:
            await self.enqueue(row)
        return row

    async def cancel_open(self, clinic_id, apt_num, reason: str) -> int:
        """PENDING/ENQUEUED rows for this AptNum → CANCELLED with skip_reason; delete their Cloud Tasks (best effort)."""

    async def enqueue(self, row: Reminder) -> None:
        name = await enqueue(queue="reminders", path="/internal/tasks/reminders",
                             payload={"clinic_id": str(row.clinic_id), "reminder_id": str(row.id)},
                             task_id=f"rem-{row.aptnum}-{row.scheduled_for:%Y%m%d%H%M}",
                             schedule_time=row.scheduled_for)
        await self.repo.mark_enqueued(row.id, task_name=name)     # PENDING → ENQUEUED
```
- **Idempotency:** the unique key (`clinic_id`, `aptnum`, `kind`, `scheduled_for`) plus `ON CONFLICT DO NOTHING` means a repeated event creates nothing new. The deterministic `task_id` means a repeated enqueue is harmless.
- `ConsentService.revoke()` (P4-02) already cancels open rows with `NO_CONSENT`. The planner still creates rows for patients without consent: the pre-send check skips them, which keeps a visible record. **Proposed:** creating the row doesn't depend on consent, because consent can be granted later (e.g. by staff).

### 6.4 Sweep (`POST /internal/jobs/reminder-sweep`, hourly)
```python
async def sweep(now: datetime) -> SweepResult:
    # 1. Overdue, never enqueued (e.g. sweep was down): PENDING and scheduled_for < now - 10 min
    #    → SKIPPED TOO_LATE (one UPDATE … RETURNING id; audit message.skip per row via MessageSender.record()).
    # 2. Due soon: PENDING and scheduled_for <= now + 48 h, oldest first, LIMIT 500 per run
    #    → enqueue() each (deterministic task IDs make a re-run safe).
    # 3. Return counts; log `reminder.sweep` with counts only.
```
- Auth: `require_internal_caller` (`sa-scheduler`). Response `200 {"enqueued": n, "too_late": m}`.
- It runs across all clinics. Rows of a clinic with `reminders.enabled=false` are set to `SKIPPED REMINDERS_DISABLED` (step 1b).
- **Concurrency:** two sweeps running at once are harmless (deterministic task IDs). **Proposed:** a Redis lock `lock:reminder-sweep` (TTL 300 s) avoids double work anyway.

### 6.5 Reminder task (`POST /internal/tasks/reminders`): pre-send verification

> **Addition (P4-17, DECISIONS #268):** the handler takes `ignore_schedule: bool = False`. Only the staging-only endpoint `POST /internal/e2e/reminders/{id}/run-now` (P4-17 §6.3) passes `True`; every other step (verification, consent, policy gate, the 15-minute cut-off, audit) is unchanged. A parity unit test checks run-now and the queued path give the same result. Staging cleanup may set pending `ZZTEST` reminders to `SKIPPED` with reason `E2E_CLEANUP` (never in prod).

```
Body:    {"clinic_id": "…", "reminder_id": "…"}            (IDs only)
Headers: X-CloudTasks-TaskRetryCount (attempt = value + 1; Verify), OIDC sa-tasks-invoker
200  finished (sent, skipped, cancelled, failed)
503  retry (Open Dental unavailable or MessagingTransientError) while still inside the send window
```
Constants (Proposed): `LATEST_SEND_BEFORE_START = 15 min`, `MAX_ATTEMPTS = 5` (queue setting).

`ReminderService.handle(reminder_id, attempt)`:

| # | Check | Result |
|---|---|---|
| 1 | Load the row `FOR UPDATE`. Status must be `ENQUEUED` (or `PENDING` if the planner enqueued it but crashed before marking it) | Anything else (`CANCELLED`, `SENT`, …) → 200, no action |
| 2 | `expected_start = scheduled_for + offset_minutes`; `now >= expected_start - 15 min` | `SKIPPED TOO_LATE` → 200 |
| 3 | Clinic `reminders.enabled` and `policy.channel_allowed("whatsapp")` | `SKIPPED REMINDERS_DISABLED` (or `CHANNEL_NOT_ALLOWED` via `record()`) → 200 |
| 4 | Contact and consent: `ConsentService.address_for(...)` and `current(...).granted` | `SKIPPED NO_CONSENT` → 200 (Open Dental not called) |
| 5 | `appt = OpenDentalAppointments.get(ctx, aptnum, priority=BACKGROUND)` | Unavailable / timeout / rate limit: if `now + next_backoff < expected_start - 15 min` and `attempt < 5` → 503; else `FAILED VERIFY_FAILED` → 200 + alert A-R1 |
| 6 | `appt is None` or `appt.status != Scheduled` or `appt.pat_num != patnum` | `SKIPPED APPT_CANCELLED`; `appointment_refs.status_cache` updated → 200 |
| 7 | `appt.start_utc != expected_start` (moved; compare to the minute) | `SKIPPED APPT_MOVED`; then `planner.plan(clinic, aptnum, patnum, appt.start_utc)` with the **current** offset if the new send time is still ahead → 200 |
| 8 | Build values (as P4-03 §6.4: clinic name and phone; in `minimal_phi` also first name and local time, via `OpenDentalPatients.get`) | Unavailable → as step 5 |
| 9 | `MessageSender.send(REMINDER, reminder_id, dedupe_key=f"reminder:{id}", attempt, max_attempts=5)` | `SENT` → row `SENT` + `provider_msg_id`; `SKIPPED` / `FAILED` → copied with reason and code; `MessagingTransientError` → 503 if inside the window, else `FAILED` |

- Every outcome updates `reminders.status`, `skip_reason`, `attempts` and `last_error_code` in one transaction with the P4-01 audit event.
- `SKIPPED APPT_CANCELLED` and `APPT_MOVED` are normal outcomes. They are counted, not alerted, and the patient gets nothing.

### 6.6 Config validation (additive to P1-19)
| Rule | Error |
|---|---|
| `reminders.offset_minutes` is an integer in 30–240 | Reject: "Reminder time must be between 30 and 240 minutes before the appointment." |
| `reminders.enabled: true` requires the policy channel allowed (existing P1-19 rule) | Reject (existing) |

### 6.7 Metrics and alerts
| Metric | Labels |
|---|---|
| `reminder_planned_total` | `outcome` = created\|too_late\|disabled |
| `reminder_outcome_total` | `status`, `reason` |
| `reminder_send_delay_s` | — (actual send − `scheduled_for`) |
| `reminder_sweep_enqueued_total` | — |
| `reminder_sweep_too_late_total` | — |
| `reminder_verify_failed_total` | — |

| Alert | Condition | Severity |
|---|---|---|
| A-R1 | `reminder_verify_failed_total` > 0 in 30 min | P2 (console list via P4-01 `outbound_messages`; staff may call the patient) |
| A-R2 | `reminder_sweep_too_late_total` > 0 or the sweep job didn't succeed in 2 h | P1 (reminders are being lost) |

## 7. Implementation guide
1. **Read** P4-03 (planner contract, notification handler pattern), P4-01 (`MessageSender`, `record()`), P4-02 (`ConsentService`), P1-03 (`reminders`), P1-02 (queue, sweep job, `enqueue()`), P1-16 (appointments), P1-19 (`reminders.*`) and P1-13 (internal auth).
2. **Migration** (§6.1) and the `SkipReason` enum update.
3. **Repository** `RemindersRepo`: `insert_pending` (ON CONFLICT DO NOTHING RETURNING), `insert_skipped`, `mark_enqueued`, `cancel_open`, `lock_for_send`, `set_outcome`, `due_for_sweep`, `overdue_unenqueued`.
4. **Planner** (§6.3) and wiring: replace `NoopReminderPlanner` in DI. Add `start_utc` to the event in P2-16 and P2-18.
5. **Sweep** endpoint (§6.4) with the Redis lock.
6. **Task handler** (§6.5), sharing the value-building code with P4-03 (`domain/messaging/values.py`).
7. **Config rule** (§6.6).
8. **Metrics and alerts** (§6.7).
9. **DST tests** (§10) using fixed clocks (`time-machine` or an injected `Clock`).
10. **Docs:** `docs/messaging/reminders.md`, covering the timeline, skip codes, what staff see, and why staff-moved-earlier appointments can miss a reminder.

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| Staff cancelled the appointment in Open Dental | Step 6 → `SKIPPED APPT_CANCELLED`; no message; no alert. |
| Staff deleted the appointment | `get()` → `None` → as above. |
| Staff moved it later (e.g. Thu 3 PM → Fri 3 PM) | Step 7 at Thu 2 PM → `SKIPPED APPT_MOVED` → new row for Fri 2 PM → reminder sent Friday. |
| Staff moved it earlier (Fri → Wed) | Not seen until the Fri check, when the Wed visit is past → step 7 creates nothing (send time passed). The Wed visit gets **no** reminder. Accepted for the MVP (DECISIONS #260). Never a wrong reminder. |
| Appointment marked `Complete` early or `Broken` | Not `Scheduled` → `SKIPPED APPT_CANCELLED`. |
| Open Dental down at reminder time | Retries with backoff while there is time; after that, or after 5 attempts, `FAILED VERIFY_FAILED` + A-R1. **Never sent unverified.** |
| Booking 45 min before the visit (offset 60) | Send time already passed → row `SKIPPED TOO_LATE`; the confirmation (P4-03) is the only message. |
| Retries push the send to < 15 min before the start | `SKIPPED TOO_LATE` (step 2). |
| Clinic changes offset 60 → 120 | Existing rows keep their 60 (`offset_minutes` on the row); new bookings use 120. Step 7 compares with the row's own offset, so no false `APPT_MOVED`. |
| Clinic turns reminders off | No new rows; open rows → `SKIPPED REMINDERS_DISABLED` at the sweep or the send. |
| STOP after the reminder was enqueued | `ConsentService.revoke()` cancels the row; if the task still fires, step 1 sees `CANCELLED` (or step 4 `NO_CONSENT`). |
| AI reschedules the appointment (event) | Planner cancels the open row (`APPT_MOVED`) and creates the new one; the old Cloud Task is deleted, or does nothing at step 1 if deletion failed. |
| Duplicate event or sweep run | Unique key + deterministic task ID → no duplicates. |
| Appointment > 48 h ahead | Row `PENDING`; the sweep enqueues it when it is ≤ 48 h away. |
| DST spring-forward day, 9:00 AM visit | Reminder at 8:00 AM local (13:00 − 1 h = 12:00 UTC = 8:00 EDT). |
| DST fall-back day, 9:00 AM visit (2026-11-01 New York) | 9:00 EST = 14:00 UTC → reminder 13:00 UTC = 8:00 AM EST. |
| Visit at 1:30 AM on a fall-back night (ambiguous local time) | Not realistic for a dental clinic. The start comes from Open Dental as UTC (P1-16 conversion), so the reminder is still `offset` minutes before it. |
| Sweep missed for 3 hours (outage) | Rows still within the window are enqueued at the next run; rows more than 10 minutes overdue → `TOO_LATE` + A-R2. |

## 9. Security, HIPAA and PHI
**PHI handled:**

| Data | Where it flows | Protection |
|---|---|---|
| AptNum, PatNum | `reminders`, task payload (reminder ID only) | IDs |
| `scheduled_for`, `offset_minutes` | `reminders` | `scheduled_for` linked to a patient reveals an appointment time (P1-03 class P): DB encrypted at rest (CMEK), never logged |
| Appointment time, first name | Open Dental → memory → template (only in `minimal_phi`) | Not stored, not logged |
| WhatsApp number | `contact_prefs` → memory → P4-01 | Decrypted in memory only |

- Task payloads carry `clinic_id` and `reminder_id` only (DECISIONS #75). The event's `start_utc` stays in memory.
- **Must never be logged:** `scheduled_for`, appointment times, names, numbers. Log `reminder_id`, status, reason and counts.
- Internal endpoints: OIDC from the two internal service accounts only (P1-13); `/internal/*` denied at Cloud Armor (P1-02).
- Audit: `message.send`, `.skip` and `.fail` through P4-01 for every outcome.

## 10. Testing
Unit tests (`backend/tests/unit/reminders/`) with an injected clock, `FakeOpenDental`, `FakeProvider` and a fake `TasksClient`:

| # | Case | Expected |
|---|---|---|
| R1 | Booked 3 days ahead, offset 60 | Row `PENDING`, `scheduled_for = start − 60 min`, `offset_minutes=60`, not enqueued |
| R2 | Booked 10 h ahead | Row `ENQUEUED`; task `schedule_time = scheduled_for` |
| R3 | Booked 45 min ahead | `SKIPPED TOO_LATE` |
| R4 | Rescheduled event | Old row `CANCELLED APPT_MOVED`; new row for the new time |
| R5 | Cancelled event | Row `CANCELLED APPT_CANCELLED` |
| R6 | Same booked event twice | One row, one task |
| R7 | Sweep with rows due in 47 h and 49 h | First enqueued, second not |
| R8 | Sweep with a `PENDING` row 20 min overdue | `SKIPPED TOO_LATE` |
| R9 | Task: appointment `Broken` | `SKIPPED APPT_CANCELLED`, 0 provider calls |
| R10 | Task: appointment `None` | `SKIPPED APPT_CANCELLED` |
| R11 | Task: start moved +1 day | `SKIPPED APPT_MOVED`; new row for the new time |
| R12 | Task: start moved −2 days (past) | `SKIPPED APPT_MOVED`; no new row |
| R13 | Task: Open Dental unavailable, plenty of time | 503 |
| R14 | Task: Open Dental unavailable, 20 min before start | `FAILED VERIFY_FAILED`, A-R1 metric, 0 provider calls |
| R15 | Task: no consent | `SKIPPED NO_CONSENT`; Open Dental not called |
| R16 | Task: everything matches | `SENT`, template `reminder_nudge_v1`, `reminders.provider_msg_id` set |
| R17 | Offset changed 60 → 120 after booking | Task compares with 60; sends; no `APPT_MOVED` |
| R18 | Config `offset_minutes: 20` and `300` | Rejected by validation |
| R19 | **DST spring forward:** 2027-03-14 9:00 AM `America/New_York` | `scheduled_for` = 12:00 UTC; `minimal_phi` text says "9:00 AM" |
| R20 | **DST fall back:** 2026-11-01 9:00 AM `America/New_York` | `scheduled_for` = 13:00 UTC; text says "9:00 AM" |
| R21 | DST in `America/Denver` and a zone without DST (`America/Phoenix`) | Correct UTC times |
| R22 | Task fires after the row was `CANCELLED` by STOP | 200, no action |
| R23 | Log capture over R1–R22 | No times, names or numbers |

**Integration** (`backend/tests/integration/reminders/`, Postgres + Redis): a 30-day simulation with a fake clock covers book → sweep → enqueue → task → send, plus cancel, staff move later, staff move earlier, and Open Dental outage. **Requirement:** 0 messages for cancelled appointments (also checked again in P4-17).
```bash
cd backend && pytest tests/unit/reminders tests/integration/reminders -q
```

## 11. Acceptance criteria
- [ ] DST transition tests pass for spring forward and fall back in at least two US zones, plus one zone without DST (R19–R21)
- [ ] The offset is configurable per clinic (30–240 minutes) and invalid values are rejected (R1, R18)
- [ ] 0 reminders for cancelled or deleted appointments in tests (R9, R10, integration simulation)
- [ ] A moved appointment gets its reminder at the new time when that time is still ahead (R4, R11)
- [ ] No reminder is ever sent without a successful Open Dental re-read; an unreachable Open Dental ends in `VERIFY_FAILED`, visible in the console (R13, R14)
- [ ] An offset change doesn't affect existing reminders and causes no false `APPT_MOVED` (R17)
- [ ] Repeated events and sweeps never create duplicate reminders (R6, R7)
- [ ] No PHI in logs or task payloads (R23)

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI
- [ ] PR reviewed (HIPAA review: `phi` label)
- [ ] No PHI in logs
- [ ] Docs / README updated (`docs/messaging/reminders.md`)
- [ ] Additive edits merged: P1-03 column and codes, P1-19 validation, P2-16 / P2-18 / P4-03 `start_utc`, DI swap of the planner
- [ ] Pilot clinic asked whether it already uses Open Dental's own reminders, to avoid double reminders (§14)

## 13. Hand-off
| Consumer | What it can rely on |
|---|---|
| P4-13 Admin console | `reminders.offset_minutes` setting with the note "Applies to appointments booked from now on."; failed reminders (`VERIFY_FAILED`, send failures) in the P4-01 failed-messages list |
| P4-17 E2E | Fake-clock simulation helpers; the "0 reminders for cancelled appointments" check |
| P5 load and security tests | Sweep and task endpoints (internal auth), pacer use (BACKGROUND priority) |
| P6 Pilot | Metrics `reminder_outcome_total` and `reminder_send_delay_s` for the pilot report |

## 14. Open questions
| Question | Owner | Needed by |
|---|---|---|
| Does the pilot clinic already send reminders from Open Dental (eReminders or another service)? If yes, decide which one to keep for AI-booked appointments, so patients don't get two | Clinic SME (P0-01) + product owner | Before enabling reminders in P6 |
| Should staff-created appointments also get our reminders (needs listing Open Dental appointments daily)? Proposed: no for the MVP | Product owner | P6 review |

## 15. References
- Plan §4.7 (reminders, pre-send re-fetch), §8 Phase 4, pilot targets ("0 reminders for cancelled appointments")
- Cloud Tasks scheduling limit and queue settings: P1-02 §3 and §6 (sources there)
- Python `zoneinfo`: https://docs.python.org/3/library/zoneinfo.html
- DECISIONS #75, #86, #92, #252–#258, #260
- Related tasks: P1-02, P1-03, P1-13, P1-15, P1-16, P1-19, P2-16, P2-18, P4-01, P4-02, P4-03, P4-13, P4-17
