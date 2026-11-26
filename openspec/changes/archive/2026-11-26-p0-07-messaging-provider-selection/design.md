# Design: P0-07 Select the patient-messaging providers

## Context

- See proposal.md, Why. The policy (`docs/compliance/messaging_policy.yaml` v1.2) sets:
  - testing channel `whatsapp`, synthetic data only, team test numbers only;
  - production `per_clinic`, options `[sms, whatsapp]`;
  - WhatsApp `allowed_with_phi: false` until BAAs with Meta and any WhatsApp provider are signed, with `fallback_until_gate: sms`.
- **P0-07a already checked the published BAA positions** (`docs/compliance/sources/README.md`, P1–P7, 2026-11-26):
  - Twilio covers Programmable SMS (Security or Enterprise Edition), not WhatsApp.
  - Vonage covers Messages API SMS/MMS for US traffic.
  - Sinch and Infobip publish no product list.
  - Bird disclaims; 360dialog says nothing.
  - Meta says it isn't a business associate.
- **BAAs are paper only** (DECISIONS #293, as for Google Cloud): records say NOT ACCEPTED, and only synthetic data is used.
- **User decisions for this task (2026-11-26):**
  - WhatsApp testing goes through the **Meta WhatsApp Cloud API directly**.
  - A **real test account** is opened and one fake message is sent to a team phone.
- **People** (same as earlier tasks): Riley Tech (tech lead), Morgan Lead (sponsor), Sam Comply (compliance advisor). The user does the human steps (accounts, phone).
- **Google Cloud has no billing**, so Cloud Run can't host a webhook endpoint yet.

## Goals / Non-Goals

**Goals:**
- A scored, sourced comparison per channel and a recorded choice.
- Paper BAA records that later tasks (P0-10, P0-11) can read as the PHI gate.
- Proven integration facts for WhatsApp: one test message sent and one signed webhook verified.
- Written sender-registration steps for P0-15.

**Non-Goals:**
- Signing any BAA for real, or sending the written BAA requests (drafted only; sending is a human step later).
- Opening an SMS test account: SMS stays switched off (`enabled: false`). It's done before SMS is switched on.
- Registering the production WhatsApp sender, business verification or templates (P0-15).
- The product adapter, webhooks endpoint, retries and opt-out code (P4-01, P4-06, P4-07).
- Production secrets in Secret Manager (P1-05).

## Decisions

1. **WhatsApp route: Meta Cloud API direct** (user decision).
   - **Why:** no company between us and Meta, so production WhatsApp needs only Meta's BAA, not two. The developer test number is free and needs no business verification.
   - **Alternatives:** Twilio WhatsApp (one SDK for both channels, but Twilio's BAA list leaves out WhatsApp, so two BAAs would be needed); 360dialog, Infobip, Vonage (scored in the comparison).
2. **SMS provider: chosen by the scoring.** Proposed: Twilio, the only candidate with a published product-level coverage list naming SMS. Vonage is the runner-up. Sinch and Infobip get "partial" on criterion 1 until they put their product list in writing. The edition price (Twilio Security Edition) is recorded for the sponsor. Verify: price and list at apply time.
3. **Criterion 1 is scored twice for WhatsApp:** "testing (no PHI)" and "production (PHI)". Today every WhatsApp provider fails the production column, which matches the policy's `phi_gate`. This isn't the spec §8 "no provider meets all Musts" stop, because P0-07a already chose that gate and the SMS fallback.
4. **Evidence follows P0-07a:** each new source gets a row in `docs/compliance/sources/README.md` (URL, date, quote, SHA-256 where `curl` works; "n/a" for Meta pages read through the web-fetch tool). No third-party pages are committed.
5. **BAA records are paper:** `baa-meta-whatsapp.md` and `baa-<sms vendor>.md`, status NOT ACCEPTED, P0-05 fields plus the spec §6 extras. Each has a short written request to send later: Meta's must ask for explicit coverage of WhatsApp Business Platform message content.
6. **Test account (human, guided).** *Outcome: the senior supplied the credentials of the team's existing Meta app with a test number, so no new account was created.* Planned steps:
   - the user creates a Meta developer account and a Business-type app with the WhatsApp product;
   - adds their own phone as a test recipient;
   - copies the temporary access token, phone number ID and app secret into their password manager.
   - Verify: test-number limits (recipient count, temporary token lifetime, `hello_world` template) against Meta's current docs.
7. **Test scripts in `scripts/messaging/`** (standard library only, Python 3.12):
   - `send_test_message.py` sends the `hello_world` template (fake content) using `WA_TOKEN`, `WA_PHONE_NUMBER_ID` and `WA_TEST_TO` from the environment. It prints only the HTTP status and the message ID, never the number or token.
   - `webhook_probe.py` is a local HTTP receiver. It answers Meta's verification request (`hub.challenge` with `WA_VERIFY_TOKEN`) and checks `X-Hub-Signature-256` (HMAC-SHA256 with `WA_APP_SECRET`). It prints only pass/fail, the event type and the status value. Verify: header name and algorithm against Meta's webhook docs.
   - They're test tools for P0-07 only. P4-01 and P4-06 build the real ones.
8. **Public URL for the webhook test (Proposed; the live webhook test was deferred to P4-06 by the user):** a temporary Cloudflare quick tunnel (`cloudflared`, no account) to the local receiver, closed right after the test.
   - **Why:** Cloud Run needs billing.
   - **No PHI passes**, only a team phone number and the template's fake content. Webhook payloads aren't saved.
   - **Alternative:** a request-inspection site (e.g. webhook.site), rejected because it stores payloads, including the team phone number.
9. **Credentials:** never in the repo, issues or logs. Env vars set per shell session. Secret names for P1-05 are listed in the integration facts (names only).

## Risks / Trade-offs

- **Meta may never sign a BAA** → WhatsApp clinics stay on SMS (policy fallback). It's recorded, not hidden.
- **Test-number limits** (temporary token, few recipients) → enough for P0-07 and P0-15 drafts. P4-01 may need a system-user token later (Verify).
- **The tunnel is a third-party service** → no PHI passes through it, it lives for minutes, and it's recorded in the vendor notes as test-only. It's never used with real data.
- **Prices and coverage lists change** → dated evidence; re-checked before go-live (P5-14).
- **The user's personal phone number** is in the Meta app → it stays in the password manager and Meta's dashboard; it never goes into the repo.

## Open Questions

- Budget ceiling for Twilio Security Edition (sponsor, Morgan Lead): recorded at apply time; it doesn't block testing, since SMS is off.
- Who signs the BAAs: the same open question as P0-05; the records stay NOT ACCEPTED.
