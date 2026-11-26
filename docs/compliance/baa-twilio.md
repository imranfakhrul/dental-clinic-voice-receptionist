# Twilio BAA record

> **Status: NOT ACCEPTED.** No BAA with Twilio exists and no Twilio account is open. **No PHI may be sent through Twilio.** SMS is integrated in the design but switched off (`messaging_policy.yaml` v1.2, `enabled: false`).

| Field | Value |
|---|---|
| Vendor | Twilio Inc. |
| Agreement name | Twilio Business Associate Addendum (name to confirm in the signed text) |
| Status | **NOT ACCEPTED** (paper record, DECISIONS #293 approach; P0-07 choice DECISIONS #300) |
| Document version / date | - |
| Accepted on | - |
| Accepted by | - (a person with authority to bind the company; still to be named, as in P0-05) |
| Authority confirmed by | - |
| Scope | The products on Twilio's HIPAA Eligible Products and Services list at signing |
| Saved copy | - (decide before signing whether the PDF goes in the repo or a private drive; the repo is public) |
| Legal review of terms | **Pending** (checked 2026-11-26 in P0-11): no BAA text accepted yet and no counsel engaged. Tracked as risk R29 ([risk register](risk/risk-register.md)); record "done YYYY-MM-DD by <name>" here when counsel has reviewed the accepted text. |
| Covered products relied on | **Programmable SMS** (Programmable SMS Basics, Long Codes, Toll-free, Advanced Opt-out), from the [HIPAA Eligible Services list](https://twil.io/HIPAA-eligible-products-and-services), last updated 2026-06-30 (P2, SHA-256 `c287de06…1b38`). The signed BAA must name or incorporate this list. WhatsApp through Twilio is **not** on it. |
| Edition/plan required for BAA | **Security Edition or Enterprise Edition** (P1). Price only from sales (T5). |
| Channels allowed by P0-07a | SMS: production channel for clinics that choose it, and fallback for WhatsApp clinics (`allowed_with_phi: true` once this record says ACCEPTED). `messaging_policy.yaml` decision_version 1.2 |
| Settings to turn on | Message body redaction (T5), Advanced Opt-Out (T8), a dedicated sending number |

## Written request to send (human, before SMS go-live)
> Subject: HIPAA BAA and Security Edition for Programmable Messaging (US SMS)
>
> We plan to send appointment confirmations and reminders for US dental clinics through Programmable Messaging (US long code or toll-free), about 1,000–3,000 messages a month at first.
>
> 1. Please send the Security Edition price and a sample BAA.
> 2. Please confirm that Programmable SMS and Advanced Opt-Out are covered under the BAA.
> 3. What are the typical review times for A2P 10DLC brand and campaign registration, and for toll-free verification?

## Gates before any real PHI through Twilio
- [ ] Security or Enterprise Edition account opened, and this BAA signed by both parties and recorded (above).
- [ ] The Google Cloud BAA is accepted ([baa-google-cloud.md](baa-google-cloud.md)).
- [ ] The clinic ↔ company BAA names Twilio as a subcontractor (P0-09).
- [ ] The vendor matrix lists Twilio with this record (P0-10).
- [ ] Sender registered (10DLC or toll-free, P0-15), body redaction on, and `sms.enabled: true` with a DECISIONS row.

## Review
Reviewed by Sam Comply (compliance advisor), 2026-11-26: "The exact product (Programmable SMS) and the edition condition are named. While this record says NOT ACCEPTED, no PHI may go to Twilio."
