# Design: P0-10 Vendor/BAA matrix

## Context
See proposal.md (Why). Facts that shape the approach:
- Five BAA records exist, all **NOT ACCEPTED / NOT SIGNED**: `baa-google-cloud.md`, `baa-google-workspace.md`, `baa-twilio.md`, `baa-meta-whatsapp.md`, `baa-clinic-example-dental.md`.
- `infra/org/allowed_services.yaml` (P0-06) has a `services` list for dev/staging/prod (16 APIs, one `hipaa_covered: no`: `servicenetworking`, exception DECISIONS #295) and a separate `ops_services` list (ops never holds PHI).
- The repo belongs to a personal GitHub account: no teams, so CODEOWNERS could only name users. **User decision 2026-11-26: no `.github/CODEOWNERS` now.**
- Only P0 issues exist on GitHub; P1-01 and P1-06 have no issue yet.
- Python has `pyyaml` 6.0.3 and `jsonschema` 4.19.2; `pytest` is not installed.

## Goals / Non-Goals
**Goals:** a single command that answers "may real PHI enter prod?"; checks that catch the mistakes listed in the spec; a rendered matrix humans can read.

**Non-Goals:** CI wiring (P1-06), the PR template file (P1-01), signing anything, re-checking Google's covered list (P0-06 owns it).

## Decisions
1. **Schema as in the task spec, unchanged.** It is the contract P1-06 and P5-14 rely on. Twilio and Meta fit it as two vendor rows; no schema change is needed.
2. **Two messaging rows, both `phi: "yes"` in prod.** The clinic picks one channel at go-live, so whichever is used must be signed. Both are listed now because both are integrated (P0-07a). When a clinic's channel is known, the unused one can move to `phi: "no"` with a control ("channel disabled for all clinics").
3. **Open Dental relay: `under_review`, `clinic_arrangement`.** As in the spec. Counsel's answer (P0-09 open question) decides the next status. If Open Dental needs its own BAA, the row becomes `signed` with that record. If the clinic's own arrangement covers it, the row becomes `signed` with `type: clinic_arrangement` and a record file showing it. `not_required` is never allowed while `phi: "yes"` (rule C4).
4. **Product-list gate rule with exceptions.** The spec says every prod API must be `hipaa_covered: yes`. `servicenetworking` is `no` by a recorded exception (control plane, never carries PHI). The checker accepts `no` only when the API's `notes` cite `Exception DECISIONS #<n>`; any other `no` or `verify` closes the gate and is named. Only the `services` list counts (it covers prod); `ops_services` is ignored because ops never holds PHI.
5. **Team tools.** Spec §14 asks about team tools that may see PHI by accident. Added: GitHub (spec row) and our AI coding assistant (reads the repo and terminal; `phi: "no"`, control: synthetic data only, no PHI in repo or terminal). Not vendors: Mailpit (local container), Docker Hub (image pulls only, no data sent), the Meta test phone numbers (covered by the Meta row). The temporary webhook tunnel planned in P0-07 was never used (test deferred to P4-06); P4-06 adds a row if it uses one.
6. **Checker shape.** One file, standard library plus `yaml` and `jsonschema`, no network, under ~250 lines: `load → validate (C1) → rules C2–C7, C9 → gate → render`; C8 compares the committed matrix with the render output. The render uses a fixed date from `reviewed_on` (not "today"), so C8 is stable between days.
7. **Tests in a throwaway virtual environment.** `python3 -m venv` in the session scratchpad, `pip install pytest pyyaml jsonschema`, run `pytest scripts/compliance/`. Nothing is installed system-wide and nothing is added to the repo except the test file. Fixtures are built in `tmp_path`, so tests never touch the real files.
8. **CODEOWNERS as text.** The spec's entries are written in `pr-vendor-check.md` under "Proposed CODEOWNERS (not active)", with the note that a personal-account repo can name only users and that branch protection must require code-owner review for it to block merges. Logged as a deviation.
9. **Reviewer.** `reviewed_by: "Sam Comply (compliance advisor)"` (mock persona, the same compliance owner used in P0-05 to P0-09); the sponsor still has to name the real compliance owner (spec §14).

## Risks / Trade-offs
- [The gate is only as good as the YAML] → Rules C3/C7 tie `signed`/`done` to files that exist; the quarterly review re-reads the records.
- [Exception parsing via notes is loose] → The pattern is exact (`Exception DECISIONS #\d+`) and the test suite covers both a valid exception and a `no` without one.
- [No CODEOWNERS or CI yet] → Until P1-01/P1-06, the checker runs locally and in review; the README says so.

## Migration Plan
Not applicable (new files).

## Open Questions
- Who is the real compliance owner? (sponsor; changes only `reviewed_by`)
- Does the Open Dental relay need its own BAA? (counsel; changes only that row)
