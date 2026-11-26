# Runbook: Google Cloud bootstrap (P0-05)

- **IDs:** [infra/bootstrap/foundation.yaml](../../infra/bootstrap/foundation.yaml) · **Checks:** [bootstrap-checks-2026-11-26.md](../compliance/bootstrap-checks-2026-11-26.md) · **BAA:** [baa-google-cloud.md](../compliance/baa-google-cloud.md) (**NOT ACCEPTED**)
- **Account:** a personal Google account, so there's no organization (DECISIONS #293). Part A below is what was actually run. Part B needs a billing account. Part C is for later, once a company domain exists.
- **Rule:** synthetic data only. No PHI in any project until every gate in the BAA record is cleared.

## Setup
```bash
# Google Cloud CLI (any install works; this one doesn't touch the system)
curl -fsSL -o gcli.tar.gz https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-linux-x86_64.tar.gz
tar -xzf gcli.tar.gz && export PATH="$PWD/google-cloud-sdk/bin:$PATH"
gcloud auth login                       # the account owner signs in in the browser
gcloud organizations list               # personal account: no output
gcloud billing accounts list            # 2026-11-26: no billing account
```

## Part A: done on 2026-11-26
```bash
# 1. Four projects with labels (Google enables a default set of APIs on each one; see the checks file)
for env in dev staging prod ops; do
  gcloud projects create dai-rcpt-$env --name="Dental AI $env" --labels=env=$env,system=dental-ai
done

# 2. Essential contacts on each project (no organization, so project level).
#    The API is enabled only in ops, and ops is used as the quota project.
gcloud services enable essentialcontacts.googleapis.com --project=dai-rcpt-ops
EMAIL=$(gcloud auth list --filter=status:ACTIVE --format="value(account)")   # the account owner; never written to the repo
for env in dev staging prod ops; do
  gcloud essential-contacts create --project=dai-rcpt-$env --billing-project=dai-rcpt-ops --email="$EMAIL" \
    --notification-categories=security,technical,billing,legal,suspension --language=en-US
done
```
**Note:** right after a project is created, calls that use it as the quota project can fail for a few minutes with `USER_PROJECT_DENIED` ("Caller does not have required permission to use project"), even for the owner, while IAM propagates. Wait and retry; it happened on 2026-11-26 and cleared within minutes.

## Part B: pending, once a billing account exists
Create a billing account in the console (https://console.cloud.google.com/billing → **Create account**). Then:
```bash
BILLING=XXXXXX-XXXXXX-XXXXXX            # from: gcloud billing accounts list
# 1. Link billing (task 2.1b)
for env in dev staging prod ops; do gcloud billing projects link dai-rcpt-$env --billing-account=$BILLING; done

# 2. Terraform state bucket (task 2.2)
gcloud storage buckets create gs://dai-rcpt-ops-tfstate --project=dai-rcpt-ops --location=US \
  --uniform-bucket-level-access --public-access-prevention
gcloud storage buckets update gs://dai-rcpt-ops-tfstate --versioning

# 3. Budget USD 50 with 50/90/100% alerts on the four projects (task 2.3)
gcloud services enable billingbudgets.googleapis.com --project=dai-rcpt-ops
gcloud billing budgets create --billing-account=$BILLING --display-name="dental-ai monthly" --budget-amount=50USD \
  --filter-projects=projects/583464999786,projects/445637737319,projects/763436157077,projects/428568892795 \
  --threshold-rule=percent=0.5 --threshold-rule=percent=0.9 --threshold-rule=percent=1.0 --billing-project=dai-rcpt-ops

# 4. Synthetic bucket test (task 3.1b): write, read, list versions, delete, then anonymous access must fail
echo '{"synthetic": true, "purpose": "bootstrap test"}' > synthetic-test.json
gcloud storage cp synthetic-test.json gs://dai-rcpt-ops-tfstate/_bootstrap/synthetic-test.json
gcloud storage cat gs://dai-rcpt-ops-tfstate/_bootstrap/synthetic-test.json
gcloud storage ls --all-versions gs://dai-rcpt-ops-tfstate/_bootstrap/
gcloud storage rm gs://dai-rcpt-ops-tfstate/_bootstrap/synthetic-test.json
curl -s -o /dev/null -w "%{http_code}\n" https://storage.googleapis.com/dai-rcpt-ops-tfstate/_bootstrap/synthetic-test.json   # expect 401/403

# 5. Checks (spec §10)
for env in dev staging prod ops; do gcloud billing projects describe dai-rcpt-$env --format="value(billingEnabled)"; done   # all True
gcloud storage buckets describe gs://dai-rcpt-ops-tfstate --format="value(versioning_enabled,public_access_prevention)"
gcloud billing budgets list --billing-account=$BILLING --billing-project=dai-rcpt-ops
```
Then record the masked billing ID in `foundation.yaml`, add the results to a new dated checks file, and tick tasks 2.1b, 2.2, 2.3 and 3.1b.

## Part C: later, with a company domain (required before real PHI)
These are the P0-05 spec §7 steps that a personal account can't do:
1. Get a company domain with Google Workspace, or Cloud Identity verified by DNS. The organization resource appears when a super-admin signs in to the console.
2. Create two break-glass super-admins with hardware security keys, enforce 2-step verification for admins, and create the groups `gcp-org-admins@`, `gcp-billing-admins@`, `gcp-security-admins@` and `gcp-developers@`.
3. Remove the default domain-wide `roles/resourcemanager.projectCreator` and `roles/billing.creator` grants. Grant IAM to the groups only (spec §6 table), and remove any `user:` bindings.
4. Create the folder `dental-ai`, then **move** (don't recreate) the four projects into it:
   ```bash
   gcloud resource-manager folders create --display-name=dental-ai --organization=ORG_ID
   for env in dev staging prod ops; do gcloud beta projects move dai-rcpt-$env --folder=FOLDER_ID; done
   ```
5. Move the essential contacts to org level (`gcloud essential-contacts create --organization=ORG_ID …`).
6. Fill in the org, folder and group fields in `foundation.yaml`, and add a DECISIONS row.
