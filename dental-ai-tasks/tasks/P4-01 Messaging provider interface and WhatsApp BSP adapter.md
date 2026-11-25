---
id: P4-01
title: Messaging provider interface + WhatsApp adapter, delivery webhooks, retries and STOP
milestone: P4
epic: E4.1
size: L
labels: area:messaging, type:feature, phi
depends_on: P0-07, P0-07a, P0-15, P1-02, P1-03, P1-05, P1-07, P1-13
status: approved
---

# P4-01: Messaging provider interface + WhatsApp adapter, delivery webhooks, retries and STOP

> Consolidated task (#50). It absorbs P4-06 "Delivery webhooks, retries and failure alerts" and P4-07 "Opt-out handling (STOP)" (see `tasks/_CONSOLIDATION.md`). The title says "WhatsApp adapter" instead of "WhatsApp BSP adapter" because the adapter speaks the WhatsApp Cloud API format, which the BSP chosen in P0-07 must support (**Verify**).

## 1. Summary
Build the layer that sends every patient message (booking confirmation, 1-hour reminder, reschedule and cancel notices) and receives everything the messaging provider sends back. It has five parts:

1. **`MessagingProvider` interface**, with a `WhatsAppCloudProvider` adapter and a `FakeProvider` for dev and tests. The provider is chosen by config, so it can be swapped.
2. **`MessageSender`**, which puts every send through a policy gate (G1–G8): the channel must be allowed in `messaging_policy.yaml`, the template must be approved, only allowed fields can be used, and the patient's consent must be on record. Only then does it call the provider.
3. **`outbound_messages` table**, which tracks each message: queued, sent, delivered, read, failed or skipped.
4. **Webhook endpoint** `POST /v1/webhooks/messaging/whatsapp`. It checks the signature on every call and updates delivery status idempotently.
5. **Inbound keyword handling.** STOP revokes consent and cancels pending reminders, START restores consent, and HELP replies with help text. Any other reply is not stored and gets one fixed auto-reply.

The task is done when:
- the sender refuses any template or field the policy doesn't allow;
- a forged webhook gets a 403;
- a final failure shows up in the failed-messages API and raises an alert;
- STOP revokes consent and cancels the jobs (test).

## 2. Why this matters
Plan §4.7 promises a confirmation right after booking and a reminder 60 minutes before the visit, both only with consent. Every one of these messages goes through this task.

This task is also the main place where messaging can leak PHI. A message that names a procedure, or that goes to the wrong number or to someone who opted out, is a privacy incident (P0-11 risk R09). The policy gate makes these mistakes impossible in code instead of relying on reviewers.

Without delivery tracking, staff never learn that a reminder failed (plan §4.7: "alert the admin in the console after the final failure").

Without STOP handling, we would keep messaging patients who asked us to stop. That breaks the consent rules and creates TCPA risk.

Blocked without this task: P4-02 (consent capture), P4-03 (confirmation, reschedule and cancel notices), P4-04 (reminders), P4-13 (failed-messages screen) and P4-17 (end-to-end test).

**Channel decision (DECISIONS #252).** The user chose WhatsApp as the channel to build. Meta states the WhatsApp Business Platform "is not HIPAA compliant" (DECISIONS #35), so **what** a message may contain is still decided by the compliance advisor through `messaging_policy.yaml` (P0-07a). The default content mode is `phi_free_nudge`: a message with no name, no date and no time. `minimal_phi` is used only after the advisor writes it into the policy file.

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P4, WhatsApp, Reminders & Admin Console**.
- **WhatsApp Cloud API:** Meta's HTTP API for sending WhatsApp messages from a business phone number. Messages go to `POST https://graph.facebook.com/<version>/<PHONE_NUMBER_ID>/messages`. A **BSP** (Business Solution Provider) helps a business get onto the platform and may bill for it. **Verify** with P0-07 that the chosen BSP lets us call the Cloud API format directly. If it doesn't, write a second adapter behind the same interface (§6).
- **Templates and the 24-hour window:** a message the business starts (confirmation, reminder) must use a **pre-approved template**. Free-form text is allowed only within 24 hours after the user's last message to us; otherwise the API returns error **131047**: "More than 24 hours have passed since the recipient last replied to the sender number." (https://developers.facebook.com/documentation/business-messaging/whatsapp/support/error-codes). Our system replies (STOP, START and HELP confirmations, the auto-reply) are always answers to a message the patient just sent, so they are inside the window.
- **Template categories:** we use **utility** templates only (P0-15 rule T10).
- **Webhooks:** Meta calls our HTTPS endpoint with delivery statuses and inbound messages.
  - **Signature:** Meta signs every payload with SHA-256 using the app's **App Secret** and sends it in the `X-Hub-Signature-256` header, prefixed with `sha256=`. We compute HMAC-SHA256 over the raw body and compare (https://developers.facebook.com/docs/graph-api/webhooks/getting-started, "Validating Payloads").
  - **Endpoint verification:** on setup Meta sends `GET ?hub.mode=subscribe&hub.challenge=<int>&hub.verify_token=<string>`. We must check the token and echo the challenge.
  - **Retries:** if we answer with anything other than 200, Meta "retries delivery with decreasing frequency until the request succeeds, for up to 7 days", and "these retries can result in duplicate webhook notifications". So our handler must be idempotent. Payloads are up to 3 MB (https://developers.facebook.com/documentation/business-messaging/whatsapp/webhooks/overview).
- **Status webhook:** `entry[].changes[].value.statuses[]` holds `id` (the WhatsApp message ID, `wamid…`), `status`, `timestamp`, `recipient_id`, an optional `biz_opaque_callback_data` (a string we set when sending) and `errors[]` with `code`.
  - Status values cover sent, delivered, read and failed.
  - Meta notes that a message can be delivered and read at the same moment, and then no "delivered" webhook is sent. So status handling must accept skipped steps.
  - The payload can also contain the user's WhatsApp profile name in `contacts[].profile.name`. That is PHI and is never stored or logged.
  - Source: https://developers.facebook.com/documentation/business-messaging/whatsapp/webhooks/reference/messages/status.
- **Error codes we act on** (same error-codes page):

  | Code | Meaning (short) |
  |---|---|
  | 131026 | Unable to deliver (not a WhatsApp number, old app, terms not accepted) |
  | 131047 | 24-hour window closed |
  | 131050 | User stopped marketing messages |
  | 131056 | Too many messages to the same number in a short time (wait and retry) |
  | 130429 | Throughput limit hit |
  | 80007 | Business account rate limit |
  | 4 | App rate limit |
  | 131000 | Unknown error, try again |
  | 131016 | Service temporarily unavailable |
  | 132000 | Template parameter count mismatch |
  | 132001 | Template doesn't exist or isn't approved |
  | 132015 | Template paused for low quality |
  | 132016 | Template permanently disabled |
  | 131008 | Missing required parameter |
  | 131009 | Invalid parameter value |
  | 133010 | Business phone number not registered |
  | 368, 131031 | Business account restricted |
- **No carrier-level STOP on WhatsApp.** With SMS, carriers and providers handle "STOP" for you. WhatsApp has no such feature for utility messages, so **we** must read inbound text and treat opt-out keywords ourselves (DECISIONS #253).
- **Consent (P1-03):** `consents` is an append-only history and `current_consents` is the latest row per (clinic, address hash, channel, purpose). A message may be sent only if the current action is `GRANTED`. Addresses are found by **blind index** (`messaging_address_bidx`, HMAC-SHA256 of the E.164 number; P1-03, P1-05).
- **Policy and templates as files:**
  - `docs/compliance/messaging_policy.yaml` (P0-07a) says which channel is allowed, in which **mode**, for which message type, with which fields, plus `never_allowed_fields`;
  - `docs/messaging/templates.yaml` (P0-15) holds the template bodies;
  - `scripts/messaging/check_templates.py` (P0-15) validates the templates against the policy. This task runs the same checks at service startup.
- **Cloud Tasks retries (P1-02):** P4-03 and P4-04 call `MessageSender.send()` from Cloud Tasks handlers on the `notifications` and `reminders` queues. If the handler returns a non-2xx response, Cloud Tasks retries with backoff, up to the queue's `max_attempts`.

New glossary terms: WhatsApp Cloud API, 24-hour customer service window, `X-Hub-Signature-256`, `wamid`, `biz_opaque_callback_data`, content mode (`phi_free_nudge` / `minimal_phi`), policy gate, `outbound_messages`, system reply.

## 4. Scope
**In scope**
- `backend/app/integrations/messaging/`: the `MessagingProvider` protocol, `WhatsAppCloudProvider`, `FakeProvider`, the provider registry and error classification.
- `backend/app/domain/messaging/`:
  - `MessageSender` with policy gate G1–G8;
  - `PolicyStore` (loads and validates the policy and templates at startup);
  - the renderer;
  - `InboundHandler` (STOP, START, HELP, other);
  - `StatusUpdater`.
- DB: the `outbound_messages` table, plus two new consent sources `WHATSAPP_STOP` and `WHATSAPP_START` (Alembic migration; additive to P1-03).
- Endpoints:
  - `GET` and `POST /v1/webhooks/messaging/whatsapp` (public, through the load balancer);
  - `GET /v1/admin/messages` and `POST /v1/admin/messages/{id}/acknowledge` (staff API for the failed-messages list).
- Retry rules: transient vs permanent errors, behaviour on the last attempt, and webhook idempotency.
- STOP/START/HELP keyword handling, including cancelling pending reminders on STOP.
- Metrics, alerts A-M1 and A-M2, and audit events `message.*` and `consent.*` for STOP/START.
- Startup self-check (policy and templates valid, secrets present, production must use the signed policy).
- `docs/integrations/messaging-runbook.md`: webhook setup in the Meta App Dashboard, rotating the token and secret, what each alert means.

**Out of scope** (and which task covers it)
- Asking for consent and the WhatsApp number in the conversation; the consent wording; the consent management screen → P4-02 (including the confirmation-card line from DECISIONS #254)
- Deciding **when** to send confirmations and reschedule/cancel notices → P4-03
- Scheduling reminders, re-fetching the appointment before sending, DST → P4-04
- The admin screen that lists failed messages → P4-13 (uses this task's API)
- Template wording, approval and sender registration → P0-15
- Choosing the BSP and signing its BAA → P0-07
- Deciding allowed content and mode → P0-07a (compliance advisor)
- An SMS adapter: not built now (DECISIONS #252). The interface is ready for one.
- Forwarding patient replies to staff, or a two-way chat over WhatsApp → not planned for the MVP

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P0-07a Messaging policy (approved spec) | `messaging_policy.yaml`: channel, mode, fields, `never_allowed_fields` | Use the test policy `docs/compliance/messaging_policy.test.yaml` (§6). It allows WhatsApp in both modes and is **refused in prod** by check S3. |
| P0-07 BSP + BAA (approved spec) | Confirmation that the BSP exposes the Cloud API format, sandbox access, Integration facts | Build against the public Cloud API docs and `FakeProvider`. Use Meta's test business phone number (**Verify** availability) with team phones only and synthetic data. |
| P0-15 Templates (approved spec) | `templates.yaml`, `check_templates.py`, template approval status, system-reply texts | Use the P0-15 example templates plus the `phi_free_nudge` and `system_replies` entries shown in §6 (additive to P0-15). |
| P1-02 Infra (approved spec) | `notifications` and `reminders` queues, load balancer and Cloud Armor, `enqueue()` | Locally, call the task handlers directly in tests. |
| P1-03 DB (approved spec) | `consents`, `current_consents`, `contact_prefs`, `reminders`, migration framework | Add this task's migration on top. Use the P1-03 test fixtures. |
| P1-05 Secrets (approved spec) | `messaging-api-key`, `messaging-webhook-secret`, blind-index key | Local: values in `.env.local` (never committed). The webhook tests sign with a test secret. |
| P1-07 Logging and alerts (approved spec) | PHI-redacting logger, metrics helper, `audit()`, alert policy module | Use the P1-07 interfaces; add alerts A-M1 and A-M2. |
| P1-13 Staff auth (approved spec) | `require_permission()`, roles | Add permissions `MESSAGE_READ` and `MESSAGE_ACK` (additive edit). |

## 6. Interface contract

### 6.1 Files and modules
```
backend/app/integrations/messaging/
    __init__.py              # get_provider(channel) registry
    base.py                  # MessagingProvider protocol, dataclasses, errors
    whatsapp_cloud.py        # WhatsAppCloudProvider
    fake.py                  # FakeProvider (records sends, scripted errors and webhooks)
backend/app/domain/messaging/
    policy.py                # PolicyStore: load + validate policy and templates (reuses check_templates.check)
    sender.py                # MessageSender: gate G1–G8, render, persist, send
    inbound.py               # InboundHandler: STOP / START / HELP / OTHER
    status.py                # StatusUpdater: webhook status → outbound_messages
    keywords.py              # keyword normalisation and sets
backend/app/api/webhooks/messaging.py        # GET/POST /v1/webhooks/messaging/whatsapp
backend/app/api/admin/messages.py            # GET /v1/admin/messages, POST /v1/admin/messages/{id}/acknowledge
backend/app/db/migrations/versions/00xx_outbound_messages.py
docs/compliance/messaging_policy.test.yaml   # dev/staging only
docs/integrations/messaging-runbook.md
```

### 6.2 Provider interface (`integrations/messaging/base.py`)
```python
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Literal, Mapping, Protocol, Sequence

class Channel(StrEnum):
    WHATSAPP = "WHATSAPP"
    SMS = "SMS"                       # reserved; no adapter in this task

@dataclass(frozen=True)
class SenderRef:
    clinic_id: str
    sender_id: str                    # WhatsApp: the business PHONE_NUMBER_ID from clinic config

@dataclass(frozen=True)
class TemplateMessage:
    sender: SenderRef
    to_e164: str                      # "+15035550123"; PHI, never logged
    provider_template_name: str       # e.g. "booking_confirmation_nudge_v1"
    language: str                     # "en_US"
    params: Mapping[str, str]         # named params, already policy-checked; PHI in minimal_phi mode
    callback_ref: str                 # outbound_messages.id (UUID); sent as biz_opaque_callback_data

@dataclass(frozen=True)
class SendResult:
    provider_msg_id: str              # "wamid.HBgL..."

class ErrorClass(StrEnum):
    TRANSIENT = "TRANSIENT"           # retry later (Cloud Tasks backoff)
    PERMANENT_RECIPIENT = "PERMANENT_RECIPIENT"   # this number can't receive; don't retry
    PERMANENT_CONFIG = "PERMANENT_CONFIG"         # our setup is broken (template, token, account); don't retry, page
    WINDOW_CLOSED = "WINDOW_CLOSED"   # 131047: free-form text outside 24 h

class ProviderError(Exception):
    def __init__(self, code: str, error_class: ErrorClass, http_status: int | None = None):
        self.code, self.error_class, self.http_status = code, error_class, http_status
        super().__init__(f"provider error {code} ({error_class})")   # never includes the provider's message text

class WebhookSignatureError(Exception): ...
class WebhookPayloadError(Exception): ...

@dataclass(frozen=True)
class StatusEvent:
    provider_msg_id: str
    status: Literal["sent", "delivered", "read", "failed"]
    occurred_at: datetime
    error_code: str | None
    callback_ref: str | None          # our outbound_messages.id if echoed back

@dataclass(frozen=True)
class InboundEvent:
    sender_id: str                    # business PHONE_NUMBER_ID that received it → clinic
    from_e164: str                    # PHI, never logged
    provider_msg_id: str
    kind: Literal["text", "other"]    # buttons, media, location … → "other"
    text: str | None                  # in memory only; never stored or logged

WebhookEvent = StatusEvent | InboundEvent

class MessagingProvider(Protocol):
    name: str                         # "whatsapp_cloud" | "fake"
    channel: Channel
    async def send_template(self, msg: TemplateMessage) -> SendResult: ...      # raises ProviderError
    async def send_text(self, sender: SenderRef, to_e164: str, text: str) -> SendResult: ...
        # system replies only (inside the 24 h window); raises ProviderError(WINDOW_CLOSED) on 131047
    def verify_signature(self, headers: Mapping[str, str], raw_body: bytes) -> None: ...  # raises WebhookSignatureError
    def verify_subscription(self, query: Mapping[str, str]) -> str: ...        # returns challenge or raises WebhookSignatureError
    def parse_webhook(self, raw_body: bytes) -> Sequence[WebhookEvent]: ...    # raises WebhookPayloadError
    def classify_error(self, code: str, http_status: int | None) -> ErrorClass: ...
```
Registry: `get_provider(Channel.WHATSAPP)` returns the instance named by env `MESSAGING_PROVIDER` (`whatsapp_cloud` | `fake`). **Proposed:** `fake` is the default for `ENV=local` and test; startup check S3 refuses `fake` in prod.

> **Addition (P4-17, DECISIONS #268):** per-clinic config `messaging.provider_override` (`null` | `fake`) lets a staging test clinic use `FakeProvider` while the env provider stays `whatsapp_cloud`; `get_provider(channel, clinic)` checks it first. Startup check S3 is extended: in prod, any clinic with an override refuses startup. On staging, fake sends are recorded in `outbound_messages` with `provider_msg_id = "fake-<uuid>"`.

### 6.3 WhatsApp Cloud adapter: request and error mapping
Send request (Proposed shape; **Verify** each field, especially named parameters `parameter_name`, against the Cloud API "messages" reference for the pinned API version):
```http
POST {WHATSAPP_API_BASE}/{WHATSAPP_GRAPH_API_VERSION}/{PHONE_NUMBER_ID}/messages
Authorization: Bearer <access token from secret messaging-api-key>
Content-Type: application/json

{
  "messaging_product": "whatsapp",
  "recipient_type": "individual",
  "to": "15035550123",
  "type": "template",
  "template": {
    "name": "booking_confirmation_nudge_v1",
    "language": {"code": "en_US"},
    "components": [{
      "type": "body",
      "parameters": [
        {"type": "text", "parameter_name": "clinic_name",  "text": "Bright Smile Dental"},
        {"type": "text", "parameter_name": "clinic_phone", "text": "(503) 555-0100"}
      ]
    }]
  },
  "biz_opaque_callback_data": "6f1c2b9e-2a7d-4c1e-9b0a-3d5e8f7a1c20"
}
```
Success response (**Verify**): `{"messaging_product":"whatsapp","contacts":[{"input":"15035550123","wa_id":"15035550123"}],"messages":[{"id":"wamid.HBgL..."}]}` → `SendResult(provider_msg_id=messages[0].id)`.

Error mapping (`classify_error`; HTTP errors carry `error.code` in the JSON body):

| Codes / condition | Class | Sender action |
|---|---|---|
| HTTP timeout (> `MESSAGING_SEND_TIMEOUT_S`), connection error, HTTP 5xx, 131000, 131016, 130429, 80007, 4, 131056 | `TRANSIENT` | Raise → task handler returns 503 → Cloud Tasks retries |
| 131026, 131050, 131009 when about `to` | `PERMANENT_RECIPIENT` | Status `FAILED`, no retry, alert A-M1 |
| 132000, 132001, 132015, 132016, 131008, 131009 (other), 133010, 368, 131031, HTTP 401/403, OAuth error 190 | `PERMANENT_CONFIG` | Status `FAILED`, no retry, alert A-M2 (P1: all messages are probably failing) |
| 131047 | `WINDOW_CLOSED` | Only possible for `send_text`. Drop the system reply and count `message_system_reply_dropped_total` |
| Any other code | `TRANSIENT` for the first 2 attempts, then `PERMANENT_CONFIG` | Avoids retrying forever on an unknown code |

**Verify:** the 131009 `error_data.details` wording that tells a bad `to` apart from other bad parameters. If they can't be told apart reliably, treat 131009 as `PERMANENT_CONFIG`.

### 6.4 MessageSender (`domain/messaging/sender.py`)
```python
class MessageType(StrEnum):
    BOOKING_CONFIRMATION = "booking_confirmation"
    REMINDER = "reminder"
    RESCHEDULE_NOTICE = "reschedule_notice"
    CANCEL_NOTICE = "cancel_notice"

@dataclass(frozen=True)
class MessageRequest:
    clinic_id: str
    message_type: MessageType
    patnum: int                       # the patient the appointment is for (a child, for household bookings)
    aptnum: int | None
    to_e164: str                      # from contact_prefs (decrypted by the caller's repository); PHI
    values: Mapping[str, str]         # candidate values; the sender keeps only what the chosen template needs
    dedupe_key: str                   # see table below
    reminder_id: str | None = None    # set by P4-04

@dataclass(frozen=True)
class SendOutcome:
    outbound_id: str
    status: Literal["SENT", "SKIPPED", "FAILED", "DUPLICATE"]
    reason: str | None                # skip/fail code (table below); never free text
    provider_msg_id: str | None

class MessagingTransientError(Exception):
    """Raised to the Cloud Tasks handler; the handler returns 503 so the queue retries."""

class MessageSender:
    async def send(self, req: MessageRequest, *, attempt: int, max_attempts: int) -> SendOutcome: ...
```
- `attempt` comes from the `X-CloudTasks-TaskRetryCount` header + 1 (**Verify** the header name).
- `max_attempts` is the queue's setting (P1-02: `notifications` 8, `reminders` 5), passed in by the handler.

`dedupe_key` (unique per clinic; Proposed):

| Type | Key |
|---|---|
| booking_confirmation | `confirm:{aptnum}` |
| reminder | `reminder:{reminder_id}` |
| reschedule_notice | `resched:{aptnum}:{new_start_utc:%Y%m%dT%H%M}` |
| cancel_notice | `cancel:{aptnum}` |

**Policy gate**, run in this order (all deterministic):

| # | Check | On failure |
|---|---|---|
| G1 | The policy and templates loaded and passed the startup checks (S1–S4) | Service doesn't start (fail closed) |
| G2 | `policy.message_types[type]` exists and its channel has `allowed: true` | `SKIPPED` `CHANNEL_NOT_ALLOWED` |
| G3 | Exactly one template matches (`message_type`, `channel`, `whatsapp_mode == policy.channels.whatsapp.mode`) | `FAILED` `NO_TEMPLATE` + A-M2 |
| G4 | That template has `provider_status: APPROVED` (the approved template allow-list) | `FAILED` `TEMPLATE_NOT_APPROVED` + A-M2 |
| G5 | The template's variables ⊆ `policy.message_types[type].fields`, none in `never_allowed_fields`, and every variable has a value | `FAILED` `POLICY_VIOLATION` + A-M2 (this is a bug) |
| G6 | Value checks: `first_name` 1–30 chars with letters, spaces, `'` and `-` only; `clinic_phone` matches `^\(\d{3}\) \d{3}-\d{4}$`; dates and times come only from the formatter; no value contains a newline, tab, URL, `{` or `}`, or more than 4 spaces in a row (**Verify** the Cloud API parameter limits) | `FAILED` `BAD_VALUE` + A-M2 |
| G7 | `current_consents(clinic, bidx(to_e164), WHATSAPP, APPOINTMENT_MESSAGES).action == GRANTED` | `SKIPPED` `NO_CONSENT` |
| G8 | No `outbound_messages` row with the same (`clinic_id`, `dedupe_key`) in `SENT`/`DELIVERED`/`READ` | `DUPLICATE` (returns the existing row) |

After the gate:
1. Insert or re-use the row, set it to `SENDING` and increment `attempts`.
2. Call `send_template`.
3. On success, set `SENT` with `provider_msg_id` and `sent_at`.
4. On `ProviderError`, act on the error class (§6.3). On `TRANSIENT`: if `attempt < max_attempts`, set the row back to `QUEUED` with `last_error_code` and raise `MessagingTransientError`; on the last attempt, set `FAILED` `RETRIES_EXHAUSTED` and fire A-M1.

**Retry of a row left in `SENDING`** (the process died after calling the provider): **Proposed:** send again. This is at-least-once: the only possible harm is a second, identical message to the same number. That is better than a missed reminder (DECISIONS #253).

**Addition (P4-03, DECISIONS #258):** `MessageSender.record(req, status=SKIPPED|FAILED, reason)` writes a row and audit event without calling the provider; `MessageRequest.template_override: str | None` selects a specific template that must still pass G2–G6; new reason codes `NO_CONTACT`, `APPT_CHANGED`, `TOO_LATE`, `VERIFY_FAILED`.

Skip and fail reason codes (stored in `outbound_messages.reason`): `CHANNEL_NOT_ALLOWED`, `NO_CONSENT`, `NO_TEMPLATE`, `TEMPLATE_NOT_APPROVED`, `POLICY_VIOLATION`, `BAD_VALUE`, `RECIPIENT_UNREACHABLE` (131026), `RECIPIENT_BLOCKED` (131050), `PROVIDER_CONFIG` (other `PERMANENT_CONFIG`), `RETRIES_EXHAUSTED`, `DELIVERY_FAILED` (a failed status arrived by webhook).

**Rendering:** the sender takes the template's variables from `req.values` in the template's order and builds `params`. In `phi_free_nudge` mode the nudge templates only have `clinic_name` and `clinic_phone`, so `first_name`, date and time are never even read from `req.values`.

### 6.5 Templates and policy additions (additive to P0-15 and P0-07a)
WhatsApp entries in `templates.yaml` get three new fields: `whatsapp_mode`, `provider_template_name` and `provider_status`, plus a new top-level `system_replies` block.
```yaml
  - id: booking_confirmation_nudge_v1
    message_type: booking_confirmation
    channel: whatsapp
    whatsapp_category: UTILITY
    whatsapp_mode: phi_free_nudge          # phi_free_nudge | minimal_phi
    provider_template_name: booking_confirmation_nudge_v1
    language: en_US
    provider_status: APPROVED              # DRAFT | SUBMITTED | APPROVED | REJECTED | PAUSED; updated by P0-15 / ops
    version: 1
    body: "Hello from {clinic_name}. Your appointment request is confirmed. For details or changes, please call {clinic_phone}. Thank you."
    variables: [clinic_name, clinic_phone]
    example: {clinic_name: "Bright Smile Dental", clinic_phone: "(503) 555-0100"}
  - id: reminder_nudge_v1
    message_type: reminder
    channel: whatsapp
    whatsapp_category: UTILITY
    whatsapp_mode: phi_free_nudge
    provider_template_name: reminder_nudge_v1
    language: en_US
    provider_status: APPROVED
    version: 1
    body: "Reminder from {clinic_name}: you have a visit coming up soon. Questions? Please call {clinic_phone}. Thank you."
    variables: [clinic_name, clinic_phone]
    example: {clinic_name: "Bright Smile Dental", clinic_phone: "(503) 555-0100"}
  # reschedule_notice_nudge_v1 and cancel_notice_nudge_v1 follow the same pattern:
  #   "{clinic_name} has an update about your appointment. Please call {clinic_phone} for details. Thank you."
  # minimal_phi variants (booking_confirmation_v1 …) are the P0-15 bodies with whatsapp_mode: minimal_phi;
  # they are submitted to Meta only after the advisor approves minimal_phi.
system_replies:                            # free-form, sent only inside the 24 h window, never contain PHI
  stop_confirmed:  "You won't get any more appointment messages from {clinic_name} on WhatsApp. Reply START to turn them back on."
  start_confirmed: "Appointment messages from {clinic_name} are turned back on. Reply STOP at any time to turn them off."
  help:            "{clinic_name} appointment messages. For help, call {clinic_phone}. Reply STOP to turn them off."
  auto_reply:      "This number doesn't read replies. To change or cancel an appointment, please call {clinic_phone}. Reply STOP to turn off messages."
```
The policy gains `whatsapp.mode`, which P0-07a already lists (`none | phi_free_nudge | minimal_phi`). In `phi_free_nudge` mode, every type's `fields` is `[clinic_name, clinic_phone]`.

`docs/compliance/messaging_policy.test.yaml` (dev and staging only):
```yaml
schema_version: 1
decision_version: "test-1"
approved_by: ["TEST POLICY - NOT FOR PRODUCTION"]
channels:
  whatsapp: {allowed: true, mode: phi_free_nudge}    # tests flip mode to minimal_phi in fixtures
  sms: {allowed: false}
  email: {allowed: false}
message_types:
  booking_confirmation: {channel: whatsapp, fields: [clinic_name, clinic_phone, first_name, appointment_date, appointment_time]}
  reminder:             {channel: whatsapp, fields: [clinic_name, clinic_phone, first_name, appointment_time]}
  reschedule_notice:    {channel: whatsapp, fields: [clinic_name, clinic_phone, first_name, appointment_date, appointment_time]}
  cancel_notice:        {channel: whatsapp, fields: [clinic_name, clinic_phone, first_name, appointment_date]}
never_allowed_fields: [last_name, dob, reason, reason_code, procedure, symptoms, provider_name, insurance, pat_num, apt_num]
```

### 6.6 Startup self-check (`PolicyStore.load()`; the service refuses to start if any check fails)
| # | Check |
|---|---|
| S1 | `check_templates.check(templates, policy, schema)` has no errors (P0-15 rules T1–T10) |
| S2 | Every `system_replies` text uses only `{clinic_name}` and `{clinic_phone}`, and contains no T7 denylist word |
| S3 | If `ENV=prod`: `MESSAGING_PROVIDER != fake`, the policy's `decision_version` doesn't start with `test`, and `MESSAGING_POLICY_PATH` is the signed `docs/compliance/messaging_policy.yaml` |
| S4 | The secrets `messaging-api-key`, `messaging-webhook-secret` and `messaging-webhook-verify-token` are present (values never logged) |

### 6.7 Table `outbound_messages` (additive to P1-03)
| Column | Type | Constraints | PHI |
|---|---|---|---|
| `id` | uuid | PK, `gen_random_uuid()` | - |
| `clinic_id` | uuid | FK `clinics`, NOT NULL | - |
| `message_type` | text | CHECK in `MessageType` | - |
| `channel` | text | `WHATSAPP`, `SMS` | - |
| `template_id` | text | NOT NULL (our ID, e.g. `reminder_nudge_v1`) | - |
| `policy_version` | text | NOT NULL | - |
| `patnum` | bigint | NOT NULL | R |
| `aptnum` | bigint | NULL | R |
| `reminder_id` | uuid | NULL, FK `reminders` | - |
| `address_bidx` | bytea | NOT NULL, length 32 | P (hash) |
| `dedupe_key` | text | NOT NULL; UNIQUE (`clinic_id`, `dedupe_key`) | - (IDs only) |
| `status` | text | `QUEUED`, `SENDING`, `SENT`, `DELIVERED`, `READ`, `FAILED`, `SKIPPED` | - |
| `reason` | text | NULL; codes from §6.4 | - |
| `last_error_code` | text | NULL; provider code only | - |
| `attempts` | int | NOT NULL DEFAULT 0 | - |
| `provider_msg_id` | text | NULL; UNIQUE where not NULL | - |
| `sent_at`, `delivered_at`, `read_at`, `failed_at` | timestamptz | NULL | - |
| `acknowledged_at` | timestamptz | NULL | - |
| `acknowledged_by` | uuid | NULL, FK `staff_users` | - |
| `created_at`, `updated_at` | timestamptz | NOT NULL | - |

Indexes:
- `ix_outbound_failed_unack` on (`clinic_id`, `status`, `acknowledged_at`) WHERE `status = 'FAILED'`;
- `ix_outbound_patnum` on (`clinic_id`, `patnum`).

The message **body is never stored**, and neither is the phone number in clear text. Staff look up the patient's phone in Open Dental by PatNum. Retention follows P1-03 (operational records).

The P1-03 `consents.source` CHECK gains `WHATSAPP_STOP` and `WHATSAPP_START`.

### 6.8 Webhook endpoints (`api/webhooks/messaging.py`)
```
GET  /v1/webhooks/messaging/whatsapp?hub.mode=subscribe&hub.challenge=<int>&hub.verify_token=<s>
     200 text/plain "<challenge>"  if mode == "subscribe" and token == secret (constant-time compare)
     403                            otherwise
POST /v1/webhooks/messaging/whatsapp
     Headers: X-Hub-Signature-256: sha256=<hex>
     Body: raw JSON ≤ 3 MB (larger → 413)
     200 {}   signature OK; events processed, or ignored as duplicates or unknown
     403      signature missing or wrong (no body parsing, nothing processed)
     400      signature OK but JSON can't be parsed (logged as error; Meta won't fix it by retrying)
     500      DB unavailable while processing → Meta retries (up to 7 days); handler is idempotent
```
- Signature check: `hmac.compare_digest(hmac.new(app_secret, raw_body, sha256).hexdigest(), header_hex)`.
- The check runs over the **exact raw bytes**, before any JSON parsing.
- No session or staff auth: the signature is the authentication.

Processing per event:

| Event | Handling |
|---|---|
| `StatusEvent` | `StatusUpdater.apply()`. Find the row by `provider_msg_id` (or by `callback_ref`). Status only moves forward: `SENT(1) < DELIVERED(2) < READ(3)`. `failed` sets `FAILED` `DELIVERY_FAILED` unless the row is already `DELIVERED` or `READ` (then it is only counted). Unknown `provider_msg_id` → count `message_status_unmatched_total` and return 200. |
| `InboundEvent` | Dedup in Redis with `SET wa:in:{provider_msg_id} 1 NX EX 604800` (7 days). Then `InboundHandler.handle()`. |
| Other `field` values (account updates, template status) | Ignored and counted. **Proposed:** template status changes (`message_template_status_update`, **Verify**) are logged as `messaging.template_status` with the template name and new status, so ops can update `provider_status`. |

### 6.9 Inbound keyword handling (`domain/messaging/inbound.py`, `keywords.py`)
Normalise the text: trim, uppercase, remove `.`, `!` and quotes, and collapse spaces. Then match **the whole message** against these sets:
```python
STOP_WORDS  = {"STOP", "STOPALL", "UNSUBSCRIBE", "END", "QUIT", "OPTOUT", "OPT OUT", "REVOKE", "STOP MESSAGES"}
START_WORDS = {"START", "UNSTOP", "SUBSCRIBE", "RESUME"}
HELP_WORDS  = {"HELP", "INFO"}
# "CANCEL" is deliberately NOT a stop word: a dental patient who writes "cancel" most likely means the
# appointment. It gets auto_reply, which says how to cancel (call) and how to stop messages (DECISIONS #253).
```
| Class | Actions (in one DB transaction, then the reply) |
|---|---|
| STOP | (Implemented through P4-02 `ConsentService.revoke(source=WHATSAPP_STOP)`, which does steps 1–3; START uses `ConsentService.grant`.) 1. Insert `consents` (`action=REVOKED`, `source=WHATSAPP_STOP`, `channel=WHATSAPP`, `purpose=APPOINTMENT_MESSAGES`, `messaging_address_bidx`, `patnum=NULL`; the address may be shared by a household, DECISIONS #185). 2. For every `contact_prefs` row with that bidx and `channel=WHATSAPP` in this clinic, set that patient's `reminders` in `PENDING`/`ENQUEUED` to `CANCELLED` with `skip_reason=NO_CONSENT`, and delete their Cloud Tasks (best effort; P4-04's pre-send consent check is the second guard). 3. Audit `consent.revoke` (actor `system`, source `WHATSAPP_STOP`). 4. `send_text(stop_confirmed)`. |
| START | Only if the current row is `REVOKED`: insert `GRANTED`, `source=WHATSAPP_START`, `wording_version=wa-start-v1`. Audit `consent.grant`. Send `start_confirmed`. Cancelled reminders are **not** brought back; future bookings send again (DECISIONS #253). If consent was never granted, reply `help` instead, because START alone doesn't create a first consent (P4-02 owns first consent). |
| HELP | Send `help`. |
| OTHER (any other text, or `kind=other`) | Don't store or log the content. Count `message_inbound_other_total`. Send `auto_reply` at most once per address per 24 h (Redis `SET wa:ar:{clinic}:{bidx_hex} 1 NX EX 86400`). |

The sender number maps to a clinic through `messaging.whatsapp.phone_number_id` in clinic config (P1-19). An unknown `phone_number_id` gets 200, a warning and a metric, with no action.

### 6.10 Staff API (failed messages; consumed by P4-13)
```
GET  /v1/admin/messages?status=FAILED&acknowledged=false&limit=50&cursor=<opaque>
     Permission: MESSAGE_READ (ADMIN, FRONT_DESK)
     200 {"items": [{"id": "uuid", "message_type": "reminder", "status": "FAILED", "reason": "RECIPIENT_UNREACHABLE",
                     "patnum": 1234, "aptnum": 5678, "attempts": 1, "failed_at": "2026-12-08T16:31:02Z",
                     "acknowledged_at": null}], "next_cursor": null}
POST /v1/admin/messages/{id}/acknowledge
     Permission: MESSAGE_ACK (ADMIN, FRONT_DESK)
     204; audit "message.acknowledge"; 404 if the id is not in the staff user's clinic; 409 if not FAILED
```
The API returns IDs and codes only. P4-13 looks up the patient name and phone through the existing Open Dental read path, under the staff user's permissions.

### 6.11 Config, secrets, metrics, alerts
| Key | Where | Default / example |
|---|---|---|
| `MESSAGING_PROVIDER` | env | `whatsapp_cloud` (prod), `fake` (local) |
| `MESSAGING_POLICY_PATH` | env | `docs/compliance/messaging_policy.yaml` (prod) |
| `MESSAGING_TEMPLATES_PATH` | env | `docs/messaging/templates.yaml` |
| `WHATSAPP_API_BASE` | env | `https://graph.facebook.com` |
| `WHATSAPP_GRAPH_API_VERSION` | env | pinned, e.g. `v24.0` (**Verify** the current version when implementing) |
| `MESSAGING_SEND_TIMEOUT_S` | env | `10` |
| `messaging.whatsapp.phone_number_id` | clinic config (P1-19) | `"106540352242922"` |
| `messaging.whatsapp.language` | clinic config | `en_US` |
| `clinic.public_phone` | clinic config (exists) | rendered as `(503) 555-0100` |
| `messaging-api-key` | Secret Manager (P1-05) | JSON `{"access_token": "...", "waba_id": "..."}` (system-user token; **Verify** the token type with the BSP) |
| `messaging-webhook-secret` | Secret Manager (P1-05) | Meta App Secret |
| `messaging-webhook-verify-token` | Secret Manager (new, additive to P1-05) | random 32-byte string |

Metrics (P1-07 helper), with labels `clinic_id`, `message_type`, `reason` and `code` only:
- `message_send_total{outcome}`
- `message_failed_total{reason}`
- `message_status_total{status}`
- `message_status_unmatched_total`
- `webhook_signature_invalid_total`
- `message_inbound_total{class}`
- `message_system_reply_dropped_total`
- `message_send_latency_ms`

Alerts (additive to P1-07):

| ID | Condition | Severity |
|---|---|---|
| A-M1 | `message_failed_total` for reasons `RECIPIENT_*`, `RETRIES_EXHAUSTED` or `DELIVERY_FAILED` > 0 in 15 min | P2 (console list + email to ops) |
| A-M2 | Any `PERMANENT_CONFIG` failure, `NO_TEMPLATE`, `TEMPLATE_NOT_APPROVED`, `POLICY_VIOLATION` or `BAD_VALUE` | P1 |
| A-M3 | `webhook_signature_invalid_total` > 20 in 10 min | P2 (possible probing, or a rotated secret) |

Audit events (P1-07 `audit()`; no PHI in `details`):

| Action | When | Details |
|---|---|---|
| `message.send` | Status `SENT` | `channel`, `template_id`, `message_type` |
| `message.skip` | Status `SKIPPED` | `reason_code` |
| `message.fail` | Status `FAILED` | `reason_code`, `provider_status` |
| `message.acknowledge` | Staff acknowledges | message ID |
| `consent.revoke` / `consent.grant` | STOP / START | `channel`, `source` |

## 7. Implementation guide
1. **Read** P0-07a (policy shape), P0-15 (`templates.yaml`, `check_templates.py`, rules T1–T10), P1-03 (consent tables, blind index), P1-02 (queues, `enqueue()`), P1-05 (secrets), P1-07 (logger, metrics, audit, alerts) and P1-13 (permissions).
2. **Verify** the Cloud API facts marked **Verify** in §3 and §6.3: send payload with named parameters, response shape, API version, token type, 131009 details, the template-status webhook field and the `X-CloudTasks-TaskRetryCount` header. Write them with links into `docs/integrations/messaging-provider.md`, section "Integration facts" (started by P0-07).
3. **Migration** `00xx_outbound_messages`: create the table (§6.7) and extend the `consents.source` CHECK. Grants: `app_rw` gets `SELECT, INSERT, UPDATE` on `outbound_messages`, and no `DELETE`.
4. **`base.py`** dataclasses and errors, then **`fake.py`**. `FakeProvider` records every send in memory, can be scripted to raise a given code on the n-th call, and can build signed webhook payloads (`make_status_webhook(...)`, `make_inbound_webhook(...)`) for tests.
5. **`policy.py`**: load YAML, run `check_templates.check()` (import it from `scripts/messaging`; **Proposed:** move the core into `backend/app/domain/messaging/template_rules.py` and make the script a thin wrapper, so both use one implementation), then run S2–S4. Expose `template_for(message_type, channel, mode)`.
6. **`sender.py`**: gate G1–G8 → row state machine → provider call → error handling (§6.4). Write the row and the audit event in the same transaction as the status change.
7. **`whatsapp_cloud.py`**: `httpx.AsyncClient` with the timeout, the request from §6.3, `classify_error`, `verify_signature` (raw bytes, constant time), `verify_subscription` and `parse_webhook` (pydantic models that ignore unknown fields; `contacts[].profile` is dropped at parse time).
8. **Webhook route**: read the raw body with a 3 MB limit, verify, parse, apply. Return 200 fast; the work is a few indexed DB updates (target p95 < 300 ms).
9. **`inbound.py` and `keywords.py`** (§6.9), including the household case (one number, several PatNums).
10. **Staff API** (§6.10) and the P1-13 permissions.
11. **Cloud Armor and load balancer** (additive to P1-02): the webhook path is public. Add a rule that allows `POST` and `GET` on `/v1/webhooks/messaging/whatsapp` with a per-IP rate limit (Proposed: 600 per minute). Run the WAF rules in preview for this path first: large JSON bodies can trigger false positives. The signature is the real control.
12. **Meta App Dashboard setup** (runbook): set the callback URL and verify token, subscribe the `messages` field, and point the phone number at the app. Repeat per environment, each with its own app or secret.
13. **Metrics, alerts and audit** (§6.11).
14. **Tests** (§10) and the runbook.

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| Policy says `whatsapp.allowed: false` or `mode: none` | Every send → `SKIPPED` `CHANNEL_NOT_ALLOWED`; nothing reaches Meta. P4-02 shouldn't offer consent in this case (it reads the same policy). |
| Advisor switches the mode from `phi_free_nudge` to `minimal_phi` | Change the policy file, release it and restart. G3 picks the `minimal_phi` templates; they must be `APPROVED` first, or sends fail with `TEMPLATE_NOT_APPROVED` (A-M2). |
| The number isn't on WhatsApp (131026) | `FAILED` `RECIPIENT_UNREACHABLE`, no retry, A-M1. Staff see it in the console and can call the patient (no SMS fallback, DECISIONS #252). |
| Rate limited (130429, 80007, 4, 131056) | `TRANSIENT`: the Cloud Tasks backoff handles it. On the last attempt, `FAILED` `RETRIES_EXHAUSTED`. |
| Access token expired or revoked (401, OAuth 190) | `PERMANENT_CONFIG`, A-M2 (P1). The runbook explains how to rotate. Messages fail until fixed; P4-04 may re-enqueue reminders still in time after the fix. |
| Template paused (132015) | `PERMANENT_CONFIG`, A-M2. Ops update `provider_status: PAUSED` so G4 stops calling Meta. |
| Cloud Tasks retries after the provider already accepted (process crashed before `SENT` was saved) | Row is `SENDING` → send again (at-least-once). The patient may get two identical messages. Counted as `message_possible_duplicate_total`. |
| Same task delivered twice after success | G8 → `DUPLICATE`, no second send. |
| Webhook `failed` after `DELIVERED` | Keep `DELIVERED`; count it. |
| `read` arrives without `delivered` | Set `READ` and `delivered_at = read_at` (Meta can skip "delivered"). |
| Status webhook arrives before our DB commit of `SENT` (race) | Match by `callback_ref` (our UUID). If the row is still `SENDING`, store `provider_msg_id` and the status from the webhook, and the sender keeps the more advanced status. |
| Duplicate webhook (Meta retry) | Status: forward-only update, no change. Inbound: Redis dedup. |
| Forged webhook or wrong secret | 403, nothing parsed, metric; A-M3 if it happens often. |
| Body > 3 MB | 413 |
| STOP from a number we never messaged | Insert a REVOKED row with `patnum=NULL` (P1-03 rule). Future consent lookups see REVOKED. Reply `stop_confirmed`. |
| STOP from a shared household number | One REVOKED row for the address. Reminders of **every** PatNum linked to that number are cancelled. |
| Patient writes "Cancel" or "cancel my appointment" | Not a stop word → `auto_reply` (call the clinic to cancel; reply STOP to stop messages). No appointment change by message in the MVP. |
| Patient writes "stop please" | No exact match → `auto_reply`, which tells them to reply STOP. **Proposed:** keep exact matching to avoid accidental revocation. Monitor `message_inbound_total{class="other"}` during the pilot. |
| START when consent is already GRANTED | No new row; reply `start_confirmed`. |
| System reply outside the 24 h window (131047) | Dropped and counted. Not possible in normal flow, since it answers a message just received. |
| Patient sends a photo or voice note | `kind=other` → `auto_reply`; the media is never downloaded. |
| Unknown `phone_number_id` | 200, warning `messaging.unknown_sender`, no action. |
| DB down during the webhook | 500 → Meta retries for up to 7 days; idempotent processing makes the replay safe. |
| `first_name` has unusual characters (e.g. "Zoë") | G6 allows Unicode letters. A name with digits or symbols → `BAD_VALUE` (A-M2), because the value didn't come from a verified Open Dental field. |

## 9. Security, HIPAA and PHI
**PHI handled:**

| Data | Where it flows | Protection |
|---|---|---|
| Patient WhatsApp number | Clinic DB (`contact_prefs`, encrypted) → memory → Meta (`to`) | Stored only encrypted and as a blind index; never in `outbound_messages` in clear |
| Template values in `minimal_phi` mode (first name, date, time) | Memory → Meta | Only if the advisor approves; limited by the policy gate |
| PatNum, AptNum | `outbound_messages`, staff API | PatNum and AptNum are IDs (P1-03 class R) |
| Inbound text, profile name | Memory only | Never stored or logged; dropped after keyword classification |

- **Fewest-PHI default:** `phi_free_nudge` sends only the clinic name and phone. Even so, the fact that a person gets a message from a dental clinic tells Meta that this number belongs to a patient. The advisor's P0-07a decision must cover this (DECISIONS #252). **No production sends until P0-07a records `whatsapp.allowed: true`.**
- **Must never be logged:** phone numbers, `to`, template parameter values, rendered bodies, inbound text, `contacts[].profile`, the access token, the app secret, the verify token, the signature header value. The provider's error `message` text is never logged either; we keep only the numeric code. Add these keys to the P1-07 redaction list: `to`, `wa_id`, `recipient_id`, `from`, `profile`, `text`, `body`, `parameters`.
- **Webhook auth:** HMAC signature over the raw body, constant-time compare, before any parsing. The verify token is compared in constant time.
- **Least privilege:** the staff API checks the clinic scope and the `MESSAGE_READ` / `MESSAGE_ACK` permissions. `READ_ONLY` and `DENTIST` roles can't acknowledge.
- **Audit:** see §6.11. Consent changes from STOP/START are append-only rows plus audit events.
- **BAA:** the BSP's BAA (P0-07) covers the BSP. Meta states it is not a business associate (DECISIONS #35). That is exactly why the content stays at the advisor-approved minimum.

## 10. Testing
Unit tests (`backend/tests/unit/messaging/`), using `FakeProvider` and respx for the HTTP adapter:

| # | Case | Expected |
|---|---|---|
| U1 | Policy channel not allowed | `SKIPPED CHANNEL_NOT_ALLOWED`, 0 provider calls |
| U2 | Template `provider_status: SUBMITTED` | `FAILED TEMPLATE_NOT_APPROVED`, 0 calls, A-M2 metric |
| U3 | Template with a `reason` variable (fixture) | Startup check S1 fails; the service doesn't start |
| U4 | `phi_free_nudge`: `req.values` contains `first_name` | Params sent = `{clinic_name, clinic_phone}` only |
| U5 | `minimal_phi` fixture | Params include `first_name`, date, time; nothing else |
| U6 | Consent REVOKED | `SKIPPED NO_CONSENT` |
| U7 | Same `dedupe_key` after `SENT` | `DUPLICATE`, 1 provider call in total |
| U8 | 130429 on attempt 1 of 5 | Raises `MessagingTransientError`; row `QUEUED`, `last_error_code=130429` |
| U9 | 130429 on attempt 5 of 5 | `FAILED RETRIES_EXHAUSTED`, A-M1 metric |
| U10 | 131026 | `FAILED RECIPIENT_UNREACHABLE`, no retry |
| U11 | 132001 / 401 | `FAILED PROVIDER_CONFIG`, A-M2 |
| U12 | Webhook with a valid signature | 200; statuses applied |
| U13 | Webhook with a wrong, missing or `sha1=` signature | 403; nothing applied |
| U14 | Body changed by one byte after signing | 403 |
| U15 | Status order `read` then `delivered` | Final `READ` |
| U16 | `failed` after `DELIVERED` | Stays `DELIVERED` |
| U17 | Same status webhook twice | One update |
| U18 | Inbound "STOP", " stop! ", "Unsubscribe" | REVOKED row, reminders cancelled, `stop_confirmed` sent |
| U19 | Inbound "cancel" and "stop please" | No consent change; `auto_reply` |
| U20 | START after STOP | GRANTED `WHATSAPP_START`; cancelled reminders stay cancelled |
| U21 | START with no prior consent | No row; `help` sent |
| U22 | Two "hello" messages in 1 hour | One `auto_reply` |
| U23 | GET subscription with the right / wrong token | Challenge echoed / 403 |
| U24 | Log capture over U1–U22 | No phone number, parameter value, inbound text or token in any log record |
| U25 | `ENV=prod` with `fake` provider or the test policy | Startup fails (S3) |

Integration (`backend/tests/integration/messaging/`, Postgres + Redis in Docker):
- **I1:** STOP for a household number with 2 PatNums and 3 pending reminders → all 3 `CANCELLED NO_CONSENT`; `current_consents` = REVOKED.
- **I2:** Crash simulation: provider succeeds and the DB update raises → the retry sends again; `message_possible_duplicate_total` = 1.
- **I3:** Staff API: FRONT_DESK lists and acknowledges; READ_ONLY gets 403; another clinic's ID gets 404.

Manual (staging, team phones only, synthetic data):
- send each nudge template;
- receive delivered and read webhooks;
- reply STOP, START and HELP;
- reply with a photo;
- record the results in the runbook.

```bash
cd backend && pytest tests/unit/messaging tests/integration/messaging -q
python scripts/messaging/check_templates.py --templates docs/messaging/templates.yaml --policy docs/compliance/messaging_policy.test.yaml
```

## 11. Acceptance criteria
- [ ] The provider can be swapped by config: the same `MessageSender` tests pass with `FakeProvider` and with `WhatsAppCloudProvider` against respx mocks
- [ ] Only templates with `provider_status: APPROVED` that match the policy's channel and mode are sent (U2, U3)
- [ ] A template or value outside the policy's `fields`, or in `never_allowed_fields`, never reaches the provider (U3, U4, U5)
- [ ] In `phi_free_nudge` mode, no patient name, date or time is sent (U4)
- [ ] No message is sent without a `GRANTED` consent (U6)
- [ ] Webhook signature verified: wrong, missing or tampered signatures get 403 and change nothing (U13, U14)
- [ ] Delivery statuses are tracked forward-only and duplicate webhooks are harmless (U15–U17)
- [ ] Transient errors retry; permanent errors don't; the last attempt marks `FAILED` (U8–U11)
- [ ] Failed messages are listed by `GET /v1/admin/messages?status=FAILED` and raise A-M1 or A-M2 (U9–U11, I3)
- [ ] STOP → consent revoked and pending reminders cancelled, including household numbers (U18, I1)
- [ ] "cancel" does not revoke consent (U19)
- [ ] No PHI in logs (U24)
- [ ] The service refuses to start in prod with the fake provider or the test policy (U25)

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI
- [ ] PR reviewed (HIPAA review: `phi` label)
- [ ] No PHI in logs
- [ ] Docs / README updated: `messaging-runbook.md`, and "Integration facts" filled in with verified facts
- [ ] P1-03, P1-05, P1-07, P1-13 and P0-15 additions merged (migration, secret, alerts, permissions, template fields)
- [ ] Staging manual run recorded (team phones, synthetic data)

## 13. Hand-off
| Consumer | What it can rely on |
|---|---|
| P4-02 Consent | `current_consents` semantics with the new sources `WHATSAPP_STOP` and `WHATSAPP_START`; the policy's `whatsapp.allowed` and `mode` (don't offer consent when not allowed). P4-02 also owns the WhatsApp number question and the confirmation-card line "WhatsApp confirmation will be sent to: …" (DECISIONS #254). |
| P4-03 Notifications | `MessageSender.send()` with `MessageType.BOOKING_CONFIRMATION`, `RESCHEDULE_NOTICE` and `CANCEL_NOTICE`, the dedupe keys, `MessagingTransientError` → return 503 |
| P4-04 Reminders | `send()` with `REMINDER` and `reminder_id`; `SendOutcome` to update `reminders.status`; STOP already cancels pending reminders (P4-04 still re-checks consent before sending) |
| P4-13 Admin console | `GET /v1/admin/messages` and `POST /v1/admin/messages/{id}/acknowledge`, reason codes for display |
| P4-17 E2E | `FakeProvider` webhook builders for time-simulated lifecycle tests |
| P5 security review | Webhook signature check, redaction keys, Cloud Armor rule |

## 14. Open questions
| Question | Owner | Needed by |
|---|---|---|
| Does the BSP chosen in P0-07 accept the Cloud API request format (or proxy to it)? If not, write an adapter for its API behind the same interface. | Tech lead (P0-07) | Step 2 |
| Is `phi_free_nudge` (clinic name + phone only) acceptable on WhatsApp, and is `minimal_phi` ever allowed? | Compliance advisor (P0-07a) | Before any production send |
| Exact Cloud API version and named-parameter support | Developer (Verify) | Step 2 |

## 15. References
- Plan §4.7 (WhatsApp reminders), §5 (data), §6 (security), §7 (admin console)
- WhatsApp webhooks overview: https://developers.facebook.com/documentation/business-messaging/whatsapp/webhooks/overview
- Webhook payload signature (`X-Hub-Signature-256`) and verification requests: https://developers.facebook.com/docs/graph-api/webhooks/getting-started
- Status webhook reference: https://developers.facebook.com/documentation/business-messaging/whatsapp/webhooks/reference/messages/status
- Error codes: https://developers.facebook.com/documentation/business-messaging/whatsapp/support/error-codes
- Templates overview: https://developers.facebook.com/documentation/business-messaging/whatsapp/templates/overview
- DECISIONS #35–#38, #78, #92, #185, #252–#254
- Related tasks: P0-07, P0-07a, P0-11, P0-14, P0-15, P1-02, P1-03, P1-05, P1-07, P1-13, P1-19, P4-02, P4-03, P4-04, P4-13, P4-17
