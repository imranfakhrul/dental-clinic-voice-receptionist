# Project map: which file is for which work

This map shows every file in the repo and the work it belongs to. It covers what is done, what is in progress, and where future work will go.

**Status:**
- ✅ **done**: committed.
- 🔄 **in progress**: in review (none right now).
- ⬜ **planned**: future. The paths come from the task specs and CLAUDE.md ("Proposed"), so they may change when the task is built.

**Update this file** whenever a task adds, moves or removes files.

---

## 1. Plans and reference (read these first)
| File | What it's for |
|---|---|
| [README.md](../README.md) | Front page of the repo: what the project is and links to everything |
| [CLAUDE.md](../CLAUDE.md) | Rules and working method for the AI assistant (and anyone else) in this repo |
| [dental-ai-tasks/plan/AI_Dental_Receptionist_Project_Plan.md](../dental-ai-tasks/plan/AI_Dental_Receptionist_Project_Plan.md) | Master plan ("plan §N" in other files) |
| [dental-ai-tasks/plan/initial_task_list.md](../dental-ai-tasks/plan/initial_task_list.md) | The original 124 seed tasks |
| [dental-ai-tasks/PROJECT_OVERVIEW.md](../dental-ai-tasks/PROJECT_OVERVIEW.md) | Tech stack, database schema, APIs, models and prices, integrations |
| `dental-ai-tasks/tasks/<ID> <title>.md` | One spec per task (the contract for that task) |
| [dental-ai-tasks/tasks/_CONSOLIDATION.md](../dental-ai-tasks/tasks/_CONSOLIDATION.md) | Which seed tasks were merged into which |
| [dental-ai-tasks/DECISIONS.md](../dental-ai-tasks/DECISIONS.md) | Every design decision, numbered ("DECISIONS #N"), newest at the bottom |
| [dental-ai-tasks/GLOSSARY.md](../dental-ai-tasks/GLOSSARY.md) | Terms: PHI, BAA, PatNum, AptNum, eConnector… |
| `dental-ai-tasks/PDF/` | All task specs as one PDF |
| [docs/phase-0-discovery-compliance/README.md](phase-0-discovery-compliance/README.md) | Phase 0 dashboard: every Phase 0 task, its GitHub issue, its output and its status |

## 2. OpenSpec (how each task is planned and recorded)
| File | What it's for |
|---|---|
| [openspec/config.yaml](../openspec/config.yaml) | Project rules for OpenSpec (one change per issue, commit only after review…) |
| `openspec/changes/<change>/` | The plan of the task being worked on: `proposal.md` (why), `design.md` (how), `tasks.md` (checklist), `specs/` (requirements) |
| `openspec/changes/archive/<date>-<change>/` | Finished task plans, kept as history |
| `openspec/specs/<capability>/spec.md` | The current requirements of the system, merged in from each finished task |

Current main specs:
| Spec | From task |
|---|---|
| [appointment-type-mapping](../openspec/specs/appointment-type-mapping/spec.md) | P0-02 |
| [emergency-triage-rules](../openspec/specs/emergency-triage-rules/spec.md) | P0-03 |
| [conversation-state-machine](../openspec/specs/conversation-state-machine/spec.md) | P0-04 |
| [cloud-foundation](../openspec/specs/cloud-foundation/spec.md) | P0-05 |
| [hipaa-guardrails](../openspec/specs/hipaa-guardrails/spec.md) | P0-06 |
| [patient-messaging-policy](../openspec/specs/patient-messaging-policy/spec.md) | P0-07a |
| [messaging-provider](../openspec/specs/messaging-provider/spec.md) | P0-07 |
| [admin-callback-email](../openspec/specs/admin-callback-email/spec.md) | P0-08 |
| [clinic-baa](../openspec/specs/clinic-baa/spec.md) | P0-09 |

---

## 3. Phase 0: Discovery and compliance (GitHub issue #17)

### ✅ P0-01 Discovery workshop (#1)
| File | What it's for |
|---|---|
| [docs/discovery/README.md](discovery/README.md) | Purpose, agenda and rules of the workshop |
| [docs/discovery/pre-read.md](discovery/pre-read.md) | Two-page explanation sent to the clinic before the workshop |
| [docs/discovery/questionnaire.md](discovery/questionnaire.md) | The questions asked (Q1–Q11, Q4a, Q4b, B1–B8) |
| [docs/discovery/clinic-decision-log.md](discovery/clinic-decision-log.md) | The clinic's answers and decisions, plus later revisions |
| [docs/discovery/review-checklist.md](discovery/review-checklist.md) | Checklist used to review the workshop results |
| `docs/discovery/signoff-2026-11-25.pdf` | Signed sign-off of the workshop decisions |

### ✅ P0-02 Appointment types (#2)
| File | What it's for |
|---|---|
| [docs/discovery/appointment-type-mapping.md](discovery/appointment-type-mapping.md) | Readable table: patient reason → appointment type → length → providers |
| `docs/discovery/appointment-type-workbook.xlsx` | Spreadsheet the clinic filled in |
| `docs/discovery/signoff-appointment-types-2026-11-26.pdf` | Clinic sign-off of the mapping |
| `backend/app/domain/clinic_config/schemas/appointment_types.schema.json` | Rules the appointment-types file must follow |
| `backend/app/domain/clinic_config/seed/example-dental-clinic/appointment_types.yaml` | The real mapping the app will load |
| `backend/tests/fixtures/clinic_config/appointment_types.example.yaml` | Example file for tests |

### ✅ P0-03 Emergency protocol (#3)
| File | What it's for |
|---|---|
| [docs/discovery/emergency-protocol.md](discovery/emergency-protocol.md) | Readable emergency rules (Tier 1/2/3) and the no-advice scripts |
| [docs/discovery/emergency-protocol-feedback-2026-11-26.md](discovery/emergency-protocol-feedback-2026-11-26.md) | Dentist's review comments and what changed |
| `backend/app/domain/clinic_config/schemas/emergency_rules.schema.json` | Rules the emergency file must follow |
| `backend/app/domain/clinic_config/seed/example-dental-clinic/emergency_rules.yaml` | The reviewed emergency rules the app will load |
| `backend/tests/fixtures/clinic_config/emergency_rules.example.yaml` | Draft example for tests |
| `evals/emergency/emergency_cases.yaml` | 71 test sentences with the expected tier |
| `evals/emergency/dry-run-results.csv` | Result of running the rules on those 71 cases |

### ✅ P0-04 Conversation flows (#4)
| File | What it's for |
|---|---|
| [docs/flows/overview.md](flows/overview.md) | How a conversation moves: all states, interrupts, which data is PHI |
| `docs/flows/state_machine.yaml` | The state machine itself (18 states, 71 transitions); the code will load it |
| `docs/flows/state_machine.schema.json` | Rules the state machine file must follow |
| `docs/flows/book-new-patient.md`, `book-existing-patient.md`, `reschedule.md`, `cancel.md`, `check-appointment.md`, `emergency.md`, `callback.md`, `faq.md` | One page per conversation flow, with a diagram |
| [docs/flows/review-2026-11-26.md](flows/review-2026-11-26.md) | Tech lead and clinic review of the flows |
| `evals/golden/*.yaml` (8 files) | Example conversations, one per flow, used to test the bot later |

### ✅ P0-05 Google Cloud setup (#5)
| File | What it's for |
|---|---|
| [docs/compliance/README.md](compliance/README.md) | Compliance home page: current state, **what's pending before real patient data**, notifications to other tasks |
| [docs/compliance/baa-google-cloud.md](compliance/baa-google-cloud.md) | Google BAA status (**not accepted**), how to accept it, and which Google services are HIPAA-covered |
| [docs/compliance/bootstrap-checks-2026-11-26.md](compliance/bootstrap-checks-2026-11-26.md) | Proof of the Google Cloud setup (check outputs) |
| [docs/runbooks/gcp-bootstrap.md](runbooks/gcp-bootstrap.md) | Step-by-step commands: what was run, the billing steps (Part B), the organization steps (Part C) |
| `infra/bootstrap/foundation.yaml` | Google Cloud IDs: projects, numbers, contacts, BAA status |

### ✅ P0-06 HIPAA guardrails (#6)
| File | What it's for |
|---|---|
| `infra/org/allowed_services.yaml` | The list of Google APIs we're allowed to use, and why |
| `infra/org/main.tf`, `variables.tf`, `outputs.tf`, `versions.tf`, `backend.tf`, `.terraform.lock.hcl` | Terraform code for the guardrails (policies, perimeters); validated, not applied yet |
| `infra/org/example.tfvars` | Example settings for the Terraform (fake organization IDs) |
| [docs/compliance/hipaa-controls.md](compliance/hipaa-controls.md) | Which guardrails are on, which are pending, with proof |
| [docs/runbooks/org-guardrails-tests.md](runbooks/org-guardrails-tests.md) | Tests to re-run after any guardrail change, and the steps for when an organization exists |
| `openspec/changes/archive/2026-11-26-p0-06-hipaa-guardrails/` | The task plan (archived) |

### ✅ P0-07a Patient messaging channel (#7)
| File | What it's for |
|---|---|
| [docs/compliance/patient-messaging-decision.md](compliance/patient-messaging-decision.md) | The decision memo: facts, options, advisor answers, signed decision (**WhatsApp now; clinic chooses SMS or WhatsApp at go-live**) |
| `docs/compliance/messaging_policy.yaml` | Rules later code must enforce: allowed channel and fields per message, fields never allowed |
| [docs/compliance/sources/README.md](compliance/sources/README.md) | Where each fact came from: URL, date, quote, fingerprint |
| `scripts/compliance/check_messaging_policy.py` | Checks the policy file is consistent |
| `openspec/changes/archive/2026-11-26-p0-07a-messaging-channel-decision/` | The task plan (archived) |

### ✅ P0-07 Messaging providers (#8)
| File | What it's for |
|---|---|
| [docs/integrations/messaging-provider.md](integrations/messaging-provider.md) | Provider comparison, the choice (Meta for WhatsApp, Twilio for SMS), integration facts, registration steps |
| [docs/compliance/baa-meta-whatsapp.md](compliance/baa-meta-whatsapp.md) | Meta BAA record (paper, NOT ACCEPTED) and the request to send |
| [docs/compliance/baa-twilio.md](compliance/baa-twilio.md) | Twilio BAA record (paper, NOT ACCEPTED) and the request to send |
| `scripts/messaging/send_test_message.py` | Sends one fake WhatsApp test message |
| `scripts/messaging/webhook_probe.py` | Receives WhatsApp webhooks and checks their signature (test only; live webhook test deferred to P4-06) |
| `openspec/changes/archive/2026-11-26-p0-07-messaging-provider-selection/` | The task plan (archived) |

Also updated by P0-07:
- `docs/compliance/sources/README.md`: where each provider fact came from (Meta M1–M9, Twilio T1–T8, Vonage, Sinch, Infobip, 360dialog).
- `dental-ai-tasks/DECISIONS.md`: #300 (providers chosen), #301 (paper BAAs, no SMS account yet, temporary tunnel for the test).
- `docs/compliance/README.md`: lists the two BAA records, what's pending before real PHI, and notes for P0-10, P0-15, P4-01/06/07 and P1-05.
- `docs/phase-0-discovery-compliance/README.md`: #8 status.

### ✅ P0-08 Admin callback email (#9)
| File | What it's for |
|---|---|
| [docs/integrations/admin-email.md](integrations/admin-email.md) | **Main file:** how callback emails reach the clinic admin: route, sender, security, config keys, login design, tests, what's pending |
| `docs/integrations/admin-email/templates/link_only.txt` | The default email: urgency, case ID and link only, no patient data |
| `docs/integrations/admin-email/templates/full_details.txt` | The email with patient details (only with the advisor's written approval) |
| [docs/compliance/baa-google-workspace.md](compliance/baa-google-workspace.md) | Google Workspace BAA record (paper, NOT ACCEPTED) and how to accept it |
| [docs/compliance/email-readiness-example-dental.md](compliance/email-readiness-example-dental.md) | Readiness check for our clinic's mailbox (not ready: placeholder address) |
| [docs/runbooks/admin-email-add-clinic.md](runbooks/admin-email-add-clinic.md) | Steps to add a new clinic to callback email |
| `scripts/email/check_templates.py` | Checks the templates contain no patient fields where they mustn't |
| `scripts/email/send_test_callback_email.py` | Sends a fake callback email to Mailpit (local) or through Gmail (`--smtp gmail`) and checks it |
| `scripts/email/docker-compose.mailpit.yml` | Starts Mailpit, a local fake mailbox (http://127.0.0.1:8025) |
| `openspec/changes/archive/2026-11-26-p0-08-admin-email-route/` | The task plan (archived) |

Also updated by P0-08:
- `docs/compliance/sources/README.md`: sources E1–E15 (Google Workspace, Gmail, delegation, app passwords, Mailpit).
- `dental-ai-tasks/DECISIONS.md`: #303 (link-only default, config keys, keyless login design), #304 (no domain until production, paper BAA, tests used instead).
- `docs/compliance/README.md`: lists the new files, what's pending before real PHI, and notes for P2-23, P2-22, P4-13/14, P0-06/P1-05 and P0-10.
- `docs/phase-0-discovery-compliance/README.md`: #9 status.

### ✅ P0-09 Clinic ↔ company BAA (#10)
| File | What it's for |
|---|---|
| [docs/compliance/baa/clinic-baa-template-v1.md](compliance/baa/clinic-baa-template-v1.md) | **Main file:** the draft BAA (from the HHS sample), for counsel to finalize |
| [docs/compliance/baa/requirements-checklist.md](compliance/baa/requirements-checklist.md) | What any clinic BAA must contain (R1–R11 from HIPAA, our terms P1–P9), with pass/fail |
| [docs/compliance/baa/annex-a-data-and-purposes.md](compliance/baa/annex-a-data-and-purposes.md) | Which patient data we handle, why, where, and for how long |
| [docs/compliance/baa/annex-b-subcontractors.md](compliance/baa/annex-b-subcontractors.md) | Our vendors that may get patient data, and their BAA status |
| [docs/compliance/baa/commitments.md](compliance/baa/commitments.md) | Every BAA promise → the task that keeps it |
| [docs/compliance/baa-clinic-example-dental.md](compliance/baa-clinic-example-dental.md) | The clinic BAA record: NOT SIGNED, reviews, clinic comments, gates |
| `openspec/changes/archive/2026-11-26-p0-09-clinic-baa/` | The task plan (archived) |

Also updated by P0-09:
- `docs/compliance/sources/README.md`: sources L1–L7 (eCFR sections, HHS pages).
- `dental-ai-tasks/DECISIONS.md`: #305 (template v1 and proposed terms), #306 (no counsel, NOT SIGNED, signed copy kept private).
- `docs/compliance/README.md`: lists the new files, the clinic BAA pending item, and notes for P0-10, P0-11, P0-12, P1-07, P5-12 and P5-14.
- `docs/phase-0-discovery-compliance/README.md`: #10 status.

### ⬜ Rest of Phase 0 (planned outputs from the Phase 0 dashboard)
| Task | Will create | What it'll be for |
|---|---|---|
| P0-10 (#11) | `docs/compliance/vendors.yaml`, `scripts/compliance/` | Every vendor that may touch patient data, and its BAA status |
| P0-11 (#12) | `docs/compliance/risk/` | HIPAA risk assessment v1 |
| P0-12 (#13) | `scripts/open_dental/`, `docs/integrations/open-dental-test-db.md` | Open Dental API keys (in Secret Manager, never in the repo) and the test database |
| P0-13 (#14) | `docs/adr/0001-gemini-models.md`, `evals/spike/p0-13/` | Which Gemini model versions we use per tier, and the test results |
| P0-14 (#15) | `docs/architecture/` | Architecture document and patient-data flow diagram |
| P0-15 (#16) | `docs/messaging/templates.yaml`, `scripts/messaging/` | WhatsApp test number and templates now; SMS sender registration before go-live |

---

## 4. Future phases (⬜ planned; folders from CLAUDE.md, "Proposed")

**Code layout once P1-01 creates it:**
| Folder | What will go there |
|---|---|
| `backend/app/api/` | Web endpoints (FastAPI) |
| `backend/app/core/` | Settings, logging, errors, security helpers |
| `backend/app/db/` | Database models and migrations |
| `backend/app/integrations/` | Clients for outside systems: Open Dental, Gemini (Vertex AI), speech, messaging, email |
| `backend/app/domain/` | Business logic: patients, scheduling, callbacks, reminders, clinic settings |
| `backend/app/orchestrator/` | The conversation engine (state machine) |
| `backend/app/tools/` | The tool gateway: the only way the bot can change Open Dental |
| `backend/app/voice/` | Voice pipeline (speech in/out, barge-in) |
| `backend/tests/` | Unit and integration tests |
| `frontend/` | Patient widget (`/widget`) and admin console (`/admin`) |
| `infra/env/` | Terraform per environment (dev, staging, prod) |
| `evals/` | Conversation and voice test sets |
| `docs/adr/`, `docs/architecture/`, `docs/runbooks/` | Decisions, architecture, operating guides |

### ⬜ Phase 1: Core platform and Open Dental adapter
| Task | Will mainly touch |
|---|---|
| P1-01 Monorepo and coding standards (+ FastAPI skeleton) | `backend/`, `frontend/`, `Makefile`, `docker-compose.yml` |
| P1-02 Terraform: network, Cloud Run, Artifact Registry, Redis, Tasks, Scheduler | `infra/env/` (needs the billing steps from P0-05 first) |
| P1-03 Cloud SQL Postgres and database schema | `infra/env/`, `backend/app/db/` |
| P1-05 Secret Manager, KMS, service accounts, field encryption | `infra/env/`, `backend/app/core/` |
| P1-06 CI/CD: build, test, deploy | `.github/workflows/` |
| P1-07 Logging, monitoring, PHI-redacting logger | `backend/app/core/`, `infra/env/` |
| P1-13 Staff login with MFA and roles | `backend/app/api/`, `backend/app/core/` |
| P1-15, P1-16 Open Dental client and patient search/create | `backend/app/integrations/open_dental/` |
| P1-19 Clinic settings service | `backend/app/domain/clinic_config/` |
| P1-20 Free-slot engine | `backend/app/domain/scheduling/` |
| P1-22 Patient tools | `backend/app/tools/` |

### ⬜ Phase 2: Text chat
| Task | Will mainly touch |
|---|---|
| P2-01 State machine engine | `backend/app/orchestrator/` (loads `docs/flows/state_machine.yaml`) |
| P2-03, P2-04, P2-05 Gemini client, context builder, data extraction | `backend/app/integrations/vertex_ai/`, `backend/app/orchestrator/` |
| P2-08 Tool gateway | `backend/app/tools/` |
| P2-12 Name, phone and date normalization | `backend/app/domain/` |
| P2-15, P2-16, P2-18 Registration, booking, reschedule and cancel flows | `backend/app/orchestrator/`, `backend/app/domain/` |
| P2-20 Emergency detector | `backend/app/domain/` (uses `emergency_rules.yaml`) |
| P2-22 Callback cases | `backend/app/domain/callbacks/` |
| P2-25, P2-27 Chat widget and cards | `frontend/` (`/widget`) |
| P2-30 End-to-end text booking test | `backend/tests/`, `frontend/` (Playwright) |

### ⬜ Phase 3: Voice (runs alongside Phase 4)
| Task | Will mainly touch |
|---|---|
| P3-01 Latency spike | `evals/spike/` |
| P3-02 Audio transport | `backend/app/voice/`, `frontend/` |
| P3-03 Speech-to-Text (re-check data logging is off) | `backend/app/integrations/speech/` |
| P3-06, P3-09 Barge-in, read-back confirmation | `backend/app/voice/` |
| P3-11 Avatar | `frontend/` |
| P3-14 Latency dashboard | `infra/env/`, `backend/app/core/` |

### ⬜ Phase 4: Messaging and admin console (runs alongside Phase 3)
| Task | Will mainly touch |
|---|---|
| P4-01–P4-04 Messaging provider, consent, confirmations, reminders | `backend/app/integrations/messaging/`, `backend/app/domain/reminders/` |
| P4-09, P4-11, P4-13, P4-13a Admin console screens | `frontend/` (`/admin`) |
| P4-17 End-to-end test: book → confirm → remind → change → notify | `backend/tests/`, `frontend/` |

### ⬜ Phase 5: Hardening
| Task | Will mainly touch |
|---|---|
| P5-01 Conversation test harness | `evals/` |
| P5-03, P5-04 Voice and scheduling edge-case tests | `evals/`, `backend/tests/` |
| P5-07 Staff acceptance testing on staging | `docs/` (results) |
| P5-08, P5-11 Patient-data-in-logs scan, penetration test | `scripts/`, `docs/compliance/` |
| P5-12 Incident response | `docs/runbooks/` |
| P5-14 HIPAA readiness review | `docs/compliance/` (re-checks P0-05, P0-06, P0-10, P0-11) |

### ⬜ Phase 6: Pilot
| Task | Will mainly touch |
|---|---|
| P6-01 Go-live checklist | `docs/runbooks/` |
| P6-02 Pilot dashboard | `infra/env/`, `backend/app/core/` |
| P6-04 Soft launch | `docs/` |
| P6-07 Pilot report and go/no-go | `docs/` |

---

## 5. Tooling (you can ignore these)
| File | What it's for |
|---|---|
| `.gitignore` | Files git must never commit (`.env`, Terraform state, keys…) |
| `.agents/skills/`, `.agents/workflows/` | OpenSpec helper instructions for AI tools |
| `openspec/specs/.gitkeep` | Keeps an empty folder in git |
