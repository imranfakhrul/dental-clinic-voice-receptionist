---
id: P4-13
title: WhatsApp, voice and callback settings screens
milestone: P4
epic: E4.2
size: M
labels: area:admin, area:frontend, type:feature
depends_on: P4-09, P1-19, P4-01, P4-02, P4-04, P2-22, P0-08, P0-15, P3-03
status: approved
---

# P4-13: WhatsApp, voice and callback settings screens

> Split (DECISIONS #266). After consolidation (#56), this issue had also absorbed P4-14 (callback cases) and P4-15 (AI activity log), which made it larger than L. Those two, plus the failed-messages page, moved to the new task **P4-13a** "Callback cases, AI activity log and failed messages screens". This task keeps only the settings screens.

## 1. Summary
Add three settings pages to the admin console (P4-09 shell). They let the clinic tune patient messages, the AI's voice and callback emails without a developer.

1. **Messages and reminders** (`/admin/settings/messages`):
   - editable:
     - confirmation message on/off;
     - reminders on/off;
     - reminder offset (30–240 minutes, with the note "Applies to appointments booked from now on.");
   - read-only:
     - channel (WhatsApp);
     - content mode;
     - each WhatsApp template's text and Meta approval status;
     - the consent texts.
2. **Voice and greeting** (`/admin/settings/voice`):
   - voice from the allow-list, with **Play sample**;
   - speaking rate 0.8–1.2;
   - pronunciation list;
   - assistant name;
   - greeting text (≤ 200 characters, placeholders `{assistant_name}` and `{clinic_name}` only).
3. **Callbacks and email** (`/admin/settings/callbacks`):
   - editable:
     - clinic email addresses for callback cases (business hours and after hours);
     - the three callback promise texts;
     - **Send test email**.
   - read-only: the email mode (`link_only` / `full_details`).

Every save goes through the P4-09 **Save and publish** step, so the server validates first, and each change becomes a new audited config version. Seed acceptance criterion: **settings are validated before save**. The browser validates first for quick feedback, and the P1-19 server rules are the final check.

## 2. Why this matters
These settings decide what patients hear and read, and whether the clinic ever learns about a callback.
- **Wrong admin email:** callback cases go nowhere. Patients who were promised a call never get one (risk R23 in P0-11). *Send test email* lets the clinic prove the address works before relying on it.
- **Wrong offset or reminders off:** patients miss appointments.
- **Hard-to-understand voice or a wrongly pronounced doctor's name:** the clinic looks unprofessional on every call.

Some things must **not** be editable here, because a clinic edit would break a legal or vendor rule:
- **WhatsApp template texts:** Meta must approve each template before it can be sent (P0-15).
- **Consent texts:** reviewed with the compliance advisor (P4-02).
- **Content mode and email mode:** PHI decisions that need the compliance advisor's written approval (P0-07a, DECISIONS #41).

The console shows these so the clinic knows exactly what patients receive, but the clinic can't change them here.

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P4, WhatsApp, Reminders & Admin Console**.
- **Config service (P1-19):**
  - `PATCH /v1/admin/config {base_version, changes, change_note}` creates a version and `POST /v1/admin/config/activate` makes it live;
  - new sessions use the active version, and running sessions keep their pinned one;
  - `GET /v1/admin/config` returns the active document.
  - The P1-19 edit matrix marks `reminders`, `voice`, `callback` and `conversation` as console-editable, except the fields this task locks (§6.5).
- **Config keys used here (P1-19 YAML):**
  ```yaml
  reminders:   {enabled: false, channel: whatsapp, confirmation_enabled: false, offset_minutes: 60}
  voice:       {language: en-US, tts_voice: null, speaking_rate: 1.0, pronunciations: {}}
  conversation: {assistant_name: null, not_understood_limit: 2, recent_turns: 6, max_turn_chars: 1000}
  callback:
    admin_emails: ["frontdesk@example-dental.test"]
    after_hours_emails: []          # empty = same as admin_emails
    email_mode: link_only           # link_only | full_details
    full_details_approval: null
    promise_business: "Our team will call you back within one business day."
    promise_urgent: "Our team will call you back today."
    promise_urgent_after_hours: "Our team will call you as soon as the office opens."
  ```
- **Existing rules (server side, P1-19 and the owning tasks):**
  - `reminders.enabled: true` requires the channel to be approved for this clinic (P0-07a);
  - `offset_minutes` 30–240, applies only to new bookings (P4-04, DECISIONS #260);
  - `voice.tts_voice` is null or in `TTS_ALLOWED_VOICES`, and `speaking_rate` 0.8–1.2 (P3-03);
  - `pronunciations`: max 50 entries, letters, spaces, hyphens and apostrophes only (P3-03, DECISIONS #232);
  - callback emails: no consumer domains, the domain passed the readiness check, and `full_details` needs `full_details_approval` (P0-08).
- **Templates and texts (files, not config):**
  - `templates.yaml` from P0-15 holds the WhatsApp templates (ID, language, body with variables, Meta approval status);
  - `consent_texts.yaml` from P4-02 holds `wa-optin-nudge-v1`, `wa-optin-minimal-v1` and `staff-optin-v1`;
  - `messaging_policy.yaml` from P0-07a / P4-01 holds the content mode `phi_free_nudge` (default) or `minimal_phi`;
  - the greeting template `greeting` is in P2-04's `reply/templates.yaml`: "Hi, this is {assistant_name} at {clinic_name}. How can I help you today?"
- **Text-to-Speech (P3-03):** `TextToSpeech.speak(reply_id, sentences, voice: VoiceChoice)` returns audio chunks (LINEAR16). `VoiceChoice(name, language_code, speaking_rate, sample_rate_hz)`. The allow-list is the env setting `TTS_ALLOWED_VOICES`.
- **Admin email (P2-22 / P2-23):** `EmailTransport.send(msg) -> provider_message_id`, sent as `ADMIN_EMAIL_SENDER` through the Workspace BAA route (P0-08).
- **Console shell (P4-09):** `NAV`, `<Can>`, `useConfig()`, `SaveAndPublishDialog`, field error mapping, MSW mocks.

New glossary terms: greeting override, test email (callback), voice sample.

## 4. Scope
**In scope**
- Three console pages and their `NAV` entries.
- Backend:
  - `GET /v1/admin/messaging/overview` (read-only templates, consent texts, content mode, channel approval);
  - `GET /v1/admin/voice/options` (allowed voices with labels);
  - `POST /v1/admin/voice/sample`;
  - `POST /v1/admin/callback/test-email`.
- New config key `conversation.greeting_override`, with its validation (P1-19 and P2-04 additive).
- P1-19 additive: lock `callback.email_mode`, `callback.full_details_approval` and `reminders.channel` for the console; length rules for the promise texts.
- Unit, backend and E2E tests.

**Out of scope** (and which task covers it)
- Callback cases list, AI activity log and failed messages → P4-13a
- Editing WhatsApp template texts → the P0-15 process (new template submitted to Meta)
- Editing consent texts or content mode → compliance advisor + file change (P4-02, P0-07a)
- Turning on `full_details` email → support, with the advisor's written approval recorded in `full_details_approval` (P0-08)
- Widget appearance (`widget.*`) → stays file-only in the MVP (Proposed); revisit in P6
- Conversation tuning (`not_understood_limit`, `recent_turns`, `max_turn_chars`) → file-only (developer-facing)

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P4-09 Shell (approved spec) | Layout, `NAV`, `<Can>`, `useConfig`, `SaveAndPublishDialog` | — |
| P1-19 Config (approved spec) | Config API, rules, edit matrix | MSW handlers with `seed/example-dental` |
| P4-01 / P4-02 / P0-15 (approved specs) | `messaging_policy.yaml`, `consent_texts.yaml`, `templates.yaml` | Read the example files committed by those tasks |
| P4-04 (approved spec) | Offset rule and note | — |
| P3-03 TTS (approved spec) | `TextToSpeech`, `TTS_ALLOWED_VOICES` | `FakeTextToSpeech` that returns a 1-second tone |
| P2-22 / P2-23 Email (approved specs) | `EmailTransport`, sender rules | `FakeEmailTransport` (records messages) |

## 6. Interface contract

### 6.1 Pages and permissions
| Route | View | Edit / actions |
|---|---|---|
| `/admin/settings/messages` | `config:read` | `config:write` |
| `/admin/settings/voice` | `config:read` | `config:write` (Play sample too) |
| `/admin/settings/callbacks` | `config:read` | `config:write` (Send test email too) |

`NAV` additions in the group "Clinic settings", `ownerTask: "P4-13"`: "Messages and reminders", "Voice and greeting", "Callbacks and email".

### 6.2 Messages and reminders page
| Field | Control | Rule / text |
|---|---|---|
| `reminders.confirmation_enabled` | toggle "Send a WhatsApp confirmation after booking" | Needs channel approval (as `enabled`) |
| `reminders.enabled` | toggle "Send a reminder before each appointment" | Disabled with the reason when `channel_approved` is false: "WhatsApp messages aren't approved for your clinic yet." |
| `reminders.offset_minutes` | number + "minutes before" (step 5) | 30–240; note **"Applies to appointments booked from now on."** |
| `reminders.channel` | read-only "WhatsApp" | locked |
| Content mode | read-only badge: "Reminder without details (patient opens a secure link)" for `phi_free_nudge`, "Reminder with date and time" for `minimal_phi` | from `messaging_policy.yaml` |
| Templates | read-only table: purpose, text with `{{1}}` variables shown as named chips (e.g. `[clinic name]`), Meta status (`APPROVED` / `PENDING` / `REJECTED`) | from `templates.yaml`; a `REJECTED` or `PENDING` template used by an enabled message shows a warning |
| Consent texts | read-only, the exact wording the patient sees in chat and hears in voice | from `consent_texts.yaml` |

Footer: "To change message wording, contact the project team. WhatsApp must approve every new text."

### 6.3 Voice and greeting page
| Field | Control | Rule |
|---|---|---|
| `voice.tts_voice` | radio list from `/voice/options` (label like "Warm female voice", "Calm male voice"), with ▶ per voice | null = default (shown as "Default") |
| `voice.speaking_rate` | slider 0.8–1.2, step 0.05, labels "Slower" / "Normal" / "Faster" | — |
| `voice.pronunciations` | table: Word → "Say it like" (e.g. `Nguyen` → `Win`), ▶ per row | ≤ 50 rows; word ≤ 40, respelling ≤ 60; letters, spaces, `-`, `'` |
| `conversation.assistant_name` | text | 1–30 chars, letters, spaces, `-`, `'`; null = "the virtual receptionist" |
| `conversation.greeting_override` | textarea with counter + "Reset to default" | ≤ 200 chars; placeholders only `{assistant_name}`, `{clinic_name}`; no other `{`/`}`; must not contain URLs, phone numbers or emails; null = P2-04 default |

**Play sample** speaks the rendered greeting (or the pronunciation row's sentence "This is {word}.") with the **unsaved** voice, rate and pronunciations, so the admin hears the change before publishing.

The greeting is used for both chat and voice. A preview line shows the rendered text, e.g. "Hi, this is Mia at Bright Smile Dental. How can I help you today?"

### 6.4 Callbacks and email page
| Field | Control | Rule |
|---|---|---|
| `callback.admin_emails` | email chips, each with **Send test email** | 1–5 addresses; P0-08 rules (no consumer domains, domain ready) |
| `callback.after_hours_emails` | email chips + "Same as above" checkbox (empty list) | 0–5; same rules |
| `callback.promise_business` | textarea + counter | 10–200 chars; no placeholders; must not promise a specific time ("within 1 hour"): soft warning only |
| `callback.promise_urgent` | textarea | 10–200 |
| `callback.promise_urgent_after_hours` | textarea | 10–200 |
| `callback.email_mode` | read-only: "Emails contain only a secure link (no patient details)" or "Emails contain patient details (approved: <reference>)" | locked |

**Send test email** sends one email to that address: subject "[TEST] AI receptionist callback email", body "This is a test from <clinic name>'s AI receptionist console. Real callback emails will arrive like this one." It contains **no case and no PHI**.
- The result is shown inline: "Sent at 10:42. Check the inbox (and spam folder)." or "Couldn't send: the address was rejected."
- A changed address can be tested **before** publishing, because the endpoint validates the address itself.

### 6.5 Backend endpoints
```
GET  /v1/admin/messaging/overview                         Permission config:read
200 {"channel": "whatsapp", "channel_approved": true, "content_mode": "phi_free_nudge",
     "templates": [{"id": "appt_reminder_nudge_v1", "purpose": "reminder", "language": "en_US",
                    "body": "Hi from {{1}}. You have an upcoming appointment. Details: {{2}}",
                    "variables": ["clinic_name", "secure_link"], "meta_status": "APPROVED", "in_use": true}],
     "consent_texts": [{"id": "wa-optin-nudge-v1", "chat": "...", "voice": "..."}]}

GET  /v1/admin/voice/options                              Permission config:read
200 {"default": "en-US-Chirp3-HD-Aoede",
     "voices": [{"name": "en-US-Chirp3-HD-Aoede", "label": "Warm female voice", "supports_rate": true}]}
     (labels from env VOICE_LABELS_JSON; Verify: which allowed voices support speaking_rate, per P3-03)

POST /v1/admin/voice/sample                               Permission config:write; rate limit 10/min per staff user
{"tts_voice": "en-US-Chirp3-HD-Aoede", "speaking_rate": 1.05,
 "pronunciations": {"Nguyen": "Win"}, "text_kind": "greeting" | "pronunciation",
 "greeting_override": "...", "assistant_name": "Mia", "word": "Nguyen"}
200 audio/wav (≤ 10 s); 422 invalid values (same rules as config); 429; 503 tts_unavailable
     The text is always built on the server from the greeting template or "This is {word}."; free text is never sent.

POST /v1/admin/callback/test-email                        Permission config:write; rate limit 5/hour per clinic
{"address": "frontdesk@brightsmile.example"}
200 {"status": "SENT", "sent_at": "...", "provider_message_id": "..."}
422 {"error": "email_rule", "rule": "consumer_domain" | "domain_not_ready" | "invalid"}
502 {"status": "FAILED", "error_code": "recipient_rejected" | "transport_error"}
```
- Audit: new P1-07 action `callback.test_email` (no object; details `reason_code` = result, `error_code`). Voice samples are not audited (no data).
- The test email goes through the P2-23 `EmailTransport` and the same sender, so it proves the real path (TLS rule, DKIM).

### 6.6 Config additions (P1-19, additive)
```yaml
conversation:
  greeting_override: null      # added by P4-13 (DECISIONS #266); ≤ 200 chars; placeholders {assistant_name}, {clinic_name} only
```
```python
LOCKED_FOR_CONSOLE += ["reminders.channel", "callback.email_mode", "callback.full_details_approval"]
# Rules (reject): greeting_override as in §6.3; promise_* 10–200 chars, no "{" or "}";
# admin_emails 1–5, after_hours_emails 0–5.
```
P2-04: the `greeting` template uses `conversation.greeting_override` when set, rendered with the same placeholder filler. The rest of P2-04 is unchanged.

## 7. Implementation guide
1. **Read** P4-09 (shell), P1-19 (rules, matrix), P4-04 (offset note), P0-15 / P4-02 / P4-01 (files), P3-03 (TTS), P2-22 / P2-23 (email) and P0-08 (email rules).
2. **P1-19 / P2-04 additive:** `greeting_override` key and rule; locks; promise and email-count rules. Tests.
3. **Backend endpoints** (§6.5): overview reads the three files at startup (cached; they change only with a deploy); voice options from env; sample uses `TextToSpeech` with a 3 s deadline and returns WAV; test email through `EmailTransport`.
4. **Pages:** Messages and reminders → Voice and greeting → Callbacks and email, with MSW mocks and `NAV` entries.
5. **Client validation** mirrors the server rules (shared constants in `frontend/lib/config-rules.ts`, generated from the backend JSON schema at build time so the two never drift; Proposed).
6. **Docs:** add the three pages to `docs/admin/settings.md` (from P4-11).

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| Admin turns reminders on before the channel is approved | Toggle disabled with the reason; a crafted PATCH is rejected by the P1-19 rule. |
| Offset changed from 60 to 120 | Saved; note shown; existing reminders keep 60 (P4-04). |
| Template used by an enabled message is `REJECTED` / `PENDING` at Meta | Warning on the page: "Reminders can't be sent until WhatsApp approves this message." The P4-01 gate already skips the send. |
| Greeting with `{patient_name}` or a URL | Field error; server 422. |
| Play sample while TTS is down | "Couldn't play the sample right now." Saving is still allowed. |
| Voice that ignores speaking rate (`supports_rate: false`) | Slider disabled with "This voice uses a fixed speed." |
| Test email to `gmail.com` | 422 `consumer_domain` before sending. |
| Test email rejected by the clinic's server | "Couldn't send: the address was rejected." Audit result FAILURE. Saving is still possible (warning in the publish dialog: "This address failed its last test."). |
| Admin removes every admin email | Blocked: at least one is required. |
| `full_details` is active | Page shows "Emails contain patient details (approved: <reference>)". It can't be changed here. |
| Two admins edit at once | 409 from the P4-09 publish step; the page reloads the latest version. |
| FRONT_DESK opens the pages | Read-only (`config:read`); no Play sample, no Send test email. |

## 9. Security, HIPAA and PHI
- **No PHI** is handled by this task. All values are clinic settings. The test email contains no case data. Voice samples use only the greeting or a pronunciation word.
- Greeting and promise texts are spoken or shown to patients exactly as written, so the rules block placeholders other than the allowed ones, and also URLs, phone numbers and emails. This stops a typo or an injected link from reaching patients.
- **Locked fields:** channel, content mode, email mode and approval reference can't be changed in the console (403 `config_section_locked`), so a PHI decision can't be changed without the advisor.
- **Rate limits:** test email 5/hour per clinic (stops the endpoint being used to spam an address); voice sample 10/min per user (TTS cost).
- **Audit:** config versions and activations (P1-19), `callback.test_email`.
- Logs: the test-email address is a clinic address, but log only its domain, to keep the log rule simple.

## 10. Testing
**Unit** (frontend, Vitest):
- **F1:** offset range and note.
- **F2:** greeting validation (allowed and forbidden placeholders, URL, length).
- **F3:** pronunciation row rules.
- **F4:** email chips (consumer domain, max 5, at least one).
- **F5:** read-only rendering of templates with variables as chips, and the rejected-template warning.
- **F6:** FRONT_DESK sees no action buttons.

**Backend** (pytest):

| # | Case | Expected |
|---|---|---|
| B1 | PATCH `reminders.offset_minutes` = 25 | 422 rule error |
| B2 | PATCH `callback.email_mode` = full_details | 403 `config_section_locked` |
| B3 | PATCH `conversation.greeting_override` with `{first_name}` | 422 |
| B4 | Greeting override set → P2-04 greeting renders it | "Hi, this is Mia at Bright Smile Dental…" |
| B5 | Voice sample with an allowed voice (fake TTS) | 200 `audio/wav` |
| B6 | Voice sample with a voice not in the allow-list | 422 |
| B7 | Test email to a ready domain (fake transport) | 200 SENT; one message, no PHI; audit SUCCESS |
| B8 | Test email to `gmail.com` | 422 `consumer_domain`; nothing sent |
| B9 | Test email 6th call in an hour | 429 |
| B10 | Messaging overview | Template list from the example files; `channel_approved` from config |
| B11 | FRONT_DESK calls sample or test email | 403 |

**E2E** (Playwright):
- **E1:** ADMIN changes the offset → publish → history shows the version, and the page shows the note.
- **E2:** ADMIN adds an email → Send test email → "Sent" → publish.
- **E3:** ADMIN edits the greeting → Play sample (mocked audio) → publish.

```bash
cd backend && pytest tests/unit/admin/test_settings_endpoints.py tests/unit/config -q
cd frontend && pnpm test && pnpm test:e2e -- settings-messages settings-voice settings-callbacks
```

## 11. Acceptance criteria
- [ ] Settings are validated in the browser and by the server before they are saved; invalid values are rejected with field messages (B1, B3, F1–F4)
- [ ] Confirmation on/off, reminders on/off and the offset (30–240, "applies from now on" note) are editable (E1)
- [ ] Template texts, Meta status, consent texts, channel and content mode are shown read-only (B10, F5)
- [ ] Voice, speaking rate, pronunciations, assistant name and greeting are editable, and Play sample plays the unsaved choice (B5, E3)
- [ ] Callback emails and promise texts are editable; Send test email works and contains no PHI (B7, E2)
- [ ] Email mode, content mode and channel can't be changed through the console (B2)
- [ ] Every change is a new audited config version; FRONT_DESK and READ_ONLY can't edit (B11, F6)

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI
- [ ] PR reviewed
- [ ] No PHI in logs
- [ ] Docs / README updated (`docs/admin/settings.md`)
- [ ] Additive edits merged: P1-19 (greeting key, locks, rules), P2-04 (greeting override), P1-07 (`callback.test_email`)

## 13. Hand-off
| Consumer | What it can rely on |
|---|---|
| P2-04 / P3 voice | `conversation.greeting_override`, `assistant_name`, voice settings via P1-19 |
| P2-22 / P2-23 | Admin emails proven by test email before the pilot |
| P4-17 E2E | Reminders and confirmation toggles for the end-to-end test |
| P6-01 Go-live checklist | "Test email sent and received for every admin address" as a checklist item |

## 14. Open questions
| Question | Owner | Needed by |
|---|---|---|
| Which allowed voices support `speaking_rate`? | Developer (Verify, with P3-03) | Step 3 |
| Should clinics edit widget appearance (`widget.*`) in the console? Proposed: not in the MVP; file-only until P6 feedback | Product owner | P6 review |

## 15. References
- Plan §7 (admin console), §4.7 (messages), §4.9 (callbacks)
- DECISIONS #41, #206, #232, #252, #253, #260, #262, #266
- Related tasks: P0-07a, P0-08, P0-15, P1-07, P1-19, P2-04, P2-22, P2-23, P3-03, P4-01, P4-02, P4-04, P4-09, P4-13a, P4-17, P6-01
