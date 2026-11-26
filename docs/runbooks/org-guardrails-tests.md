# Runbook: HIPAA guardrails tests (P0-06)

- **Evidence:** [hipaa-controls.md](../compliance/hipaa-controls.md)
- **Allow-list:** [infra/org/allowed_services.yaml](../../infra/org/allowed_services.yaml)
- **Terraform:** [infra/org/](../../infra/org/main.tf)
- **Re-run** the relevant part after **any** change to the allow-list, the policies or the perimeters, and add the dated results to `hipaa-controls.md`.

```bash
PREFIX=dai-rcpt
OPS=--billing-project=$PREFIX-ops     # quota project for Org Policy / API Keys calls
```

## A. Now (personal account, no organization)

### A1. Only allowed APIs are enabled
```bash
for p in dev staging prod ops; do echo "$PREFIX-$p:"; gcloud services list --enabled --project=$PREFIX-$p --format="value(config.name)"; done
```
**Expected:** only APIs from `allowed_services.yaml` (`services` for dev, staging and prod; `ops_services` for ops), plus `always_on` and `aliases`.
- **If an unexpected API appears:** disable it, without `--force`. If Google refuses with `COMMON_SU_SERVICE_HAS_DEPENDENT_SERVICES`, disable the dependent service it names first.
- **Known leftover:** `cloudtrace` and `sql-component` in ops.

### A2. No Gemini Developer API, no API keys, no Speech-to-Text yet
```bash
for p in dev staging prod ops; do gcloud services list --enabled --project=$PREFIX-$p --format="value(config.name)" | grep -E "generativelanguage|speech" ; done   # expected: nothing
gcloud services enable apikeys.googleapis.com --project=$PREFIX-ops          # temporary
for p in dev staging prod ops; do gcloud services api-keys list --project=$PREFIX-$p $OPS; done   # expected: empty
gcloud services disable apikeys.googleapis.com --project=$PREFIX-ops
```
**If a key is found:** delete it, find out who created it and why, and log an incident (spec §8).

### A3. Speech-to-Text data logging
- **While `speech.googleapis.com` is off everywhere:** record "API not enabled; logging cannot be on".
- **Once P3-03 enables it:** open the console → APIs & Services → Cloud Speech API → **Data logging** tab, in each project. The tab must offer "Enable data logging", meaning it's off. Take a dated screenshot for `hipaa-controls.md`.

## B. Terraform checks (any time)
```bash
cd infra/org
terraform init -backend=false && terraform fmt -check && terraform validate
```
Until the organization exists, `example.tfvars` holds fake org, folder and customer IDs.

## When the organization exists
**Needs:** P0-05 runbook Part C (company domain, organization, folder `dental-ai`, groups, break-glass admins) and Part B (state bucket).

1. Copy `example.tfvars` to `terraform.tfvars` and fill in the real `org_id`, `folder_id`, `directory_customer_id` and `admin_groups` from `infra/bootstrap/foundation.yaml`. These are identifiers, not secrets.
2. If an access policy already exists in the organization, import it; don't create a second one:
   ```bash
   gcloud access-context-manager policies list --organization=ORG_ID
   terraform import google_access_context_manager_access_policy.org accessPolicies/POLICY_ID
   ```
3. As a member of `gcp-security-admins`:
   ```bash
   gcloud auth application-default login
   terraform init && terraform plan -out=org.plan
   ```
   A second engineer reviews the plan.
4. Apply in the spec §7 step 4 order, using `-target` per step:
   1. the Gemini Developer API deny and locations;
   2. the boolean constraints, the domain restriction and the VM external IP rule;
   3. the folder allow-list;
   4. the ops override;
   5. the access policy and the perimeters.
5. Run sections A and C. Record the results in `hipaa-controls.md` and change each ⏳ to ✅.
6. Disable the leftover `cloudtrace` and `sql-component` in ops if they're still there.

## C. Negative and positive tests (spec §10; only with the organization)
Run them against `$PREFIX-dev`. **Every** negative test must **fail** for the stated reason.
```bash
gcloud services enable generativelanguage.googleapis.com --project=$PREFIX-dev       # restrictServiceUsage error
gcloud services enable bigquery.googleapis.com --project=$PREFIX-dev                 # not on the allow-list
gcloud storage buckets create gs://$PREFIX-dev-loc-test --location=EU --project=$PREFIX-dev   # resourceLocations error
gcloud iam service-accounts create guardrail-test --project=$PREFIX-dev
gcloud iam service-accounts keys create /dev/null --iam-account=guardrail-test@$PREFIX-dev.iam.gserviceaccount.com   # key creation disabled
gcloud projects add-iam-policy-binding $PREFIX-dev --member=user:outsider@example.com --role=roles/viewer   # domain restriction
gcloud iam service-accounts delete guardrail-test@$PREFIX-dev.iam.gserviceaccount.com --quiet      # clean-up
```
**Important:** if a negative test **succeeds**, the control is missing. Undo what the test created right away (disable the API, delete the bucket or the binding), then fix the policy.

Positive checks:
```bash
gcloud org-policies describe gcp.restrictServiceUsage --folder=FOLDER_ID
gcloud org-policies describe gcp.resourceLocations --organization=ORG_ID
gcloud access-context-manager perimeters list --policy=ACCESS_POLICY_ID
gcloud access-context-manager perimeters dry-run describe dai_dev --policy=ACCESS_POLICY_ID
```

**Perimeter test:**
1. Create a test bucket in `$PREFIX-prod`.
2. With a non-admin identity outside the perimeter, list its objects. VPC-SC must refuse.
3. Have an admin, through the ingress rule, list it. This must work.
4. Delete the bucket.
