# Project Plan
## AI Voice Receptionist & Appointment Management System for US Dental Clinics

**Document type:** Implementation plan (MVP + roadmap)
**Version:** 1.0

---

## 1. Executive Summary

We will build a web-based AI receptionist that patients can talk to (voice) or type to (chat), switching freely between the two. It identifies new vs. returning patients through Open Dental, registers new patients without duplicates, offers only real availability, books / reschedules / cancels appointments, sends WhatsApp confirmations and one-hour reminders, escalates emergencies, and, when it can't resolve something, records a callback request and emails the clinic admin (no live transfer). The system runs on **Google Cloud**, with **Gemini models on Vertex AI** for conversation and Google Cloud Speech-to-Text and Text-to-Speech for voice. That way one Google Cloud BAA covers the LLM, voice, hosting and database. The system is designed around HIPAA requirements from day one: PHI minimization, BAAs with every vendor that touches PHI, encryption, RBAC, and audit logging.

**Guiding principles**

1. **Open Dental is the source of truth.** We store references (PatNum, AptNum), not copies of records.
2. **The LLM talks; deterministic code acts.** The model understands and converses; identification, scheduling and booking are enforced by backend business logic.
3. **Stream everything.** STT, LLM and TTS all stream so the first audio reply starts quickly.
4. **Safety over automation.** Never diagnose, never invent availability, never book without confirmation, and raise a callback request for the admin when unsure.
5. **Swappable providers.** LLM, STT, TTS and messaging sit behind interfaces.
6. **Fewest possible BAAs.** Keep everything that touches PHI inside Google Cloud where possible.

> **Why Vertex AI:** Standalone LLM APIs (e.g., Groq) were considered for their speed, but they would add more vendors and BAAs. With **Gemini on Vertex AI**, one click-to-accept Google Cloud BAA covers the LLM, STT, TTS, hosting and database. Because of the provider abstraction, another LLM can still be plugged in later if it's needed and covered by a BAA.

---

## 2. What a Patient Can Do (Functional Scope)

| # | Patient capability | MVP |
|---|---|---|
| 1 | Talk to the receptionist by voice, with interruption (barge-in) | ✅ |
| 2 | Type in chat instead, or switch between voice and text mid-conversation | ✅ |
| 3 | See a live transcript and appointment options in the chat panel | ✅ |
| 4 | Ask about services, hours, location and accepted insurance | ✅ |
| 5 | Be recognized as an existing patient (after verification) | ✅ |
| 6 | Register as a new patient conversationally | ✅ |
| 7 | Describe a concern (e.g., tooth pain, cleaning) and get the right appointment type, with no diagnosis given | ✅ |
| 8 | See real available slots and book one | ✅ |
| 9 | Receive a booking confirmation (on screen + WhatsApp) | ✅ |
| 10 | Receive a WhatsApp reminder ~1 hour before the appointment (with consent) | ✅ |
| 11 | Reschedule or cancel an appointment | ✅ (basic) |
| 12 | Check an existing appointment | ✅ |
| 13 | Get emergency guidance (911 / urgent slot / urgent callback request) | ✅ |
| 14 | Have an unresolved issue (or a request to talk to a person) recorded, with a callback from the admin | ✅ |
| 15 | Opt out of WhatsApp messages | ✅ |
| 16 | Phone calls, insurance verification, intake forms, multi-language | ❌ Future |

**What clinic staff can do:** receive callback-request emails with the patient's name, number and situation, track those cases in the admin console, review AI-booked appointments and activity logs, configure hours, holidays, appointment types, policies, emergency rules, reminder settings and voice, and manage consent/opt-outs.

---

## 3. System Architecture

### 3.1 High-level view

```
┌──────────────────────── Frontend (Web, desktop + mobile) ────────────────────────┐
│  Avatar + Voice Panel  │  Chat Panel (messages, live transcript, slot cards)     │
│  Mic / VAD client      │  Keyboard-accessible, text-only mode                    │
└──────────────┬─────────────────────────────────────────────┬────────────────────┘
               │ WebSocket / WebRTC (audio + events)          │ HTTPS (chat, session)
┌──────────────▼─────────────────────────────────────────────▼────────────────────┐
│                               Backend (API Gateway)                              │
│  Auth & Session  │  Security/Authorization Layer  │  Rate limiting                │
├──────────────────────────────────────────────────────────────────────────────────┤
│  Conversation Orchestrator (state machine + slot filling)                        │
│    ├─ Streaming Audio Handler (STT in, TTS out, barge-in)                        │
│    ├─ AI Model Router (fast model / strong model / rules)                        │
│    ├─ Safety & Emergency Detector (rules + model)                                │
│    └─ Tool Gateway (validated, allow-listed tools only)                          │
├──────────────────────────────────────────────────────────────────────────────────┤
│  Patient Identification Svc │ Scheduling Svc │ Callback Svc│ Clinic Config Svc   │
│  Open Dental Adapter        │ WhatsApp Adapter │ Reminder Scheduler (job queue) │
│  Audit Logger (PHI-redacted)                                                     │
└──────┬───────────────┬──────────────┬───────────────┬──────────────┬────────────┘
       │               │              │               │              │
  Open Dental API  Vertex AI     Google Cloud   Google Cloud   WhatsApp BSP + Email (BAA)
                   (Gemini)      Speech-to-Text Text-to-Speech
       │
  Cloud SQL for PostgreSQL (encrypted) + Memorystore Redis (session state, locks) + Cloud Tasks (jobs)
  ── all Google Cloud components under one Google Cloud BAA ──
```

### 3.2 Recommended tech stack (Google Cloud; finalize in Phase 0)

| Layer | Recommendation | Notes |
|---|---|---|
| Frontend | React / Next.js + TypeScript, Tailwind | Accessible components; WebRTC/WebSocket audio |
| Avatar | 2D animated / Lottie or Rive avatar driven by state (idle, listening, thinking, speaking) | Lightweight; lip-sync optional later |
| Real-time voice transport | WebSocket audio streaming (or WebRTC) to the backend | Browser echo cancellation enabled |
| Backend | Python (FastAPI) on **Cloud Run** or **GKE** | Async, streaming-friendly; private networking |
| Voice agent framework | Pipecat (optional) | Has Google STT/TTS/Gemini integrations; speeds up VAD, turn-taking and barge-in |
| **LLM** | **Gemini on Vertex AI** (Gemini Enterprise Agent Platform), GA model versions only, model IDs configurable | Fast Flash-class model for most turns; Pro-class model for complex cases |
| **STT** | **Google Cloud Speech-to-Text** (streaming) | Phrase hints / custom vocabulary for dental terms and names; **do not opt into data logging** |
| **TTS** | **Google Cloud Text-to-Speech** (streaming, natural American English voice) | SSML for pauses and number read-back |
| VAD | Silero VAD (server) + browser-side VAD | Turn detection and barge-in |
| Database | **Cloud SQL for PostgreSQL** (or AlloyDB), encrypted at rest with CMEK | References, consent, reminders, callback cases, audit |
| Cache / locks | **Memorystore for Redis** | Session state, slot locks |
| Jobs / scheduling | **Cloud Tasks** + **Cloud Scheduler** | Reminder jobs at appointment − 60 min, retries |
| Secrets & keys | **Secret Manager** + **Cloud KMS** | Open Dental keys never reach the frontend |
| Logging / monitoring | **Cloud Logging** + **Cloud Monitoring** (PHI redacted before logging) | Latency dashboards per pipeline stage |
| Messaging | WhatsApp Business Platform via a BSP that signs a BAA | Pre-approved templates |
| Admin email | **Gmail API via Google Workspace** (under the Workspace BAA), or a transactional email service that signs a BAA | Callback-request emails to the clinic admin; TLS enforced |

### 3.3 BAA strategy (vendor matrix)

| Vendor | Covers | How the BAA is obtained |
|---|---|---|
| **Google Cloud** | Vertex AI (Gemini), Speech-to-Text, Text-to-Speech, Cloud Run/GKE, Cloud SQL, Memorystore, Cloud Tasks, Secret Manager, KMS, Logging | Accept the Google Cloud BAA in the console (click-to-accept; requires a Google Cloud agreement and billing account) |
| **Google Workspace** (if Gmail is used for admin emails) | Gmail | Accept the Workspace BAA in the Workspace admin console |
| **WhatsApp BSP** | Reminder and confirmation messages | Sign the BSP's BAA (choose a BSP that offers one) |
| **Clinic ↔ our company** | Our app's access to Open Dental data | We are the clinic's business associate, so we sign a BAA with each clinic |

**Rules**

- Use only Google Cloud products on Google's **HIPAA covered-products list**, and check the list again before adding any new service.
- **Do not use Google AI Studio / Gemini Developer API keys**: call Gemini only through Vertex AI in the BAA-covered Google Cloud project.
- **Do not use Pre-GA (preview/experimental) models or features** with PHI.
- Turn off or avoid any data-logging / data-sharing options (e.g., the Speech-to-Text data logging program).
- Keep PHI out of logs, so no extra monitoring vendor needs a BAA.
- Have a HIPAA advisor or lawyer review the BAA terms before production.

> **Compliance gate:** No PHI flows to any vendor until its BAA is accepted or signed and recorded in the vendor matrix above.

---

## 4. Core Design Decisions

### 4.1 Conversation orchestration: hybrid state machine + LLM

- A **deterministic state machine** owns the workflow: `GREETING → INTENT → IDENTIFY/REGISTER → VERIFY → APPOINTMENT_TYPE → AVAILABILITY → CONFIRM → BOOK → WRAP_UP`, with side branches `EMERGENCY`, `CALLBACK_REQUEST`, `RESCHEDULE` and `CANCEL`.
- The **LLM** handles natural language: intent extraction, slot extraction (name, DOB, phone, preferred time), phrasing replies and handling digressions.
- **Slot memory** (structured JSON) prevents re-asking for information already given, so only missing fields are requested.
- The LLM receives a **compact context**: the current state, filled slots (with PHI masked where possible), the last few turns and allowed tools. It does not get the full history.

### 4.2 Tool calling and guardrails

- Backend tools: `search_patient`, `verify_patient`, `create_patient`, `get_appointment_availability`, `get_patient_appointments`, `book_appointment`, `reschedule_appointment`, `cancel_appointment`, `get_clinic_information`, `get_provider_information`, `create_callback_request` (creates the callback case and sends the admin email, see §4.9).
- Every tool call passes through a **Tool Gateway**:
  - JSON-schema validation of inputs.
  - **State preconditions**: e.g., `book_appointment` is allowed only when the patient is verified, the slot came from a fresh availability query, and an explicit confirmation is recorded.
  - **Session scoping**: tools can only act on the patient verified in *this* session.
  - **Idempotency keys** on create/modify operations.
- The LLM never sees Open Dental credentials or raw API access.
- **Prompt-injection defense**: user text is treated as data; system instructions can't be overridden; tool outputs are sanitized before being shown to the model.

### 4.3 Model routing

| Situation | Handler |
|---|---|
| Greetings, acknowledgements, confirmations | Templates / Gemini Flash-Lite-class model |
| Intent and slot extraction | Gemini Flash-class model with structured (JSON) output |
| Ambiguous, multi-part or complaint conversations | Gemini Pro-class model |
| Emergency keywords | Rule-based detector first, model as second check |
| Identification, scheduling, booking logic | Deterministic code (no LLM decision) |
| Static answers (hours, address, insurance list) | Clinic config lookup (no LLM call) |

### 4.4 Low-latency voice pipeline

```
Mic → client VAD → audio frames (20ms) → streaming STT (partials + finals)
    → endpointing (VAD + silence + semantic turn detection)
    → orchestrator → LLM stream (tokens)
    → sentence chunker → streaming TTS → audio chunks → playback
    ↑ barge-in: user speech detected → stop TTS + cancel LLM stream immediately
```

**Latency targets (to validate in testing):**

| Stage | Target |
|---|---|
| End of user speech → endpoint detected | ≤ 300–500 ms |
| LLM time-to-first-token | ≤ 300 ms |
| TTS time-to-first-audio | ≤ 250 ms |
| **Voice-to-voice (first audio heard)** | **≤ ~1.0–1.5 s p50** |
| Barge-in stop time | ≤ 200 ms |
| Text chat first token | ≤ 1 s |

**Voice architecture:** a cascaded pipeline: Google Speech-to-Text → Gemini (text) → Google Text-to-Speech. Each step is under our control, transcripts are available, and each piece is easy to test. Live / native-audio models are not used, to keep costs down.

**Techniques:** speculative LLM calls on stable partial transcripts; filler phrases ("Let me check that for you…") while Open Dental queries run; parallel tool calls; caching clinic info, providers and appointment types; warm connections.

**Critical data confirmation:** Names, phone numbers, dates and times are read back ("That's 5-5-5, 1-2-3, 4-5-6-7, correct?") before use. Names can be spelled out letter by letter.

### 4.5 Patient identification and duplicate prevention

**Matching strategy (configurable per clinic):**

1. Normalize: names (case, whitespace, common nicknames), phone (E.164), DOB (ISO).
2. Search Open Dental by last name + DOB, and separately by phone.
3. Score candidates:
   - **Strong match:** last name + first name (fuzzy) + DOB match → proceed to verification.
   - **Partial match** (e.g., phone only, or shared family phone) → ask for an additional identifier.
   - **Multiple matches** → ask a disambiguating question; if it's still ambiguous, create a callback request (§4.9).
   - **No match** → confirm spelling and DOB once more → new patient flow.
4. **Verification:** require at least two identifiers per clinic policy (e.g., DOB + phone); never verify on phone alone.
5. **Never auto-create** a patient when the result is ambiguous.
6. Don't reveal record details before verification (avoid confirming "yes, you're a patient here" to an unverified caller).

### 4.6 Scheduling and conflict prevention

- Availability is calculated from Open Dental schedules, operatories, existing appointments, appointment-type durations and clinic rules (hours, holidays, new-patient slots, emergency blocks).
- Offer 2–3 options at a time, phrased naturally.
- **Booking sequence:** confirm with patient → acquire short Redis lock on the slot → **re-query Open Dental** → create the appointment with an idempotency key → verify the created record → release lock → confirm to patient.
- The appointment is only "booked" once Open Dental confirms creation.
- On conflict: apologize, re-fetch and offer alternatives.
- New patient appointments can be created with an "unconfirmed/AI-booked" status or note, so staff can review them (configurable).

### 4.7 WhatsApp reminders

- After booking: store `AptNum`, WhatsApp number reference, consent record (timestamp, channel, wording shown) and preferences.
- Send a confirmation template immediately (if consented).
- Schedule a job at `appointment_time − 60 min` (clinic time zone, DST-aware).
- **Before sending:** re-fetch the appointment from Open Dental; if it's cancelled, moved or the patient opted out, cancel the job (and reschedule it if moved).
- Use pre-approved WhatsApp templates with minimal content: name, clinic, date and time. No procedure or symptom details.
- Track delivery webhooks (sent / delivered / read / failed); retry with backoff and alert the admin in the console after the final failure.
- Handle opt-out keywords ("STOP") and update consent.
- Note: the WhatsApp Business messaging window rules require template messages for business-initiated reminders.

### 4.8 Emergency and safety handling

- **Tier 1 (life-threatening):** difficulty breathing or swallowing, swelling spreading to the eye or neck, uncontrolled bleeding, major trauma → immediately advise calling 911 or going to the ER; also create an URGENT callback case + admin email (§4.9).
- **Tier 2 (urgent dental):** severe pain, facial swelling, knocked-out tooth, signs of infection → collect minimal info, offer the earliest urgent slot; if none is available, create an URGENT callback request and email the admin (§4.9).
- **Tier 3 (routine symptoms):** sensitivity, mild pain → appropriate appointment type.
- Rules are stored in clinic configuration and must be **reviewed and approved by the clinic**. Detection is rules-first with model assistance; when uncertain, create an URGENT callback request.
- Fixed, pre-approved response scripts for emergencies. No diagnosis and no treatment advice.

### 4.9 Unresolved Situations: Callback Request + Admin Email (no live transfer)

The AI handles every conversation end to end. **There is no live transfer to a human.** When the AI can't resolve something, it records the situation, tells the patient the admin team will contact them, and emails the clinic admin straight away.

**When this flow runs:**

- The patient asks to speak to a person.
- The AI can't understand the patient after repeated attempts.
- Identification fails, or several patient records match.
- A scheduling conflict can't be resolved, or there is no suitable slot.
- Open Dental is unavailable, or booking / rescheduling / cancellation fails.
- Insurance or billing questions that need staff checks.
- Questions that need medical judgment.
- Complaints, or sensitive or complex requests.
- Urgent (Tier 2) dental issues when no urgent slot is available (flagged **URGENT**).

**Flow**

1. **Detect** that the situation can't be resolved (rules + model signal, per the triggers above).
2. **Collect details**, depending on patient type:
   - **New patient:** collect the full new-patient details: first and last name, phone number, WhatsApp number if different, date of birth, email, address, preferred contact method, and the reason or situation.
   - **Existing patient:** identify and verify through Open Dental if possible, and link the patient reference (PatNum). If verification fails, collect name, phone number and date of birth so the admin can find the record.
   - **Both:** a short description of the situation in the patient's own words, plus the preferred callback time.
3. **Read back** the name and phone number to confirm them (as in §4.4).
4. **Create a callback case** in the app DB: reason category, urgency, patient details, situation summary and status `OPEN`.
5. **Tell the patient** (always in English), for example: *"Thank you, [First Name]. I've noted your situation, and our admin team will contact you very soon at [phone number]. Is there anything else I can help you with today?"* For an **URGENT** case, add: "I've marked this as urgent."
6. **Email the admin** right away (see the template below).
7. **Track the case:** the admin marks it `CONTACTED` / `RESOLVED` in the admin console. If the email fails to send, retry with backoff and show the case in the dashboard's "unsent alerts" list.

**Admin email template**

```
Subject: [ACTION NEEDED] Patient callback request – [Reason category] – [URGENT/Normal]

Please contact this patient regarding the following:

Patient name:     [Full name]
Phone number:     [Phone]  (WhatsApp: [number, if different])
Patient type:     New patient / Existing patient (PatNum: [id] | Not verified)
Date of birth:    [DOB]
Email:            [Email, if collected]
Reason:           [Category, e.g., No suitable slot / Insurance question / Complaint]
Situation:        [1–3 sentence summary]
Preferred callback time: [if given]
Urgency:          [URGENT / Normal]
Received:         [Date & time, clinic time zone]
Case ID:          [ID]  – mark as resolved in the admin console
```

**Rules and safeguards**

- **New patients:** if Open Dental is reachable and there's no duplicate ambiguity, the patient record can be created right away (configurable). Otherwise the details stay in the callback case only, and staff create the record, so no duplicates are created automatically (see §4.5).
- **HIPAA:** this email contains PHI (name, phone, DOB, situation). Send it only through an email service covered by a **BAA** (Gmail via Google Workspace under the Workspace BAA, or a transactional email service with a BAA), with TLS enforced, to a clinic-controlled admin address. As a configurable alternative, the email can contain only the case ID and a link to the secure admin console.
- Send **one email per case**: no duplicate emails if the patient repeats the request in the same session.
- **Emergencies are separate:** for Tier 1 emergencies the AI still tells the patient to call 911 (§4.8) *and* creates an URGENT case + email.
- Every case and email is recorded in the audit log.

---

## 5. Data Model (Application DB)

Only references and operational data are stored; PHI is minimized.

| Table | Key fields |
|---|---|
| `clinics` | id, name, timezone, Open Dental connection ref, settings JSON |
| `sessions` | id, clinic_id, channel (voice/text), started_at, ended_at, status, verified_patnum (nullable) |
| `session_state` (Redis, TTL) | current state, slots (encrypted), last N turns |
| `appointment_refs` | id, clinic_id, aptnum, patnum, created_by_session, status_cache |
| `contact_prefs` | patnum, whatsapp_number (encrypted), preferred_channel |
| `consents` | patnum, channel, granted/revoked, timestamp, source, wording_version |
| `reminders` | id, aptnum, scheduled_for, status, attempts, provider_msg_id, last_error |
| `callback_requests` | id, session_id, patient_type (new/existing), patnum (nullable), contact details (encrypted), reason, urgency, summary (encrypted), status (OPEN/CONTACTED/RESOLVED), email_status, assigned_to |
| `audit_log` | id, actor (system/user/staff), action, object_type, object_ref, timestamp, result, ip (no free-text PHI) |
| `staff_users` | id, clinic_id, role, MFA status |
| `clinic_config` | hours, holidays, appointment types, emergency rules, policies, voice, versions |

**Retention:** transcripts are off by default or kept short-term (configurable; e.g., 30 days for quality review); raw audio is not stored unless explicitly authorized. Secure deletion jobs enforce retention.

---

## 6. Security & HIPAA Plan

| Area | Controls |
|---|---|
| **Vendors / BAA** | Vendor inventory; BAA status tracked per vendor (see §3.3): Google Cloud (LLM, STT, TTS, hosting, DB, logging), Google Workspace or email provider, WhatsApp BSP, and each clinic. No PHI flows to a vendor without an executed BAA. |
| **Encryption** | TLS 1.2+ everywhere; AES-256 at rest (Google default encryption + CMEK via Cloud KMS); field-level encryption for phone, DOB and summaries; KMS-managed keys. |
| **Access control** | RBAC (Admin, Front Desk, Dentist, Read-only); MFA for staff; least privilege for the Open Dental API key. |
| **Sessions** | Short-lived tokens; secure cookies; per-session patient scoping; idle timeout. |
| **PHI minimization** | Mask or tokenize identifiers in LLM prompts where possible; send only the needed fields; no PHI in URLs. |
| **Logging** | Structured logs with PHI redaction middleware; debug tools disabled in production; audit log for patient searches, patient creation/updates, appointment creation/changes/cancellations, callback cases, authentication, admin actions, API errors and security events. |
| **App security** | Input validation, prompt-injection tests, tool-misuse tests, rate limiting, bot protection on the public widget, OWASP Top 10 review. |
| **Operations** | Risk assessment, incident response plan, backup and restore drills, access reviews, security review before production. |

---

## 7. Clinic Admin Console (MVP)

- Clinic profile: name, address, phone, time zone.
- Operating hours and holidays (synced from Open Dental where possible).
- Appointment type mapping: reason → Open Dental appointment type and duration → eligible providers.
- Policies: new-patient rules, verification fields required, cancellation window.
- Emergency rules editor with approval workflow and version history.
- WhatsApp settings: templates, reminder offset (default 60 min), consent text.
- Voice settings: voice, speed, greeting.
- Callback settings: admin email address(es), email content mode (full details vs. case link only), what the AI tells the patient, which situations trigger a callback.
- Callback cases list (open / contacted / resolved, urgent first), unsent-email alerts, and the AI activity log (filtered, role-restricted).

---

## 8. Delivery Plan (Phases)

The work is delivered in the phases below, in order. Some phases can run in parallel where their dependencies allow.

### Phase 0 — Discovery & Compliance Foundation
- Confirm clinic workflows, verification policy, appointment types and emergency protocol with the pilot clinic.
- Get Open Dental API access (developer key + customer key), and set up a test database.
- Set up the Google Cloud organization and project; **accept the Google Cloud BAA**; restrict the project to HIPAA covered products (org policies, VPC Service Controls).
- Pick the WhatsApp BSP and email route, and sign their BAAs; prepare the clinic ↔ company BAA.
- Choose the GA Gemini model versions for each routing tier.
- Finalize the tech stack, architecture and data-flow diagram showing PHI boundaries.
- Start the WhatsApp Business account, number registration and template approvals (they take time).
- **Deliverables:** architecture doc, vendor/BAA matrix (§3.3), conversation flow designs, risk assessment v1.

### Phase 1 — Core Platform & Open Dental Adapter
- Infrastructure as code, CI/CD, environments (dev/staging/prod), secrets management.
- Auth, RBAC, audit logging framework, PHI-redacting logger.
- Open Dental adapter: patient search/get/create, appointments get/create/update/break, providers, appointment types, schedules, operatories; with retry, rate-limit handling and idempotency.
- Availability engine with unit tests against clinic rules.
- **Deliverables:** tested service layer, all backend tools (§4.2) implemented as endpoints.

### Phase 2 — Text Chat Receptionist
- Conversation orchestrator (state machine + slot filling), LLM integration, model router.
- Tool gateway with validation and preconditions.
- Intent handling: FAQs, scheduling, existing appointment lookup, reschedule, cancel.
- Patient identification, verification and new-patient registration with duplicate prevention.
- Emergency detector v1 and callback-request service (case creation + admin email via a BAA-covered email provider).
- Chat UI: messages, slot option cards, confirmation cards, loading and error states.
- **Deliverables:** end-to-end booking via text chat on staging with the Open Dental test DB.

### Phase 3 — Voice Pipeline & Avatar
- Google Speech-to-Text / Text-to-Speech streaming integration, VAD, endpointing, barge-in, Gemini stream cancellation.
- Build an early latency prototype (STT → Gemini Flash → TTS) to validate the targets before building the full voice UI.
- Sentence-level TTS streaming; filler phrases during tool calls.
- Read-back confirmation for names, phones, dates; spelling mode.
- Avatar states (idle / listening / thinking / speaking), mic indicator, live transcript in chat.
- Seamless voice ↔ text switching in the same session.
- Latency instrumentation per stage and tuning.
- **Deliverables:** voice-to-voice booking demo meeting latency targets in internal tests.

### Phase 4 — WhatsApp, Reminders & Admin Console
- WhatsApp BSP integration, templates, delivery webhooks, opt-out handling.
- Reminder scheduler with pre-send verification, retry and failure alerts.
- Confirmation, reschedule and cancellation notifications.
- Admin console (§7) and callback cases list.
- **Deliverables:** full lifecycle — book → confirm → remind → reschedule/cancel → notify.

### Phase 5 — Hardening, Testing & Security Review
- Full test plan (§9): voice quality, accents, noise, edge cases, load tests.
- Security testing: penetration test, prompt injection, tool misuse, PHI leakage scans.
- HIPAA readiness review: BAAs executed, policies, risk assessment final, incident response plan.
- Clinic review and sign-off on emergency scripts and policies.
- **Deliverables:** test reports, security report, compliance checklist signed off.

### Phase 6 — Pilot Launch & Iteration
- Soft launch at one pilot clinic (e.g., limited hours or new bookings flagged for staff review).
- Monitor KPIs (§11); regular review of callback cases and failed conversations.
- Tune prompts, vocabulary, routing and rules.
- **Deliverables:** pilot report, go/no-go for wider rollout.

---

## 9. Testing Strategy

| Category | Approach |
|---|---|
| **Unit** | Availability engine, matching/normalization, state machine transitions, tool validators. |
| **Integration** | Open Dental test DB; STT/TTS/LLM/WhatsApp sandbox; reminder scheduler with time simulation. |
| **Conversation evals** | Scripted test suite (100+ scenarios): new/existing patients, ambiguous matches, interruptions, topic changes, reschedule/cancel, emergencies, complaints, off-topic, prompt injection. Run automatically on every prompt/model change. |
| **Voice** | Recorded test sets across accents, background noise, phone-quality mics; measure WER on names, numbers and dates; barge-in and silence handling. |
| **Scheduling** | Double-booking races (concurrent sessions), holidays, provider restrictions, outside hours, DST transitions. |
| **Reminders** | Timing accuracy, cancelled/rescheduled appointments, failures, retries, opt-out. |
| **Security** | Pen test, auth/authorization tests, credential exposure scan, PHI-in-logs scan, LLM red-teaming. |
| **Performance** | Latency p50/p95 per stage; load test for concurrent sessions. |
| **UAT** | Clinic staff run real-world scenarios on staging before pilot. |

---

## 10. Team & Roles (suggested)

| Role | Responsibility |
|---|---|
| Tech Lead / Architect | Architecture, security design, code quality |
| Backend Engineer (×1–2) | Orchestrator, Open Dental adapter, scheduling, reminders |
| Voice/AI Engineer | Streaming pipeline, prompts, model routing, evals |
| Frontend Engineer | Voice UI, avatar, chat, admin console, accessibility |
| QA Engineer | Test automation, conversation evals, UAT |
| Compliance / Security advisor (part-time) | HIPAA review, BAAs, policies |
| Clinic SME (pilot clinic) | Workflows, emergency rules, sign-off |

---

## 11. Success Metrics (KPIs)

| Metric | Target for pilot |
|---|---|
| Booking completion rate (no callback needed) | ≥ 70% of booking conversations |
| Callback emails delivered to admin | 100% (retried until sent, otherwise flagged in dashboard) |
| Voice-to-voice latency (p50 / p95) | ≤ 1.5 s / ≤ 2.5 s |
| Double bookings caused by AI | 0 |
| Duplicate patient records created | 0 (ambiguous cases go to a callback request) |
| Reminder delivery success | ≥ 95% of consented reminders |
| Reminders sent for cancelled appointments | 0 |
| Critical-field recognition accuracy (after read-back) | ≥ 98% |
| Emergency scenarios correctly escalated (test suite) | 100% |
| PHI-in-logs incidents | 0 |
| Patient satisfaction (post-chat rating) | ≥ 4.2 / 5 |
| No-show rate change | Measurable reduction vs. baseline |

---

## 12. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| A Google service or feature is not on the HIPAA covered list (e.g., a preview model or feature) | Can't be used with PHI | Check the covered-products list before use; GA versions only; use a covered alternative |
| WhatsApp BSP or email provider won't sign a BAA | Reminder/callback emails blocked | Choose a provider that signs BAAs; use Gmail via Workspace BAA; case-link-only emails |
| Vendor lock-in to Google Cloud | Harder to switch later | Provider interfaces for LLM/STT/TTS; standard Postgres; containerized backend |
| Open Dental API limits, permissions or latency | Slow or failed scheduling | Cache config data; parallelize; filler speech; callback request + admin email when unavailable |
| STT errors on names and numbers | Wrong patient or data | Custom vocabulary, read-back, spelling mode, multi-identifier verification |
| LLM hallucinates slots or advice | Patient harm or bad bookings | Slots come only from tools; deterministic booking; output guardrails; no-diagnosis policy |
| Race conditions in booking | Double booking | Slot lock + re-check + idempotency + post-create verification |
| WhatsApp template approval delays | Late reminder feature | Start approval in Phase 0; SMS fallback option (with BAA) |
| Latency targets missed | Unnatural conversation | Stage-level instrumentation, streaming everywhere, Flash-class models, US region hosting near the clinic, pre-cached filler phrases, early latency prototype |
| Prompt injection / abuse of public widget | Data exposure | Tool scoping per verified session, rate limits, bot protection, red-team testing |
| Emergency misclassification | Patient safety | Rules-first detection, conservative thresholds, clinic-approved scripts, URGENT callback when uncertain |
| Scope creep (phone calls, insurance) | Delay | Strict MVP scope; Post-MVP roadmap (§14) |

---

## 13. Open Questions for the Clinic / Client

1. Which identifiers does the clinic require for verification (DOB + phone? address?)
2. Should AI-booked new-patient appointments be auto-confirmed or flagged for staff review?
3. Which appointment types may the AI book, and which require staff?
4. What is the approved emergency protocol and which admin email address(es) should receive callback requests (including after hours)?
5. Cancellation policy (e.g., minimum notice) and whether the AI may cancel within that window.
6. Is collecting insurance details in scope for the MVP, or should it route to staff?
7. Does the clinic already use Google Workspace (with a BAA) so Gmail can send admin emails?
8. Which WhatsApp BSP, and is SMS acceptable as a fallback?
9. Transcript retention policy (none / short-term for QA)?
10. Single location or multi-location from day one?
11. Where will the widget live (clinic website, standalone page, kiosk)?

---

## 14. Post-MVP Roadmap

| Horizon | Features |
|---|---|
| **Next** | Inbound phone calls (SIP/Twilio with BAA), insurance info collection, intake forms, pre-appointment instructions, waitlist and cancellation slot filling, analytics dashboard |
| **Later** | Outbound calls, recall/cleaning reminders, missed-appointment follow-ups, multi-language (Spanish first), multi-location and multi-provider support, AI performance monitoring |

---

## 15. Definition of Done (MVP)

- All MVP capabilities in §2 work end to end on production infrastructure.
- Every vendor that processes PHI has an executed BAA.
- Security review and penetration test are complete, with critical findings fixed.
- The clinic has approved the emergency rules, scripts and policies.
- KPIs are instrumented and the pilot runs successfully with the agreed KPIs met.
- Runbooks exist for outages (Open Dental, LLM, STT/TTS, WhatsApp) and incidents.
