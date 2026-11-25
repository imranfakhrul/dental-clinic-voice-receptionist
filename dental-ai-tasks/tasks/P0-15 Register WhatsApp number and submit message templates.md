---
id: P0-15
title: Register patient-messaging sender and prepare message templates
milestone: P0
epic: E0.3
size: M
labels: area:messaging, area:compliance, type:chore
depends_on: P0-07, P0-07a, P0-01
status: approved
---

# P0-15: Register patient-messaging sender and prepare message templates

## 1. Summary
Get the pilot clinic's patient-messaging sender approved by carriers, and write the message templates **as code**, so that P4 can send confirmations, reminders and reschedule/cancel notices on day one.

The channel follows the P0-07a decision:
- **SMS path (default, DECISIONS #37).** Register the clinic as an A2P 10DLC **brand**, as an ISV customer under our provider account. Register one **campaign**, buy one local number, and configure opt-out handling.
- **WhatsApp path (only if P0-07a allows it).** Register the WhatsApp Business number and display name, and submit utility templates. Until P0-07a decides, only PHI-free drafts may be submitted (DECISIONS #38).

The deliverables:
- `docs/messaging/templates.yaml` with a JSON Schema;
- `scripts/messaging/check_templates.py`, which validates the templates against `messaging_policy.yaml`;
- opt-in, HELP and STOP texts;
- the clinic's website texts (privacy policy and SMS terms sections);
- a registration record.

This task was retitled from "Register WhatsApp number and submit message templates". The ID is kept because P4-01 and P4-03 depend on it; see DECISIONS #78.

Done means:
- the brand and campaign are approved (or WhatsApp templates approved, if that path is chosen);
- the number is attached to a messaging service;
- `check_templates.py` passes in CI;
- a test message reached a team phone with synthetic data;
- P4-01, P4-02, P4-03 and P4-04 are notified.

## 2. Why this matters
US carriers filter or surcharge SMS from unregistered business numbers. Twilio states that unregistered 10DLC traffic gets "additional carrier fees" and more filtering. Registration has review times of days to weeks:
- brand manual review "seven business days or more";
- campaign review "up to 5 business days", longer on rejection.

If this starts in P4, reminders can't go live with the pilot.

The templates are also the main PHI-leak surface in messaging: a message that says "your root canal" on a lock screen discloses PHI. Writing the templates once, as data checked against `messaging_policy.yaml`, means P4 code can't add a forbidden field, and the carrier sees exactly the messages we will send. Carriers compare sample messages with real traffic.

Plan references: §4.7 (messaging and reminders), §3.3 (BAA rules), §2 #9–10 (confirmations and reminders), §6 (PHI minimization).

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P0, Discovery & Compliance Foundation**.
- **Channel decision:** P0-07a found that Meta states WhatsApp Business Platform "is not HIPAA compliant" and that Meta is not a business associate (DECISIONS #35). So the proposed default is SMS through a provider whose BAA covers SMS (DECISIONS #37). The decision and its content rules are in `docs/compliance/messaging_policy.yaml`:
  - `channels.*.allowed`;
  - `message_types.*.fields` (default: `first_name`, `clinic_name`, `appointment_date`, `appointment_time`, `clinic_phone`);
  - `never_allowed_fields` (last name, DOB, reason, procedure, symptoms, provider name, insurance, PatNum, AptNum).
- **Provider:** chosen and BAA-signed in P0-07. Examples below use **Twilio** field names, because Twilio's HIPAA-eligible list includes SMS (P0-07a). **Verify** the field names if P0-07 picks another provider.
- **A2P 10DLC** (https://www.twilio.com/docs/messaging/compliance/a2p-10dlc, https://www.twilio.com/docs/messaging/compliance/a2p-10dlc/collect-business-info):
  - **Brand** = who sends. "Standard and Low-Volume Standard Brands require a Tax ID (e.g. EIN in U.S.)"; a business with an EIN must not register as Sole Proprietor.
  - **Low-Volume Standard:** under 6,000 segments per day, up to 5 campaigns.
  - **Brand fields:** exact legal name as on the IRS CP 575 EIN letter, business type, industry (`HEALTHCARE`), EIN, a working website, a contact person, address, and `brand_contact_email`.
  - A new EIN "can take 30-90 days to propagate".
  - The customer profile approval "may take 72 hours or more".
  - **Campaign** = what is sent and how people opt in. Fields:
    - `description` (40–4096 characters);
    - `message_flow` (40–2048; every opt-in method; for website opt-in, privacy policy and terms URLs, and consent text containing "Reply STOP to unsubscribe" and "Reply HELP for help");
    - `message_samples`, 2 to 5, each 20–1024 characters, naming the brand, `[]` for variables;
    - `us_app_to_person_usecase`;
    - `has_embedded_links` and `has_embedded_phone`;
    - the opt-in, opt-out and help messages and keywords, required only if we manage opt-out ourselves.
  - **Use cases:** `CUSTOMER_CARE`, `ACCOUNT_NOTIFICATION`, `MIXED` (higher cost, lower throughput), and `LOW_VOLUME` (Low-Volume Standard only, "lower monthly fee than MIXED"). There is no healthcare-specific use case; `HEALTHCARE` is an industry value.
  - **Review:** a brand is "typically… within a few minutes", but manual review takes "seven business days or more"; a campaign takes "up to 5 business days", and if it takes over 10 days, contact support (https://www.twilio.com/docs/messaging/compliance/a2p-10dlc/direct-standard-onboarding).
  - **Fees:** not retrieved. **Verify** on Twilio's pricing page.
- **Toll-free alternative:** "Twilio toll-free numbers can't send SMS messages to the United States and Canada until you've completed toll-free verification" (https://www.twilio.com/docs/messaging/compliance/toll-free/console-onboarding). Toll-free numbers always unsubscribe a patient who replies STOP.
- **Opt-out:** by default Twilio handles STOP, UNSUBSCRIBE, END, QUIT, STOPALL, REVOKE, OPTOUT and CANCEL on long codes. START and UNSTOP opt back in, and HELP is reserved. Sending to an opted-out number fails with error **21610** (https://www.twilio.com/docs/messaging/tutorials/advanced-opt-out). Advanced Opt-Out (custom texts) is off by default and set per Messaging Service.
- **WhatsApp templates** (only for the WhatsApp path):
  - **Categories:** utility, marketing, authentication. Utility must be non-promotional and specific to, or requested by, the user. Unclear templates become marketing.
  - **Variables:** positional `{{1}}` or named `{{first_name}}` (lowercase and underscores), with sample values required. A template "cannot start or end with a parameter".
  - **Limits:** body ≤ 1024 characters.
  - **Review:** "up to 24 hours".
  - Sources: https://developers.facebook.com/documentation/business-messaging/whatsapp/templates/template-review and https://developers.facebook.com/docs/whatsapp/updates-to-pricing/new-template-guidelines.
- **SMS length:** one GSM-7 segment is 160 characters; any non-GSM character (e.g. an emoji or "’") switches to UCS-2 with 70 characters per segment. **Verify** segment rules with the provider. We target one segment per message, two at most.

## 4. Scope
**In scope**
- Collecting the clinic's brand information (from the P0-01 SME and signatory), with no PHI.
- **SMS path:**
  - the clinic's secondary customer profile under our ISV account;
  - brand registration (Low-Volume Standard);
  - campaign registration;
  - one local number in the clinic's area code;
  - a Messaging Service with the number, default opt-out handling and status callback URL placeholders.
- **WhatsApp path (conditional):**
  - WhatsApp Business number and display name;
  - utility templates, PHI-free until P0-07a allows fields.
- `docs/messaging/templates.yaml` and `docs/messaging/templates.schema.json`.
- `scripts/messaging/check_templates.py` and its tests.
- Opt-in consent text (handed to P4-02), HELP and STOP texts, and texts for the clinic's website (privacy policy section and SMS terms).
- The registration record `docs/messaging/registration-<clinic_slug>.md`.
- One synthetic test send to a team phone.

**Out of scope** (and which task covers it)
- Choosing the channel → P0-07a; choosing and signing the provider BAA → P0-07
- The sending adapter, webhooks, retries, opt-out sync → P4-01
- Consent capture and storage in the widget → P4-02
- Sending confirmations and notices → P4-03; reminder scheduling and pre-send checks → P4-04
- Publishing the clinic website pages → the clinic (we supply the text)
- Rendering dates and times in the clinic's time zone → P4-03 (format defined here)

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P0-07a Messaging decision (approved spec) | Channel per message type; allowed fields | Start the SMS path and the templates with the Proposed default policy (DECISIONS #37). If WhatsApp is still open, submit only PHI-free WhatsApp drafts (DECISIONS #38). |
| P0-07 Provider + BAA (approved spec) | Provider account, ISV setup, BAA | Prepare the brand data, templates and texts now. Submit the registration only on the provider chosen in P0-07, since registrations don't move between providers (**Verify**). |
| P0-01 Workshop (approved spec) | Clinic legal name, EIN, address, website, contact; Q8 channel preference; area code | Use placeholders in `registration-<clinic_slug>.md`. Brand submission waits for these. |
| Clinic website owner (external) | Publishing the privacy policy section and the SMS terms | Send the texts (§6) early. The campaign's `message_flow` must link to live pages. |

## 6. Interface contract

### Files
| Path | Content |
|---|---|
| `docs/messaging/templates.yaml` | Message templates per type and channel (format below) |
| `docs/messaging/templates.schema.json` | JSON Schema for the file |
| `scripts/messaging/check_templates.py` | Validator (rules T1–T10) |
| `scripts/messaging/test_check_templates.py` | Pytest tests |
| `scripts/messaging/send_test_sms.py` | One-off synthetic test send (dev only) |
| `docs/messaging/opt-in-and-help-texts.md` | Consent text, HELP, STOP confirmation, website texts |
| `docs/messaging/registration-<clinic_slug>.md` | Brand, campaign, number, Messaging Service IDs, statuses, dates (no secrets) |

### `templates.schema.json`
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Patient message templates",
  "type": "object",
  "required": ["schema_version", "policy_version", "date_format", "time_format", "templates"],
  "additionalProperties": false,
  "properties": {
    "schema_version": {"const": 1},
    "policy_version": {"type": "string"},
    "date_format": {"const": "ddd, MMM D"},
    "time_format": {"const": "h:mm A"},
    "templates": {
      "type": "array",
      "minItems": 4,
      "items": {
        "type": "object",
        "required": ["id", "message_type", "channel", "version", "body", "variables", "example"],
        "additionalProperties": false,
        "properties": {
          "id": {"type": "string", "pattern": "^[a-z0-9_]+_v[0-9]+$"},
          "message_type": {"enum": ["booking_confirmation", "reminder", "reschedule_notice", "cancel_notice"]},
          "channel": {"enum": ["sms", "whatsapp"]},
          "version": {"type": "integer", "minimum": 1},
          "body": {"type": "string", "minLength": 20, "maxLength": 1024},
          "variables": {"type": "array", "items": {"type": "string", "pattern": "^[a-z_]+$"}, "uniqueItems": true},
          "include_stop_help": {"type": "boolean", "default": false},
          "whatsapp_category": {"const": "UTILITY"},
          "example": {"type": "object", "additionalProperties": {"type": "string"}}
        }
      }
    }
  }
}
```

### `templates.yaml` (Proposed wording; SMS path)
Variables use `{name}` in the body. P4-01 renders them; for WhatsApp, P4-01 maps them to named parameters `{{name}}`.
```yaml
schema_version: 1
policy_version: "1.0"          # must equal messaging_policy.yaml decision_version
date_format: "ddd, MMM D"      # e.g. "Tue, Mar 10" in the clinic's time zone
time_format: "h:mm A"          # e.g. "9:30 AM"
templates:
  - id: booking_confirmation_v1
    message_type: booking_confirmation
    channel: sms
    version: 1
    include_stop_help: true
    body: "{clinic_name}: Hi {first_name}, you're booked for {appointment_date} at {appointment_time}. To change it, call {clinic_phone}. Reply STOP to opt out, HELP for help."
    variables: [clinic_name, first_name, appointment_date, appointment_time, clinic_phone]
    example: {clinic_name: "Bright Smile Dental", first_name: "Maria", appointment_date: "Tue, Mar 10", appointment_time: "9:30 AM", clinic_phone: "(503) 555-0100"}
  - id: reminder_v1
    message_type: reminder
    channel: sms
    version: 1
    body: "{clinic_name}: Hi {first_name}, reminder: your visit is today at {appointment_time}. Need to change it? Call {clinic_phone}."
    variables: [clinic_name, first_name, appointment_time, clinic_phone]
    example: {clinic_name: "Bright Smile Dental", first_name: "Maria", appointment_time: "9:30 AM", clinic_phone: "(503) 555-0100"}
  - id: reschedule_notice_v1
    message_type: reschedule_notice
    channel: sms
    version: 1
    body: "{clinic_name}: Hi {first_name}, your visit is now {appointment_date} at {appointment_time}. Questions? Call {clinic_phone}."
    variables: [clinic_name, first_name, appointment_date, appointment_time, clinic_phone]
    example: {clinic_name: "Bright Smile Dental", first_name: "Maria", appointment_date: "Thu, Mar 12", appointment_time: "2:00 PM", clinic_phone: "(503) 555-0100"}
  - id: cancel_notice_v1
    message_type: cancel_notice
    channel: sms
    version: 1
    body: "{clinic_name}: Hi {first_name}, your visit on {appointment_date} is cancelled. To book again, call {clinic_phone}."
    variables: [clinic_name, first_name, appointment_date, clinic_phone]
    example: {clinic_name: "Bright Smile Dental", first_name: "Maria", appointment_date: "Tue, Mar 10", clinic_phone: "(503) 555-0100"}
```
> **Addition (P4-01, DECISIONS #252, #253):** WhatsApp entries also carry `whatsapp_mode` (`phi_free_nudge` | `minimal_phi`), `provider_template_name`, `language` and `provider_status` (`DRAFT`/`SUBMITTED`/`APPROVED`/`REJECTED`/`PAUSED`; P4-01 sends only `APPROVED`). The user chose WhatsApp, so the `phi_free_nudge` templates (clinic name and phone only) are submitted first, and `minimal_phi` ones only after the advisor approves. A top-level `system_replies` block holds the PHI-free STOP/START/HELP confirmations and the auto-reply. Examples in P4-01 §6.5.

Notes:
- Every message starts with the clinic name, as carriers expect the brand to be named.
- There are no links (`has_embedded_links: false`).
- The clinic phone is the only embedded phone number (`has_embedded_phone: true`).
- The words "dental" or "dentist" may appear only inside `clinic_name`. The templates never name a service, reason or provider.

### Validator `check_templates.py`
```
python scripts/messaging/check_templates.py \
    --templates docs/messaging/templates.yaml \
    --policy docs/compliance/messaging_policy.yaml   # exit 0 ok, 1 errors; prints rule, template id, message
```
| Rule | Check |
|---|---|
| T1 | Valid against `templates.schema.json` |
| T2 | `policy_version` equals `messaging_policy.yaml` `decision_version` |
| T3 | Every `{var}` in `body` is listed in `variables`, and vice versa |
| T4 | Every variable is in `message_types[<type>].fields` of the policy |
| T5 | No variable is in `never_allowed_fields` |
| T6 | `channel` equals the policy's channel for that type, and that channel has `allowed: true` |
| T7 | The body (with `example` filled in) contains none of the denylist words, case-insensitive, whole words. The list is kept in the script and extended in review: `appointment type`, `cleaning`, `exam`, `x-ray`, `filling`, `crown`, `root canal`, `extraction`, `implant`, `whitening`, `ortho`, `braces`, `emergency`, `pain`, `toothache`, `swelling`, `bleeding`, `infection`, `insurance`, `balance`, `payment`, `dr.`, `doctor`, `hygienist`. Exception: text inside the `clinic_name` example value. |
| T8 | SMS: the rendered `example` is GSM-7 only and ≤ 160 characters (warning if 161–306, error above 306) |
| T9 | At least one SMS template per type has `include_stop_help: true` **or** P4-01 sends the first-message disclosure. Proposed: the `booking_confirmation` template carries it. |
| T10 | WhatsApp templates: `whatsapp_category: UTILITY`, and the body doesn't start or end with a variable |

```python
# scripts/messaging/check_templates.py: core types (sketch)
from dataclasses import dataclass

@dataclass(frozen=True)
class Finding:
    rule: str          # "T1".."T10"
    template_id: str   # or "-" for file-level rules
    message: str       # no PHI; templates contain only fictional examples
    level: str         # "error" | "warning"

def check(templates: dict, policy: dict, schema: dict) -> list[Finding]: ...
def render(body: str, values: dict[str, str]) -> str: ...      # "{x}" -> value; KeyError -> T3 finding
def is_gsm7(text: str) -> bool: ...                             # GSM 03.38 basic + extension table
def main(argv: list[str] | None = None) -> int: ...             # 0 ok, 1 any error
```

### Campaign registration (SMS path; Twilio field names, **Verify** with P0-07's provider)
```json
{
  "brand": {
    "type": "LOW_VOLUME_STANDARD",
    "business_name": "<exact legal name on CP 575>",
    "business_type": "<Corporation | Limited Liability Corporation | ...>",
    "business_industry": "HEALTHCARE",
    "business_registration_identifier": "EIN",
    "business_registration_number": "<EIN>",
    "website_url": "https://<clinic website>",
    "brand_contact_email": "<clinic contact>"
  },
  "campaign": {
    "us_app_to_person_usecase": "LOW_VOLUME",
    "description": "Appointment notifications from <Clinic legal name> to its patients who opted in on the clinic website: booking confirmations, a reminder about one hour before the visit, and notices when a visit is rescheduled or cancelled. No marketing.",
    "message_flow": "Patients opt in on the clinic website (https://<clinic website>/...) when booking with the online assistant, by ticking an unchecked box: '<consent text from opt-in-and-help-texts.md>'. Privacy policy: https://<clinic website>/privacy. SMS terms: https://<clinic website>/sms-terms. Reply STOP to unsubscribe, HELP for help.",
    "message_samples": [
      "Bright Smile Dental: Hi Maria, you're booked for Tue, Mar 10 at 9:30 AM. To change it, call (503) 555-0100. Reply STOP to opt out, HELP for help.",
      "Bright Smile Dental: Hi Maria, reminder: your visit is today at 9:30 AM. Need to change it? Call (503) 555-0100.",
      "Bright Smile Dental: Hi Maria, your visit on Tue, Mar 10 is cancelled. To book again, call (503) 555-0100."
    ],
    "has_embedded_links": false,
    "has_embedded_phone": true,
    "opt_out_handling": "provider_default"
  }
}
```
Proposed use case: `LOW_VOLUME`, because the pilot brand is Low-Volume Standard and the messages cover several notification types. If the provider or carriers reject it, use `ACCOUNT_NOTIFICATION`. Avoid `MIXED`, which has higher cost and lower throughput. **Verify** which use case the provider recommends for appointment notifications.

### Opt-in, HELP and STOP texts (`opt-in-and-help-texts.md`; P4-02 uses the consent text verbatim)
```text
CONSENT CHECKBOX (unchecked by default):
"Text me appointment confirmations, a reminder before my visit, and changes from <Clinic name> at the number I gave. Up to 4 messages per appointment. Msg & data rates may apply. Reply STOP to opt out, HELP for help. Consent is not required to book. Privacy: <url> · Terms: <url>"

HELP reply (if provider default isn't used):
"<Clinic name> appointment texts. For help call <clinic phone>. Reply STOP to opt out. Msg & data rates may apply."

STOP confirmation (provider default or custom):
"<Clinic name>: You're unsubscribed and won't get more texts. Reply START to resubscribe."
```
If P0-07a sets `risk_notice_required: true`, P4-02 adds the advisor-approved risk sentence to the consent text. That sentence lives in `messaging_policy.yaml`, not here.

**Website texts for the clinic** (in the same file):
- an "SMS terms" page: program name, message types, frequency, rates, STOP/HELP, support contact, carriers not liable;
- a privacy policy paragraph: "Mobile numbers and SMS consent are not shared with third parties for marketing." **Verify** this exact requirement with the provider's campaign guidance.

### Registration record (`registration-<clinic_slug>.md`)
```markdown
# Messaging registration: <clinic_slug>
- Channel: sms | whatsapp          (from messaging_policy.yaml decision_version <x>)
- Provider: <name>; BAA record: docs/compliance/baa-<vendor>.md
- Customer profile SID: <BU…>  status: <…>  date: <…>
- Brand SID: <BN…>  type: LOW_VOLUME_STANDARD  status: <…>  date: <…>
- Campaign SID: <QE…>  use case: <…>  status: <…>  date: <…>
- Number: +1<area code>… (E.164)  Messaging Service SID: <MG…>
- Opt-out handling: provider default (STOP/START/HELP)
- Templates version: templates.yaml schema 1, ids: booking_confirmation_v1, …
- Test send: YYYY-MM-DD to team phone, synthetic data, delivered: yes/no
```
SIDs and IDs are not secrets. API keys and auth tokens are never written here; they go to Secret Manager (`messaging-api-key` per project; P1-05 / P4-01).

### Test send (dev only, synthetic data)
```bash
# Requires secret access in <prefix>-dev; destination must be in TEST_PHONE_ALLOWLIST.
python scripts/messaging/send_test_sms.py \
  --template booking_confirmation_v1 \
  --to "+15035550199" \
  --use-example-values
# Prints: provider message SID and status. Never prints the body after rendering with non-example values.
```
`send_test_sms.py` refuses to run if:
- `--to` isn't in `TEST_PHONE_ALLOWLIST`;
- any value other than the template's `example` is supplied;
- the environment is not `dev`.

## 7. Implementation guide
1. **Read the P0-07a decision.** Set `policy_version` and the channel per type. If the decision isn't final, use the Proposed default and mark the file `draft`.
2. **Write `templates.schema.json`, `templates.yaml` and `check_templates.py` with tests** (§10). Add `check_templates.py` to CI with P1-06, and run it locally until then.
3. **Collect brand data** from the clinic via the SME:
   - legal name exactly as on the CP 575;
   - EIN;
   - business type;
   - address;
   - website;
   - contact;
   - area code preference.

   Store it in `registration-<clinic_slug>.md`; the EIN is not secret but is kept out of public places.
4. **Send the website texts** to the clinic, and get confirmation that the privacy and SMS terms pages are live (URLs).
5. **SMS path, on the P0-07 provider:**
   1. create the clinic's secondary customer profile (ISV);
   2. register the Low-Volume Standard brand;
   3. when the brand is approved, register the campaign with the JSON in §6;
   4. buy a local number in the clinic's area code;
   5. create a Messaging Service, add the number, keep default opt-out handling, leave the status callback empty (P4-01 sets it);
   6. link the campaign.

   Record every SID and status. **Verify** each step in the provider's current console or API.
6. **WhatsApp path (only if allowed):**
   - register the number and display name;
   - create `whatsapp` templates in `templates.yaml` (category `UTILITY`, no leading or trailing variable), run the validator, and submit them through the provider;
   - record the approval status.

   If WhatsApp isn't decided yet, submit only a PHI-free draft such as "{clinic_name}: You have a message about your visit. Please call {clinic_phone}.", if the team wants to start Meta review early (DECISIONS #38).
7. **Track approvals.** Check the status twice a week. If rejected, read the reason, fix the template or `message_flow`, and resubmit. Log every resubmission in the record.
8. **Test send** with `send_test_sms.py` to a team phone, using the example values. Reply STOP, check that a second send fails with 21610, reply START, and check that it delivers again. Record the results.
9. **Notify:**
   - P4-01: Messaging Service SID secret name, templates file, validator, opt-out behaviour and 21610;
   - P4-02: consent text and risk-notice rule;
   - P4-03: date and time formats;
   - P4-04: reminder template;
   - P0-10: provider row, no change in PHI fields;
   - P0-14: F10 content matches.

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| The clinic's EIN is new (under 90 days) | Brand review may fail on mismatch. Wait, or file the provider's EIN appeal (5–7 business days). Record it in the open questions. |
| The brand goes to manual review (7+ business days) | Continue the templates and validator; P4 builds against the provider's test credentials. |
| The campaign is rejected for the use case | Resubmit with `ACCOUNT_NOTIFICATION`, adjusting the description. |
| The campaign is rejected because the opt-in isn't visible | Make sure the website pages are live and the `message_flow` URLs work; add a screenshot URL if the provider accepts one (**Verify**). |
| The clinic doesn't want its own brand (wants our company as sender) | Not proposed: patients don't know our company, and carriers expect the brand to match message content. Escalate to the sponsor. If accepted, our company is the brand and every message still names the clinic. |
| A template exceeds 160 characters with long clinic names | Shorten the wording; T8 warns. Two segments are allowed, never more. |
| Someone adds `{reason}` to a template | T4/T5 fail in CI; the PR can't merge. |
| The P0-07a decision changes fields later (e.g. removes `first_name`) | Bump `policy_version`; T2 fails until the templates are updated. Carrier samples must be updated if the wording changes materially (**Verify** whether that needs a new campaign). |
| The number is lost or ported | Keep the record. Re-attach a new number to the Messaging Service; the campaign stays (**Verify**). |
| A patient replies with free text (e.g. "can I come at 10?") | Not handled by this task. P4-01 forwards inbound replies according to its spec; the auto-reply points to the clinic phone. |

## 9. Security, HIPAA and PHI
- **No real PHI is handled.**
  - Brand data is business information.
  - Templates and samples use fictional values (Maria, `555-01xx`).
  - Test sends go only to team phones with example values.
- **Content rules are enforced by code:** T4–T7 make sure no template can carry a field outside `messaging_policy.yaml`, a `never_allowed_fields` item, or a service, reason or provider word.
- **Gate:** real patient messages are sent only after P0-07 (provider BAA), P0-09 (clinic BAA) and the P0-10 `--gate` are open. Registration and templates can be completed before that.
- **Secrets:** provider credentials only in Secret Manager. The registration record holds SIDs only.
- **Audit:** git history of `templates.yaml` (every wording change is reviewed), the registration record, and the provider console logs.

## 10. Testing
`pytest scripts/messaging/` (fixtures in `scripts/messaging/fixtures/`):
- the §6 example files → exit 0, no findings;
- a template with `{last_name}` → T5 error;
- a template with `{reason}`, not in the policy fields → T4 error;
- `{first_name}` in the body but missing from `variables` → T3 error;
- the word "cleaning" in the body → T7 error; the same word only inside the `clinic_name` example (e.g. "Clean Teeth Dental") → no error;
- a body of 170 GSM characters → T8 warning; 320 → T8 error; a body containing "’" → T8 non-GSM error;
- the policy's `decision_version` differs → T2 error;
- a WhatsApp template ending with `{clinic_phone}` → T10 error;
- the channel `whatsapp` while the policy has `whatsapp.allowed: false` → T6 error.

```python
def test_reason_variable_is_rejected(policy, schema):
    tpl = load("fixtures/templates_ok.yaml")
    tpl["templates"][0]["body"] += " Reason: {reason}"
    tpl["templates"][0]["variables"].append("reason")
    findings = check(tpl, policy, schema)
    assert any(f.rule in ("T4", "T5") and f.level == "error" for f in findings)
```

Manual checks:
- The STOP, 21610, START test send in step 8 (results recorded).
- The reviewer reads the rendered examples aloud as they'd appear on a lock screen, and confirms that nothing reveals a reason for the visit.

## 11. Acceptance criteria
- [ ] `templates.yaml`, `templates.schema.json` and `check_templates.py` (T1–T10) are committed; the §10 tests pass
- [ ] Four templates exist (confirmation, reminder, reschedule, cancel) for the decided channel, with variables only from `messaging_policy.yaml`
- [ ] SMS path: brand and campaign are **approved**, the local number is attached to a Messaging Service, and the SIDs are recorded (or, if still in review, submitted with status tracked and the blocker logged)
- [ ] WhatsApp path (only if allowed): number and display name registered, utility templates approved
- [ ] Opt-in, HELP and STOP texts and the clinic website texts are committed, and the clinic pages are live
- [ ] The test send, STOP (21610) and START behaviour are verified on a team phone with synthetic data
- [ ] The P4-01, P4-02, P4-03, P4-04, P0-10 and P0-14 issues are notified

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI: `pytest scripts/messaging/` (local until P1-06 adds it)
- [ ] PR reviewed (HIPAA review if labelled `phi`): reviewed by the tech lead and the compliance owner (wording); no `phi` label (no real PHI)
- [ ] No PHI in logs: scripts print IDs, rules and statuses only
- [ ] Docs / README updated: `docs/messaging/README.md` links the templates, texts and record

## 13. Hand-off
| Task | Can rely on |
|---|---|
| P4-01 Messaging adapter | Templates file and validator (run at startup too), Messaging Service SID, opt-out behaviour, error 21610, provider secret name |
| P4-02 Consent | Exact consent text and website URLs; risk-notice rule from the policy |
| P4-03 Confirmations / notices | Templates per type; `date_format` / `time_format` in the clinic's time zone |
| P4-04 Reminders | `reminder_v1` template |
| P0-10 / P0-14 | Provider row and flow F10 fields unchanged |
| P6-01 Go-live | Registration approved; numbers active |

## 14. Open questions
| Question | Owner | Needed by |
|---|---|---|
| Which A2P use case does the provider recommend for appointment notifications (`LOW_VOLUME` vs `ACCOUNT_NOTIFICATION`)? | Tech lead, with the provider | Step 5 |
| What are the current brand, campaign and number fees, and who pays (us or the clinic)? | Project sponsor | Step 5 |
| Can the clinic publish the SMS terms and privacy text on its website, and who does it? | Clinic SME | Step 4 |
| Is the clinic's EIN older than 90 days, and does its legal name exactly match the CP 575? | Clinic signatory | Step 3 |

## 15. References
- Plan §4.7, §3.3, §2 #9–10, §6
- A2P 10DLC overview: https://www.twilio.com/docs/messaging/compliance/a2p-10dlc
- Brand and campaign fields: https://www.twilio.com/docs/messaging/compliance/a2p-10dlc/collect-business-info
- Direct standard onboarding (review times): https://www.twilio.com/docs/messaging/compliance/a2p-10dlc/direct-standard-onboarding
- Toll-free verification: https://www.twilio.com/docs/messaging/compliance/toll-free/console-onboarding
- Opt-out handling: https://www.twilio.com/docs/messaging/tutorials/advanced-opt-out
- WhatsApp template review: https://developers.facebook.com/documentation/business-messaging/whatsapp/templates/template-review
- WhatsApp template categories: https://developers.facebook.com/docs/whatsapp/updates-to-pricing/new-template-guidelines
- Related tasks: P0-01, P0-07, P0-07a, P0-09, P0-10, P0-14, P1-05, P1-06, P4-01, P4-02, P4-03, P4-04, P6-01
