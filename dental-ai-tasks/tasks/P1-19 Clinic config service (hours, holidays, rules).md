---
id: P1-19
title: Clinic config service (versioned config, validation, console API, session pinning, Open Dental policy)
milestone: P1
epic: E1.3
size: L
labels: area:backend, type:feature
depends_on: P0-01, P0-02, P0-03, P0-08, P1-03, P1-06, P1-07, P1-13, P1-15, P1-16
status: approved
---

# P1-19: Clinic config service (versioned config, validation, console API, session pinning, Open Dental policy)

## 1. Summary
Build the service that holds **every clinic's rules** in one validated, versioned document and serves them to the rest of the backend. The rules cover:
- AI booking hours, holidays, booking horizon, reserved blockouts;
- the appointment-type mapping (P0-02) and the emergency rules (P0-03);
- verification and cancellation policies, callback email settings (P0-08);
- the Open Dental policy (P1-15, P1-16), reminders, voice and privacy.

What it does:
- **Versions:** every change creates a new immutable version in `clinic_config_versions` (P1-03). The clinic's active version is a pointer, and rollback means activating an older version.
- **Edits:** the console (P4-11) edits most sections through an API. **Safety-critical sections** (emergency rules, verification minimums) are file-only, imported through a release PR with approvals (P1-06).
- **Sessions:** each conversation is **pinned** to the version it started with.
- **Propagation:** instances learn about changes through Redis pub/sub, with a 60 s fallback.
- **Open Dental checks:** references to Open Dental (providers, operatories, appointment types, blockout types) are checked on save and daily. A broken reference disables only the affected variant and warns the admin.

Done means:
- the pilot clinic's seed (P0-01, P0-02, P0-03 and P0-08 outputs) imports as version 1 and validates;
- `ClinicODContextProvider` and `ClinicODPolicyProvider` (from P1-15 and P1-16) are backed by real config;
- the console API creates, lists, compares and activates versions with audit entries;
- invalidation reaches every instance and the Open Dental setup cache.

## 2. Why this matters
The product's behaviour comes from the clinic, not from us (P0-01):
- who counts as verified (§4.5);
- what the AI may book, and when (§4.6);
- how emergencies are handled (§4.8);
- where callback emails go (§4.9);
- how far ahead patients can book (DECISIONS #86).

P1-20 (slots), P2-12 (verification), P2-16 and P2-18 (booking, cancellation), P2-20 (emergency detection), P2-22 (callback email), P4-04 (reminders) and P4-11 (console screens) all read these rules. Without one validated source, each would invent its own.

Getting it wrong is visible and risky:
- a wrong holiday lets the AI book a closed day;
- a provider who left keeps getting bookings;
- an unreviewed emergency rule could miss a Tier 1 case (§4.8: rules "must be reviewed and approved by the clinic").

Versioning and session pinning also answer the audit question "which rule did the AI follow in that conversation?"

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P1, Core Platform & Open Dental Adapter**.
- **What already exists:**
  - **P1-03:**
    - `clinics` (`timezone`, `od_customer_key_secret`, `active_config_version`, `status`);
    - `clinic_config_versions` (`clinic_id`, `version`, `config` jsonb, `schema_version`, `created_by_staff_id`, `change_note`, `created_at`; immutable through an append-only trigger);
    - `sessions` (this task adds `config_version`);
    - `ClinicScopedRepository`.
  - **P0-02:** `appointment_types.yaml` and its JSON Schema, the load-time rules table (§6 of P0-02), and the synthetic fixture `backend/tests/fixtures/clinic_config/appointment_types.example.yaml`.
  - **P0-03:** `emergency_rules.yaml` and its JSON Schema, plus load-time rules. Status lifecycle: `draft` → `clinic_reviewed` → `approved`; **production loads only `approved`** (DECISIONS #14).
  - **P0-08:** callback keys `callback.admin_emails`, `after_hours_emails`, `email_mode` (`link_only` default), `full_details_approval`, with load-time rules (no consumer domains, domain readiness, `full_details` needs approval).
  - **P0-01:** workshop answers with defaults:
    - Q1: name + DOB + mobile or ZIP;
    - Q5: 24 h cancellation notice; inside it the AI creates a callback;
    - Q8: messaging channel;
    - Q9: no transcripts;
    - Q10: single location;
    - B3, B4, B8;
    - B5: hours, holidays, reserved slots.
  - **DECISIONS #86:** `scheduling.booking_horizon_days`, default 7, range 1–365, editable by the Admin role.
  - **P1-13:** `Permission.CONFIG_READ` / `CONFIG_WRITE`, `require()`, CSRF, internal OIDC auth.
  - **P1-07:** `audit()` (action `config.update`), event logging.
  - **P1-15:** the `ClinicODContextProvider` protocol, `OpenDentalSetup.invalidate()`, `od-setup-refresh` daily job, setup models (providers, operatories, appointment types, `ScheduleBlock` with `blockout_def_num`).
  - **P1-16:** the `ClinicODPolicyProvider` protocol and the `open_dental.*` keys with defaults.
  - **P1-06:** release PRs with approvals (`releases/<env>.yaml`), the `migrate` job pattern.
- **Open Dental schedules vs our hours:** Open Dental's schedules already say when each provider works and which blockouts exist (P1-15 `ScheduleBlock`: `SchedType` Provider/Practice/Blockout, `blockout_def_num`). Proposed (DECISIONS #138):
  - provider availability comes **only** from Open Dental;
  - our `hours` are an extra **AI booking window** (the AI never offers slots outside it), and our `holidays` close whole days even if Open Dental has a schedule;
  - reserved slots are Open Dental blockout types listed by DefNum.
- **Blockout types** are definitions in Open Dental (category 25, P1-16 research: https://www.opendental.com/site/apidefinitions.html). **Verify:** list them with `GET /definitions?Category=25` on test DB (B) and confirm that `ScheduleBlock.blockout_def_num` holds the same DefNum.

## 4. Scope
**In scope**
- **Package `backend/app/domain/clinic_config/`:**
  - `models.py` (`ClinicConfig` and its sections);
  - `rules.py` (load-time rules);
  - `service.py` (`ClinicConfigService`);
  - `cache.py` (in-process cache and pub/sub);
  - `od_check.py` (Open Dental reference check);
  - `providers.py` (`ConfigClinicODContextProvider`, `ConfigClinicODPolicyProvider`);
  - `cli.py` (`validate`, `import`, `export`, `diff`).
- **Seed layout** `backend/app/domain/clinic_config/seed/<clinic_slug>/`: `clinic.yaml`, `appointment_types.yaml` (P0-02), `emergency_rules.yaml` (P0-03). Plus a JSON Schema `schemas/clinic.schema.json` generated from the Pydantic model and checked into git (CI fails if stale).
- **Admin API** `backend/app/api/admin/config.py`: read, versions, diff, create version (PATCH), activate.
- **Internal endpoint** `POST /internal/jobs/config-od-check`, called after `od-setup-refresh`. Also a Cloud Run job `config-import`, run by the release pipeline for file-only sections.
- **Migration:** expand-only `sessions.config_version` (int, NULL) with a composite FK to `clinic_config_versions`.
- **CI:** `python -m app.domain.clinic_config validate` over every seed folder and the fixtures, and a check that the generated schema is current.
- **Docs:** `docs/clinic-config.md` covering sections, the edit matrix, the import process and rollback.

**Out of scope** (and which task covers it)
- Console screens for these sections → P4-11 (calls this API)
- Using hours, holidays and blockouts to compute slots → P1-20
- Emergency detection logic → P2-20
- Verification and matching logic → P2-12
- Sending callback emails → P2-22
- Reminder scheduling → P4-04
- Clinical sign-off of emergency rules for production → P5-15
- Terraform-level settings (audit retention, etc.) → P1-07 (not clinic config)

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P1-03 (approved) | Tables, append-only trigger, repository base | Use its migration |
| P0-02, P0-03, P0-08, P0-01 (approved) | Schemas, load-time rules, fixtures, default values | The synthetic fixtures exist; the pilot seed files arrive after the workshop. Use `seed/example-dental/` (synthetic) until then |
| P1-13 (approved) | `require(Permission.CONFIG_WRITE)`, internal auth | Use the spec signatures; tests use P1-13's test principal factory |
| P1-15 / P1-16 (approved) | Provider protocols, `OpenDentalSetup` | Run against `od_fake`, whose seed includes providers, operatories, appointment types and blockouts |
| P1-07 (approved) | `audit()`, logging | Spec signatures |
| P1-06 (approved) | Release PR flow for `config-import` | Run the CLI locally until the pipeline step exists |

## 6. Interface contract

### Config document (`ClinicConfig`, `schema_version: 1`)
```yaml
# seed/example-dental/clinic.yaml (synthetic). appointment_types and emergency_rules come from their own files.
schema_version: 1
clinic:
  display_name: "Example Dental"
  public_phone_e164: "+15035550100"       # the clinic's own number (not PHI); used in scripts {callback_phone}
  website_url: "https://example-dental.test"
hours:                                    # AI booking window, clinic local time; Open Dental schedules still decide provider availability
  mon: [{start: "08:00", end: "12:00"}, {start: "13:00", end: "17:00"}]
  tue: [{start: "08:00", end: "17:00"}]
  wed: [{start: "08:00", end: "17:00"}]
  thu: [{start: "08:00", end: "17:00"}]
  fri: [{start: "08:00", end: "14:00"}]
  sat: []
  sun: []
holidays:                                 # clinic local dates
  - {date: "2026-12-25", name: "Christmas Day", closed: true}
  - {date: "2026-12-31", name: "New Year's Eve", closed: false, hours: [{start: "08:00", end: "12:00"}]}
scheduling:
  booking_horizon_days: 7                 # DECISIONS #86; 1–365
  min_lead_minutes: 120                   # routine bookings: earliest offer = now + this (DECISIONS #142)
  min_lead_minutes_urgent: 30             # Tier 2 urgent bookings (P0-03): earliest offer = now + this
  options_per_offer: 3                    # §4.6: offer 2–3
  reserved_blockouts:                     # Open Dental blockout DefNums (category 25)
    new_patient: []                       # slots inside these blockouts go to new patients only
    emergency: []                         # only Tier 2 urgent bookings (P0-03)
  other_blockouts_block_booking: true     # any other blockout = not bookable
appointment_types: {}                     # the P0-02 document, embedded unchanged (file: appointment_types.yaml)
emergency_rules: {}                       # the P0-03 document, embedded unchanged (file: emergency_rules.yaml)
verification:                             # file-only
  required: [full_name, dob]
  one_of: [mobile_phone, zip_code]        # P0-01 Q1
  max_attempts: 3                         # P1-13 / P2-12
policies:
  cancel_min_notice_hours: 24             # P0-01 Q5
  reschedule_min_notice_hours: 24
  inside_notice_action: callback          # callback | allow
  new_patient_auto_create: true           # P0-01 B4
callback:                                 # P0-08
  admin_emails: ["frontdesk@example-dental.test"]
  after_hours_emails: []                  # empty = same as admin_emails
  email_mode: link_only                   # link_only | full_details
  full_details_approval: null
  promise_business: "Our team will call you back within one business day."   # P0-01 B6
  promise_urgent: "Our team will call you back today."
  promise_urgent_after_hours: "Our team will call you as soon as the office opens."   # added by P2-22 (DECISIONS #207)
open_dental:                              # P1-15, P1-16 (DECISIONS #127, #133–#135)
  clinic_num: null
  version: null                           # e.g. "24.3.10"; drives feature flags below
  phone_search_mode: legacy_phone
  existing_patient_statuses: [Patient, Inactive]
  new_patient_phone_field: WirelessPhone
  max_search_results: 25
  booking:
    note_text_new_patient: "Booked online by the AI receptionist. New patient: please review."
    note_text_existing: "Booked online by the AI receptionist."
    confirmed_defnum_new_patient: null
    confirmed_defnum_existing: null
  cancel:
    send_to_unscheduled_list: true
reminders:                                # P4-04; channel decided per P0-01 Q8 / P0-07a
  enabled: false
  channel: whatsapp                       # whatsapp | sms
  confirmation_enabled: false
  offset_minutes: 60
voice:
  language: en-US                         # only en-US in the MVP
  tts_voice: null                         # null = P3 default voice
  speaking_rate: 1.0                      # 0.8–1.2
  pronunciations: {}                      # added by P3-03 (DECISIONS #232): word → respelling, max 50, letters/spaces/hyphens/apostrophes; console-editable
privacy:
  transcript_retention_days: 0            # P0-01 Q9: 0 = none; max 30
widget: {}                                # added by P2-25 (DECISIONS #211): allowed_origins, accent_color, logo_url, launcher_label; console-editable
clinic_info: {}                           # added by P1-22 (DECISIONS #152): address, parking, insurers_accepted, services, languages, payment, new_patients, provider_bios; console-editable
conversation: {}                          # added by P2-01 (DECISIONS #157): not_understood_limit (2), recent_turns (6), max_turn_chars (1000); console-editable
```

```python
class TimeRange(BaseModel):
    start: time
    end: time                              # end > start; minutes multiple of 5

class Holiday(BaseModel):
    date: date
    name: str = Field(max_length=80)
    closed: bool = True
    hours: list[TimeRange] = []            # only when closed is False

class ClinicConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal[1]
    clinic: ClinicInfo
    hours: WeeklyHours
    holidays: list[Holiday]
    scheduling: SchedulingPolicy           # booking_horizon_days: int = Field(7, ge=1, le=365) …
    appointment_types: AppointmentTypeMapping   # P0-02 model (validated also against its JSON Schema)
    emergency_rules: EmergencyRules             # P0-03 model
    verification: VerificationPolicy
    policies: BookingPolicies
    callback: CallbackSettings
    open_dental: OpenDentalSettings
    reminders: ReminderSettings
    voice: VoiceSettings
    privacy: PrivacySettings
```
One section model per block above. Each section model also uses `extra="forbid"`.

### Edit matrix
| Section | Console (PATCH, `CONFIG_WRITE`) | File import (release PR) |
|---|---|---|
| `clinic`, `hours`, `holidays`, `scheduling`, `policies`, `callback`, `reminders`, `voice` | yes | yes |
| `appointment_types` | yes (provider, operatory, `bookable_by_ai`, variant enable/disable); structure changes by file | yes |
| `open_dental` | yes, except `version` and `clinic_num` (set at onboarding by file) | yes |
| `privacy` | no: transcript retention is a compliance setting (file + compliance owner approval) | yes |
| `emergency_rules` | **no** (view only) | yes |
| `verification` | **no** (view only) | yes |

Locked sections and fields are listed in `rules.LOCKED_FOR_CONSOLE`. A PATCH touching them returns 403 `config_section_locked`.

> **Addition (P6-01, DECISIONS #280):** new section `pilot` (`chat_enabled`, `voice_enabled`, `reminders_enabled`, `ai_hours`, `unlisted_only`, `closed_message_key`). Switching a channel off is one console action (`pilot:kill`); switching on, `ai_hours` and `unlisted_only` changes need a second approver through `config_change_requests` kind `pilot_enable`. **Addition (P6-04, DECISIONS #282):** `privacy.transcript_retention_days` may be set to 14 for the pilot only with the clinic's written consent (file-only, release PR).

> **Addition (P4-13, DECISIONS #266):** new key `conversation.greeting_override` (null = P2-04 default; ≤ 200 chars; placeholders `{assistant_name}` and `{clinic_name}` only; no URLs, phone numbers or emails). `reminders.channel`, `callback.email_mode` and `callback.full_details_approval` are added to `LOCKED_FOR_CONSOLE`. New rules: `callback.promise_*` 10–200 chars with no `{`/`}`; `admin_emails` 1–5, `after_hours_emails` 0–5.

> **Addition (P4-11, DECISIONS #264):** in `appointment_types`, `duration_min` is console-editable **only** for variants with `od_appointment_type_num: null` (typed variants take their length from the Open Dental appointment type pattern, P1-20); editing it on a typed variant returns 403 `config_section_locked`. New range rules: `min_lead_minutes` 0–1440, `min_lead_minutes_urgent` 0–240, `options_per_offer` 2–3, `cancel_min_notice_hours` / `reschedule_min_notice_hours` 0–168, untyped `duration_min` 10–240, and one blockout type may not be in both `reserved_blockouts.new_patient` and `.emergency`. `GET /v1/admin/config/diff` gains an optional `section` filter (e.g. `section=emergency_rules`). New endpoint `POST /v1/admin/config/preview-availability` (counts only, stores nothing) is defined in P4-11 §6.6.

### Load-time rules (`rules.py`; run on every new version, import and activation)
| Rule | Source | On failure |
|---|---|---|
| All P0-02 load-time rules (reason codes once, `other` not bookable, approved needs Open Dental numbers, duration multiple of increment, ages) | P0-02 | Reject |
| All P0-03 load-time rules (unique IDs, tier prefixes, scripts, placeholders, advice words, reviewed_by) | P0-03 | Reject |
| `emergency_rules.status`: `approved` in prod; `clinic_reviewed` or `approved` in dev and staging; `draft` only in `ENV=local` | DECISIONS #14 | Reject activation |
| P0-08 rules: no consumer email domains; domain passed readiness; `full_details` without `full_details_approval` → treated as `link_only` + warning | P0-08 | Reject / warn |
| `verification`: `required` contains `dob` and a name; `required` + `one_of` gives ≥ 2 identifiers; phone can never be the only identifier | §4.5 | Reject |
| Hours: ranges sorted, non-overlapping, 5-minute granularity; at least one open day | ours | Reject |
| Holidays: unique dates; `hours` only when `closed: false` | ours | Reject |
| No holiday in the next 365 days, or none past 60 days from now | ours | Warning (stale calendar) |
| `booking_horizon_days` 1–365; `min_lead_minutes` 0–2880; `min_lead_minutes_urgent` 0–`min_lead_minutes`; `options_per_offer` 2–3 | #86, #142, §4.6 | Reject |
| Free-text fields (notes, promises, names) contain no `{` placeholders except the allowed ones and ≤ 300 chars | ours | Reject |
| `privacy.transcript_retention_days` 0–30 | §5, P0-01 Q9 | Reject |
| `reminders.enabled: true` requires `channel` approved for this clinic (P0-07a decision recorded) | P0-07a | Reject |
| `reminders.offset_minutes` is an integer in 30–240 (added by P4-04, DECISIONS #260); a change applies only to appointments booked afterwards | P4-04 | Reject |

### Open Dental reference check (`od_check.py`)
```python
@dataclass(frozen=True)
class OdCheckResult:
    checked_at: datetime
    disabled_variants: frozenset[tuple[str, int]]    # (reason code, variant index)
    unknown_blockout_defnums: frozenset[int]
    warnings: tuple[str, ...]                        # codes only, e.g. "provider_inactive:4"
    od_reachable: bool

async def check_od_references(ctx: ClinicODContext, cfg: ClinicConfig, setup: OpenDentalSetup) -> OdCheckResult: ...
```
What it checks:
- every `od_prov_num` exists and isn't hidden;
- every operatory exists and isn't hidden;
- every `od_appointment_type_num` exists and isn't hidden;
- the Open Dental appointment length matches `duration_min` (warning only; Open Dental wins);
- every reserved blockout DefNum exists (`GET /definitions?Category=25`, a new P1-15 setup kind `blockout_types`, cached 6 h).

Behaviour:
- **Result storage:** stored in Redis `cfg:odcheck:{clinic_id}:{version}` (TTL 48 h) and returned with the config.
- **Open Dental unreachable:** `od_reachable=False`, nothing is disabled, and the previous result is kept.
- **When it runs:** on save, on activation, and daily via `POST /internal/jobs/config-od-check` (Scheduler, 09:30 UTC, after `od-setup-refresh`).
- **When something new breaks:** log `config.od_reference_invalid` (codes only) and set the console banner flag. The P1-07 log metric gives a P3 alert.

### Service (`service.py`)
```python
@dataclass(frozen=True)
class ActiveConfig:
    clinic_id: uuid.UUID
    version: int
    config: ClinicConfig
    od_check: OdCheckResult | None
    tz: ZoneInfo                                   # from clinics.timezone

class ClinicConfigService:
    async def active(self, clinic_id: uuid.UUID) -> ActiveConfig: ...
    async def get_version(self, clinic_id: uuid.UUID, version: int) -> ActiveConfig: ...
    async def list_versions(self, clinic_id: uuid.UUID, *, limit: int = 50) -> list[ConfigVersionMeta]: ...
    async def create_version(self, clinic_id: uuid.UUID, cfg: ClinicConfig, *, actor: Actor, change_note: str,
                             source: Literal["console", "import", "system"], activate: bool) -> int: ...
    async def activate(self, clinic_id: uuid.UUID, version: int, *, actor: Actor, change_note: str) -> None: ...
    async def pin_session(self, session_id: uuid.UUID, clinic_id: uuid.UUID) -> ActiveConfig: ...   # sets sessions.config_version
    async def for_session(self, session_id: uuid.UUID) -> ActiveConfig: ...                         # pinned version
```
- **`create_version`** runs everything in one transaction:
  1. validate the model and the rules;
  2. `version = max + 1`;
  3. insert;
  4. update `clinics.active_config_version` if `activate`;
  5. `audit(action=AuditAction.CONFIG_UPDATE, object_type="config", object_ref=str(version), details={"config_version": version, "reason_code": source, "sections": [...]})`.

  After commit it publishes to `cfg:changed` and calls `OpenDentalSetup.invalidate(clinic_id)` when `open_dental` or `appointment_types` changed.
- **`activate`** re-runs the rules for the current environment (an old version may have `clinic_reviewed` rules that prod now refuses), then the same audit, publish and invalidate steps.
- **Concurrency:** `create_version` takes `pg_advisory_xact_lock(hashtext('cfg:' || clinic_id))`, so version numbers never collide.

### Cache (`cache.py`)
- **Versions are immutable:** each instance keeps an LRU (64 entries) keyed by `(clinic_id, version)`.
- **Active version pointer:** held per clinic, refreshed by:
  - Redis pub/sub channel `cfg:changed` (message `{"clinic_id": "...", "version": 4}`; no PHI);
  - a fallback check of `clinics.active_config_version` at most every **60 s**.
- **Redis down:** the 60 s database check still works.
- **`pin_session`** reads the pointer fresh from the database, so a new session never starts on an outdated version.

### Providers (replace the P1-15 and P1-16 stubs)
```python
class ConfigClinicODContextProvider(ClinicODContextProvider):
    async def get(self, clinic_id: uuid.UUID) -> ClinicODContext: ...   # clinics row + config.open_dental.clinic_num
class ConfigClinicODPolicyProvider(ClinicODPolicyProvider):
    async def get(self, clinic_id: uuid.UUID) -> ClinicODPolicy: ...    # config.open_dental → ClinicODPolicy
```
Both use the **active** config. Writes in flight use the policy read at their start.

### Admin API (all `/v1/admin/config`, staff session + CSRF from P1-13; the clinic comes from the staff principal)
| Method and path | Permission | Request | Response |
|---|---|---|---|
| `GET /v1/admin/config` | `CONFIG_READ` | - | `{version, config, od_check, warnings, locked_sections}` (+ `timezone` read-only and `od_holidays_supported`, added by P4-09, DECISIONS #262) |
| `GET /v1/admin/config/versions?limit=50` | `CONFIG_READ` | - | `[{version, created_at, created_by, source, change_note, active}]` |
| `GET /v1/admin/config/versions/{v}` | `CONFIG_READ` | - | `{version, config}` |
| `GET /v1/admin/config/diff?from=3&to=4` | `CONFIG_READ` | - | `{changes: [{path: "scheduling.booking_horizon_days", from: 7, to: 14}]}` |
| `PATCH /v1/admin/config` | `CONFIG_WRITE` | `{base_version, changes: {<section>: {…partial…}}, change_note}` | `201 {version}` |
| `POST /v1/admin/config/activate` | `CONFIG_WRITE` | `{version, change_note}` | `200 {version}` |

PATCH rules:
- **Merge:** a JSON merge (RFC 7396) of `changes` into the active config. Lists are replaced, not merged.
- **Concurrency:** `base_version` must equal the active version, else 409 `config_version_conflict`. This stops two admins overwriting each other.
- **Change note:** `change_note` is required (5–500 chars) and staff are told not to include patient data. It is still checked against a simple pattern list (dates of birth, phone numbers) and rejected if one matches.

Error bodies use P1-01's `AppError` shape:
| Code | HTTP | When |
|---|---|---|
| `config_validation_failed` | 422 | Schema or a load-time rule fails; body lists `{path, rule}` (no values) |
| `config_section_locked` | 403 | PATCH touches a file-only section or field |
| `config_version_conflict` | 409 | `base_version` is stale |
| `config_not_allowed_in_env` | 422 | Activation refused (e.g. emergency rules not `approved` in prod) |
| `config_version_not_found` | 404 | Unknown version (or another clinic's) |

### CLI and release import (`cli.py`)
```bash
python -m app.domain.clinic_config validate --dir backend/app/domain/clinic_config/seed/example-dental
python -m app.domain.clinic_config diff --clinic example-dental --dir seed/example-dental     # file vs active
python -m app.domain.clinic_config import --clinic example-dental --dir seed/example-dental \
       --sections emergency_rules,verification --note "Emergency rules v0.2 (dentist reviewed)" --activate
python -m app.domain.clinic_config export --clinic example-dental --version 4 --out /tmp/cfg-v4
```
- **First import** (no active version): all sections are taken from the files, as version 1.
- **Later imports:** only the listed `--sections` are taken from the files. Every other section is copied from the active version, so console edits are never lost.
- **In cloud environments**, imports run only as the Cloud Run job `config-import` (`sa-migrate` identity, P1-05), triggered by the promote workflow when the release file lists:
```yaml
# releases/prod.yaml (P1-06), added field
config_imports:
  - {clinic: example-dental, sections: [emergency_rules], note: "Emergency rules approved by Dr. A. Smith (P5-15)", activate: true}
```
  The release PR needs the normal prod approvals (two of A/B/C, DECISIONS #110). For `emergency_rules` it also needs the dentist's sign-off reference in the note. `check_release_approvals.py` gains one check: `emergency_rules` imports to prod require `status: approved` in the file.

### Migration
```sql
ALTER TABLE app.sessions ADD COLUMN config_version int NULL;
ALTER TABLE app.sessions ADD CONSTRAINT sessions_config_version_fk
  FOREIGN KEY (clinic_id, config_version) REFERENCES app.clinic_config_versions (clinic_id, version);
```

### Log events
| Event | Fields |
|---|---|
| `config.version_created` | `clinic_id`, `config_version`, `reason_code` (source), `activated` |
| `config.activated` | `clinic_id`, `config_version` |
| `config.validation_failed` | `clinic_id`, `rule`, `path` |
| `config.od_reference_invalid` | `clinic_id`, `config_version`, `count` |
| `config.cache_refreshed` | `clinic_id`, `config_version`, `via` (`pubsub`/`poll`) |

## 7. Implementation guide
1. **Read** P0-01 (answers), P0-02, P0-03, P0-08 (rules and fixtures), DECISIONS #9–#14, #86, #126–#127, #133–#135, and P1-15 and P1-16 §6. **Verify** the blockout definitions (`GET /definitions?Category=25`) and the `blockout_def_num` link on test DB (B).
2. **Models:**
   - section models;
   - embed the P0-02 and P0-03 models, validated also against their JSON Schemas with `jsonschema` (Draft 2020-12);
   - generate `clinic.schema.json` (`model_json_schema()`) and add the CI staleness check.
3. **`rules.py`:** every rule in the table, each a small function returning `RuleViolation(path, rule)` with no values. Unit tests T1–T8.
4. **Seed folder** `seed/example-dental/` with all three files (synthetic) and a `README.md`. Validate it in CI.
5. **Service and cache:**
   - versions, advisory lock, audit, pub/sub, fallback poll, `pin_session`, the migration (T9–T13);
   - wire `pin_session` into session creation (the P2-01 hook: document the call; P2-01 calls it).
6. **`od_check.py`:**
   - add the setup kind `blockout_types` to P1-15's `OpenDentalSetup` (a small extension, same cache rules);
   - the internal job and Scheduler job via P1-02 tfvars (T14–T15).
7. **Providers:** replace the P1-15 and P1-16 stubs (T16).
8. **Admin API:** merge-patch, locked sections, conflict, diff, activate (T17–T20).
9. **CLI and release import:**
   - `validate`, `diff`, `import`, `export`;
   - the `config-import` Cloud Run job definition (Terraform, like `migrate`);
   - the `config_imports` field and the new check in P1-06's scripts (T21).
10. **Docs and notify:**
    - P1-20: hours/holidays/horizon/blockouts semantics;
    - P2-01: `pin_session`/`for_session`;
    - P2-12: verification;
    - P2-16 and P2-18: policies;
    - P2-20: emergency rules;
    - P2-22: callback;
    - P4-04: reminders;
    - P4-11: API, edit matrix, warnings;
    - P5-15: prod import path;
    - P6-01: onboarding import.

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| Admin changes booking horizon from 7 to 14 while 3 conversations are running | Running sessions keep version N (pinned); new sessions get N+1; audit row with `config_version` |
| Two admins edit at the same time | The second PATCH gets 409 `config_version_conflict`; the console reloads and shows the diff |
| Admin tries to edit emergency rules in the console | 403 `config_section_locked`; console shows them read-only with the release-PR process link |
| A provider in the mapping leaves (hidden in Open Dental) | Daily check disables that variant; the reason falls back to `when_not_bookable` (callback); console banner + P3 alert; clinic updates the mapping |
| Open Dental down during save | Save allowed; `od_check.od_reachable=false`; previous check result kept; re-checked daily |
| Holiday falls inside the booking horizon but Open Dental has a schedule that day | Day closed for the AI (holidays win) |
| Holiday list runs out (none in the next 60 days) | Warning on every save and in the console; no block |
| Prod activation of an old version whose emergency rules were `clinic_reviewed` | Refused: `config_not_allowed_in_env` |
| Redis pub/sub message lost | Instance picks up the new pointer within 60 s; sessions already pinned are unaffected |
| Seed file has an unknown field | Rejected (`extra="forbid"`); CI fails before merge |
| `full_details` set without approval | Saved as given but treated as `link_only` at send time; warning shown (P0-08) |
| Change note contains a phone number | 422; the note isn't stored |
| Rollback to version 2 | `activate(2)` creates no new version; audit `config.update` with `reason_code=rollback`; caches invalidated |
| Clinic `PAUSED` | Config still readable; P2 refuses new sessions (outside this task) |

## 9. Security, HIPAA and PHI
- **PHI handled: none by design.** The config holds clinic facts: hours, Open Dental numbers, staff-facing texts, the clinic's public phone and admin email addresses (clinic-controlled mailboxes; not patient data).
- **What keeps PHI out:**
  - `extra="forbid"`;
  - a fixed set of allowed placeholders;
  - change notes checked against simple PHI patterns;
  - the P1-07 logging allow-list. Logs and API errors carry paths and rule names, never values.
- **Who can change what:**
  - Admin role only (`CONFIG_WRITE`, P1-13);
  - every new version and activation is audited (`config.update`), in the same transaction (fail closed);
  - versions are immutable through the P1-03 trigger.
- **Safety-critical sections** (`emergency_rules`, `verification`, `privacy`) can only change through a reviewed file and a release PR with prod approvals. The prod emergency rules must be `approved` (P5-15 sign-off).
- **Tenant isolation:** every query is clinic-scoped (`ClinicScopedRepository`). Another clinic's version IDs return 404.
- **Risks reduced:**
  - an unreviewed emergency rule in production (§4.8);
  - AI booking on closed days or with departed providers;
  - silent config drift (versions plus audit).

## 10. Testing
| # | Test | Expected |
|---|---|---|
| T1 | Load `seed/example-dental/` and the P0-02/P0-03 fixtures | Valid `ClinicConfig` |
| T2 | Each P0-02 and P0-03 negative fixture (missing reason, bad tier prefix, bad placeholder…) | Rejected with the matching rule name |
| T3 | `verification.required=[mobile_phone]`, `one_of=[]` | Rejected (phone alone) |
| T4 | Overlapping hours, 7-minute boundary, holiday with `closed: true` and hours | Rejected each |
| T5 | `booking_horizon_days` 0 and 366; 14; `min_lead_minutes_urgent` 150 with `min_lead_minutes` 120; PATCH both lead times to 60/15 | Rejected; accepted; rejected; accepted (console-editable) |
| T6 | `emergency_rules.status=clinic_reviewed` with `ENV=prod` / `ENV=staging` | Activation refused / accepted |
| T7 | Unknown field anywhere | Rejected |
| T8 | Error output for a bad email domain | Contains path and rule, not the address |
| T9 | `create_version` twice concurrently | Versions N+1 and N+2; no collision |
| T10 | Update attempt on `clinic_config_versions` row | Refused by trigger |
| T11 | Pinned session after activation of a new version | `for_session` returns the old version; new session gets the new one |
| T12 | Pub/sub message → other instance (two app processes) | Picks up within 1 s; with pub/sub disabled within 60 s |
| T13 | Every create/activate | One `config.update` audit row in the same transaction; audit failure rolls back the version |
| T14 | `od_fake` with provider 4 hidden | Variant using it disabled; warning code `provider_inactive:4`; event logged |
| T15 | `od_fake` down during check | `od_reachable=false`; previous result kept; nothing newly disabled |
| T16 | Providers | `ClinicODContext` has tz and `clinic_num` from config; `ClinicODPolicy` matches `open_dental` section |
| T17 | PATCH `scheduling.booking_horizon_days: 14` as Admin; as Front Desk | 201 new version; 403 |
| T18 | PATCH touching `emergency_rules` | 403 `config_section_locked` |
| T19 | PATCH with stale `base_version` | 409 |
| T20 | `diff?from=1&to=2`; activate(1) | Path-level changes; version 1 active again, audit `reason_code=rollback` |
| T21 | CLI `import --sections emergency_rules` after a console edit to `hours` | New version has the file's emergency rules and the console's hours |

## 11. Acceptance criteria
- [ ] `ClinicConfig` covers every section in §6 with `extra="forbid"`; the generated `clinic.schema.json` is current (CI)
- [ ] All load-time rules from P0-02, P0-03, P0-08 and §6 run on save, import and activation; failures report path and rule only (T1–T8)
- [ ] Every change creates an immutable version with an audit entry in the same transaction; rollback works by activation (T9, T10, T13, T20)
- [ ] Sessions are pinned to their starting version; new sessions see a change within 60 s on every instance, usually within 1 s (T11, T12)
- [ ] Safety-critical sections are not editable through the console; prod accepts only `approved` emergency rules; release-PR import works (T6, T18, T21)
- [ ] Open Dental references are checked on save, activation and daily; broken references disable only the affected variant and warn (T14, T15)
- [ ] `ConfigClinicODContextProvider` and `ConfigClinicODPolicyProvider` replace the P1-15 and P1-16 stubs (T16)
- [ ] The admin API (read, versions, diff, PATCH, activate) enforces `CONFIG_READ`/`CONFIG_WRITE`, CSRF and optimistic concurrency (T17–T20)
- [ ] The synthetic seed folder validates in CI; the pilot seed imports as version 1 once P0-01/02/03 deliver it
- [ ] `docs/clinic-config.md` documents the sections, edit matrix, import and rollback; the §7 step 10 issues are notified

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI (T1–T21, seed validation, schema staleness check)
- [ ] PR reviewed (HIPAA review if labelled `phi`): not labelled `phi` (config holds no patient data); the tech lead and compliance owner still review the edit matrix and the emergency-rules import path
- [ ] No PHI in logs (only paths, rule names, versions)
- [ ] Docs / README updated: `docs/clinic-config.md`, seed README, P6-01 onboarding note

## 13. Hand-off
| Task | Can rely on |
|---|---|
| P1-20 Availability, slot lock, booking | `hours` = AI booking window; `holidays` close days; `scheduling.*` incl. `booking_horizon_days`, `min_lead_minutes` (routine), `min_lead_minutes_urgent` (Tier 2), `options_per_offer`, `reserved_blockouts`; `appointment_types` with `od_check.disabled_variants` |
| P2-01 State machine | `pin_session()` at session start, `for_session()` afterwards |
| P2-12 Matching and verification | `verification`, `open_dental.existing_patient_statuses` |
| P2-16 / P2-18 Booking, reschedule, cancel | `policies.*`, booking horizon, note texts via `ClinicODPolicy` |
| P2-20 Emergency detection | `emergency_rules` (status checked per environment) |
| P2-22 Callback and admin email | `callback.*`, `clinic.public_phone_e164` |
| P4-04 Reminders | `reminders.*` |
| P3 Voice | `voice.*` |
| P4-11 Policies screens | Admin API, edit matrix (`locked_sections`), `od_check` warnings, diff |
| P5-12 Retention | `privacy.transcript_retention_days` |
| P5-15 Emergency sign-off | Prod import via `config_imports` in a release PR |
| P6-01 Onboarding | CLI `validate`/`import` for a new clinic; `open_dental.version` and `clinic_num` set at onboarding |

## 14. Open questions
| Question | Owner | Needed by |
|---|---|---|
| Does `ScheduleBlock.blockout_def_num` match the DefNums from `GET /definitions?Category=25`, and which blockout types does the pilot clinic use for new-patient and emergency slots? Recommended: assume they match and verify on day 1; keep both `reserved_blockouts` lists empty (other blockouts block booking) until the clinic names them in P0-01 B5. | Tech lead (test DB (B)) + clinic (P0-01 B5) | Step 1 / pilot seed |

## 15. References
- Plan §4.5, §4.6, §4.8, §4.9, §5, §7
- P0-01 (answers), P0-02 (appointment types), P0-03 (emergency rules), P0-08 (callback email)
- Open Dental Definitions API: https://www.opendental.com/site/apidefinitions.html
- Open Dental Schedules API (blockouts): https://www.opendental.com/site/apischedules.html
- JSON Merge Patch (RFC 7396): https://www.rfc-editor.org/rfc/rfc7396
- Pydantic JSON Schema: https://docs.pydantic.dev/latest/concepts/json_schema/
- PostgreSQL advisory locks: https://www.postgresql.org/docs/16/functions-admin.html#FUNCTIONS-ADVISORY-LOCKS
- Redis pub/sub: https://redis.io/docs/latest/develop/interact/pubsub/
- Related tasks: P0-01, P0-02, P0-03, P0-07a, P0-08, P1-02, P1-03, P1-05, P1-06, P1-07, P1-13, P1-15, P1-16, P1-20, P2-01, P2-12, P2-16, P2-18, P2-20, P2-22, P3-02, P4-04, P4-11, P5-12, P5-15, P6-01
