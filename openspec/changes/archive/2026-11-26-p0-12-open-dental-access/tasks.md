# Tasks: P0-12 Open Dental access and test database (issue #13)

## 1. Facts (read-only)

- [x] 1.1 Fetch Open Dental's apisetup, apipermissions, apiimplementation, apilocal and apispecification pages; confirm the hosted test DB, auth header, permission groups and tiers, rate limits and error codes, minimum versions (Remote API, the methods we need vs the clinic's 24.3), and the exact GET paths for the smoke test. Add source rows to `docs/compliance/sources/README.md` without copying the published credentials. Verify: each fact used has a row.

## 2. Documents and data

- [x] 2.1 Write `docs/integrations/open-dental-access.md`: API mode, auth, permissions to request (Patients create only), tier and fees (Verify), rate limits, version notes, keys and secrets plan (local `.env` now, Secret Manager later), customer-key list (no values), the vendor-relations email draft (not sent), and placeholders for the smoke-test results. Verify: every spec §6 item has a value, a Verify marker or "pending".
- [x] 2.2 Write `.env.example` (placeholders only) and confirm `.env` is git-ignored. Verify: `git check-ignore .env` succeeds; `.env.example` has no values.
- [x] 2.3 Write `infra/dev/open-dental-test-db/seed/seed_patients.csv` (≥30 fictional patients covering the spec §6 cases), `seed_setup.md`, and `docs/integrations/open-dental-test-data.md`. Verify: every case in the spec table has at least one row; all phones are `555-01xx`.
- [x] 2.4 Write `docs/integrations/open-dental-test-db.md`: test DB (B) design, both possible homes, reset procedure, status **pending**. Verify: the pending reasons are listed.

## 3. Scripts and the hosted test

- [x] 3.1 Write `scripts/open_dental/seed_test_db.py` (CSV validation with `--dry-run`; refuses hosted and non-`testdb` targets). Run `--dry-run` and a refusal case. Verify: dry run passes; hosted target is refused without any request.
- [x] 3.2 Write `scripts/open_dental/smoke_test.py` (read-only; counts and IDs only). Test offline with a mocked server (status, wrong key, 429). Verify: the mocked run passes and prints no names or DOBs.
- [ ] 3.3 (human-assisted) Put the published hosted credentials in the local `.env` (user, own terminal), **ask before** running `smoke_test.py --target hosted` once, and record the results (statuses, counts, wrong-key status, latencies, 429 behaviour) in `open-dental-access.md`. Verify: results recorded; no key in the output or repo. **Deferred by the user (2026-11-26):** keys to be added later; how to run it is in `open-dental-access.md` §8. Left unticked.

## 4. Records

- [x] 4.1 Append DECISIONS rows (next number 312): rate limits and Patients-create-only refinement of #62; deviations (no email sent, no developer key, test DB (B) and seed load pending, local `.env` instead of Secret Manager, clinic key pending the BAA). Update the Open Dental row notes in `vendors.yaml` if facts changed, and re-render. Verify: rows present; `check_vendors.py` passes.
- [x] 4.2 Update `docs/compliance/README.md` (pending items and notifications for P1-15, P1-16, P1-20, P3-15, P1-06, P0-02, P0-10, P0-11), the Phase 0 README #13 status, and `docs/PROJECT_MAP.md`. Run the public-repo scan, a key scan (`git grep -n "ODFHIR "`), and the link check. Verify: clean.

## Workflow follow-up

- After the user has reviewed the work and given the go-ahead: archive the change (sync the `open-dental-access` spec), commit with a one-line descriptive message, push `feature/phase-0-discovery-compliance`, comment the hand-offs on issue #3 if still open (P0-02) or skip, and close issue #13 with a comment listing the files. Do none of these before the user says so.
