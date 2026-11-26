# Messaging registration: example-dental

Record of sender registrations for Example Dental (P0-15). IDs and statuses only: **no API keys, tokens, EINs or real patient data** in this file. Credentials stay in the git-ignored `.env` now, and in the secret store later (P1-05).

| | |
|---|---|
| Policy | `messaging_policy.yaml` decision_version 1.2: WhatsApp for testing now (synthetic, team phones); at go-live the clinic chooses SMS or WhatsApp; WhatsApp with real data only after the Meta and provider BAAs |
| Templates | `docs/messaging/templates.yaml` schema 1, policy 1.2: `booking_confirmation_sms_v1`, `reminder_sms_v1`, `reschedule_notice_sms_v1`, `cancel_notice_sms_v1`, `booking_confirmation_wa_v1`, `reminder_wa_v1`, `reschedule_notice_wa_v1`, `cancel_notice_wa_v1` |
| Last updated | 2026-11-26, Riley Tech (tech lead) |

## 1. WhatsApp (Meta Cloud API, direct)
| Item | Value | Status | Date |
|---|---|---|---|
| Provider and BAA | Meta; [baa-meta-whatsapp.md](../compliance/baa-meta-whatsapp.md) | BAA **NOT ACCEPTED** (paper record) | 2026-11-26 |
| WhatsApp Business Account | The team's existing Meta app (P0-07) | In use for testing; ID kept in `.env` (`WA_WABA_ID`) | 2026-11-26 |
| Sender | Meta **test** phone number | Active; one `hello_world` message delivered in P0-07 | 2026-11-26 |
| Display name | Not set: the test number uses Meta's test name. The clinic's display name is registered with a real number at go-live | Not submitted | - |
| Templates | The 4 `*_wa_v1` templates | **DRAFT**, not submitted. Submit with `scripts/messaging/submit_whatsapp_templates.py --submit` when the user says so (dry run by default); review takes up to 24 hours (M9) | - |
| Test send | `send_test_message.py --template <id>` with example values to the team phone | Not done (needs an APPROVED template) | - |

## 2. SMS (Twilio, A2P 10DLC): drafts, not submitted
**Blockers** (DECISIONS #301, #322):
1. **No Twilio account** while SMS is switched off; it's opened before SMS is switched on, with Security or Enterprise Edition for the BAA.
2. **Clinic business details are placeholders:** legal name exactly as on the IRS CP 575 letter, EIN (kept out of this public repo), business type, address, website, contact.
3. **Clinic website pages** (SMS terms and privacy paragraph in [opt-in-and-help-texts.md](opt-in-and-help-texts.md) §3) must be live first: carrier review checks them (M2, M3).

| Step | Value (draft) | Status | Owner |
|---|---|---|---|
| ISV secondary customer profile for the clinic | Under our Twilio account (M6) | Not submitted | Tech lead, at SMS switch-on |
| Brand | Low-Volume Standard (EIN required, M1) | Not submitted | Tech lead + clinic signatory |
| Campaign | Use case `LOW_VOLUME` (fallback `ACCOUNT_NOTIFICATION`; not `MIXED`, M4) | Not submitted | Tech lead |
| Number | One local number in the clinic's area code | Not bought | Tech lead |
| Messaging Service | Number attached, default opt-out handling, status callback set by P4-01 | Not created | Tech lead / P4-01 |
| Test send, STOP → 21610 → START | Team phone, example values | Not done | Tech lead |

### 2.1 Brand (draft; Twilio field names)
```json
{
  "brand_type": "LOW_VOLUME_STANDARD",
  "business_name": "<exact legal name on CP 575>",
  "business_type": "<Corporation | Limited Liability Corporation | Partnership | ...>",
  "business_industry": "HEALTHCARE",
  "business_registration_identifier": "EIN",
  "business_registration_number": "<EIN, entered in the Twilio console only>",
  "website_url": "https://<clinic website>",
  "brand_contact_email": "<clinic contact>"
}
```
A sole proprietorship that has an EIN still registers as Low-Volume Standard, not as a Sole Proprietor brand (M2). A new EIN can fail matching; the appeal with the CP 575 or 147C letter takes about 5–7 business days (M5).

### 2.2 Campaign (draft)
```json
{
  "us_app_to_person_usecase": "LOW_VOLUME",
  "description": "Appointment notifications from <Clinic legal name> to its own patients who opted in on the clinic website: a booking confirmation, a reminder about one hour before the visit, and a notice when a visit is moved or cancelled. No marketing.",
  "message_flow": "Patients opt in on the clinic website (https://<clinic website>) when they book with the online assistant, by ticking an unchecked box that reads: 'Send me appointment confirmations, a reminder before my visit, and notices if it changes, from <Clinic name>, by text message to the number I gave. Up to 4 messages per appointment. Msg & data rates may apply. Reply STOP to opt out, HELP for help. Consent is not required to book.' Privacy policy: https://<clinic website>/privacy. SMS terms: https://<clinic website>/sms-terms.",
  "privacy_policy_url": "https://<clinic website>/privacy",
  "terms_and_conditions_url": "https://<clinic website>/sms-terms",
  "message_samples": [
    "Example Dental: Hi Maria, you're booked for Tue, Mar 10 at 9:30 AM. To change it, call (503) 555-0100. Reply STOP to opt out, HELP for help.",
    "Example Dental: Hi Maria, reminder: your visit is today at 9:30 AM. To change it, call (503) 555-0100. Reply STOP to opt out.",
    "Example Dental: Hi Maria, your visit on Tue, Mar 10 is cancelled. To book again, call (503) 555-0100. Reply STOP to opt out."
  ],
  "has_embedded_links": false,
  "has_embedded_phone": true
}
```
The samples are the rendered `*_sms_v1` examples; at submission, replace "Example Dental" with the clinic's brand name, and use `[first name]`, `[date]`, `[time]` for the variables (M2). Opt-out keywords stay with Twilio's defaults (M8), so the optional opt-in, opt-out and help fields are left out.

## 3. Open questions
| Question | Owner | Needed by |
|---|---|---|
| Does Twilio recommend `LOW_VOLUME` or `ACCOUNT_NOTIFICATION` for appointment notifications? (The docs list both; no healthcare use case, M4) | Tech lead, with Twilio | SMS switch-on |
| Brand, campaign and number fees, and who pays (the pricing page didn't render for our reader) | Morgan Lead (sponsor) | SMS switch-on |
| Who publishes the clinic's SMS terms and privacy paragraph, and on which domain? | Clinic, at onboarding | Before campaign submission |
| Is the clinic's EIN older than about 90 days, and does the legal name match the CP 575 exactly? | Clinic signatory | Before brand submission |
| Does a material wording change need a new campaign or only updated samples? | Tech lead, with Twilio | First wording change after approval |

## 4. Change log
| Date | Change |
|---|---|
| 2026-11-26 | Created (P0-15): WhatsApp test sender recorded, templates DRAFT; SMS brand and campaign drafts, not submitted |
