# Design: P0-06 HIPAA guardrails (personal account, no organization)

## Context

- See proposal.md, Why. P0-05 created four projects (`dai-rcpt-{dev,staging,prod,ops}`) in a personal account. There's no organization, folder, groups or billing (DECISIONS #293, #294; `infra/bootstrap/foundation.yaml`).
- **Read-only checks on 2026-11-26:**
  - `access-context-manager policies list` needs `organizations/<number>`, so VPC-SC is impossible now.
  - The Org Policy API isn't enabled anywhere, so whether project-level policies work without an organization is still unknown.
  - `generativelanguage`, `speech` and `apikeys` aren't enabled in any project.
  - Terraform isn't installed.
- **Already recorded:**
  - Google enabled 23 default APIs in each project (`docs/compliance/bootstrap-checks-2026-11-26.md`).
  - The covered-products snapshot is in `docs/compliance/baa-google-cloud.md`. Every plan §3.2 service is covered; Gemini appears as "Generative AI on Agent Platform".

## Goals / Non-Goals

**Goals:**
- Finished, validated guardrail code that can be applied without rework once an organization exists.
- Every control that works at project level done for real now, with dated evidence.
- An honest record: each control marked enforced, project-level substitute, or pending, with what it waits for.

**Non-Goals:**
- Applying org/folder policies, Assured Workloads or VPC-SC (needs an organization).
- A Terraform apply of any kind (needs the state bucket from P0-05 Part B).
- Networks, restricted VIP and Cloud Run perimeter setup (P1-02); CMEK keys (P1-03, P1-05); the CI ingress rule (P1-06); alerting on violations (P1-07).

## Decisions

1. **Assured Workloads: decide from the docs now, choose finally with the organization.**
   - During apply, fetch Google's "US Data Boundary for Healthcare and Life Sciences" page and compare its in-scope products with every candidate API.
   - Record the comparison and a recommendation in `hipaa-controls.md` and DECISIONS.
   - Assured Workloads needs an organization and its own folder, so nothing is created now.
   - *Alternative:* skip the comparison until an organization exists. Rejected, because spec §5 asks for it from the docs, and it decides whether CMEK becomes mandatory (P1-03, P1-05).
2. **The allow-list is built from three live sources** (spec §6 format):
   - the HIPAA covered list (the P0-05 snapshot, re-checked for the extra APIs);
   - the `gcp.restrictServiceUsage` supported-services list;
   - the VPC-SC supported-products page.

   Each `verify` becomes `yes` or `no`. A `no` for "covered" drops the API, unless it never touches PHI, in which case it gets a DECISIONS exception (for example, the CI-only APIs in `ops`).
3. **Terraform is written in full but not applied.**
   - `infra/org/` follows spec §6: `backend.tf` points at `gs://dai-rcpt-ops-tfstate`, prefix `org/`; the allow-list is read with `yamldecode(file(...))`.
   - `example.tfvars` uses obviously fake org and folder IDs, plus the real project numbers.
   - Checked with `terraform init -backend=false`, `terraform fmt -check` and `terraform validate`. Argument names are checked against the current `hashicorp/google` provider schema (the `validate` itself does this).
   - No `terraform.tfvars` with real org IDs yet, because none exist.
   - The Terraform CLI goes in the scratchpad from HashiCorp's official release zip, with its checksum verified.
4. **Probe project-level org policies (one reversible step, after the user says yes).**
   - Enable `orgpolicy.googleapis.com` in `dai-rcpt-ops` only, and call with `--billing-project=dai-rcpt-ops`.
   - Try setting `gcp.resourceLocations = in:us-locations` on `dai-rcpt-dev`.
   - **If it works:** apply the project-level equivalents to all four projects with `gcloud org-policies set-policy`, from YAML files in `infra/org/project-level/`. These are the Gemini Developer API deny, the service allow-list (ops gets its own short list), US locations, and the baseline constraints. Then run the matching negative tests.
   - **If it fails:** record the exact error; every policy becomes pending.
   - When the organization exists, Terraform takes over at org/folder level, and the project-level policies are deleted (a runbook step), so there's one source of truth.
   - *Alternative:* Terraform with local state for the project-level policies. Rejected: no durable state location, and the repo is public.
5. **Disable the default APIs that aren't on the allow-list** in all four projects, after the user says yes.
   - This is the project-level substitute for the service allow-list, and it works with or without org policies.
   - Always-on services (Logging, Monitoring, Service Usage, Service Management, and the others Google won't let you disable) are kept and listed.
   - Dependent APIs are disabled in dependency order, not with `--force`, so nothing that's needed is removed silently.
   - Output is saved for the evidence file.
6. **Key and Gemini Developer API checks.**
   - `generativelanguage.googleapis.com` must be absent from `services list --enabled` in all four projects.
   - API keys are listed with `gcloud services api-keys list --project=<id> --billing-project=dai-rcpt-ops`. If the API Keys API must be enabled for that, it's enabled in ops only, after the user says yes.
7. **Speech-to-Text data logging.**
   - The API isn't enabled anywhere, and data logging can only be turned on in the console with the API enabled. So we record "API not enabled; logging cannot be on" for each project, with the date and the services-list output as evidence.
   - P3-03 re-checks it with a screenshot when it enables the API.
8. **Negative tests run only against an applied control.**
   - A test against a control that isn't in place would *succeed* and change the account (for example, actually enabling the Gemini Developer API). So each test is run only if its control was applied. Otherwise it's marked "not run: control pending".
   - The runbook keeps the spec §10 tests unchanged, for when the organization exists.
9. **Records.**
   - `hipaa-controls.md`: the decision, the allow-list table, and a controls table with the status of each (enforced / project-level / pending), the checks with dates, and the test results.
   - A DECISIONS row (next number 295).
   - In `docs/compliance/README.md`, the pending list gains the org-level policies, VPC-SC and the Terraform apply; the notifications table gains P0-13, P1-02, P1-03/P1-05, P1-06, P1-07 and P0-10.
   - README link; Phase 0 README #6 status.

## Risks / Trade-offs

- **[Project-level org policies may not work without an organization]** → The probe decides; both outcomes are planned for, and nothing is assumed.
- **[Disabling a default API could break a later task]** → Only APIs off the allow-list are disabled; any of them can be re-enabled in seconds with a DECISIONS row. The projects are empty.
- **[Terraform untested against a real organization]** → `validate` checks the schema only. The first real `plan` happens with the organization and is reviewed before apply (spec §7 step 3).
- **[Google pages change]** → The allow-list records `checked_on` and the source URLs; P5-14 re-checks them.
- **[The public repo shows the guardrail design]** → It contains only IDs and policy names, no secrets; the example org and folder IDs are fake.

## Migration Plan

When the organization exists:
1. Fill in `terraform.tfvars` from `foundation.yaml`.
2. Run `terraform plan`, have it reviewed, and apply in the spec §7 step 4 order.
3. Delete the project-level policies.
4. Run the full spec §10 tests.

To roll back the project-level work: `gcloud org-policies delete` for each policy, and `gcloud services enable` for any API.
