# Google Cloud bootstrap checks (2026-11-26)

- **Task:** P0-05 ([issue #5](https://github.com/imranfakhrul/dental-clinic-voice-receptionist/issues/5)). These are the spec §10 checks, adapted to a personal account with no organization (DECISIONS #293).
- **Ran:** 2026-11-26, Google Cloud SDK 594.0.1, as the account owner. The owner's email is replaced with `<owner-email>`.
- There's no pull request in this workflow, so this file replaces "save the output in the PR description".
- **Data:** synthetic only. No PHI exists in any project, and none may until the gates in [baa-google-cloud.md](baa-google-cloud.md) are cleared.

## Results
| Check | Expected | Result |
|---|---|---|
| Organization | None (personal account) | ✅ none |
| Four projects, labelled `env` and `system=dental-ai`, `ACTIVE` | dev, staging, prod, ops | ✅ all four |
| Billing linked | `True` for all four | ⏳ **deferred:** no billing account yet (DECISIONS #294; runbook Part B) |
| Project IAM | Only the owner (no organization, so no groups) | ✅ `roles/owner` for `<owner-email>` only |
| Service accounts / keys | None | ✅ 0 service accounts, so no keys |
| Essential contacts: security, technical, billing, legal, suspension | All five categories on all four projects | ✅ `VALID` on all four |
| State bucket `gs://dai-rcpt-ops-tfstate` (versioning, public access prevented) | Exists | ⏳ **pending:** needs billing (task 2.2) |
| Synthetic bucket round-trip and anonymous access refused | Pass | ⏳ **pending:** needs the bucket (task 3.1b) |
| Budget `dental-ai monthly` (USD 50; 50%, 90%, 100%) | Exists | ⏳ **pending:** needs a billing account (task 2.3) |

## APIs enabled by default (input for P0-06)
Google enabled these APIs automatically when each project was created; we didn't enable them. We enabled only `essentialcontacts.googleapis.com`, and only in `dai-rcpt-ops`. P0-06 must check each one against the HIPAA covered-products list and disable those not needed or not covered.

## Raw output
```text
$ gcloud organizations list
(no output: no organization)

$ gcloud projects describe dai-rcpt-<env>  (id, number, labels, state, parent)
dai-rcpt-dev	583464999786	dev	dental-ai	ACTIVE	
dai-rcpt-staging	445637737319	staging	dental-ai	ACTIVE	
dai-rcpt-prod	763436157077	prod	dental-ai	ACTIVE	
dai-rcpt-ops	428568892795	ops	dental-ai	ACTIVE	

$ gcloud billing projects describe dai-rcpt-<env> --format="value(billingEnabled)"
dai-rcpt-dev False
dai-rcpt-staging False
dai-rcpt-prod False
dai-rcpt-ops False

$ gcloud billing accounts list
(no output: no billing account)

$ gcloud projects get-iam-policy dai-rcpt-<env> (role, member)
dai-rcpt-dev:
roles/owner	user:<owner-email>
dai-rcpt-staging:
roles/owner	user:<owner-email>
dai-rcpt-prod:
roles/owner	user:<owner-email>
dai-rcpt-ops:
roles/owner	user:<owner-email>

$ gcloud iam service-accounts keys: user-managed keys per project
dai-rcpt-dev: service accounts = 0
dai-rcpt-staging: service accounts = 0
dai-rcpt-prod: service accounts = 0
dai-rcpt-ops: service accounts = 0

$ gcloud essential-contacts list --project=dai-rcpt-<env>
dai-rcpt-dev: <owner-email>	SECURITY,TECHNICAL,BILLING,LEGAL,SUSPENSION	VALID
dai-rcpt-staging: <owner-email>	SECURITY,TECHNICAL,BILLING,LEGAL,SUSPENSION	VALID
dai-rcpt-prod: <owner-email>	SECURITY,TECHNICAL,BILLING,LEGAL,SUSPENSION	VALID
dai-rcpt-ops: <owner-email>	SECURITY,TECHNICAL,BILLING,LEGAL,SUSPENSION	VALID

$ gcloud services list --enabled --project=dai-rcpt-<env>
dai-rcpt-dev:
  analyticshub.googleapis.com
  apptopology.googleapis.com
  bigquery.googleapis.com
  bigqueryconnection.googleapis.com
  bigquerydatapolicy.googleapis.com
  bigquerydatatransfer.googleapis.com
  bigquerymigration.googleapis.com
  bigqueryreservation.googleapis.com
  bigquerystorage.googleapis.com
  cloudapis.googleapis.com
  cloudtrace.googleapis.com
  dataform.googleapis.com
  dataplex.googleapis.com
  datastore.googleapis.com
  logging.googleapis.com
  monitoring.googleapis.com
  servicemanagement.googleapis.com
  serviceusage.googleapis.com
  sql-component.googleapis.com
  storage-api.googleapis.com
  storage-component.googleapis.com
  storage.googleapis.com
  telemetry.googleapis.com
dai-rcpt-staging:
  analyticshub.googleapis.com
  apptopology.googleapis.com
  bigquery.googleapis.com
  bigqueryconnection.googleapis.com
  bigquerydatapolicy.googleapis.com
  bigquerydatatransfer.googleapis.com
  bigquerymigration.googleapis.com
  bigqueryreservation.googleapis.com
  bigquerystorage.googleapis.com
  cloudapis.googleapis.com
  cloudtrace.googleapis.com
  dataform.googleapis.com
  dataplex.googleapis.com
  datastore.googleapis.com
  logging.googleapis.com
  monitoring.googleapis.com
  servicemanagement.googleapis.com
  serviceusage.googleapis.com
  sql-component.googleapis.com
  storage-api.googleapis.com
  storage-component.googleapis.com
  storage.googleapis.com
  telemetry.googleapis.com
dai-rcpt-prod:
  analyticshub.googleapis.com
  apptopology.googleapis.com
  bigquery.googleapis.com
  bigqueryconnection.googleapis.com
  bigquerydatapolicy.googleapis.com
  bigquerydatatransfer.googleapis.com
  bigquerymigration.googleapis.com
  bigqueryreservation.googleapis.com
  bigquerystorage.googleapis.com
  cloudapis.googleapis.com
  cloudtrace.googleapis.com
  dataform.googleapis.com
  dataplex.googleapis.com
  datastore.googleapis.com
  logging.googleapis.com
  monitoring.googleapis.com
  servicemanagement.googleapis.com
  serviceusage.googleapis.com
  sql-component.googleapis.com
  storage-api.googleapis.com
  storage-component.googleapis.com
  storage.googleapis.com
  telemetry.googleapis.com
dai-rcpt-ops:
  analyticshub.googleapis.com
  apptopology.googleapis.com
  bigquery.googleapis.com
  bigqueryconnection.googleapis.com
  bigquerydatapolicy.googleapis.com
  bigquerydatatransfer.googleapis.com
  bigquerymigration.googleapis.com
  bigqueryreservation.googleapis.com
  bigquerystorage.googleapis.com
  cloudapis.googleapis.com
  cloudtrace.googleapis.com
  dataform.googleapis.com
  dataplex.googleapis.com
  datastore.googleapis.com
  essentialcontacts.googleapis.com
  logging.googleapis.com
  monitoring.googleapis.com
  servicemanagement.googleapis.com
  serviceusage.googleapis.com
  sql-component.googleapis.com
  storage-api.googleapis.com
  storage-component.googleapis.com
  storage.googleapis.com
  telemetry.googleapis.com
```
