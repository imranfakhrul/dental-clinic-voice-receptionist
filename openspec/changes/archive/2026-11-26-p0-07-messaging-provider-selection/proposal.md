# Proposal: P0-07 Select the patient-messaging providers (issue #8)

## Why

P0-07a (DECISIONS #297–#299, `messaging_policy.yaml` v1.2) decided:
- **WhatsApp now**, for building and testing with synthetic data.
- **At go-live, each clinic chooses SMS or WhatsApp.** SMS needs a provider whose signed BAA names its SMS product. WhatsApp with real details needs signed BAAs with Meta and with any WhatsApp provider in the path.

P0-15 (sender and templates) and P4-01 (messaging adapter) can't start until a provider is chosen per channel, a test account exists, and the provider's API, webhook and opt-out facts are written down.

## What Changes

- **Comparison `docs/integrations/messaging-provider.md`:**
  - at least 3 providers per channel, scored against the 9 criteria in spec §6 with dated evidence;
  - WhatsApp: Meta Cloud API direct, Twilio, Vonage, Infobip, 360dialog;
  - SMS: Twilio, Vonage, Sinch, Infobip;
  - the choice with reasons (Proposed: **Meta Cloud API direct** for WhatsApp, the user's decision; SMS decided by the scoring);
  - "Integration facts" for P4-01 and P4-06, and sender-registration steps and lead times for P0-15.
- **BAA records, paper only** (as for Google Cloud, DECISIONS #293): `docs/compliance/baa-meta-whatsapp.md` and `docs/compliance/baa-<sms vendor>.md`, both **NOT ACCEPTED**, in the P0-05 format plus the spec §6 extra fields. Each holds the written request to send to the vendor (Meta: a BAA that explicitly covers WhatsApp message content).
- **A real WhatsApp test account** (the user creates it, guided): a Meta developer app with the free test number. One fake message to a team phone, and one delivery webhook received and its signature checked. Credentials stay in the user's password manager, never in the repo.
- **Two small test scripts** in `scripts/messaging/`: send one test template message, and a local webhook receiver that verifies Meta's signature. Standard library only; tokens and phone numbers come from environment variables and are never printed or committed.
- **Records:** DECISIONS rows, source rows in `docs/compliance/sources/README.md`, pending notifications (P0-10, P0-15, P4-01, P4-06, P4-07, P1-05), and links from the compliance README, the Phase 0 README and `docs/PROJECT_MAP.md`.
- **No product code. No PHI. No Google Cloud changes.**

## Capabilities

### New Capabilities
- `messaging-provider`: which provider carries each patient-messaging channel, the BAA gate per channel, the test-account rules (synthetic content, team phones only, credentials outside the repo), and the integration facts later code relies on (API, webhook signature, opt-out, sender registration).

### Modified Capabilities
- None. (`patient-messaging-policy` is unchanged: this task only buys what it allows.)

## Impact

- **New files:**
  - `docs/integrations/messaging-provider.md`
  - `docs/compliance/baa-meta-whatsapp.md`
  - `docs/compliance/baa-<sms vendor>.md`
  - `scripts/messaging/send_test_message.py`
  - `scripts/messaging/webhook_probe.py`
- **Edited files:**
  - `dental-ai-tasks/DECISIONS.md`
  - `docs/compliance/sources/README.md`
  - `docs/compliance/README.md`
  - `docs/phase-0-discovery-compliance/README.md`
  - `docs/PROJECT_MAP.md`
- **Outside the repo (human):** a Meta developer account and app, with the test number and token kept in the user's password manager.
- **Downstream:**
  - P0-15 registers the WhatsApp sender and templates on the chosen route.
  - P4-01 builds against the integration facts.
  - P0-10 imports the BAA records.
  - P1-05 creates the production secrets from the listed names.
