# AI Dental Receptionist

A web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website.
The AI identifies or registers them in Open Dental, books, reschedules or cancels real appointments, and sends confirmations and reminders.
It escalates emergencies, and creates a callback case for the clinic admin when it can't help.
It runs on Google Cloud (Gemini on Vertex AI, Speech-to-Text, Text-to-Speech, Cloud Run) and is designed to be HIPAA-ready from day one.

## Where to start
| Link | What |
|---|---|
| [CLAUDE.md](CLAUDE.md) | Project rules, tech stack, planned repo layout and workflow (for developers and AI agents) |
| [dental-ai-tasks/PROJECT_OVERVIEW.md](dental-ai-tasks/PROJECT_OVERVIEW.md) | Architecture, database schema, APIs, AI models and costs |
| [dental-ai-tasks/plan/](dental-ai-tasks/plan/) | Master project plan |
| [dental-ai-tasks/tasks/](dental-ai-tasks/tasks/) | One approved spec per task (`P0-01` … `P6-07`) |
| [dental-ai-tasks/PDF/](dental-ai-tasks/PDF/) | All task specs in one PDF |
| [dental-ai-tasks/DECISIONS.md](dental-ai-tasks/DECISIONS.md) | Decision log |
| [dental-ai-tasks/GLOSSARY.md](dental-ai-tasks/GLOSSARY.md) | Terms (PHI, BAA, PatNum, eConnector, …) |
| [docs/phase-0-discovery-compliance/](docs/phase-0-discovery-compliance/README.md) | Phase 0 overview: goal, all 16 tasks with issue numbers, status and order of work |
| [docs/discovery/clinic-decision-log.md](docs/discovery/clinic-decision-log.md) | Clinic decisions from the discovery workshop (P0-01) |

## Branches
| Branch | Purpose |
|---|---|
| `main` | Stable, reviewed work. Only the senior developer merges into it. |
| `Development` | Shared base: project setup, planning documents and tooling. New phase branches start from here or from `main`. |
| `feature/phase-<N>-<name>` | All work for one phase (one GitHub parent issue), with every sub-issue committed on it |

The phase branches:

| Phase | Branch | GitHub parent issue |
|---|---|---|
| P0 Discovery & compliance | `feature/phase-0-discovery-compliance` | #17 |
| P1 Core platform + Open Dental adapter | `feature/phase-1-core-platform` | created when the phase starts |
| P2 Text chat | `feature/phase-2-text-chat` | created when the phase starts |
| P3 Voice | `feature/phase-3-voice` | created when the phase starts |
| P4 Messaging + admin console | `feature/phase-4-messaging-admin` | created when the phase starts |
| P5 Hardening & security | `feature/phase-5-hardening` | created when the phase starts |
| P6 Pilot | `feature/phase-6-pilot` | created when the phase starts |

## Workflow
1. Each phase is a GitHub **parent issue**, and each task in it is a **sub-issue** (e.g. #17 → #1–#16).
2. For each sub-issue, on the phase branch:
   - `/opsx:propose` plans the task from its spec in `dental-ai-tasks/tasks/`;
   - `/opsx:apply` implements it.
3. Commit messages are one line: task ID plus what was done, e.g. `P0-01: add discovery pre-read, questionnaire, …`.
4. Push the phase branch. The senior developer reviews it and merges it into `main`.
5. After the merge, `/opsx:archive` closes out each OpenSpec change, and the sub-issues are closed.

## Status
Planning is complete: 70 approved task specs. Phase 0 is in progress on `feature/phase-0-discovery-compliance`; progress is tracked in GitHub issue #17 and its sub-issues.
