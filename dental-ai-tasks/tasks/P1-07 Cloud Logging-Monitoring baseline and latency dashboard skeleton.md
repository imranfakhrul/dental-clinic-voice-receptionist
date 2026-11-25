---
id: P1-07
title: PHI-safe logging, audit log service, monitoring, alerting and latency dashboard
milestone: P1
epic: E1.1
size: L
labels: area:infra, area:backend, area:security, type:feature, phi
depends_on: P1-01, P1-02, P1-03
status: approved
---

# P1-07: PHI-safe logging, audit log service, monitoring, alerting and latency dashboard

## 1. Summary
This issue builds everything we use to see what the system is doing, without leaking patient data. It also absorbs **P1-11 (PHI-redacting logger)** and **P1-12 (Audit log service)**.

1. **PHI-safe logging** (`backend/app/core/logging.py`, replaces P1-01's minimal logger). Three layers:
   - an **allow-list** of log fields; anything else is dropped;
   - **fixed event names** as messages, checked by a test;
   - a **regex scrubber** for anything that slips through, including exception text.

   No request or response bodies, query strings or uvicorn access logs.
2. **Audit log service** (`backend/app/core/audit.py`):
   - `audit()` writes to the `audit_log` table (P1-03) **in the same transaction** as the action it records;
   - a PHI-free copy goes to a protected Cloud Logging bucket after commit (6 years by default, **configurable**);
   - the closed list of actions and `details` keys is defined here.
3. **Tracing and latency metrics:**
   - OpenTelemetry with Cloud Trace and Cloud Monitoring;
   - a `stage_timer()` helper and the `dai.stage.latency` histogram for every pipeline stage;
   - the latency dashboard skeleton, filled by P3 tasks.
4. **Cloud side** (Terraform module `infra/modules/observability/`):
   - log buckets, sinks and retention;
   - CMEK on log buckets;
   - Data Access audit logs for KMS, Secret Manager, Cloud SQL Admin and IAM;
   - log-based metrics, uptime checks, notification channels, alert policies and dashboards for dev, staging and prod.

Done means:
- the PHI leak test suite finds 0 leaks;
- every state-changing PHI action writes an audit row or fails;
- audit copies land in the protected `audit-logs` bucket;
- the alerts in §6 exist and a test alert reaches every channel;
- the dashboard shows the stage panels.

## 2. Why this matters
Plan §6 requires:
- structured logs with PHI redaction;
- debug tools off in production;
- an audit log for patient searches, patient and appointment changes, callbacks, authentication, admin actions, errors and security events.

Cloud Logging is reached by many people and tools (incident responders, support, exports). If PHI gets into logs, it spreads outside the controls we built for the database. P0-11 lists:
- **R01:** exceptions, debug output or request dumps write PHI to Cloud Logging;
- **R20:** audit entries missing or altered;
- **R31:** breach detected late.

This task is the main control for all three.

The pilot targets also need measurement:
- 0 PHI in logs;
- callback emails delivered 100% or flagged;
- voice-to-voice latency ≤ 1.5 s p50 / 2.5 s p95.

Without stage-level metrics, P3 can't tune latency, and without alerts, failed reminders or emails go unnoticed.

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P1, Core Platform & Open Dental Adapter**.
- **What already exists:**
  - **P1-01:**
    - `core/logging.py` (minimal JSON logger, "P1-07 replaces the formatter");
    - `request_id` and `trace_id` contextvars, parsed from `X-Request-ID` and `X-Cloud-Trace-Context`;
    - `print` banned (ruff `T20`);
    - `AppError` messages are fixed strings;
    - `debug=False`.
  - **P1-02:** LB request logs (100% sampled), firewall deny logs, NAT logs; queue names; LB hosts `api.<domain>` and `app.<domain>`.
  - **P1-03:** table `audit_log` (append-only for `app_rw`, triggers) with columns `clinic_id`, `occurred_at`, `actor_type`, `actor_id`, `action`, `object_type`, `object_ref`, `result`, `ip`, `request_id`, `details`. "P1-07 owns the list" of actions and `details` keys.
  - **P1-05:**
    - audit actions `key.rotate`, `key.reencrypt`, `key.rebuild_bidx`, `security.decrypt_failed`;
    - "enable Data Access logs for KMS and Secret Manager";
    - never log crypto values.
  - **P1-06:**
    - deploy identities `sa-deploy-*`;
    - alert when a revision fails to become ready;
    - nightly failures open GitHub issues; P1-07 adds paging for prod-impacting ones.
  - **P0-06:** alert on perimeter dry-run violations and policy changes (Admin Activity audit logs are always on).
  - **P0-14:** flow F01 (no PHI in URLs) means LB logs may hold URLs.
- **What counts as PHI here:** any of the HIPAA identifiers linked to a patient or their care. That includes names, phone numbers, emails, addresses, dates (except year), and IP addresses of patients. The free text a patient types or says, and the LLM's replies, are PHI too.
- **Pseudonymous IDs are allowed in logs:** PatNum, AptNum and our UUIDs. Access to logs is restricted (P1-05 PAM `ops-read`) and they are needed for support. This rule is recorded as a decision (§6).
- **Facts to verify at implementation:**
  - Cloud Logging log buckets: regional location (`us-central1`), retention up to 3650 days, **bucket locking** (once locked, retention can't be reduced and the bucket can't be deleted until entries expire), CMEK per bucket;
  - sinks and exclusion filters;
  - Data Access audit log configuration (`google_project_iam_audit_config`);
  - Cloud Monitoring notification channel types (email now; SMS, Slack and webhook are available for later use);
  - uptime checks against HTTPS hosts;
  - OpenTelemetry Python exporters for Cloud Trace and Cloud Monitoring (package names `opentelemetry-exporter-gcp-trace` and `opentelemetry-exporter-gcp-monitoring`);
  - the LB `X-Forwarded-For` format (`<client-ip>,<lb-ip>`).

## 4. Scope
**In scope**
- **Backend:**
  - `core/logging.py`: structlog configuration, field allow-list, scrubber, safe exception formatter, stdlib bridge for third-party loggers, Cloud Logging JSON fields;
  - `core/audit.py`: `audit()`, `audit_now()`, `Actor`, the enums, after-commit mirror to logs;
  - `core/telemetry.py`: OpenTelemetry setup, `stage_timer()`, `Stage` enum, `record_counter()`;
  - an access-log middleware (method, route template, status, duration; no path parameters or query);
  - the client IP helper;
  - `Settings` additions.
- **Tests:**
  - the PHI leak suite (corpus of synthetic PHI through every logging path);
  - a log-call lint test;
  - audit transaction tests;
  - telemetry unit tests.
- **Terraform** `infra/modules/observability/`, called from each env root:
  - log buckets `app-logs` (30 days) and `audit-logs` (retention from `audit_retention_days`, default 2190 = 6 years, **not locked**), CMEK key `logs` (added to `kr-<env>`);
  - sinks and an exclusion so logs are not stored twice;
  - Data Access audit config;
  - log-based metrics, notification channels built from `infra/monitoring/notification_targets.yaml` (email only for now; on-call SMS and chat ready to switch on), alert policies, uptime checks, and dashboards (`latency`, `service-health`).
- **Org-level alerts** (in `infra/org/`, P0-06 code) for policy, perimeter and IAM changes, routed to the prod channels.
- **Docs:**
  - `docs/observability/logging.md`: field allow-list, event naming, what never to log;
  - `docs/observability/audit-actions.md`: the action list;
  - `docs/observability/alerts.md`: each alert, its meaning and first response;
  - `docs/runbooks/alerts/` (one short page per alert).

**Out of scope** (and which task covers it)
- Filling the latency dashboard with real voice stages → P3 tasks (they call `stage_timer()` with the stages defined here)
- Admin console views of the audit log → P4-09 (reads `audit_log`)
- Incident response plan and breach notification → P5-12
- PHI-in-logs scan of real environment logs before go-live → P5-08 (uses the scrubber patterns here)
- Error-tracking SaaS (Sentry etc.) → not used (would be a new vendor; Cloud Error Reporting is used instead, **Verify** it is covered by the Cloud BAA)
- Business analytics (booking rates) → P6 (counters defined here are enough for the pilot report)

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P1-01 Repo (approved spec) | `core/logging.py`, contextvars, `AppError` | Replace the module in place; all tests run locally. |
| P1-03 Cloud SQL + schema (approved spec) | `audit_log` table, `app_rw` role | Audit tests run against the CI Postgres with P1-03's migrations. |
| P1-02 Terraform base (approved spec) | Projects, key ring, LB hosts, queues | Write the module now; apply in dev after P1-02. Uptime checks need the LB hosts with DNS (P1-02 §14). |
| Alert recipients (external) | Email addresses for alerts | Start with the team email group `alerts@`; more people, on-call phones or a chat can be added later in `notification_targets.yaml` (§6). |

## 6. Interface contract

### Logging rules
- **Format:** one JSON object per line on stdout, which Cloud Run sends to Cloud Logging. Field names follow Cloud Logging's structured logging:

```json
{"severity":"WARNING","message":"opendental.rate_limited","time":"2026-11-24T15:02:11.123Z",
 "logging.googleapis.com/trace":"projects/acme-dai-prod/traces/4bf92f3577b34da6a3ce929d0e0e4736",
 "logging.googleapis.com/spanId":"00f067aa0ba902b7",
 "request_id":"7f3c9a1e2b4d4c8e","service":"api","version":"3f9c2e1",
 "clinic_id":"0b6f…","session_id":"9d2e…","endpoint":"appointments","status_code":429,"retry_after_s":2,"attempt":1}
```
- **`message` is an event name:** `^[a-z0-9_]+(\.[a-z0-9_]+)+$`, e.g. `booking.slot_taken`, `opendental.rate_limited`. Never an f-string or a variable. Enforced by test T5.
- **Field allow-list** (`LOG_FIELD_ALLOWLIST` in `core/logging.py`). Any other key is **dropped**, and the drop is counted in metric `dai.log.dropped_fields` with the key name only:

| Group | Allowed fields |
|---|---|
| Correlation | `request_id`, `trace_id`, `span_id`, `session_id`, `clinic_id`, `task_name`, `job` |
| Service | `service`, `version`, `env`, `instance_id` |
| HTTP | `method`, `route` (template, e.g. `/v1/sessions/{session_id}`), `status_code`, `duration_ms` |
| IDs (pseudonymous) | `patnum`, `aptnum`, `callback_id`, `reminder_id`, `staff_user_id`, `config_version` |
| Outcomes | `error_code`, `error_type`, `result`, `reason_code`, `state`, `from_state`, `to_state`, `tool`, `model`, `model_tier`, `stage`, `channel`, `attempt`, `retry_after_s`, `count`, `endpoint`, `provider_status`, `template_id`, `queue` |
| Exceptions | `exc_type`, `exc_frames` (file, line, function only) |

  Adding a field is a code change reviewed by the compliance owner (CODEOWNERS on `core/logging.py`).
- **Scrubber** (last layer; runs on `message`, every string value and exception text). It replaces matches with `[REDACTED:<kind>]`:

| Kind | Pattern (simplified; the real ones are tested) |
|---|---|
| `phone` | `(\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}` |
| `email` | `[\w.+-]+@[\w-]+\.[\w.-]+` |
| `date` | ISO dates, `MM/DD/YYYY`, `Month D, YYYY` |
| `ssn` | `\b\d{3}-\d{2}-\d{4}\b` |
| `ip` | IPv4/IPv6 literals (except in `ip`-free logs by design; staff IPs go only to the audit table) |
| `long_digits` | 9+ consecutive digits (insurance, account numbers) |

  Names and free-text symptoms can't be caught by regex. That is why layers 1 and 2 exist: **patient text, transcripts, LLM prompts and replies are never passed to a logger at all.**
- **Exceptions:**
  - logged with `exc_type` and `exc_frames`;
  - `str(exc)` is included **only** for `AppError` subclasses, whose messages are fixed strings;
  - for any other exception, the text goes through the scrubber and is truncated to 200 characters;
  - locals are never captured.
- **Third-party loggers** (uvicorn, httpx, httpcore, asyncpg, sqlalchemy, google.*) go through the same processors:
  - set to `WARNING`;
  - `uvicorn.access` disabled (our middleware logs route templates instead);
  - SQLAlchemy `echo` always off.
- **Levels:**
  - `DEBUG` is allowed only with `ENV=local`; in cloud environments a `LOG_LEVEL=DEBUG` setting is rejected by a `Settings` validator;
  - prod default is `INFO`.

```python
# backend/app/core/logging.py (shape)
import structlog

def configure_logging(settings: Settings) -> None:
    shared = [
        structlog.contextvars.merge_contextvars,      # request_id, trace_id, session_id, clinic_id
        add_service_fields(settings),                 # service, version, env
        add_cloud_trace(settings.VERTEX_PROJECT),     # logging.googleapis.com/trace
        enforce_event_name,                           # invalid name -> "log.invalid_event" + counter
        allowlist_fields,                             # drop unknown keys
        safe_exception,                               # exc_type, exc_frames, scrubbed text
        scrub_values,                                 # regex layer
        map_severity,                                 # level -> severity
        structlog.processors.TimeStamper(fmt="iso", utc=True, key="time"),
    ]
    ...

log = structlog.get_logger()
log.warning("opendental.rate_limited", endpoint="appointments", retry_after_s=2, attempt=1)
```

### Access log middleware
One line per HTTP request and per WebSocket session end:
- `http.request` with `method`, `route`, `status_code`, `duration_ms`;
- `ws.closed` with `route`, `duration_ms`, `reason_code`.

`route` is the matched route template, never the raw path. Health endpoints are not logged (Cloud Run probes would flood the logs).

### Client IP (`core/net.py`)
```python
def client_ip(request: Request) -> str | None:
    """Client IP as seen by the Google external LB.

    X-Forwarded-For is '<client>, <lb>' (Verify); take the second-to-last entry.
    Never trust the first entry: the client can forge it.
    """
```
The IP is stored **only** in `audit_log.ip` (database, CMEK, P1-03), never in logs. For `PATIENT_SESSION` actors, the IP counts as PHI.

### Audit service (`backend/app/core/audit.py`)
```python
class ActorType(StrEnum):
    SYSTEM = "SYSTEM"
    STAFF = "STAFF"
    PATIENT_SESSION = "PATIENT_SESSION"

class AuditResult(StrEnum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    DENIED = "DENIED"

class ObjectType(StrEnum):
    PATIENT = "patient"
    APPOINTMENT = "appointment"
    CALLBACK = "callback"
    CONSENT = "consent"
    MESSAGE = "message"
    STAFF = "staff"
    CONFIG = "config"
    SESSION = "session"
    KEY = "key"

@dataclass(frozen=True, slots=True)
class Actor:
    type: ActorType
    id: str                      # staff UUID, session UUID, or service name ("api", "reminder-sweep")
    ip: str | None = None        # from client_ip(); None for SYSTEM

async def audit(
    session: AsyncSession,       # the caller's session: the row commits or rolls back with the action
    *,
    action: AuditAction,
    result: AuditResult,
    actor: Actor,
    clinic_id: uuid.UUID | None,
    object_type: ObjectType | None = None,
    object_ref: str | int | None = None,   # IDs only: PatNum, AptNum, UUID
    details: Mapping[str, str | int | bool] | None = None,
) -> None: ...

async def audit_now(**kwargs: Any) -> None:
    """Writes in its own short transaction.

    For events that must be recorded even when the caller's transaction rolls back:
    DENIED and FAILURE results, security events, and read actions such as patient.search.
    """
```
Rules:
- **Fail closed.** If the audit insert fails, the exception propagates. The PHI action in the same transaction is rolled back and the caller returns 500 (`AuditWriteError`). For `audit_now`, the failure is logged as `audit.write_failed` (counter metric, alert A11) and the caller's request also fails, **except** for read-only security events, where availability wins and the failure is only alerted.
- **Validation before insert:**
  - `object_ref` must match `^[0-9]+$` or a UUID;
  - `details` keys must be in `AUDIT_DETAIL_KEYS`, and values must be `bool`, `int`, or `str` of at most 64 characters matching `^[A-Za-z0-9_.:-]*$` (codes, not text).
  - A violation raises `AuditValidationError` (a programming error; tests catch it).
- **Mirror to logs:**
  - an SQLAlchemy `after_commit` listener emits each committed audit row as a log line `audit.event` with `log_type="audit"` and the same fields **except `ip`**;
  - a sink routes these lines to the protected `audit-logs` bucket;
  - if the transaction rolls back, nothing is mirrored, because nothing happened.

`AUDIT_DETAIL_KEYS`: `reason_code`, `error_code`, `channel`, `tool`, `state`, `count`, `attempt`, `role_from`, `role_to`, `config_version`, `template_id`, `provider_status`, `tier`, `match_count`, `identifiers_used` (e.g. `"dob+phone"`, the field names, never values).

### Audit action list (`AuditAction`, closed StrEnum; new actions are a reviewed code change)
| Action | When | object_type / object_ref | Typical details |
|---|---|---|---|
| `patient.search` | Any Open Dental patient lookup | patient / PatNum or none | `match_count`, `identifiers_used` |
| `patient.verify` | Identity verified (≥ 2 identifiers) | patient / PatNum | `identifiers_used` |
| `patient.verify_failed` | Verification failed | patient / none | `reason_code`, `attempt` |
| `patient.create` | New patient created in Open Dental | patient / PatNum | — |
| `patient.update` | Patient fields updated in Open Dental | patient / PatNum | `reason_code` (which group of fields) |
| `appointment.book` / `.reschedule` / `.cancel` | Appointment change in Open Dental | appointment / AptNum | `channel`, `reason_code` |
| `safety.emergency_detected` | Non-`none` emergency result on a turn; added by P2-20 (DECISIONS #203) | session / session_id | `signal`, `source`, `category_ids`, `rules_version`, `fired` |
| `appointment.change_refused` | Reschedule or cancel refused by policy (notice window, not changeable, needs staff); added by P2-18 (DECISIONS #199) | appointment / AptNum | `kind`, `reason_code`, `min_notice_hours`, `checkpoint` |
| `callback.create` / `.status_change` | Callback case created / status changed | callback / UUID | `reason_code`, `state` |
| `callback.email_sent` / `.email_failed` | Admin email outcome | callback / UUID | `attempt`, `error_code` |
| `callback.view_contact` / `.assign` / `.attempt` / `.reopen` / `.email_resend` / `.test_email` | Staff case actions and settings test email; added by P4-13a / P4-13 (DECISIONS #266) | callback / UUID (none for `test_email`) | `reason_code`, `count`, `error_code` |
| `appointment.review` | Staff marked an AI-booked appointment reviewed; added by P4-13a | appointment / AptNum | — |
| `appointment.duplicate_reported` | Staff reported that an AI-created patient is a duplicate; added by P6-02 (DECISIONS #281) | appointment / AptNum | — |
| `pilot.flag_changed` | Pilot flag changed (kill switch or approved turn-on); added by P6-01 (DECISIONS #280) | clinic / UUID | `flag`, `from`, `to`, `approver` |
| `transcript.view` | Reviewer opened a pilot transcript; added by P6-04 (DECISIONS #282) | session / UUID | — |

> **Addition (P5-12, P6-02; DECISIONS #278, #281):** new alert policies `retention-job-failed`, `kpi-double-booking` and `kpi-cancelled-reminder` (email; the last two are SEV1). Every alert policy gets a `documentation` link to its runbook in `docs/runbooks/`.
| `consent.grant` / `.revoke` | Consent change | consent / UUID | `channel`, `template_id` |
| `message.send` / `.skip` / `.fail` | Patient message outcome | message / reminder UUID | `channel`, `template_id`, `reason_code`, `provider_status` |
| `emergency.tier1` / `.tier2` | Emergency escalation | session / UUID | `tier`, `reason_code` |
| `auth.login` / `.login_failed` / `.mfa_failed` / `.logout` | Staff auth (P1-13) | staff / UUID | `reason_code` |
| `staff.create` / `.role_change` / `.deactivate` | Staff admin | staff / UUID | `role_from`, `role_to` |
| `config.update` | Clinic config version created | config / version | `config_version` |
| `audit.view` | Staff viewed the audit log (P4-09) | none | `count` |
| `security.decrypt_failed` / `.clinic_mismatch` / `.rate_limited` / `.injection_suspected` / `.tool_denied` | Security events | varies | `reason_code`, `tool` |
| `key.rotate` / `.reencrypt` / `.rebuild_bidx` | Key tools (P1-05) | key / keyset name | `count` |
| `data.retention_delete` | Retention job (P5-12) | varies | `count` |

### Telemetry (`backend/app/core/telemetry.py`)
```python
class Stage(StrEnum):
    HTTP = "http"
    STT_FIRST_PARTIAL = "stt_first_partial"
    STT_FINAL = "stt_final"
    LLM_FIRST_TOKEN = "llm_first_token"
    LLM_TOTAL = "llm_total"
    TOOL_CALL = "tool_call"
    OPENDENTAL_API = "opendental_api"
    TTS_FIRST_AUDIO = "tts_first_audio"
    VOICE_TO_VOICE = "voice_to_voice"       # end of user speech -> first assistant audio heard
    TEXT_REPLY_FIRST_TOKEN = "text_reply_first_token"
    ENDPOINT_DETECTED = "endpoint_detected"   # added by P3-01 (DECISIONS #224): end of user speech -> endpoint
    BARGE_IN_STOP = "barge_in_stop"           # added by P3-01: user speech detected -> assistant audio stopped
    VOICE_TO_FIRST_SOUND = "voice_to_first_sound"   # added by P3-14 (DECISIONS #247): first audio incl. fillers; VOICE_TO_VOICE excludes fillers and is measured on the browser clock

@contextmanager
def stage_timer(stage: Stage, *, channel: str | None = None, tool: str | None = None,
                model_tier: str | None = None, endpoint: str | None = None) -> Iterator[None]:
    """Records dai.stage.latency (ms histogram) and a trace span named stage.<stage>."""

def record_counter(name: Literal["dai.booking.outcome", "dai.callback.created", "dai.callback.email",   # last added by P2-22 "dai.reminder.outcome",
                                 "dai.opendental.error", "dai.log.dropped_fields", "dai.audit.write_failed"],
                   value: int = 1, **attrs: str) -> None: ...
```
- **Metric `dai.stage.latency`:** a histogram in ms, with buckets 25, 50, 100, 200, 300, 500, 750, 1000, 1500, 2000, 2500, 3000, 5000, 10000. Attributes: `stage`, `channel`, `tool`, `model_tier`, `endpoint`, `env`. **No `clinic_id` or IDs**, to keep cardinality and PHI out.
- **Traces:**
  - exported to Cloud Trace;
  - sample ratio `TRACE_SAMPLE_RATIO`: 1.0 in dev, 0.1 in staging and prod (Proposed);
  - span attributes use the same allow-list as logs;
  - auto-instrumentation for FastAPI, httpx, asyncpg and redis with **URL query and body capture off**.

```python
# Settings additions (extends P1-01)
OTEL_ENABLED: bool = True
TRACE_SAMPLE_RATIO: float = Field(default=0.1, ge=0.0, le=1.0)
METRICS_EXPORT_INTERVAL_S: int = Field(default=60, ge=10)
APP_VERSION: str = "dev"                          # baked into the image (P1-06)

@field_validator("LOG_LEVEL")
...  # DEBUG only when ENV=local
```

### Cloud Logging layout (per environment project)
| Bucket | Location | Retention | Locked | CMEK | Receives |
|---|---|---|---|---|---|
| `app-logs` | us-central1 | 30 days | no | key `logs` | Cloud Run (`api`, `web`, jobs) except audit mirror lines; LB, firewall, NAT, Cloud Tasks, Scheduler logs |
| `audit-logs` | us-central1 | `audit_retention_days` (default **2190 = 6 years**) | **no** (configurable on purpose, see below) | key `logs` | Cloud Audit Logs (Admin Activity, Data Access, System Event, Policy Denied) + app lines with `jsonPayload.log_type="audit"` |
| `_Default` | — | 30 days | — | — | Nothing new: an exclusion on the `_Default` sink drops what the two sinks above store |
| `_Required` | — | 400 days (Google-managed) | — | — | Admin Activity and System Event audit logs (always; cannot be changed) |

```hcl
resource "google_logging_project_bucket_config" "audit" {
  project        = var.project_id
  location       = var.region
  bucket_id      = "audit-logs"
  retention_days = var.audit_retention_days     # default 2190 (6 years); allowed 365-3650
  locked         = var.audit_bucket_locked      # default false; see "Changing audit retention"
  cmek_settings { kms_key_name = var.kms_key_ids["logs"] }
}

resource "google_logging_project_sink" "audit" {
  name        = "to-audit-logs"
  destination = "logging.googleapis.com/projects/${var.project_id}/locations/${var.region}/buckets/audit-logs"
  filter      = "logName:\"cloudaudit.googleapis.com\" OR jsonPayload.log_type=\"audit\""
}

resource "google_project_iam_audit_config" "data_access" {
  for_each = toset(["cloudkms.googleapis.com", "secretmanager.googleapis.com",
                    "sqladmin.googleapis.com", "iam.googleapis.com"])
  project  = var.project_id
  service  = each.value
  audit_log_config { log_type = "ADMIN_READ" }
  audit_log_config { log_type = "DATA_READ" }
  audit_log_config { log_type = "DATA_WRITE" }
}
```
Notes:
- The KMS key `logs` is added to `kr-<env>` (P1-02 `kms` module). The Cloud Logging service agent needs `cryptoKeyEncrypterDecrypter` on it. **Verify** the per-bucket CMEK flow and the service-agent name.
- Log views: a view `audit-readers` on `audit-logs` for `gcp-security-admins` and the PAM `ops-read` entitlement. Developers have no access to prod logs (P1-05).

**Changing audit retention (decided: 6 years by default, changeable without problems).** The client may want a different retention later, longer or shorter, for example after advice on a state law. So the bucket is **not locked**. Locking would make shortening impossible forever. Instead:
- **One setting drives both copies:**
  - `audit_retention_days` in `infra/env/<env>/terraform.tfvars` sets the log bucket;
  - the app setting `AUDIT_RETENTION_DAYS` (same value, mapped by Terraform into the `api` env) sets how long P5-12's retention job keeps `audit_log` rows in the database.
  - Allowed range: 365–3650 days (Cloud Logging maximum, **Verify**). The `Settings` validator and a Terraform `validation` block enforce it.
- **To change it:** a release PR on `releases/tf-prod.yaml` (P1-06) with the new value and the reason. Two `prod-approvers` approve, and the change is applied by Terraform. No code change.
  - Increasing applies at once.
  - Decreasing makes entries older than the new value expire. The PR template for this change asks for the compliance owner's written approval.
- **Protection without the lock:**
  - only `sa-tf-apply-prod` and `gcp-org-admins` can change bucket settings;
  - every change is in Admin Activity audit logs, which are always kept 400 days in `_Required`;
  - alert **A18** fires on any `UpdateBucket` or `DeleteBucket` call or sink change for `audit-logs`;
  - the database `audit_log` table stays append-only (P1-03).
- **If the client later wants the stronger lock**, set `audit_bucket_locked = true` through the same release PR. After that the retention can only be increased.

**Alert recipients and on-call (`infra/monitoring/notification_targets.yaml`).** Decided: **email only for now.** The on-call setup is built and ready, so the client can add people, phone numbers or a chat later by editing one file, with no code change:
```yaml
schema_version: 1
email:                                   # active now: every alert, every severity
  - alerts@example-company.com           # Google Workspace group; add or remove addresses freely
oncall:                                  # ready, empty for now: P1 alerts go here as SMS when filled
  enabled: false
  sms: []                                # E.164 numbers, e.g. "+15551234567" (on-call staff phones, not patients)
  hours: "24x7"                          # or e.g. "Mon-Sat 07:00-22:00 America/New_York" (Proposed; via alert policy snoozes, Verify)
chat:                                    # ready, off for now
  enabled: false
  type: none                             # none | slack | google_chat_webhook
  target: ""                             # Slack channel or webhook URL (webhook URL goes to Secret Manager, never here)
```
- Terraform reads this file (`yamldecode(file(...))`) and creates one notification channel per entry.
- **Severity routing:** P1 goes to email plus on-call SMS (when `oncall.enabled`) plus chat (when enabled); P2 goes to email plus chat; P3 goes to email.
- With today's file, every alert goes to email only.
- **To turn on on-call SMS:** add numbers, set `enabled: true`, open a release PR, and apply.
- **To turn on chat:** a Slack target needs a `vendors.yaml` row first (no PHI, P0-10). A Google Chat webhook needs its URL stored in Secret Manager (`alerts-chat-webhook`), not in the file.
- `check_notification_targets.py` (run in `pr.yml`) validates the file:
  - schema;
  - E.164 numbers;
  - no webhook URLs inline;
  - at least one email.

### Log-based metrics
| Metric | Filter (abridged) | Type |
|---|---|---|
| `log_5xx` | `jsonPayload.message="http.request" AND jsonPayload.status_code>=500` | counter, label `route` |
| `od_rate_limited` | `jsonPayload.message="opendental.rate_limited"` | counter |
| `od_error` | `jsonPayload.message="opendental.error"` | counter, label `error_code` |
| `audit_write_failed` | `jsonPayload.message="audit.write_failed"` | counter |
| `decrypt_failed` | `jsonPayload.message="audit.event" AND jsonPayload.action="security.decrypt_failed"` | counter |
| `callback_email_failed` | `jsonPayload.action="callback.email_failed"` | counter |
| `task_failed` | Cloud Tasks logs with `jsonPayload.status != "OK"` and final attempt (**Verify** field names) | counter, label `queue` |
| `log_dropped_fields` | `jsonPayload.message="log.dropped_field"` | counter, label `field` |
| `firewall_denied` | firewall deny log entries | counter |
| `perimeter_violation` | `protoPayload.metadata.@type="type.googleapis.com/google.cloud.audit.VpcServiceControlAuditMetadata"` | counter, label `dryRun` |

### Alert policies (Proposed thresholds; tune in P5-03)
Severity → channels: see `notification_targets.yaml` above. **Today all severities go to email.** When switched on: **P1** (prod, user-facing) adds on-call SMS and chat; **P2** adds chat. Dev and staging alerts are always P3 (email).

| # | Alert | Condition | Severity (prod) |
|---|---|---|---|
| A1 | Uptime: `api.<domain>/healthz` or `app.<domain>/` | 2 of 3 regions fail for 2 min | P1 |
| A2 | 5xx rate | `log_5xx` > 2% of requests for 5 min | P1 |
| A3 | Revision not ready / instances failing startup | Cloud Run container startup failures > 0 for 5 min (**Verify** metric) | P1 |
| A4 | Voice-to-voice latency | `dai.stage.latency{stage=voice_to_voice}` p95 > 2500 ms for 15 min | P2 |
| A-V2 (P3-14) | Barge-in stop | `stage=barge_in_stop` p95 > 400 ms for 30 min | P3 |
| A-V3 (P3-14) | Voice provider failures | sessions ending `stt_unavailable`/`tts_unavailable` > 5% in 15 min (min 20) | P2 |
| A5 | Text reply latency | `text_reply_first_token` p95 > 3000 ms for 15 min | P2 |
| A6 | Open Dental errors | `od_error` > 5 in 5 min, or `od_rate_limited` > 20 in 5 min | P1 |
| A7 | Queue task failed after all retries | `task_failed` > 0 | P2 (P1 for `callback-emails`) |
| A8 | Callback email failed | `callback_email_failed` > 0 | P1 |
| A-M1 | Patient message finally failed (recipient unreachable or blocked, retries exhausted, delivery failed) | `message_failed_total` for those reasons > 0 in 15 min | P2 (added by P4-01) |
| A-M2 | Messaging configuration broken (template missing, unapproved or paused, token or account error, policy violation) | any such failure | P1 (added by P4-01) |
| A-M3 | Many forged or wrongly signed messaging webhooks | `webhook_signature_invalid_total` > 20 in 10 min | P2 (added by P4-01) |
| A9 | Decrypt failure | `decrypt_failed` > 0 | P1 (possible tampering) |
| A10 | Cloud SQL | CPU > 80% 15 min, or storage > 85%, or instance down | P1 |
| A11 | Audit write failed | `audit_write_failed` > 0 | P1 |
| A12 | Log field dropped | `log_dropped_fields` > 0 in 1 h | P3 (a developer tried to log a non-allowed field) |
| A13 | Perimeter violation | `perimeter_violation{dryRun=false}` > 0 → P2; dry-run → P3 | P2 / P3 |
| A14 | IAM/policy change in prod | Admin Activity: `SetIamPolicy`, org policy or perimeter update, not by `sa-tf-apply-prod` | P2 |
| A15 | Break-glass use | PAM grant activated, or `postgres` user login (Cloud SQL log) | P2 |
| A16 | Redis | memory > 85% or instance down | P1 |
| A18 | Audit bucket or sink changed | Admin Activity: `UpdateBucket`, `DeleteBucket`, `UpdateSink`, `DeleteSink` on `audit-logs` / `to-audit-logs` | P2 |
| A17 | Nightly prod-impacting failure | P1-06 `iam-audit` or `image-vulns` job writes `ci.nightly_failed` via a webhook-to-log path (Proposed) or the issue label is watched | P3 |

Every alert has a runbook page in `docs/runbooks/alerts/<id>.md` (what it means, first 3 checks, whom to call). Alert notifications contain **no PHI**: metric names, counts, and resource names only.

### Dashboards (`infra/monitoring/dashboards/*.json`, `google_monitoring_dashboard`)
- **`latency`:**
  - one row per `Stage` with p50 and p95 lines and the target line (voice-to-voice 1500 / 2500 ms);
  - panels for STT, LLM, TTS and Open Dental per `endpoint`;
  - panels without data show "No data yet (P3)".
- **`service-health`:**
  - requests and 5xx by route; instances; CPU and memory;
  - Cloud SQL CPU, connections, storage;
  - Redis memory;
  - queue depth and failed tasks;
  - Open Dental errors and 429s;
  - booking, callback and reminder outcome counters.

## 7. Implementation guide
1. **Read** P1-01 (`logging.py`, `request_id.py`, errors), P1-03 (`audit_log`), P1-05 (actions, Data Access logs), P1-06 (version, deploy identities), P0-06 (policy alerts), P0-11 R01, R20, R31, and plan §6.
2. **Logging module:**
   1. write the processors and the allow-list;
   2. bridge stdlib logging and disable `uvicorn.access`;
   3. add the access-log middleware and `client_ip()`;
   4. add the `Settings` validator for `LOG_LEVEL`.
3. **PHI leak suite (T1–T5) before anything else uses the logger.** Fixture `phi_corpus.yaml` holds synthetic names, phones in 8 formats, emails, DOBs in 5 formats, addresses, SSN-like strings, and symptom sentences. Each test pushes the corpus through a logging path and asserts that no corpus value appears in the captured output.
4. **Audit service:** enums, `audit()`, `audit_now()`, validation, the after-commit mirror. Tests T6–T10 use the CI Postgres.
5. **Telemetry:** OTel SDK setup in the lifespan (disabled when `OTEL_ENABLED=false`, e.g. in unit tests), `stage_timer()`, counters, auto-instrumentation with capture off (T11, T12).
6. **Terraform `observability` module:**
   1. add the KMS key `logs`;
   2. create the buckets, sinks, exclusion, Data Access config and log views;
   3. add `notification_targets.yaml` with its checker, then the log-based metrics, notification channels (email active; on-call SMS and chat present but disabled), alert policies, uptime checks and dashboards;
   4. apply in dev, then staging.
   5. prod: apply with `audit_retention_days = 2190` and `audit_bucket_locked = false`; test a retention change in staging (2190 → 2555 → 2190) through release PRs to prove the change path.
7. **Org alerts** (A13–A15) through a PR to `infra/org/`.
8. **Verify end to end in dev:**
   - trigger each alert with a test, e.g. a route that returns 500, a fake `opendental.rate_limited` burst, a log call with a non-allowed field;
   - confirm delivery to every channel;
   - confirm that audit rows appear in the DB and their mirror lines in `audit-logs`, and that `app-logs` contains no `audit.event`.
9. **Docs:** `logging.md` (with "never log" rules and examples), `audit-actions.md`, `alerts.md` and the runbook pages.
10. **Notify:**
    - all backend tasks: use `log` with event names, `audit()` in the action's transaction, `stage_timer()`;
    - P1-13: `auth.*` actions;
    - P1-15: `opendental.*` events and `OPENDENTAL_API` stage;
    - P2 and P3 tasks: stages;
    - P4-09: audit table queries and `audit.view`;
    - P5-08: scrubber patterns for the log scan;
    - P5-12: alert runbooks, `AUDIT_RETENTION_DAYS` for the DB retention job.

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| Developer logs `log.info(f"booked for {name}")` | T5 fails in CI (non-literal message). If it reached runtime anyway, `enforce_event_name` replaces the message with `log.invalid_event`, and the scrubber runs on the rest. |
| Developer logs a field `phone=...` | Dropped by the allow-list; `log.dropped_field` with `field="phone"`; A12 alerts. |
| An exception from httpx contains a URL with query parameters or a response snippet | Non-`AppError` text is scrubbed and truncated to 200 characters. Open Dental client errors are wrapped in `AppError` subclasses (P1-15), so their text is fixed. |
| Audit insert fails (DB down) during a booking | The transaction rolls back; the booking is not committed locally. Open Dental may already have the appointment, so P2-16 must record the audit **before** calling Open Dental, as an `IN_PROGRESS` idempotency row plus an audit row, then update. P2-16 owns the ordering. |
| Audit row committed but the log mirror fails (process killed right after commit) | The DB row is the record of truth; the mirror is a copy. P5-12's weekly check compares DB counts and mirror counts per day and reports gaps. |
| Cloud Logging ingestion delayed or unavailable | stdout lines are buffered by Cloud Run; the app never blocks on logging. |
| Metrics exporter fails | OTel drops data after retries; the app continues; A1 and A2 still work, because they are based on logs and uptime checks. |
| Alert storm (many alerts at once during an outage) | Policies use 5-min windows and auto-close; on-call handles A1 first (runbook order). |
| Client asks to change audit retention | Release PR with the new `audit_retention_days` (365–3650) and the reason; 2 approvals; shortening needs the compliance owner's written approval; A18 fires on apply as expected and is acknowledged with the PR link. |
| Someone changes the audit bucket outside Terraform | A18 alerts; Terraform restores the configured value on the next apply; investigate via Admin Activity logs. |
| Client wants to add an on-call person or a phone number | Edit `notification_targets.yaml`, release PR, apply. No code change. |
| Staff IP needed in an investigation | Read from `audit_log.ip` in the DB (PAM `db-breakglass` or P4-09 for admins), not from logs. |
| High-cardinality attribute added to a metric | Review rule: no IDs in metric attributes; T12 checks that `stage_timer` rejects unknown keyword attributes. |

## 9. Security, HIPAA and PHI
- **PHI handled:**
  - **database:** audit rows contain PatNum, AptNum and UUIDs (pseudonymous) and, for patient sessions, the client IP (PHI). They live in Cloud SQL (CMEK, P1-03).
  - **logs:** carry pseudonymous IDs only, never names, contact details, dates of birth, free text, transcripts, prompts, LLM output, IPs of patients, request or response bodies, or query strings.
- **Controls:**
  - three-layer redaction (allow-list, event names, scrubber);
  - fixed `AppError` messages;
  - no uvicorn access logs;
  - DEBUG blocked outside local;
  - tracing with capture off and allow-listed attributes;
  - metric attributes without IDs.
- **Integrity of the audit trail:**
  - append-only table (P1-03);
  - audit in the same transaction, failing closed;
  - a PHI-free copy in a protected log bucket (6 years by default). Only Terraform and org admins can change it, every change is logged and alerted (A18), and it can be locked later if the client wants.
- **Retention:**
  - app logs 30 days;
  - audit logs 6 years by default (`audit_retention_days`, configurable 1–10 years);
  - `_Required` 400 days (Google-managed);
  - all US-only and CMEK-encrypted.
- **Access:**
  - prod logs only via PAM `ops-read`;
  - the audit bucket view for security admins;
  - Data Access logs record who read KMS keys and secrets.
- **HIPAA:**
  - §164.312(b) audit controls;
  - §164.308(a)(1)(ii)(D) information system activity review (dashboards, alerts);
  - §164.308(a)(6) incident detection (alerts feed P5-12);
  - §164.316(b)(2) six-year retention of documentation.
- **Risks reduced:** P0-11 R01, R20, R31.

## 10. Testing
Unit and integration tests (`backend/tests/unit/observability/`, `backend/tests/integration/audit/`):

| # | Test | Expected |
|---|---|---|
| T1 | Every value in `phi_corpus.yaml` passed as an extra field (`name=…`, `phone=…`, `note=…`) | None appears in output; each key is reported as dropped |
| T2 | Corpus values inside allowed string fields (e.g. `reason_code="call 555-123-4567"`) and inside exception messages of `ValueError`, `httpx.HTTPStatusError` | Phones, emails, dates, SSNs and long digits are `[REDACTED:<kind>]` |
| T3 | Request with a JSON body full of corpus values hitting a route that raises | Access log and error log contain no corpus value; no body is logged |
| T4 | Third-party logger (`logging.getLogger("httpx").warning("GET https://x/?phone=5551234567")`) | Output is scrubbed; same JSON format |
| T5 | **Log-call lint:** AST scan of `backend/app/` for `log.<level>(` / `logger.<level>(` whose first argument is not a string literal matching the event-name pattern | No violations |
| T6 | `audit()` inside a transaction that commits | One `audit_log` row; one `audit.event` log line with `log_type="audit"` and no `ip` |
| T7 | `audit()` inside a transaction that rolls back | No row, no log line |
| T8 | `audit()` with `details={"note": "free text"}` or a `details` value with spaces | `AuditValidationError` |
| T9 | Audit insert fails (simulate with a revoked grant) | `AuditWriteError`; the caller's change is rolled back; `audit.write_failed` logged |
| T10 | `audit_now(action=patient.verify_failed, result=FAILURE, …)` while the outer transaction rolls back | Row exists (own transaction) |
| T11 | `stage_timer(Stage.TOOL_CALL, tool="book_appointment")` with an in-memory metric reader | One histogram point with attributes `stage`, `tool`; one span `stage.tool_call` |
| T12 | `stage_timer(Stage.HTTP, patnum=123)` | `TypeError` (unknown attribute not accepted) |
| T13 | `Settings(ENV=prod, LOG_LEVEL="DEBUG")` | `ValidationError` |
| T14 | `client_ip` with `X-Forwarded-For: 1.2.3.4, 9.9.9.9, 35.1.1.1` | Returns `9.9.9.9` (the entry the LB added for the client, second-to-last) |

Cloud checks in dev (recorded in `docs/observability/alerts.md`):
- each alert A1–A18 fired once by a test trigger and was delivered to every configured channel;
- `gcloud logging buckets describe audit-logs --location us-central1` shows retention 2190 and the CMEK key;
- a retention change through a release PR in staging updates the bucket and fires A18 (step 6.5);
- `notification_targets.yaml` with an invalid phone number or an inline webhook URL fails `check_notification_targets.py`;
- a Logs Explorer query on `app-logs` for `jsonPayload.log_type="audit"` returns nothing; the same query on `audit-logs` returns the mirror lines;
- the KMS Data Access logs show the `api` startup decrypt (P1-05).

## 11. Acceptance criteria
- [ ] `core/logging.py` emits Cloud Logging JSON with trace correlation, the field allow-list, event-name enforcement, scrubber and safe exceptions; uvicorn access logs are off; DEBUG is rejected outside local
- [ ] The PHI leak suite (T1–T5) passes with 0 leaks, and request/response bodies are never logged
- [ ] `audit()` writes in the caller's transaction and fails closed; `audit_now()` covers denied, failed, read and security events; `details` and `object_ref` are validated (T6–T10)
- [ ] The action list and `details` keys are documented in `audit-actions.md` and enforced as enums
- [ ] Committed audit rows are mirrored (without IP) to the `audit-logs` bucket: retention from `audit_retention_days` (default 2190), CMEK, changeable only through Terraform with alert A18; the change path was tested in staging
- [ ] `app-logs` (30 days, CMEK) receives app and infrastructure logs; `_Default` stores nothing duplicated
- [ ] Data Access logs are on for Cloud KMS, Secret Manager, Cloud SQL Admin and IAM
- [ ] OpenTelemetry traces and the `dai.stage.latency` histogram work through `stage_timer()` (T11, T12)
- [ ] Alerts A1–A18 exist in prod (as P3 in dev and staging), each with a runbook page; a test alert reached the email recipients; on-call SMS and chat are configurable in `notification_targets.yaml` (disabled now) and the file is validated in CI
- [ ] The `latency` and `service-health` dashboards exist with all panels (P3 panels showing "No data yet")
- [ ] The §7 step 10 issues are notified

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI (T1–T14)
- [ ] PR reviewed (HIPAA review if labelled `phi`): labelled `phi`; reviewed by the tech lead and the compliance owner (allow-list, actions, retention)
- [ ] No PHI in logs: T1–T5 pass, and the dev log sample review after step 8 finds none
- [ ] Docs / README updated: `logging.md`, `audit-actions.md`, `alerts.md`, alert runbooks, the "how to log" section in `backend/README.md`

## 13. Hand-off
| Task | Can rely on |
|---|---|
| All backend tasks | `log = structlog.get_logger()`; event-name messages; allow-listed fields only; `audit()` in the action's transaction, `audit_now()` for denied/failed/read/security events; `stage_timer()` |
| P1-13 Auth | `auth.*` and `staff.*` actions; `Actor(type=STAFF, id, ip=client_ip(request))` |
| P1-15 Open Dental client | `opendental.rate_limited` / `opendental.error` events, `Stage.OPENDENTAL_API` with `endpoint`; errors wrapped in `AppError` |
| P2-01, P2-16, P2-18, P2-22 | `patient.*`, `appointment.*`, `callback.*` actions; audit-before-Open-Dental ordering (§8); `TEXT_REPLY_FIRST_TOKEN` stage |
| P3 voice tasks | `STT_*`, `LLM_*`, `TTS_FIRST_AUDIO`, `VOICE_TO_VOICE` stages; the latency dashboard |
| P4-01, P4-02, P4-04 | `message.*`, `consent.*` actions; A7/A8 alerts on queues |
| P4-09 Admin console | Query `audit_log` (by clinic, action, date); log `audit.view` |
| P5-03 Load tests | Dashboards and alert thresholds to tune |
| P5-08 Log scan | Scrubber patterns and the PHI corpus to scan real logs |
| P5-12 Incident response / retention | Alert runbooks, `AUDIT_RETENTION_DAYS` (default 2190) for the DB audit retention job, DB-vs-mirror count check |

## 14. Open questions
| Question | Owner | Needed by |
|---|---|---|
| The email address(es) for alerts (default `alerts@` group) | Project sponsor | Step 6 |

## 15. References
- Plan §3.2, §5, §6, §9 (pilot targets)
- Cloud Logging structured logging: https://docs.cloud.google.com/logging/docs/structured-logging
- Log buckets, retention and locking: https://docs.cloud.google.com/logging/docs/buckets
- CMEK for Cloud Logging: https://docs.cloud.google.com/logging/docs/routing/managed-encryption-storage
- Sinks and exclusions: https://docs.cloud.google.com/logging/docs/routing/overview
- Data Access audit logs: https://docs.cloud.google.com/logging/docs/audit/configure-data-access
- Log-based metrics: https://docs.cloud.google.com/logging/docs/logs-based-metrics
- Alerting and notification channels: https://docs.cloud.google.com/monitoring/support/notification-options
- Uptime checks: https://docs.cloud.google.com/monitoring/uptime-checks
- OpenTelemetry Python with Google Cloud: https://docs.cloud.google.com/trace/docs/setup/python-ot
- structlog: https://www.structlog.org/
- HHS "Guidance regarding methods for de-identification" (list of identifiers): https://www.hhs.gov/hipaa/for-professionals/privacy/special-topics/de-identification/
- HIPAA Security Rule 45 CFR §164.308, §164.312, §164.316
- Related tasks: P0-06, P0-10, P0-11, P0-14, P1-01, P1-02, P1-03, P1-05, P1-06, P1-13, P1-15, P2-01, P2-16, P2-18, P2-22, P4-01, P4-02, P4-04, P4-09, P5-03, P5-08, P5-12, P6-01
