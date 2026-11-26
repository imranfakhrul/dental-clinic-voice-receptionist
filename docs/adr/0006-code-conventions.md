# ADR 0006: Code conventions

| | |
|---|---|
| Status | **Accepted** (2026-11-26) |
| Date | 2026-11-26 |
| Task | P0-14 (issue #15) · DECISIONS #318; enforced by P1-01 |
| Deciders | Riley Tech (tech lead), backend review (Riley Tech, second pass) |

## Context
P1-01 sets up the monorepo and its linters. One written set of rules avoids conflicting choices across P1–P5. Most rules already live in `CLAUDE.md` and `PROJECT_OVERVIEW.md`; this ADR makes them the accepted baseline.

## Options considered
| Option | For | Against |
|---|---|---|
| **Adopt the CLAUDE.md conventions as they are** | Already agreed in planning; tools enforce most of them | None found |
| Decide per module as code is written | Flexible | Drift; reviews argue style |

## Decision
| Area | Rule |
|---|---|
| Layout | `backend/app/{api,core,db,integrations,domain,orchestrator,tools,voice}`, `backend/tests/{unit,integration}`, `frontend/`, `infra/`, `evals/`, `scripts/`, `docs/` ([containers.md §3](../architecture/containers.md#3-component-responsibilities)) |
| Backend stack | Python 3.12, FastAPI, Pydantic v2, async SQLAlchemy 2 + Alembic, asyncpg, redis-py, httpx; `uv` for dependencies |
| Lint and types | `ruff` (line length 110; rules E, F, W, I, B, UP, S, ASYNC, RUF, T20, DTZ) and `mypy --strict` |
| Errors | Typed error hierarchy; one JSON error format; never exception text in responses |
| Logging | Structured PHI-redacting logger only; no `print()` |
| Time | Timezone-aware datetimes only; stored as UTC (`timestamptz`); clinic timezone handled explicitly (DST) |
| Data formats | Phone numbers E.164; dates of birth ISO `YYYY-MM-DD` |
| Config | Settings from environment variables (pydantic-settings); secrets as `SecretStr`, from Secret Manager in the cloud and the git-ignored `.env` locally |
| I/O | Async all the way; explicit timeout on every external call; retry only idempotent operations |
| Tests | pytest, `asyncio_mode=auto`, `respx` for HTTP; `@pytest.mark.integration` for Docker-dependent tests; synthetic data only; every bug fix with a test |
| Frontend | Next.js + strict TypeScript, eslint, prettier, Vitest, Playwright; WCAG 2.2 AA; no message text in browser storage or the console |
| Database | Every schema change is an Alembic migration; `audit_log` and `consents` append-only |
| Commits | One-line messages; one branch per phase |

## Consequences
- P1-01 configures the tools to enforce these rules in CI (P1-06).
- A rule change needs a new ADR revision and a CLAUDE.md update.

## Review triggers
- A rule blocks a task and a better option is shown.
- A tool version change makes a rule impossible (for example a ruff rule set renamed).
