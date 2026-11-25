---
id: P0-06
title: Restrict projects to HIPAA covered products (org policies + VPC-SC)
milestone: P0
epic: E0.2
size: M
labels: area:compliance, area:infra, type:chore
depends_on: P0-05
status: approved
---

# P0-06: Restrict projects to HIPAA covered products (org policies + VPC-SC)

## 1. Summary
Put guardrails on the Google Cloud foundation from P0-05 so that PHI can only ever land in HIPAA-covered services in the US:
- an **allow-list of services** (everything else is refused);
- **US-only resource locations**;
- a small set of baseline security org policies;
- one **VPC Service Controls perimeter per environment** around the PHI services;
- a confirmed-off check for Speech-to-Text data logging and a proof that no Gemini Developer API (AI Studio) keys exist.

Step 1 decides between Google's **Assured Workloads "US Data Boundary for Healthcare and Life Sciences"** package and our own org policies. Either way, everything is written as Terraform in `infra/org/`. Done means: the policies and perimeters are applied, the negative tests in §10 all fail the way they should, and the results are recorded in `docs/compliance/hipaa-controls.md`.

## 2. Why this matters
Google's BAA covers only the services on its HIPAA supported-services list. Google tells customers to "disable unsupported Google Cloud services … when working with PHI" (https://docs.cloud.google.com/docs/security/compliance/hipaa). Plan §3.3 adds our own rules: covered products only, no AI Studio / Gemini Developer API keys, no Pre-GA features with PHI, and no data-logging programs.

A policy that **prevents** mistakes is much stronger than a rule people must remember. With this task done:
- a developer can't accidentally enable a non-covered service or create resources in Europe;
- a leaked credential can't copy prod data out of the prod perimeter;
- nobody can call Gemini through an API key outside the BAA.

P0-13 (choosing Gemini models) and P1-02 (all Terraform infrastructure) depend on this task, and P5-14 (HIPAA readiness review) audits it.

Plan references: §3.2 (stack), §3.3 (BAA rules), §6 (security), §8 Phase 0.

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P0, Discovery & Compliance Foundation**.
- **What P0-05 created:** an organization on the company domain, folder `dental-ai` with projects `<prefix>-dev`, `-staging`, `-prod`, `-ops`, groups (`gcp-security-admins` has org-policy rights), a Terraform state bucket `gs://<prefix>-ops-tfstate`, and the IDs file `infra/bootstrap/foundation.yaml`. Real PHI is allowed only in prod (DECISIONS #25).
- **Organization policy:** a rule set on the org, a folder or a project that limits what can be configured. Child folders and projects inherit it unless they override it.
  - **`gcp.restrictServiceUsage`:** an allow-list *or* a deny-list (not both) of services. Requests to a refused service fail with "Request is disallowed by organization's constraints/gcp.restrictServiceUsage constraint". Services that depend on a refused service are refused too. Only certain services can be controlled this way. Essential ones such as IAM, Cloud Logging and Cloud Monitoring are always allowed. Supported list: https://docs.cloud.google.com/organization-policy/reference/restrict-services-supported-services.md.txt. Docs: https://docs.cloud.google.com/resource-manager/docs/organization-policy/restricting-resources
  - **`gcp.resourceLocations`:** where new resources may be created. The US value group is `in:us-locations`. It applies only to **new** resources, it doesn't affect global resources, and it controls where resources are created, not every place data is stored. Docs: https://docs.cloud.google.com/resource-manager/docs/organization-policy/defining-locations
- **VPC Service Controls (VPC-SC):** a **perimeter** around projects that blocks Google API calls carrying data across its boundary (for example, copying a prod bucket into a dev project, or calling the prod Vertex AI API from the internet with a stolen token). Perimeters live in an **access policy** (Access Context Manager). **Dry-run mode** logs would-be violations with `dryRun=true` instead of blocking them. Supported services: https://docs.cloud.google.com/vpc-service-controls/docs/supported-products. Notes from that page:
  - Vertex AI ("Agent Platform"), Speech-to-Text, Text-to-Speech, Secret Manager and KMS are supported.
  - Cloud Run is supported but needs extra setup (P1-02).
  - Cloud SQL is protected only through its Admin API, so public IP must be blocked by org policy.
  - Cloud Tasks supports only some targets.
  - **Verify:** Memorystore for Redis wasn't confirmed.
- **Assured Workloads "US Data Boundary for Healthcare and Life Sciences":** a Google-managed package for HIPAA/HITRUST workloads. It sets `gcp.resourceLocations` to US regions, sets `gcp.restrictServiceUsage` to its in-scope services, **requires CMEK** (`gcp.restrictNonCmekServices`) and a minimum TLS version (`gcp.restrictTLSVersion`). It is "included in Assured Workloads Free tier". Speech-to-Text, Text-to-Speech, Cloud SQL, Cloud Storage, Secret Manager, KMS, Memorystore and Vertex AI are in scope. Docs: https://docs.cloud.google.com/assured-workloads/docs/data-boundaries/us-data-boundary-healthcare-life-sciences.md.txt
- **Speech-to-Text data logging:** opt-in and **off by default**, set per project. Turning it on requires certifying that you have no HIPAA BAA with Google. It can only be checked in the console: APIs & Services → Cloud Speech API → Data logging tab. Docs: https://docs.cloud.google.com/speech-to-text/docs/data-logging
- **Gemini Developer API / AI Studio:** `generativelanguage.googleapis.com`, called with API keys. It is outside our plan's BAA approach (§3.3), so we never use it. We call Gemini only through Vertex AI (`aiplatform.googleapis.com`).
- **CMEK:** Customer-Managed Encryption Keys in Cloud KMS. See GLOSSARY.md.

## 4. Scope
**In scope**
- The Assured Workloads vs. own-policies decision (§7 step 1), recorded in DECISIONS.md.
- `infra/org/allowed_services.yaml`: the single list of allowed APIs, with evidence columns.
- Org policies: service allow-list on the `dental-ai` folder, Gemini Developer API denied at org level, US locations, and the baseline constraints in §6.
- Access policy plus three perimeters (dev, staging, prod), each with restricted services and an admin ingress rule.
- The Speech-to-Text data-logging check, the API-key check, and negative tests.
- `docs/compliance/hipaa-controls.md` and the runbook `docs/runbooks/org-guardrails-tests.md`.

**Out of scope** (and which task covers it)
- VPC networks, restricted-VIP DNS (`restricted.googleapis.com`), Cloud Run ingress/egress and switching dev/staging perimeters to enforced → P1-02
- KMS keys and CMEK setup (needed if Assured Workloads is chosen) → P1-03, P1-05
- The CI identity's ingress rule into the perimeters and Workload Identity Federation → P1-06
- Audit-log (Data Access) configuration and alerting on dry-run violations → P1-07
- Choosing Gemini models and a US regional endpoint → P0-13
- STT data logging "off" in application code/config → P3-03 (this task checks the project setting)
- Vendor matrix entry → P0-10

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P0-05 Google Cloud org + BAA (approved spec) | Org ID, folder ID, project IDs, state bucket, `gcp-security-admins` group (from `infra/bootstrap/foundation.yaml`) | Write and `terraform validate` all of `infra/org/` against placeholder IDs in a `example.tfvars`. Do the Assured Workloads comparison (step 1) from the docs alone. Nothing is applied until P0-05 is done. |
| P1-01 Product repo (soft) | A place for `infra/org/` | Keep the code in a temporary repo or branch and move it in unchanged. |

## 6. Interface contract

### Files (Proposed)
| Path | Content |
|---|---|
| `infra/org/allowed_services.yaml` | The allowed APIs and why (format below). Single source of truth. |
| `infra/org/main.tf`, `variables.tf`, `outputs.tf`, `backend.tf` | Org policies, access policy, perimeters |
| `infra/org/terraform.tfvars` | Real IDs copied from `infra/bootstrap/foundation.yaml` (not secret) |
| `docs/compliance/hipaa-controls.md` | What is enforced, check results, dates, evidence screenshots |
| `docs/runbooks/org-guardrails-tests.md` | Negative tests (§10) to re-run after any change |

Terraform state: backend `gcs`, bucket `<prefix>-ops-tfstate`, prefix `org/`.

### `allowed_services.yaml`
```yaml
schema_version: 1
checked_on: "2026-12-02"
sources:
  hipaa_covered: https://docs.cloud.google.com/docs/security/compliance/hipaa
  restrict_supported: https://docs.cloud.google.com/organization-policy/reference/restrict-services-supported-services.md.txt
  vpcsc_supported: https://docs.cloud.google.com/vpc-service-controls/docs/supported-products
services:
  - api: aiplatform.googleapis.com
    purpose: Gemini via Vertex AI (P2-03)
    hipaa_covered: verify     # yes | no | verify; record the exact list entry name in notes
    restrict_supported: verify
    vpcsc_restricted: true    # put in perimeter restricted_services
    notes: "Covered-list entry name: <e.g. Generative AI on Agent Platform>"
  - api: speech.googleapis.com
    purpose: Streaming STT (P3-03)
    hipaa_covered: yes
    restrict_supported: verify
    vpcsc_restricted: true
    notes: "Data logging must stay off"
```

**Candidate list** (Proposed; every `verify` must become `yes` or the service is dropped or logged as an exception):
| API | Purpose | Covered | In perimeter |
|---|---|---|---|
| `aiplatform.googleapis.com` | Gemini (Vertex AI) | Verify entry name | Yes |
| `speech.googleapis.com` | Speech-to-Text | Yes | Yes |
| `texttospeech.googleapis.com` | Text-to-Speech | Yes | Yes |
| `run.googleapis.com` | Cloud Run backend | Yes | Yes (P1-02 setup) |
| `sqladmin.googleapis.com` | Cloud SQL | Yes | Yes (Admin API only) |
| `redis.googleapis.com` | Memorystore for Redis | Yes | Verify VPC-SC support |
| `cloudtasks.googleapis.com` | Reminder/email jobs | Yes | Yes (check targets) |
| `cloudscheduler.googleapis.com` | Scheduled jobs | Yes | Verify |
| `secretmanager.googleapis.com` | Secrets | Yes (footnote: Verify) | Yes |
| `cloudkms.googleapis.com` | Keys | Yes (footnote: Verify) | Yes |
| `storage.googleapis.com` | Buckets (state, exports) | Verify | Yes |
| `artifactregistry.googleapis.com` | Container images | Verify | Yes |
| `compute.googleapis.com` | VPC networking | Verify | Verify |
| `vpcaccess.googleapis.com` | Serverless VPC connector | Verify | Verify |
| `servicenetworking.googleapis.com` | Private IP for Cloud SQL / Redis | Verify | Verify |
| `iamcredentials.googleapis.com`, `sts.googleapis.com` | CI Workload Identity Federation (`ops` project only) | Not PHI | No (`ops` is outside perimeters) |

Logging, Monitoring and IAM are always allowed by Google, so they aren't listed. `generativelanguage.googleapis.com` is deliberately absent and is also denied at org level.

### Org policies (Proposed; constraint names marked Verify must be checked in the constraint reference before apply)
| Constraint | Value | Applied at |
|---|---|---|
| `gcp.restrictServiceUsage` | deny `generativelanguage.googleapis.com` | Organization |
| `gcp.restrictServiceUsage` | allow-list = APIs in `allowed_services.yaml` (`ops`: its own short list) | Folder `dental-ai` (override on `<prefix>-ops`) |
| `gcp.resourceLocations` | `in:us-locations` | Organization |
| `iam.disableServiceAccountKeyCreation` (Verify) | enforced | Organization |
| `iam.allowedPolicyMemberDomains` (Verify) | company Workspace/Cloud Identity customer ID only | Organization |
| `iam.automaticIamGrantsForDefaultServiceAccounts` (Verify) | enforced (no Editor role for default SAs) | Organization |
| `storage.uniformBucketLevelAccess` (Verify) | enforced | Organization |
| `storage.publicAccessPrevention` (Verify) | enforced | Organization |
| `sql.restrictPublicIp` (Verify) | enforced | Organization |
| `compute.vmExternalIpAccess` (Verify) | deny all | Organization |

If Assured Workloads is chosen, it sets services, locations, CMEK and TLS itself. Our Terraform then only adds the org-level Gemini Developer API deny, the baseline rows above, and the VPC-SC perimeters.

### VPC-SC (Proposed)
| Perimeter | Projects | Mode at the end of P0-06 | Becomes enforced |
|---|---|---|---|
| `dai_prod` | `<prefix>-prod` | Enforced | Now |
| `dai_staging` | `<prefix>-staging` | Dry-run | P1-02, after dry-run logs show no unexpected violations |
| `dai_dev` | `<prefix>-dev` | Dry-run | P1-02, same rule |

- `restricted_services` = every `allowed_services.yaml` entry with `vpcsc_restricted: true` that VPC-SC supports.
- `<prefix>-ops` is in no perimeter.
- Ingress rule (all three perimeters): members of `gcp-org-admins` and `gcp-security-admins` may call the restricted services from any source, so admins aren't locked out. **Verify:** whether ingress rules accept Google groups as identities. If not, list the admin user accounts explicitly and document it in the runbook.

Terraform shape (excerpt):
```hcl
resource "google_org_policy_policy" "folder_allowed_services" {
  name   = "folders/${var.folder_id}/policies/gcp.restrictServiceUsage"
  parent = "folders/${var.folder_id}"
  spec {
    rules {
      values { allowed_values = local.allowed_apis }   # from allowed_services.yaml
    }
  }
}

resource "google_access_context_manager_service_perimeter" "dev" {
  parent = "accessPolicies/${google_access_context_manager_access_policy.org.name}"
  name   = "accessPolicies/${google_access_context_manager_access_policy.org.name}/servicePerimeters/dai_dev"
  title  = "dai_dev"
  use_explicit_dry_run_spec = true
  spec {                                            # dry-run configuration
    resources           = ["projects/${var.project_numbers.dev}"]
    restricted_services = local.perimeter_apis
  }
}
```
**Verify:** argument names against the current `hashicorp/google` provider docs before applying.

### Outputs for other tasks (`terraform output`)
`access_policy_id`, `perimeter_names` (map env → name), `allowed_apis` (list).

## 7. Implementation guide
1. **Decide: Assured Workloads or own policies.**
   - Compare the in-scope products of "US Data Boundary for Healthcare and Life Sciences" with every API in the candidate list.
   - **If every API we need is in scope:** use Assured Workloads.
     - Assured Workloads creates its own folder. **Verify:** whether the existing empty P0-05 projects can be moved into it; if not, create new projects inside it with the P0-05 commands.
     - Update `foundation.yaml`, add an amendment note at the end of P0-05's runbook, and log a DECISIONS row that supersedes #24.
     - Tell P1-03/P1-05 that CMEK becomes mandatory for every supported service.
   - **Otherwise:** use our own policies, and record which APIs were missing.

   Either way, write the result and the evidence links in `hipaa-controls.md`.
2. **Build `allowed_services.yaml`.** For every candidate API, check the three sources and fill the columns. Drop anything that isn't HIPAA-covered, or log an exception in DECISIONS.md if it never touches PHI (e.g. the CI-only APIs in `ops`).
3. **Write `infra/org/` Terraform:**
   - org policies per §6;
   - the access policy (**Verify:** only one org-level access policy can exist; reuse it if it already does);
   - three perimeters and the admin ingress rule.

   Run `terraform fmt`, `terraform validate` and `terraform plan`, with the plan reviewed by a second person.
4. **Apply in a safe order:**
   1. the org-level Gemini Developer API deny and the location policy;
   2. the baseline constraints;
   3. the folder allow-list;
   4. the `ops` override;
   5. the perimeters (dev and staging in dry-run, prod enforced).

   Apply as a member of `gcp-security-admins` from a workstation (`gcloud auth application-default login`). There is no CI yet.
5. **Check Speech-to-Text data logging** in each of the four projects: console → APIs & Services → Cloud Speech API → Data logging. Expected: logging is not enabled (the tab offers "Enable data logging"). Take a dated screenshot for `hipaa-controls.md`. If the API isn't enabled in a project yet, record "API not enabled; logging cannot be on" and repeat the check when P3-03 enables it.
6. **Check for API keys:** `gcloud services api-keys list --project=<id>` for all four projects. Expected: none. Delete any key found and log it.
7. **Run the negative tests** in §10 and record the results.
8. **Write `docs/compliance/hipaa-controls.md`:** the decision from step 1, the allowed-services table, the policy list, the perimeter modes, the STT and API-key checks with dates, and the test results.
9. **Notify:**
   - P0-13: Gemini only via `aiplatform.googleapis.com`, US region only.
   - P1-02: perimeters to switch to enforced; restricted VIP; Cloud Run VPC-SC setup.
   - P1-03/P1-05: CMEK, if Assured Workloads was chosen.
   - P1-06: the CI ingress rule.
   - P1-07: dry-run violation logs.
   - P0-10: the evidence file.

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| A needed API isn't on the HIPAA covered list | Don't allow it for PHI projects. Find a covered alternative, or log an exception in DECISIONS.md only if it provably never handles PHI (tech lead + compliance advisor approve). |
| A needed API isn't supported by `gcp.restrictServiceUsage` | It can't be controlled by this constraint. Rely on IAM (only admins can enable APIs) and list it in `hipaa-controls.md` as "controlled by IAM only". |
| A developer tries to enable a refused API | It fails with the `gcp.restrictServiceUsage` error. Adding an API needs a PR changing `allowed_services.yaml` plus a DECISIONS row. |
| A resource is requested in a non-US region | Creation fails. Only new resources are checked, so after any policy change confirm there are no older resources outside the US (`gcloud asset search-all-resources`). |
| A global resource or endpoint (e.g. a global Gemini endpoint) | Not blocked by the location policy. P0-13 must choose a US regional Vertex AI endpoint and record it. |
| An enforced perimeter blocks an admin in the console | Use the ingress rule for admin groups. If it's misconfigured, a break-glass account (P0-05) switches the prod perimeter to dry-run, fixes it, and switches back. Log the incident. |
| Dry-run logs show violations in dev/staging | Expected while building. P1-02 reviews them and adds ingress/egress rules before enforcing. |
| An access policy already exists in the org | Reuse it (import into Terraform). Don't create a second one. |
| Assured Workloads needs projects to be recreated | Acceptable while projects are empty. Do it before any resource is created and update `foundation.yaml`. |
| A constraint name in §6 is wrong or deprecated (e.g. replaced by a "managed" version) | Use the current equivalent from the constraint reference and record the mapping in `hipaa-controls.md`. |
| Someone has enabled STT data logging | Disable it immediately, log an incident, and tell the compliance advisor. Logged data isn't deleted with the project (per the docs), so ask Google support about deletion. |
| An AI Studio API key is found | Delete it, find out who created it and why, and confirm the org-level deny is in place. |

## 9. Security, HIPAA and PHI
- **No PHI is handled.** The projects are still empty. This task is what makes it safe to put PHI into prod later (together with P0-09 and P0-10; DECISIONS #25).
- **Controls added:** service allow-list, US-only locations, no service-account keys, domain-restricted IAM, no public buckets or SQL public IPs, no VM external IPs, an enforced prod perimeter, no Gemini Developer API.
- **Least privilege for this task:** only `gcp-security-admins` members apply `infra/org/`. No service account keys are created to run Terraform.
- **Evidence:** `hipaa-controls.md` with dates and screenshots is the evidence for P0-11 (risk assessment) and P5-14 (HIPAA readiness review).
- **Audit:** policy and perimeter changes appear in Admin Activity audit logs (always on). Alerting on them is P1-07.

## 10. Testing
Terraform: `terraform fmt -check`, `terraform validate`, and a peer-reviewed `terraform plan` before apply.

Negative tests (put them in `docs/runbooks/org-guardrails-tests.md` and run them against `<prefix>-dev`; every one must **fail** with the stated reason):
```bash
gcloud services enable generativelanguage.googleapis.com --project=PREFIX-dev      # restrictServiceUsage error
gcloud services enable bigquery.googleapis.com --project=PREFIX-dev                # not on our allow-list
gcloud storage buckets create gs://PREFIX-dev-loc-test --location=EU --project=PREFIX-dev   # resourceLocations error
gcloud iam service-accounts create guardrail-test --project=PREFIX-dev
gcloud iam service-accounts keys create /dev/null --iam-account=guardrail-test@PREFIX-dev.iam.gserviceaccount.com   # key creation disabled
gcloud projects add-iam-policy-binding PREFIX-dev --member=user:someone@gmail.com --role=roles/viewer   # domain restriction
```
Clean up the test service account afterwards.

Positive checks:
```bash
gcloud org-policies describe gcp.restrictServiceUsage --folder=FOLDER_ID
gcloud org-policies describe gcp.resourceLocations --organization=ORG_ID
gcloud access-context-manager perimeters list --policy=ACCESS_POLICY_ID
gcloud access-context-manager perimeters dry-run describe dai_dev --policy=ACCESS_POLICY_ID
for p in dev staging prod ops; do gcloud services api-keys list --project=PREFIX-$p; done   # expected: empty
```
Perimeter test: with a non-admin test identity outside the perimeter, list objects of a test bucket in `<prefix>-prod`. It must be refused by VPC-SC. Delete the bucket afterwards.

## 11. Acceptance criteria
- [ ] The Assured Workloads vs. own-policies decision is recorded in DECISIONS.md with evidence links (and P0-05 is amended if Assured Workloads was chosen)
- [ ] `allowed_services.yaml` has no `verify` values left; every allowed API is HIPAA-covered or has a logged exception
- [ ] The org policies in §6 (or the Assured Workloads equivalents plus the baseline) are applied by Terraform from `infra/org/`
- [ ] `generativelanguage.googleapis.com` can't be enabled in any project, and no API keys exist in the four projects
- [ ] Creating a resource outside US locations fails
- [ ] The `dai_prod` perimeter is enforced; `dai_dev` and `dai_staging` exist in dry-run; all restrict the agreed services
- [ ] Admins can still manage prod through the ingress rule (checked by an admin)
- [ ] Speech-to-Text data logging is confirmed off (or the API isn't enabled) in all four projects, with dated evidence
- [ ] All negative tests in §10 fail as expected; results are in `hipaa-controls.md`
- [ ] The P0-10, P0-13, P1-02, P1-03, P1-05, P1-06 and P1-07 issues are notified

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI: not applicable (no CI yet). `terraform validate` and the runbook tests were run by hand; P1-06 adds `terraform validate` for `infra/org/` to CI.
- [ ] PR reviewed (HIPAA review if labelled `phi`): plan reviewed by a second engineer; `hipaa-controls.md` reviewed by the compliance advisor; no `phi` label because no PHI is handled
- [ ] No PHI in logs: no PHI exists yet
- [ ] Docs / README updated: `hipaa-controls.md` and the guardrails runbook committed and linked from `docs/compliance/`

## 13. Hand-off
| Task | Can rely on |
|---|---|
| P0-13 Gemini model choice | Gemini only via `aiplatform.googleapis.com`; the covered-list entry name; US locations only (choose a US regional endpoint) |
| P1-02 Terraform base | `allowed_apis` output; perimeters to enforce after reviewing dry-run logs; Cloud Run needs VPC-SC setup; Cloud SQL public IP is already blocked |
| P1-03 / P1-05 Cloud SQL, KMS | Whether CMEK is mandatory everywhere (Assured Workloads) or only where the plan requires it |
| P1-06 CI/CD | `ops` is outside the perimeters; CI needs an ingress rule; no service-account keys possible (use Workload Identity Federation) |
| P1-07 Monitoring | Dry-run violation logs to alert on; policy-change audit events |
| P3-03 Speech-to-Text | Project-level data logging confirmed off; code must not enable it |
| P0-10, P0-11, P5-14 | `docs/compliance/hipaa-controls.md` as evidence |

## 14. Open questions
| Question | Owner | Needed by |
|---|---|---|
| Does Assured Workloads' HCLS boundary cover Cloud Run, Cloud Tasks, Cloud Scheduler, Artifact Registry and the networking APIs? (Decides step 1) | Tech lead | Step 1 |
| If Assured Workloads is chosen: can existing empty projects move into its folder, or must they be recreated? | Tech lead | Step 1 |
| Do VPC-SC ingress rules accept Google groups as identities? | Tech lead | Step 3 |
| Is Memorystore for Redis supported by VPC-SC? If not, how is it protected (private IP only)? | Tech lead | Step 3 |
| Should `staging` get the same enforced perimeter as prod before clinic UAT (P5-07), even though it holds synthetic data only? Proposed: yes, enforced in P1-02. | Tech lead + compliance advisor | P1-02 |

## 15. References
- Plan §3.2, §3.3 (BAA rules: covered products only, no AI Studio keys, no Pre-GA with PHI, no data logging), §6, §8 Phase 0
- Google Cloud HIPAA and supported services: https://docs.cloud.google.com/docs/security/compliance/hipaa
- Restricting resource/service usage: https://docs.cloud.google.com/resource-manager/docs/organization-policy/restricting-resources
- Supported services for restrictServiceUsage: https://docs.cloud.google.com/organization-policy/reference/restrict-services-supported-services.md.txt
- Resource locations: https://docs.cloud.google.com/resource-manager/docs/organization-policy/defining-locations
- VPC-SC supported products: https://docs.cloud.google.com/vpc-service-controls/docs/supported-products
- VPC-SC dry-run mode: https://docs.cloud.google.com/vpc-service-controls/docs/dry-run-mode
- Assured Workloads US Data Boundary for Healthcare and Life Sciences: https://docs.cloud.google.com/assured-workloads/docs/data-boundaries/us-data-boundary-healthcare-life-sciences.md.txt
- Speech-to-Text data logging: https://docs.cloud.google.com/speech-to-text/docs/data-logging
- Terraform Google provider: https://registry.terraform.io/providers/hashicorp/google/latest/docs
- Related tasks: P0-05, P0-10, P0-11, P0-13, P1-02, P1-03, P1-05, P1-06, P1-07, P3-03, P5-07, P5-14
