# CLAUDE.md — AI Dental Receptionist

> Keep this file **under 200 lines**. Link to `dental-ai-tasks/` docs instead of copying them here.

## What this project is
A web-based AI receptionist for US dental clinics. Patients use voice or text chat on the clinic's website.
The AI finds or registers the patient in **Open Dental** and books, reschedules or cancels real appointments.
It also sends confirmations and reminders by WhatsApp, escalates emergencies, and creates callback cases
that are emailed to the clinic admin (there is no live transfer). It must be **HIPAA-ready from day one**.

## Current state (update when it changes)
- **Planning is done; no product code exists yet.** All 70 task specs are approved (`status: approved`).
- **Phase 0** is on GitHub: parent issue **#17**, with sub-issues **#1–#16** (one per P0 task).
- The next phases go on GitHub only when the senior asks, using the same pattern: one parent issue per phase,
  tasks as sub-issues, full spec as the issue body.
- The code layout below is **Proposed** until P1-01 is built (DECISIONS #2).

## Where things are
| Path | What |
|---|---|
| `dental-ai-tasks/PROJECT_OVERVIEW.md` | Tech stack, DB schema, APIs, models and prices, integrations |
| `dental-ai-tasks/plan/AI_Dental_Receptionist_Project_Plan.md` | Master plan (sections referenced as "plan §N") |
| `dental-ai-tasks/tasks/<ID> <title>.md` | One spec per task, written from `tasks/_TEMPLATE.md` |
| `dental-ai-tasks/tasks/_CONSOLIDATION.md` | Which of the 124 seed tasks were merged into the 70 issues |
| `dental-ai-tasks/DECISIONS.md` | Append-only decision log (cited as "DECISIONS #N") |
| `dental-ai-tasks/GLOSSARY.md` | Terms: PHI, BAA, PatNum, AptNum, eConnector, … |
| `dental-ai-tasks/PDF/` | Compiled PDF of all task specs |
| `openspec/` | OpenSpec workflow (specs/changes); use the `opsx:*` skills |

## Phases
P0 Discovery & compliance → P1 Core platform + Open Dental adapter → P2 Text chat →
P3 Voice and P4 WhatsApp + admin console (run in parallel) → P5 Hardening → P6 Pilot.
Task IDs look like `P1-15`. A merged task keeps its ID as a stub file containing `merged_into: <survivor>`.
**Always work from the survivor spec.** IDs are never reused.

## Non-negotiable rules (from PROJECT_OVERVIEW §1 and the security sections)
1. **Open Dental is the source of truth.** Store only Open Dental IDs (`PatNum`, `AptNum`), never copies of patient records.
2. **The LLM talks; code acts.** Gemini only phrases replies and extracts data. A deterministic state machine
   decides, and the tool gateway executes. The LLM never calls Open Dental directly.
3. **Explicit confirmation before any write.** Show a confirmation card; the write must use exactly what the
   patient confirmed (operation hash plus an idempotency key).
4. **Safety over automation.** Emergency rules run *before* the LLM. No diagnosis. When unsure, create a callback.
5. **No PHI goes to a vendor without a signed BAA.** Allowed: Google Cloud, Google Workspace, and one messaging
   provider (each under a BAA). Never add a new third-party service, SDK or script without a BAA check.
6. **US only.** All Google Cloud services and Vertex AI use US locations. Only HIPAA-covered Google Cloud products.
   Use only GA Gemini model IDs (no `preview`, `exp` or `latest` models; DECISIONS #68).
7. **No PHI in logs, errors, analytics, test fixtures or commits.** Use the PHI-redacting logger. Tests use
   synthetic data only. Error responses never include exception text.
8. **Secrets** live only in Secret Manager and reach the app as env vars mapped by Cloud Run (`SecretStr` in
   settings). Never commit `.env` files, keys or Open Dental credentials.
9. **No slot hold** at offer or at selection. Collisions are caught by re-checking the slot before booking
   (DECISIONS #146, #290).

## Tech stack (details in PROJECT_OVERVIEW §2–§3)
- **Backend:** Python 3.12, FastAPI, Pydantic v2, async SQLAlchemy 2 + Alembic, asyncpg, redis-py, httpx.
- **Frontend:** Next.js + TypeScript + Tailwind. Patient widget at `/widget` (embedded by an iframe through
  `embed.js`) and admin console at `/admin`. WCAG 2.2 AA.
- **AI and voice:** Gemini on Vertex AI (Flash-Lite / Flash / Pro routing tiers), Google Speech-to-Text V2 and
  Text-to-Speech, Silero VAD on the server.
- **Google Cloud:** Cloud Run, Cloud SQL Postgres (CMEK), Memorystore Redis, Cloud Tasks and Scheduler,
  Secret Manager and KMS, Identity Platform (staff MFA), Cloud Logging, Monitoring and Trace.
- **Infrastructure and CI:** Terraform for everything; GitHub Actions deploys dev → staging → prod.

## Planned repo layout (Proposed, P1-01)
```text
backend/app/{api,core,db,integrations,domain,orchestrator,tools,voice}   backend/tests/{unit,integration}
frontend/   infra/{org,bootstrap,env}   evals/   scripts/   docs/{discovery,flows,compliance,architecture,adr,runbooks}
Makefile    docker-compose.yml (API + Postgres 16 + Redis 7)
```
- `integrations/` holds external clients (open_dental, vertex_ai, speech, messaging, email).
  `domain/` holds business logic (patients, scheduling, callbacks, reminders, clinic_config).
- App entry: `create_app()` in `backend/app/main.py`. Settings: `backend/app/core/config.py` (pydantic-settings).
- Health checks: `GET /healthz` (liveness) and `GET /readyz` (checks Postgres and Redis).

## Commands (once P1-01 exists)
```bash
make dev        # docker compose up: API, Postgres, Redis
make test       # pytest (unit tests; integration tests need the compose services)
make lint       # ruff check + ruff format --check
make typecheck  # mypy --strict
make fmt        # ruff format
cd backend && uv sync && uv run pytest -q
cd frontend && pnpm install && pnpm test
```

## Coding standards
- **Python:** ruff (line length 110; rule sets E, F, W, I, B, UP, S, ASYNC, RUF, T20, DTZ) and `mypy --strict`.
  - Never use `print()`; log through the structured logger.
  - Never use naive datetimes: they must be timezone-aware, with the clinic timezone handled explicitly (DST matters).
  - Use async I/O all the way through, with explicit timeouts on every external call.
  - Use the typed error hierarchy so every error returns the same JSON format.
- **Tests:** pytest with `asyncio_mode=auto`; mock HTTP with `respx`; mark Docker-dependent tests `@pytest.mark.integration`.
  Every bug fix comes with a test. Prompt or model changes must pass the conversation eval harness (P5-01).
- **Frontend:** strict TypeScript, eslint and prettier, Vitest, Playwright for end-to-end tests.
  Never store message text in localStorage, sessionStorage, cookies or the console.
- **Database:** every schema change is an Alembic migration. `audit_log` and `consents` are append-only.
- **Writes to Open Dental:** always through the tool gateway (schema validation, state preconditions,
  session scoping, idempotency keys). Retry only idempotent operations.

## Workflow per GitHub issue (OpenSpec)
1. Pick a sub-issue under its phase parent and check that its "Depends on" issues are closed.
2. Work on the phase branch `feature/phase-<N>-<name>` (e.g. `feature/phase-0-discovery-compliance`). There is one branch per parent issue/phase, and every sub-issue of that phase is committed on it.
3. `/opsx:propose <id>-<slug>: implement issue #N from dental-ai-tasks/tasks/<ID>*.md`. Review the result;
   use `/opsx:update` to revise it.
4. `/opsx:apply` to implement. Commit with a **one-line message**. **Always ask before pushing.**
5. The senior merges into `main`; we never merge and don't open PRs unless asked.
6. After the merge, `/opsx:archive` moves the change to `openspec/changes/archive/` and merges its specs into `openspec/specs/`.

## How to work in this repo
- **Before changing anything, read the task spec** (`dental-ai-tasks/tasks/<ID>*.md`). Its acceptance criteria and
  definition of done are the contract.
- **Markers:** `Proposed:` is our design choice and is not yet confirmed. `Verify:` is an unconfirmed fact about
  an external system; check the official docs before relying on it.
- **Decisions:** when a design choice is made or changed, append a row to `DECISIONS.md`
  (newest at the bottom). Never delete rows; a new row supersedes the old one.
- **Spec edits:** keep specs coherent with `PROJECT_OVERVIEW.md` and the other specs that reference them. When a task
  is merged or split, update `_CONSOLIDATION.md`.
- **Git:** one branch per phase (`feature/phase-0-discovery-compliance`, `feature/phase-1-core-platform`, …; full list in README.md); the next phase branch starts from `main` after the previous one is merged. The senior merges into `main`.
  Commit messages are one line. Never push without asking first.
- **GitHub:** repo `imranfakhrul/dental-clinic-voice-receptionist`. Sub-issues are linked with
  `gh api -X POST repos/<repo>/issues/<parent>/sub_issues -F sub_issue_id=<issue database id>`. Use the
  database id, not the issue number; `gh` 2.46 has no sub-issue flag.
- In issue and PR text, put code like `@dataclass` in backticks so it doesn't notify a GitHub user.

## Glossary quick reference
- **PHI:** protected health information. **BAA:** business associate agreement (required before a vendor receives PHI).
- **PatNum / AptNum:** Open Dental patient and appointment IDs; these are the only patient data we keep.
- **eConnector:** Open Dental program at the clinic that the Open Dental API reaches through.
- **Clinic SME:** the clinic contact (usually the office manager) who signs off decisions.
- **Callback case:** an unresolved request emailed to the clinic admin for a human follow-up.
