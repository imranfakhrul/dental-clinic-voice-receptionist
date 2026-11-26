# HIPAA technical controls (P0-06)

- **Task:** P0-06 ([issue #6](https://github.com/imranfakhrul/dental-clinic-voice-receptionist/issues/6)).
- **Checked:** 2026-11-26, as the account owner (email shown as `<owner-email>`).
- **Setup:** a personal Google account with **no organization** and **no billing account** (DECISIONS #293, #294). Every project holds synthetic data only, and **no PHI may enter any project** (see [baa-google-cloud.md](baa-google-cloud.md)).
- **Related files:**
  - allow-list: [`infra/org/allowed_services.yaml`](../../infra/org/allowed_services.yaml)
  - Terraform: [`infra/org/`](../../infra/org/main.tf)
  - tests: [`docs/runbooks/org-guardrails-tests.md`](../runbooks/org-guardrails-tests.md)
  - decisions: DECISIONS #295, #296

## 1. Assured Workloads or our own policies (spec §7 step 1)
**Decision: our own policies** (DECISIONS #295).
- **Source:** [US Data Boundary for Healthcare and Life Sciences](https://docs.cloud.google.com/assured-workloads/docs/data-boundaries/us-data-boundary-healthcare-life-sciences.md.txt), in-scope products checked 2026-11-26.
- **Rule from spec §7:** use Assured Workloads only if every API we need is in scope. It isn't.

| Our API | In Assured Workloads HCLS scope? |
|---|---|
| `aiplatform` (as "Generative AI on Vertex AI"), `speech`, `texttospeech`, `run`, `sqladmin`, `redis` ("Memorystore for Redis"), `cloudtasks`, `cloudscheduler`, `secretmanager`, `cloudkms`, `storage`, `artifactregistry`, `compute` | Yes |
| `identitytoolkit` (Identity Platform, staff MFA) | **No** |
| `cloudtrace` (Cloud Trace); the Cloud Run Trace integration is also listed as unsupported | **No** |
| `vpcaccess` (Serverless VPC Access), `servicenetworking` | **No** |

**Other reasons it doesn't fit now:**
- Assured Workloads needs an organization and creates its own folder.
- It sets `gcp.restrictNonCmekServices`, which makes CMEK mandatory for in-scope services.
- It denies TLS 1.0/1.1.

**Effect on other tasks:** CMEK stays required only where the plan requires it (P1-03, P1-05). P5-14 should re-check the in-scope list.

## 2. Allowed services
The full columns and sources are in `allowed_services.yaml` (checked 2026-11-26).

| API | Purpose | HIPAA covered | restrictServiceUsage | VPC-SC perimeter |
|---|---|---|---|---|
| `aiplatform` | Gemini via Vertex AI | Yes ("Generative AI on Agent Platform") | Yes | Yes |
| `speech` | Speech-to-Text | Yes | Yes | Yes |
| `texttospeech` | Text-to-Speech | Yes | Yes | Yes |
| `run` | Cloud Run | Yes | Yes | Yes (extra setup, P1-02) |
| `sqladmin` | Cloud SQL | Yes | Yes | Yes (Admin API only) |
| `redis` | Memorystore | Yes | Yes | Yes (GA) |
| `cloudtasks` | Jobs | Yes | Yes | Yes |
| `cloudscheduler` | Scheduled jobs | Yes | Yes | Yes |
| `secretmanager` | Secrets | Yes | Yes | Yes |
| `cloudkms` | Keys | Yes | Yes | Yes |
| `storage` | Buckets | Yes | Yes | Yes |
| `artifactregistry` | Images | Yes | Yes | Yes |
| `compute` | VPC networking | Yes | Yes | Yes |
| `cloudtrace` | Tracing | Yes | Yes | Yes |
| `identitytoolkit` | Staff login, MFA | Yes | **No**: IAM only | Yes |
| `servicenetworking` | Private IP peering | **No**: exception #295, never PHI | **No**: IAM only | No |

**Dropped:**
- `vpcaccess`: P1-02 uses Cloud Run Direct VPC egress instead.
- `generativelanguage`: never allowed.

**`dai-rcpt-ops` short list** (never holds PHI): `storage`, `essentialcontacts`, `orgpolicy`, `billingbudgets`, `iamcredentials`, `sts`. The admin-only APIs have exception #295.

## 3. Controls and their status
**Statuses:**
- ✅ **enforced**: in place now.
- 🟡 **project-level substitute**: a weaker stand-in, in place now.
- ⏳ **pending**: written in Terraform, waiting for an organization.

| Control (spec §6) | Status | Detail |
|---|---|---|
| Service allow-list (`gcp.restrictServiceUsage`, folder) | 🟡 / ⏳ | **Substitute:** on 2026-11-26 the 13 default APIs not on the list, plus the `cloudapis` bundle, were disabled in all four projects (§4.1). Only the project Owner (you) can enable APIs. **Pending:** the policy itself (needs an organization). |
| Gemini Developer API denied (org) | 🟡 / ⏳ | **Substitute:** not enabled in any project, and 0 API keys (§4.3). **Pending:** the deny policy. |
| US-only locations (`gcp.resourceLocations`) | ⏳ | Needs an organization (§4.2). No resources exist yet, so nothing is outside the US. |
| `iam.disableServiceAccountKeyCreation` | 🟡 / ⏳ | **Substitute:** 0 service accounts, so 0 keys (P0-05 checks). **Pending:** the policy. |
| `iam.allowedPolicyMemberDomains` | ⏳ | Needs an organization and a company domain. Today the only IAM member is the owner. |
| `iam.automaticIamGrantsForDefaultServiceAccounts` | ⏳ | Needs an organization. No default service accounts exist yet. |
| `storage.uniformBucketLevelAccess`, `storage.publicAccessPrevention` | ⏳ | Needs an organization. No buckets yet; the state bucket is created with both flags (P0-05 Part B). |
| `sql.restrictPublicIp` | ⏳ | Needs an organization. No Cloud SQL yet (P1-03 must use private IP). |
| `compute.vmExternalIpAccess` | ⏳ | Needs an organization. No VMs are planned. |
| VPC-SC perimeters `dai_prod` (enforced), `dai_dev` and `dai_staging` (dry-run) | ⏳ | Needs an organization: `access-context-manager policies list` requires `organizations/<number>`. |
| Speech-to-Text data logging off | ✅ | The API isn't enabled in any project, so logging can't be on (§4.3). **P3-03 must re-check it**, with a screenshot, when it enables the API. |
| Terraform `infra/org/` | ⏳ | `fmt -check` and `validate` pass (Terraform 1.17.2, provider `hashicorp/google` 7.46.2). It isn't applied: needs an organization and the state bucket. |

**Constraint names:** all 10 names in spec §6 exist in Google's [constraint reference](https://docs.cloud.google.com/organization-policy/reference/org-policy-constraints), checked 2026-11-26, with no deprecation note. Google also offers `managed` versions (for example `iam.managed.disableServiceAccountKeyCreation`); reconsider them at the first real `plan`.

## 4. Evidence (2026-11-26)

### 4.1 Default APIs disabled (task 3.1)
- **Disabled in all four projects:** the bundle `cloudapis.googleapis.com` first, because it depends on the defaults and Google refused the others with `COMMON_SU_SERVICE_HAS_DEPENDENT_SERVICES` while it was on.
- **Then:** `dataform`, `dataplex`, `analyticshub`, `apptopology`, `datastore`, `telemetry`, `bigquerymigration`, `bigqueryreservation`, `bigquerydatatransfer`, `bigquerydatapolicy`, `bigqueryconnection`, `bigquerystorage`, `bigquery`.
- `--force` was never used. Enabled APIs afterwards:
```text
dai-rcpt-dev:     cloudtrace logging monitoring servicemanagement serviceusage sql-component storage-api storage-component storage
dai-rcpt-staging: cloudtrace logging monitoring servicemanagement serviceusage sql-component storage-api storage-component storage
dai-rcpt-prod:    cloudtrace logging monitoring servicemanagement serviceusage sql-component storage-api storage-component storage
dai-rcpt-ops:     cloudtrace essentialcontacts logging monitoring orgpolicy servicemanagement serviceusage sql-component storage-api storage-component storage
```
(all `.googleapis.com`; `orgpolicy` was enabled in ops by task 3.2.)
- **Known leftover:** `dai-rcpt-ops` still has the defaults `cloudtrace` and `sql-component`, which aren't on its short list. They hold no data and cost nothing; disable them on the next ops change.

### 4.2 Project-level org policy probe (tasks 3.2 and 3.3)
```text
$ gcloud services enable orgpolicy.googleapis.com --project=dai-rcpt-ops
Operation "operations/acat.p2-428568892795-..." finished successfully.

$ gcloud org-policies set-policy probe-locations.yaml --billing-project=dai-rcpt-ops
  # gcp.resourceLocations = in:us-locations on projects/dai-rcpt-dev
ERROR: (gcloud.org-policies.set-policy) [<owner-email>] does not have permission to access projects instance [dai-rcpt-dev]
(or it may not exist): Permission 'orgpolicy.policies.create' denied on resource
'//cloudresourcemanager.googleapis.com/projects/dai-rcpt-dev' (or it may not exist).
  reason: IAM_PERMISSION_DENIED
```
**Result:** org policies **can't** be set without an organization. Even the project Owner lacks `orgpolicy.policies.create`, which comes with the Org Policy Administrator role, granted on an organization. So no project-level policies were applied, and `infra/org/project-level/` wasn't created (design decision 4, "if it fails").

### 4.3 API keys, Gemini Developer API and Speech-to-Text (task 3.4)
```text
$ gcloud services enable apikeys.googleapis.com --project=dai-rcpt-ops   # temporary, for the key check
$ gcloud services api-keys list --project=dai-rcpt-<env> --billing-project=dai-rcpt-ops
dai-rcpt-dev: keys = 0
dai-rcpt-staging: keys = 0
dai-rcpt-prod: keys = 0
dai-rcpt-ops: keys = 0
$ gcloud services disable apikeys.googleapis.com --project=dai-rcpt-ops
$ gcloud services list --enabled --project=dai-rcpt-<env> | grep -E "generativelanguage|speech|apikeys"
0 matches in each of the four projects
```

### 4.4 Negative tests (task 3.5)
Every spec §10 negative test checks a policy that couldn't be applied. Running one now would **succeed** and change the account (for example, actually enabling the Gemini Developer API), so none was run.

| Test (spec §10) | Result |
|---|---|
| Enable `generativelanguage` → restrictServiceUsage error | Not run: control pending |
| Enable `bigquery` → not on allow-list | Not run: control pending (BigQuery is disabled, but the owner could re-enable it) |
| Bucket in `EU` → resourceLocations error | Not run: control pending |
| Create a service-account key → key creation disabled | Not run: control pending |
| Add an outside `user:` → domain restriction | Not run: control pending |
| Perimeter: outside identity reads a prod bucket → VPC-SC refusal | Not run: no perimeter, no bucket |
| **Positive:** API keys list empty | ✅ Passed (§4.3) |

## 5. Before real PHI
Everything marked ⏳ is in the "Pending before real PHI" list in [README.md](README.md#pending-before-real-phi). To clear it, follow the steps in the [guardrails runbook](../runbooks/org-guardrails-tests.md#when-the-organization-exists). The runbook needs an organization (P0-05 runbook Part C) and the state bucket (Part B).
