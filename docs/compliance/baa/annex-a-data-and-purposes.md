# Annex A: data and purposes (v1)

> Draft, not legal advice. Part of [template v1](clinic-baa-template-v1.md). Version v1, 2026-11-26. Describes data **categories**, never real data.

**Where stored** is the planned production setup on Google Cloud (US regions only, P0-06). Hosting is still open until the client chooses (DECISIONS #302). If production runs elsewhere, this annex and [Annex B](annex-b-subcontractors.md) change before any PHI flows (template 7.2).

**Retention** values come from the P5-12 retention policy (DECISIONS #278; Proposed, advisor to verify).

## A.1 Data categories
| # | Data category | Examples | Purpose | Where stored | Sent to (subcontractor) | Retention |
|---|---|---|---|---|---|---|
| A1 | Identifiers | First and last name, date of birth, phone, mobile phone, email, address, ZIP | Find or register the patient in Open Dental; verify identity; callbacks | Encrypted session state in Redis (session TTL, P2-01); encrypted callback fields in Cloud SQL (P1-03, P1-05); **never** a copy of the patient record (Open Dental is the record) | Google Cloud (Gemini for extraction, Speech-to-Text, Text-to-Speech, hosting) | Session: TTL. Callback fields: blanked 90 days after the case is resolved |
| A2 | Open Dental references | `PatNum`, `AptNum` | Link our records to the clinic's records | Cloud SQL (`appointment_refs`, `sessions`) | Google Cloud (hosting) | 1 year after last update |
| A3 | Visit reason and situation | Visit-reason text, callback situation description, emergency description | Book the right appointment type; callbacks; emergency escalation | Encrypted session state; encrypted callback summary in Cloud SQL | Google Cloud | Session: TTL. Callback: blanked 90 days after resolved |
| A4 | Messaging contact and consent | WhatsApp or SMS number, consent records | Appointment confirmations and reminders (only first name, clinic name, date, time, clinic phone in messages, per `messaging_policy.yaml`) | Cloud SQL (encrypted contact preferences, `consents`, message metadata) | The messaging provider for the clinic's chosen channel (Annex B) | Contact preferences: while consent is active, 1 year after revoked. Consents: 6 years. Message metadata: 1 year |
| A5 | Callback emails | Default `link_only`: urgency, random case ID and link, **no PHI**. `full_details` only with written advisor approval | Tell the clinic's admin about a callback case | `link_only`: nothing. `full_details`: the sender's Sent folder | Google Workspace (Gmail) | `full_details`: Sent items deleted after 30 days (Proposed, P0-08) |
| A6 | Voice audio | The patient's speech | Speech recognition | **Not stored**: streamed to Speech-to-Text and discarded | Google Cloud (Speech-to-Text) | None |
| A7 | Transcripts | Conversation text | Quality review | **Not stored** (P0-01 Q9). Only the last few turns live in the encrypted session state for the conversation itself | Google Cloud (Gemini, within the session) | 0 days; at most 30 if the pilot enables it (P6-04), which needs an Annex A change first |
| A8 | Audit log | Actions with object references (IDs, codes, timestamps), no free-text PHI | Security and compliance evidence | Cloud SQL `audit_log` plus a PHI-free copy in a protected log bucket (P1-07) | Google Cloud | 6 years (Proposed; counsel to verify) |

**Not collected:** insurance details (P0-01 Q6), clinical notes, diagnoses, payment data.

**Backups:** encrypted Cloud SQL backups hold A1–A4 and A8 for up to 30 daily backups (P1-03). They expire on that schedule (template 5.3).

## A.2 Coverage check (PHI slots → rows)
Source: the PHI column of the slot table in [docs/flows/overview.md](../../flows/overview.md). 11 PHI slots, all covered; no row invented without a source.

| PHI slot | Collected in | Annex A row |
|---|---|---|
| `first_name` | `IDENTIFY`, `EMERGENCY`, `CALLBACK_REQUEST` | A1 |
| `last_name` | `IDENTIFY`, `CALLBACK_REQUEST` | A1 |
| `dob` | `IDENTIFY` | A1 |
| `phone` | `IDENTIFY`, `EMERGENCY`, `CALLBACK_REQUEST` | A1 |
| `zip` | `VERIFY` | A1 |
| `email` | `REGISTER` | A1 |
| `address` | `REGISTER` | A1 |
| `mobile_phone` | `REGISTER` | A1 |
| `reason_text` | `APPOINTMENT_TYPE` | A3 |
| `whatsapp_number` | `CONSENT` | A4 |
| `situation` | `EMERGENCY`, `CALLBACK_REQUEST` | A3 |

| Other source | Annex A row |
|---|---|
| `apt_num` slot and Open Dental `PatNum` (not PHI slots by themselves, but linkable to a patient) | A2 |
| `messaging_policy.yaml` message fields and consent | A4 |
| [admin-email.md](../../integrations/admin-email.md) content modes | A5 |
| P0-01 Q9 (no transcripts, no audio) | A6, A7 |
| P1-07 / P5-12 audit log | A8 |

Re-run this check whenever the slot table changes (spec requirement "Annex A matches the data we actually handle").
