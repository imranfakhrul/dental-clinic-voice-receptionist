# Meta (WhatsApp Business Platform) BAA record

> **Status: NOT ACCEPTED.** No BAA with Meta exists, and Meta's terms currently say it **is not a business associate** (S1). **No PHI may be sent over WhatsApp.** WhatsApp is used only for testing, with synthetic content sent to team phones (`messaging_policy.yaml` v1.2, `testing_only` use).

| Field | Value |
|---|---|
| Vendor | Meta Platforms, Inc. (WhatsApp Business Platform) |
| Agreement name | - (no BAA offered; to be requested, below) |
| Status | **NOT ACCEPTED** (paper record, DECISIONS #293 approach; P0-07 choice DECISIONS #300) |
| Document version / date | - |
| Accepted on | - |
| Accepted by | - (a person with authority to bind the company; still to be named, as in P0-05) |
| Authority confirmed by | - |
| Scope | - |
| Saved copy | - (decide before signing whether the PDF goes in the repo or a private drive; the repo is public) |
| Legal review of terms | **Pending** (checked 2026-11-26 in P0-11): no BAA text accepted yet and no counsel engaged. Tracked as risk R29 ([risk register](risk/risk-register.md)); record "done YYYY-MM-DD by <name>" here when counsel has reviewed the accepted text. |
| Covered products relied on | **WhatsApp Business Platform Cloud API** message content and metadata. Today Meta's terms §4.2 say Meta "is not a Business Associate or Subcontractor" and the platform "is not HIPAA compliant" (S1, page modified 2026-09-23). |
| Edition/plan required for BAA | - (none offered) |
| Channels allowed by P0-07a | WhatsApp: testing only, synthetic data (`allowed_with_phi: false`). Production WhatsApp only after this record says ACCEPTED (`phi_gate`), else SMS fallback. `messaging_policy.yaml` decision_version 1.2 |
| Provider in the path | None besides Meta (Cloud API direct, [messaging-provider.md](../integrations/messaging-provider.md)) |

## Written request to send (human, before go-live)
> Subject: Business Associate Agreement for WhatsApp Business Platform (Cloud API), US healthcare
>
> We are building appointment confirmations and reminders for US dental clinics, which are HIPAA covered entities, using the WhatsApp Business Platform Cloud API directly. The messages would contain a patient's first name, the clinic name, and the appointment date and time.
>
> 1. Will Meta sign a Business Associate Agreement covering WhatsApp Business Platform (Cloud API) message content and metadata for this use?
> 2. If yes, please send the agreement text, and confirm that it overrides §4.2 of the Meta Terms for WhatsApp Business Platform for our account.
> 3. If no, please confirm in writing that no BAA is available.

Accept only if the agreement **explicitly** covers Cloud API message content, and only after legal review (P0-11). If Meta declines, record the answer here and keep WhatsApp clinics on SMS (DECISIONS #299).

## Gates before any real PHI on WhatsApp
- [ ] This BAA is signed by both parties and recorded (above).
- [ ] The Google Cloud BAA is accepted ([baa-google-cloud.md](baa-google-cloud.md)).
- [ ] The clinic ↔ company BAA names Meta as a subcontractor (P0-09).
- [ ] The vendor matrix lists Meta with this record (P0-10).
- [ ] `messaging_policy.yaml` is changed to `allowed_with_phi: true` for WhatsApp, with a DECISIONS row.

## Review
Reviewed by Sam Comply (compliance advisor), 2026-11-26: "The product is named exactly (Cloud API message content). While this record says NOT ACCEPTED, no PHI may go to Meta; testing with synthetic content to team phones is acceptable."
