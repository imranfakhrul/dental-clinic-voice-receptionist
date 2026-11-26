# Patient-messaging providers (P0-07)

| | |
|---|---|
| Task | P0-07 ([issue #8](https://github.com/imranfakhrul/dental-clinic-voice-receptionist/issues/8)) |
| Prepared by | Riley Tech (tech lead), 2026-11-26 |
| Status | **Chosen:** WhatsApp = **Meta WhatsApp Cloud API (direct)**; SMS = **Twilio Programmable Messaging** (switched off until go-live). Both BAAs are **NOT ACCEPTED** (paper), so no PHI. |
| Policy | [messaging_policy.yaml](../compliance/messaging_policy.yaml) v1.2, memo [patient-messaging-decision.md](../compliance/patient-messaging-decision.md) |
| Evidence | [sources/README.md](../compliance/sources/README.md). IDs such as M2, T1, P2 refer to it. All checked 2026-11-26. |
| BAA records | [baa-meta-whatsapp.md](../compliance/baa-meta-whatsapp.md), [baa-twilio.md](../compliance/baa-twilio.md) |

## 1. What the policy allows (P0-07a, decision version 1.2)
| Use | Channel | Data | Condition |
|---|---|---|---|
| Testing now (dev, staging) | WhatsApp | Synthetic only, team phones only | No BAA needed (no PHI) |
| Production, clinic chose SMS | SMS | Real (first name, clinic, date, time, clinic phone) | SMS provider's signed BAA names its SMS product |
| Production, clinic chose WhatsApp | WhatsApp | Real | Signed BAAs with **Meta** and any WhatsApp provider in the path; until then the clinic uses SMS |

## 2. How providers are scored
- The 9 criteria from the task spec §6. **Must** = 1, 2 (recorded), 3, 4, 5. **Should** = 6–9.
- Each cell is **yes**, **no** or **partial**, with its evidence ID.
- A provider that fails a Must is out for that use.
- **Criterion 1 for WhatsApp has two columns:** testing (no PHI, so a BAA isn't needed) and production (PHI).
- **How we read two Musts:**
  - **#3:** the sender options must be documented. No provider publishes review lead times, so lead time is asked in writing (§6) and scored "partial" for everyone.
  - **#5:** the opt-out must reach us (passthrough) so P4-07 can honour it. Provider-level keyword handling is a plus.

## 3. WhatsApp comparison
| # | Criterion | Meta Cloud API (direct) | Twilio WhatsApp | Vonage Messages API | Infobip | 360dialog |
|---|---|---|---|---|---|---|
| 1a | BAA, **testing** (no PHI) | yes, not needed | yes, not needed | yes, not needed | yes, not needed | yes, not needed |
| 1b | BAA, **production** (PHI) | **no**: Meta "is not a Business Associate" (S1) | **no**: not on the eligible list (P2), and Meta is in the path (S1) | **no**: BAA names SMS/MMS only (P3) | **no**: no list, WhatsApp not named (P5) | **no**: no HIPAA/BAA statement (P7) |
| 2 | Edition/plan for a BAA, price | no BAA offered (S1) | Security/Enterprise Edition, price by sales (P1, T5) | US SMS only (P3) | not published (P5) | none (P7) |
| 3 | Sender options, lead time | yes: free test number (M1); production needs own number, display-name review, cap of 2 numbers until business verification (M8); lead time not published → **partial** | partial: shared sandbox number, testing only (T6) | **no**: "Limited Availability … cannot guarantee you will receive a WhatsApp account" (V3) | partial: test sender (I4) | partial: sandbox, 25 messages, one recipient (D1) |
| 4 | Signed webhooks | yes: `X-Hub-Signature-256` (M2) | yes: `X-Twilio-Signature` (T1) | yes: signed JWT (V1) | yes: HMAC `X-Hub-Signature` (I1) | **no**: not documented (D1) |
| 5 | Opt-out | partial: no keyword handling; inbound messages reach our webhook, opt-out instructions required (M6) | partial: same WhatsApp rules | partial: not documented | partial: not documented for WhatsApp | partial: not documented |
| 6 | Body retention / redaction | partial: kept at most 30 days (M5) | partial: redaction in Editions (T5) | partial: auto-redact listed for SMS (V4) | not found | not found |
| 7 | REST API, Python SDK, sandbox | partial: REST; no official Python SDK (M7); free test number (M1) | yes: REST, twilio-python (T1), sandbox (T6) | partial: SDK `vonage`; sandbox not for QA (V2) | partial: SDKs exist, test sender (I4) | partial: sandbox (D1), no SDK found |
| 8 | Status page, US processing | partial: no status page found; US processing not stated | partial: status.twilio.com; US processing not stated | not found | partial: platform status page; US processing not stated | not found |
| 9 | Price (US, utility template) | partial: per delivered message (M4); Meta utility fee from $0.0034 (T7) | partial: $0.005 + Meta fee (T7) | not found | not found | partial: from €49 per number per month + Meta fees (D2) |
| | **Result** | **Chosen for testing** | Passes for testing | **Out** (Must 3) | Passes for testing | **Out** (Must 4) |

**Production WhatsApp:** every provider fails 1b today. That's expected: P0-07a put production WhatsApp behind the `phi_gate` with SMS as fallback (DECISIONS #299). This isn't the spec §8 "no provider meets all Musts" stop.

## 4. SMS comparison
| # | Criterion | Twilio Programmable Messaging | Vonage Messages API SMS | Sinch | Infobip |
|---|---|---|---|---|---|
| 1 | BAA covers SMS (published) | **yes**: Programmable SMS on the eligible list, 2026-06-30 (P2) | **yes**: Messages API SMS/MMS, US traffic (P3) | partial: "product level" BAAs, products not named (P4) | partial: "eligible services", no list (P5) |
| 2 | Edition/plan for a BAA, price | Security or Enterprise Edition (P1); price by sales (T5) | dedicated numbers for HIPAA messaging (P3); price not found | not published | not published |
| 3 | US sender options, lead time | yes: 10DLC brand + campaign (T3), toll-free verification on a paid account (T4); lead time not published → **partial** | partial: not documented on pages read | partial: 10DLC and toll-free offered (N2) | partial: 10DLC via The Campaign Registry (I2) |
| 4 | Signed webhooks | yes: `X-Twilio-Signature` (T1) | yes: signed JWT (V1) | yes: HMAC-SHA256 on Conversation API (N1); the standalone SMS API is end of sale (N3) | yes: HMAC (I1) |
| 5 | STOP / opt-out | yes: STOP, UNSUBSCRIBE, END, QUIT, STOPALL, REVOKE, OPTOUT, CANCEL handled by default (T8); passthrough to our webhook: Verify | partial: not documented | partial: `OPT_OUT` trigger (N1) | yes: STOP creates a blocklist record (I2) |
| 6 | Body redaction | yes: body redaction in Editions (T5) | partial: auto-redact listed (V4) | not found | not found |
| 7 | REST, Python SDK, sandbox | yes: twilio-python (T1); trial account | yes: SDK `vonage` (V1) | partial: SDK not found; free trial (N2) | partial: SDKs exist; free trial with a shared test sender (I4) |
| 8 | Status page, US processing | partial: status.twilio.com; US processing not stated | not found | partial: status.sinch.com | partial: platform status page |
| 9 | US price per message | $0.0083 + carrier fees (T2) | **not confirmed** (V4) | $0.0078 + carrier fees (N2) | $0.00818 average (I3) |
| | **Result** | **Chosen** | Runner-up | **Out** (Must 1 until the product list is in writing) | **Out** (Must 1 until the product list is in writing) |

Bird was excluded in P0-07a (P6: "not … a business associate").

## 5. Choice and reasons
**Decided by Riley Tech (tech lead) on 2026-11-26.** Prices noted by Morgan Lead (sponsor).

**WhatsApp: Meta WhatsApp Cloud API, direct** (also the user's decision):
- No company between us and Meta. Production WhatsApp would need **one** BAA (Meta's), not two.
- A free test number with no business verification (M1).
- Signed webhooks (M2).
- Twilio and Infobip also pass for testing, but each adds a second vendor and fee (T7) without adding BAA coverage.

**SMS: Twilio Programmable Messaging:**
- The only provider whose published, dated eligible list names the exact product (P2).
- Default STOP handling (T8), body redaction (T5), signed webhooks and an SDK (T1).
- Vonage is the runner-up: SMS is covered, but STOP handling and the US price weren't documented in the pages read.

**Sponsor note (Morgan Lead):**
- Twilio's Security Edition price is only available from sales. It's needed only before SMS goes live, so it doesn't block testing.
- Ask for the price in writing (§6), with the 10DLC and toll-free lead times.

## 6. Questions to send in writing (human, before go-live)
| To | Question |
|---|---|
| Meta | Will Meta sign a BAA covering WhatsApp Business Platform (Cloud API) message content for US healthcare appointment messages? Request in [baa-meta-whatsapp.md](../compliance/baa-meta-whatsapp.md). |
| Twilio | Security Edition price at about 1,000–3,000 messages a month; a sample BAA; confirm Programmable Messaging (SMS) and Advanced Opt-Out are covered; typical 10DLC and toll-free review times. Request in [baa-twilio.md](../compliance/baa-twilio.md). |
| Sinch, Infobip (optional) | The written product list under your BAA: is SMS on it? |

## 7. Integration facts (for P4-01, P4-06, P4-07)

### 7.1 WhatsApp: Meta Cloud API
**Status:** sending is **proven** (live test 2026-11-26, §9). Webhook verification and signature are **documented and self-tested locally, not yet proven live** (deferred to P4-06).

| Item | Value | Evidence |
|---|---|---|
| Product | WhatsApp Business Platform, Cloud API (hosted by Meta) | M1, S4 |
| API | REST, `POST https://graph.facebook.com/v27.0/<PHONE_NUMBER_ID>/messages`, `Authorization: Bearer <token>`. Pin the version in config. | M9 |
| SDK | None official (M7). Use `httpx` (our stack) with explicit timeouts. | M7 |
| Tokens | The test token expires within hours. Production uses a system-user token (Verify in P4-01). | M1 |
| Error seen in the live test | `131030`: recipient not on the test number's allowed list | §9 |
| Webhook verification | GET with `hub.mode=subscribe`, `hub.verify_token`, `hub.challenge`. Reply 200 with the challenge when the token matches. | M2 |
| Webhook signature | Header `X-Hub-Signature-256: sha256=<hex>`: HMAC-SHA256 of the raw body with the app secret. Compare in constant time. | M2 |
| Status values | `sent`, `delivered`, `read`, `failed` (with an `errors` array); `played` is voice only. | M3 |
| Business-initiated messages | Reminders and confirmations are outside the 24-hour window, so they must be approved **templates** (utility category, S6). | M7 |
| Opt-out | No keyword handling. Inbound "STOP" arrives as a normal message, and P4-07 must recognise it and stop sending. Opt-in must name the business (P4-02). | M6 |
| Retention at Meta | Message content kept at most 30 days. | M5 |
| Limits | Free test number; production numbers capped at 2 until business verification. | M1, M8 |
| Secrets (P1-05, names only) | `whatsapp-access-token`, `whatsapp-app-secret`, `whatsapp-webhook-verify-token`. Config, not secret: `whatsapp-phone-number-id`, `whatsapp-graph-api-version`. | - |

### 7.2 SMS: Twilio Programmable Messaging
**Status: documented, not tested** (SMS is switched off; no account yet).

| Item | Value | Evidence |
|---|---|---|
| Product | Twilio Programmable Messaging (SMS) through a Messaging Service; on the HIPAA eligible list | P2 |
| BAA condition | Security or Enterprise Edition account | P1, T5 |
| SDK | `twilio-python`; use its request validator, as Twilio advises | T1 |
| Webhook signature | `X-Twilio-Signature`: HMAC-SHA1 with the auth token over the full URL plus sorted POST parameters | T1 |
| Opt-out | Default keywords handled by Twilio (T8). Whether the STOP message is also passed to our webhook: Verify in P4-07. | T8 |
| Body redaction | Available in Editions: turn it on | T5 |
| Status values | Verify in P4-01 (not checked here) | - |
| Secrets (P1-05, names only) | `twilio-account-sid`, `twilio-auth-token`, `twilio-messaging-service-sid` | - |

## 8. Sender registration steps (for P0-15)
| When | Channel | Steps | Lead time |
|---|---|---|---|
| Now | WhatsApp test | Meta developer app → WhatsApp product → test number (automatic) → add team phones as recipients → `hello_world` template. Free text (e.g. a "TEST ONLY" message) is allowed only within 24 hours after the recipient messages the number (M7). Our own templates (PHI-free drafts) go through template review. | Minutes for the test number; template review time not published |
| Before a WhatsApp clinic goes live | WhatsApp production | Business portfolio → business verification (more than 2 numbers) → own number (voice/SMS capable, not a short code) → register it via the API → display-name review → utility templates with only the `messaging_policy.yaml` fields. **Real details only after the Meta BAA.** | Not published (M8); start early |
| Before an SMS clinic goes live (or as the WhatsApp fallback) | SMS | Paid Twilio account on Security Edition → sign BAA → Messaging Service → **either** A2P 10DLC brand (Standard brands need a Tax ID) + campaign (T3) **or** toll-free verification (T4) → turn on body redaction and Advanced Opt-Out. | Not published (T3, T4); ask sales (§6) |

## 9. Test-account record (task 3)
| Item | Value |
|---|---|
| Account | The team's existing Meta app with a WhatsApp **test number**; credentials provided by the senior and kept in the user's password manager, **not in the repo** |
| Recipient list | The test number only messages numbers on its allowed list (up to 5). The first send failed with `(#131030) Recipient phone number not in allowed list` until the user's phone was added. |
| Test message | **Passed 2026-11-26:** `send_test_message.py` → HTTP 200 (accepted); the `hello_world` template arrived on a team phone |
| Signed webhook received | **Deferred to P4-06** (user decision, DECISIONS #301). Signature logic passes the local self-test (`webhook_probe.py --self-test`: right secret accepted, wrong secret rejected, verification GET handled). |
| Scripts | [send_test_message.py](../../scripts/messaging/send_test_message.py), [webhook_probe.py](../../scripts/messaging/webhook_probe.py) |
