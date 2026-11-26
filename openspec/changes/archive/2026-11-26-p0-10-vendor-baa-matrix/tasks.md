# Tasks: P0-10 Vendor/BAA matrix (issue #11)

## 1. Data

- [x] 1.1 Write `docs/compliance/vendors.schema.json` exactly as in the task spec §6. Verify: it loads as Draft 2020-12 (`jsonschema.Draft202012Validator.check_schema`).
- [x] 1.2 Write `docs/compliance/vendors.yaml` with rows google-cloud, google-workspace, twilio, meta-whatsapp, open-dental, github, ai-coding-assistant; clinic `example-dental`; gate items gcp_baa, guardrails, clinic_baa, matrix. Statuses copied from the five BAA records on the day. (Role: Sam Comply as reviewer.) Verify: every status matches its record's first line.

## 2. Checker and tests

- [x] 2.1 Write `scripts/compliance/check_vendors.py`: C1–C9, gate logic with the `Exception DECISIONS #n` rule for the product list, `--render`, `--gate`; prints vendor IDs and paths only. Verify: under ~250 lines; `python3 scripts/compliance/check_vendors.py` runs.
- [x] 2.2 Write `scripts/compliance/test_check_vendors.py` with the spec §10 cases (plus: covered-list exception accepted, `no` without exception closes the gate). Run in a scratchpad virtual environment with pytest. Verify: all tests pass.
- [x] 2.3 Render `docs/compliance/vendor-matrix.md` and run `--gate`. Verify: validate exits 0; `--gate` prints CLOSED with the expected reasons (exit 2); Workspace shows "PHI blocked for this vendor".

## 3. Docs

- [x] 3.1 Write `docs/compliance/pr-vendor-check.md` (PR checklist text from spec §6) with the proposed CODEOWNERS entries as text, marked not active. Verify: no `.github/CODEOWNERS` file exists.
- [x] 3.2 Update `docs/compliance/README.md`: file table rows, "How to add a vendor", the review routine, the checker commands, and the "Vendor matrix" pending item. Verify: links resolve.

## 4. Records

- [x] 4.1 Append DECISIONS rows (next number 307): matrix design (two messaging rows, product-list exception rule, team-tool rows); deviations (no CODEOWNERS file by user decision, P1-01/P1-06 issues don't exist so hand-offs go in the README, mock reviewer). Verify: rows present.
- [x] 4.2 Update the Phase 0 README #11 status and `docs/PROJECT_MAP.md` (new and changed files); add pending notifications for P1-01, P1-06 in `docs/compliance/README.md`. Run the public-repo scan and the link check. Verify: scan clean, no broken links.

## Workflow follow-up

- After the user has reviewed the work and given the go-ahead: archive the change (sync the `vendor-baa-matrix` spec), commit with a one-line descriptive message, push `feature/phase-0-discovery-compliance`, comment the hand-offs on issues #12 (P0-11) and #13 (P0-12), and close issue #11 with a comment listing the files. Do none of these before the user says so.
