# Design: P0-05 Google Cloud foundation (personal account) and BAA record

## Context

- **The user's decisions on 2026-11-26** are in proposal.md, Why: real setup in a personal Gmail account (so no organization), BAA on paper only, prefix `dai-rcpt`, a USD 50 budget, and gcloud installed by us with the user logging in.
- **Decisions from DECISIONS #23–#27 that still apply:** gcloud commands from a runbook; IDs in `infra/bootstrap/foundation.yaml`; real PHI only in prod after all gates; the BAA record in `docs/compliance/baa-google-cloud.md`; IAM only through groups (which needs an organization).
- **The repo is public.** The spec assumed a private repo, so personal data and the billing account ID need care.
- **This machine has no gcloud.** Nothing exists yet under `infra/`, `docs/compliance/` or `docs/runbooks/`.

## Goals / Non-Goals

**Goals:**
- Four real, billed, labelled projects, a protected state bucket, a USD 50 budget and contacts, each checked with gcloud.
- Honest records: real IDs, `NOT ACCEPTED` for the BAA, and a pending list for everything that needs an organization.
- A real covered-products snapshot from Google's current HIPAA page.

**Non-Goals:**
- No BAA acceptance and no saved BAA PDF.
- No organization, folder, groups, org IAM or break-glass admins. These are impossible without a company domain and are recorded as pending.
- No org policies or service restrictions (P0-06), no Terraform (P1-02), no service accounts or KMS (P1-05), no CI identity (P1-06).
- No PHI of any kind. Tests use synthetic objects only.

## Decisions

1. **The Google Cloud CLI is installed in the scratchpad** from Google's official Linux archive, with no system-wide install. The user logs in once with `! <scratchpad>/google-cloud-sdk/bin/gcloud auth login`. Credentials stay in the user's normal gcloud config directory and never in the repo.
2. **Every step that changes the account is shown first and runs only after the user says yes.** This covers creating projects (IDs are permanent, and deletion is a 30-day soft delete), linking billing, creating the bucket, enabling APIs, and creating the budget and contacts. Read-only checks run without asking.
   - **Pre-flight, read-only:** the active account, `gcloud organizations list` (expect none), the billing accounts (the user picks one if there are several), and whether the 4 project IDs are free.
3. **Project IDs are `dai-rcpt-{dev,staging,prod,ops}`.** If any ID is taken, all four get the same short suffix (spec §8), which is recorded in DECISIONS.
4. **Without an organization:**
   - the projects have no parent;
   - the account owner is the only IAM member;
   - essential contacts are set on each project instead of at org level;
   - the budget is scoped to the four projects by project number.

   The runbook keeps a second "with organization" section, the spec's original steps. It includes moving the projects into the organization later (`gcloud beta projects move`), so nothing is recreated.
5. **Only the APIs needed for this task are enabled, in `dai-rcpt-ops` only:** `billingbudgets.googleapis.com` and `essentialcontacts.googleapis.com` (if the CLI requires them), plus Cloud Storage for the bucket. Calls use `--billing-project=dai-rcpt-ops` where needed, so dev, staging and prod keep no enabled services beyond Google's defaults. Any default APIs found enabled are listed for P0-06.
6. **"Test everything like real with mock data":**
   - run the spec §10 checks, adapted to projects;
   - a synthetic round-trip in the state bucket: write a test file (`synthetic: true`, no PHI), read it back, list versions, delete it;
   - an anonymous HTTP request to the bucket, which must be refused (public access prevention).

   The output, with IDs only and emails and the billing ID masked, is saved to `docs/compliance/bootstrap-checks-2026-11-26.md`. There's no PR, so this file replaces "the PR description".
7. **What the public repo records:**
   - Project IDs, project numbers and the bucket name are committed: they're identifiers, not secrets.
   - The billing account ID is committed only as `XXXXXX-XXXXXX-<last 6>`.
   - The user's email is never committed; the contacts are described as "the account owner's email".
   - A scan before the review checks for `@gmail.com`, `@googlemail.com` and full billing IDs.
8. **The covered-products snapshot is real.** Google's HIPAA page (https://docs.cloud.google.com/docs/security/compliance/hipaa) is fetched during apply. For each plan §3.2 service, the exact entry name, whether it's listed, and the footnote text are copied with the date. The entry covering Gemini on Vertex AI is identified by its exact name. Anything not listed becomes a DECISIONS row (spec §8).
9. **The BAA record is honest.** Status `NOT ACCEPTED`, with the console path and steps, who must accept (a person with authority to bind the company, still to be named), the scope still to verify, and the gate it blocks. No acceptor, date or PDF is invented. This follows the user's explicit choice not to mock the BAA.
10. **The pending list** (in `docs/compliance/README.md`, the BAA record and DECISIONS) is everything required before real PHI that this setup can't do:
    - a company domain plus Workspace or Cloud Identity, and so an organization;
    - the folder `dental-ai` and moving the projects into it;
    - the four groups and org IAM through groups, and removing default domain-wide grants;
    - two break-glass super-admins with hardware keys, and 2-step verification enforced;
    - org-level essential contacts;
    - accepting the BAA, with a saved copy and the legal review (P0-11).

11. **No billing account yet (found in pre-flight, 2026-11-26).** The account has no billing account. The user chose to create the projects and contacts now. Linking billing, the state bucket and the budget wait until a billing account exists (tasks 2.1b, 2.2 and 2.3 stay open and are listed as pending). Essential contacts use the Essential Contacts API, enabled only in `dai-rcpt-ops` and called with `--billing-project=dai-rcpt-ops`. This is gcloud's quota-project flag, and it needs no billing.
12. **Billing deferred; P0-05 closes without it (user decision 2026-11-26, DECISIONS #294).** The admin will add the billing account later. Linking billing, the state bucket, the budget and the bucket test move to a "Deferred" section in tasks.md and stay on the pending list. The spec's billing, bucket and budget requirements remain the target. They're met when runbook Part B runs, recorded in a follow-up commit. Nothing in P0-06 to P0-14 needs the state bucket. P1-02 (Terraform) needs it first, so Part B must run before P1-02 starts.

## Risks / Trade-offs

- **[Personal accounts often have a low project quota]** → Check the quota during pre-flight. If creating a project fails on quota, stop and ask the user: request a quota increase, or reuse fewer projects.
- **[Personal-account IAM breaks "groups only"]** → Accepted for synthetic testing only. Recorded as pending, and the PHI gate stays closed.
- **[Project IDs are permanent and public]** → They're shown to the user before creation. The prefix contains no personal or company-identifying data.
- **[Unexpected cost]** → Empty projects and a near-empty bucket cost about nothing. The USD 50 budget alerts early. No compute is created.
- **[Google's HIPAA page changes]** → The snapshot is dated. P0-06, P0-13 and P5-14 refresh it.
- **[The gcloud install in the scratchpad may be cleared by a reboot]** → It's reinstallable in one step. All results are recorded in the repo, and nothing depends on the scratchpad.

## Migration Plan

The cloud changes can be rolled back: `gcloud projects delete` (with a 30-day restore) and `gcloud storage rm -r` for the bucket. Later, moving to an organization is a move, not a rebuild (decision 4).
