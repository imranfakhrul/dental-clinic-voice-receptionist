---
id: P4-03
title: Booking confirmation, reschedule and cancel notices (WhatsApp) and moving reminders with the appointment
milestone: P4
epic: E4.1
size: M
labels: area:messaging, type:feature, phi
depends_on: P4-01, P4-02, P1-02, P1-16, P1-20, P2-16, P2-18
status: approved
---

# P4-03: Booking confirmation, reschedule and cancel notices (WhatsApp) and moving reminders with the appointment

> Consolidated task (#52). It absorbs P4-08 "Reschedule and cancellation notifications" (see `tasks/_CONSOLIDATION.md`).

## 1. Summary
After the AI books, reschedules or cancels an appointment, and only after Open Dental has confirmed it, this task sends the patient a WhatsApp message: a booking confirmation, a reschedule notice or a cancel notice. It also tells the reminder planner (P4-04) to create, move or cancel the 1-hour reminder.

The flow is:
1. Every confirmed change raises an `AppointmentChanged` event (`booked`, `rescheduled` or `cancelled`).
2. A publisher tells the reminder planner and puts one task, holding IDs only, on the `notifications` queue.
3. The task handler re-reads the appointment from Open Dental and sends only if it still matches the event. So if a patient books and then cancels a minute later, they get only the cancel notice.
4. It builds the template values and calls P4-01's `MessageSender`, which applies the policy, consent and retry rules.

In the chat, the AI also says "I'm sending a confirmation to your WhatsApp ending in 0123" when the patient has consent on record.

The task is done when:
- a confirmation is sent only after a verified create;
- the reminder moves with a rescheduled appointment and disappears with a cancelled one;
- a change that no longer matches Open Dental sends nothing.

## 2. Why this matters
Plan §2 #9 and §4.7 promise a confirmation "immediately (if consented)" after booking. The seed tasks add notices for reschedule and cancel, and say the reminder job must move with the appointment.

Without this task, patients get no written record of what the AI did. If the reminder isn't moved, a rescheduled patient gets a reminder for the **old** time, which is exactly the kind of mistake the pilot targets forbid ("0 reminders for cancelled appointments").

Sending only after Open Dental confirms protects against the worst case: telling a patient they're booked when they're not (plan principle "Open Dental is the source of truth").

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P4, WhatsApp, Reminders & Admin Console**.
- **Verified create (P1-20, P1-16):** the booking sequence writes the appointment, then reads it back with `GET /appointments/{AptNum}`. It returns `BookingOutcome(status="booked")` only if `PatNum`, time, operatory, status `Scheduled` and our marker all match. `outcome_unknown` means we couldn't confirm it, and then nothing must be sent.
- **`AppointmentChanged` (P2-18):** an event published after a confirmed reschedule or cancel. Its default publisher is a no-op; this task replaces it and adds the `booked` kind.
- **Open Dental appointment status (P1-16):** `AppointmentStatus` is `Scheduled`, `Complete`, `UnschedList`, `Broken`, `Planned`, `PtNote` or `PtNoteCompleted`. Our cancel uses Break, which leaves the appointment `Broken` or moves it to the unscheduled list, per clinic policy. `OpenDentalAppointments.get()` returns `None` on 404, for example when staff deleted the appointment.
- **Cloud Tasks queue `notifications` (P1-02):** 5 dispatches/s, max 8 attempts, backoff 10–300 s, gives up after 2 hours. Payloads are **IDs only** (DECISIONS #75). `enqueue()` takes a deterministic `task_id`, so the same task isn't created twice.
- **MessageSender (P4-01):** `send(MessageRequest, attempt, max_attempts)` runs the policy gate (channel, approved template for the content mode, allowed fields, value checks, consent, dedupe), sends and tracks the result. It raises `MessagingTransientError` so the queue retries. Dedupe keys are `confirm:{aptnum}`, `resched:{aptnum}:{new_start}` and `cancel:{aptnum}`.
- **Content modes (P4-01):**
  - `phi_free_nudge`: only the clinic name and phone, so we don't even read the patient's name or the time for the message;
  - `minimal_phi`: adds first name, date and time.
- **Consent and number (P4-02):** `contact_prefs` holds the patient's WhatsApp number (encrypted), and `ConsentService.current()` says whether it's granted. For a household, a child's row points to the parent's number.
- **Changes staff make directly in Open Dental** are not seen by this task (no polling; DECISIONS #258). Reminders stay correct because P4-04 re-reads the appointment before sending.

New glossary terms: notification task, `APPT_CHANGED` skip, `ReminderPlanner`.

## 4. Scope
**In scope**
- **`AppointmentChanged`** gains `kind="booked"` and `op_key`. P2-16's `BookHandler` publishes `booked` after a confirmed `booked` outcome (not on `replayed` when already published).
- **`NotificationPublisher`** (implements P2-18's `AppointmentEvents`): it calls the `ReminderPlanner` and enqueues the notification task.
- **`ReminderPlanner` contract** (interface and a no-op default here; P4-04 implements it).
- **Task handler** `POST /internal/tasks/notifications`: re-fetch, match check, too-late check, build values, call `MessageSender`.
- **`MessageSender.record()`** (additive to P4-01): writes a `SKIPPED` or `FAILED` row without calling the provider, so skipped notices are visible and audited.
- **Chat note** after booked, rescheduled and cancelled replies (additive P2-04 templates).
- **`appointment_refs.status_cache`** update from the re-fetch.
- Metrics, alert A-N1, and the audit events through P4-01.

**Out of scope** (and which task covers it)
- Reminder rows, send times, DST and the pre-send re-fetch → P4-04
- Policy gate, sending, retries, delivery status, STOP → P4-01
- Consent and number capture → P4-02
- Notices for changes staff make directly in Open Dental → not in the MVP (DECISIONS #258); possible later with Open Dental polling
- Calendar files (.ics) → not in the MVP (P2-16 open question 2)
- Email or SMS notices → not built (DECISIONS #252)

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P4-01 Messaging (approved spec) | `MessageSender.send()`, `MessageRequest`, `MessagingTransientError`, `PolicyStore`, `FakeProvider` | Use `FakeProvider` and the test policy; add `record()` here (additive). |
| P4-02 Consent (approved spec) | `contact_prefs` lookup, `ConsentService.current()` | Seed fixtures with granted and revoked rows. |
| P1-02 Infra (approved spec) | `notifications` queue, `enqueue()`, OIDC-authenticated `/internal/tasks/*` | Tests call the handler directly with the Cloud Tasks headers. |
| P1-16 Adapter (approved spec) | `OpenDentalAppointments.get()`, `OpenDentalPatients.get()`, `Priority.BACKGROUND`, errors | Use the P1-16 fake adapter (`FakeOpenDental`) with scripted appointments. |
| P1-20 Booking (approved spec) | `BookingOutcome` `booked` only after a verified create | Unit-test the publisher with a fake `BookHandler` outcome. |
| P2-16 / P2-18 (approved specs) | `BookHandler`, `AppointmentChanged`, `AppointmentEvents` | Additive edits; until merged, the publisher is tested directly. |
| P4-04 Reminders (not yet written) | Implementation of `ReminderPlanner` | `NoopReminderPlanner` (logs the event name) until P4-04 lands; the contract is fixed here. |

## 6. Interface contract

### 6.1 Event (P2-18 model, extended)
```python
class AppointmentChanged(BaseModel):
    kind: Literal["booked", "rescheduled", "cancelled"]      # "booked" added by P4-03
    clinic_id: str
    pat_num: int
    apt_num: int
    session_id: uuid.UUID
    occurred_at: datetime
    start_utc: datetime | None = None   # added by P4-04 (DECISIONS #260): start after the change (booked/rescheduled); in memory only, never in a task payload
    op_key: str            # NEW: the P2-08 idempotency key of the tool call that made the change (deterministic)
```
- Published by:
  - P2-16 `BookHandler` on `booked` (new);
  - P2-18 on `rescheduled` and `cancelled` (as before);
  - the Tier 2 urgent path, which reuses `BookHandler`.
- Rule (P2-18): publish only after a confirmed success. A `replayed` outcome publishes only if no event with the same `op_key` was published. The publisher keeps `evt:{op_key}` in Redis for 24 h (`SET NX`).

### 6.2 Publisher (`backend/app/domain/messaging/notifications.py`)
```python
class ReminderPlanner(Protocol):                     # implemented by P4-04
    async def on_appointment_changed(self, event: AppointmentChanged) -> None: ...
    # booked      → create the reminder row(s) for this AptNum
    # rescheduled → cancel PENDING/ENQUEUED rows for this AptNum (skip_reason APPT_MOVED) and create new ones
    # cancelled   → cancel PENDING/ENQUEUED rows for this AptNum (skip_reason APPT_CANCELLED)
    # Must be idempotent; reads Open Dental itself if it needs the new time.

class NoopReminderPlanner:                           # default until P4-04
    async def on_appointment_changed(self, event: AppointmentChanged) -> None:
        log.info("reminder_planner.noop", kind=event.kind)

class NotificationPublisher:                          # implements P2-18 AppointmentEvents
    def __init__(self, planner: ReminderPlanner, tasks: TasksClient, redis: Redis) -> None: ...
    async def publish(self, event: AppointmentChanged) -> None:
        """1. dedupe on op_key; 2. planner.on_appointment_changed (errors caught + logged);
        3. enqueue the notification task (3 tries: 0.2 s, 1 s, 3 s; then log + alert A-N1). Never raises."""
```
`publish()` runs after the reply to the patient is decided, so it never delays or blocks the chat. **Proposed:** it runs in a FastAPI background task.

Task creation:
```python
await enqueue(
    queue="notifications",
    path="/internal/tasks/notifications",
    payload={"clinic_id": e.clinic_id, "kind": e.kind, "apt_num": e.apt_num, "pat_num": e.pat_num},
    task_id=f"ntf-{e.kind}-{hashlib.sha256(e.op_key.encode()).hexdigest()[:24]}",
)
```
The payload holds IDs only. The P1-02 payload allow-list gains `kind` (additive edit).

### 6.3 Task handler (`backend/app/api/internal/tasks_notifications.py`)
```
POST /internal/tasks/notifications        (OIDC from Cloud Tasks; P1-02)
Headers: X-CloudTasks-TaskRetryCount (attempt = value + 1; Verify the header name)
Body:    {"clinic_id": "…", "kind": "booked", "apt_num": 7713, "pat_num": 48}
200  done (sent, skipped, duplicate or permanently failed: no retry wanted)
503  transient (Open Dental unavailable, or MessagingTransientError) and attempt < 8
```
Steps (`NotificationService.handle(payload, attempt, max_attempts=8)`):

| # | Step | On failure / no |
|---|---|---|
| 1 | `policy.channel_allowed("whatsapp")` and clinic config `reminders.confirmation_enabled` (added by P4-04 review, DECISIONS #260; off → `SKIPPED REMINDERS_DISABLED`) | `record(SKIPPED, CHANNEL_NOT_ALLOWED)` → 200 |
| 2 | `ConsentService.address_for(clinic, pat_num, WHATSAPP)` exists | `record(SKIPPED, NO_CONTACT)` → 200 |
| 3 | `ConsentService.current(clinic, bidx, WHATSAPP).granted` | `record(SKIPPED, NO_CONSENT)` → 200 (checked before Open Dental to save a call) |
| 4 | `appt = OpenDentalAppointments.get(ctx, apt_num, priority=BACKGROUND)` | `OpenDentalUnavailable` / timeout / rate-limited → 503 while `attempt < 8`; on attempt 8 `record(FAILED, VERIFY_FAILED)` → 200 (A-M1) |
| 5 | Match check (table below) | `record(SKIPPED, APPT_CHANGED)` → 200 |
| 6 | Too-late check: `appt.start_utc <= now` for `booked` and `rescheduled`; for `cancelled` only when `appt` exists and its start has passed | `record(SKIPPED, TOO_LATE)` → 200 |
| 7 | Update `appointment_refs.status_cache` and `status_checked_at` | Ignore errors (cache only) |
| 8 | Build values (§6.4) and `MessageRequest` | `OpenDentalPatients.get` unavailable (only in `minimal_phi`) → same as step 4 |
| 9 | `MessageSender.send(req, attempt=attempt, max_attempts=8)` | `MessagingTransientError` → 503; any `SendOutcome` → 200 |

Match check:

| Kind | Sends when | Otherwise |
|---|---|---|
| `booked` | `appt` exists, `appt.pat_num == pat_num`, `status == Scheduled` | `APPT_CHANGED` (e.g. cancelled or moved in the meantime; a newer event covers it) |
| `rescheduled` | `appt` exists, same PatNum, `status == Scheduled` | `APPT_CHANGED` |
| `cancelled` | `appt is None`, or `status in {Broken, UnschedList}` | `APPT_CHANGED` (e.g. booked again) |

Two rapid reschedules of the same appointment are both fine: each task renders the **current** time from Open Dental. The dedupe key `resched:{aptnum}:{start}` makes the second task a `DUPLICATE` when both see the same final time, so the patient gets one notice for the final time.

### 6.4 Values and request
```python
def build_request(kind, appt, pat_num, address, cfg, policy, patient: PatientRecord | None) -> MessageRequest:
    tz = ZoneInfo(cfg.clinic.timezone)
    local = appt.start_utc.astimezone(tz) if appt else None
    values = {"clinic_name": cfg.clinic.display_name,
              "clinic_phone": format_us_phone(cfg.clinic.public_phone)}          # "(503) 555-0100"
    if policy.whatsapp_mode == "minimal_phi":
        values["first_name"] = (patient.preferred_name or patient.first_name).strip()
        if local:
            values["appointment_date"] = format_date(local, templates.date_format)   # "Tue, Mar 10"
            values["appointment_time"] = format_time(local, templates.time_format)   # "9:30 AM"
    mtype, key = {
        "booked":      (MessageType.BOOKING_CONFIRMATION, f"confirm:{appt.apt_num}"),
        "rescheduled": (MessageType.RESCHEDULE_NOTICE,    f"resched:{appt.apt_num}:{appt.start_utc:%Y%m%dT%H%M}"),
        "cancelled":   (MessageType.CANCEL_NOTICE,        f"cancel:{apt_num}"),
    }[kind]
    return MessageRequest(clinic_id=…, message_type=mtype, patnum=pat_num, aptnum=apt_num,
                          to_e164=address.e164, values=values, dedupe_key=key)
```
- In `phi_free_nudge` mode the patient record is **not fetched** (step 8 is skipped), so no name leaves Open Dental.
- If a `cancelled` appointment was deleted (`appt is None`) and the mode needs `appointment_date`, the sender's G5 check fails for missing values. **Proposed:** the cancel template in `minimal_phi` mode then falls back to a nudge-style template (`cancel_notice_nudge_v1`). `build_request` picks it explicitly via `MessageRequest.template_override` (additive to P4-01; the override must still pass G2–G6).

### 6.5 `MessageSender.record()` (additive to P4-01)
```python
async def record(self, req_or_ids: MessageRequest | MessageIds, *, status: Literal["SKIPPED", "FAILED"],
                 reason: str) -> SendOutcome: ...
# Inserts (or updates, by dedupe_key) an outbound_messages row without calling the provider; audits message.skip / .fail.
# For steps 1–3, where no address is known, address_bidx is the clinic's all-zero placeholder (32 zero bytes).
```
New reason codes (additive to P4-01 §6.4): `NO_CONTACT`, `APPT_CHANGED`, `TOO_LATE`, `VERIFY_FAILED`.

### 6.6 Chat note (additive to P2-04 templates)
| Intent | Text | When |
|---|---|---|
| `whatsapp_note_booked` | "I'm sending a confirmation to your WhatsApp ending in {last4}." | After `booked`, if the policy allows WhatsApp and consent is granted for this patient's number |
| `whatsapp_note_rescheduled` | "I'm sending the new time to your WhatsApp ending in {last4}." | After `rescheduled`, same condition |
| `whatsapp_note_cancelled` | "I'm sending a cancellation notice to your WhatsApp ending in {last4}." | After `cancelled`, same condition |

- The note is a second sentence after `booked`, `rescheduled` or `cancelled`.
- Voice says "ending in 0-1-2-3".
- In `phi_free_nudge` mode the wording is the same; the patient already saw on the consent text what the message will contain.
- `{last4}` comes from the session slot or `contact_prefs`, and is rendered by code.

### 6.7 Metrics and alerts
| Metric | Labels |
|---|---|
| `notification_enqueued_total` | `kind` |
| `notification_enqueue_failed_total` | `kind` |
| `notification_outcome_total` | `kind`, `status`, `reason` |
| `notification_latency_ms` | `kind` (event `occurred_at` → `SENT`); target p95 < 60 s |

| Alert | Condition | Severity |
|---|---|---|
| A-N1 | `notification_enqueue_failed_total` > 0 in 10 min | P2 (the patient was told a message is coming; ops check Cloud Tasks) |

`VERIFY_FAILED` and final send failures already raise A-M1 through P4-01.

## 7. Implementation guide
1. **Read** P2-18 §`AppointmentChanged`, P2-16 `BookHandler`, P1-20 `BookingOutcome`, P1-16 appointments and patients, P1-02 queues and `enqueue()`, P4-01 sender and reason codes, and P4-02 `ConsentService`.
2. **Extend the event** with `kind="booked"` and `op_key`. Add the publish call to `BookHandler` (P2-16 additive) and pass `op_key` from P2-18's calls.
3. **`ReminderPlanner`** protocol and `NoopReminderPlanner`. Wire them by dependency injection, so P4-04 swaps in its implementation.
4. **`NotificationPublisher`**: Redis dedupe, planner call, enqueue with retries, alert metric. Register it as the `AppointmentEvents` implementation.
5. **`MessageSender.record()`** and the new reason codes (P4-01 additive), plus `template_override`.
6. **Task handler** and `NotificationService.handle()` with steps 1–9.
7. **Chat notes** in P2-04, rendered after the outcome templates.
8. **Metrics and alert**.
9. **Tests** (§10). Then update `docs/flows/booking.md` and `docs/flows/reschedule.md` with the notification step.

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| `BookingOutcome` is `outcome_unknown` or `in_progress` | No event, no message (only a verified `booked` publishes). |
| Same `book_appointment` call replayed (P2-08 idempotency) | `op_key` already in Redis → no second event; the task ID is also the same → no second task. |
| Patient booked, then cancelled within a minute | Confirmation task re-reads → `Broken` → `SKIPPED APPT_CHANGED`. The cancel notice is sent. |
| Patient rescheduled twice quickly | Both tasks render the final time. The second is a `DUPLICATE` (same dedupe key) or sends the newer time if it changed again. |
| Staff deleted the appointment before the confirmation task ran | `get()` → `None` → `booked` mismatch → `SKIPPED APPT_CHANGED`. |
| Open Dental down for 2 hours | 8 attempts → `FAILED VERIFY_FAILED` → A-M1 and the failed-messages list (P4-01). Nothing is sent unverified. |
| Policy channel off | `SKIPPED CHANNEL_NOT_ALLOWED`; no Open Dental call. No chat note. |
| Patient said "No thanks" to WhatsApp | `SKIPPED NO_CONTACT` or `NO_CONSENT`; no chat note. |
| Patient sent STOP between booking and send | Step 3 → `SKIPPED NO_CONSENT`. |
| Appointment is in 20 minutes (urgent Tier 2 booking) | Confirmation is still sent (start is in the future). The reminder planner decides that a 1-hour reminder is too late (P4-04). |
| Cancel of an appointment whose time has passed | `SKIPPED TOO_LATE`. |
| Deleted appointment, cancel notice in `minimal_phi` mode | Falls back to the nudge cancel template (§6.4). |
| Household: parent books two children | Two events and two tasks. Both go to the parent's number with their own dedupe keys (one per AptNum). |
| Cloud Tasks enqueue fails three times | `notification_enqueue_failed_total`, A-N1; the reminder planner was still called. **Proposed:** no outbox in the MVP. |
| Reminder planner raises | Logged with event kind and IDs; the notification task is still enqueued. P4-04's hourly sweep and pre-send check are the backup. |
| Task arrives for another environment's clinic | `ClinicODContextProvider.get` fails → 200 with an error log (no retry storm). |

## 9. Security, HIPAA and PHI
**PHI handled:**

| Data | Where it flows | Protection |
|---|---|---|
| PatNum, AptNum | Event, task payload, `outbound_messages` | IDs only (DECISIONS #75) |
| Appointment time | Open Dental → memory → template value (only in `minimal_phi`) → Meta | Never in task payloads, logs or our DB |
| First name | Open Dental → memory → template value (only in `minimal_phi`) | Not fetched at all in `phi_free_nudge` mode |
| WhatsApp number | `contact_prefs` → memory → P4-01 | Decrypted in memory only |
| Last 4 digits | Chat note | The verified patient's own session |

- **Must never be logged:** times, names, numbers, rendered values. Logs carry `kind`, `apt_num`, `pat_num`, `reason` and `status` only (P1-07 allow-list).
- **No unverified sends:** step 4 must succeed before any message (pilot target "0 reminders for cancelled appointments" applies in spirit to notices too).
- **Audit:** `message.send`, `.skip` and `.fail` through P4-01, including `record()`.
- The internal task endpoint is reachable only from inside the project (OIDC + internal ingress, P1-02).

## 10. Testing
Unit tests (`backend/tests/unit/notifications/`) with `FakeOpenDental`, `FakeProvider`, a fake `TasksClient` and a recording `ReminderPlanner`:

| # | Case | Expected |
|---|---|---|
| N1 | `booked` outcome | Event published once; planner called with `booked`; one task with an IDs-only payload |
| N2 | `outcome_unknown` | No event, no task |
| N3 | Replayed booking | No second event or task |
| N4 | Handler: booked + Scheduled + consent | `SENT`, template `booking_confirmation_nudge_v1`, params = clinic name and phone only |
| N5 | Handler in `minimal_phi` | Params include first name, date and time in clinic time (DST date fixture) |
| N6 | Booked but appointment now `Broken` | `SKIPPED APPT_CHANGED`; 0 provider calls |
| N7 | Cancelled, appointment deleted (`None`) | Cancel notice sent |
| N8 | Rescheduled twice to the same final time | 1 send, 1 `DUPLICATE` |
| N9 | Open Dental unavailable, attempt 3 of 8 | 503 |
| N10 | Open Dental unavailable, attempt 8 of 8 | `FAILED VERIFY_FAILED`, 200 |
| N11 | No consent | `SKIPPED NO_CONSENT`; Open Dental not called |
| N12 | Policy off | `SKIPPED CHANNEL_NOT_ALLOWED`; Open Dental not called |
| N13 | Start time passed | `SKIPPED TOO_LATE` |
| N14 | `phi_free_nudge` | `OpenDentalPatients.get` never called |
| N15 | Chat note | Shown only when consent is granted; contains last 4 only |
| N16 | Reschedule event | Planner receives `rescheduled` (reminder moves; checked end to end in P4-04 and P4-17) |
| N17 | Log capture over N1–N15 | No time, name or number in any log record |

Integration (`backend/tests/integration/notifications/`): book → task → `FakeProvider` → status webhook → `DELIVERED`, using Postgres and Redis in Docker.
```bash
cd backend && pytest tests/unit/notifications tests/integration/notifications -q
```

## 11. Acceptance criteria
- [ ] A confirmation is sent only after a verified create: no event or message for `outcome_unknown`, `in_progress` or a replay (N1–N3)
- [ ] The reminder planner is told about every booked, rescheduled and cancelled event, so the reminder job moves with the appointment (N1, N16; end to end in P4-17)
- [ ] Before any send, the appointment is re-read from Open Dental and a mismatch sends nothing (N6, N10)
- [ ] Reschedule and cancel notices are sent with the correct message type and dedupe key (N7, N8)
- [ ] No message without policy permission and consent; Open Dental is not called in those cases (N11, N12)
- [ ] In `phi_free_nudge` mode no patient name or time is fetched or sent (N4, N14)
- [ ] The chat tells the patient where the WhatsApp message goes, only when it will be sent (N15)
- [ ] No PHI in logs or task payloads (N1, N17)

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI
- [ ] PR reviewed (HIPAA review: `phi` label)
- [ ] No PHI in logs
- [ ] Docs / README updated (booking and reschedule flow docs)
- [ ] Additive edits merged: P2-16 publish call, P2-18 event fields, P2-04 chat notes, P1-02 payload key, P4-01 `record()` + reason codes + `template_override`

## 13. Hand-off
| Consumer | What it can rely on |
|---|---|
| P4-04 Reminders | `ReminderPlanner.on_appointment_changed()` is called once per confirmed change (booked, rescheduled, cancelled), after Open Dental confirmed it; it must be idempotent |
| P4-13 Admin console | Skipped and failed notices appear in `outbound_messages` with reason codes (`APPT_CHANGED`, `VERIFY_FAILED`, …) |
| P4-17 E2E | Book → confirm → reschedule → notice → cancel → notice, with `FakeProvider` |
| P2-16 / P2-18 | `NotificationPublisher` replaces the no-op `AppointmentEvents` |

## 14. Open questions
| Question | Owner | Needed by |
|---|---|---|
| Should changes staff make directly in Open Dental also send notices (needs Open Dental polling)? Proposed: no for the MVP; revisit after the pilot | Product owner | P6 review |

## 15. References
- Plan §2 #9 (confirmation), §4.7 (WhatsApp reminders), §8 Phase 4
- DECISIONS #75, #92, #199, #252–#256, #258
- Related tasks: P1-02, P1-16, P1-20, P2-04, P2-08, P2-16, P2-18, P4-01, P4-02, P4-04, P4-13, P4-17
