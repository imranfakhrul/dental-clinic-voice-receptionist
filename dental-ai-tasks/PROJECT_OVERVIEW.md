# AI Dental Receptionist: Project Overview

A web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental**, books, reschedules or cancels real appointments, sends confirmations and reminders, handles emergencies safely, and creates a callback case (with an email to the clinic admin) when it cannot finish a request. It is HIPAA-ready from day one.

This is a summary of the approved task specs in `tasks/` (as of 2026-11-24). The specs are the source of detail. Items marked **Proposed** are our design choices; **Verify** means an external fact still to be confirmed. Parts not yet specified (admin console, reminders, messaging provider) are marked *planned*.

---

## 1. Core principles

| Principle | What it means in practice |
|---|---|
| Open Dental is the source of truth | We store only Open Dental IDs (`PatNum`, `AptNum`), never copies of patient records |
| The LLM talks, code acts | Gemini only phrases replies and extracts data; a deterministic state machine decides, and a tool gateway executes |
| Explicit confirmation before any write | A confirmation card lists every detail; the write uses exactly what the patient confirmed (operation hash) |
| Safety over automation | Emergency rules run before the LLM; no diagnosis; callback when unsure |
| Fewest vendors, all under a BAA | Google Cloud (BAA), Google Workspace (BAA), one messaging provider (BAA) |
| Stream everything | Replies stream sentence by sentence; voice is fully streaming |

---

## 2. Technologies

### 2.1 Frontend
| Item | Technology |
|---|---|
| Framework | Next.js + TypeScript + Tailwind |
| Patient widget | `embed.js` snippet on the clinic site → iframe `/widget`; chat panel, cards, avatar panel |
| Admin console | Next.js (*planned*, P4) |
| Voice in browser | `getUserMedia` (echo cancellation, noise suppression), AudioWorklet (16 kHz PCM16, 20 ms frames), client VAD (`@ricky0123/vad-web`, **Proposed**) |
| Avatar | 2D animated avatar (Rive, **Proposed**) with idle / listening / thinking / speaking |
| Bot protection | reCAPTCHA Enterprise (the only third-party script allowed) |
| Accessibility | WCAG 2.2 AA, text-only mode, keyboard use, axe tests |
| Tests | Vitest, Playwright (E2E on staging) |

### 2.2 Backend
| Item | Technology |
|---|---|
| Language / framework | Python 3.12, **FastAPI**, Pydantic v2, async I/O |
| Database access | SQLAlchemy 2 (async) + Alembic migrations |
| Real-time | WebSocket `wss://api.<domain>/v1/sessions/{session_id}/ws` (text and voice on one socket) |
| Voice pipeline | Custom asyncio or Pipecat (decided by the P3-01 spike, ADR 0003), Silero VAD on the server |
| Quality | `ruff`, `mypy`, pytest (+ `respx` for HTTP mocks) |
| Code layout | `backend/app/{api, core, db, integrations, domain, orchestrator, tools, voice}` |

### 2.3 Google Cloud infrastructure
| Service | Use |
|---|---|
| Cloud Run | `api` service (REST, WebSocket, task handlers), US region (`us-central1`) |
| Cloud SQL for PostgreSQL | Application database, CMEK encryption, private IP |
| Memorystore for Redis | Live conversation state, slot memory (encrypted fields), locks, rate limits |
| Cloud Tasks + Cloud Scheduler | Callback-email queue, reminders, daily Open Dental refresh |
| Secret Manager + Cloud KMS | Open Dental keys, field-encryption keys, CMEK |
| Identity Platform | Staff login with TOTP MFA |
| Cloud Logging / Monitoring / Trace | PHI-redacted logs, latency dashboards, alerts |
| Vertex AI | Gemini models (US multi-region endpoint) |
| Speech-to-Text V2, Text-to-Speech | Voice |
| Terraform | All infrastructure as code; GitHub Actions CI/CD (dev → staging → prod) |
| Org policies, VPC Service Controls | US-only locations, HIPAA-covered services only, no API keys, no AI Studio |

---

## 3. AI models (Vertex AI) and prices

### 3.1 Gemini models per routing tier (P0-13, ADR 0001)
Model IDs are configuration (`GEMINI_MODEL_LITE`, `GEMINI_MODEL_FLASH`, `GEMINI_MODEL_PRO`), not code. Only GA models, US endpoint `us` (`aiplatform.us.rep.googleapis.com`), request logging off, durable caching off.

| Tier | Used for | Primary model | Fallback |
|---|---|---|---|
| `lite` | Greetings, simple acknowledgements | `gemini-3.5-flash-lite` | `gemini-3.1-flash-lite` |
| `flash` | Intent and slot extraction (JSON), normal replies | `gemini-3.8-flash` | `gemini-3.5-flash` |
| `pro` | Ambiguous, multi-part or complaint conversations | `gemini-4-argon` (if verified GA + covered) | `gemini-3.8-flash` with a higher thinking budget |

Many replies need no LLM at all: templates (confirmations, booked, cancelled), FAQ answers from clinic config, and emergency scripts are rendered by code.

### 3.2 Gemini prices (Vertex AI pricing page, read 2026-11-24)
We use the **US multi-region (non-global)** endpoint, so the non-global column applies. USD per 1M tokens, prompts ≤ 200K tokens.

| Model | Input | Cached input | Output | Notes |
|---|---|---|---|---|
| Gemini 3.5 Flash-Lite | $0.33 | $0.033 | $2.75 | Global: $0.30 / $2.50 |
| Gemini 3.1 Flash-Lite | $0.275 (audio $0.55) | $0.0275 | $1.65 | Global: $0.25 / $1.50 |
| Gemini 3.8 Flash (intro, until 2026-12-31) | $0.825 | $0.0825 | $4.125 | Global: $0.75 / $3.75 |
| Gemini 3.8 Flash (from 2027-01-01) | $1.65 | $0.165 | $8.25 | Global: $1.50 / $7.50 |
| Gemini 3.5 Flash | $1.65 | $0.165 | $9.90 | Global: $1.50 / $9.00 |
| Gemini 4 Argon (promo, until 2026-11-30) | $2.20 | $0.11 | $11.00 | Promotional (50% credit back) |
| Gemini 4 Argon (from 2026-12-01) | $4.40 | $0.22 | $22.00 | Global: $4.00 / $20.00 |

Not used: Gemini 3.8 Live API (speech-to-speech; we use the cascade for cost and control), preview models (never with PHI), grounding (off).

### 3.3 Speech-to-Text (P3-03)
| Item | Value |
|---|---|
| API | Speech-to-Text **V2**, `StreamingRecognize` (gRPC), location `us` |
| Model | `chirp_3` (or the model chosen by the P3-01 spike), `en-US` |
| Features | Interim (partial) results, automatic punctuation, phrase hints (dental words, clinic and dentist names, per-state hints) |
| Privacy | Data logging never enabled; audio never stored |
| Price (V2, standard models incl. Chirp) | $0.016/min (0–500K min/month), $0.010 (500K–1M), $0.008 (1M–2M), $0.004 (>2M); billed per second |

### 3.4 Text-to-Speech (P3-03)
| Item | Value |
|---|---|
| API | Text-to-Speech `StreamingSynthesize` (per-sentence `SynthesizeSpeech` as fallback) |
| Voice | Always a standard **female American English** voice from an allow-list (`TTS_ALLOWED_VOICES`, ADR 0007); `en-US` only |
| Read-aloud | Our `SpeechNormalizer` (phone digits one by one, times, "Doctor", clinic pronunciations); no SSML needed |

| Voice type | Free per month | Price per 1M characters |
|---|---|---|
| Chirp 3: HD | 1M chars | $30 |
| Neural2 | 1M chars | $16 |
| WaveNet | 4M chars | $4 |
| Standard | 4M chars | $4 |
| Studio | 1M chars | $160 |

The final voice family is chosen in the P3-01 listening test (likely Chirp 3 HD or Neural2).

### 3.5 Rough cost per conversation (estimate, **Proposed** assumptions)
Assumptions: 15 patient turns; per LLM turn ≈ 2,000 input + 150 output tokens (extraction) and ≈ 1,500 input + 60 output tokens (reply) on `gemini-3.8-flash` (half the replies are templates with no LLM call); voice sends ≈ 2 min of speech (client VAD gating); TTS ≈ 100 characters per reply.

| Item | Text chat | Voice (Chirp 3 HD) |
|---|---|---|
| LLM (intro price / from 2027) | ≈ $0.05 / $0.10 | ≈ $0.05 / $0.10 |
| Speech-to-Text | - | ≈ $0.03 |
| Text-to-Speech | - | ≈ $0.045 |
| **Total** | **≈ $0.05–0.10** | **≈ $0.13–0.18** |
P3-14 measures the real numbers (`dai.tts.chars`, `dai.stt.requests`, token counts).

### 3.6 Full flow

**Text turn**
```
Patient types → WebSocket user_turn → TurnProcessor (Redis lock)
  → emergency rules (P2-20, before any LLM)
  → extraction (Gemini, structured JSON) → slot validation
  → state machine handler → tool gateway → Open Dental (via adapter)
  → reply: template | config answer | Gemini stream → output guard (per sentence)
  → reply_chunk messages (sentence by sentence) → chat panel
```

**Voice turn** (target: first audio ≤ 1.5 s p50 after the patient stops)
```
Mic → AudioWorklet 16 kHz → client VAD (sends speech only, 300 ms pre-roll)
  → WebSocket binary frames → server Silero VAD → STT V2 streaming (partials)
  → endpointing (300 / 800 / 1200 / 1500 ms silence rules)
  → [speculative extraction on the partial during the wait]
  → same TurnProcessor as text (read-back of names/phone/DOB first)
  → reply sentences → SpeechNormalizer → TTS streaming → jitter buffer → speaker
  ↺ barge-in: patient speaks → pause at once → real words: stop TTS + cancel LLM; "uh-huh": resume
  ↺ filler ("Let me check that for you.") if no reply audio after 700 ms
```

**Latency targets:** endpoint ≤ 500 ms, LLM first token ≤ 300 ms, TTS first audio ≤ 250 ms, voice-to-voice ≤ 1.5 s p50 / 2.5 s p95, barge-in stop ≤ 200 ms, text first chunk ≤ 1 s.

---

## 4. Database (Cloud SQL PostgreSQL, schema `app`)

Conventions: UUID primary keys (except `audit_log`), `timestamptz` in UTC, PHI columns encrypted at field level (`*_enc`, AES via KMS-wrapped keys) with blind indexes (`*_bidx`, HMAC) for lookups. PHI legend: **P** = PHI, **R** = Open Dental reference, **-** = not PHI. Roles: `app_owner` (migrations), `app_rw` (the API; no update/delete on append-only tables), `app_ro`.

### `clinics`
| Column | Type | Notes |
|---|---|---|
| `id` | uuid | PK |
| `slug` | text | UNIQUE, `^[a-z0-9-]{3,40}$` |
| `name` | text | NOT NULL |
| `timezone` | text | IANA zone, e.g. `America/Los_Angeles` |
| `od_customer_key_secret` | text | Secret Manager secret **name** (never the key) |
| `active_config_version` | int | FK → `clinic_config_versions` |
| `status` | text | `ACTIVE`, `PAUSED`, `OFFBOARDED` |
| `created_at`, `updated_at` | timestamptz | |

### `clinic_config_versions` (immutable)
| Column | Type | Notes |
|---|---|---|
| `clinic_id`, `version` | uuid, int | PK |
| `config` | jsonb | Hours, holidays, appointment types, emergency rules, policies, voice, widget, clinic info, conversation settings (validated by Pydantic) |
| `schema_version` | int | |
| `created_by_staff_id` | uuid | FK `staff_users`, NULL = system |
| `change_note` | text | ≤ 500 chars |
| `created_at` | timestamptz | |

### `staff_users`
| Column | Type | Notes |
|---|---|---|
| `id` | uuid | PK |
| `clinic_id` | uuid | FK |
| `idp_uid` | text | UNIQUE (Identity Platform) |
| `email` | text | UNIQUE per clinic |
| `display_name` | text | |
| `role` | text | `ADMIN`, `FRONT_DESK`, `DENTIST`, `READ_ONLY` |
| `mfa_enrolled`, `active` | bool | |
| `last_login_at`, `created_at`, `updated_at` | timestamptz | |

### `sessions` (one patient conversation; live state is in Redis)
| Column | Type | PHI | Notes |
|---|---|---|---|
| `id` | uuid | - | PK |
| `clinic_id` | uuid | - | FK |
| `channel` | text | - | `TEXT`, `VOICE` (starting channel) |
| `status` | text | - | `ACTIVE`, `ENDED`, `EXPIRED`, `ESCALATED` |
| `end_reason` | text | - | `COMPLETED`, `IDLE_TIMEOUT`, `USER_LEFT`, `EMERGENCY_911`, `CALLBACK_CREATED`, `ERROR` |
| `verified_patnum` | bigint | R | Set after identity verification |
| `channel_switches` | int | - | |
| `config_version` | int | - | Config pinned for the session |
| `started_at`, `last_activity_at`, `ended_at` | timestamptz | - | |

### `appointment_refs` (appointments this system created or changed)
| Column | Type | PHI | Notes |
|---|---|---|---|
| `id` | uuid | - | PK |
| `clinic_id` | uuid | - | UNIQUE (`clinic_id`, `aptnum`) |
| `aptnum`, `patnum` | bigint | R | |
| `created_by_session_id` | uuid | - | FK `sessions` |
| `status_cache` | text | - | `SCHEDULED`, `CANCELLED`, `BROKEN`, `COMPLETE`, `UNKNOWN` (cache only) |
| `status_checked_at`, `created_at`, `updated_at` | timestamptz | - | |

### `contact_prefs`
| Column | Type | PHI | Notes |
|---|---|---|---|
| `clinic_id`, `patnum` | uuid, bigint | R | PK |
| `channel` | text | - | `SMS`, `WHATSAPP` |
| `messaging_address_enc` | bytea | P | Encrypted phone |
| `messaging_address_bidx` | bytea | P (hash) | Lookup index |
| `created_at`, `updated_at` | timestamptz | - | |

### `consents` (append-only; current state = latest row)
| Column | Type | PHI | Notes |
|---|---|---|---|
| `id` | uuid | - | PK |
| `clinic_id` | uuid | - | FK |
| `patnum` | bigint | R | NULL if only the address is known (e.g. STOP) |
| `messaging_address_bidx` | bytea | P (hash) | |
| `channel` | text | - | `SMS`, `WHATSAPP` |
| `purpose` | text | - | `APPOINTMENT_MESSAGES` |
| `action` | text | - | `GRANTED`, `REVOKED` |
| `source` | text | - | `CHAT`, `VOICE`, `SMS_STOP`, `SMS_START`, `STAFF` |
| `wording_version` | text | - | Template ID, e.g. `optin-v1` |
| `session_id`, `staff_user_id` | uuid | - | FKs |
| `occurred_at` | timestamptz | - | |

### `reminders`
| Column | Type | PHI | Notes |
|---|---|---|---|
| `id` | uuid | - | PK |
| `clinic_id` | uuid | - | FK |
| `aptnum`, `patnum` | bigint | R | |
| `kind` | text | - | `BEFORE_1H` |
| `scheduled_for` | timestamptz | P | UTC send time |
| `status` | text | - | `PENDING`, `ENQUEUED`, `SENT`, `SKIPPED`, `FAILED`, `CANCELLED` |
| `skip_reason` | text | - | `NO_CONSENT`, `APPT_CANCELLED`, `APPT_MOVED`, `TOO_LATE` |
| `task_name` | text | - | Cloud Tasks task ID |
| `attempts` | int | - | |
| `provider_msg_id`, `last_error_code` | text | - | Codes only |
| `created_at`, `updated_at` | timestamptz | - | |

### `callback_requests`
| Column | Type | PHI | Notes |
|---|---|---|---|
| `id` | uuid | - | PK |
| `clinic_id`, `session_id` | uuid | - | FKs |
| `case_ref` | text | - | `CB-` + 6 random chars, UNIQUE per clinic (shown to the patient) |
| `patient_type` | text | - | `NEW`, `EXISTING`, `UNKNOWN` |
| `patnum` | bigint | R | NULL if not verified |
| `contact_name_enc`, `contact_phone_enc` | bytea | P | Nullable for emergencies before details are known |
| `contact_phone_bidx` | bytea | P (hash) | |
| `contact_dob_enc`, `contact_email_enc`, `preferred_time_enc` | bytea | P | Optional |
| `reason_code` | text | - | `BOOKING_FAILED`, `NO_SLOTS`, `IDENTITY_UNVERIFIED`, `INSURANCE_BILLING`, `CLINICAL_QUESTION`, `URGENT_DENTAL`, `PATIENT_REQUEST`, `SYSTEM_ERROR`, `OTHER` |
| `reason_detail`, `extra_reasons` | text, text[] | - | Registry detail codes |
| `urgency` | text | - | `ROUTINE`, `URGENT` |
| `summary_enc` | bytea | P | Code-built summary |
| `status` | text | - | `OPEN`, `CONTACTED`, `RESOLVED` (one OPEN case per session) |
| `email_status` | text | - | `PENDING`, `SENT`, `FAILED` |
| `email_attempts`, `email_seq`, `email_sent_seq` | int | - | |
| `email_last_error`, `email_sent_at`, `upgraded_at` | text, timestamptz | - | |
| `assigned_to_staff_id` | uuid | - | FK |
| `created_at`, `updated_at`, `contacted_at`, `resolved_at` | timestamptz | - | |

### `audit_log` (append-only)
| Column | Type | Notes |
|---|---|---|
| `id` | bigint identity | PK |
| `clinic_id` | uuid | NULL for system events |
| `occurred_at` | timestamptz | |
| `actor_type`, `actor_id` | text | `SYSTEM`, `STAFF`, `PATIENT_SESSION` |
| `action` | text | e.g. `patient.search`, `appointment.book`, `auth.login_failed`, `config.update` |
| `object_type`, `object_ref` | text | IDs only (PatNum, AptNum, UUID) |
| `result` | text | `SUCCESS`, `FAILURE`, `DENIED` |
| `ip`, `request_id` | inet, text | |
| `details` | jsonb | Allow-listed codes and IDs only |

### `idempotency_keys` (safe retries for writes)
| Column | Type | Notes |
|---|---|---|
| `clinic_id`, `key` | uuid, text | PK; e.g. `book:<session_id>:<slot_hash>` |
| `operation` | text | `BOOK`, `RESCHEDULE`, `CANCEL`, `CREATE_PATIENT` |
| `request_hash` | bytea | SHA-256 of the canonical request |
| `status` | text | `IN_PROGRESS`, `SUCCEEDED`, `FAILED` |
| `result_ref` | text | AptNum or PatNum |
| `created_at`, `expires_at` | timestamptz | 24 h |

### Redis keys (live conversation, TTL = session idle time)
| Key | Content |
|---|---|
| `conv:{sid}:state` | Conversation state (JSON, no PHI): current state, history, flags |
| `conv:{sid}:slots` | Slot memory; PHI fields encrypted per field |
| `conv:{sid}:turns` | Last N turns (encrypted) for the LLM context |
| `conv:{sid}:display` | Last 30 shown messages (encrypted) for reload history |

---

## 5. Our APIs

### 5.1 Patient-facing (widget)
| Method + path | Auth | Request | Response |
|---|---|---|---|
| `GET /v1/public/clinics/{clinic_slug}/widget` | none (rate limited, cached 300 s) | - | `{display_name: string, accent_color: string, logo_url: string\|null, launcher_label: string, public_phone: string (E.164), recaptcha_site_key: string, voice_enabled: bool}` |
| `POST /v1/sessions` | reCAPTCHA token | `{clinic_slug: string (required), channel: "TEXT"\|"VOICE" (required)}` | 201 `{session_id: uuid, token: string (JWT), idle_timeout_s: int (900), expires_at: string (RFC 3339)}` |
| `DELETE /v1/sessions/{id}` | session token | - | 204 (end the chat) |
| `WS /v1/sessions/{session_id}/ws` | first message `auth` | see 5.2 | see 5.2 |

Rules: the token is never put in a URL; idle timeout 15 min, max life 2 h; one token = one session = one clinic.

### 5.2 WebSocket protocol (JSON text messages + binary audio)
| Direction | `type` | Fields (type) |
|---|---|---|
| C→S | `auth` | `token: string`, `protocol: 1\|2`, `resume: bool` |
| C→S | `user_turn` | `text: string (≤ 1000)`, `client_turn_id: string`, `choice_id: string?` |
| C→S | `ping` | - |
| S→C | `ready` | session info |
| S→C | `turn_ack` | `client_turn_id`, `turn_id` |
| S→C | `typing` | `on: bool` |
| S→C | `reply_chunk` | `turn_id`, `seq: int`, `text: string`, `final: bool`, `choices?: [{id, label}]`, `card?: ConfirmationCard`, `info_card?: InfoCard` |
| S→C | `error` | `code: rate_limited\|busy\|message_too_long\|internal_error\|protocol_error`, `retry_after_s?` |
| S→C | `session_expired` | - |
| C→S (v2) | `voice_start`, `voice_stop`, `speech_start`, `speech_end`, `mute`, `playback_ended`, `playback_paused` | voice control |
| S→C (v2) | `voice_ready`, `endpoint`, `utterance_discarded`, `transcript`, `playback_start`, `playback_pause`, `playback_resume`, `playback_flush`, `voice_stopped` | voice control |
| Binary (v2) | audio frame | 9-byte header (kind, seq, utterance/reply id) + PCM16 audio (mic: 16 kHz, 320 samples) |

Close codes: 4401 not authenticated, 4408 session expired, 4429 too many connections, 4400 protocol error.

Example confirmation card payload:
```json
{"type": "reply_chunk", "turn_id": "t-17", "seq": 1, "final": true,
 "text": "Please check them. If everything looks right, say yes. If anything is wrong, tell me what to change.",
 "card": {"kind": "book", "op_hash": "9f2c…",
          "rows": [{"label": "Patient", "value": "Priya Patel", "field": "name"},
                   {"label": "Date and time", "value": "Tue, Dec 8, 2026 at 9:00 AM PST", "field": "time"},
                   {"label": "Dentist", "value": "Dr. Lee", "field": "provider"}]},
 "choices": [{"id": "confirm:yes:9f2c…", "label": "Yes, that's correct"}]}
```

### 5.3 Staff and admin
| Method + path | Request | Response / notes |
|---|---|---|
| `POST /v1/auth/session` | Header `Authorization: Bearer <Identity Platform ID token>` (TOTP MFA required) | 200 `{staff, csrf_token}` + cookie `__Host-dai_staff` |
| `DELETE /v1/auth/session` | cookie + `X-CSRF-Token` | 204 logout |
| `GET /v1/admin/config` | - | Active clinic config (`CONFIG_READ`) |
| `PATCH /v1/admin/config` | Partial config JSON | New draft version (`CONFIG_WRITE`) |
| `GET /v1/admin/config/versions?limit=50`, `GET /v1/admin/config/versions/{v}`, `GET /v1/admin/config/diff?from=&to=` | - | History and diff |
| `POST /v1/admin/config/activate` | `{version: int}` | Activates a version |
| `GET /v1/admin/staff`, `POST /v1/admin/staff`, `PATCH /v1/admin/staff/{id}`, `POST /v1/admin/staff/{id}/resend-invite` | `{email, display_name, role}` | Staff management (`ADMIN`) |
| `POST /v1/admin/opendental/refresh` | - | Re-read providers, operatories, appointment types |
| Callback cases console API | - | *planned* (P4-13/P4-14) |

### 5.4 Internal (Cloud Tasks / Scheduler, OIDC-authenticated)
| Method + path | Purpose |
|---|---|
| `POST /internal/tasks/callback-emails` | Send one callback email (retried up to 10 times) |
| `POST /internal/jobs/callback-email-sweep` | Re-enqueue stuck emails |
| `POST /internal/jobs/od-setup-refresh` | Daily Open Dental setup refresh |
| `POST /internal/jobs/config-od-check` | Daily check that config references still exist in Open Dental |
| `GET /healthz`, `GET /readyz` | Health checks |

### 5.5 Backend tools (called by the state machine through the tool gateway, never directly by the LLM)
Result envelope: `{"ok": true, "data": {...}}` or `{"ok": false, "error": {"code": "slot_taken", "next": "offer_alternatives", "data": {...}}}`.

| Tool | Required input (type) | Output | Writes |
|---|---|---|---|
| `search_patient` | `last_name: str`, `dob: date (YYYY-MM-DD)`, `first_name?: str`, `phone?: str (E.164)` | `{outcome: "no_match"\|"verify"\|"ambiguous", ask_for: [str]}` | no |
| `verify_patient` | `answers: {mobile_phone?, zip_code?, first_name?}` | `{verified: bool, attempts_left: int}` | session only |
| `create_patient` | `first_name`, `last_name`, `dob`, `mobile_phone`, `email?`, `address?{line1, line2, city, state, zip}` | `{created: true}` | yes |
| `get_appointment_availability` | `reason_code: str`, `urgent?: bool`, `preferences?{earliest_date, latest_date, weekdays, parts_of_day, provider_name?}`, `later?: bool` | `{status, options: [{slot_id, when, provider, visit}], more: bool}` (2–3 options) | no |
| `get_patient_appointments` | `{}` | `{appointments: [{handle, when, provider, visit, status}]}` | no |
| `book_appointment` | `slot_id: str` | `{booked: true, when, provider, visit}` | yes |
| `reschedule_appointment` | `handle: str`, `slot_id: str` | `{rescheduled: true, when, provider, visit}` | yes |
| `cancel_appointment` | `handle: str` | `{cancelled: true}` | yes |
| `get_clinic_information` | `topics: [hours\|address\|phone\|parking\|insurance\|services\|languages\|payment\|new_patients\|website]` | `{answers: {topic: text}}` | no |
| `get_provider_information` | `provider_name?: str` | `{providers: [{name, specialty, works_on}]}` | no |
| `create_callback_request` | `reason_code`, `urgency`, `summary (≤ 500)` | `{case_ref: "CB-7Q2M4X", promise: str}` | yes |
| `record_consent` | `channel`, `granted: bool`, `template_id` | `{recorded: true}` | yes (*planned* P4-02) |

Every write needs a fresh "yes" to a confirmation card whose operation hash matches the arguments, an idempotency key, and an audit entry.

---

## 6. Integrations

### 6.1 Open Dental (practice-management system, source of truth)
| Item | Value |
|---|---|
| API | Open Dental Remote API, base `https://api.opendental.com/api/v1` |
| Auth | Header `Authorization: ODFHIR {DeveloperKey}/{CustomerKey}`; developer key in Secret Manager, one customer key per clinic |
| Throttle | 1 request/s per customer key; our client queues per clinic, retries with backoff, maps errors to typed exceptions |
| Minimum clinic version | 22.4.10 (Verify against the pilot clinic) |

| Endpoint | Used for |
|---|---|
| `GET /patients/Simple` | Search by last name, first name, birthdate (identification) |
| `GET /patients` | Search with `Phone` (fallback) |
| `GET /patients/{PatNum}` | Read one patient (verification, callback contact) |
| `POST /patients` | Create a new patient (`LName`, `FName` required; `Birthdate`, `WirelessPhone`, `Email`, `Address`…); duplicate check before create |
| `GET /appointments/Slots` | Open slots per provider (`dateStart`, `dateEnd`, `lengthMinutes`, `ProvNum`, `OpNum`) |
| `GET /appointments`, `GET /appointments/{AptNum}` | Patient's appointments; re-check before changes |
| `POST /appointments` | Book (`PatNum`, `Op`, `AptDateTime`, `Pattern`, `ProvNum`, `AppointmentTypeNum`, `Note` with AI marker) |
| `PUT /appointments/{AptNum}` | Reschedule (new `AptDateTime`, `Op`) |
| `PUT /appointments/{AptNum}/Break` | Cancel (`sendToUnscheduledList: true`) |
| `PUT /appointments/{AptNum}/Note` | Append the AI marker `[AI-booked ref:…]` |
| `GET /providers`, `/operatories`, `/appointmenttypes`, `/clinics`, `/schedules`, `/definitions` | Setup data (cached, refreshed daily) |

### 6.2 Communication
| Channel | Provider | Status |
|---|---|---|
| Admin callback email | **Gmail API** from our Google Workspace (Workspace HIPAA BAA), sender `callbacks@<company domain>`, keyless service account with domain-wide delegation (`gmail.send` only), TLS enforced per clinic domain | Approved (P0-08, P2-22) |
| Email content | Default `link_only`: urgency, time, case ID and console link, **no PHI**; `full_details` only with written compliance approval | Approved |
| Patient confirmations and reminders | **SMS** via a provider whose BAA covers SMS (Proposed default); **WhatsApp** only if the compliance advisor approves, because Meta states the WhatsApp Business Platform is not HIPAA compliant | Decision memo P0-07a; provider P0-07; sending *planned* (P4) |
| Reminder timing | 1 hour before the appointment, only with recorded consent; skipped if cancelled or moved | *planned* (P4) |
| Bot protection | reCAPTCHA Enterprise (score < 0.3 blocked, 0.3–0.5 strict mode) | Approved (P2-25) |

### 6.3 Abilities (what the AI can do)
| Ability | How it works |
|---|---|
| **Identify a returning patient** | Collects first name, last name, DOB and phone (or ZIP) before any search; needs ≥ 2 matching identifiers, never phone alone; no hint about which detail was wrong |
| **Register a new patient** | Collects name, DOB, mobile (email/address optional or required per clinic); confirmation card; duplicate check; creates in Open Dental; never auto-creates when ambiguous |
| **Household booking** | A parent can book for up to four family members in one chat |
| **Search availability** | Reason → appointment type → duration → eligible providers; real Open Dental slots minus blockouts and holidays; 2–3 options; nearest opening after the requested time |
| **Book** | Confirmation card → slot lock → re-check → `POST /appointments` → verify → booked message (and SMS/WhatsApp *planned*) |
| **Check appointments** | Lists future scheduled appointments for the verified patient |
| **Reschedule / cancel** | Respects the clinic's notice window; inside the window → callback; optional cancel reason; offers to rebook |
| **Answer clinic questions** | Hours, address, parking, insurance accepted, services, payment, providers — from clinic config, no LLM guessing |
| **Emergencies** | Tier 1 (e.g. trouble breathing): "call 911" script, URGENT case; crisis: 988 script; Tier 2 (severe pain, swelling): earliest urgent slot or URGENT callback; never diagnoses |
| **Callback** | Any unresolved request becomes a case (`CB-…`) with an admin email; one open case per session |
| **Voice** | Streaming speech in and out, barge-in, fillers, read-back of names/phone/DOB, spelling mode, female US English voice |
| **Switch voice ↔ text** | Same session and memory; switch anytime |
| **Consent** | Records opt-in/opt-out for messages (*planned* P4) |

---

## 7. Security and HIPAA (summary)
- Business Associate Agreements: Google Cloud, Google Workspace, messaging provider; clinic ↔ company BAA.
- US-only locations, HIPAA-covered services only, no API keys, no Gemini Developer API (AI Studio).
- PHI encrypted in the DB (CMEK + field encryption) and in Redis; never in logs, URLs or email subjects.
- Raw audio never stored; STT data logging never enabled.
- Staff: MFA (TOTP), roles (`ADMIN`, `FRONT_DESK`, `DENTIST`, `READ_ONLY`), audit log for every PHI access and write.

## 8. Pilot targets
| Target | Value |
|---|---|
| Bookings without callback | ≥ 70% |
| Voice-to-voice latency | ≤ 1.5 s p50, ≤ 2.5 s p95 |
| Double bookings / duplicate patients | 0 / 0 |
| Reminders for cancelled appointments | 0 |
| Emergency escalation in tests | 100% |
| PHI in logs | 0 |

## 9. Phases
P0 discovery and compliance → P1 core platform and Open Dental adapter → P2 text chat → P3 voice (parallel with P4) → P4 messaging, reminders and admin console → P5 hardening and security review → P6 pilot launch.
