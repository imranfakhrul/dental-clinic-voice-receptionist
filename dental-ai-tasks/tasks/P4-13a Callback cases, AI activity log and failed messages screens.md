---
id: P4-13a
title: Callback cases, AI activity log and failed messages screens
milestone: P4
epic: E4.2
size: L
labels: area:admin, area:frontend, area:backend, type:feature, phi
depends_on: P4-09, P2-22, P2-23, P1-13, P1-07, P1-03, P1-15, P4-01, P4-03, P4-04
status: approved
---

# P4-13a: Callback cases, AI activity log and failed messages screens

> New task split from P4-13 (DECISIONS #266). It holds the scope of **P4-14** "Callback cases list and status workflow" and **P4-15** "AI activity log and AI-booked appointment review" (both merged into it), plus the **failed-messages page** promised to P4-01. P4-13 keeps the settings screens.

## 1. Summary
Build the console pages clinic staff use every day.

1. **Callbacks** (`/admin/callbacks`, detail `/admin/callbacks/[id]`):
   - list of callback cases, **URGENT pinned on top**, with filters by status, urgency, reason, assignee and date;
   - case detail: reason, situation, contact (masked for READ_ONLY), linked PatNum/AptNum, email status;
   - workflow `OPEN → CONTACTED → RESOLVED`, assign to a staff member, and a **contact attempt** log with fixed outcome codes (no free-text notes);
   - ADMIN can reopen a resolved case;
   - **unsent email** badge with **Resend email**;
   - auto-refresh every 30 s, open-case count in the tab title, red banner while an URGENT case is open.
2. **AI activity** (`/admin/activity`): one row per patient conversation with time, channel, verified yes/no, outcomes (booked, rescheduled, cancelled, callback, emergency, abandoned) and linked IDs. **No free text and no transcript.**
3. **AI-booked appointments** (`/admin/activity/appointments`): every appointment the AI created, with the patient name and appointment details read live from Open Dental, and a **Mark reviewed** action, so the clinic can check the AI's work during the pilot.
4. **Failed messages** (`/admin/messages`): WhatsApp confirmations, notices and reminders that failed or were skipped for a reason staff should act on, with the patient looked up live from Open Dental and **Acknowledge**.

Seed acceptance criteria carried over:
- status changes are audited;
- urgent cases are pinned on top;
- no free-text PHI is shown in the activity log.

## 2. Why this matters
- **Callbacks are the safety net.** Every time the AI can't finish (identity not verified, no slot, emergency with no urgent slot), it promises the patient a call. If staff can't see and work the cases quickly, those patients are forgotten. That is risk R23, and for URGENT cases it is a patient-safety risk. The email is only a pointer, because in `link_only` mode it contains no details. The console is where staff actually read the case.
- **The activity log and AI-booked review** let the clinic trust the AI. In the pilot, the office manager checks each AI booking (right provider, right visit type) and sees how many conversations ended in a booking. This also feeds the ≥ 70 % "booked without callback" target.
- **Failed messages:** if a confirmation or reminder fails (wrong number, patient blocked the business), staff need to know so they can phone the patient. P4-01 records the failure, and this page shows it.

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P4, WhatsApp, Reminders & Admin Console**.
- **Callback cases (P1-03 + P2-22):** table `callback_requests`. Its columns:

  | Group | Columns |
  |---|---|
  | IDs | `id`, `clinic_id`, `session_id`, `case_ref` (`CB-7KQ2MZ`) |
  | Reason and urgency | `reason_code` (category: `BOOKING_FAILED`, `NO_SLOTS`, `IDENTITY_UNVERIFIED`, `INSURANCE_BILLING`, `CLINICAL_QUESTION`, `URGENT_DENTAL`, `PATIENT_REQUEST`, `SYSTEM_ERROR`, `OTHER`), `reason_detail` (registry key, with a staff label), `extra_reasons[]`, `urgency` (`ROUTINE` / `URGENT`), `upgraded_at` |
  | Patient | `patient_type`, `patnum` |
  | Encrypted (P1-05) | `contact_name_enc`, `contact_phone_enc` (+ `_bidx`), `contact_dob_enc`, `contact_email_enc`, `preferred_time_enc`, `summary_enc` |
  | Status and staff | `status` (`OPEN` / `CONTACTED` / `RESOLVED`), `assigned_to_staff_id` |
  | Email | `email_status` (`PENDING` / `SENT` / `FAILED`), `email_attempts`, `email_seq`, `email_sent_seq`, `email_last_error`, `email_sent_at` |
  | Timestamps | `created_at`, `updated_at`, `contacted_at`, `resolved_at` |

  - Contact may be NULL for URGENT emergency cases until collected.
  - Partial unique index: one `OPEN` case per session.
  - Console index on (`clinic_id`, `status`, `urgency`, `created_at` DESC).
  - The staff labels come from the P2-22 reason registry, e.g. `no_suitable_slot` → "No suitable time found (preference attached)".
- **Unsent email (P2-22):** `email_status = FAILED` after retries. Alerts A-CB1 (ticket) and A-CB2 (page for URGENT). The query is `WHERE clinic_id = ? AND email_status = 'FAILED' ORDER BY urgency DESC, created_at`. Emails are sent by the `callback-emails` Cloud Tasks queue, keyed by (`case_id`, `email_seq`).
- **Email link (P0-08):** `{ADMIN_CONSOLE_BASE_URL}/cases/{case_id}`. The console lives at `frontend/app/admin/` (P4-09, DECISIONS #262), so this task adds the route `/admin/cases/[id]` that redirects to `/admin/callbacks/[id]`, and `ADMIN_CONSOLE_BASE_URL` is set to `https://app.<domain>/admin` (DECISIONS #266).
- **RBAC (P1-13, DECISIONS #120):**
  - permissions: `callback:read` (list and detail, contact masked), `callback:read_contact` (full contact), `callback:update` (status, assignee), `activity:read`, `message:read`, `message:ack`;
  - roles:
    - ADMIN: all;
    - FRONT_DESK: callbacks incl. contact and update, activity, messages;
    - DENTIST: callbacks incl. contact and update;
    - READ_ONLY: callbacks with masked contact (phone `+1 •••-•••-4567`, name = first initial).
  - Foreign-clinic IDs return 404. The example route `PATCH /v1/admin/callbacks/{callback_id}` is in P1-13.
- **Audit (P1-07):** `audit(session, action, result, actor, clinic_id, object_type, object_ref, details)` with IDs and codes only.
  - Existing actions:
    - `callback.create` / `.status_change` / `.email_sent` / `.email_failed`;
    - `appointment.book` / `.reschedule` / `.cancel`;
    - `safety.emergency_detected`, `emergency.tier1` / `.tier2`;
    - `patient.verify` / `.verify_failed`;
    - `message.send` / `.skip` / `.fail`.
  - AI actions use `actor_type = PATIENT_SESSION` and `actor_id = <session UUID>`.
- **Sessions (P1-03):** `sessions` with `channel` (`TEXT` / `VOICE`), `status`, `end_reason` (`COMPLETED`, `IDLE_TIMEOUT`, `USER_LEFT`, `EMERGENCY_911`, `CALLBACK_CREATED`, `ERROR`), `verified_patnum`, `channel_switches`, `started_at`, `ended_at`. Transcripts are not stored (`privacy.transcript_retention_days: 0`).
- **AI-made appointments (P1-03):** `appointment_refs` (`aptnum`, `patnum`, `created_by_session_id`, `status_cache`, `created_at`).
- **Failed messages API (P4-01 §6.10):**
  - `GET /v1/admin/messages?status=FAILED&acknowledged=false&limit&cursor` returns `{id, message_type, status, reason, patnum, aptnum, attempts, failed_at, acknowledged_at}`;
  - `POST /v1/admin/messages/{id}/acknowledge` returns 204, or 409 if the message is not FAILED.
  - Reason codes:
    - from P4-01, e.g. `RECIPIENT_UNREACHABLE`, `NOT_ON_WHATSAPP`, `OUTSIDE_WINDOW`;
    - from P4-03: `APPT_CHANGED`, `VERIFY_FAILED`, `NO_CONTACT`, `TOO_LATE`;
    - from P4-04: `APPT_CANCELLED`, `APPT_MOVED`, `VERIFY_FAILED`, `REMINDERS_DISABLED`.
- **Open Dental reads (P1-15):** patient and appointment reads through the adapter with `Priority.INTERACTIVE` and the per-clinic rate budget. Staff lookups are audited as `patient.search` with the staff actor.
- **Console shell (P4-09):** `NAV` (Callbacks and Failed messages entries already reserved for this work), `<Can>`, the table component, Home tiles linking here, MSW mocks.

New glossary terms: contact attempt, AI activity log, AI-booked review, case auto-refresh.

## 4. Scope
**In scope**
- Backend endpoints in §6.3–§6.6: callbacks list, detail, update, attempts, reopen, resend; activity list; AI-booked list and review; message enrichment.
- DB (additive to P1-03):
  - table `callback_attempts`;
  - columns `appointment_refs.reviewed_at` / `reviewed_by`;
  - an `audit_log` index for the activity query.
- Audit actions (additive to P1-07): `callback.view_contact`, `callback.assign`, `callback.attempt`, `callback.reopen`, `callback.email_resend`, `appointment.review`.
- P2-22 additive: `CallbackEmailService.resend(case_id)`.
- Frontend pages:
  - callbacks list and detail, plus the `/admin/cases/[id]` redirect;
  - activity;
  - AI-booked appointments;
  - failed messages.
- Tests (backend, frontend, E2E).

**Out of scope** (and which task covers it)
- Settings screens → P4-13
- Writing notes into Open Dental (commlog) from the console → not in the MVP; staff write commlogs in Open Dental
- Push notifications or sound for new cases → not in the MVP (email + A-CB2 page cover it)
- Exporting cases or activity to CSV → not in the MVP (PHI export risk)
- KPI dashboard → P6-02 (may reuse the activity query)
- Audit log viewer for compliance → P4-09 / P5

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P4-09 Shell (approved spec) | `NAV`, `<Can>`, table, MSW | — |
| P2-22 / P2-23 (approved specs) | `callback_requests`, registry labels, email queue | Seed fixtures: 30 cases (mix of urgency, status, email status) via `tests/fixtures/callbacks.py` |
| P1-13 (approved spec) | `require()`, masking rule | — |
| P1-07 (approved spec) | `audit()`, action enum | — |
| P1-15 (approved spec) | Patient and appointment reads | P1-15 fake Open Dental with seeded patients |
| P4-01 (approved spec) | Messages API | MSW handler with the §6.10 example |
| P4-03 / P4-04 (approved specs) | Reason codes for display | Static label map in this task (§6.7) |

## 6. Interface contract

### 6.1 Pages and permissions
| Route | View | Actions |
|---|---|---|
| `/admin/callbacks` | `callback:read` | — |
| `/admin/callbacks/[id]` | `callback:read` (contact masked without `callback:read_contact`) | status, assign, attempt, resend: `callback:update`; reopen: `callback:reopen` (ADMIN only, new) |
| `/admin/cases/[id]` | redirect to `/admin/callbacks/[id]` (keeps the P0-08 email link) | — |
| `/admin/activity` | `activity:read` | — |
| `/admin/activity/appointments` | `activity:read` | Mark reviewed: `activity:read` + `callback:update` (Proposed: same people who work cases) |
| `/admin/messages` | `message:read` | Acknowledge: `message:ack` |

New permission (P1-13 additive): `CALLBACK_REOPEN = "callback:reopen"`, for ADMIN only.

`NAV` additions:
- the existing "Callbacks" and "Failed messages" entries change `ownerTask` to `"P4-13a"`;
- new entries "AI activity" and "AI-booked appointments" in the group "Patients", `view: "activity:read"`.

### 6.2 Callbacks list
```
┌ ⚠ 1 URGENT case is open ──────────────────────────────────────────────── [View] ┐
Filters: [Open ▾] [All urgency ▾] [All reasons ▾] [Anyone ▾] [Last 30 days ▾]   Auto-refresh ● 30 s

 Urgency  Case       Received          Reason                                Contact        Assigned  Attempts  Email
 URGENT   CB-7KQ2MZ  Today 9:02 AM     Emergency: urgent, no slot            J. •••-4567*   Sarah     1 (No answer)  Sent
 Normal   CB-3PW8RT  Today 8:15 AM     No suitable time found                John Smith     —         0         ⚠ Not sent [Resend]
```
- **Sort:** `status` (OPEN, CONTACTED, RESOLVED) → `urgency` (URGENT first) → `created_at` (oldest first within OPEN, so nobody waits longest). URGENT OPEN or CONTACTED cases are always pinned on top whatever the filter, except a status filter that excludes them.
- **Columns:**
  - urgency badge;
  - `case_ref`;
  - received time (clinic time zone);
  - staff label of `reason_detail`, with "+N" when `extra_reasons` is not empty;
  - contact (masked per permission; "Not collected yet" for NULL);
  - assignee;
  - attempt count and last outcome;
  - email status.
- **Auto-refresh:** every 30 s while the tab is visible (`document.visibilityState`), using `GET …?since=<etag>`. When the result has not changed, the server returns 304 and the client does nothing.
  - Tab title: `(N) Callbacks · <clinic>`, where N = OPEN cases.
  - The red banner shows while any URGENT case is OPEN.
- **Default filter:** OPEN + CONTACTED, last 30 days. Paging is by cursor (50 per page).

### 6.3 Callback endpoints
```
GET  /v1/admin/callbacks?status=OPEN,CONTACTED&urgency=URGENT&reason=NO_SLOTS&assignee=<uuid|none|me>
                        &from=2026-12-01&to=2026-12-08&cursor=<opaque>&limit=50      Permission callback:read
200 {"items": [CallbackListItem], "next_cursor": null, "counts": {"open": 3, "open_urgent": 1, "email_failed": 1}}
     ETag header; If-None-Match → 304

CallbackListItem = {"id": "uuid", "case_ref": "CB-7KQ2MZ", "urgency": "URGENT", "status": "OPEN",
  "reason_code": "URGENT_DENTAL", "reason_detail": "emergency_tier2_no_slot", "reason_label": "Emergency: urgent, no slot",
  "extra_reason_labels": [], "created_at": "...", "upgraded_at": null,
  "contact": {"name": "John Smith", "phone": "+15551234567"} | {"name": "J.", "phone": "+1 •••-•••-4567", "masked": true} | null,
  "assigned_to": {"id": "uuid", "display_name": "Sarah Lee"} | null,
  "attempts": 1, "last_outcome": "NO_ANSWER", "email_status": "SENT"}

GET  /v1/admin/callbacks/{id}                              Permission callback:read
200 CallbackDetail = CallbackListItem + {"patient_type": "existing", "patnum": 1234, "dob": "1985-04-12" | masked,
     "email": "...", "preferred_time": "Weekday mornings", "summary": "<decrypted situation text>",
     "session_id": "uuid", "aptnum": null, "email_attempts": 1, "email_last_error": null, "email_sent_at": "...",
     "contacted_at": null, "resolved_at": null, "history": [HistoryItem]}
     history = status changes, assignments and attempts (from callback_attempts + audit_log), newest first

PATCH /v1/admin/callbacks/{id}                             Permission callback:update
{"status": "CONTACTED" | "RESOLVED", "assigned_to_staff_id": "uuid" | null, "base_updated_at": "..."}
200 CallbackDetail;  409 stale (base_updated_at differs);  422 invalid transition

POST /v1/admin/callbacks/{id}/attempts                     Permission callback:update
{"outcome": "NO_ANSWER" | "LEFT_VOICEMAIL" | "WRONG_NUMBER" | "SPOKE_WITH_PATIENT" | "APPOINTMENT_MADE" | "OTHER"}
201 {"attempt_no": 2, "case": CallbackDetail}
     SPOKE_WITH_PATIENT or APPOINTMENT_MADE on an OPEN case also sets status CONTACTED (one transaction)

POST /v1/admin/callbacks/{id}/reopen                       Permission callback:reopen (ADMIN)
{"reason": "RESOLVED_BY_MISTAKE" | "PATIENT_CALLED_AGAIN" | "OTHER"}
200 CallbackDetail;  409 open_case_exists (another OPEN case for the same session; link to it)

POST /v1/admin/callbacks/{id}/resend-email                 Permission callback:update
202 {"email_status": "PENDING", "email_seq": 3}
409 if email_status is PENDING (a send is already queued); rate limit 3 per case per hour
```
**Status transitions:**

| From | To | Allowed by | Side effects |
|---|---|---|---|
| OPEN | CONTACTED | `callback:update` | `contacted_at = now` |
| OPEN | RESOLVED | `callback:update` | `contacted_at` stays NULL if never contacted; `resolved_at = now` |
| CONTACTED | RESOLVED | `callback:update` | `resolved_at = now` |
| CONTACTED | OPEN | not allowed (422) | — |
| RESOLVED | OPEN | `callback:reopen` via `/reopen` | `resolved_at = NULL`; audit `callback.reopen` |

**Resend:** `CallbackEmailService.resend(case_id)` (P2-22 additive) increments `email_seq`, sets `email_status = PENDING` and enqueues one task named after (`case_id`, `email_seq`), so a double click can't send twice. The email is the normal `link_only` email for the case.

### 6.4 DB additions (P1-03, additive)
`callback_attempts` (append-only for `app_rw`, like `audit_log`):

| Column | Type | Constraints | PHI |
|---|---|---|---|
| `id` | uuid | PK | - |
| `clinic_id` | uuid | FK | - |
| `callback_id` | uuid | FK `callback_requests`, index (`callback_id`, `occurred_at`) | - |
| `attempt_no` | int | NOT NULL; UNIQUE (`callback_id`, `attempt_no`) | - |
| `outcome` | text | CHECK in the six codes | - |
| `staff_id` | uuid | FK `staff_users` | - |
| `occurred_at` | timestamptz | NOT NULL | - |

`appointment_refs` gains `reviewed_at timestamptz NULL` and `reviewed_by uuid NULL FK staff_users`.

`audit_log` gains the index `ix_audit_session_actor` on (`clinic_id`, `actor_id`, `occurred_at`) WHERE `actor_type = 'PATIENT_SESSION'`, for the activity query.

No free-text column is added anywhere (DECISIONS #266: staff write details in Open Dental's commlog).

### 6.5 AI activity endpoints
```
GET /v1/admin/activity?from=2026-12-01&to=2026-12-08&channel=TEXT|VOICE&outcome=BOOKED&cursor&limit=50
                                                            Permission activity:read
200 {"items": [{
      "session_id": "uuid", "started_at": "...", "ended_at": "...", "channel": "VOICE", "channel_switches": 1,
      "verified": true, "patnum": 1234,
      "outcomes": ["BOOKED"],                     // see mapping below; [] → "No action"
      "aptnums": [48213], "case_refs": [], "end_reason": "COMPLETED"}],
     "totals": {"sessions": 42, "booked": 18, "rescheduled": 3, "cancelled": 2, "callback": 9, "emergency": 1, "abandoned": 7},
     "next_cursor": null}
```
Outcome mapping (from `audit_log` rows with `actor_type = PATIENT_SESSION` and `actor_id = session_id`, plus `sessions.end_reason`):

| Outcome | Source |
|---|---|
| `BOOKED` | `appointment.book` SUCCESS |
| `RESCHEDULED` | `appointment.reschedule` SUCCESS |
| `CANCELLED` | `appointment.cancel` SUCCESS |
| `CALLBACK` | `callback.create` SUCCESS (`case_ref` from `callback_requests.session_id`) |
| `EMERGENCY` | `emergency.tier1` or `.tier2` |
| `CHANGE_REFUSED` | `appointment.change_refused` |
| `ABANDONED` | `end_reason` in `IDLE_TIMEOUT`, `USER_LEFT` with none of the above |
| `ERROR` | `end_reason = ERROR` |

- The response contains IDs, codes and counts only. **No names, no free text, no summaries** (seed acceptance criterion).
- PatNum is shown as a number. Staff who need the name open the AI-booked page or Open Dental.
- Not audited per view (it shows no PHI beyond PatNum/AptNum IDs); `activity.view` is **Proposed** as a counter metric only.

```
GET  /v1/admin/activity/appointments?reviewed=false&from&to&cursor&limit=25    Permission activity:read
200 {"items": [{"aptnum": 48213, "patnum": 1234, "created_at": "...", "session_id": "uuid",
      "patient_name": "John Smith", "start_local": "2026-12-09T09:00:00-05:00", "provider": "HYG1",
      "operatory": "Op 2", "visit_type": "Recall", "od_status": "Scheduled",
      "reviewed_at": null, "reviewed_by": null}],
     "unreviewed_count": 5, "od_unavailable": false}
     Patient name and appointment fields are read live from Open Dental (P1-15, INTERACTIVE, batch of ≤ 25);
     audit patient.search (staff actor, count) once per page

POST /v1/admin/activity/appointments/{aptnum}/review       Permission activity:read + callback:update
204; audit appointment.review; 404 if not in appointment_refs for this clinic; idempotent
```
If Open Dental is unreachable, the list still returns the IDs and times from `appointment_refs` with `od_unavailable: true`. The page shows "Patient details unavailable right now".

### 6.6 Failed messages page
- Uses the P4-01 API unchanged. Enrichment for display goes through the new endpoint `GET /v1/admin/messages/enrich?ids=…` (≤ 50). It returns `{id, patient_name, phone_masked_last4, appointment_local}`, read live from Open Dental.
  - Permission `message:read`;
  - audit `patient.search` (staff, count).
- **Columns:**
  - failed time;
  - message type (Confirmation / Reschedule notice / Cancel notice / Reminder);
  - patient (name, and phone ending in 4567);
  - appointment time;
  - reason in plain words (§6.7);
  - what to do;
  - **Acknowledge**.
- **Default filter:** FAILED, not acknowledged. A toggle shows SKIPPED messages with reasons staff may care about (`VERIFY_FAILED`, `NO_CONTACT`).
- The Home tile (P4-09) "Failed messages" links here.

### 6.7 Reason labels (frontend `lib/reason-labels.ts`)
| Code | Shown text | Suggested action |
|---|---|---|
| `RECIPIENT_UNREACHABLE` / `NOT_ON_WHATSAPP` | "The number isn't on WhatsApp or can't be reached." | "Call the patient and check the number." |
| `OUTSIDE_WINDOW` | "WhatsApp didn't allow this message right now." | "Call the patient if it's important." |
| `BLOCKED` / `OPTED_OUT` | "The patient stopped WhatsApp messages." | "No action needed." |
| `VERIFY_FAILED` | "We couldn't check the appointment in Open Dental before sending." | "Call the patient to remind them." |
| `NO_CONTACT` | "No WhatsApp number on file." | "Ask for a number at the next visit." |
| `APPT_CHANGED` / `APPT_MOVED` / `APPT_CANCELLED` | "The appointment changed, so the old message wasn't sent." | "No action needed." |
| other / unknown | "Message failed (code <code>)." | "Contact support if this repeats." |

The final provider-code list comes from P4-01 §6. A unit test fails if a code in P4-01's enum has no label.

## 7. Implementation guide
1. **Read** P2-22 (case model, registry, email queue), P1-13 (RBAC, masking), P1-07 (audit), P1-03 (tables), P4-01 §6.10, P4-03 / P4-04 reason codes, P4-09 (shell) and P0-08 (link).
2. **Migrations** (§6.4), with append-only grants and triggers for `callback_attempts` (same pattern as `audit_log`).
3. **Callback API** (§6.3):
   - repository queries use the console index;
   - decrypt contact fields only in the detail and list serializers, and only when `callback:read_contact` is present. Otherwise mask from the decrypted value in memory, and never return the raw value;
   - audit `callback.view_contact` once per detail view with contact (list views are covered by a single `callback.view_contact` with `count`);
   - transitions and attempts run in one transaction with audit (fail closed).
4. **Resend** in P2-22's email service (additive) and the endpoint.
5. **Activity API** (§6.5): one query for sessions in the window, then one query for audit rows of those session IDs (uses `ix_audit_session_actor`); map the outcomes in Python. AI-booked list with Open Dental batch reads.
6. **Messages enrichment** endpoint.
7. **Pages:** callbacks list and detail (with the polling hook `usePoll(url, 30_000)` that pauses when hidden), `/admin/cases/[id]` redirect, activity, AI-booked, failed messages. MSW mocks for all.
8. **Docs:** `docs/admin/callbacks.md` (how staff work a case: assign → call → record attempt → resolve; write details in the Open Dental commlog), `docs/admin/activity.md`.
9. **Config:** set `ADMIN_CONSOLE_BASE_URL` to `https://app.<domain>/admin` in each environment (P2-23 env).

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| Two staff change the same case at once | Second PATCH gets 409; page reloads the case and shows "Updated by Lisa a moment ago". |
| Case upgraded to URGENT while the list is open | Next poll moves it to the top; banner appears. |
| URGENT emergency case without contact yet | Contact shows "Not collected yet"; still pinned; staff can use PatNum if verified. |
| READ_ONLY opens a case | Contact masked; no action buttons; summary hidden (it may contain PHI) and shown as "Hidden for your role". |
| Decryption fails for a field | Field shows "Unavailable"; `security.decrypt_failed` audit (P1-05); rest of the case shows. |
| Resend while a send is queued | 409 "An email is already being sent." |
| Resend fails again | Case keeps `FAILED`; A-CB1 fires as usual (P2-22). |
| Reopen when another OPEN case exists for that session | 409 with a link to the open case. |
| Email link opened by a logged-out user | Login + MFA, then back to the case (P4-09 `returnTo`). |
| Email link for another clinic's case | 404 (P1-13 rule). |
| Open Dental down on AI-booked or failed messages pages | IDs and times shown; "Patient details unavailable right now". |
| Appointment no longer in Open Dental | Row shows status "Not found in Open Dental"; still reviewable. |
| Session without any audit outcome and still `ACTIVE` | Shown as "In progress". |
| Very large clinic history | Cursor paging; activity window max 31 days per request (422 beyond). |
| Tab hidden for hours | Polling paused; refreshes once when visible again. |

## 9. Security, HIPAA and PHI
- **PHI handled:**
  - callback contact name, phone, DOB, email, preferred time and situation summary (decrypted in memory for the response);
  - patient names and appointment details read from Open Dental for the AI-booked and failed-messages pages;
  - PatNum/AptNum.
- **Where PHI goes:** only to the authenticated staff browser over TLS, under MFA sessions (P1-13). Nothing is cached server-side.
- **Browser:** API responses carry `Cache-Control: no-store`. The React Query cache is cleared on logout and on idle logout (P4-09).
- **Never logged:** names, phones, DOBs, summaries or email addresses. Logs carry case IDs and codes only (P1-07 redaction).
- **Masking:** READ_ONLY never receives raw contact values. Masking happens on the server, and a test inspects the JSON.
- **Free text:** no new free-text fields. Contact attempts are codes. The activity log has no text (seed criterion).
- **Audit:**
  - `callback.view_contact`, `callback.status_change`, `callback.assign`, `callback.attempt`, `callback.reopen`, `callback.email_resend`;
  - `appointment.review`, `message.acknowledge` (P4-01);
  - `patient.search` for live lookups (staff actor, `count`).
- **Minimum necessary:** the list shows the contact needed to call back; the full summary is on the detail page only.
- **Access:** clinic-scoped queries, 404 on foreign IDs, and a permission on every route (P1-13 T10 default-deny test covers the new routes).

## 10. Testing
**Backend** (pytest):

| # | Case | Expected |
|---|---|---|
| B1 | List sort with mixed cases | URGENT OPEN first, then OPEN by age, CONTACTED, RESOLVED |
| B2 | READ_ONLY list and detail | Contact masked; summary absent; raw values not in the JSON |
| B3 | FRONT_DESK detail | Full contact; one `callback.view_contact` audit row |
| B4 | OPEN → CONTACTED → RESOLVED | Timestamps set; two `callback.status_change` audit rows |
| B5 | CONTACTED → OPEN via PATCH | 422 |
| B6 | Reopen as FRONT_DESK | 403; as ADMIN 200 + audit |
| B7 | Concurrent PATCH with an old `base_updated_at` | 409 |
| B8 | Attempt `APPOINTMENT_MADE` on OPEN | Attempt row + status CONTACTED in one transaction |
| B9 | `app_rw` UPDATE on `callback_attempts` | Permission denied |
| B10 | Resend on FAILED | `email_seq` +1, PENDING, one task; second resend → 409 |
| B11 | ETag unchanged | 304 |
| B12 | Activity mapping fixture (book, callback, emergency, abandoned sessions) | Outcomes and totals as in §6.5 |
| B13 | Activity response contains no name/summary keys (schema check against a PHI field list) | Pass |
| B14 | AI-booked with Open Dental down | `od_unavailable: true`, IDs present |
| B15 | Review twice | Idempotent; one audit row with the first time |
| B16 | Foreign-clinic case ID | 404 |
| B17 | Every P4-01/P4-03/P4-04 reason code has a label | Pass (frontend unit test reads the enum JSON) |

**Frontend** (Vitest):
- **F1:** polling pauses when hidden.
- **F2:** tab title count.
- **F3:** banner on URGENT.
- **F4:** transition buttons per status and permission.
- **F5:** masked contact rendering.
- **F6:** `/admin/cases/[id]` redirect.

**E2E** (Playwright):
- **E1:** FRONT_DESK opens the email link → logs in → case → assigns self → records "No answer" → records "Appointment made" → resolves; history shows all steps.
- **E2:** a failed email case → Resend → badge turns to "Sending".
- **E3:** ADMIN marks an AI booking reviewed; unreviewed count drops.
- **E4:** READ_ONLY sees masked contacts and no buttons.

```bash
cd backend && pytest tests/unit/admin/test_callbacks_api.py tests/unit/admin/test_activity_api.py tests/integration/admin -q
cd frontend && pnpm test && pnpm test:e2e -- callbacks activity messages
```

## 11. Acceptance criteria
- [ ] Urgent cases are pinned on top of the callbacks list (B1)
- [ ] Every status change, assignment, attempt, reopen and resend is audited (B3, B4, B6, B10)
- [ ] Cases move OPEN → CONTACTED → RESOLVED; only ADMIN can reopen; invalid transitions are rejected (B4–B6)
- [ ] Contact attempts are recorded with fixed outcome codes; no free-text note field exists (B8, schema check)
- [ ] READ_ONLY never receives raw contact data (B2)
- [ ] Unsent emails show a badge and can be resent exactly once at a time (B10, E2)
- [ ] The P0-08 email link opens the case after login (F6, E1)
- [ ] The list refreshes every 30 s while visible, shows the open count in the tab title and a banner for URGENT (F1–F3)
- [ ] The AI activity log shows outcomes per session with no free-text PHI (B12, B13)
- [ ] AI-booked appointments show live Open Dental details and can be marked reviewed (B14, B15, E3)
- [ ] Failed messages show the patient, a plain reason and a suggested action, and can be acknowledged (B17)

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI
- [ ] PR reviewed
- [ ] No PHI in logs
- [ ] Docs / README updated (`docs/admin/callbacks.md`, `docs/admin/activity.md`)
- [ ] Additive edits merged: P1-03 (tables, columns, index), P1-07 (audit actions), P1-13 (`callback:reopen`), P2-22 (`resend`), P2-23 env (`ADMIN_CONSOLE_BASE_URL`)

> **Additions (DECISIONS #278, #281):** (1) a callback whose PHI was blanked by the P5-12 retention job (`phi_purged_at` set) shows "Details removed under the retention policy" instead of contact fields; contact, attempt, resend and reopen actions are hidden for it. (2) The AI-booked list gets a **Report duplicate** action (ADMIN, FRONT_DESK) for patients the AI created who turn out to be duplicates; it writes audit `appointment.duplicate_reported` and feeds the P6-02 duplicate-patients KPI.

## 13. Hand-off
| Consumer | What it can rely on |
|---|---|
| P4-17 Phase 4 E2E | Callbacks list and failed-messages page for the "notify" steps |
| P5-07 UAT | Staff workflow pages to test with the clinic |
| P5-08 / P5-11 security tests | New routes, masking rule, audit actions |
| P6-02 KPI dashboard | Activity outcome mapping and totals query |
| P6 support | `docs/admin/callbacks.md` for clinic training |

## 14. Open questions
| Question | Owner | Needed by |
|---|---|---|
| Should "Mark reviewed" be limited to ADMIN instead of everyone who works cases? Proposed: ADMIN + FRONT_DESK (anyone with `callback:update` and `activity:read`) | Product owner, at the P0-01 follow-up | Before the pilot |
| Should a second email go out when an URGENT case stays OPEN for 30 minutes? (P2-22 open question 1) Proposed: not in the MVP; revisit with pilot data | Product owner | P6 review |

## 15. References
- Plan §2 (staff), §4.9 (callbacks), §7 (admin console)
- DECISIONS #41, #120, #203, #206, #207, #262, #266
- Related tasks: P0-08, P1-03, P1-05, P1-07, P1-13, P1-15, P2-22, P2-23, P4-01, P4-03, P4-04, P4-09, P4-13, P4-17, P5-07, P6-02
