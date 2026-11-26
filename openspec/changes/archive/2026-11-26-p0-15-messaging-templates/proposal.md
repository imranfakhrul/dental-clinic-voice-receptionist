# Proposal: P0-15 Patient-messaging sender and message templates (issue #16)

## Why

P4 must send booking confirmations, reminders and reschedule/cancel notices on day one, and the templates are the main place PHI can leak in messaging: a lock-screen message that says "your root canal" discloses PHI. Writing the templates once, as data checked by code against `messaging_policy.yaml`, means P4 code can't add a forbidden field, and carriers or Meta review exactly the messages we will send. US carriers also filter unregistered SMS traffic, and 10DLC registration takes days to weeks, so the SMS registration package must be ready well before go-live.

The situation on 2026-11-26 differs from the spec, which assumed SMS first:
- **Policy v1.2** (DECISIONS #299): WhatsApp is the **testing** channel now (synthetic data, team phones); at go-live each clinic chooses **SMS or WhatsApp**, and WhatsApp may carry real details only after the Meta and provider BAAs are signed (until then that clinic uses SMS). `opt_out_text_required: true` means **every** message carries opt-out text.
- **Providers** (DECISIONS #300, #301): WhatsApp = Meta Cloud API direct, using the team's existing Meta app and test number; SMS = Twilio, but **no Twilio account** exists while SMS is off.
- **Clinic:** Example Dental (`example-dental`); its legal name, EIN and website are placeholders, so a 10DLC brand can't be submitted.

**User decision (2026-11-26): drafts now, live steps later.** Everything that can be written and checked offline is done now. Submitting WhatsApp templates to Meta and the synthetic test send are prepared as scripts, but run only when the user puts the Meta credentials in the git-ignored `.env` and says so. SMS brand and campaign registration stays a prepared draft until a Twilio account and the clinic's real business details exist.

## What Changes

- **`docs/messaging/templates.yaml` + `templates.schema.json`:**
  - 4 SMS templates (confirmation, reminder, reschedule, cancel), one GSM-7 segment where possible;
  - 4 WhatsApp utility templates with the same fields (testing now; production only after the WhatsApp gate), with `provider_template_name`, `language`, `provider_status`;
  - a `system_replies` block (STOP, START, HELP, auto-reply), PHI-free;
  - date and time formats for P4-03.
- **`scripts/messaging/check_templates.py`** with rules T1–T10, adapted to policy v1.2 (channel must be integrated; every template carries opt-out text; a full set of four types per channel), plus `test_check_templates.py` with fixtures.
- **`docs/messaging/opt-in-and-help-texts.md`:** consent checkbox text with the policy's risk notice placeholder (wording owner P4-02, approval by the compliance advisor), HELP and STOP texts, and the clinic website texts (SMS terms page, privacy paragraph).
- **`docs/messaging/registration-example-dental.md`:** registration record. WhatsApp: test number in use, templates `DRAFT`. SMS: 10DLC brand and campaign drafts (Twilio field names, facts re-checked on Twilio's pages), status "not submitted", with the blockers.
- **Live-step scripts (prepared, not run):**
  - `scripts/messaging/submit_whatsapp_templates.py`: creates the WhatsApp templates on the team's WhatsApp Business Account; `--dry-run` by default; prints names and statuses only;
  - test-send mode for an approved template in the existing `send_test_message.py`, example values only, to `WA_TEST_TO` only.
- **Records:** sources (Twilio and Meta pages checked on the day), DECISIONS rows, `.env.example` keys (no values), `docs/messaging/README.md`, hand-offs for P4-01, P4-02, P4-03, P4-04, P0-10 and P0-14, READMEs and `docs/PROJECT_MAP.md`.

No real PHI, no live call to Meta or Twilio during apply.

## Capabilities

### New Capabilities
- `patient-message-templates`: the approved patient message templates per type and channel, the content rules enforced by the validator against the messaging policy, the opt-in/HELP/STOP texts, and the sender registration record and live-step guards.

### Modified Capabilities
- (none)

## Impact

- **New:** `docs/messaging/` (README, templates, schema, texts, registration record), `scripts/messaging/check_templates.py`, its tests and fixtures, `scripts/messaging/submit_whatsapp_templates.py`.
- **Updated:** `scripts/messaging/send_test_message.py` (template mode), `.env.example`, `docs/compliance/sources/README.md`, `dental-ai-tasks/DECISIONS.md`, `docs/compliance/README.md`, `docs/PROJECT_MAP.md`, `docs/phase-0-discovery-compliance/README.md`.
- **Downstream:** P4-01 loads and validates the templates at startup; P4-02 uses the consent text; P4-03 the formats; P4-04 the reminder; flows F10a/F10b in `phi-flows.md` stay as they are.
