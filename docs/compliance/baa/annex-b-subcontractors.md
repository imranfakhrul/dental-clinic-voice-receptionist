# Annex B: subcontractors (v1)

> Draft, not legal advice. Part of [template v1](clinic-baa-template-v1.md). Version v1, 2026-11-26.

Under template 3.4, **no PHI goes to a subcontractor until its BAA is in effect.** Today **none** is: every record below says NOT ACCEPTED. All work uses synthetic data only.

| # | Subcontractor | Services | Receives PHI? | BAA | Status (2026-11-26) | Record |
|---|---|---|---|---|---|---|
| B1 | Google Cloud | Hosting, database, Redis, Gemini on Vertex AI, Speech-to-Text, Text-to-Speech, logging (US regions only) | Yes (Annex A rows A1–A4, A6–A8) | Google Cloud Platform HIPAA Business Associate Addendum | **NOT ACCEPTED** (pending) | [baa-google-cloud.md](../baa-google-cloud.md) |
| B2 | Google Workspace | Admin callback emails (Gmail) | Only in `full_details` mode (A5); none in the default `link_only` | Google Workspace HIPAA Business Associate Amendment | **NOT ACCEPTED** (pending; no Workspace until production) | [baa-google-workspace.md](../baa-google-workspace.md) |
| B3 | Twilio | SMS confirmations and reminders, **if the clinic chooses SMS** | Yes, minimal (A4: first name, date, time) | Twilio BAA (needs Security or Enterprise Edition) | **NOT ACCEPTED** (pending; request drafted) | [baa-twilio.md](../baa-twilio.md) |
| B4 | Meta (WhatsApp Cloud API) | WhatsApp confirmations and reminders, **if the clinic chooses WhatsApp** | Yes, minimal (A4) | Meta BAA | **NOT ACCEPTED** (pending; Meta's terms say it isn't a business associate) | [baa-meta-whatsapp.md](../baa-meta-whatsapp.md) |

**Only the messaging subcontractor for the clinic's chosen channel is used** (P0-07a). Until its BAA is in effect, a clinic that chose WhatsApp uses SMS or waits (`messaging_policy.yaml`). The clinic's choice is written into its record.

**Not subcontractors:**
- Mailpit (a local test mail catcher, synthetic data only, never production).
- Development tools that never see PHI.

## Open questions
| Question | Owner | Effect |
|---|---|---|
| Open Dental's API requests pass through Open Dental's servers to the clinic's eConnector (P0-01 B1). Is that relay covered by the clinic's own arrangement with Open Dental, or must it be listed here? | Counsel | If it must be listed: add row B5 and its BAA record before any PHI flows |
| Will anyone access production PHI from outside the United States (support or engineering)? | Sponsor + tech lead | Fills template 3.11 (term P6). If yes, the named roles are listed here |

## Changes
A new subcontractor, or a change in what an existing one receives, needs:
1. a BAA record with status ACCEPTED;
2. written notice to the clinic at least 30 days before the first PHI flows (template 3.4.2);
3. a new version of this annex.
