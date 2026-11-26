# Tasks: P0-09 Clinic ↔ company BAA (issue #10)

## 1. Verify the sources (read-only)

- [x] 1.1 Re-read eCFR 45 CFR 164.504(e), 164.314(a), 164.410 and the HHS sample BAA provisions and business-associate guidance pages. Add source rows to `docs/compliance/sources/README.md` (URL, date, quote, SHA-256 or "n/a"). Verify: each required term R1–R11 and the 60-day breach limit has a source row; any citation that differs from the task spec is noted.

## 2. Documents

- [x] 2.1 Write `docs/compliance/baa/requirements-checklist.md` (v1): R1–R11 with citations, P1–P9 with proposed values, and a pass/fail/section column. Verify: 11 required and 9 proposed rows.
- [x] 2.2 Write `docs/compliance/baa/annex-a-data-and-purposes.md` (v1) from the PHI slot table, `messaging_policy.yaml`, `admin-email.md` and P0-01 Q9, plus a slot-to-row coverage table. Verify: all 11 PHI slots in the overview table map to a row (the plan said 12; the table has 11); audio and transcripts say "not stored".
- [x] 2.3 Write `docs/compliance/baa/annex-b-subcontractors.md` (v1): Google Cloud, Google Workspace, Twilio, Meta with links to their records and real status; the Open Dental relay and outside-US access as open questions. Verify: no row says signed; every link resolves.
- [x] 2.4 Write `docs/compliance/baa/commitments.md`: every R and P term → owner task → where checked; tech lead (Riley Tech) feasibility line per row. Verify: every term in the checklist has a row.
- [x] 2.5 Write `docs/compliance/baa/clinic-baa-template-v1.md` from the HHS sample provisions with our proposed terms and the annexes by reference, marked draft and not legal advice. Verify: the checklist's section column is filled from this template, and every template term has a commitments row.

## 3. Reviews and record

- [x] 3.1 (roles: Sam Comply, compliance advisor; Riley Tech, tech lead) Run the §10 checks: R1–R11 pass in the template, commitments coverage, Annex A coverage, Annex B matches the records. Record the results and review lines. Verify: each check has a result.
- [x] 3.2 (roles: Alex Sample, SME; Dr. Casey Example, signatory) Clinic reads the draft and gives comments; any requested change goes through the commitments table first. Verify: comments recorded with the response.
- [x] 3.3 Write `docs/compliance/baa-clinic-example-dental.md` in the P0-05 format: status **NOT SIGNED**, versions, signatories, counsel pending, gates, and where a real signed copy will be kept (private, not this repo). Verify: every field present; status is NOT SIGNED.

## 4. Records

- [x] 4.1 Append DECISIONS rows (next number 305): the proposed terms P1–P9 and the template base; and the deviations (no counsel, paper record NOT SIGNED, mock reviews, signed copy kept out of the public repo). Verify: the rows are present.
- [x] 4.2 Update `docs/compliance/README.md` (file table; the clinic BAA pending item; notifications for P0-10, P0-11, P0-12, P1-12, P5-12, P5-13, P5-14), the Phase 0 README #10 status, and `docs/PROJECT_MAP.md` (new and changed files). Run the public-repo scan and the link check. Verify: the scan is clean and there are no broken links.

## Workflow follow-up

- After the user has reviewed the work and given the go-ahead: archive the change (sync the `clinic-baa` spec), commit with a one-line descriptive message, push `feature/phase-0-discovery-compliance`, comment the hand-offs on issues #11 (P0-10), #12 (P0-11) and #13 (P0-12), and close issue #10 with a comment listing the files. Do none of these before the user says so.
