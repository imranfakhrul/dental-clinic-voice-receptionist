# Opt-in, HELP and STOP texts, and clinic website texts

Version 1, 2026-11-26 (P0-15). Wording reviewed by Sam Comply (compliance advisor, mock) on 2026-11-26. **P4-02 uses the consent text verbatim**; any change goes through the compliance advisor and updates this file, `templates.yaml` and, for SMS, the carrier campaign's `message_flow`.

Placeholders in `<angle brackets>` are filled from clinic config at onboarding (P1-19). Facts: sources M2–M4, M8 in [sources/README.md](../compliance/sources/README.md#p0-15-messaging-templates-and-registration-checked-2026-11-26).

## 1. Consent checkbox (widget, unchecked by default)
Shown when the patient books, next to the field for the messaging number. The patient can book without ticking it.

```text
[ ] Send me appointment confirmations, a reminder before my visit, and notices if it changes, from <Clinic name>,
    by <text message | WhatsApp> to the number I gave. Up to 4 messages per appointment. Msg & data rates may apply.
    Reply STOP to opt out, HELP for help. Consent is not required to book.
    <RISK NOTICE>
    Privacy: <privacy URL> · Terms: <SMS terms URL>
```

`<RISK NOTICE>`: `messaging_policy.yaml` sets `risk_notice_required: true`, so P4-02 inserts the advisor-approved risk sentence here. That sentence is owned by the policy (wording owner P4-02, approval by the compliance advisor), not by this file.

## 2. Keyword replies
The texts live in `templates.yaml` → `system_replies` (checked by rule T11: only clinic name and phone).

| Channel | Keyword | Who sends the reply | Text |
|---|---|---|---|
| SMS | STOP (and UNSUBSCRIBE, END, QUIT, STOPALL, REVOKE, OPTOUT, CANCEL) | Twilio by default (M8); later sends fail with error 21610 until START | Twilio's default, or `system_replies.sms.stop_confirmed` if Advanced Opt-Out is turned on |
| SMS | START, UNSTOP | Twilio by default | Twilio's default |
| SMS | HELP | Twilio by default, or our text | `system_replies.sms.help` |
| WhatsApp | STOP | P4-01 (WhatsApp has no carrier-level keywords) | `system_replies.whatsapp.stop_confirmed` |
| WhatsApp | START | P4-01 | `system_replies.whatsapp.start_confirmed` |
| WhatsApp | HELP | P4-01 | `system_replies.whatsapp.help` |
| WhatsApp | any other text | P4-01 | `system_replies.whatsapp.auto_reply` |

## 3. Clinic website texts (the clinic publishes them; needed before SMS campaign registration)
Carrier review checks these pages: both must be public (no login), on the clinic's own domain (M3).

### 3.1 SMS terms page (`https://<clinic website>/sms-terms`)
```text
<Clinic name> appointment messages

Program: <Clinic name> sends appointment messages to patients who opt in when they book with the online
assistant on our website.

Messages you get: a booking confirmation, a reminder about one hour before your visit, and a notice if a visit
is moved or cancelled. No marketing.

How often: up to 4 messages per appointment.

Cost: Message and data rates may apply.

Opt out: reply STOP to any message. You'll get one confirmation and no more messages. Reply START to resubscribe.

Help: reply HELP, or call us at <clinic phone>.

Carriers are not liable for delayed or undelivered messages.

Privacy: see our privacy policy at <privacy URL>.
```

### 3.2 Privacy policy paragraph (add to the clinic's privacy policy)
```text
Appointment text messages. If you agree to receive appointment messages, we use your mobile number only to send
them. Mobile numbers and text-messaging consent are not shared with third parties or affiliates for marketing
or promotional purposes. You may receive up to 4 messages per appointment. Message and data rates may apply.
Reply STOP to opt out or HELP for help.
```

These include what carrier review requires of a privacy policy (M3): mobile numbers aren't shared with third parties, message frequency, and "Message and data rates may apply".

## 4. Review
| Reviewer | Date | Result |
|---|---|---|
| Sam Comply (compliance advisor, mock) | 2026-11-26 | Lock-screen read-aloud of all 8 rendered examples: no reason, service, provider or clinical word; consent is optional and unchecked; risk notice slot kept for the policy sentence |
| Alex Sample (office manager, mock) | 2026-11-26 | Website texts accepted for Example Dental; publishing waits for the real clinic website (registration record) |
