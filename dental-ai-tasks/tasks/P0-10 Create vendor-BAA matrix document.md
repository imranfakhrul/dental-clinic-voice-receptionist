---
id: P0-10
title: Create vendor/BAA matrix document
milestone: P0
epic: E0.2
size: S
labels: area:compliance, type:docs
depends_on: P0-05
status: approved
---

# P0-10: Create vendor/BAA matrix document

## 1. Summary
Create the **vendor/BAA matrix**: one living record of every third party our system or team sends data to. For each one it says:
- what we use it for;
- whether PHI reaches it;
- its BAA status, with a link to the BAA record.

It also shows the **PHI gate**, which says whether real PHI may enter production yet.

The deliverables:
- `docs/compliance/vendors.yaml`, the machine-readable source of truth, with a JSON Schema;
- a small checker script that validates the file and renders `docs/compliance/vendor-matrix.md`;
- the text of the PR "vendor and PHI check" (P1-01 puts it in the PR template);
- `CODEOWNERS` rules so a compliance owner reviews every change.

Done means:
- every vendor known today has a row (Google Cloud, Google Workspace, the messaging provider, Open Dental, the clinic, GitHub);
- the checker passes;
- the rendered matrix and the PHI gate are committed;
- P0-11 has been notified.

## 2. Why this matters
Plan §3.3 sets the compliance gate: **no PHI flows to any vendor until its BAA is accepted or signed and recorded in the vendor matrix.** Without a single, checked record:
- a developer can add a new SaaS (error tracking, analytics, a different LLM) that silently receives PHI;
- nobody can answer "may we turn on real patient data in prod today?";
- the HIPAA readiness review (P5-14) has no evidence.

The matrix turns the gate from a sentence into something a reviewer and CI can check. It is also the input for the risk assessment (P0-11).

Plan references: §3.3 (BAA strategy, vendor matrix, compliance gate), §6 (security & HIPAA plan), §1 principle 6 (fewest BAAs).

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P0, Discovery & Compliance Foundation**.
- **BAA records already defined:** each BAA task writes one record file in the same format (P0-05):
  - `docs/compliance/baa-google-cloud.md` (P0-05);
  - `docs/compliance/baa-google-workspace.md` (P0-08);
  - `docs/compliance/baa-<vendor>.md` for the messaging provider (P0-07, after the P0-07a decision);
  - `docs/compliance/baa-clinic-<clinic_slug>.md` for each clinic (P0-09).

  This task does not copy their contents. It links to them and checks they exist.
- **Google Cloud products:** one Google Cloud BAA covers many products, but only those on Google's HIPAA covered-products list. P0-06 already keeps the per-API list with evidence in `infra/org/allowed_services.yaml` (fields `api`, `purpose`, `hipaa_covered: yes|no|verify`, …), and the org policy enforces it. The matrix **renders** that list as a section. It does not keep a second copy.
- **PHI gate (DECISIONS #25):** real PHI may enter `<prefix>-prod` only after all of the following:
  - the Google Cloud BAA (P0-05);
  - the guardrails (P0-06);
  - the clinic BAA (P0-09);
  - this matrix showing them (P0-10).

  It also needs the BAA of every other vendor that will receive PHI, i.e. messaging (P0-07) and Workspace (P0-08), before PHI flows **to that vendor**.
- **What counts as a vendor here:** any third party (company or service outside our own Google Cloud projects' code) that receives, stores or can access data from our system or from our team's work on it. Open-source libraries running inside our containers are not vendors. A SaaS SDK that sends data out (e.g. an error tracker) is.
- **Who reviews:** a "compliance owner" (a named person, see §14), backed by the compliance advisor.

## 4. Scope
**In scope**
- `docs/compliance/vendors.yaml` + `docs/compliance/vendors.schema.json`.
- `scripts/compliance/check_vendors.py`: validate, check links, compute the PHI gate, render `vendor-matrix.md`.
- The initial rows (§6) and the PHI gate items.
- `docs/compliance/pr-vendor-check.md`: the checklist text for the PR template.
- `CODEOWNERS` entries for the compliance files and the integration folders.
- The review routine (quarterly + on change) written in `docs/compliance/README.md`.

**Out of scope** (and which task covers it)
- Creating `.github/pull_request_template.md` and the repo layout → P1-01 (includes our checklist text)
- Running the checker in CI on every PR → P1-06 (CI/CD pipeline); until it exists, run it locally and in review
- Signing any BAA → P0-05, P0-07, P0-08, P0-09
- The Google API allow-list and its evidence → P0-06 (`allowed_services.yaml`)
- Risk analysis of each vendor → P0-11
- Final check that every PHI vendor has an executed BAA → P5-14 (uses this matrix)

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P0-05 Google Cloud foundation (approved spec) | `baa-google-cloud.md` record | Add the Google Cloud row with `baa.status: pending` and `record: null`; switch to `signed` when the record exists. |
| P0-06, P0-07, P0-08, P0-09 (approved specs, soft) | `allowed_services.yaml`, the other BAA records, the guardrails evidence | Add their rows and gate items as `pending`. The checker treats a missing `allowed_services.yaml` as "Google product list: not yet available" and keeps the gate closed. |
| P1-01 monorepo (not started) | The repo layout and the PR template | Commit the files at the paths in §6 now; P1-01 copies the checklist text into the template. |

## 6. Interface contract

### Files
| Path | Content |
|---|---|
| `docs/compliance/vendors.yaml` | Source of truth (format below) |
| `docs/compliance/vendors.schema.json` | JSON Schema (below) |
| `docs/compliance/vendor-matrix.md` | **Generated**, do not edit by hand. Header line says so. |
| `scripts/compliance/check_vendors.py` | Checker and renderer (Python 3.12, `pyyaml`, `jsonschema`) |
| `docs/compliance/pr-vendor-check.md` | Checklist text for the PR template |
| `docs/compliance/README.md` | Index of compliance docs, review routine, how to add a vendor |
| `.github/CODEOWNERS` | Entries below (created here if P1-01 hasn't created the file yet) |

### `vendors.schema.json`
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Vendor/BAA matrix",
  "type": "object",
  "required": ["schema_version", "reviewed_on", "reviewed_by", "vendors", "clinics", "phi_gate"],
  "additionalProperties": false,
  "properties": {
    "schema_version": {"const": 1},
    "reviewed_on": {"type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}$"},
    "reviewed_by": {"type": "string", "minLength": 1},
    "vendors": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["id", "name", "services", "phi", "environments", "baa", "owner", "tasks"],
        "additionalProperties": false,
        "properties": {
          "id": {"type": "string", "pattern": "^[a-z0-9-]+$"},
          "name": {"type": "string"},
          "services": {"type": "array", "items": {"type": "string"}, "minItems": 1},
          "phi": {"enum": ["yes", "no", "conditional"]},
          "phi_condition": {"type": "string"},
          "no_phi_control": {"type": "string"},
          "environments": {"type": "array", "items": {"enum": ["dev", "staging", "prod", "ops", "team"]}, "minItems": 1},
          "baa": {
            "type": "object",
            "required": ["status"],
            "additionalProperties": false,
            "properties": {
              "status": {"enum": ["signed", "pending", "under_review", "not_required"]},
              "type": {"enum": ["click_through", "signed_contract", "clinic_arrangement"]},
              "date": {"type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}$"},
              "record": {"type": ["string", "null"]}
            }
          },
          "product_list": {"type": "string"},
          "owner": {"type": "string"},
          "tasks": {"type": "array", "items": {"type": "string", "pattern": "^P\\d-\\d{2}[a-z]?$"}},
          "notes": {"type": "string"}
        }
      }
    },
    "clinics": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["clinic_slug", "baa"],
        "additionalProperties": false,
        "properties": {
          "clinic_slug": {"type": "string", "pattern": "^[a-z0-9-]+$"},
          "baa": {
            "type": "object",
            "required": ["status"],
            "additionalProperties": false,
            "properties": {
              "status": {"enum": ["signed", "pending"]},
              "date": {"type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}$"},
              "record": {"type": ["string", "null"]}
            }
          }
        }
      }
    },
    "phi_gate": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["id", "description", "task", "status"],
        "additionalProperties": false,
        "properties": {
          "id": {"type": "string", "pattern": "^[a-z0-9_]+$"},
          "description": {"type": "string"},
          "task": {"type": "string"},
          "status": {"enum": ["done", "pending"]},
          "evidence": {"type": ["string", "null"]}
        }
      }
    }
  }
}
```

### `vendors.yaml`: initial content (Proposed; statuses as of writing)
```yaml
schema_version: 1
reviewed_on: "2026-11-24"
reviewed_by: "<compliance owner>"
vendors:
  - id: google-cloud
    name: Google Cloud
    services: [Vertex AI (Gemini), Speech-to-Text, Text-to-Speech, Cloud Run, Cloud SQL, Memorystore, Cloud Tasks, Secret Manager, KMS, Cloud Logging]
    phi: "yes"
    environments: [dev, staging, prod, ops]
    baa: {status: pending, type: click_through, record: null}
    product_list: infra/org/allowed_services.yaml
    owner: "<tech lead>"
    tasks: [P0-05, P0-06]
    notes: "Only APIs in allowed_services.yaml with hipaa_covered: yes may touch PHI"
  - id: google-workspace
    name: Google Workspace (Gmail)
    services: [Admin callback emails from callbacks@]
    phi: conditional
    phi_condition: "Only when a clinic uses callback.email_mode = full_details (DECISIONS #41)"
    environments: [prod, team]
    baa: {status: pending, type: click_through, record: null}
    owner: "<Workspace super admin>"
    tasks: [P0-08]
  - id: messaging-provider
    name: "Messaging provider (chosen in P0-07)"
    services: [Appointment confirmations, reminders]
    phi: "yes"
    environments: [staging, prod]
    baa: {status: pending, type: signed_contract, record: null}
    owner: "<tech lead>"
    tasks: [P0-07a, P0-07]
    notes: "Rename id/name once the vendor is chosen"
  - id: open-dental
    name: Open Dental (API relay)
    services: [Open Dental API, requests relayed to the clinic's eConnector]
    phi: "yes"
    environments: [dev, staging, prod]
    baa: {status: under_review, type: clinic_arrangement, record: null}
    owner: "<compliance owner>"
    tasks: [P0-09, P0-12]
    notes: "Counsel decides if the clinic's own arrangement with Open Dental covers the relay (P0-09 §14). dev/staging use the test DB only"
  - id: github
    name: GitHub
    services: [Source code, issues, pull requests, CI]
    phi: "no"
    no_phi_control: "Synthetic data only in code, fixtures, issues and screenshots; PR vendor/PHI check; P1-11 log redaction"
    environments: [team]
    baa: {status: not_required}
    owner: "<tech lead>"
    tasks: [P1-01]
clinics:
  - clinic_slug: "pilot-clinic"   # replace with the real slug from P0-01
    baa: {status: pending, record: null}
phi_gate:
  - {id: gcp_baa, description: "Google Cloud BAA accepted", task: P0-05, status: pending, evidence: null}
  - {id: guardrails, description: "Org guardrails applied and tested", task: P0-06, status: pending, evidence: docs/compliance/hipaa-controls.md}
  - {id: clinic_baa, description: "Clinic BAA signed (at least one clinic)", task: P0-09, status: pending, evidence: null}
  - {id: matrix, description: "Vendor matrix complete and reviewed", task: P0-10, status: pending, evidence: docs/compliance/vendor-matrix.md}
```

### Checker: `scripts/compliance/check_vendors.py`
```
python scripts/compliance/check_vendors.py            # validate only; exit 0 / 1
python scripts/compliance/check_vendors.py --render   # validate, then write vendor-matrix.md
python scripts/compliance/check_vendors.py --gate     # print GATE OPEN / GATE CLOSED and the reasons; exit 0 if open, 2 if closed
```
**Rules.** Each failing rule is an error (exit 1) unless marked as a warning:
| # | Rule |
|---|---|
| C1 | The file is valid against `vendors.schema.json`. |
| C2 | Vendor `id`s and `clinic_slug`s are unique. |
| C3 | `baa.status: signed` ⇒ `date` set and `record` is a path to a file that exists. |
| C4 | `phi: "yes"` or `"conditional"` ⇒ `baa.status` is not `not_required`. |
| C5 | `phi: "no"` ⇒ `no_phi_control` is set. `phi: "conditional"` ⇒ `phi_condition` is set. |
| C6 | `product_list` set ⇒ the file exists. If it is missing: warning, and the gate is closed. |
| C7 | Gate item `status: done` ⇒ `evidence` is a path to a file that exists. |
| C8 | `vendor-matrix.md` equals what `--render` would write (CI uses this to catch hand edits or a forgotten render). |
| C9 | Warning if `reviewed_on` is more than 100 days old. |

**Gate logic (`--gate`).** The gate is **OPEN** only when:
- every `phi_gate` item is `done`;
- every vendor with `phi: "yes"` that is used in `prod` has `baa.status: signed`;
- at least one clinic has `baa.status: signed`;
- every API in `product_list` that is enabled in prod has `hipaa_covered: yes`.

Otherwise it is **CLOSED**, and the output lists each reason, e.g. `CLOSED: messaging-provider phi=yes in prod, baa=pending`.

The gate is per vendor too. A vendor with `phi: conditional` and an unsigned BAA does not close the global gate. Instead the matrix shows **"PHI blocked for this vendor"**, and the owning feature's config must keep it off (e.g. `email_mode` stays `link_only`).

### Rendered `vendor-matrix.md` (layout)
1. A header: "Generated from vendors.yaml on <date>. Do not edit."
2. **PHI gate:** OPEN/CLOSED, then the items table (item, task, status, evidence) and the list of reasons.
3. **Vendors:**

   | Vendor | Services | PHI | Environments | BAA status | BAA date | Record | Owner | Tasks |
   |---|---|---|---|---|---|---|---|---|
4. **Clinics:**

   | Clinic | BAA status | Date | Record |
   |---|---|---|---|
5. **Google Cloud products:** rendered from `allowed_services.yaml`: API, purpose, HIPAA covered, `checked_on`.
6. **Last review:** date and reviewer.

### PR check text (`pr-vendor-check.md`; P1-01 copies it into the PR template)
```markdown
### Vendor and PHI check
- [ ] This PR adds **no** new external service, SaaS, SDK that sends data out, or Google Cloud API.
      If it does: `docs/compliance/vendors.yaml` (and `infra/org/allowed_services.yaml` for Google APIs) is updated in this PR, and the compliance owner is a reviewer.
- [ ] This PR sends **no new kind of PHI** to an existing vendor. If it does: the vendor's row and the clinic BAA Annex A (P0-09) are updated.
- [ ] No PHI in code, tests, fixtures, logs, screenshots or the PR description (synthetic data only).
- [ ] No Pre-GA (preview/experimental) model or feature receives PHI.
```

### `CODEOWNERS` entries
```
/docs/compliance/                     @<org>/compliance-owners
/infra/org/allowed_services.yaml      @<org>/compliance-owners
/backend/app/integrations/            @<org>/compliance-owners @<org>/backend-leads
/scripts/compliance/                  @<org>/compliance-owners
```
Proposed: the GitHub team `compliance-owners` contains the compliance owner and the tech lead. A change to these paths can't merge without their review. **Verify:** this needs branch protection with "Require review from Code Owners" enabled (P1-01 / P1-06).

## 7. Implementation guide
1. **Create the schema and the YAML** exactly as in §6. Fill in the real owners and statuses from the BAA records that exist on the day.
2. **Write `check_vendors.py`:**
   - load the YAML with `yaml.safe_load` and validate it with `jsonschema` Draft 2020-12;
   - apply C2–C9;
   - compute the gate;
   - render the Markdown with plain string building (no template engine).

   Keep it under ~250 lines, with no network calls.
3. **Unit tests** in `scripts/compliance/test_check_vendors.py` (pytest), one per rule (§10).
4. **Render** `vendor-matrix.md` and commit it together with the YAML.
5. **Write `pr-vendor-check.md`** and the `CODEOWNERS` entries. Comment on the P1-01 issue with the text, and on the P1-06 issue with the CI commands:
   - `check_vendors.py` on every PR;
   - `--gate` as a **required step before the first prod deploy that enables real PHI**.
6. **Write `docs/compliance/README.md`:**
   - an index of the compliance files;
   - "How to add a vendor" (steps: add a row with `pending`, get the BAA through the vendor's task, add the record, set it to `signed`, re-render);
   - the review routine (step 7).
7. **Review routine:**
   - **quarterly**, the compliance owner re-reads every row, re-checks Google's covered-products list against `allowed_services.yaml`, updates `reviewed_on` and re-renders;
   - **on any change** (new vendor, new Google API, BAA signed or renewed, vendor dropped), update it in the same PR.
8. **Notify:** P0-11 (the matrix is its input), P5-14 (evidence), and P0-07, P0-08 and P0-09 (set their row to `signed` when done).

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| A developer adds an error-tracking SaaS SDK without a row | The PR check and CODEOWNERS on `backend/app/integrations/` catch it in review. If it would receive PHI, it is blocked until there is a BAA. Prefer Cloud Logging, which is covered (plan §3.3). |
| A vendor refuses to sign a BAA | Keep `phi: "no"` with a real `no_phi_control`, or drop the vendor. Never `phi: "yes"` with `not_required` (C4 fails). |
| A BAA record exists but the PDF copy is missing | The status stays `pending` until the record lists a saved copy. The reviewer checks this; the checker only checks that the record file exists. |
| Google removes a product from the covered list | The quarterly review finds it. Set `hipaa_covered: no` in `allowed_services.yaml` (P0-06 owns it) and the gate closes. Escalate to the tech lead to stop that API in prod. |
| A Google API is enabled in prod but missing from `allowed_services.yaml` | It shouldn't be possible (the org policy blocks it). If found, treat it as a possible incident and tell the compliance owner. |
| The messaging vendor changes later | Add the new row as `pending`; write "dropped on YYYY-MM-DD" in the old row's `notes`. Keep it until its data is deleted (vendor's return/destroy), then remove it in a PR that references the deletion evidence. Clinic BAA Annex B is updated, and clinics are notified per P0-09 P7. |
| The BAA of a `conditional` vendor is pending | The global gate stays open if everything else is done, but the matrix shows "PHI blocked for this vendor" and the feature flag stays off (e.g. `link_only`). |
| Someone edits `vendor-matrix.md` by hand | C8 fails; re-render from the YAML. |
| A second clinic joins | Add a `clinics` row as `pending`. That clinic's production key and data stay blocked until its own BAA is signed (P0-09). The global gate already counts as open from the first clinic, so per-clinic onboarding must check the clinic row (P0-12 / onboarding). |

## 9. Security, HIPAA and PHI
- **No PHI is handled.** The matrix lists vendors and categories, never patient data.
- **This task is part of the PHI gate.** Its `--gate` output is the single answer to "may real PHI enter prod?". The first prod deploy that turns on real data must show **GATE OPEN** in its logs (P1-06).
- The files are internal compliance documents in the private repo. Vendor contract amounts or contacts don't belong here.
- **Audit:** git history of `vendors.yaml` is the audit trail of who changed which vendor status and when. CODEOWNERS makes every change reviewed.

## 10. Testing
Unit tests (`pytest scripts/compliance/`), each with a small YAML fixture:
- valid example from §6 → exit 0; `--gate` → CLOSED, listing the pending items;
- all items done, all PHI vendors signed with existing records → `--gate` OPEN (exit 0);
- C2 duplicate id; C3 `signed` with a missing record file; C4 `phi: yes` + `not_required`; C5 `phi: no` without a control; C7 `done` without evidence → each exits 1 with a message naming the vendor and rule;
- C6 `product_list` missing → warning, gate CLOSED;
- C8 hand-edited `vendor-matrix.md` → exit 1;
- C9 `reviewed_on` 120 days ago → warning only, exit 0;
- `conditional` vendor pending → gate unaffected, rendered matrix says "PHI blocked for this vendor";
- `allowed_services.yaml` with a `verify` API → gate CLOSED with that API named.

Manual: the compliance owner reviews the rendered matrix against the BAA records.

## 11. Acceptance criteria
- [ ] `vendors.yaml`, `vendors.schema.json`, `vendor-matrix.md` and `docs/compliance/README.md` are committed
- [ ] Rows exist for Google Cloud, Google Workspace, the messaging provider, Open Dental, GitHub and the pilot clinic, with statuses that match the BAA records on the day
- [ ] `check_vendors.py` implements C1–C9 and the gate logic; all §10 tests pass
- [ ] `--gate` prints CLOSED with correct reasons today, and OPEN when the test fixture has everything done
- [ ] `pr-vendor-check.md` and the CODEOWNERS entries are committed; the P1-01 and P1-06 issues have the text and commands
- [ ] The compliance owner has reviewed the matrix (`reviewed_by`, `reviewed_on` filled in)
- [ ] The P0-11 and P5-14 issues are notified

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI: the §10 tests pass locally; they run in CI once P1-06 exists
- [ ] PR reviewed (HIPAA review if labelled `phi`): reviewed by the compliance owner; no `phi` label (no PHI handled)
- [ ] No PHI in logs: the checker prints vendor IDs and file paths only
- [ ] Docs / README updated: `docs/compliance/README.md`

## 13. Hand-off
| Task | Can rely on |
|---|---|
| P0-11 Risk assessment | The vendor list with PHI flags and environments, as the input for data flows and third-party risk |
| P1-01 Monorepo | The PR checklist text and CODEOWNERS entries |
| P1-06 CI/CD | `check_vendors.py` on every PR; `--gate` before the first prod deploy with real PHI |
| P0-07, P0-08, P0-09 | A row to set to `signed` with their record |
| P5-14 HIPAA readiness | The rendered matrix and gate output as evidence |
| Clinic onboarding (P0-12, later clinics) | The `clinics` rows: no production key or data for a clinic until its row is `signed` |

## 14. Open questions
| Question | Owner | Needed by |
|---|---|---|
| Who is the compliance owner (named person) and who is in `compliance-owners`? | Project sponsor | Step 1 |
| Does the Open Dental relay need its own BAA, or is it covered by the clinic's arrangement? (Same question as P0-09 §14.) | Counsel | Before the first prod data |
| Are there other team tools that may see PHI by accident (e.g. a team chat or shared drive used for support)? If yes, add them as rows with a BAA or a `no_phi_control`. | Tech lead | Step 1 |

## 15. References
- Plan §3.3 (BAA strategy, vendor matrix, compliance gate), §6, §1 principle 6
- HHS business associates guidance: https://www.hhs.gov/hipaa/for-professionals/privacy/guidance/business-associates/index.html
- Google Cloud HIPAA covered products: https://docs.cloud.google.com/docs/security/compliance/hipaa
- GitHub CODEOWNERS: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners (Verify: branch protection setting name)
- JSON Schema 2020-12: https://json-schema.org/draft/2020-12/release-notes
- Related tasks: P0-05, P0-06, P0-07, P0-07a, P0-08, P0-09, P0-11, P0-12, P1-01, P1-06, P1-11, P5-14
