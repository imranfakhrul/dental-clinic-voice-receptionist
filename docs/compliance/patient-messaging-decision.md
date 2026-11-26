# Decision memo: patient messaging channel (P0-07a)

| | |
|---|---|
| Task | P0-07a ([issue #7](https://github.com/imranfakhrul/dental-clinic-voice-receptionist/issues/7)) |
| For | Sam Comply (compliance advisor) and Morgan Lead (project sponsor), our company |
| Prepared by | Riley Tech (tech lead), 2026-11-26 |
| Status | **Decided (v1.2):**

- **Now:** WhatsApp is used for building and testing, with synthetic data only.
- **Production:** each clinic chooses **SMS or WhatsApp**.
  - SMS goes through a provider with a BAA.
  - WhatsApp may carry real details only after **BAAs with Meta and the WhatsApp provider are signed**. Until then, that clinic uses SMS.

See §6.5. |
| Policy file | [messaging_policy.yaml](messaging_policy.yaml), checked by `scripts/compliance/check_messaging_policy.py` |
| Sources | [sources/README.md](sources/README.md). IDs such as S1 and P2 below refer to it. All checked 2026-11-26. |

## 1. Question
Which channel may carry booking confirmations, reminders, and reschedule and cancel notices to patients, and with what content?

The options are WhatsApp, SMS, a WhatsApp "you have a message" nudge with a secure link, or email. A message from a dental clinic with the patient's name and appointment time reveals a patient relationship, so it is likely PHI. It may only travel through vendors covered by a BAA (plan §3.3).

## 2. Facts
1. **Meta isn't a business associate.** Meta's terms say the business acknowledges "Meta is not a Business Associate or Subcontractor" and that "the WhatsApp Business Platform is not HIPAA compliant" (S1, §4.2, page modified 2026-09-23). Meta also makes no warranty that the platform meets the needs of healthcare (S2).
2. **WhatsApp's own policy restricts health information.** It says: "Don't use WhatsApp … to send or request any health related information if applicable regulations prohibit distribution of such information to systems that do not meet heightened requirements…" (S3, §3).
3. **Meta itself processes the message content.** With the Cloud API, Meta processes "message content", phone numbers and message details (S4 §1.1, S5 §2.2). A provider's BAA can't cover Meta's part of the path.
4. **No provider puts WhatsApp under a BAA** (table below). Twilio's eligible list leaves it out (P2). Vonage's BAA names only SMS/MMS (P3). Sinch and Infobip don't name it (P4, P5). 360dialog publishes no HIPAA or BAA statement at all (P7).
5. **SMS is covered by documented BAAs.**
   - **Twilio:** its eligible list includes Programmable SMS and MMS, with long codes, toll-free, short codes and opt-out (P2, updated 2026-06-30). A BAA requires Security or Enterprise Edition (P1).
   - **Vonage:** its Messages API covers SMS and MMS "under the Vonage BAA for U.S. traffic", with dedicated numbers (P3).

### BAA coverage by provider (2026-11-26)
| Provider | SMS | WhatsApp | Conditions / notes |
|---|---|---|---|
| Twilio (P1, P2) | **Covered** (Programmable SMS/MMS) | **Not covered** (not on the eligible list) | Security or Enterprise Edition |
| Vonage (P3) | **Covered** (Messages API SMS/MMS, US traffic) | Not named | Dedicated numbers only for HIPAA messaging |
| Sinch (P4) | BAA exists "per product"; the products aren't published | Not named | Ask Sinch for the product list in writing (P0-07) |
| Infobip (P5) | BAA "for eligible services"; 2021 attestation covered SMS | Not named | No public eligible list |
| Bird (P6) | "not … a business associate" unless agreed in writing | Same | Excluded unless a BAA is negotiated |
| 360dialog (P7) | - (WhatsApp only) | No HIPAA/BAA statement found | Excluded |

## 3. Message types and content
| Message type | When (source) | Content in the plan | Minimum content proposed |
|---|---|---|---|
| Booking confirmation | Right after booking (plan §4.7, P4-03) | Name, clinic, date, time | First name, clinic name, date, time, clinic phone, opt-out text |
| Reminder | 60 minutes before the visit (plan §4.7, P4-04) | Name, clinic, date, time | Same as the confirmation |
| Reschedule notice | After a reschedule (P4-08) | Name, clinic, new date and time | Same as the confirmation |
| Cancel notice | After a cancellation (P4-08) | Name, clinic, date | First name, clinic name, date, clinic phone, opt-out text |

**Never in any message:** last name, date of birth, reason or reason code, procedure, symptoms, provider name, insurance, PatNum, AptNum.

## 4. Options
| Option | What the patient gets | Vendors in the path | BAA coverage | Main risk |
|---|---|---|---|---|
| **A. WhatsApp, minimal content, informed consent** | WhatsApp message: first name, clinic, date, time | Provider + **Meta** | Provider maybe; **Meta disclaims it** (S1); no provider names WhatsApp (§2) | Legal: no BAA chain is possible; Meta's policy restricts health information (S3) |
| **B. SMS through a provider with a BAA** | Text message: first name, clinic, date, time | SMS provider + carriers | **Documented** (Twilio P2, Vonage P3) | Carrier registration lead time; SMS isn't end-to-end encrypted |
| **C. WhatsApp PHI-free nudge + secure link** | "You have a new message from your dental office: <link>" | Provider + Meta (no PHI in the text) + our app | No PHI to Meta *if* the message itself reveals nothing | The clinic's sender name plus the phone number may itself reveal the relationship; needs a secure page and patient verification (new task); poor experience one hour before the visit |
| **D. Email under the Workspace BAA** | Email with details | Google Workspace | Workspace BAA (P0-08, DECISIONS #40) | Low reach for a 1-hour reminder; email addresses often not collected |

## 5. Questions for the advisor
1. Given Meta's §4.2 statement, may PHI (first name, clinic, appointment date and time) be sent over WhatsApp at all, with or without the patient's informed consent?
2. If not, is a PHI-free WhatsApp message (option C) acceptable, given that the sender is a dental clinic's account?
3. Is SMS through a provider under a BAA acceptable for this content, and what must the patient be told?
4. What must the consent wording say (risk notice, channel, opt-out), and does TCPA add requirements?
5. Must the clinic ↔ company BAA (P0-09) mention the messaging channel and subcontractor?

## 6. Decision

### 6.1 Advisor's written answers (Sam Comply, compliance advisor, 2026-11-26)
These are the advisor's opinions for this project, based on the facts in §2. They aren't general legal advice.

1. **No.** Meta states it isn't a business associate and that the platform isn't HIPAA compliant, and no provider offers a BAA that covers WhatsApp. So there is no BAA chain for this content. Patient consent doesn't fix that for routine messages that we start. WhatsApp's own policy (S3) also points the other way. **Don't send PHI over WhatsApp.**
2. **Not approved for the MVP.** A message sent from a dental clinic's WhatsApp account to a patient's number can itself reveal the patient relationship, even if the text contains nothing else. It also needs a secure page with patient verification, which no task covers. It may be reconsidered later only with a reviewed design, as a new task.
3. **Yes, with conditions:**
   - The provider's signed BAA must name the SMS product we use (see P2, P3).
   - Only the minimum fields in §3.
   - A dedicated sending number.
   - The patient must be told that a text message isn't encrypted end to end and may be seen by anyone with access to their phone, and how to stop messages.
4. **Consent wording.** P4-02 writes it, and it must be confirmed with the advisor before launch. It must:
   - name the channel (text message to the number the patient gives);
   - name the message types (confirmation, reminder, changes);
   - include the risk notice from answer 3;
   - say that message and data rates may apply;
   - explain opt-out with STOP and help with HELP;
   - state that consent isn't required to book.

   **TCPA:** treat it as requiring the patient's prior express consent for these automated texts. Keep a dated record of that consent (P4-02 stores it). Honour STOP at once (P4-07). The provider and carrier rules (registration, quiet hours) are checked with the chosen provider in P0-07 and P0-15.
5. **Yes.** The clinic ↔ company BAA (P0-09) must say that we use subcontractors that handle PHI under their own BAAs, including the SMS provider. The vendor matrix (P0-10) must list it.

### 6.2 Decision (approved by the sponsor)
| Message type | Testing (now; synthetic data) | Real patients (go-live; superseded by §6.5: the clinic's choice) | Fields |
|---|---|---|---|
| Booking confirmation | WhatsApp | SMS (option B) | first name, clinic name, date, time, clinic phone |
| Reminder | WhatsApp | SMS (option B) | first name, clinic name, date, time, clinic phone |
| Reschedule notice | WhatsApp | SMS (option B) | first name, clinic name, date, time, clinic phone |
| Cancel notice | WhatsApp | SMS (option B) | first name, clinic name, date, clinic phone |

- **WhatsApp:** the testing channel only. It carries synthetic data, goes only to the team's test numbers, and never carries real PHI (`allowed_with_phi: false`, `testing_only: true`).
- **SMS:** integrated now but switched off (`enabled: false`). It's switched on at go-live, after P0-07 signs the provider's BAA.
- **Email:** not used for these messages.
- **Conditions:**
  - SMS is sent only through a provider whose signed BAA names its SMS product.
  - No message without recorded consent, including the risk notice.
  - Every message includes opt-out text.
  - The never-allowed fields in §3 are a hard limit for all templates.
  - The sources are re-checked before go-live (P5-14); weaker coverage re-opens this decision.
- **Scope change:** plan §2 #9–10 and §4.7 assumed WhatsApp for real patients. WhatsApp stays, for testing; SMS is added for real patients. These tasks need re-scoping when they're specified (DECISIONS #297, #298):
  - P0-07 (a WhatsApp provider for testing; an SMS provider with a BAA for go-live);
  - P0-15 (WhatsApp test number and templates now; SMS sender registration before go-live);
  - P4-01 (both adapters: WhatsApp active, SMS switched off);
  - P4-03, P4-04, P4-07, P4-08;
  - P4-13 (settings screens).

**Signed:**
- Sam Comply, compliance advisor, 2026-11-26
- Morgan Lead, project sponsor, 2026-11-26

### 6.3 Clinic informed (P0-01 Q8)
- **Sent** 2026-11-26 to Alex Sample, office manager (clinic SME): "Reminders and confirmations will go by text message (SMS) through a provider that signs a BAA; WhatsApp won't be used because Meta doesn't sign a BAA. Messages carry only first name, clinic, date, time and the clinic phone, and only if the patient agrees."
- **Reply** 2026-11-26: "Agreed, that's what we expected; most of our patients prefer texts anyway."
- **Recorded** as revision Q8-r1 in the [clinic decision log](../discovery/clinic-decision-log.md).

### 6.4 Revision v1.1: testing channel (user decision, 2026-11-26)
The project owner decided:
- **WhatsApp is the only channel used now, for testing.** The team uses its own WhatsApp test numbers with synthetic data only.
- **SMS is integrated** (adapter and templates) but **not used now**.

**Why this is allowed:** no real patient data exists in testing (DECISIONS #25), so no PHI reaches Meta.

**What still holds (advisor, Sam Comply):** answers 1–2 apply to **real** patient data. Before real patients use the system, either:
- the production channel switches to SMS through a provider whose BAA names its SMS product (as in `messaging_policy.yaml`), or
- this decision is re-opened.

**The policy file** encodes this: `environments.testing.active_channel: whatsapp`, `environments.production.active_channel: sms`, with `live: false`.

**Signed:**
- Sam Comply, compliance advisor, 2026-11-26
- Morgan Lead, project sponsor, 2026-11-26

### 6.5 Revision v1.2: the clinic chooses the production channel (user decision, 2026-11-26)
The project owner decided:
- **WhatsApp is used now**, for building and testing (as in §6.4).
- **At go-live, each clinic chooses SMS or WhatsApp** for its patients.
- **We plan to sign a BAA with Meta** for production WhatsApp.

**Rules this sets** (encoded in `messaging_policy.yaml` v1.2, `environments.production.channel_choice: per_clinic`):

| Clinic chooses | Real patient details may be sent when | Until then |
|---|---|---|
| SMS | The SMS provider's signed BAA names its SMS product (P0-07) | Clinic isn't live |
| WhatsApp | **Signed BAAs with Meta and with the WhatsApp provider** are on file and recorded in the vendor matrix (P0-10) | Clinic uses SMS (`fallback_until_gate: sms`), or waits |

**Advisor's note (Sam Comply):**
- Meta's current terms (S1, §4.2, modified 2026-09-23) say Meta "is not a Business Associate", and no WhatsApp provider's BAA names WhatsApp (§2).
- A Meta BAA would therefore be a special agreement. Ask Meta for it in writing early (P0-07). Accept it only if it explicitly covers WhatsApp Business Platform message content, and only after legal review (P0-11).
- If Meta declines, WhatsApp clinics stay on SMS; WhatsApp may carry no patient details.
- **Consent** (P4-02) must name the channel the clinic chose.

**Signed:**
- Sam Comply, compliance advisor, 2026-11-26
- Morgan Lead, project sponsor, 2026-11-26
