# Proposal: P0-09 Prepare the clinic ↔ company BAA (issue #10)

## Why

Under HIPAA the clinic (covered entity) may let us (business associate) handle its patients' PHI only if a Business Associate Agreement is in place. The clinic BAA is the last item of the PHI gate (DECISIONS #25), with the Google Cloud BAA (P0-05), the guardrails (P0-06), the messaging and email BAAs (P0-07, P0-08) and the vendor matrix (P0-10).

A BAA is also a list of **operational promises**: breach-notice deadline, return or destroy at the end, subcontractor control. Signing a promise the system can't keep is a compliance risk. So every promise must be tied to a task that implements it.

Our situation (user decision 2026-11-26): **no legal counsel is engaged yet, and no real signature is possible now.** So the documents are drafted in full, reviewed by the compliance advisor and the clinic SME, and the agreement is recorded as a **paper record, NOT SIGNED**, like the Google, Meta and Twilio records. The PHI gate stays closed.

## What Changes

- **`docs/compliance/baa/requirements-checklist.md`:** required terms R1–R11 with their 45 CFR citations (164.504(e), 164.314(a), 164.410), checked against eCFR and the HHS sample provisions during apply; our proposed terms P1–P9; a pass/fail column for reviewing any draft.
- **`docs/compliance/baa/annex-a-data-and-purposes.md`:** every PHI data category, filled from the P0-04 PHI slots (`docs/flows/overview.md`), the P0-07a messaging policy, the P0-08 email mode (`link_only`) and P0-01 Q9 (no transcripts, no audio stored). Storage locations are the planned production ones, noting that hosting is still open (DECISIONS #302).
- **`docs/compliance/baa/annex-b-subcontractors.md`:** Google Cloud, Google Workspace, Meta (WhatsApp) and Twilio (SMS), each pointing to its BAA record and its real status (all NOT ACCEPTED). The open question on Open Dental's API relay is listed for counsel.
- **`docs/compliance/baa/commitments.md`:** every promise → owner task → where it is checked, with the tech lead's feasibility sign-off (Riley Tech).
- **`docs/compliance/baa/clinic-baa-template-v1.md`:** a draft template from the HHS sample provisions plus our proposed terms and the annexes, clearly marked **draft, not legal advice, counsel review pending**.
- **`docs/compliance/baa-clinic-example-dental.md`:** the record in the P0-05 format: template version, annex versions, counterparty signatory (Dr. Casey Example, P0-01), status **NOT SIGNED**, gates, and the mock reviews (Sam Comply as compliance advisor, Alex Sample and Dr. Casey Example for the clinic).
- **Reviews (mock personas):** the §10 checks: R1–R11 present in the draft, every draft term has a commitments row, Annex A matches the PHI slot list and messaging policy, Annex B matches the existing records.
- **Records:** DECISIONS rows (proposed terms and deviations), pending notifications for P0-10, P0-11, P0-12, P1-12, P5-12, P5-13 and P5-14, and links from the READMEs and `docs/PROJECT_MAP.md`.
- **No signed PDF**, no product code, no PHI, no cloud changes.

## Capabilities

### New Capabilities
- `clinic-baa`: the requirements every clinic BAA must meet, what the annexes must list, the rule that every promise has an owner task, and the gate that keeps real PHI and the clinic's production Open Dental key out until the BAA is signed.

### Modified Capabilities
None.

## Impact

- New docs under `docs/compliance/baa/` and the record `docs/compliance/baa-clinic-example-dental.md`.
- Updated: `dental-ai-tasks/DECISIONS.md`, `docs/compliance/README.md`, `docs/compliance/sources/README.md`, `docs/phase-0-discovery-compliance/README.md`, `docs/PROJECT_MAP.md`.
- Hand-offs: P0-10 (Annex B, record), P0-11 (Annex A, commitments), P0-12 (production key only after signature), P1-12 (audit retention), P5-12 (breach notice, access requests), P5-13 (return/destroy), P5-14 (evidence).
- Acceptance criteria met only partly: signature, counsel finalization and sending to a real signatory stay pending, recorded honestly.
