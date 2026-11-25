# Tasks: P0-01 Discovery workshop (issue #1)

Tasks marked **(human)** can't be done by an agent. Leave them unchecked until a person completes them.

## 1. Discovery documents (repo)

- [x] 1.1 Create `docs/discovery/pre-read.md` from plan §1–§2. Verify: at most 2 pages; covers what the AI does and does not do, "no live transfer", the callback flow and the no-patient-data rule; uses only made-up examples.
- [x] 1.2 Create `docs/discovery/questionnaire.md` with Part A (Q1–Q11 plus Q4a/Q4b) and Part B (B1–B8), each with its Proposed default and "Feeds tasks", copied exactly from spec §6. Verify: 20 IDs, none renumbered, and the `Verify:` marker on B2 is kept.
- [x] 1.3 Create `docs/discovery/clinic-decision-log.md` as a template. It needs the §6 header, a table with one row per question ID (placeholders only) and the status legend, plus the sections "Requests outside MVP", "Revisions after sign-off" and "Pending notifications". Verify: it contains no real names or contacts.
- [x] 1.4 Create `docs/discovery/review-checklist.md` from spec §10, including the no-PHI check and the "differs from default" check. Verify: every item in spec §10 appears.
- [x] 1.5 Create `docs/discovery/README.md` covering the folder's purpose, the 90-minute agenda (15 / 45 / 20 / 10 minutes) and the workshop rules (no PHI, no live Open Dental screens, record the meeting only if everyone consents). Verify: the README links to all four files above.
- [x] 1.6 Create the root `README.md` with a one-paragraph project summary and links to `CLAUDE.md`, `dental-ai-tasks/` and `docs/discovery/clinic-decision-log.md`. Verify: the links resolve on GitHub.

## 2. Preparing for the workshop (human)

- [x] 2.1 (human) Name the SME, the Open Dental admin, the dentist/owner and the BAA signatory, and enter them in the log header.
- [ ] 2.2 (human) Send the pre-read and questionnaire to the clinic at least 3 business days before the workshop. Verify: the date sent is recorded on issue #1.

## 3. Workshop and sign-off (human)

- [x] 3.1 (human) Run the 90-minute workshop and fill in the log live, reading back each answer. Verify: every Part A row is `Answered` or `Agreed default`, and every Part B row is answered or `Blocked` with an owner, a due date and the task that needs it.
- [x] 3.2 (human) A second team member completes `review-checklist.md`, including the no-PHI check, and records this in writing on issue #1.
- [x] 3.3 (human) Send version 1.0 to the SME and save their written approval as `signoff-YYYY-MM-DD.pdf` in `docs/discovery/`.
- [ ] 3.4 (human) Post each answer as a comment on the issue of every surviving task in "Feeds tasks" (use `_CONSOLIDATION.md` to find them). For phases without issues yet, add the answer to "Pending notifications". Verify: every Phase 0 issue that is fed has its comment.
- [x] 3.5 (human) Pass any requests outside the MVP to the tech lead. Verify: they are listed in the log.

## 4. Finish

- [x] 4.1 After sign-off, set the log's version to 1.0 and add the approval line to its header. Verify: the header links to `signoff-YYYY-MM-DD.pdf`.
- [ ] 4.2 Commit with a one-line message and ask the user before pushing `feature/phase-0-discovery-compliance`. Verify: `git log -1 --format=%s` is one line and nothing was pushed without approval.

## Workflow follow-up

- The senior merges into `main`. After that, run `/opsx:archive p0-01-discovery-workshop` and close issue #1.
