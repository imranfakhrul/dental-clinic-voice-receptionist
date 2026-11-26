# Proposal: P0-05 Create the Google Cloud foundation and record the BAA status (GitHub issue #5)

## Why

Every service that will touch PHI runs on Google Cloud (plan §3.2). This task is the root of the infrastructure work:
- P0-06 (restricting to HIPAA-covered products) and P0-10 (the vendor matrix) depend on it directly;
- through P0-06 it unblocks P0-13 and P1-02 to P1-06.

Plan §3.3's gate is strict: **no PHI goes to a vendor until its BAA is accepted and recorded.**

Source of truth: `dental-ai-tasks/tasks/P0-05 Create Google Cloud org-project and accept Google Cloud BAA.md` (approved). It has no dependencies.

**What the user decided on 2026-11-26** (this changes the spec's plan):
- **The Google Cloud setup is real**, in the user's existing Google Cloud account, and it's tested with synthetic data only.
- **The account is a personal Gmail account**, so there is **no organization resource**: Google creates one only for a company domain (Workspace or Cloud Identity). The folder, Google groups, org-level IAM and org-level essential contacts can't be created now. They're recorded as pending, to be done before any real PHI.
- **The BAA is paper only.** It's recorded as **not accepted**. Nobody accepts it in this task.
- Project prefix `dai-rcpt`, a monthly budget of USD 50, and gcloud installed in the scratchpad with the user logging in.

## What Changes

**Real Google Cloud resources, created with `gcloud` after the user approves each step:**
- Projects `dai-rcpt-dev`, `dai-rcpt-staging`, `dai-rcpt-prod` and `dai-rcpt-ops`, labelled `env` and `system=dental-ai`, all linked to the user's billing account. No service APIs are enabled beyond what these steps need. P0-06 restricts services first.
- The Terraform state bucket `gs://dai-rcpt-ops-tfstate` (location `US`, versioning on, uniform access, public access prevented).
- A monthly budget of USD 50 with alerts at 50%, 90% and 100%, covering the four projects.
- Project-level essential contacts (security, technical, billing, legal, suspension) on all four projects.

**Records in the repo:**
- `infra/bootstrap/foundation.yaml`: the real project IDs and numbers, the bucket and the budget. The billing account ID is masked and no personal email appears, because the repo is public. The org, folder and groups fields are `null`, marked pending.
- `docs/runbooks/gcp-bootstrap.md`: the exact commands that were run (personal-account path), plus the org path for when a company domain exists.
- `docs/compliance/baa-google-cloud.md`: status **NOT ACCEPTED**, the acceptance steps, the gate it blocks, and a **real, dated covered-products snapshot** taken from Google's HIPAA page for every plan §3.2 service, with the Gemini entry and footnotes resolved.
- `docs/compliance/README.md` and a "Pending before real PHI" list: the organization, folder, groups, org IAM and break-glass admins, the BAA acceptance and the legal review.
- `docs/compliance/bootstrap-checks-2026-11-26.md`: the adapted spec §10 check output (IDs only, no secrets or emails), standing in for "the PR description".
- A `DECISIONS.md` row for the personal-account deviation, the paper BAA, the prefix and the budget.
- Links from the root README to `docs/compliance/` and `docs/runbooks/`. Issue #5 is marked done in the Phase 0 README, with the pending items listed.

## Capabilities

### New Capabilities
- `cloud-foundation`: the Google Cloud environment layout (four projects, their purposes and PHI rules), the Terraform state bucket, budget alerts, contacts, the IAM baseline, the recorded IDs, and the BAA status gate that blocks PHI until the BAA is accepted.

### Modified Capabilities
<!-- none -->

## Impact

- **Cloud:** four new projects and one bucket in the user's account, all free to hold. Possible tiny storage costs, and the budget alerts at USD 50.
- **New folders:** `infra/bootstrap/`, `docs/runbooks/` and `docs/compliance/`.
- **Edited files:** `DECISIONS.md`, the root `README.md` and the Phase 0 README.
- **Downstream:**
  - P0-06 must work with projects only until an organization exists. Org policies need an org or a folder.
  - P0-10 imports the BAA record, which says **not accepted**.
  - P0-13 uses the covered-products Gemini entry.
  - P1-02 imports these projects and doesn't recreate them.
- **The gate stays closed:** no real PHI may enter any project until the BAA is accepted and the pending items are done.
