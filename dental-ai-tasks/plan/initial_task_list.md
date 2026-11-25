# Initial task list (seed)

Starting point for discussion: 124 tasks from the first breakdown. Each one gets discussed and then written up in detail as `tasks/<ID>.md`. Tasks can be split, merged or renamed during discussion; record the change in DECISIONS.md.


## Phase 0 - Discovery & Compliance Foundation

### E0.1 Clinic discovery
_Answer the open questions (plan §13) with the pilot clinic so later work has fixed rules._

#### P0-01 — Run discovery workshop with pilot clinic
- **Size:** M  ·  **Labels:** area:compliance, type:docs  ·  **Depends on:** none  ·  **Plan ref:** §13
- **Description:** Walk the clinic through the plan and get written answers to all 11 open questions in §13 (verification identifiers, staff review of AI bookings, bookable appointment types, emergency protocol, admin emails, cancellation window, insurance scope, Workspace, BSP/SMS, transcript retention, locations, widget placement).
- **Acceptance criteria:**
  - All 11 questions answered in a shared decision log
  - Clinic contact (SME) named for sign-offs
  - Decision log linked from the repo README

#### P0-02 — Document appointment-type mapping (reason -> type -> duration -> providers)
- **Size:** S  ·  **Labels:** area:scheduling, type:docs  ·  **Depends on:** P0-01  ·  **Plan ref:** §7, §13.3
- **Description:** Capture which patient reasons map to which Open Dental appointment types, their durations, eligible providers, and which types the AI may NOT book.
- **Acceptance criteria:**
  - Mapping table approved by clinic
  - Stored as seed data (YAML/JSON) for clinic_config

#### P0-03 — Document draft emergency protocol (Tier 1/2/3) for clinic review
- **Size:** S  ·  **Labels:** area:compliance, area:ai, type:docs, phi  ·  **Depends on:** P0-01  ·  **Plan ref:** §4.8
- **Description:** Write Tier 1 (911), Tier 2 (urgent slot or URGENT callback) and Tier 3 rules with trigger phrases and fixed response scripts. No diagnosis or treatment advice.
- **Acceptance criteria:**
  - Draft rules + scripts sent to clinic
  - Clinic feedback recorded; final sign-off tracked in P5-15

#### P0-04 — Write conversation flow designs
- **Size:** M  ·  **Labels:** area:ai, type:docs  ·  **Depends on:** P0-01  ·  **Plan ref:** §4.1
- **Description:** Flow diagrams for: new booking (new + existing patient), reschedule, cancel, check appointment, FAQ, emergency, callback. Include states and transitions from §4.1.
- **Acceptance criteria:**
  - One diagram per flow in /docs/flows
  - Every state of the §4.1 state machine appears in at least one flow

### E0.2 Compliance foundation
_BAAs, vendor matrix and risk assessment before any PHI moves._

#### P0-05 — Create Google Cloud org/project and accept Google Cloud BAA
- **Size:** S  ·  **Labels:** area:compliance, area:infra, type:chore  ·  **Depends on:** none  ·  **Plan ref:** §3.3
- **Description:** Create the org, billing account and dev/staging/prod projects. Accept the Google Cloud BAA in the console and record the date and signer.
- **Acceptance criteria:**
  - BAA accepted and recorded in vendor matrix
  - Separate projects for dev, staging, prod

#### P0-06 — Restrict projects to HIPAA covered products (org policies + VPC-SC)
- **Size:** M  ·  **Labels:** area:compliance, area:infra, type:chore  ·  **Depends on:** P0-05  ·  **Plan ref:** §3.3 Rules
- **Description:** Apply org policy constraints (allowed services, resource locations = US), set up VPC Service Controls perimeter around PHI services, and disable Speech-to-Text data logging.
- **Acceptance criteria:**
  - Org policy denies non-covered services
  - VPC-SC perimeter includes Vertex AI, STT, TTS, Cloud SQL, Memorystore
  - STT data logging confirmed OFF
  - No AI Studio / Gemini Developer API keys exist

#### P0-07 — Select WhatsApp BSP that signs a BAA and sign it
- **Size:** S  ·  **Labels:** area:compliance, area:messaging, type:chore  ·  **Depends on:** P0-01  ·  **Plan ref:** §3.3
- **Description:** Compare BSPs that offer a BAA; pick one; sign the BAA. Decide on SMS fallback (with BAA) if approved by the clinic.
- **Acceptance criteria:**
  - BSP chosen with written reasons
  - BAA signed and recorded in vendor matrix

#### P0-08 — Decide admin email route and sign BAA
- **Size:** S  ·  **Labels:** area:compliance, area:messaging, type:chore  ·  **Depends on:** P0-01  ·  **Plan ref:** §4.9
- **Description:** Gmail API via Google Workspace (Workspace BAA) or a transactional email service with a BAA. Decide full-details vs case-link-only default.
- **Acceptance criteria:**
  - Route chosen and BAA accepted/signed
  - Email content mode default recorded

#### P0-09 — Prepare clinic <-> company BAA
- **Size:** S  ·  **Labels:** area:compliance, type:docs  ·  **Depends on:** P0-01  ·  **Plan ref:** §3.3
- **Description:** Draft the BAA between our company and the pilot clinic; send for legal review.
- **Acceptance criteria:**
  - Draft BAA sent to clinic and HIPAA advisor
  - Signature tracked in vendor matrix

#### P0-10 — Create vendor/BAA matrix document
- **Size:** S  ·  **Labels:** area:compliance, type:docs  ·  **Depends on:** P0-05  ·  **Plan ref:** §3.3
- **Description:** Living table: vendor, services, PHI yes/no, BAA status, date, owner. Add a CI/PR checklist item: 'new vendor? update matrix'.
- **Acceptance criteria:**
  - Matrix in /docs/compliance
  - PR template includes vendor check

#### P0-11 — Risk assessment v1
- **Size:** M  ·  **Labels:** area:compliance, type:docs  ·  **Depends on:** P0-10  ·  **Plan ref:** §6
- **Description:** HIPAA security risk assessment v1 covering data flows, threats, likelihood/impact and planned controls.
- **Acceptance criteria:**
  - Risk register with owners
  - Reviewed by compliance advisor

### E0.3 Technical setup decisions
_Access and choices that unblock Phase 1._

#### P0-12 — Get Open Dental API keys and a test database
- **Size:** S  ·  **Labels:** area:open-dental, type:chore  ·  **Depends on:** P0-01  ·  **Plan ref:** §8 Phase 0
- **Description:** Request developer key + customer key; set up an Open Dental test DB with synthetic patients, providers, operatories and schedules.
- **Acceptance criteria:**
  - Keys stored in Secret Manager (never in code)
  - Test DB reachable from dev project
  - Synthetic seed data documented

#### P0-13 — Choose GA Gemini model versions per routing tier
- **Size:** S  ·  **Labels:** area:ai, type:spike  ·  **Depends on:** P0-06  ·  **Plan ref:** §4.3
- **Description:** Pick GA Flash-Lite, Flash and Pro model IDs on Vertex AI in a US region; confirm each is on the HIPAA covered list. Model IDs must be config, not code.
- **Acceptance criteria:**
  - Model IDs per tier recorded in an ADR
  - All are GA and covered

#### P0-14 — Architecture doc + PHI data-flow diagram
- **Size:** M  ·  **Labels:** area:infra, type:docs  ·  **Depends on:** P0-04, P0-13  ·  **Plan ref:** §3
- **Description:** Final architecture doc with the data-flow diagram that shows PHI boundaries (what PHI goes to Gemini, STT, TTS, BSP, email, DB).
- **Acceptance criteria:**
  - Diagram marks every PHI hop with its BAA
  - ADR list started (stack, Pipecat yes/no, Cloud Run vs GKE)

#### P0-15 — Register WhatsApp number and submit message templates
- **Size:** S  ·  **Labels:** area:messaging, type:chore  ·  **Depends on:** P0-07  ·  **Plan ref:** §4.7
- **Description:** Start WhatsApp Business account, number registration and submit templates: booking confirmation, 1-hour reminder, reschedule, cancel. Content: name, clinic, date, time only.
- **Acceptance criteria:**
  - Templates submitted (approval tracked)
  - No symptom/procedure text in any template


## Phase 1 - Core Platform & Open Dental Adapter

### E1.1 Infrastructure & DevOps
_Repeatable environments and delivery pipeline._

#### P1-01 — Set up monorepo structure and coding standards
- **Size:** S  ·  **Labels:** area:infra, type:chore  ·  **Depends on:** none  ·  **Plan ref:** -
- **Description:** Repo layout: /backend (FastAPI), /frontend (Next.js), /infra (Terraform), /docs, /evals. Linting, formatting, pre-commit, PR template with HIPAA checklist.
- **Acceptance criteria:**
  - CI runs lint + type check on every PR
  - PR template includes PHI and vendor checks

#### P1-02 — Terraform base: VPC, Cloud Run, Artifact Registry
- **Size:** M  ·  **Labels:** area:infra, type:chore  ·  **Depends on:** P0-06, P1-01  ·  **Plan ref:** §3.2
- **Description:** Infrastructure as code for networking (private VPC, serverless VPC connector), Cloud Run services, Artifact Registry. US region only.
- **Acceptance criteria:**
  - terraform plan/apply works for dev
  - No public DB endpoints

#### P1-03 — Terraform: Cloud SQL Postgres with CMEK
- **Size:** M  ·  **Labels:** area:infra, type:chore, phi  ·  **Depends on:** P1-02  ·  **Plan ref:** §3.2, §6
- **Description:** Cloud SQL for PostgreSQL, private IP, CMEK via Cloud KMS, automated backups, PITR.
- **Acceptance criteria:**
  - Encrypted with CMEK key
  - Backups and PITR enabled
  - Only reachable on private network

#### P1-04 — Terraform: Memorystore Redis, Cloud Tasks, Cloud Scheduler
- **Size:** S  ·  **Labels:** area:infra, type:chore  ·  **Depends on:** P1-02  ·  **Plan ref:** §3.2
- **Description:** Redis for session state and slot locks (TLS, AUTH), Cloud Tasks queues (reminders, emails) and Scheduler.
- **Acceptance criteria:**
  - Redis TLS + AUTH on
  - Queues created with retry policies

#### P1-05 — Secret Manager + KMS setup and service accounts
- **Size:** S  ·  **Labels:** area:infra, area:security, type:chore  ·  **Depends on:** P1-02  ·  **Plan ref:** §6
- **Description:** Least-privilege service accounts per service; secrets (Open Dental keys, BSP, email) in Secret Manager; KMS keys for field-level encryption.
- **Acceptance criteria:**
  - No secrets in env files or repo
  - Each service has its own SA with minimal roles

#### P1-06 — CI/CD pipeline: build, test, deploy to dev/staging/prod
- **Size:** M  ·  **Labels:** area:infra, type:chore  ·  **Depends on:** P1-02  ·  **Plan ref:** -
- **Description:** Cloud Build or GitHub Actions with Workload Identity Federation; deploy on merge to dev, manual promote to staging/prod.
- **Acceptance criteria:**
  - Main branch auto-deploys to dev
  - Promotion to prod requires approval
  - No long-lived GCP keys in GitHub

#### P1-07 — Cloud Logging/Monitoring baseline + latency dashboard skeleton
- **Size:** S  ·  **Labels:** area:infra, type:chore  ·  **Depends on:** P1-02  ·  **Plan ref:** §3.2
- **Description:** Structured JSON logs, log-based metrics, uptime checks, alerting channel, empty dashboard for per-stage latency (filled in P3).
- **Acceptance criteria:**
  - Alerts reach the team channel
  - Dashboard exists with placeholders

### E1.2 Backend foundation
_Shared services every feature uses._

#### P1-08 — FastAPI service skeleton with health checks and config
- **Size:** S  ·  **Labels:** area:backend, type:feature  ·  **Depends on:** P1-01  ·  **Plan ref:** -
- **Description:** App factory, settings from env/Secret Manager, /healthz, /readyz, error handling, request IDs, async DB and Redis clients.
- **Acceptance criteria:**
  - Service deploys to Cloud Run dev
  - Readiness checks DB and Redis

#### P1-09 — Database schema and migrations (all §5 tables)
- **Size:** M  ·  **Labels:** area:backend, type:feature, phi  ·  **Depends on:** P1-03, P1-08  ·  **Plan ref:** §5
- **Description:** Alembic migrations for clinics, sessions, appointment_refs, contact_prefs, consents, reminders, callback_requests, audit_log, staff_users, clinic_config.
- **Acceptance criteria:**
  - Migrations run in CI against a test DB
  - Only references stored (PatNum, AptNum), no record copies

#### P1-10 — Field-level encryption helper (KMS envelope encryption)
- **Size:** M  ·  **Labels:** area:backend, area:security, type:feature, phi  ·  **Depends on:** P1-05, P1-09  ·  **Plan ref:** §6
- **Description:** Encrypt/decrypt helper for phone, DOB, WhatsApp number, callback contact details and summaries. Key rotation supported.
- **Acceptance criteria:**
  - Encrypted columns unreadable in raw DB dump
  - Unit tests for round trip and rotation

#### P1-11 — PHI-redacting logger middleware
- **Size:** M  ·  **Labels:** area:backend, area:security, type:feature, phi  ·  **Depends on:** P1-08  ·  **Plan ref:** §6
- **Description:** Logging filter that redacts names, phones, DOBs, emails, addresses and free text before anything reaches Cloud Logging.
- **Acceptance criteria:**
  - Test suite with PHI samples shows 0 leaks
  - Request/response bodies never logged in prod

#### P1-12 — Audit log service
- **Size:** S  ·  **Labels:** area:backend, type:feature  ·  **Depends on:** P1-09  ·  **Plan ref:** §5, §6
- **Description:** audit(actor, action, object_type, object_ref, result, ip) - append-only, no free-text PHI. Covers searches, patient create/update, appointment changes, callbacks, auth, admin actions, errors, security events.
- **Acceptance criteria:**
  - Append-only (no update/delete grants)
  - Helper used by all later services

#### P1-13 — Staff auth with MFA and RBAC
- **Size:** M  ·  **Labels:** area:backend, area:security, type:feature  ·  **Depends on:** P1-09  ·  **Plan ref:** §6
- **Description:** Staff login (Identity Platform) with MFA required; roles Admin, Front Desk, Dentist, Read-only; route-level permission decorator.
- **Acceptance criteria:**
  - MFA enforced for all staff
  - Role checks covered by tests

#### P1-14 — Patient session tokens, idle timeout and rate limiting
- **Size:** S  ·  **Labels:** area:backend, area:security, type:feature  ·  **Depends on:** P1-08, P1-04  ·  **Plan ref:** §6
- **Description:** Anonymous short-lived session tokens for the widget, secure cookies, idle timeout, per-IP and per-session rate limits.
- **Acceptance criteria:**
  - Session expires after idle timeout
  - Rate limit returns 429 and is logged

### E1.3 Open Dental adapter
_One typed client; no other code talks to Open Dental._

#### P1-15 — Open Dental HTTP client: auth, retries, rate-limit handling
- **Size:** M  ·  **Labels:** area:open-dental, type:feature, phi  ·  **Depends on:** P0-12, P1-08  ·  **Plan ref:** §8 Phase 1
- **Description:** Async client with auth headers from Secret Manager, timeouts, exponential backoff, rate-limit handling, typed errors, PHI-safe logging.
- **Acceptance criteria:**
  - Retries on 5xx/timeouts only
  - Unit tests with mocked responses

#### P1-16 — Adapter: patient search / get / create
- **Size:** M  ·  **Labels:** area:open-dental, type:feature, phi  ·  **Depends on:** P1-15  ·  **Plan ref:** §4.5
- **Description:** Search by last name + DOB and by phone; get by PatNum; create patient. Normalized result models.
- **Acceptance criteria:**
  - Integration tests against test DB
  - Create uses an idempotency key

#### P1-17 — Adapter: appointments get / create / update / break
- **Size:** M  ·  **Labels:** area:open-dental, type:feature, phi  ·  **Depends on:** P1-15  ·  **Plan ref:** §4.6
- **Description:** Get by patient and by AptNum, create, update (reschedule), break/cancel, with an AI-booked note/status option.
- **Acceptance criteria:**
  - Integration tests for each operation
  - Create returns the verified AptNum

#### P1-18 — Adapter: providers, appointment types, schedules, operatories
- **Size:** S  ·  **Labels:** area:open-dental, type:feature  ·  **Depends on:** P1-15  ·  **Plan ref:** §4.4 Techniques
- **Description:** Read-only config endpoints with a cache layer (TTL) for providers, appointment types, schedules, operatories.
- **Acceptance criteria:**
  - Cache hit/miss metrics
  - Cache invalidation on config change

### E1.4 Availability engine & backend tools
_Deterministic scheduling logic and the tool endpoints the AI will call._

#### P1-19 — Clinic config service (hours, holidays, rules)
- **Size:** S  ·  **Labels:** area:backend, type:feature  ·  **Depends on:** P1-09, P0-02  ·  **Plan ref:** §5, §7
- **Description:** Load and version clinic_config: hours, holidays, appointment type mapping, new-patient rules, emergency blocks, verification policy.
- **Acceptance criteria:**
  - Config is versioned
  - Seeded from P0-02 mapping

#### P1-20 — Availability engine: compute free slots
- **Size:** L  ·  **Labels:** area:scheduling, type:feature  ·  **Depends on:** P1-17, P1-18, P1-19  ·  **Plan ref:** §4.6
- **Description:** Calculate slots from schedules, operatories, existing appointments, type duration, provider eligibility, hours, holidays, new-patient slots, emergency blocks. Clinic time zone, DST-aware. Returns 2-3 best options.
- **Acceptance criteria:**
  - Pure function core with unit tests
  - Handles DST, holidays, out-of-hours
  - Never returns a slot that overlaps an existing appointment

#### P1-21 — Slot lock + booking sequence
- **Size:** M  ·  **Labels:** area:scheduling, type:feature  ·  **Depends on:** P1-20, P1-04  ·  **Plan ref:** §4.6
- **Description:** Confirm -> Redis lock on slot -> re-query Open Dental -> create with idempotency key -> verify created record -> release lock. On conflict return alternatives.
- **Acceptance criteria:**
  - Concurrent booking test: 0 double bookings
  - Lock always released (finally/TTL)

#### P1-22 — Tool endpoints: patient tools
- **Size:** M  ·  **Labels:** area:backend, type:feature, phi  ·  **Depends on:** P1-16, P1-12  ·  **Plan ref:** §4.2
- **Description:** search_patient, verify_patient, create_patient as internal endpoints with JSON schemas. Audit every call.
- **Acceptance criteria:**
  - JSON schema per tool
  - Audit entry per call

#### P1-23 — Tool endpoints: appointment tools
- **Size:** M  ·  **Labels:** area:backend, type:feature, phi  ·  **Depends on:** P1-21, P1-22  ·  **Plan ref:** §4.2
- **Description:** get_appointment_availability, get_patient_appointments, book_appointment, reschedule_appointment, cancel_appointment.
- **Acceptance criteria:**
  - JSON schema per tool
  - Booking uses P1-21 sequence

#### P1-24 — Tool endpoints: info tools
- **Size:** S  ·  **Labels:** area:backend, type:feature  ·  **Depends on:** P1-19, P1-18  ·  **Plan ref:** §4.2, §4.3
- **Description:** get_clinic_information, get_provider_information served from config/cache (no LLM).
- **Acceptance criteria:**
  - Answers hours, address, insurance list, services


## Phase 2 - Text Chat Receptionist

### E2.1 Conversation orchestrator
_State machine owns the flow; the LLM only talks and extracts._

#### P2-01 — State machine core with all states and side branches
- **Size:** M  ·  **Labels:** area:ai, area:backend, type:feature  ·  **Depends on:** P0-04, P1-08  ·  **Plan ref:** §4.1
- **Description:** GREETING -> INTENT -> IDENTIFY/REGISTER -> VERIFY -> APPOINTMENT_TYPE -> AVAILABILITY -> CONFIRM -> BOOK -> WRAP_UP, plus EMERGENCY, CALLBACK_REQUEST, RESCHEDULE, CANCEL.
- **Acceptance criteria:**
  - Transition table unit-tested
  - Illegal transitions rejected

#### P2-02 — Slot memory (structured JSON) in Redis with encryption
- **Size:** S  ·  **Labels:** area:ai, area:backend, type:feature, phi  ·  **Depends on:** P2-01, P1-10  ·  **Plan ref:** §4.1, §5
- **Description:** Store filled slots (name, DOB, phone, preferred time, reason) per session with TTL; only ask for missing fields.
- **Acceptance criteria:**
  - Slots encrypted at rest in Redis
  - Re-asking prevented (test)

#### P2-03 — LLM provider interface + Vertex AI Gemini implementation
- **Size:** M  ·  **Labels:** area:ai, type:feature  ·  **Depends on:** P0-13, P1-08  ·  **Plan ref:** §3.2, §1 principle 5
- **Description:** Provider interface (stream, structured output, cancel). Gemini via Vertex AI SDK only, model IDs from config, streaming tokens.
- **Acceptance criteria:**
  - Can swap provider via config
  - No AI Studio / API-key usage
  - Stream can be cancelled

#### P2-04 — Compact context builder with PHI masking
- **Size:** S  ·  **Labels:** area:ai, type:feature, phi  ·  **Depends on:** P2-02, P2-03  ·  **Plan ref:** §4.1, §6
- **Description:** Build prompt: system rules, current state, masked slots, last N turns, allowed tools only.
- **Acceptance criteria:**
  - Prompt never contains full history
  - PHI masked where not needed (tested)

#### P2-05 — Intent + slot extraction with structured JSON output
- **Size:** M  ·  **Labels:** area:ai, type:feature  ·  **Depends on:** P2-04  ·  **Plan ref:** §4.3
- **Description:** Flash-class model returns {intent, slots, confidence}. Validate with schema; fallback re-ask on low confidence.
- **Acceptance criteria:**
  - Schema-validated output
  - Eval set of 50 utterances >= 95% intent accuracy

#### P2-06 — Model router (templates / Flash-Lite / Flash / Pro / rules)
- **Size:** S  ·  **Labels:** area:ai, type:feature  ·  **Depends on:** P2-05  ·  **Plan ref:** §4.3
- **Description:** Route by situation per §4.3: templates for greetings, Flash for extraction, Pro for complex/complaints, config lookup for static answers.
- **Acceptance criteria:**
  - Routing decisions logged (no PHI)
  - Static answers make no LLM call

#### P2-07 — System prompt v1 + reply phrasing
- **Size:** S  ·  **Labels:** area:ai, type:feature  ·  **Depends on:** P2-04  ·  **Plan ref:** §1 principles
- **Description:** Receptionist persona, safety rules (no diagnosis, never invent slots, confirm before booking), English only, short spoken-style replies.
- **Acceptance criteria:**
  - Prompt versioned in repo
  - Prompt changes trigger eval run (P5-01)

### E2.2 Tool gateway & guardrails
_Every tool call is validated before it runs._

#### P2-08 — Tool gateway: schema validation + allow-list
- **Size:** S  ·  **Labels:** area:ai, area:security, type:feature  ·  **Depends on:** P1-22, P2-01  ·  **Plan ref:** §4.2
- **Description:** Only tools allowed in the current state are offered and accepted; inputs validated against JSON schema.
- **Acceptance criteria:**
  - Unknown or disallowed tool -> rejected and audited

#### P2-09 — Tool gateway: state preconditions + session scoping
- **Size:** M  ·  **Labels:** area:ai, area:security, type:feature, phi  ·  **Depends on:** P2-08  ·  **Plan ref:** §4.2
- **Description:** book_appointment only if verified + fresh availability + explicit confirmation recorded. Tools act only on this session's verified PatNum.
- **Acceptance criteria:**
  - Tests: booking blocked without confirmation
  - Tests: cannot read another patient's data

#### P2-10 — Idempotency keys on create/modify tools
- **Size:** S  ·  **Labels:** area:backend, type:feature  ·  **Depends on:** P2-09  ·  **Plan ref:** §4.2
- **Description:** Deterministic idempotency keys per session+action so retries never create duplicates.
- **Acceptance criteria:**
  - Retry test creates exactly one record

#### P2-11 — Prompt-injection defenses and tool output sanitizing
- **Size:** M  ·  **Labels:** area:ai, area:security, type:feature  ·  **Depends on:** P2-08  ·  **Plan ref:** §4.2
- **Description:** User text treated as data; tool outputs sanitized before reaching the model; output guardrail blocks diagnoses and invented slots.
- **Acceptance criteria:**
  - Injection test set (20+ cases) passes
  - Slot times in replies must match tool output

### E2.3 Patient identification & registration
_Find the right patient, never create duplicates._

#### P2-12 — Normalization utilities (names, nicknames, phone E.164, DOB ISO)
- **Size:** S  ·  **Labels:** area:backend, type:feature  ·  **Depends on:** P1-08  ·  **Plan ref:** §4.5
- **Description:** Normalize case/whitespace, nickname table, phone to E.164, DOB parsing from spoken/typed formats.
- **Acceptance criteria:**
  - Unit tests incl. 'Bob'->'Robert', '5/3/90', spoken numbers

#### P2-13 — Candidate matching and scoring
- **Size:** M  ·  **Labels:** area:backend, type:feature, phi  ·  **Depends on:** P2-12, P1-16  ·  **Plan ref:** §4.5
- **Description:** Search by last name + DOB and by phone; score strong / partial / multiple / none per §4.5; thresholds configurable per clinic.
- **Acceptance criteria:**
  - Each outcome covered by tests
  - Ambiguous result never auto-creates

#### P2-14 — Verification flow (2+ identifiers, no record leaks)
- **Size:** S  ·  **Labels:** area:ai, area:backend, type:feature, phi  ·  **Depends on:** P2-13, P2-09  ·  **Plan ref:** §4.5
- **Description:** Require identifiers per clinic policy; never verify on phone alone; don't confirm 'you are a patient' before verification.
- **Acceptance criteria:**
  - Unverified user gets no record details (test)

#### P2-15 — New patient registration flow
- **Size:** M  ·  **Labels:** area:ai, area:backend, type:feature, phi  ·  **Depends on:** P2-13, P2-14  ·  **Plan ref:** §4.5, §4.9
- **Description:** Collect required fields conversationally, confirm spelling and DOB once more, create in Open Dental only if no duplicate ambiguity.
- **Acceptance criteria:**
  - Duplicate check before create
  - Fallback to callback when ambiguous

### E2.4 Scheduling conversations
_Book, check, reschedule, cancel, FAQs._

#### P2-16 — Booking flow: reason -> type -> 2-3 options -> confirm -> book
- **Size:** M  ·  **Labels:** area:ai, area:scheduling, type:feature  ·  **Depends on:** P2-06, P1-23, P2-14  ·  **Plan ref:** §4.6
- **Description:** Map concern to appointment type (no diagnosis), offer 2-3 real options, explicit confirmation, book, confirm only after Open Dental confirms.
- **Acceptance criteria:**
  - End-to-end booking passes on staging
  - Conflict path re-offers alternatives

#### P2-17 — Check existing appointment flow
- **Size:** S  ·  **Labels:** area:ai, type:feature  ·  **Depends on:** P2-14, P1-23  ·  **Plan ref:** §2 #12
- **Description:** After verification, list upcoming appointments for this patient only.
- **Acceptance criteria:**
  - Only verified patient's appointments shown

#### P2-18 — Reschedule and cancel flows (with cancellation window policy)
- **Size:** M  ·  **Labels:** area:ai, area:scheduling, type:feature  ·  **Depends on:** P2-16  ·  **Plan ref:** §2 #11, §13.5
- **Description:** Basic reschedule and cancel, respecting clinic cancellation window; outside policy -> callback request.
- **Acceptance criteria:**
  - Policy enforced by code, not prompt
  - Audit entries created

#### P2-19 — FAQ answers from clinic config
- **Size:** S  ·  **Labels:** area:ai, type:feature  ·  **Depends on:** P1-24, P2-06  ·  **Plan ref:** §2 #4
- **Description:** Hours, location, services, accepted insurance answered from config with no LLM-invented facts.
- **Acceptance criteria:**
  - Answers match config exactly

### E2.5 Emergency & callback
_Safety first; unresolved cases go to the admin by email._

#### P2-20 — Emergency detector v1 (rules first, model second)
- **Size:** M  ·  **Labels:** area:ai, type:feature, phi  ·  **Depends on:** P0-03, P2-05  ·  **Plan ref:** §4.8
- **Description:** Keyword/phrase rules per tier from clinic config, then model check; uncertain -> URGENT callback. Runs on every user turn.
- **Acceptance criteria:**
  - Tier 1 test phrases -> 911 script 100%
  - Rules editable in config

#### P2-21 — Emergency scripts and Tier 2 urgent-slot path
- **Size:** S  ·  **Labels:** area:ai, area:scheduling, type:feature  ·  **Depends on:** P2-20, P2-16  ·  **Plan ref:** §4.8
- **Description:** Fixed pre-approved scripts; Tier 2 offers earliest urgent slot or creates URGENT callback.
- **Acceptance criteria:**
  - Scripts come from config, not LLM

#### P2-22 — Callback request service (case creation)
- **Size:** M  ·  **Labels:** area:backend, type:feature, phi  ·  **Depends on:** P1-10, P1-12  ·  **Plan ref:** §4.9
- **Description:** Create callback_requests with reason, urgency, patient type, encrypted details, status OPEN; one case per session+reason.
- **Acceptance criteria:**
  - Duplicate requests in one session -> one case
  - All fields encrypted where required

#### P2-23 — Admin email sender (BAA-covered, retry, unsent alerts)
- **Size:** M  ·  **Labels:** area:messaging, type:feature, phi  ·  **Depends on:** P2-22, P0-08, P1-04  ·  **Plan ref:** §4.9
- **Description:** Send template email via Gmail API/Workspace or BAA email provider over TLS; full or case-link-only mode; Cloud Tasks retry with backoff; failures flagged.
- **Acceptance criteria:**
  - Email sent within 1 minute in staging
  - Failed sends appear as unsent alerts

#### P2-24 — Callback conversation flow (collect, read back, tell patient)
- **Size:** M  ·  **Labels:** area:ai, type:feature, phi  ·  **Depends on:** P2-22, P2-23  ·  **Plan ref:** §4.9
- **Description:** Trigger on §4.9 conditions; collect new/existing details; read back name + phone; tell patient admin will call; mark URGENT when needed.
- **Acceptance criteria:**
  - All §4.9 triggers covered by tests
  - Patient message matches approved wording

### E2.6 Chat UI
_Patient-facing text widget._

#### P2-25 — Next.js widget shell + session handshake
- **Size:** S  ·  **Labels:** area:frontend, type:feature  ·  **Depends on:** P1-14  ·  **Plan ref:** §3.1
- **Description:** Embeddable widget, session token handshake, layout for avatar panel + chat panel, responsive (desktop + mobile).
- **Acceptance criteria:**
  - Works in an iframe on a test clinic page
  - No PHI in URLs

#### P2-26 — Chat messages with streaming replies
- **Size:** M  ·  **Labels:** area:frontend, type:feature  ·  **Depends on:** P2-25, P2-16  ·  **Plan ref:** §4.4
- **Description:** Message list, input, streaming tokens over WebSocket/SSE, typing indicator, loading and error states.
- **Acceptance criteria:**
  - First token shown <= 1s on staging

#### P2-27 — Slot option cards and confirmation cards
- **Size:** S  ·  **Labels:** area:frontend, type:feature  ·  **Depends on:** P2-26  ·  **Plan ref:** §2 #3
- **Description:** Clickable slot cards (2-3 options) and a booking confirmation card; clicking sends structured choice.
- **Acceptance criteria:**
  - Card selection goes through same confirmation rule

#### P2-28 — Accessibility pass (keyboard, screen reader, text-only mode)
- **Size:** S  ·  **Labels:** area:frontend, type:feature  ·  **Depends on:** P2-27  ·  **Plan ref:** §3.1
- **Description:** Keyboard navigation, ARIA live regions, contrast, text-only mode.
- **Acceptance criteria:**
  - axe scan: 0 critical issues

#### P2-29 — Bot protection on public widget
- **Size:** S  ·  **Labels:** area:frontend, area:security, type:feature  ·  **Depends on:** P2-25  ·  **Plan ref:** §6
- **Description:** reCAPTCHA Enterprise / App Check style protection on session creation.
- **Acceptance criteria:**
  - Automated abuse test is blocked

#### P2-30 — Phase 2 E2E: text booking on staging
- **Size:** S  ·  **Labels:** area:qa, type:test  ·  **Depends on:** P2-16, P2-24, P2-27  ·  **Plan ref:** §8 Phase 2
- **Description:** Automated E2E (Playwright) for new-patient booking, existing-patient booking, callback, emergency.
- **Acceptance criteria:**
  - Suite green on staging with Open Dental test DB


## Phase 3 - Voice Pipeline & Avatar

### E3.1 Voice pipeline
_Cascaded STT -> Gemini -> TTS, streaming end to end._

#### P3-01 — Latency spike: STT -> Gemini Flash -> TTS prototype
- **Size:** M  ·  **Labels:** area:voice, type:spike  ·  **Depends on:** P2-03  ·  **Plan ref:** §4.4, §8 Phase 3
- **Description:** Minimal script measuring end-of-speech -> first audio. Decide Pipecat vs custom pipeline.
- **Acceptance criteria:**
  - p50/p95 numbers recorded
  - ADR: Pipecat yes/no

#### P3-02 — Audio transport (WebSocket/WebRTC) browser <-> backend
- **Size:** M  ·  **Labels:** area:voice, area:frontend, type:feature  ·  **Depends on:** P3-01, P2-25  ·  **Plan ref:** §3.2
- **Description:** Mic capture with browser echo cancellation, 20 ms frames, bidirectional audio streaming, reconnect handling.
- **Acceptance criteria:**
  - Stable 10-minute session without drops

#### P3-03 — Streaming Speech-to-Text integration with phrase hints
- **Size:** M  ·  **Labels:** area:voice, type:feature, phi  ·  **Depends on:** P3-02  ·  **Plan ref:** §3.2
- **Description:** Google STT streaming with partials/finals, phrase hints for dental terms and clinic provider names, data logging OFF.
- **Acceptance criteria:**
  - Partials arrive in near real time
  - Data logging confirmed off in code/config

#### P3-04 — VAD + endpointing (client VAD, Silero server, semantic turn)
- **Size:** M  ·  **Labels:** area:voice, type:feature  ·  **Depends on:** P3-03  ·  **Plan ref:** §4.4
- **Description:** Combine VAD, silence threshold and semantic turn detection to find end of turn.
- **Acceptance criteria:**
  - End-of-speech -> endpoint <= 500 ms p50

#### P3-05 — Streaming Text-to-Speech with sentence chunker + SSML
- **Size:** M  ·  **Labels:** area:voice, type:feature  ·  **Depends on:** P3-02  ·  **Plan ref:** §4.4
- **Description:** Chunk LLM tokens into sentences, stream to Google TTS, SSML for pauses and digit-by-digit numbers.
- **Acceptance criteria:**
  - TTS first audio <= 250 ms
  - Phone numbers read digit by digit

#### P3-06 — Barge-in: stop TTS and cancel LLM stream
- **Size:** M  ·  **Labels:** area:voice, type:feature  ·  **Depends on:** P3-04, P3-05  ·  **Plan ref:** §4.4
- **Description:** User speech during playback stops audio and cancels in-flight Gemini stream and pending TTS.
- **Acceptance criteria:**
  - Barge-in stop <= 200 ms

#### P3-07 — Filler phrases during tool calls + warm connections
- **Size:** S  ·  **Labels:** area:voice, type:feature  ·  **Depends on:** P3-05  ·  **Plan ref:** §4.4
- **Description:** Pre-synthesized fillers ('Let me check that for you...') while Open Dental runs; keep warm gRPC connections.
- **Acceptance criteria:**
  - Filler plays when tool > 700 ms

#### P3-08 — Speculative LLM calls on stable partials
- **Size:** S  ·  **Labels:** area:voice, area:ai, type:feature  ·  **Depends on:** P3-04  ·  **Plan ref:** §4.4
- **Description:** Start LLM on stable partial transcript; discard if final differs. Never runs tools speculatively.
- **Acceptance criteria:**
  - Measured latency gain recorded
  - No side-effect tools in speculative calls

### E3.2 Critical data confirmation
_Names, numbers, dates are always read back._

#### P3-09 — Read-back confirmation for names, phones, dates, times
- **Size:** S  ·  **Labels:** area:voice, area:ai, type:feature, phi  ·  **Depends on:** P3-05, P2-02  ·  **Plan ref:** §4.4
- **Description:** Before using a critical slot, read it back and require yes/no; corrections update slot memory.
- **Acceptance criteria:**
  - Read-back required by state machine, not prompt

#### P3-10 — Spelling mode (letter by letter)
- **Size:** S  ·  **Labels:** area:voice, type:feature  ·  **Depends on:** P3-09  ·  **Plan ref:** §4.4
- **Description:** Patient can spell names; handle NATO-style and plain letters.
- **Acceptance criteria:**
  - Spelled names match in tests

### E3.3 Voice UI & avatar
_What the patient sees while talking._

#### P3-11 — Avatar with states (idle / listening / thinking / speaking)
- **Size:** M  ·  **Labels:** area:frontend, type:feature  ·  **Depends on:** P3-02  ·  **Plan ref:** §3.2
- **Description:** Lottie/Rive 2D avatar driven by pipeline events; mic indicator.
- **Acceptance criteria:**
  - State changes within 100 ms of events

#### P3-12 — Live transcript in chat panel
- **Size:** S  ·  **Labels:** area:frontend, type:feature  ·  **Depends on:** P3-03, P2-26  ·  **Plan ref:** §2 #3
- **Description:** Show partial and final transcripts plus AI replies in the chat panel.
- **Acceptance criteria:**
  - Transcript matches spoken content

#### P3-13 — Seamless voice <-> text switching in one session
- **Size:** S  ·  **Labels:** area:frontend, area:ai, type:feature  ·  **Depends on:** P3-12  ·  **Plan ref:** §2 #2
- **Description:** Same session and slot memory whether the patient speaks or types; switch any time.
- **Acceptance criteria:**
  - Switch mid-booking keeps all filled slots

#### P3-14 — Per-stage latency instrumentation + dashboard
- **Size:** S  ·  **Labels:** area:voice, area:infra, type:feature  ·  **Depends on:** P3-06, P1-07  ·  **Plan ref:** §4.4
- **Description:** Metrics for endpoint, LLM TTFT, TTS first audio, voice-to-voice, barge-in; p50/p95 panels.
- **Acceptance criteria:**
  - Dashboard shows all §4.4 stages

#### P3-15 — Latency tuning to hit targets
- **Size:** M  ·  **Labels:** area:voice, type:feature  ·  **Depends on:** P3-14  ·  **Plan ref:** §4.4, §11
- **Description:** Tune chunk sizes, endpoint thresholds, model tier, region, caching until targets are met in internal tests.
- **Acceptance criteria:**
  - Voice-to-voice <= 1.5 s p50, <= 2.5 s p95

#### P3-16 — Phase 3 demo: voice-to-voice booking
- **Size:** S  ·  **Labels:** area:qa, type:test  ·  **Depends on:** P3-13, P3-15  ·  **Plan ref:** §8 Phase 3
- **Description:** Recorded demo of a full voice booking with read-back and barge-in.
- **Acceptance criteria:**
  - Demo accepted by tech lead


## Phase 4 - WhatsApp, Reminders & Admin Console

### E4.1 WhatsApp & reminders
_Confirm now, remind one hour before, never for cancelled visits._

#### P4-01 — Messaging provider interface + WhatsApp BSP adapter
- **Size:** M  ·  **Labels:** area:messaging, type:feature, phi  ·  **Depends on:** P0-07, P0-15  ·  **Plan ref:** §4.7
- **Description:** Interface (send_template, parse_webhook); BSP implementation using approved templates only.
- **Acceptance criteria:**
  - Provider swappable
  - Only approved template IDs accepted

#### P4-02 — Consent capture and storage
- **Size:** S  ·  **Labels:** area:messaging, area:ai, type:feature, phi  ·  **Depends on:** P1-09, P2-16  ·  **Plan ref:** §4.7, §5
- **Description:** Ask for WhatsApp consent in conversation; store timestamp, channel, wording version, source.
- **Acceptance criteria:**
  - No message sent without consent record

#### P4-03 — Booking confirmation message
- **Size:** S  ·  **Labels:** area:messaging, type:feature, phi  ·  **Depends on:** P4-01, P4-02  ·  **Plan ref:** §2 #9
- **Description:** Send confirmation template after Open Dental confirms booking.
- **Acceptance criteria:**
  - Sent only after verified create

#### P4-04 — Reminder scheduler (appointment - 60 min, DST-aware)
- **Size:** M  ·  **Labels:** area:messaging, type:feature  ·  **Depends on:** P4-03, P1-04  ·  **Plan ref:** §4.7
- **Description:** Cloud Tasks job at appointment time minus configurable offset in clinic time zone.
- **Acceptance criteria:**
  - DST transition tests pass
  - Offset configurable per clinic

#### P4-05 — Pre-send verification (re-fetch appointment)
- **Size:** S  ·  **Labels:** area:messaging, area:open-dental, type:feature  ·  **Depends on:** P4-04  ·  **Plan ref:** §4.7
- **Description:** Before sending, re-fetch from Open Dental; cancelled or opted out -> cancel job; moved -> reschedule job.
- **Acceptance criteria:**
  - 0 reminders for cancelled appointments in tests

#### P4-06 — Delivery webhooks, retries and failure alerts
- **Size:** M  ·  **Labels:** area:messaging, type:feature  ·  **Depends on:** P4-01  ·  **Plan ref:** §4.7
- **Description:** Verify webhook signatures; track sent/delivered/read/failed; retry with backoff; alert in console after final failure.
- **Acceptance criteria:**
  - Webhook signature verified
  - Failed reminders visible in admin console

#### P4-07 — Opt-out handling (STOP)
- **Size:** S  ·  **Labels:** area:messaging, type:feature  ·  **Depends on:** P4-06  ·  **Plan ref:** §4.7
- **Description:** Inbound STOP keywords revoke consent and cancel pending jobs.
- **Acceptance criteria:**
  - STOP -> consent revoked + jobs cancelled (test)

#### P4-08 — Reschedule and cancellation notifications
- **Size:** S  ·  **Labels:** area:messaging, type:feature  ·  **Depends on:** P4-03, P2-18  ·  **Plan ref:** §8 Phase 4
- **Description:** Send templates on reschedule/cancel and update reminder jobs.
- **Acceptance criteria:**
  - Reminder job moves with the appointment

### E4.2 Clinic admin console
_Staff configure the AI and work callback cases._

#### P4-09 — Admin console shell with staff login and RBAC
- **Size:** S  ·  **Labels:** area:admin, area:frontend, type:feature  ·  **Depends on:** P1-13  ·  **Plan ref:** §7
- **Description:** Next.js admin app, MFA login, role-based navigation.
- **Acceptance criteria:**
  - Read-only role cannot edit anything

#### P4-10 — Clinic profile, hours and holidays screens
- **Size:** S  ·  **Labels:** area:admin, type:feature  ·  **Depends on:** P4-09, P1-19  ·  **Plan ref:** §7
- **Description:** Edit profile, time zone, hours, holidays (sync from Open Dental where possible).
- **Acceptance criteria:**
  - Changes versioned and audited

#### P4-11 — Appointment type mapping and policies screens
- **Size:** M  ·  **Labels:** area:admin, type:feature  ·  **Depends on:** P4-10  ·  **Plan ref:** §7
- **Description:** Reason -> type -> duration -> providers; new-patient rules, verification fields, cancellation window.
- **Acceptance criteria:**
  - Availability engine picks up changes without redeploy

#### P4-12 — Emergency rules editor with approval workflow and history
- **Size:** M  ·  **Labels:** area:admin, type:feature  ·  **Depends on:** P4-09, P2-20  ·  **Plan ref:** §7, §4.8
- **Description:** Edit tier rules and scripts; changes need clinic approver; version history and rollback.
- **Acceptance criteria:**
  - Unapproved rules never go live

#### P4-13 — WhatsApp, voice and callback settings screens
- **Size:** S  ·  **Labels:** area:admin, type:feature  ·  **Depends on:** P4-09  ·  **Plan ref:** §7
- **Description:** Templates, reminder offset, consent text; voice, speed, greeting; admin email(s), email mode, callback triggers.
- **Acceptance criteria:**
  - Settings validated before save

#### P4-14 — Callback cases list and status workflow
- **Size:** M  ·  **Labels:** area:admin, type:feature, phi  ·  **Depends on:** P4-09, P2-22  ·  **Plan ref:** §4.9, §7
- **Description:** List (urgent first), filters, case detail, mark CONTACTED/RESOLVED, assign to staff, unsent-email alerts.
- **Acceptance criteria:**
  - Status changes audited
  - Urgent cases pinned on top

#### P4-15 — AI activity log and AI-booked appointment review
- **Size:** S  ·  **Labels:** area:admin, type:feature  ·  **Depends on:** P4-09, P1-12  ·  **Plan ref:** §2 staff, §7
- **Description:** Filtered, role-restricted view of AI actions; list of AI-booked appointments flagged for review.
- **Acceptance criteria:**
  - No free-text PHI shown in activity log

#### P4-16 — Consent / opt-out management screen
- **Size:** S  ·  **Labels:** area:admin, type:feature, phi  ·  **Depends on:** P4-07, P4-09  ·  **Plan ref:** §2 staff
- **Description:** View and change patient messaging consent with audit trail.
- **Acceptance criteria:**
  - Every change audited

#### P4-17 — Phase 4 E2E: book -> confirm -> remind -> reschedule/cancel -> notify
- **Size:** S  ·  **Labels:** area:qa, type:test  ·  **Depends on:** P4-05, P4-08, P4-14  ·  **Plan ref:** §8 Phase 4
- **Description:** Automated full lifecycle test with time simulation.
- **Acceptance criteria:**
  - Suite green on staging


## Phase 5 - Hardening, Testing & Security Review

### E5.1 Testing
_Prove it works across real-world conditions._

#### P5-01 — Conversation eval harness (runs on every prompt/model change)
- **Size:** M  ·  **Labels:** area:qa, area:ai, type:test  ·  **Depends on:** P2-30  ·  **Plan ref:** §9
- **Description:** Scripted multi-turn scenarios with pass/fail checks on state, tool calls and replies; runs in CI.
- **Acceptance criteria:**
  - CI blocks merge on eval regression

#### P5-02 — Write 100+ conversation scenarios
- **Size:** L  ·  **Labels:** area:qa, type:test  ·  **Depends on:** P5-01  ·  **Plan ref:** §9, §11
- **Description:** New/existing patients, ambiguous matches, interruptions, topic changes, reschedule/cancel, emergencies, complaints, off-topic, prompt injection.
- **Acceptance criteria:**
  - 100+ scenarios committed
  - Emergency scenarios 100% pass

#### P5-03 — Voice test sets: accents, noise, mic quality; WER on critical fields
- **Size:** M  ·  **Labels:** area:qa, area:voice, type:test  ·  **Depends on:** P3-16  ·  **Plan ref:** §9, §11
- **Description:** Recorded sets; measure WER for names, numbers, dates; barge-in and silence handling.
- **Acceptance criteria:**
  - Critical-field accuracy after read-back >= 98%

#### P5-04 — Scheduling edge-case tests (races, DST, holidays, providers)
- **Size:** S  ·  **Labels:** area:qa, area:scheduling, type:test  ·  **Depends on:** P1-21  ·  **Plan ref:** §9
- **Description:** Concurrent-session double-booking races, holidays, provider restrictions, outside hours, DST.
- **Acceptance criteria:**
  - 0 double bookings under concurrency

#### P5-05 — Reminder tests (timing, cancel/move, retries, opt-out)
- **Size:** S  ·  **Labels:** area:qa, area:messaging, type:test  ·  **Depends on:** P4-17  ·  **Plan ref:** §9
- **Description:** Time-simulated reminder accuracy and failure paths.
- **Acceptance criteria:**
  - 0 reminders for cancelled appointments

#### P5-06 — Load and latency tests (concurrent sessions)
- **Size:** M  ·  **Labels:** area:qa, area:infra, type:test  ·  **Depends on:** P3-15  ·  **Plan ref:** §9
- **Description:** Load test target concurrency; record p50/p95 per stage under load.
- **Acceptance criteria:**
  - Latency targets hold at pilot load

#### P5-07 — UAT with clinic staff on staging
- **Size:** S  ·  **Labels:** area:qa, type:test  ·  **Depends on:** P5-02, P4-17  ·  **Plan ref:** §9
- **Description:** Clinic staff run real scenarios; collect issues.
- **Acceptance criteria:**
  - UAT sign-off form completed

### E5.2 Security & compliance review
_Close the HIPAA gate before real patients._

#### P5-08 — PHI-in-logs scan and credential exposure scan
- **Size:** S  ·  **Labels:** area:security, type:test, phi  ·  **Depends on:** P1-11  ·  **Plan ref:** §9, §11
- **Description:** Automated scans of logs, repo and images for PHI and secrets.
- **Acceptance criteria:**
  - 0 findings or all fixed

#### P5-09 — LLM red teaming: prompt injection and tool misuse
- **Size:** M  ·  **Labels:** area:security, area:ai, type:test  ·  **Depends on:** P2-11  ·  **Plan ref:** §9
- **Description:** Attempt cross-patient access, forced booking, data exfiltration, jailbreaks.
- **Acceptance criteria:**
  - No critical findings open

#### P5-10 — Auth/authorization tests + OWASP Top 10 review
- **Size:** S  ·  **Labels:** area:security, type:test  ·  **Depends on:** P4-09  ·  **Plan ref:** §6
- **Description:** Test RBAC, session scoping, IDOR, injection, SSRF, etc.
- **Acceptance criteria:**
  - Report with all highs fixed

#### P5-11 — External penetration test and fixes
- **Size:** M  ·  **Labels:** area:security, type:test  ·  **Depends on:** P5-10  ·  **Plan ref:** §15
- **Description:** Third-party pen test; fix critical/high findings.
- **Acceptance criteria:**
  - Critical findings fixed and retested

#### P5-12 — Incident response plan and outage runbooks
- **Size:** S  ·  **Labels:** area:compliance, type:docs  ·  **Depends on:** P0-11  ·  **Plan ref:** §15
- **Description:** IR plan; runbooks for Open Dental, LLM, STT/TTS, WhatsApp outages and breach handling.
- **Acceptance criteria:**
  - Runbooks in /docs/runbooks
  - Tabletop exercise done

#### P5-13 — Backup/restore drill and retention deletion jobs
- **Size:** S  ·  **Labels:** area:infra, area:compliance, type:chore  ·  **Depends on:** P1-03  ·  **Plan ref:** §5, §6
- **Description:** Restore Cloud SQL into a test instance; implement transcript/data retention deletion jobs.
- **Acceptance criteria:**
  - Restore succeeded and timed
  - Retention job deletes expired data

#### P5-14 — HIPAA readiness review (BAAs, policies, risk assessment final)
- **Size:** S  ·  **Labels:** area:compliance, type:docs  ·  **Depends on:** P5-11, P5-12  ·  **Plan ref:** §8 Phase 5
- **Description:** Confirm every PHI vendor has an executed BAA; finalize risk assessment; advisor sign-off.
- **Acceptance criteria:**
  - Compliance checklist signed

#### P5-15 — Clinic sign-off on emergency scripts and policies
- **Size:** S  ·  **Labels:** area:compliance, type:docs  ·  **Depends on:** P4-12, P5-07  ·  **Plan ref:** §15
- **Description:** Clinic approves final emergency rules, scripts and policies in the console approval workflow.
- **Acceptance criteria:**
  - Approval recorded with version


## Phase 6 - Pilot Launch & Iteration

### E6.1 Pilot
_Real patients at one clinic, measured and tuned._

#### P6-01 — Production readiness checklist and go-live
- **Size:** S  ·  **Labels:** area:infra, type:chore  ·  **Depends on:** P5-14, P5-15  ·  **Plan ref:** §8 Phase 6
- **Description:** Prod deploy, alerts, on-call, feature flags (limited hours, new bookings flagged for review).
- **Acceptance criteria:**
  - Checklist complete
  - Rollback tested

#### P6-02 — KPI instrumentation and pilot dashboard
- **Size:** M  ·  **Labels:** area:infra, area:admin, type:feature  ·  **Depends on:** P3-14, P4-14  ·  **Plan ref:** §11
- **Description:** Booking completion, callback rate, latency, double bookings, duplicates, reminder success, ratings, no-show baseline.
- **Acceptance criteria:**
  - All §11 KPIs visible

#### P6-03 — Post-chat rating widget
- **Size:** S  ·  **Labels:** area:frontend, type:feature  ·  **Depends on:** P2-26  ·  **Plan ref:** §11
- **Description:** Simple 1-5 rating at end of conversation, no free-text PHI.
- **Acceptance criteria:**
  - Ratings feed KPI dashboard

#### P6-04 — Soft launch at pilot clinic
- **Size:** S  ·  **Labels:** area:qa, type:chore  ·  **Depends on:** P6-01, P6-02  ·  **Plan ref:** §8 Phase 6
- **Description:** Enable widget on clinic site with limited hours; daily check-ins first week.
- **Acceptance criteria:**
  - Widget live
  - Daily review notes

#### P6-05 — Weekly review of callbacks and failed conversations
- **Size:** S  ·  **Labels:** area:ai, type:chore  ·  **Depends on:** P6-04  ·  **Plan ref:** §8 Phase 6
- **Description:** Review cases, label failure causes, file follow-up issues.
- **Acceptance criteria:**
  - Weekly review doc

#### P6-06 — Tuning: prompts, vocabulary, routing, rules
- **Size:** M  ·  **Labels:** area:ai, area:voice, type:feature  ·  **Depends on:** P6-05  ·  **Plan ref:** §8 Phase 6
- **Description:** Apply fixes from reviews; every change goes through eval suite.
- **Acceptance criteria:**
  - Eval suite green after each change

#### P6-07 — Pilot report and go/no-go
- **Size:** S  ·  **Labels:** area:compliance, type:docs  ·  **Depends on:** P6-06  ·  **Plan ref:** §8 Phase 6
- **Description:** KPI results vs targets, incidents, lessons, recommendation for wider rollout.
- **Acceptance criteria:**
  - Report shared with stakeholders
