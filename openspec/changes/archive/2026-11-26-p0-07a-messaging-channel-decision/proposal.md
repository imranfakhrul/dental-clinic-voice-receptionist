# Proposal: P0-07a Decide the HIPAA-compatible patient messaging channel (issue #7)

## Why

The plan assumes WhatsApp reminders are HIPAA-safe once a WhatsApp provider (BSP) signs a BAA. Meta's own terms contradict this: Meta says it is not a business associate and that the WhatsApp Business Platform is not HIPAA compliant (DECISIONS #35). A reminder from a dental clinic with the patient's name, date and time is likely PHI. So the channel and the content of every patient message must be decided in writing by the compliance advisor and the sponsor before P0-07 (provider), P0-15 (templates) and P4-01 to P4-08 (messaging features) can start.

## What Changes

- **Decision memo `docs/compliance/patient-messaging-decision.md`:**
  - the question;
  - dated, sourced facts: Meta terms §4.2, WhatsApp policy §3, Cloud API hosting, and the BAA coverage of at least 3 providers per channel considered;
  - the content of each message type;
  - options A–D compared;
  - the 5 advisor questions with written answers;
  - the signed decision per message type;
  - a record that the clinic was informed.
- **Content policy `docs/compliance/messaging_policy.yaml`:** the allowed channel per message type, the allowed fields, the never-allowed fields and the consent rules. It passes the spec §10 checks, which run as a small script.
- **Source record `docs/compliance/sources/README.md`:** URL, date checked, the quoted sentence and a SHA-256 of each fetched page. Full copies aren't committed, because the repo is public and the pages are third-party copyrighted (design decision 3).
- **Records:**
  - a DECISIONS row for the decision and any scope change against plan §2 #9–10 / §4.7;
  - a revision row for P0-01 Q8 in the clinic decision log;
  - pending notifications for P0-07, P0-15 and P4-01/02/03/07/08;
  - links from `docs/compliance/README.md`, the Phase 0 README and `docs/PROJECT_MAP.md`.
- **No code and no cloud changes.**

## Capabilities

### New Capabilities
- `patient-messaging-policy`: which channel may carry each patient message type, which fields a message may contain, which fields are never allowed, and the consent rules. Later messaging code must enforce these limits.

### Modified Capabilities
- None.

## Impact

- **New files:**
  - `docs/compliance/patient-messaging-decision.md`
  - `docs/compliance/messaging_policy.yaml`
  - `docs/compliance/sources/README.md`
  - `scripts/compliance/check_messaging_policy.py` (the spec §10 checks)
- **Edited files:**
  - `dental-ai-tasks/DECISIONS.md`
  - `docs/discovery/clinic-decision-log.md` (Q8 revision row)
  - `docs/compliance/README.md`
  - `docs/phase-0-discovery-compliance/README.md`
  - `docs/PROJECT_MAP.md`
  - `README.md` (if a new top-level link is needed)
- **Downstream:**
  - P0-07 picks the provider for the decided channel.
  - P0-15 and the P4 messaging tasks may need re-scoping if the channel isn't WhatsApp.
  - P0-09 and P0-10 take the vendor path.
- **No PHI.** Examples use field names only.
