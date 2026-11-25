# Task consolidation (DECISIONS #76)

The 124 seed tasks are consolidated into **69 issues** (70 after the P4-13 split, DECISIONS #266) so the whole production-grade project fits in 60–70 GitHub issues. Nothing is dropped: each merged task's scope and acceptance criteria move into its survivor. Merged tasks keep their IDs as stub files (`status: merged`, `merged_into: <survivor>`); `tools/build_pdf.py` redirects dependencies on a merged task to its survivor. IDs are never reused.

When writing a survivor spec: include the merged tasks' descriptions and acceptance criteria, re-size it (must stay ≤ L; split with `a`/`b` suffixes if not), and list the merged IDs in §1.

| # | Issue | Title (seed) | Absorbs |
|---|---|---|---|
| 1 | P0-01 | Run discovery workshop with pilot clinic | - |
| 2 | P0-02 | Document appointment-type mapping (reason -> type -> duration -> providers) | - |
| 3 | P0-03 | Document draft emergency protocol (Tier 1/2/3) for clinic review | - |
| 4 | P0-04 | Write conversation flow designs | - |
| 5 | P0-05 | Create Google Cloud org/project and accept Google Cloud BAA | - |
| 6 | P0-06 | Restrict projects to HIPAA covered products (org policies + VPC-SC) | - |
| 7 | P0-07 | Select WhatsApp BSP that signs a BAA and sign it | - |
| 8 | P0-07a | Decide HIPAA-compatible patient messaging channel (compliance memo) | - |
| 9 | P0-08 | Decide admin email route and sign BAA | - |
| 10 | P0-09 | Prepare clinic <-> company BAA | - |
| 11 | P0-10 | Create vendor/BAA matrix document | - |
| 12 | P0-11 | Risk assessment v1 | - |
| 13 | P0-12 | Get Open Dental API keys and a test database | - |
| 14 | P0-13 | Choose GA Gemini model versions per routing tier | - |
| 15 | P0-14 | Architecture doc + PHI data-flow diagram | - |
| 16 | P0-15 | Register WhatsApp number and submit message templates | - |
| 17 | P1-01 | Set up monorepo structure and coding standards | P1-08 FastAPI service skeleton with health checks and config |
| 18 | P1-02 | Terraform base: VPC, Cloud Run, Artifact Registry | P1-04 Terraform: Memorystore Redis, Cloud Tasks, Cloud Scheduler |
| 19 | P1-03 | Terraform: Cloud SQL Postgres with CMEK | P1-09 Database schema and migrations (all §5 tables) |
| 20 | P1-05 | Secret Manager + KMS setup and service accounts | P1-10 Field-level encryption helper (KMS envelope encryption) |
| 21 | P1-06 | CI/CD pipeline: build, test, deploy to dev/staging/prod | - |
| 22 | P1-07 | Cloud Logging/Monitoring baseline + latency dashboard skeleton | P1-11 PHI-redacting logger middleware, P1-12 Audit log service |
| 23 | P1-13 | Staff auth with MFA and RBAC | P1-14 Patient session tokens, idle timeout and rate limiting |
| 24 | P1-15 | Open Dental HTTP client: auth, retries, rate-limit handling | P1-18 Adapter: providers, appointment types, schedules, operatories |
| 25 | P1-16 | Adapter: patient search / get / create | P1-17 Adapter: appointments get / create / update / break |
| 26 | P1-19 | Clinic config service (hours, holidays, rules) | - |
| 27 | P1-20 | Availability engine: compute free slots | P1-21 Slot lock + booking sequence |
| 28 | P1-22 | Tool endpoints: patient tools | P1-23 Tool endpoints: appointment tools, P1-24 Tool endpoints: info tools |
| 29 | P2-01 | State machine core with all states and side branches | P2-02 Slot memory (structured JSON) in Redis with encryption |
| 30 | P2-03 | LLM provider interface + Vertex AI Gemini implementation | P2-06 Model router (templates / Flash-Lite / Flash / Pro / rules) |
| 31 | P2-04 | Compact context builder with PHI masking | P2-07 System prompt v1 + reply phrasing, P2-11 Prompt-injection defenses and tool output sanitizing |
| 32 | P2-05 | Intent + slot extraction with structured JSON output | - |
| 33 | P2-08 | Tool gateway: schema validation + allow-list | P2-09 Tool gateway: state preconditions + session scoping, P2-10 Idempotency keys on create/modify tools |
| 34 | P2-12 | Normalization utilities (names, nicknames, phone E.164, DOB ISO) | P2-13 Candidate matching and scoring, P2-14 Verification flow (2+ identifiers, no record leaks) |
| 35 | P2-15 | New patient registration flow | - |
| 36 | P2-16 | Booking flow: reason -> type -> 2-3 options -> confirm -> book | P2-17 Check existing appointment flow |
| 37 | P2-18 | Reschedule and cancel flows (with cancellation window policy) | P2-19 FAQ answers from clinic config |
| 38 | P2-20 | Emergency detector v1 (rules first, model second) | P2-21 Emergency scripts and Tier 2 urgent-slot path |
| 39 | P2-22 | Callback request service (case creation) | P2-23 Admin email sender (BAA-covered, retry, unsent alerts), P2-24 Callback conversation flow (collect, read back, tell patient) |
| 40 | P2-25 | Next.js widget shell + session handshake | P2-26 Chat messages with streaming replies, P2-29 Bot protection on public widget |
| 41 | P2-27 | Slot option cards and confirmation cards | P2-28 Accessibility pass (keyboard, screen reader, text-only mode) |
| 42 | P2-30 | Phase 2 E2E: text booking on staging | - |
| 43 | P3-01 | Latency spike: STT -> Gemini Flash -> TTS prototype | - |
| 44 | P3-02 | Audio transport (WebSocket/WebRTC) browser <-> backend | P3-04 VAD + endpointing (client VAD, Silero server, semantic turn) |
| 45 | P3-03 | Streaming Speech-to-Text integration with phrase hints | P3-05 Streaming Text-to-Speech with sentence chunker + SSML |
| 46 | P3-06 | Barge-in: stop TTS and cancel LLM stream | P3-07 Filler phrases during tool calls + warm connections, P3-08 Speculative LLM calls on stable partials |
| 47 | P3-09 | Read-back confirmation for names, phones, dates, times | P3-10 Spelling mode (letter by letter) |
| 48 | P3-11 | Avatar with states (idle / listening / thinking / speaking) | P3-12 Live transcript in chat panel, P3-13 Seamless voice <-> text switching in one session |
| 49 | P3-14 | Per-stage latency instrumentation + dashboard | P3-15 Latency tuning to hit targets, P3-16 Phase 3 demo: voice-to-voice booking |
| 50 | P4-01 | Messaging provider interface + WhatsApp BSP adapter | P4-06 Delivery webhooks, retries and failure alerts, P4-07 Opt-out handling (STOP) |
| 51 | P4-02 | Consent capture and storage | P4-16 Consent / opt-out management screen |
| 52 | P4-03 | Booking confirmation message | P4-08 Reschedule and cancellation notifications |
| 53 | P4-04 | Reminder scheduler (appointment - 60 min, DST-aware) | P4-05 Pre-send verification (re-fetch appointment) |
| 54 | P4-09 | Admin console shell with staff login and RBAC | P4-10 Clinic profile, hours and holidays screens |
| 55 | P4-11 | Appointment type mapping and policies screens | P4-12 Emergency rules editor with approval workflow and history |
| 56 | P4-13 | WhatsApp, voice and callback settings screens | - (split, DECISIONS #266) |
| 56a | P4-13a | Callback cases, AI activity log and failed messages screens (new) | P4-14 Callback cases list and status workflow, P4-15 AI activity log and AI-booked appointment review |
| 57 | P4-17 | Phase 4 E2E: book -> confirm -> remind -> reschedule/cancel -> notify | - |
| 58 | P5-01 | Conversation eval harness (runs on every prompt/model change) | P5-02 Write 100+ conversation scenarios |
| 59 | P5-03 | Voice test sets: accents, noise, mic quality; WER on critical fields | P5-06 Load and latency tests (concurrent sessions) |
| 60 | P5-04 | Scheduling edge-case tests (races, DST, holidays, providers) | P5-05 Reminder tests (timing, cancel/move, retries, opt-out) |
| 61 | P5-07 | UAT with clinic staff on staging | P5-15 Clinic sign-off on emergency scripts and policies |
| 62 | P5-08 | PHI-in-logs scan and credential exposure scan | P5-09 LLM red teaming: prompt injection and tool misuse, P5-10 Auth/authorization tests + OWASP Top 10 review |
| 63 | P5-11 | External penetration test and fixes | - |
| 64 | P5-12 | Incident response plan and outage runbooks | P5-13 Backup/restore drill and retention deletion jobs |
| 65 | P5-14 | HIPAA readiness review (BAAs, policies, risk assessment final) | - |
| 66 | P6-01 | Production readiness checklist and go-live | - |
| 67 | P6-02 | KPI instrumentation and pilot dashboard | P6-03 Post-chat rating widget |
| 68 | P6-04 | Soft launch at pilot clinic | P6-05 Weekly review of callbacks and failed conversations, P6-06 Tuning: prompts, vocabulary, routing, rules |
| 69 | P6-07 | Pilot report and go/no-go | - |

Also: P0-11 gaps G1–G3 (workforce security policies and training, periodic access reviews, device policy) are added to the scope of **P5-14**.
