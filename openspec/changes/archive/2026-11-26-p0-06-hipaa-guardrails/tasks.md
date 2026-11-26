# Tasks: P0-06 HIPAA guardrails (issue #6)

## 1. Research and decisions (read-only)

- [x] 1.1 Fetch Google's "US Data Boundary for Healthcare and Life Sciences" page and compare its in-scope products with every candidate API (spec §6). Verify: the comparison table and a recommendation are ready for `hipaa-controls.md`, and the open question on Cloud Run, Tasks, Scheduler, Artifact Registry and networking is answered.
- [x] 1.2 Fetch the `gcp.restrictServiceUsage` supported-services list and the VPC-SC supported-products page. Re-check the HIPAA list for the APIs not in the P0-05 snapshot (`compute`, `vpcaccess`, `servicenetworking`, `iamcredentials`, `sts`). Answer the open questions: Memorystore VPC-SC support, and Google groups in ingress rules. Verify: every candidate API has a yes/no for each of the three columns.

## 2. Allow-list and Terraform (no cloud changes)

- [x] 2.1 Write `infra/org/allowed_services.yaml` (spec §6 format, `checked_on`, source URLs) with the PHI-project list and the ops short list. Log a DECISIONS exception for any kept API that isn't covered but never touches PHI. Verify: it parses, and `grep -c verify` on the value columns is 0.
- [x] 2.2 Install the Terraform CLI in the scratchpad from HashiCorp's release zip, with the checksum verified. Verify: `terraform version` prints a version.
- [x] 2.3 Write `infra/org/` (`backend.tf`, `variables.tf`, `main.tf`, `outputs.tf`, `example.tfvars`) with the org policies, the access policy, the three perimeters and the admin ingress rule. The allow-list is read from the YAML. Verify: `terraform init -backend=false`, `terraform fmt -check` and `terraform validate` pass.

## 3. Project-level controls in Google Cloud (each mutating step only after the user says yes)

- [x] 3.1 Disable, in all four projects, the default APIs that aren't on the allow-list (dependency order, no `--force`), and list the ones Google keeps always on. Verify: `services list --enabled` shows only allowed or always-on APIs, saved for evidence.
- [x] 3.2 Probe: enable `orgpolicy.googleapis.com` in `dai-rcpt-ops` only and try `gcp.resourceLocations = in:us-locations` on `dai-rcpt-dev`. Verify: the result (works / exact error) is recorded.
- [x] 3.3 If the probe works: write `infra/org/project-level/*.yaml` and apply the project-level policies to the four projects (Gemini Developer API deny, service allow-list with the ops short list, US locations, baseline constraints). If it doesn't: mark every policy pending. Verify: `gcloud org-policies list --project=<id>` matches the files, or the pending reason is recorded.
- [x] 3.4 Checks: the Gemini Developer API isn't enabled in any project; no API keys exist (enable the API Keys API in ops only if needed); Speech-to-Text data logging is recorded as "API not enabled; logging cannot be on" for each project. Verify: dated output saved.
- [x] 3.5 Run the negative tests from spec §10 whose control was applied in 3.3; mark the others "not run: control pending". Clean up any test resources. Verify: each run test was refused for the stated reason.

## 4. Records

- [x] 4.1 Write `docs/compliance/hipaa-controls.md`: the Assured Workloads comparison and recommendation, the allow-list table, a controls table (enforced / project-level / pending, with what each waits for), the checks with dates, and the test results. Verify: every spec §6 control appears with a status.
- [x] 4.2 Write `docs/runbooks/org-guardrails-tests.md`: the spec §10 negative and positive tests for the organization, the project-level variants used now, and the migration steps (apply Terraform, delete project-level policies). Verify: the commands match what was run.
- [x] 4.3 Append the DECISIONS row (next number 295). Update `docs/compliance/README.md`: the pending list (org-level policies, VPC-SC, Terraform apply, Assured Workloads choice) and the notifications table (P0-10, P0-13, P1-02, P1-03/P1-05, P1-06, P1-07). Verify: the rows are present.
- [x] 4.4 Link the new docs from the root README and `docs/compliance/README.md`. Set #6 in the Phase 0 README to its honest status. Run the public-repo scan (personal emails, billing ID) and the link check. Verify: the scan is clean and there are no broken links.

## 5. Finish (only after the user's review)

- [x] 5.1 After the user has reviewed the work and given the go-ahead, archive the change (sync the `hipaa-guardrails` spec), commit with a one-line descriptive message, push `feature/phase-0-discovery-compliance`, and close issue #6 with a comment listing the files and the pending items. Do none of these before the user says so. Verify: one commit, the branch matches origin, and #6 is closed under #17.
