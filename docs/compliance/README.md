# Compliance records

| File | What |
|---|---|
| [baa-google-cloud.md](baa-google-cloud.md) | Google Cloud HIPAA BAA record. Status **NOT ACCEPTED**. Includes the covered-products snapshot (2026-11-26). P0-10 imports it into the vendor matrix. |
| [bootstrap-checks-2026-11-26.md](bootstrap-checks-2026-11-26.md) | Output of the Google Cloud setup checks (P0-05) |

Runbook: [docs/runbooks/gcp-bootstrap.md](../runbooks/gcp-bootstrap.md) · IDs: [infra/bootstrap/foundation.yaml](../../infra/bootstrap/foundation.yaml)

## Current state (2026-11-26)
- **Google Cloud:** projects `dai-rcpt-dev`, `dai-rcpt-staging`, `dai-rcpt-prod` and `dai-rcpt-ops` exist in a personal Google account, with no organization (DECISIONS #293).
- **Data:** synthetic only. **No PHI may enter any project.**

## Pending before real PHI
Every item must be done before any real PHI enters `dai-rcpt-prod` (dev, staging and ops never get real PHI):

| Item | Why it's pending | Task |
|---|---|---|
| Accept the Google Cloud HIPAA BAA, save the copy, legal review | Paper-only for now (user decision 2026-11-26) | P0-05 / P0-11 |
| Billing account linked to the four projects | No billing account yet | P0-05, deferred (runbook Part B); needed before P1-02 |
| Terraform state bucket `gs://dai-rcpt-ops-tfstate` and its synthetic test | Needs billing | P0-05, deferred (Part B); needed before P1-02 |
| Budget USD 50 with 50/90/100% alerts | Needs a billing account | P0-05, deferred (Part B) |
| Company domain with Workspace or Cloud Identity, and so an organization | Personal account has no organization | P0-05 (runbook Part C) |
| Folder `dental-ai`, with the projects moved into it | Needs an organization | P0-05 (Part C) |
| IAM through groups only; default domain-wide creator grants removed | Needs an organization and groups | P0-05 (Part C) |
| Two break-glass super-admins with hardware keys; 2-step verification enforced for admins | Needs Workspace or Cloud Identity | P0-05 (Part C) |
| Org-level essential contacts | Needs an organization (project-level contacts are set) | P0-05 (Part C) |
| Covered-products restriction, US-only locations, Speech-to-Text data logging off, unneeded default APIs disabled | Next task | P0-06 |
| Clinic ↔ company BAA | Not signed | P0-09 |
| Vendor matrix lists every PHI vendor with a signed BAA | Not built | P0-10 |

## Pending notifications
These GitHub issues aren't closed yet or don't have this information. When each task starts, comment on its issue with the paths above.

| Task | What it relies on | Posted on issue (date) |
|---|---|---|
| P0-06 Covered-products restriction | Project IDs and numbers; no organization, so org policies need Part C or project-level controls; the 23 APIs Google enabled by default (checks file); the snapshot | - |
| P0-10 Vendor/BAA matrix | `baa-google-cloud.md` as the Google Cloud row: **NOT ACCEPTED** | - |
| P0-13 Gemini model choice | Covered entries "Generative AI on Agent Platform" and "Gemini Enterprise Agent Platform" (Vertex AI renamed); GA models only | - |
| P1-02 Terraform base | `foundation.yaml`: **import** the four projects, never recreate them; the state bucket once Part B is done | - |
