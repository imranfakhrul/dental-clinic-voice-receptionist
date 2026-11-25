---
id: P0-05
title: Create Google Cloud org/project and accept Google Cloud BAA
milestone: P0
epic: E0.2
size: S
labels: area:compliance, area:infra, type:chore
depends_on: none
status: approved
---

# P0-05: Create Google Cloud org/project and accept Google Cloud BAA

## 1. Summary
Set up our company's Google Cloud foundation:
- an organization resource tied to our company domain;
- a billing account;
- a `dental-ai` folder holding `dev`, `staging`, `prod` and `ops` projects;
- access granted only through Google groups, two break-glass super-admins, budget alerts and essential contacts.

Accept the **Google Cloud HIPAA Business Associate Addendum (BAA)** and record who accepted it, when, and which version. Org, billing and BAA steps are manual (console). Folders, projects, the Terraform state bucket, budgets and contacts are created with `gcloud` commands from a reviewed runbook, so P1-02 can import them into Terraform. Done means: the BAA is accepted and recorded in `docs/compliance/baa-google-cloud.md`, the four projects exist and are linked to billing, no IAM role is granted to an individual user, and all IDs are recorded for P0-06 and P1-02.

## 2. Why this matters
Every service that will touch PHI runs on Google Cloud: Gemini, Speech-to-Text, Text-to-Speech, Cloud Run, Cloud SQL, Redis (plan §3.2). HIPAA requires a signed BAA before any vendor processes PHI. Plan §3.3's compliance gate is explicit: **no PHI flows to any vendor until its BAA is accepted and recorded.**

This task is the root of the infrastructure work. P0-06 (restricting the org to HIPAA-covered products) and P0-10 (vendor matrix) depend on it directly. Through P0-06 it unblocks P0-13 (model choice) and P1-02 to P1-06 (Terraform, databases, secrets, CI/CD). Separate projects per environment are the basis for keeping real PHI in prod only.

No patient or clinic staff member sees this task directly. If it's done badly, though (personal accounts owning projects, no BAA record, everyone able to create projects), it causes HIPAA and access-control findings later (P5-14).

Plan references: §3.2 (stack), §3.3 (BAA strategy and rules), §6 (security: vendors, access control), §8 Phase 0.

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P0, Discovery & Compliance Foundation**.
- **Organization resource:** the top of a company's Google Cloud hierarchy (organization → folders → projects). It exists for **Google Workspace** and **Cloud Identity** customers and is created automatically once the account is associated with a domain and a user signs in to the console. Source: https://docs.cloud.google.com/resource-manager/docs/creating-managing-organization. **Verify:** whether Cloud Identity Free is enough for our case (the page names Cloud Identity but doesn't mention the Free edition).
- **Projects, folders, billing account:** a project holds resources and is where APIs are enabled; folders group projects so policies (P0-06) can be applied once; a billing account pays for projects linked to it.
- **Google Cloud HIPAA BAA:** Google's Business Associate Addendum. According to Google's support page (https://support.google.com/cloud/answer/6329727), it is accepted in the console at **IAM & Admin → Privacy & Security** (`console.cloud.google.com/iam-admin/privacy`): select a project, find "Google Cloud Platform HIPAA Business Associate Addendum", click **Review and Accept**, then **I Accept**. The same page says you "only need to opt in to the HIPAA BAA within one Google Cloud project in your account", and that the opt-in only appears if your Google Cloud agreement doesn't already include the BAA by reference. **Verify:** which IAM role is needed to accept, and whether acceptance covers the whole organization or the billing account. The page doesn't say; check it in the console and in the accepted document's text.
- **Covered products:** only services on Google's HIPAA supported-services list may process PHI. Google says to "disable unsupported Google Cloud services … when working with PHI". The list is the "Google Cloud supported services" section of https://docs.cloud.google.com/docs/security/compliance/hipaa. Enforcing it is P0-06's job; this task only takes a dated snapshot.
- **Break-glass account:** an emergency super-admin account kept for recovery only, with a hardware security key, never used day to day.
- **Essential contacts:** the email addresses Google uses for security, billing, legal and technical notices at org level.
- **PHI / BAA basics:** see GLOSSARY.md.

## 4. Scope
**In scope**
- Organization (on the company's existing Google Workspace domain, or Cloud Identity if there is none), two break-glass super-admins with security keys, 2-step verification enforced for admins.
- Billing account, budget and alerts.
- Folder `dental-ai`; projects `<prefix>-dev`, `<prefix>-staging`, `<prefix>-prod`, `<prefix>-ops`; billing links.
- A Terraform state bucket in `<prefix>-ops` (versioned, uniform access, no public access).
- Google groups and org-level IAM bindings for those groups; removing default broad grants.
- Essential contacts.
- Accepting the Google Cloud BAA, and recording it with a saved copy of the accepted text.
- A dated snapshot of the covered-products list for the services in plan §3.2.
- The runbook `docs/runbooks/gcp-bootstrap.md` and the IDs file `infra/bootstrap/foundation.yaml`.

**Out of scope** (and which task covers it)
- Org policies (allowed services, US-only locations), VPC Service Controls, turning off Speech-to-Text data logging, checking for AI Studio keys → P0-06
- The full vendor/BAA matrix and the PR vendor check → P0-10 (it imports this task's BAA record)
- Choosing Gemini model versions and the region → P0-13 (with P0-06 for locations)
- Terraform for networking, Cloud Run, Artifact Registry; importing these projects → P1-02
- Service accounts, KMS keys, secrets → P1-05
- CI identity (Workload Identity Federation) → P1-06; this task only creates the `ops` project and the state bucket it will use
- Audit-log configuration and monitoring → P1-07
- Google Workspace BAA for Gmail → P0-08
- Legal review of the BAA terms → the compliance advisor, tracked in P0-11 / P5-14

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| None | - | Can start immediately. |
| Company domain and admin access (external) | Admin access to the company's Google Workspace or DNS (to verify a domain for Cloud Identity) | If missing, write the runbook (§7 steps 3–9) against placeholder IDs and get it reviewed. Only steps 1, 2 and 10 need the domain. |
| Person with authority to accept the BAA (external) | Someone who may legally bind the company | Ask the company owner to name them (§14). Everything except §7 step 10 can proceed. |

## 6. Interface contract
This task produces cloud resources and records. Downstream tasks rely on the names, IDs and files below.

**Naming (Proposed)**
| Resource | Name / ID |
|---|---|
| Folder | display name `dental-ai` |
| Projects | `<prefix>-dev`, `<prefix>-staging`, `<prefix>-prod`, `<prefix>-ops` (`<prefix>` = short company prefix, e.g. `acme-dai`; project IDs are global and permanent) |
| Terraform state bucket | `gs://<prefix>-ops-tfstate` (location `US`, versioning on) |
| Groups | `gcp-org-admins@`, `gcp-billing-admins@`, `gcp-security-admins@`, `gcp-developers@` (on the company domain) |

**Environment rules (Proposed)**
| Project | Purpose | Real PHI allowed? |
|---|---|---|
| `<prefix>-prod` | Pilot and live clinics | Yes, only after P0-06, P0-09 and the other gates in §9 |
| `<prefix>-staging` | Pre-release testing, clinic UAT (P5-07) | No: synthetic data only |
| `<prefix>-dev` | Development | No: synthetic data only |
| `<prefix>-ops` | Terraform state, CI identity, shared tooling | No |

All four are under the BAA and will get the same covered-products restrictions (P0-06).

**`infra/bootstrap/foundation.yaml`** (IDs are not secrets; commit them)
```yaml
schema_version: 1
recorded_on: "2026-12-01"
org:
  domain: example.com
  org_id: "123456789012"
billing:
  billing_account_id: "000000-AAAAAA-BBBBBB"
  budget_monthly_usd: 500          # Proposed, see §14
folder:
  name: dental-ai
  folder_id: "987654321098"
projects:
  dev: {project_id: acme-dai-dev, project_number: "111111111111"}
  staging: {project_id: acme-dai-staging, project_number: "222222222222"}
  prod: {project_id: acme-dai-prod, project_number: "333333333333"}
  ops: {project_id: acme-dai-ops, project_number: "444444444444"}
terraform_state_bucket: acme-dai-ops-tfstate
groups:
  org_admins: gcp-org-admins@example.com
  billing_admins: gcp-billing-admins@example.com
  security_admins: gcp-security-admins@example.com
  developers: gcp-developers@example.com
baa:
  record: docs/compliance/baa-google-cloud.md
  accepted_on: "2026-12-01"
```

**Org-level IAM (Proposed; groups only)**
| Group | Role | Where |
|---|---|---|
| `gcp-org-admins` | `roles/resourcemanager.organizationAdmin` | Organization |
| `gcp-billing-admins` | `roles/billing.admin` | Billing account |
| `gcp-security-admins` | `roles/orgpolicy.policyAdmin`, `roles/iam.securityReviewer` | Organization (P0-06 uses them) |
| `gcp-developers` | `roles/viewer` | `<prefix>-dev` only (P1-05 adds least-privilege roles later) |

**`docs/compliance/baa-google-cloud.md`** (P0-10 imports it into the matrix)
```markdown
# Google Cloud HIPAA BAA record
- Vendor: Google Cloud
- Agreement name (as shown in console): Google Cloud Platform HIPAA Business Associate Addendum
- Document version / date printed on the agreement: <…>
- Accepted on: YYYY-MM-DD (UTC)
- Accepted by: <name>, <role>; authority to bind the company confirmed by <name> on YYYY-MM-DD
- Project used to opt in: <prefix>-ops
- Scope: <what the document and console say: organization / billing account / account>  ← Verify
- Saved copy: docs/compliance/agreements/google-cloud-baa-YYYY-MM-DD.pdf
- Covered-products snapshot: <date>, https://docs.cloud.google.com/docs/security/compliance/hipaa (table below)
- Legal review of terms: pending (compliance advisor), tracked in P0-11
```
Covered-products snapshot table (services from plan §3.2):
| Service | Listed? (snapshot date) | Notes |
|---|---|---|
| Vertex AI / Gemini | Verify: listed under the names "Generative AI on Agent Platform", "Gemini Enterprise Agent Platform" or "Gemini Enterprise", not as "Vertex AI". Record the exact entry that covers the Gemini API calls we make. | P0-13 confirms per model |
| Speech-to-Text | Listed (with a footnote) | Don't opt in to data logging (P0-06) |
| Text-to-Speech, Cloud Run, Cloud SQL, Memorystore, Cloud Tasks, Cloud Scheduler | Listed | - |
| Secret Manager, Cloud KMS, Cloud Logging | Listed (with footnotes) | Verify: read the footnote text and copy it here |

## 7. Implementation guide
Steps 1, 2 and 10 are done in the console; everything else uses the `gcloud` commands in the runbook. Run commands from Cloud Shell or a workstation signed in as a member of `gcp-org-admins`.

1. **Organization.** If the company has Google Workspace, sign in to the Cloud console as a Workspace super-admin; the organization resource appears for the domain. Otherwise sign up for Cloud Identity with the company domain and verify it via DNS. Never create projects under a personal Gmail account.
2. **Admins.**
   - Create two break-glass super-admin accounts (`breakglass1@`, `breakglass2@`), each with a hardware security key, used only for recovery. Store the recovery steps in the company password manager, not in the repo.
   - Enforce 2-step verification for all admins.
   - Create the four groups from §6.
3. **Remove default broad grants.** When an organization is created, the whole domain may get project-creator and billing-account-creator roles by default. **Verify** in the org IAM policy and remove them:
   ```bash
   gcloud organizations get-iam-policy ORG_ID --format=json > org-iam-before.json
   gcloud organizations remove-iam-policy-binding ORG_ID --member=domain:example.com --role=roles/resourcemanager.projectCreator
   gcloud organizations remove-iam-policy-binding ORG_ID --member=domain:example.com --role=roles/billing.creator
   ```
4. **Group bindings** (as in §6):
   ```bash
   gcloud organizations add-iam-policy-binding ORG_ID --member=group:gcp-org-admins@example.com --role=roles/resourcemanager.organizationAdmin
   gcloud organizations add-iam-policy-binding ORG_ID --member=group:gcp-security-admins@example.com --role=roles/orgpolicy.policyAdmin
   gcloud organizations add-iam-policy-binding ORG_ID --member=group:gcp-security-admins@example.com --role=roles/iam.securityReviewer
   ```
   Then remove any role granted directly to an individual `user:` (keep the break-glass accounts' super-admin status, which lives in the Workspace / Cloud Identity admin console, not in Cloud IAM).
5. **Billing account.** Create it, or reuse the company's existing one, in the console. Grant `roles/billing.admin` to `gcp-billing-admins` on the billing account.
6. **Folder and projects:**
   ```bash
   gcloud resource-manager folders create --display-name=dental-ai --organization=ORG_ID
   for env in dev staging prod ops; do
     gcloud projects create PREFIX-$env --folder=FOLDER_ID --name="Dental AI $env" --labels=env=$env,system=dental-ai
     gcloud billing projects link PREFIX-$env --billing-account=BILLING_ACCOUNT_ID
   done
   gcloud projects add-iam-policy-binding PREFIX-dev --member=group:gcp-developers@example.com --role=roles/viewer
   ```
   Don't enable any service APIs yet beyond what the commands need. P0-06 applies the service restrictions first.
7. **Terraform state bucket:**
   ```bash
   gcloud storage buckets create gs://PREFIX-ops-tfstate --project=PREFIX-ops --location=US --uniform-bucket-level-access --public-access-prevention
   gcloud storage buckets update gs://PREFIX-ops-tfstate --versioning
   ```
8. **Budget and alerts** (Proposed amount, §14):
   ```bash
   gcloud billing budgets create --billing-account=BILLING_ACCOUNT_ID --display-name="dental-ai monthly" \
     --budget-amount=500USD --threshold-rule=percent=0.5 --threshold-rule=percent=0.9 --threshold-rule=percent=1.0
   ```
   Budget alerts go to billing admins by default. **Verify** that `gcp-billing-admins` members receive them.
9. **Essential contacts:**
   ```bash
   gcloud essential-contacts create --organization=ORG_ID --email=gcp-security-admins@example.com --notification-categories=security,technical
   gcloud essential-contacts create --organization=ORG_ID --email=gcp-billing-admins@example.com --notification-categories=billing,legal,suspension
   ```
10. **Accept the BAA** (by the person with authority, §14):
    1. Open `console.cloud.google.com/iam-admin/privacy`, select `PREFIX-ops`, find "Google Cloud Platform HIPAA Business Associate Addendum", choose **Review and Accept**, read it, then **I Accept**.
    2. Save the agreement text as a PDF.
    3. If no opt-in appears, the company's Google Cloud agreement may already include the BAA by reference. Record that agreement's name and date instead, and confirm with Google support or the account team.
    4. **Verify** and record the scope (organization / billing account / account) and the role that was needed.
11. **Record it.**
    - Write `docs/compliance/baa-google-cloud.md` with the covered-products snapshot.
    - Commit the PDF under `docs/compliance/agreements/`. The repo is private; the agreement is confidential but contains no PHI. If P1-01 hasn't created the repo yet, keep these in the company's shared drive and move them in later.
    - Write `infra/bootstrap/foundation.yaml` and finish `docs/runbooks/gcp-bootstrap.md` with the exact commands that were run.
12. **Notify.** Comment on the issues of P0-06, P0-10, P0-13 and P1-02 with the IDs file path. Tell P1-02 to **import** these projects (`terraform import`), not recreate them.

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| Someone already created projects under a personal Gmail account | Don't reuse them. Create fresh projects under the organization; delete or migrate the old ones only after checking they hold no data. |
| The company has no Workspace and can't change DNS | Blocked. Escalate to the company owner. Personal accounts are not acceptable for a HIPAA system. |
| The BAA opt-in doesn't appear | Probably already included by reference in the company's Google Cloud agreement (support page). Record that agreement instead, and confirm in writing with Google. |
| The acceptor lacks permission on the Privacy & Security page | Find the required role (Verify), grant it temporarily to that person through a group, accept, and remove it again. Record what was needed in the runbook. |
| The acceptor doesn't have legal authority | Stop. Acceptance must be done or approved in writing by someone with authority (§14). |
| A project ID is taken | Choose another prefix for **all four** projects (keep them consistent) and record it. Project IDs can't be changed later. |
| A service we plan to use isn't on the covered list | Record it in the snapshot as "not covered", tell the tech lead, and log in DECISIONS.md that it must not process PHI or must be replaced (plan §3.3). |
| A Gemini model or feature is Pre-GA | Not decided here; P0-13 must pick GA only (plan §3.3). |
| The budget threshold fires during setup | Billing admins investigate; nothing should be running yet. Treat it as a signal of a mis-created resource. |
| A break-glass account's security key is lost | Recover with the second break-glass account, replace the key, and log the event. |
| Someone wants to load "just a few real records" into dev | Not allowed: real PHI goes in prod only, and only after the gates in §9. |

## 9. Security, HIPAA and PHI
- **No PHI is handled.** Completing this task does **not** allow PHI in Google Cloud. Real PHI may enter `<prefix>-prod` only after **all** of these: the Google Cloud BAA is accepted (this task), P0-06 restrictions are in place, the clinic ↔ company BAA is signed (P0-09), and the vendor matrix shows it (P0-10).
- **Access control:** IAM only through groups. Two break-glass super-admins with hardware keys. 2-step verification enforced for admins. No individual `user:` IAM bindings, and no service account keys created.
- **Confidential, not PHI:** the BAA PDF and org IDs. Keep them in the private repo or shared drive.
- **Audit:** Admin Activity audit logs are on by default in Google Cloud. **Verify** this and record it; configuring Data Access logs belongs to P1-07.

## 10. Testing
No application code. Run these checks after setup, save their output in the PR description (with IDs, no secrets), and have a reviewer confirm them:
```bash
gcloud organizations list                                   # exactly one org for the company domain
gcloud projects list --filter="parent.id=FOLDER_ID" --format="value(projectId)"   # dev, staging, prod, ops
for env in dev staging prod ops; do gcloud billing projects describe PREFIX-$env --format="value(billingEnabled)"; done   # all True
gcloud organizations get-iam-policy ORG_ID --flatten="bindings[].members" --filter="bindings.members:user:" --format="value(bindings.role)"     # expected: no output
gcloud organizations get-iam-policy ORG_ID --flatten="bindings[].members" --filter="bindings.members:domain:" --format="value(bindings.role)"   # must not list projectCreator or billing.creator
gcloud storage buckets describe gs://PREFIX-ops-tfstate --format="value(versioning_enabled,public_access_prevention)"
gcloud billing budgets list --billing-account=BILLING_ACCOUNT_ID
gcloud essential-contacts list --organization=ORG_ID
```
Also check by hand: the BAA status on the Privacy & Security page shows accepted, the saved PDF opens, and both break-glass accounts can sign in with their security keys.

## 11. Acceptance criteria
- [ ] One organization exists for the company domain; no project of this system lives outside it
- [ ] Folder `dental-ai` holds exactly `<prefix>-dev`, `-staging`, `-prod` and `-ops`, all linked to the billing account
- [ ] The Google Cloud HIPAA BAA is accepted (or confirmed as included by reference), and `docs/compliance/baa-google-cloud.md` records version, date, acceptor, authority, scope and a saved PDF
- [ ] The covered-products snapshot lists every service from plan §3.2 with a date; the Vertex AI / Gemini entry and the footnotes are resolved (no remaining "Verify")
- [ ] The org IAM policy has no `user:` bindings and no domain-wide project-creator or billing-creator grant
- [ ] Two break-glass super-admins with hardware security keys exist, and 2-step verification is enforced for admins
- [ ] The state bucket exists with versioning on and public access prevented
- [ ] A monthly budget with 50/90/100% alerts and essential contacts (security, technical, billing, legal) are set
- [ ] `infra/bootstrap/foundation.yaml` and `docs/runbooks/gcp-bootstrap.md` are committed, and the P0-06, P0-10, P0-13 and P1-02 issues are notified

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI: not applicable (no code); the §10 checks were run and their output reviewed
- [ ] PR reviewed (HIPAA review if labelled `phi`): reviewed by the tech lead and the compliance advisor (BAA record); no `phi` label because no PHI is handled
- [ ] No PHI in logs: no PHI exists in any project yet
- [ ] Docs / README updated: runbook and BAA record committed; README links `docs/compliance/` and `docs/runbooks/`

## 13. Hand-off
| Task | Can rely on |
|---|---|
| P0-06 Covered-products restriction | Org ID, folder ID, project IDs, the `gcp-security-admins` group with org-policy rights, and the covered-products snapshot |
| P0-10 Vendor/BAA matrix | `docs/compliance/baa-google-cloud.md` as the Google Cloud row |
| P0-13 Gemini model choice | The covered-products entry that covers Gemini calls |
| P1-02 Terraform base | `foundation.yaml` IDs and the state bucket; projects are imported, not recreated |
| P1-05 Service accounts / KMS | Projects exist; no user bindings to clean up |
| P1-06 CI/CD | The `ops` project for Workload Identity Federation and the state bucket |
| P0-11 / P5-14 Risk assessment, HIPAA review | BAA record, IAM model, break-glass process |

## 14. Open questions
| Question | Owner | Needed by |
|---|---|---|
| Does the company already have Google Workspace on its domain (or only DNS access)? | Company owner | Step 1 |
| Who has legal authority to accept the Google Cloud BAA for the company? | Company owner | Step 10 |
| Project prefix (e.g. `acme-dai`)? It is permanent. | Tech lead | Step 6 |
| Monthly budget amount for alerts? Proposed: USD 500 until the pilot. | Company owner + tech lead | Step 8 |
| Should the compliance advisor review the BAA terms **before** acceptance rather than before production (plan §3.3 says before production)? | Compliance advisor | Step 10 |

## 15. References
- Plan §3.2 (stack), §3.3 (BAA strategy, rules and compliance gate), §6 (vendors, access control), §8 Phase 0
- Google Cloud HIPAA compliance and supported services: https://docs.cloud.google.com/docs/security/compliance/hipaa
- Accepting the BAA (Privacy compliance and records for Google Cloud): https://support.google.com/cloud/answer/6329727
- Creating and managing organization resources: https://docs.cloud.google.com/resource-manager/docs/creating-managing-organization
- gcloud reference (projects, folders, billing, storage, essential-contacts): https://cloud.google.com/sdk/gcloud/reference
- Related tasks: P0-06, P0-08, P0-09, P0-10, P0-11, P0-13, P1-01, P1-02, P1-05, P1-06, P1-07, P5-07, P5-14
