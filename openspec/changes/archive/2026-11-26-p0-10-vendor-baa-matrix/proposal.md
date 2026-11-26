# Proposal: P0-10 Vendor/BAA matrix (issue #11)

## Why

Plan §3.3: **no PHI flows to any vendor until its BAA is accepted or signed and recorded in the vendor matrix.** Today the BAA facts are spread over five record files (Google Cloud, Google Workspace, Twilio, Meta, the clinic) and nobody can answer "may real PHI enter prod today?" with one command. A developer could also add a SaaS SDK that sends data out without anyone noticing.

The matrix turns the gate into something a reviewer and, later, CI can check. It is also the input for the risk assessment (P0-11) and the evidence for P5-14.

## What Changes

- **`docs/compliance/vendors.yaml`** (source of truth) and **`vendors.schema.json`** (JSON Schema 2020-12, as in the task spec §6). Rows with statuses that match the records on the day:
  - Google Cloud (pending; product list `infra/org/allowed_services.yaml`);
  - Google Workspace (conditional PHI: only `full_details` email; pending);
  - **Twilio** (SMS) and **Meta** (WhatsApp Cloud API) as two rows instead of the spec's generic "messaging provider" (P0-07 chose both; the clinic uses one);
  - Open Dental API relay (`under_review`, counsel question from P0-09);
  - GitHub (no PHI, with its control);
  - our AI coding assistant (no PHI, synthetic data only), added under spec §14 "other team tools".
  - Clinic `example-dental` (pending, record from P0-09); PHI gate items `gcp_baa`, `guardrails`, `clinic_baa`, `matrix`.
- **`scripts/compliance/check_vendors.py`**: rules C1–C9, the gate logic (`--gate`: OPEN/CLOSED with reasons, exit 0/2), and `--render` that writes **`docs/compliance/vendor-matrix.md`** (generated, not hand-edited).
- **Unit tests** `scripts/compliance/test_check_vendors.py` (pytest), one per rule and gate case from spec §10.
- **`docs/compliance/pr-vendor-check.md`**: the PR checklist text for P1-01, plus the **proposed CODEOWNERS entries as text only**.
- **No `.github/CODEOWNERS` now** (user decision 2026-11-26): it is added when the app goes to production editing; the entries wait in `pr-vendor-check.md`.
- **`docs/compliance/README.md`**: "How to add a vendor", the review routine (quarterly and on change), and links.
- **Records:** DECISIONS rows, notifications (P0-11, P5-14 issues; P1-01 and P1-06 have no issue yet, so their hand-off goes in the README's pending notifications), `docs/PROJECT_MAP.md`.
- No product code, no PHI, no cloud changes.

## Capabilities

### New Capabilities
- `vendor-baa-matrix`: the machine-checked list of every vendor that may receive data, each one's PHI flag and BAA status, and the PHI gate that answers whether real PHI may enter production.

### Modified Capabilities
None.

## Impact

- New: `docs/compliance/vendors.yaml`, `vendors.schema.json`, `vendor-matrix.md`, `pr-vendor-check.md`, `scripts/compliance/check_vendors.py`, `scripts/compliance/test_check_vendors.py`.
- Updated: `docs/compliance/README.md`, `dental-ai-tasks/DECISIONS.md`, `docs/phase-0-discovery-compliance/README.md`, `docs/PROJECT_MAP.md`.
- Dev dependency for running the tests locally: `pytest` (not installed today), in a throwaway virtual environment; `pyyaml` and `jsonschema` are already available.
- Hand-offs: P0-11, P1-01, P1-06, P5-14, P0-12 (clinic row), P0-07/P0-08/P0-09 (rows to flip to `signed`).
- Acceptance criteria partly met: CODEOWNERS is text only, and the P1-01/P1-06 issues don't exist yet.
