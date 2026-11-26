# Vendor/BAA matrix

> Generated from `docs/compliance/vendors.yaml` (reviewed on 2026-11-26). **Do not edit.** Change the YAML and run `python3 scripts/compliance/check_vendors.py --render`.

## PHI gate: CLOSED

| Item | Task | Status | Evidence |
|---|---|---|---|
| Google Cloud BAA accepted | P0-05 | pending | docs/compliance/baa-google-cloud.md |
| Org guardrails applied and tested | P0-06 | pending | docs/compliance/hipaa-controls.md |
| Clinic BAA signed (at least one clinic) | P0-09 | pending | docs/compliance/baa-clinic-example-dental.md |
| Vendor matrix complete and reviewed | P0-10 | done | docs/compliance/vendor-matrix.md |

Why it's closed:

- google-cloud phi=yes in prod, baa=pending
- twilio phi=yes in prod, baa=pending
- meta-whatsapp phi=yes in prod, baa=pending
- open-dental phi=yes in prod, baa=under_review
- no clinic has a signed BAA
- gate item gcp_baa (P0-05) is pending
- gate item guardrails (P0-06) is pending
- gate item clinic_baa (P0-09) is pending

## Vendors

| Vendor | Services | PHI | Environments | BAA status | BAA date | Record | Owner | Tasks |
|---|---|---|---|---|---|---|---|---|
| Google Cloud | Vertex AI (Gemini), Speech-to-Text, Text-to-Speech, Cloud Run, Cloud SQL, Memorystore, Cloud Tasks, Secret Manager, KMS, Cloud Logging | yes | dev, staging, prod, ops | pending | - | docs/compliance/baa-google-cloud.md | Riley Tech (tech lead) | P0-05, P0-06 |
| Google Workspace (Gmail) | Admin callback emails from callbacks@ | conditional: Only when a clinic uses callback.email_mode = full_details (DECISIONS #41, #303); the default link_only email carries no PHI **PHI blocked for this vendor** | prod, team | pending | - | docs/compliance/baa-google-workspace.md | Workspace super admin (not named yet; no Workspace until production, DECISIONS #304) | P0-08 |
| Twilio (Programmable SMS) | SMS appointment confirmations and reminders, for clinics that choose SMS | yes | staging, prod | pending | - | docs/compliance/baa-twilio.md | Riley Tech (tech lead) | P0-07a, P0-07 |
| Meta (WhatsApp Cloud API) | WhatsApp appointment confirmations and reminders, for clinics that choose WhatsApp | yes | dev, staging, prod | pending | - | docs/compliance/baa-meta-whatsapp.md | Riley Tech (tech lead) | P0-07a, P0-07 |
| Open Dental (API relay) | Open Dental API, requests relayed to the clinic's eConnector | yes | dev, staging, prod | under_review | - | - | Sam Comply (compliance advisor) | P0-09, P0-12 |
| GitHub | Source code, issues, pull requests, CI | no (control: Synthetic data only in code, fixtures, issues and screenshots; PR vendor and PHI check (pr-vendor-check.md); PHI-redacting logger (P1-07); public-repo scan before each commit) | team | not_required | - | - | Riley Tech (tech lead) | P1-01 |
| AI coding assistant (Anthropic, Claude Code) | Reads the repository and terminal output while the team writes code and docs | no (control: Never given PHI: synthetic data only in the repo, terminal, test output and prompts; no access to prod data or the clinic's Open Dental) | team | not_required | - | - | Riley Tech (tech lead) | P0-10 |
| Google AI Studio / Gemini Developer API | Gemini models via API key (local development and the P0-13 spike) | no (control: Synthetic data only; allowed only with APP_ENV=local (startup check, ADR 0001); key only in the git-ignored .env; never a production fallback. Free tier may be read by human reviewers and used to improve Google products (sources G10, G11)) | team | not_required | - | - | Riley Tech (tech lead) | P0-13, P2-03 |

Notes:

- **google-cloud:** Record says NOT ACCEPTED (paper, DECISIONS #293). Only APIs in allowed_services.yaml may be used; real PHI only in prod (DECISIONS #25). Hosting is local-first until the client chooses (DECISIONS #302).
- **twilio:** Record says NOT ACCEPTED; BAA needs Security or Enterprise Edition. No account yet (DECISIONS #301). Messages carry only first name, clinic, date, time (messaging_policy.yaml).
- **meta-whatsapp:** Record says NOT ACCEPTED; Meta's terms say it isn't a business associate. Used now for testing only, synthetic data to team test numbers (messaging_policy.yaml allowed_with_phi: false).
- **open-dental:** Counsel decides whether the clinic's own arrangement with Open Dental covers the relay (P0-09 Annex B open question). dev and staging use the Open Dental test database only. Fees: $30 per location per month, paid by us, while a key is enabled (P0-12, DECISIONS #312). No developer key yet.
- **ai-coding-assistant:** Added for spec §14 (team tools that may see PHI by accident). If it is ever used on prod data or logs, it needs a BAA first.
- **google-ai-studio:** Exception to CLAUDE.md rules 5-6 for local synthetic use (DECISIONS #316). Separate from the Google Cloud row: not a Google Cloud offering and not under the Cloud BAA.

## Clinics

| Clinic | BAA status | Date | Record |
|---|---|---|---|
| example-dental | pending | - | docs/compliance/baa-clinic-example-dental.md |

## Google Cloud products (from `infra/org/allowed_services.yaml`, dev/staging/prod)

| API | Purpose | HIPAA covered | Checked on |
|---|---|---|---|
| `aiplatform.googleapis.com` | Gemini via Vertex AI (P2-03) | yes | 2026-11-26 |
| `speech.googleapis.com` | Streaming Speech-to-Text (P3-03) | yes | 2026-11-26 |
| `texttospeech.googleapis.com` | Text-to-Speech (P3) | yes | 2026-11-26 |
| `run.googleapis.com` | Cloud Run backend and frontend | yes | 2026-11-26 |
| `sqladmin.googleapis.com` | Cloud SQL Postgres (P1-03) | yes | 2026-11-26 |
| `redis.googleapis.com` | Memorystore for Redis (P1-02) | yes | 2026-11-26 |
| `cloudtasks.googleapis.com` | Reminder and email jobs | yes | 2026-11-26 |
| `cloudscheduler.googleapis.com` | Scheduled jobs | yes | 2026-11-26 |
| `secretmanager.googleapis.com` | Secrets (P1-05) | yes | 2026-11-26 |
| `cloudkms.googleapis.com` | Keys, CMEK, field encryption (P1-05) | yes | 2026-11-26 |
| `storage.googleapis.com` | Buckets (exports) | yes | 2026-11-26 |
| `artifactregistry.googleapis.com` | Container images | yes | 2026-11-26 |
| `compute.googleapis.com` | VPC networks, firewall, Direct VPC egress for Cloud Run (P1-02) | yes | 2026-11-26 |
| `dns.googleapis.com` | Private DNS zones that send *.googleapis.com to the restricted VIP and name the Private Service Connect endpoint for Vertex AI `us` (P0-14 network map, P1-02) | yes | 2026-11-26 |
| `servicenetworking.googleapis.com` | Private services access (private IP for Cloud SQL and Memorystore) | no (exception) | 2026-11-26 |
| `cloudtrace.googleapis.com` | Request tracing (P1-07) | yes | 2026-11-26 |
| `identitytoolkit.googleapis.com` | Identity Platform, staff login with MFA (admin console) | yes | 2026-11-26 |

## Last review

2026-11-26 by Sam Comply (compliance advisor)
