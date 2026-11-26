# Proposal: P0-01 Discovery workshop with the pilot clinic (GitHub issue #1)

## Why

The product's rules come from the clinic, not from us. Examples: who counts as verified, what the AI may book, how emergencies are handled, where callback emails go, and how long transcripts are kept.
P0-01 is the root of the task graph. Until its answers are signed off, seven Phase 0 tasks are blocked: P0-02, P0-03, P0-04, P0-07, P0-08, P0-09 and P0-12.
Without these answers, later phases would hard-code guesses that are expensive to undo.

Source of truth: `dental-ai-tasks/tasks/P0-01 Run discovery workshop with pilot clinic.md` (approved).

## What Changes

**Repo deliverables (done by the agent or a developer):**
- `docs/discovery/pre-read.md` is a plain-language summary for the clinic, at most 2 pages:
  - what the AI does and does not do;
  - what "no live transfer" means and how the callback flow works;
  - the rule "no real patient data until the BAA is signed".
- `docs/discovery/questionnaire.md` holds every Part A question (Q1–Q11, with Q4a/Q4b) and Part B question (B1–B8).
  - Each question has its Proposed default, so the clinic can confirm a default instead of answering from scratch.
  - The question IDs are fixed and must never be renumbered.
- `docs/discovery/clinic-decision-log.md` is a ready-to-fill template in the spec's §6 format:
  - a header naming the SME, the Open Dental admin and the BAA signatory;
  - one row per question ID;
  - a "Requests outside MVP" section;
  - a section for revisions after sign-off.
- `docs/discovery/review-checklist.md` is the reviewer checklist from spec §10, including the no-PHI check.
- `docs/discovery/README.md` explains what the folder is and the workshop process. The repo root gets a new `README.md` that links to the decision log.

**Human steps (tracked as `(human)` tasks; the agent cannot do them):**
- Confirm the pilot clinic and name its four contacts: SME, Open Dental admin, dentist/owner and BAA signatory.
- Send the pre-read and questionnaire at least 3 business days before the workshop.
- Run the 90-minute workshop and fill in the log live.
- Get the SME's written approval of version 1.0, saved as `signoff-YYYY-MM-DD.pdf`.
- Have a second person confirm that no PHI is present.
- Comment each answer on the GitHub issues of the tasks it affects.

No application code, infrastructure or system behavior changes.

## Capabilities

### New Capabilities
- None. This change produces process documents only. No system behavior is specified, so `.openspec.yaml` sets `skip_specs: true`.

### Modified Capabilities
- None.

## Impact

- **New files:** `docs/discovery/*` and the root `README.md`. These are the first files outside `dental-ai-tasks/`. P1-01 later adds the rest of the monorepo around them and keeps them unchanged.
- **Downstream:** the decision log is cited as "P0-01 Q<n>" or "P0-01 B<n>" by P0-02, P0-03, P0-04, P0-07a/P0-07, P0-08, P0-09 and P0-12, and by P1-16, P1-19, P2-14 and P2-15.
- **Privacy:** no PHI anywhere, because no BAA exists yet (P0-09 comes after this task). The log header holds only clinic staff's work contact details, which are not PHI.
