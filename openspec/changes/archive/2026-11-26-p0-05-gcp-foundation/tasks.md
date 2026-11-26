# Tasks: P0-05 Google Cloud foundation and BAA record (issue #5)

## 1. Tooling and pre-flight (read-only)

- [x] 1.1 Install the Google Cloud CLI in the scratchpad from Google's official Linux archive. Verify: `gcloud --version` prints a version.
- [x] 1.2 (human) The user logs in by typing `! <scratchpad>/google-cloud-sdk/bin/gcloud auth login`. Verify: `gcloud auth list` shows one active account. Its email isn't written anywhere in the repo.
- [x] 1.3 Pre-flight, read-only:
  - `gcloud organizations list` (expect none, which confirms the personal account);
  - the billing accounts (the user picks one if there are several);
  - the project quota;
  - whether `dai-rcpt-{dev,staging,prod,ops}` are free.

  Verify: the results are shown to the user, with a plan of the exact commands to run next.

## 2. Create the resources (each step only after the user says yes)

- [x] 2.1 Create the four projects with labels `env=<env>` and `system=dental-ai`. Verify: all four are listed with both labels.
- [x] 2.4 Set essential contacts on each of the four projects (the account owner's email) for security, technical, billing, legal and suspension. Verify: each project lists all five categories.

## 3. Test with synthetic data

- [x] 3.1 Run the spec §10 checks, adapted to a setup without an organization. List the APIs enabled in each project for P0-06.

## 4. Records

- [x] 4.1 Fetch Google's HIPAA supported-services page and write `docs/compliance/baa-google-cloud.md`:
  - status **NOT ACCEPTED**;
  - acceptance steps, the role or authority still to confirm, and the gate it blocks;
  - a dated covered-products snapshot for every plan §3.2 service, with the exact Gemini/Vertex AI entry and the footnote text.

  Verify: no "Verify" remains in the snapshot; any service not listed is marked "not covered".
- [x] 4.2 Write `infra/bootstrap/foundation.yaml`: the real project IDs and numbers, the bucket, the budget, the BAA record path, the billing ID masked, and org, folder and groups `null` (pending). Write `docs/runbooks/gcp-bootstrap.md` with the exact commands that were run, plus the "with organization" section (including moving the projects into the org). Verify: the YAML parses, and the commands in the runbook match the check output.
- [x] 4.3 Write `docs/compliance/README.md` with the "Pending before real PHI" list (design decision 10). Append a `DECISIONS.md` row (personal account, paper BAA, prefix, USD 50 budget, pending list, plus any "not covered" service). Add a "Pending notifications" table for P0-06, P0-10, P0-13 and P1-02 (P1-02: import the projects, don't recreate them).
- [x] 4.4 Link `docs/compliance/` and `docs/runbooks/` from the root README. Set #5 in the Phase 0 README to "✅ (synthetic setup; BAA and org pending)". Run the public-repo scan for personal emails and the full billing ID, and check that all links resolve. Verify: the scan is clean and there are no broken links.

## 5. Finish (only after the user's review)

- [x] 5.1 Stop and wait for the user's review. Only after they give the go-ahead, archive the change (sync the `cloud-foundation` spec), `git add`, make **one** commit with a one-line descriptive message, push `feature/phase-0-discovery-compliance`, and close issue #5 with a comment listing the files and the pending items. Verify: one commit, the branch matches origin, and #5 is closed under #17.

## 6. Deferred until a billing account exists (not done)

Billing is deferred: the admin will add the billing account later (user decision 2026-11-26, DECISIONS #294). These steps are **not done**. They are plain bullets, not checkboxes, so they don't count as tasks of this change. The commands are in `docs/runbooks/gcp-bootstrap.md` Part B, and the items stay on the "Pending before real PHI" list in `docs/compliance/README.md`. When billing exists, run Part B and record it in a follow-up commit.

- **2.1b** Link each project to the user's billing account once it exists. Verify: `billingEnabled` is `True` for each.
- **2.2** Create `gs://dai-rcpt-ops-tfstate` in `dai-rcpt-ops`: location `US`, uniform access, public access prevention, versioning on. Verify: describe shows versioning enabled and public access prevention `enforced`.
- **2.3** Create the budget `dental-ai monthly`: USD 50, thresholds 50%, 90% and 100%, scoped to the four projects. Enable only the API it needs, in `dai-rcpt-ops`. Verify: `gcloud billing budgets list` shows it with the three thresholds.
- **3.1b** Run a synthetic round-trip in the state bucket (write a test file, read it, list versions, delete it), and make an anonymous request that must be refused. Verify: every check has the expected result. Save the output, with emails and the billing ID masked, to `docs/compliance/bootstrap-checks-2026-11-26.md`.
