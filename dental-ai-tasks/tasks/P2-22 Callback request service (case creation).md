---
id: P2-22
title: Callback request service (case creation), admin email sender and callback conversation flow
milestone: P2
epic: E2.5
size: L
labels: area:backend, area:ai, area:messaging, type:feature, phi
depends_on: P0-04, P0-08, P1-02, P1-03, P1-05, P1-07, P1-16, P1-19, P1-22, P2-01, P2-04, P2-05, P2-08, P2-20
status: approved
---

# P2-22: Callback request service (case creation), admin email sender and callback conversation flow

## 1. Summary
Build everything behind "our team will call you back" (plan §4.9). This task absorbs **P2-23 (admin email sender)** and **P2-24 (callback conversation flow)**, so it has three parts:

| Part | What it does |
|---|---|
| A. Case service | `CallbackService` creates and updates `callback_requests` (encrypted contact and situation, reason, urgency, status `OPEN`); one open case per session; registers the real `create_callback_request` tool handler |
| B. Admin email sender | Sends one email per case (plus one more if the case is upgraded to URGENT) through the P0-08 route (Gmail API, Workspace BAA, TLS, `link_only` by default) via the `callback-emails` Cloud Tasks queue; failures become unsent alerts |
| C. Conversation | The `CALLBACK_REQUEST` state: collects only what is missing, shows the callback confirmation card, creates the case and tells the patient when the team will call |

Done means:
- every §4.9 trigger ends in exactly one case per session, with all PHI fields encrypted;
- the admin email arrives within 1 minute on staging;
- failed sends appear as unsent alerts (and URGENT failures page on-call);
- the patient hears or reads the approved wording, including the response-time promise.

## 2. Why this matters
There is no live transfer (plan §4.9). Every conversation the AI can't finish — no slot, failed identification, Open Dental down, insurance or medical questions, complaints, emergencies — ends here. If a case is lost or its email never arrives, a patient (possibly in pain) is never called. Pilot KPIs: **callback emails delivered to admin 100%** (retried until sent, otherwise flagged), **≥ 70% bookings without callback** (so the callback must be a clean exit, not a dead end), **0 PHI in logs**.

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P2, Text Chat Receptionist**.
- **Cloud Tasks:** a Google Cloud queue that calls our HTTP endpoint and retries with backoff when it fails. Docs: <https://docs.cloud.google.com/tasks/docs/configuring-queues>.
- **Domain-wide delegation (Gmail):** a Workspace admin lets a service account send as one mailbox (`callbacks@`) with only the `gmail.send` scope. Docs: <https://developers.google.com/workspace/guides/create-credentials#domain-wide_delegation>.
- **What already exists:**
  - **P0-08** (approved): sender `callbacks@<company domain>`, TLS compliance rule, SPF/DKIM/DMARC; config `callback.admin_emails`, `after_hours_emails`, `email_mode` (`link_only` default, `full_details` only with `full_details_approval`); the two email templates; keyless delegation design (**Verify** before build); `case_id` must be random and opaque; link format `{ADMIN_CONSOLE_BASE_URL}/cases/{case_id}`.
  - **P1-03** (approved): table `callback_requests` (`patient_type`, `patnum`, `contact_name_enc`, `contact_phone_enc`, `contact_phone_bidx`, `reason_code` ∈ `BOOKING_FAILED`, `NO_SLOTS`, `IDENTITY_UNVERIFIED`, `INSURANCE_BILLING`, `CLINICAL_QUESTION`, `URGENT_DENTAL`, `PATIENT_REQUEST`, `SYSTEM_ERROR`, `OTHER`, `urgency`, `summary_enc`, `status`, `email_status`, `email_attempts`); contact columns NULLable for URGENT emergency cases (DECISIONS #203).
  - **P1-02** (approved): queue `callback-emails` (10 attempts, backoff 10 s → 300 s, 5 doublings, 6 h max) and `enqueue(queue, path, payload, task_id, schedule_time)`; IDs only in payloads; targets `/internal/tasks/<queue>` on the `run.app` URL.
  - **P1-05** (approved): `FieldCipher.encrypt/decrypt(…, ctx=EncContext)`, `blind_index(kind="phone", …)`.
  - **P1-07** (approved): audit actions `callback.create`, `callback.status_change`, `callback.email_sent`, `callback.email_failed`; `record_counter("dai.callback.created", …)`; alerting.
  - **P1-22** (approved): tool contract `create_callback_request(reason_code, urgency, summary)` → `{case_ref, promise}` (stub registered there; real handler here).
  - **P2-08** (approved): needs a confirmed `callback` card except emergency reasons and staff-only reasons; operation hash `{kind, session_id, reason_code, urgency, phone, callback_time}`; key `callback:{session_id}:{reason_code}`; budget 2 per session.
  - **P2-04** (approved): `confirm_callback` template and card (Name, Phone, Reason, Best time to call), `callback_created`, `read_back`.
  - **P2-05 / P2-01** (approved): slots `situation` (≤ 500), `callback_time` (≤ 120), names, phone, DOB, email.
  - **P2-20** (approved): `create_urgent()` / `update_contact()` interface and the four emergency reasons.
  - Reasons raised by other flows: see the registry in §6.

## 4. Scope
**In scope**
- Part A: `CallbackService`, reason registry, case ref generator, additive P1-03 columns, the real `create_callback_request` handler, staff-only cases.
- Part B: `AdminEmailSender` task handler, Gmail sender with keyless delegation, recipient choice (business hours vs after hours), both templates, outbox sweep job, unsent-email state and alerts.
- Part C: `CallbackHandler` for `CALLBACK_REQUEST`, response-time promise from config, templates.
- Tests for every §4.9 trigger.

**Out of scope** (and which task covers it)
- Console screens for cases, status changes (`CONTACTED` / `RESOLVED`) and the unsent-alerts list → P4-14 (reads the fields defined here)
- Editing `callback.*` config in the console → P4-13
- Workspace BAA, sender mailbox, DNS and TLS rule → P0-08 (done before staging)
- Emergency detection and scripts → P2-20
- Retention and deletion jobs for closed cases → P5 (retention task)

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P0-08 (approved) | Sender, delegation, templates | `FakeEmailTransport` records messages; dev uses a team test domain |
| P1-02 (approved) | Queue and `enqueue()` | `InlineTaskRunner` in tests calls the handler directly, simulating retries |
| P1-03 / P1-05 (approved) | Table and cipher | Alembic migration here; cleartext test keyset |
| P2-01 / P2-04 / P2-05 / P2-08 (approved) | State machine, card, slots, gateway | Their test doubles; `FakeLlmProvider` |
| P2-20 (approved) | Emergency calls into `create_urgent` | The interface is defined there and implemented here |
| P4-14 (not written) | Shows unsent alerts | Fields and query defined here; ops alert covers the gap |

## 6. Interface contract

### A. Reason registry (`backend/app/domain/callbacks/reasons.py`)
Every reason any flow may raise. `category` is the P1-03 `reason_code`; `detail` is stored in the new `reason_detail` column.

| `detail` (raised by) | `category` | Default urgency | Staff label (console, `full_details` email) | Needs patient contact | Card |
|---|---|---|---|---|---|
| `human_requested` (P0-04) | `PATIENT_REQUEST` | ROUTINE | Asked to speak to a person | yes | yes |
| `not_understood_limit` (P2-01) | `OTHER` | ROUTINE | AI could not understand the request | yes | yes |
| `identity_needs_staff`, `verification_locked`, `match_multiple_unresolved` (P2-12) | `IDENTITY_UNVERIFIED` | ROUTINE | Could not verify identity | yes | yes |
| `registration_needs_staff` (P2-15) | `IDENTITY_UNVERIFIED` | ROUTINE | New patient needs staff to register | yes | yes |
| `voice_capture_failed` (P3-09, DECISIONS #240) | `OTHER` | ROUTINE | Details could not be captured by voice | yes | yes |
| `guarantor_link` (P2-15) | `OTHER` | ROUTINE | Link minor to guarantor in Open Dental | no (staff-only) | no |
| `not_bookable_by_ai`, `booking_needs_confirmation`, `change_needs_confirmation`, `reschedule_needs_staff` (P2-16, P2-18) | `BOOKING_FAILED` | ROUTINE | Booking / change needs staff | yes | yes |
| `no_suitable_slot` (P2-16) | `NO_SLOTS` | ROUTINE | No suitable time found (preference attached) | yes | yes |
| `inside_notice_window` (P2-18) | `PATIENT_REQUEST` | ROUTINE | Change requested inside the notice window | yes | yes |
| `insurance_question` (P2-18) | `INSURANCE_BILLING` | ROUTINE | Insurance or billing question | yes | yes |
| `medical_question` (P2-04 `no_medical_advice`) | `CLINICAL_QUESTION` | ROUTINE | Question needing a dentist | yes | yes |
| `complaint` (P2-05) | `PATIENT_REQUEST` | ROUTINE | Complaint | yes | yes |
| `od_unavailable`, `system_error`, `budget_exceeded` (P0-04, P2-08) | `SYSTEM_ERROR` | ROUTINE | System problem during the request | yes | yes |
| `emergency_tier1`, `emergency_crisis`, `emergency_uncertain`, `emergency_tier2_no_slot` (P2-20) | `URGENT_DENTAL` | URGENT | Emergency: 911 advised / crisis / possible emergency / urgent, no slot | optional (collected after) | no |

A test fails if any reason string used in `flows/` is missing from the registry.

### A. Data (additive to P1-03, DECISIONS #207)
| Column | Type | PHI | Meaning |
|---|---|---|---|
| `case_ref` | text, UNIQUE (`clinic_id`, `case_ref`) | - | Patient-facing reference, `CB-` + 6 random Crockford base32 chars (not derived from any data) |
| `reason_detail` | text | - | Registry `detail` of the first reason |
| `extra_reasons` | text[] | - | Later reasons in the same session, in order |
| `contact_dob_enc` | bytea NULL | P | DOB when the patient is not verified |
| `contact_email_enc` | bytea NULL | P | Optional email |
| `preferred_time_enc` | bytea NULL | P | Best time to call (patient's words, ≤ 120) |
| `email_seq` | int NOT NULL DEFAULT 1 | - | Emails due for this case (1, or 2 after an URGENT upgrade) |
| `email_sent_seq` | int NOT NULL DEFAULT 0 | - | Emails sent |
| `email_last_error` | text NULL | - | Error code only (e.g. `gmail_5xx`, `recipient_rejected`) |
| `email_sent_at` | timestamptz NULL | - | Last successful send |
| `upgraded_at` | timestamptz NULL | - | When urgency rose to URGENT |
- Partial unique index `ux_callback_open_session` on (`session_id`) WHERE `status = 'OPEN' AND session_id IS NOT NULL` — one open case per session (DECISIONS #206).
- `email_status` gains no new values: `PENDING` / `SENT` / `FAILED`. Staff-only cases also email (they are work for staff).

### A. Case service (`backend/app/domain/callbacks/service.py`)
```python
class CallbackContact(BaseModel):
    patient_type: Literal["NEW", "EXISTING", "UNKNOWN"]
    pat_num: int | None = None
    name: str | None = None                  # "Jane Doe"
    phone_e164: str | None = None
    dob: date | None = None
    email: str | None = None

class CaseInput(BaseModel):
    session_id: uuid.UUID
    reason_detail: str                       # registry key
    urgency: Literal["ROUTINE", "URGENT"] | None = None   # None → registry default
    contact: CallbackContact
    situation_text: str | None = None        # patient's own words, ≤ 500 (DECISIONS #206)
    context_line: str | None = None          # built by code, e.g. "Preference: mornings, Dr. Lee" / "Appointment: Tue Dec 8 9:00 AM"
    preferred_time: str | None = None

class CaseResult(BaseModel):
    case_id: uuid.UUID
    case_ref: str
    created: bool                            # False when merged into the session's open case
    urgency: Literal["ROUTINE", "URGENT"]
    email_due: bool

class CallbackService:
    async def create(self, inp: CaseInput, ctx: ToolContext) -> CaseResult: ...
    async def create_urgent(self, *, session_id, reason, pat_num, contact_name, contact_phone_e164,
                            situation: EmergencySituation) -> str: ...          # P2-20 interface → case_ref
    async def update_contact(self, case_ref: str, *, contact_name: str, contact_phone_e164: str) -> None: ...
# Addition (P4-13a, DECISIONS #266): CallbackEmailService.resend(case_id) -> int  # email_seq += 1, email_status = PENDING,
#   enqueue one task named (case_id, email_seq); 409 if already PENDING. Used by the console Resend button.
# ADMIN_CONSOLE_BASE_URL = https://app.<domain>/admin; the console route /admin/cases/{case_id} redirects to the case page.
```
`create` rules, in one DB transaction:
1. Validate: `reason_detail` in the registry; contact required unless the reason is staff-only or emergency.
2. `SELECT … FOR UPDATE` the session's `OPEN` case.
   - **None** → insert with status `OPEN`, `email_status = PENDING`, `email_seq = 1`; `created=True`.
   - **Exists, same reason** → no change (idempotent); return it.
   - **Exists, new reason** → append to `extra_reasons`; fill empty contact fields; append the new situation to the summary (encrypted); if the new urgency is URGENT and the case was ROUTINE → set URGENT, `upgraded_at`, `email_seq += 1`, `email_status = PENDING` (one more email). No other change sends a new email.
3. Summary (`summary_enc`) is built by code (no LLM, DECISIONS #206):
   ```
   Reason: No suitable time found
   Context: Preference: weekday mornings · Dr. Lee
   Patient said: "I can only come before work, around 7."
   ```
   Emergency cases: `Reason: Emergency: possible emergency (911 advised) · Facial swelling` + `Patient said: "…"`.
4. Encrypt every PHI field with `EncContext(table="callback_requests", column=…, clinic_id=…)`; phone blind index `kind="phone"`.
5. After commit: `enqueue("callback-emails", "/internal/tasks/callback-emails", {"case_id": str(id), "seq": email_seq}, task_id=f"cbmail-{id}-{email_seq}")`. Enqueue failure is logged; the sweep (Part B) picks it up.
6. Audit `callback.create` (details `reason_detail`, `category`, `urgency`, `merged`) or `callback.status_change` (`upgraded`). Counter `dai.callback.created` (`category`, `urgency`, `merged`).

**Tool handler** `create_callback_request` (replaces the P1-22 stub): args from the handler (never from the model) — `reason_code` (registry `detail`), `urgency`, `summary` → builds `CaseInput` from slot memory and the principal; returns `{case_ref, promise}`. Idempotency key `callback:{session_id}:{reason_code}` (P2-08).

### B. Admin email sender (`backend/app/integrations/email/`)
```python
class EmailMessage(BaseModel):
    to: tuple[str, ...]
    subject: str
    body_text: str

class EmailTransport(Protocol):
    async def send(self, msg: EmailMessage) -> str: ...      # returns provider message id
    # raises EmailTemporaryError (5xx, 429, timeout) or EmailPermanentError (4xx recipient/auth/format)

class GmailTransport(EmailTransport): ...    # users.messages.send as ADMIN_EMAIL_SENDER via keyless delegation (P0-08; Verify)

# POST /internal/tasks/callback-emails   body {"case_id": "...", "seq": 1}   (Cloud Tasks OIDC auth, internal only)
async def handle_callback_email(payload: dict, retry_count: int) -> Response: ...
```
Handler steps:
1. Load the case `FOR UPDATE`. If `email_sent_seq >= seq` → 200 (already sent; at-least-once safe).
2. **Recipients:** `after_hours_emails` when now (clinic tz) is outside `hours` or on a holiday, else `admin_emails` (P0-08).
3. **Render** (P0-08 templates). Subject:
   - `[ACTION NEEDED] Patient callback request – Normal – Case {case_id}`
   - `[ACTION NEEDED] Patient callback request – URGENT – Case {case_id}`
   - `[ACTION NEEDED] Patient callback request – URGENT (911 advised) – Case {case_id}` for `emergency_tier1` / `emergency_crisis` (P2-20 open question 2)
   - an upgrade email adds `(upgraded to URGENT)`.
   `link_only` body has no PHI. `full_details` (only with approval) decrypts fields in memory and follows plan §4.9; the subject never contains PHI in either mode.
4. **Send.** Success → `email_sent_seq = seq`, `email_status = SENT`, `email_sent_at`, audit `callback.email_sent` (`attempt`), counter `dai.callback.email` (`result=sent`).
5. **Temporary error** → `email_attempts += 1`, `email_last_error`; return 503 so Cloud Tasks retries (P1-02 queue: 10 attempts, 10 s → 300 s, ≈ 25 min). On the last attempt (`retry_count >= 9`) → `email_status = FAILED`, audit `callback.email_failed`, alert A-CB1; return 200.
6. **Permanent error** → `FAILED` at once, audit, alert A-CB1; return 200 (no useless retries).
7. **URGENT case, first attempt failed** → page on-call immediately (A-CB2), while retries continue (DECISIONS #206).

**Outbox sweep** (additive Cloud Scheduler job in P1-02): `callback-email-sweep`, every 2 minutes, `POST /internal/jobs/callback-email-sweep` → re-enqueues cases with `email_status = PENDING` and `email_sent_seq < email_seq` older than 2 minutes (same `task_id`, so no duplicates). **Verify:** how long Cloud Tasks keeps a task name reserved after it completes (dedup window), and that re-enqueue of a finished name fails cleanly (treat "already exists" as success).

**Unsent alerts:** cases with `email_status = FAILED` are the console's "unsent alerts" list (P4-14 query: `WHERE clinic_id = ? AND email_status = 'FAILED' ORDER BY urgency DESC, created_at`). Staff can still see every case in the console regardless of email.

### C. Conversation (`flows/callback.py`, `CallbackHandler`)
The triggering flow fires its event with `flags.callback_reason = <detail>` (and, for emergencies, P2-20 calls `create_urgent` directly — this handler is not used for Tier 1 / crisis / uncertain / tier-2-no-slot).

**On enter:**
1. **Staff-only reason** (`guarantor_link`) → create at once (no card, P2-08 exception); no patient wording here (P2-15 owns it); return to the previous flow.
2. **Offer step** for reasons where the patient was only offered a callback (`faq_unknown`, `insurance_question`, `inside_notice_window`, `budget_exceeded`, `not_changeable`): the triggering flow already asked "Would you like our team to call you?"; "no" never reaches this state.
3. **Contact** — ask only what is missing (DECISIONS #205):

   | Patient | Collected |
   |---|---|
   | Verified (active patient) | Name and phone from Open Dental (P1-16 `get`, not shown until the card); question `callback_phone_on_file`: "Should our team call you at the number ending in {last4}?" with choices "Yes" / "Use a different number" |
   | Not verified, says existing | First and last name, phone, date of birth |
   | New patient | First and last name, phone, date of birth; one optional `callback_email_ask` with a "Skip" choice |

   Address, WhatsApp number and contact preferences are **not** collected (staff ask on the call).
4. **Situation:** asked only for `human_requested`, `not_understood_limit`, `medical_question`, `complaint`, `insurance_question` ("In a few words, what would you like our team to help with?"). Other reasons already carry a code-built context line (preference, appointment, topic).
5. **Best time:** `callback_time_ask` with choices "Morning", "Afternoon", "Any time" (free text accepted, ≤ 120 chars).
6. **Card:** `confirm_callback` (P2-04 #174) with rows Name, Phone, Reason (staff label shortened for patients, e.g. "No suitable time found"), Best time to call, and Urgency when URGENT. Voice: the phone is read digit by digit (`read_back` rules). `change` → back to the field (`change_target`: `name`, `phone`, `callback_time`).
7. `yes` → `create_callback_request` (gateway: `confirmation_recorded`) → reply `callback_created` + promise → `WRAP_UP` ("Is there anything else I can help you with today?").
8. Patient says they no longer want a callback before the card → `anything_else`; nothing created.

**Promise text** (P1-19 `callback` keys `promise_business` and `promise_urgent` already exist; `promise_urgent_after_hours` is additive; console-editable in P4-13; DECISIONS #206, P0-01 B6):
```yaml
callback:
  promise_business: "Our team will call you back within one business day."
  promise_urgent: "I've marked this as urgent. Our team will call you back today."
  promise_urgent_after_hours: "I've marked this as urgent. Our team will call you as soon as the office opens."   # new
```
Rules: plain text, ≤ 200 chars, no placeholders other than `{clinic_name}`; English only.

### C. Templates (added to P2-04)
| Intent | Text |
|---|---|
| `callback_phone_on_file` | "Should our team call you at the number ending in {last4}?" |
| `callback_situation_ask` | "In a few words, what would you like our team to help with?" |
| `callback_time_ask` | "When is the best time to call you?" (choices) |
| `callback_email_ask` | "Would you like to add an email address? It's optional." (choice "Skip") |
| `confirm_callback` | (P2-04) |
| `callback_created` | "Thank you, {first_name}. I've noted your request, and our team will contact you at {phone_masked}. {promise} Your reference is {case_ref}." |
| `anything_else` | (P2-18) |

`{phone_masked}` = `(•••) •••-0123` in text; voice says "the number ending in 0 1 2 3". `{first_name}` comes from the card's confirmed value. All wording is reviewed by the product owner (acceptance: "patient message matches approved wording" = snapshot tests).

### §4.9 trigger coverage
| Plan §4.9 trigger | Event / reason |
|---|---|
| Asks for a person | `human_requested` |
| Not understood after repeated attempts | `not_understood_limit` |
| Identification fails / several records match | `identity_needs_staff`, `verification_locked`, `match_multiple_unresolved` |
| Scheduling conflict unresolved / no suitable slot | `no_suitable_slot`, `booking_needs_confirmation`, `not_bookable_by_ai` |
| Open Dental unavailable / booking, rescheduling or cancellation fails | `od_unavailable`, `change_needs_confirmation`, `reschedule_needs_staff`, `system_error` |
| Insurance or billing questions | `insurance_question` |
| Questions needing medical judgment | `medical_question` |
| Complaints, sensitive or complex requests | `complaint` |
| Urgent (Tier 2) with no urgent slot | `emergency_tier2_no_slot` (P2-20) |
| Tier 1 emergency (also a case) | `emergency_tier1` (P2-20) |

### Audit, metrics, alerts (no PHI)
| Item | Fields |
|---|---|
| `callback.create`, `callback.status_change`, `callback.email_sent`, `callback.email_failed` (P1-07) | `reason_detail`, `category`, `urgency`, `merged`, `attempt`, `error_code` |
| `dai.callback.created` (counter) | `category`, `urgency`, `merged`, `channel` |
| `dai.callback.email` (counter, additive to P1-07's list) | `result` (`sent` / `retry` / `failed`), `mode` |
| `dai.callback.email_latency_s` (histogram) | case created → email sent |
| **A-CB1** (alert, ticket) | any `email_status = FAILED` |
| **A-CB2** (page) | URGENT case: first email attempt failed, or still unsent after 5 minutes |
| **A-CB3** (alert) | PENDING older than 10 minutes (queue or sweep broken) |

## 7. Implementation guide
1. **Migration** (with P1-03's owner): §6 columns, partial unique index, `idempotency_keys.operation` `CALLBACK` (from P2-08).
2. **Registry and service** (Part A) with unit tests for merge, upgrade and idempotency; register the real tool handler; wire P2-20's `create_urgent` / `update_contact`.
3. **Email transport.** Implement `GmailTransport` after **verifying** P0-08's keyless delegation design in dev (`docs/integrations/admin-email.md`). `FakeEmailTransport` for tests.
4. **Task handler and sweep.** `/internal/tasks/callback-emails` (OIDC check as for other internal endpoints), Scheduler job `callback-email-sweep` (Terraform in P1-02's module, additive).
5. **Alerts** A-CB1..3 in the P1-07 alerting setup.
6. **Conversation** (Part C): `CallbackHandler`, templates, `promise_urgent_after_hours` (P1-19 additive), `choice_id` mapping for time choices.
7. **Trigger tests**: one integration test per row of the §4.9 table, from the triggering state to an `OPEN` case and an email in the fake transport.
8. **Staging check:** `scripts/smoke/callback_e2e.py` creates a synthetic case through the chat and measures time to the email arriving in a team test mailbox (target ≤ 60 s); also forces a permanent failure (invalid recipient on a test clinic) and checks the unsent state and alert.
9. **Docs:** `docs/flows/callback.md`, `docs/runbooks/callback-email-unsent.md` (how staff and on-call handle A-CB1/A-CB2). Notify P4-13, P4-14, P5 retention.

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| Patient asks for a person twice in one session | Same reason → same case; no second email |
| `no_suitable_slot` case, then a complaint in the same session | Reason appended to the open case; no new email (still ROUTINE) |
| ROUTINE case, then a Tier 2 no-slot emergency | Case upgraded to URGENT; second email "(upgraded to URGENT)"; page if it fails |
| Two browser tabs race to create | Row lock + partial unique index → one case |
| Verified patient's Open Dental phone missing | Ask for a phone like an unverified patient |
| Patient refuses to give a phone (non-emergency) | No case; reply explains the team needs a number to call; offer the clinic's phone from `clinic.public_phone_e164` |
| Open Dental down (`od_unavailable`) for a verified patient | Name and phone cannot be fetched → ask for them |
| Email: recipient rejected (permanent) | `FAILED` at once, A-CB1; case visible in the console |
| Email: Gmail 5xx for 25 minutes | Retries, then `FAILED`, A-CB1; URGENT also A-CB2 at first failure |
| Enqueue failed after commit | Sweep re-enqueues within ~2 minutes |
| Crash after Gmail accepted but before DB update | Possible duplicate email on retry (accepted, rare); documented in the runbook |
| After-hours URGENT case | `after_hours_emails`; promise `promise_urgent_after_hours` |
| `full_details` configured without approval | Treated as `link_only` (P0-08 load rule) |
| Session expires after the card but before "yes" | Nothing created; the next session starts fresh |
| Budget: 3rd callback attempt in a session | P2-08 budget (2) → merged case already exists; reply `callback_created` with the existing ref |
| Child added by a parent (household) | Contact is the parent's (verified) phone; card's Name row is the parent; the situation mentions the child only if the parent said so |
| Situation text contains instructions ("ignore rules") | Stored as data, encrypted; never sent to the LLM again; email `link_only` |

## 9. Security, HIPAA and PHI
- **PHI handled:** contact name, phone, DOB, email, best time, situation text, PatNum, reason (health-related for medical and emergency reasons).
- **Stored:** only in `callback_requests` encrypted columns (P1-05, associated data bound to table/column/clinic); phone blind index for staff search.
- **Email:** `link_only` by default — no PHI in the email or subject; `full_details` only with written approval (P0-08); TLS enforced to clinic domains; sender mailbox not used interactively.
- **Queue payloads:** case ID and sequence only.
- **Never logged:** any contact field, situation, best time, rendered email body, recipients' local parts (log the domain only).
- **Access:** cases are read only through the console with MFA and RBAC (P4-14); `case_ref` and `case_id` are random and reveal nothing.
- **Audit:** every create, merge, upgrade, email sent and failed.

## 10. Testing
```bash
cd backend && pytest tests/unit/domain/callbacks tests/unit/integrations/email tests/unit/orchestrator/flows/test_callback.py -q
pytest tests/integration/callback -q                   # Postgres + InlineTaskRunner + FakeEmailTransport
python scripts/smoke/callback_e2e.py --env staging     # real Gmail route to a team test mailbox
```
| # | Case | Expected |
|---|---|---|
| T1 | Create: verified patient, `no_suitable_slot` | One OPEN case, encrypted fields, context line, email enqueued |
| T2 | Duplicate same reason | Same case, no second email |
| T3 | New reason in the same session | Appended; no new email |
| T4 | Upgrade ROUTINE → URGENT | `email_seq=2`; second email with "(upgraded to URGENT)" |
| T5 | Concurrent creates | One case (index + lock) |
| T6 | Encryption | Dump of the row shows no plaintext; decrypt with wrong context fails |
| T7 | Every §4.9 trigger (table rows) | Case with the right category and detail |
| T8 | Registry completeness | Every reason string in `flows/` is in the registry |
| T9 | Email sent, link_only | Subject and body contain no PHI (PHI corpus check) |
| T10 | full_details with approval | Plan §4.9 fields present; subject still without PHI |
| T11 | After hours | `after_hours_emails` used |
| T12 | Temporary failures then success | Retries; SENT; attempts counted |
| T13 | 10 temporary failures | FAILED, audit, A-CB1 |
| T14 | Permanent failure | FAILED at first attempt, no retry |
| T15 | URGENT first failure | A-CB2 page fired |
| T16 | Enqueue failed | Sweep sends within one sweep cycle |
| T17 | Conversation: verified, phone on file | Asks only "number ending in …", best time, card, case, promise |
| T18 | Conversation: new patient | Name, phone, DOB, optional email, best time, card |
| T19 | Card change (phone) | Back to phone; new card; hash matches |
| T20 | Wording snapshots | `callback_created` and promises match the approved text exactly |
| T21 | Staff-only `guarantor_link` | Case without card or patient contact; email sent |
| T22 | Emergency `create_urgent` without contact, then `update_contact` | URGENT case with NULL contact, later filled |
| T23 | Log capture with PHI corpus | No PHI in logs |
| T24 | Staging smoke | Email arrives ≤ 60 s; forced failure shows FAILED and alert |

## 11. Acceptance criteria
- [ ] Duplicate requests in one session give one case; a new reason merges; only an URGENT upgrade sends a second email (T2–T5)
- [ ] All PHI fields are encrypted; the email in `link_only` mode contains no PHI (T6, T9)
- [ ] The admin email arrives within 1 minute on staging (T24)
- [ ] Failed sends end as `FAILED` and appear as unsent alerts; URGENT failures page on-call (T13–T15, T24)
- [ ] Every §4.9 trigger is covered by a test (T7)
- [ ] The patient message matches the approved wording, including the response-time promise from config (T17, T18, T20)
- [ ] Only missing details are asked; verified patients are not asked for name or DOB again (T17)
- [ ] No PHI in logs (T23)

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI; staging smoke linked in the PR
- [ ] PR reviewed (HIPAA review: labelled `phi`)
- [ ] No PHI in logs
- [ ] `docs/flows/callback.md` and `docs/runbooks/callback-email-unsent.md` written; additive changes to P1-02, P1-03, P1-07 and P1-19 merged
- [ ] P4-13, P4-14 and P5 retention issues notified

## 13. Hand-off
| Consumer | What they can rely on |
|---|---|
| P2-12, P2-15, P2-16, P2-18 | Every reason in the registry ends in a case with the right category; `flags.callback_reason` contract |
| P2-20 | `create_urgent` / `update_contact` implemented; URGENT emails with "(911 advised)" for Tier 1 / crisis |
| P4-14 Cases console | Columns, status values, `case_ref`, unsent-alert query, `extra_reasons`, `upgraded_at` |
| P4-13 Callback settings | `callback.promise_business`, `promise_urgent`, `promise_urgent_after_hours` and their rules (plus P0-08 keys) |
| P5 hardening | Alerts A-CB1..3, runbook, at-least-once note |

## 14. Open questions
| # | Question | Recommended answer | Owner |
|---|---|---|---|
| 1 | Should a second email be sent when staff haven't opened an URGENT case after 30 minutes? | Not in the MVP; the A-CB2 page covers send failures, and the console sorts URGENT first. Revisit in the pilot. | Product owner |
| 2 | Should the patient get a WhatsApp or email copy of the case reference? | No in the MVP (no consent step for it); the reference is shown in the chat. | Product owner |
| 3 | Should closed cases' encrypted details be deleted after a retention period? | Yes; the period is set by the P5 retention task with the compliance advisor (Proposed: 90 days after `RESOLVED`). | Compliance advisor |

## 15. References
- Plan: §4.4, §4.9, §5, §6, §7, §11
- P0-01 Q4b, B6; P0-08 templates and delegation design
- DECISIONS: #75, #174, #179, #189, #203, #205, #206, #207
- Related tasks: P0-04, P0-08, P1-02, P1-03, P1-05, P1-07, P1-16, P1-19, P1-22, P2-01, P2-04, P2-05, P2-08, P2-12, P2-15, P2-16, P2-18, P2-20, P4-13, P4-14
- Cloud Tasks retry configuration: <https://docs.cloud.google.com/tasks/docs/configuring-queues>
- Gmail API `users.messages.send`: <https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/send>
