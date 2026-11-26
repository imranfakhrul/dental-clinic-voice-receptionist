# Proposal: P0-06 Restrict projects to HIPAA-covered products (issue #6)

## Why

Google's BAA covers only the services on its HIPAA supported-services list. Guardrails that **prevent** a mistake are much stronger than rules people must remember. The guardrails needed are:
- a service allow-list;
- US-only locations;
- baseline security constraints;
- VPC Service Controls perimeters;
- no Gemini Developer API (AI Studio) keys;
- Speech-to-Text data logging kept off.

P0-13 and P1-02 depend on this task, and P5-14 audits it.

**Our setup differs from the spec.** P0-05 runs in a personal Google account with **no organization** and **no billing account** (DECISIONS #293, #294). The spec assumes an organization, a `dental-ai` folder, groups and a Terraform state bucket. Without an organization, Assured Workloads, VPC-SC access policies and org/folder-level policies can't be created. We confirmed this read-only: the access-policy call requires `organizations/<number>`. So this change follows spec §5, "how to start without it":
- write and validate all of `infra/org/` against example IDs;
- make the Assured Workloads decision from the docs;
- do everything that works at project level, for real;
- record the rest as pending before real PHI.

## What Changes

- **Assured Workloads vs. own policies:** a comparison from Google's current docs, with a recommendation, logged in DECISIONS. The final choice waits for an organization, because Assured Workloads needs one.
- **`infra/org/allowed_services.yaml`:** the single allow-list. Every candidate API is checked against three Google sources (the HIPAA covered list, the restrictServiceUsage supported list, the VPC-SC supported list). No `verify` values are left.
- **`infra/org/` Terraform:**
  - org policies;
  - the Gemini Developer API deny;
  - US locations;
  - the baseline constraints;
  - the access policy;
  - perimeters `dai_dev` and `dai_staging` (dry-run) and `dai_prod` (enforced), with an admin ingress rule.

  It passes `terraform fmt -check` and `terraform validate` with `example.tfvars`. **It isn't applied**, because that needs an organization and the state bucket.
- **Real, at project level (each mutating step only after the user says yes):**
  - disable the default APIs Google enabled that aren't on the allow-list (from the P0-05 checks);
  - probe whether org policies can be set on a project with no organization; if yes, apply the project-level equivalents and run the matching negative tests;
  - check that no API keys exist and that the Gemini Developer API isn't enabled;
  - record the Speech-to-Text data-logging state.
- **`docs/compliance/hipaa-controls.md`:** evidence. **`docs/runbooks/org-guardrails-tests.md`:** the negative and positive tests.
- **Records:** a DECISIONS row, pending items and notifications in `docs/compliance/README.md`, README links, and the Phase 0 status.

## Capabilities

### New Capabilities
- `hipaa-guardrails`: the technical controls that keep PHI inside HIPAA-covered Google Cloud services in US locations: the service allow-list, location limits, baseline constraints, VPC-SC perimeters, no Gemini Developer API keys, Speech-to-Text data logging off, and the evidence and tests that prove them.

### Modified Capabilities
- None. `cloud-foundation` (P0-05) is unchanged; this change builds on its projects.

## Impact

- **New files:**
  - `infra/org/` (`allowed_services.yaml`, `main.tf`, `variables.tf`, `outputs.tf`, `backend.tf`, `example.tfvars`, and project-level policy YAML if the probe succeeds);
  - `docs/compliance/hipaa-controls.md`;
  - `docs/runbooks/org-guardrails-tests.md`.
- **Edited files:** `dental-ai-tasks/DECISIONS.md`, `docs/compliance/README.md`, `README.md`, `docs/phase-0-discovery-compliance/README.md`.
- **Google Cloud:** default APIs disabled in the four projects; possibly project-level org policies; the Org Policy API (and the API Keys API, if the key check needs it) enabled in `dai-rcpt-ops` only. No cost and no billing needed.
- **Tooling:** Terraform CLI installed in the scratchpad (not system-wide).
- **No PHI is handled.**
