---
id: P0-07a
title: Decide HIPAA-compatible patient messaging channel (compliance memo)
milestone: P0
epic: E0.2
size: S
labels: area:compliance, area:messaging, type:docs
depends_on: none
status: approved
---

# P0-07a: Decide HIPAA-compatible patient messaging channel (compliance memo)

## 1. Summary
Write a short decision memo for the compliance advisor and the project sponsor. It answers one question: **which channel may carry booking confirmations, reminders and reschedule/cancel notices, and with what content?** The options are WhatsApp, SMS, a PHI-free WhatsApp nudge with a secure link, or email.

The memo states the verified facts with their sources, compares the options, and ends with a written decision. It also produces `docs/compliance/messaging_policy.yaml`, a machine-readable content policy that later tasks enforce: which channel is allowed for which message type, and which fields a message may contain. Done means: the advisor and the sponsor have signed the decision, the clinic has been informed (P0-01 Q8), and P0-07 can select a provider.

## 2. Why this matters
The plan (§2 #9–10, §3.3, §4.7) assumes WhatsApp reminders are HIPAA-safe as long as we "sign the BSP's BAA". Checking Meta's own terms contradicts that (DECISIONS #35):
- **Meta Terms for WhatsApp Business Platform, §4.2** (last modified 2026-09-23): you acknowledge "that Meta is not a Business Associate or Subcontractor … and that the WhatsApp Business Platform is not HIPAA compliant." Source: https://www.facebook.com/legal/Meta-Terms-for-WhatsApp-Business-Platform
- **WhatsApp Business Messaging Policy, §3:** don't use WhatsApp to "send or request any health related information, if applicable regulations prohibit distribution of such information to systems that do not meet heightened requirements". Source: https://business.whatsapp.com/policy
- **Meta processes message content.** The Cloud API is "provided by Meta", and "message content" is data Meta processes (Meta Hosting Terms for Cloud API, §1.1 and §2.2: https://www.facebook.com/legal/Meta-Hosting-Terms-Cloud-API). A BSP's BAA can't cover Meta's part of the path.
- **Twilio's "HIPAA Eligible Services" list** (updated 2026-06-30) includes Programmable SMS and MMS but **not WhatsApp**. Twilio signs a BAA only for its Security or Enterprise Edition. Source: https://www.twilio.com/en-us/hipaa

A reminder with the patient's name, the clinic, and the date and time, sent by a dental clinic, reveals a patient relationship and is likely PHI. Sending it over the wrong channel could be a HIPAA violation for the clinic and for us. This is a legal judgement, so it must be made in writing by the compliance advisor, not by developers.

The decision blocks P0-07 (provider and BAA), P0-15 (sender registration and templates) and P4-01 to P4-08 (messaging features). Patients see the result directly: which app the reminder arrives in, and what it says.

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P0, Discovery & Compliance Foundation**.
- **What the plan wanted (§4.7):** a confirmation right after booking, and a reminder 60 minutes before the appointment, sent only with consent and only with "name, clinic, date and time", no procedure or symptoms. Plus reschedule/cancel notices (P4-08) and STOP opt-out (P4-07).
- **BSP:** WhatsApp Business Solution Provider, a company that connects businesses to the WhatsApp Business Platform. With the Cloud API, Meta itself hosts and processes the messages.
- **WhatsApp template categories:** business-initiated messages must use pre-approved templates categorized as **authentication, marketing or utility** (https://developers.facebook.com/documentation/business-messaging/whatsapp/templates/overview). Utility templates follow up on user actions and must be non-promotional. **Verify:** whether Meta accepts appointment reminders as utility (they aren't named in Meta's examples).
- **Business associate:** a vendor that creates, receives, keeps or transmits PHI for a covered entity (the clinic) or for another business associate (us). It needs a BAA. Whether a messaging network counts as one, or whether an exception applies, is for the advisor to decide.
- **Patient-requested communication:** HHS guidance discusses when a provider may communicate with a patient through a less secure channel at the patient's request after warning them of the risk. **Verify with the advisor** whether and how it applies here, given Meta's terms.
- **US SMS registration:** application-to-person SMS from ordinary US numbers generally requires carrier registration (A2P 10DLC), or toll-free number verification. **Verify** the current rules and lead times with the chosen provider; this affects P0-15.
- **TCPA:** a US law on automated texts and calls, with consent rules. **Verify with the advisor** how it applies to appointment messages and what the consent wording (P4-02) must say.

## 4. Scope
**In scope**
- Re-checking and quoting the sources above (dated) and the BAA position of at least three messaging providers per channel considered.
- Defining exactly what data each message type would contain.
- Comparing options A–D (§6) and listing the questions the advisor must answer.
- The decision record, signed by the compliance advisor and the project sponsor, and the clinic informed.
- `docs/compliance/messaging_policy.yaml` (the content policy that later tasks enforce).
- Updating P0-01 Q8 wording if the workshop hasn't happened yet (done in this spec change; see DECISIONS #39).

**Out of scope** (and which task covers it)
- Choosing the provider and signing its BAA → P0-07
- Registering numbers/senders and submitting templates → P0-15 (re-scoped to the chosen channel)
- Consent capture and wording in the conversation → P4-02
- Sending, scheduling, webhooks, opt-out → P4-01 to P4-08
- Changing the plan document (read-only); the change is recorded in DECISIONS.md and noted for the PDF

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| None (hard) | - | Start now. |
| P0-01 Discovery workshop (soft) | Q8: the clinic's view on SMS vs WhatsApp; patients' preferences | Write the memo now. Its decision section lists the clinic's input as pending and is completed after the workshop, or by email with the SME. |
| Compliance advisor (external) | A written opinion | Book the review as soon as the memo draft is ready. |

## 6. Interface contract

### Files
| Path | Content |
|---|---|
| `docs/compliance/patient-messaging-decision.md` | The memo (structure below) |
| `docs/compliance/messaging_policy.yaml` | The decided content policy (format below) |
| `docs/compliance/sources/` | PDFs or saved copies of every quoted source page, file name with the date |

### Memo structure
1. **Question:** one paragraph.
2. **Facts:** each with a quote of at most one sentence, a URL and the date checked. Meta terms, Meta policy, Cloud API hosting, and each provider's BAA coverage.
3. **Message types and their content:** a table, one row per message type.
4. **Options A–D:** compared in the table below.
5. **Questions for the advisor:** numbered, as listed below.
6. **Decision:** the chosen option per message type, content rules, consent requirements, conditions, signatures (advisor, sponsor), date, and clinic informed (date, SME).

### Options
| Option | What the patient gets | Vendors in the message path | BAA coverage | Main risk |
|---|---|---|---|---|
| **A. WhatsApp, minimal content + informed consent** | WhatsApp message with first name, clinic, date, time | BSP + Meta | BSP may sign; **Meta disclaims** | Legal: Meta not a BA and states non-compliance; Meta policy restriction |
| **B. SMS via BAA provider** (Proposed default) | Text message with first name, clinic, date, time | SMS provider + carriers | Provider BAA (e.g. Twilio lists SMS; Security/Enterprise Edition) | Carrier registration lead time; SMS isn't encrypted end to end (advisor to judge) |
| **C. WhatsApp PHI-free nudge + secure link** | "You have a new message from your dental office: <link>"; details only after opening our secure page | BSP + Meta (no PHI) + our app | No PHI to Meta if the link and text carry none | Needs a secure page plus patient verification (more build work, new task); worse experience 1 hour before the visit |
| **D. Email under the Workspace BAA** | Email with details | Google Workspace | Workspace BAA (P0-08) | Low open rate for a 1-hour reminder; email address often not collected |

Options can differ per message type (e.g. B for reminders, C for reschedule notices).

### Questions for the advisor (minimum)
1. Given Meta's §4.2 statement, may PHI (first name + clinic + appointment date/time) be sent over WhatsApp at all, with or without the patient's informed consent?
2. If not, is a PHI-free WhatsApp message (option C) acceptable, given that the sender is a dental clinic's account?
3. Is SMS through a provider under a BAA acceptable for this content, and what must the patient be told?
4. What must the consent wording say (risk notice, channel, opt-out), and does TCPA add requirements?
5. Must the clinic ↔ company BAA (P0-09) mention the messaging channel and subcontractor?

### `messaging_policy.yaml` (example: shape only, the values are set by the decision)
```yaml
schema_version: 1
decision_version: "1.0"
decided_on: "2026-12-05"
approved_by: ["<compliance advisor>", "<project sponsor>"]
memo: docs/compliance/patient-messaging-decision.md
channels:
  sms:
    allowed: true
    provider_baa_required: true
  whatsapp:
    allowed: false            # true only if the advisor approves option A or C
    mode: none                # none | phi_free_nudge | minimal_phi
  email:
    allowed: false
message_types:
  booking_confirmation: {channel: sms, fields: [first_name, clinic_name, appointment_date, appointment_time, clinic_phone]}
  reminder:             {channel: sms, fields: [first_name, clinic_name, appointment_date, appointment_time, clinic_phone]}
  reschedule_notice:    {channel: sms, fields: [first_name, clinic_name, appointment_date, appointment_time, clinic_phone]}
  cancel_notice:        {channel: sms, fields: [first_name, clinic_name, appointment_date, clinic_phone]}
never_allowed_fields: [last_name, dob, reason, reason_code, procedure, symptoms, provider_name, insurance, pat_num, apt_num]
consent:
  required: true
  risk_notice_required: true   # set by the advisor
  wording_owner: P4-02
```
**Rules for later tasks:**
- P4-01 must refuse to send any message type whose channel isn't `allowed`.
- P4-01 must refuse any template variable not in that type's `fields`.
- `never_allowed_fields` can never appear in any template, regardless of the per-type list.

## 7. Implementation guide
1. **Re-check the sources** listed in §2 and save dated copies under `docs/compliance/sources/`. If any wording has changed, quote the new wording.
2. **Check providers.** Per channel considered, check at least three providers' published HIPAA/BAA pages, and record exactly which products their BAA covers (e.g. Twilio's eligible-services list). Candidates to check: Twilio, Vonage, Sinch, Infobip, Bird, and 360dialog for WhatsApp. **Verify:** each one's current BAA position; don't rely on sales claims without a document.
3. **Fill in the message-type table** from plan §4.7, P4-03 and P4-08.
4. **Draft the options comparison** and the advisor questions. Keep the memo to about 3 pages.
5. **Advisor review.** Send the memo; get written answers to every question.
6. **Sponsor decision.** The sponsor approves the chosen option(s). If WhatsApp is dropped or limited, the sponsor also accepts the scope change against plan §2 #9–10 and §4.7. Record it in DECISIONS.md.
7. **Inform the clinic** (P0-01 Q8): send a two-line summary to the SME and record the date and response in the decision section.
8. **Write `messaging_policy.yaml`** to match the decision exactly, and have the advisor confirm it.
9. **Notify** P0-07, P0-15, P4-01, P4-02, P4-03, P4-07 and P4-08 with the decision and the policy file. If the channel isn't WhatsApp, flag that P0-15 and the P4 titles need re-scoping; log it in DECISIONS.md when those tasks are specified.

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| The advisor approves WhatsApp with conditions (option A) | Record the conditions in the decision and encode them in `messaging_policy.yaml` (e.g. `risk_notice_required: true`). P4-02 must implement the conditions. |
| The advisor rejects all PHI on WhatsApp but allows option C | C needs a secure page with patient verification, which no task covers yet. Propose a new task (log it in DECISIONS.md, new epic/ID) before P4 starts. |
| No provider's BAA covers the chosen channel | That option fails. Pick the next option; don't send PHI without a covered BAA (plan §3.3 compliance gate). |
| Sources change after the decision (Meta or a provider updates its terms) | Re-check before go-live (P5-14). If coverage is weaker, re-open the decision. |
| The clinic insists on WhatsApp against the advisor's opinion | Not allowed. Escalate to the sponsor; the advisor's written opinion stands. Offer option C. |
| The sponsor wants to keep WhatsApp and decide later | Messaging features (P4) stay blocked; P0-15 may only submit PHI-free template drafts (DECISIONS #38). |
| The patient has no mobile phone or declines messages | Out of scope here; P4-02 handles no-consent (no messages, booking unaffected). |

## 9. Security, HIPAA and PHI
- **No PHI is handled.** The memo uses example field names only.
- This task decides **where PHI may go**. The resulting `never_allowed_fields` list and channel rules are hard limits for P4-01 to P4-08.
- Saved source copies and the advisor's opinion are confidential company documents (private repo or drive), not PHI.
- **Audit:** not applicable. Later, every message send is audited by P4-01 / P1-12.

## 10. Testing
No application code. Checks:
- `messaging_policy.yaml` parses as YAML. Every `message_types.*.channel` refers to a channel with `allowed: true`. No field in any `fields` list appears in `never_allowed_fields`. A reviewer checks this by hand; P4-01 adds the automated test.
- Reviewer checklist: every fact in the memo has a URL, a date and a saved copy; every advisor question has a written answer; the decision matches the YAML.

## 11. Acceptance criteria
- [ ] `patient-messaging-decision.md` contains dated, sourced facts (Meta terms §4.2, Meta policy §3, Cloud API hosting, and the BAA coverage of ≥ 3 providers per considered channel)
- [ ] Every advisor question has a written answer from the compliance advisor
- [ ] The decision names one option per message type and is signed by the advisor and the sponsor
- [ ] The clinic SME has been informed, and the date is recorded
- [ ] `messaging_policy.yaml` matches the decision and passes the §10 checks
- [ ] A DECISIONS.md row records the decision and any scope change against plan §2 #9–10 / §4.7
- [ ] The P0-07, P0-15, P4-01, P4-02, P4-03, P4-07 and P4-08 issues have a comment with the decision

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI: not applicable (no code); the §10 checks were done by the reviewer
- [ ] PR reviewed (HIPAA review if labelled `phi`): reviewed by the compliance advisor; no `phi` label because no PHI is handled
- [ ] No PHI in logs: no PHI in any file
- [ ] Docs / README updated: memo and policy linked from `docs/compliance/`

## 13. Hand-off
| Task | Can rely on |
|---|---|
| P0-07 Provider + BAA | The allowed channel(s) and the conditions a provider must meet |
| P0-15 Sender registration / templates | Which channel to register, and the exact fields allowed per message type |
| P4-01 Messaging adapter | `messaging_policy.yaml` as an enforced content policy |
| P4-02 Consent | Consent and risk-notice requirements from the advisor |
| P4-03, P4-07, P4-08 | Channel and fields per message type |
| P0-09, P0-10, P5-14 | Advisor opinion and the chosen vendor path for the BAA chain and vendor matrix |

## 14. Open questions
| Question | Owner | Needed by |
|---|---|---|
| The five advisor questions in §6 | Compliance advisor | Step 5 |
| If WhatsApp is limited or dropped: does the sponsor accept the scope change against plan §2 #9–10 and §4.7? | Project sponsor | Step 6 |
| Does the pilot clinic's patient base prefer WhatsApp or SMS? | Clinic SME (P0-01 Q8) | Step 7 |
| If option C is chosen: who specifies the secure message page (new task)? | Tech lead | Before P4 |

## 15. References
- Plan §2 #9–10 and #15, §3.3 (BAA strategy and compliance gate), §4.7 (WhatsApp reminders), §12 (risk: BSP won't sign a BAA)
- Meta Terms for WhatsApp Business Platform: https://www.facebook.com/legal/Meta-Terms-for-WhatsApp-Business-Platform
- WhatsApp Business Messaging Policy: https://business.whatsapp.com/policy
- Meta Hosting Terms for Cloud API: https://www.facebook.com/legal/Meta-Hosting-Terms-Cloud-API
- WhatsApp template categories: https://developers.facebook.com/documentation/business-messaging/whatsapp/templates/overview
- Twilio HIPAA: https://www.twilio.com/en-us/hipaa (HIPAA Eligible Services list, updated 2026-06-30)
- HHS HIPAA guidance for professionals: https://www.hhs.gov/hipaa/for-professionals/index.html
- Related tasks: P0-01, P0-07, P0-08, P0-09, P0-10, P0-15, P4-01, P4-02, P4-03, P4-07, P4-08, P5-14
