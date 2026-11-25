---
id: P1-01
title: Set up monorepo, coding standards and FastAPI service skeleton
milestone: P1
epic: E1.1
size: M
labels: area:infra, area:backend, type:chore
depends_on: none
status: approved
---

# P1-01: Set up monorepo, coding standards and FastAPI service skeleton

## 1. Summary
Create the product repository and the first runnable backend. This issue also absorbs **P1-08 (FastAPI service skeleton with health checks and config)**.

The deliverables:
1. **Monorepo:**
   - layout: `backend/`, `frontend/`, `infra/`, `docs/`, `evals/`, `scripts/`;
   - tooling: uv, ruff, mypy, pytest, pnpm, eslint/prettier;
   - pre-commit hooks, including gitleaks;
   - PR template with the vendor and PHI check;
   - CODEOWNERS and branch protection;
   - a GitHub Actions **PR workflow** (lint, type check, tests, secret scan, compliance checkers).
2. **Backend skeleton:**
   - `create_app()` factory with a lifespan that opens async Postgres and Redis clients;
   - typed `Settings`;
   - `/healthz` and `/readyz`;
   - a request-ID middleware;
   - a typed error hierarchy with one JSON error format;
   - production safety switches (no docs, no debug).
3. **Local stack:** `docker compose up` runs the API, Postgres 16 and Redis 7, so every later task has a working base.
4. **Frontend shell:** one Next.js app with empty `/widget` and `/admin` areas.

The P0 documents move into the repo unchanged.

Done means:
- a new developer can clone the repo, run `make dev`, and get `200` from `/readyz`;
- every PR runs the checks in §6 and can't merge if they fail.

Deploying to Cloud Run moves to P1-06 (DECISIONS #81).

## 2. Why this matters
Every later task assumes these conventions:
- where code goes;
- how config is read;
- what an error looks like;
- how a request is traced;
- which checks guard a PR.

If each developer invents them, P2's orchestrator, P1's adapters and P4's console won't fit together.

Two compliance controls also start here:
- the **PR vendor/PHI check** and **CODEOWNERS** (P0-10);
- **secret scanning on every commit** (P0-11 R12).

The skeleton's production switches are the first control for P0-11 R01: no debug pages or stack traces in prod.

Plan references: §3.2 (stack), §1 principle 5 (swappable providers), §6 (logging, debug tools disabled in production). The conventions follow CLAUDE.md "Proposed code conventions", accepted as ADR 0006 (P0-14).

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P1, Core Platform & Open Dental Adapter**.
- **Architecture (P0-14):**
  - two Cloud Run services, `web` (Next.js) and `api` (FastAPI);
  - the `api` service serves REST, WebSocket and Cloud Tasks handlers;
  - module responsibilities: `api/`, `core/`, `db/`, `integrations/`, `domain/`, `orchestrator/`, `tools/`.
- **Conventions (ADR 0006):**
  - Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 async, Alembic;
  - type hints everywhere, `ruff` + `mypy`;
  - errors as typed exception classes;
  - env vars in `UPPER_SNAKE_CASE`, secrets from Secret Manager;
  - times stored in UTC; phones in E.164; DOB as ISO `YYYY-MM-DD`.
- **Config already defined by approved specs:**
  - `OPEN_DENTAL_BASE_URL` (P0-12);
  - `VERTEX_PROJECT`, `VERTEX_LOCATION`, `GEMINI_MODEL_LITE`, `GEMINI_MODEL_FLASH`, `GEMINI_MODEL_PRO`, `GEMINI_ALLOWED_MODELS` (P0-13).
- **Compliance files that must live in the repo:**
  - from P0-10: `docs/compliance/vendors.yaml`, `scripts/compliance/check_vendors.py`, `docs/compliance/pr-vendor-check.md`;
  - from P0-06: `infra/org/allowed_services.yaml`;
  - from P0-07a and P0-15: `docs/compliance/messaging_policy.yaml`, `docs/messaging/templates.yaml`, `scripts/messaging/check_templates.py`;
  - from P0-01 to P0-04: `docs/discovery/`, `docs/flows/`.
- **Tool choices** (Proposed in DECISIONS #82; **Verify** current versions at setup and lock them):
  - **uv**: Python package and environment manager with a lockfile, https://docs.astral.sh/uv/;
  - **ruff**: linter and formatter;
  - **mypy**: type checker;
  - **pnpm**: Node package manager;
  - **pre-commit**: git hooks;
  - **gitleaks**: secret scanner, https://github.com/gitleaks/gitleaks.

## 4. Scope
**In scope**
- Repository creation (private, GitHub organization), directory layout, root `README.md`, `Makefile`.
- Backend: `pyproject.toml`, `uv.lock`, the `app` package with `main.py`, `core/config.py`, `core/errors.py`, `core/request_id.py`, `core/logging.py` (minimal JSON logger; P1-07 replaces its formatter with PHI redaction), `db/session.py`, `core/redis.py`, `api/health.py`, `api/deps.py`.
- Tests: `backend/tests/unit/`, `backend/tests/integration/`, pytest config, test fixtures for the app and settings.
- Local stack: `Dockerfile` for the API, `docker-compose.yml` (api, postgres:16, redis:7), `.env.example`.
- Frontend shell: Next.js + TypeScript + Tailwind app in `frontend/` with `/widget` and `/admin` placeholder pages and a `/api/health` route, plus eslint, prettier and `tsc --noEmit`.
- Quality gates: `.pre-commit-config.yaml`, `.github/workflows/pr.yml`, `.github/pull_request_template.md`, `.github/CODEOWNERS`, branch protection settings (documented, applied by an org admin).
- Moving the P0 documents into `docs/` and `scripts/` unchanged.

**Out of scope** (and which task covers it)
- Terraform, Artifact Registry, Cloud Run services → P1-02
- Deploy pipeline, Workload Identity Federation, Cloud Run dev deploy → P1-06 (takes over the P1-08 "deploys to Cloud Run dev" criterion)
- Cloud SQL and the database schema → P1-03; Alembic migrations beyond the empty baseline → P1-03
- PHI-redacting logger and audit log → P1-07
- Secret Manager and KMS setup, service accounts → P1-05
- Auth and sessions → P1-13
- Widget and console UI → P2-25, P4-09

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| None (hard) | — | Start immediately. |
| P0-10 (approved spec, soft) | `pr-vendor-check.md`, CODEOWNERS entries, `check_vendors.py` | If they aren't written yet, copy the text from the P0-10 spec §6 and add the workflow step with `continue-on-error: true` until the script exists. |
| P0-15 / P0-06 (approved specs, soft) | `check_templates.py`, `allowed_services.yaml` | Same: add the steps, and skip them with a clear log line if the file doesn't exist yet. |
| GitHub org admin (external) | Repo creation, the `compliance-owners` and `backend-leads` teams, branch protection | Ask on day 1; the settings to apply are listed in §6. |

## 6. Interface contract

### Repository layout
```text
repo/
├── README.md                     # quick start, links to docs/architecture and docs/adr
├── Makefile                      # dev, test, lint, typecheck, fmt, up, down
├── .pre-commit-config.yaml
├── .gitleaks.toml
├── .editorconfig
├── .github/
│   ├── CODEOWNERS
│   ├── pull_request_template.md
│   └── workflows/pr.yml
├── backend/
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── Dockerfile
│   ├── alembic.ini               # baseline only; P1-03 adds migrations
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py               # create_app()
│   │   ├── api/                  # health.py, deps.py (routes per feature added later)
│   │   ├── core/                 # config.py, errors.py, request_id.py, logging.py, redis.py
│   │   ├── db/                   # session.py, base.py, migrations/
│   │   ├── integrations/         # open_dental/, vertex_ai/, speech/, messaging/, email/  (empty packages)
│   │   ├── domain/               # patients/, scheduling/, callbacks/, reminders/, clinic_config/
│   │   ├── orchestrator/
│   │   └── tools/
│   └── tests/
│       ├── conftest.py
│       ├── unit/
│       └── integration/
├── frontend/                     # Next.js app: app/widget, app/admin
├── infra/                        # org/ (from P0-06), bootstrap/ (P0-05), env/ (P1-02)
├── evals/                        # golden/ (P0-04), spike/ (P0-13)
├── scripts/                      # compliance/ (P0-10), messaging/ (P0-15), open_dental/ (P0-12)
├── docs/                         # discovery/, flows/, compliance/, architecture/, adr/, runbooks/, integrations/, messaging/
└── docker-compose.yml
```

### `backend/pyproject.toml` (key parts; versions are lower bounds, the lockfile pins exact ones)
```toml
[project]
name = "dental-ai-backend"
requires-python = ">=3.12,<3.13"
dependencies = [
  "fastapi>=0.115",
  "uvicorn[standard]>=0.30",
  "pydantic>=2.7",
  "pydantic-settings>=2.3",
  "sqlalchemy[asyncio]>=2.0.30",
  "asyncpg>=0.29",
  "alembic>=1.13",
  "redis>=5.0",
  "httpx>=0.27",
]

[dependency-groups]
dev = ["pytest>=8", "pytest-asyncio>=0.23", "respx>=0.21", "mypy>=1.10", "ruff>=0.5", "pre-commit>=3.7"]

[tool.ruff]
line-length = 110
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "B", "UP", "S", "ASYNC", "RUF", "T20", "DTZ"]
# S = bandit security rules; T20 = no print(); DTZ = no naive datetimes
ignore = ["S101"]            # allow assert in tests (per-file below)

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S101", "S105", "S106"]

[tool.mypy]
python_version = "3.12"
strict = true
plugins = ["pydantic.mypy"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
markers = ["integration: needs docker compose services"]
```
**Verify** the current package versions at setup. These lower bounds are Proposed; uv records the exact versions.

### Settings (`app/core/config.py`)
```python
from enum import StrEnum
from functools import lru_cache
from pydantic import Field, PostgresDsn, RedisDsn, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Env(StrEnum):
    LOCAL = "local"
    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", frozen=True)

    ENV: Env = Env.LOCAL
    SERVICE_NAME: str = "api"
    LOG_LEVEL: str = "INFO"
    DATABASE_URL: PostgresDsn                      # postgresql+asyncpg://user:pass@host:5432/db
    REDIS_URL: RedisDsn                            # redis://host:6379/0 (rediss:// in cloud)
    DB_POOL_SIZE: int = Field(default=5, ge=1, le=50)
    READINESS_TIMEOUT_S: float = Field(default=1.0, gt=0, le=5)
    CORS_ALLOWED_ORIGINS: list[str] = []           # exact origins, never "*"
    # Integrations (values set per environment; secrets injected by Cloud Run from Secret Manager)
    OPEN_DENTAL_BASE_URL: str = "https://api.opendental.com/api/v1"   # P0-12
    OD_DEVELOPER_KEY: SecretStr | None = None                          # secret od-developer-key
    VERTEX_PROJECT: str | None = None                                  # P0-13
    VERTEX_LOCATION: str = "us"
    GEMINI_MODEL_LITE: str | None = None
    GEMINI_MODEL_FLASH: str | None = None
    GEMINI_MODEL_PRO: str | None = None
    GEMINI_ALLOWED_MODELS: list[str] = []

    @property
    def is_prod(self) -> bool:
        return self.ENV is Env.PROD

    @field_validator("VERTEX_LOCATION")
    @classmethod
    def _us_only(cls, v: str) -> str:
        if v != "us" and not v.startswith("us-"):
            raise ValueError("VERTEX_LOCATION must be 'us' or a 'us-*' region (DECISIONS #65)")
        return v

    @field_validator("CORS_ALLOWED_ORIGINS")
    @classmethod
    def _no_wildcard(cls, v: list[str]) -> list[str]:
        if any(o == "*" or "*" in o for o in v):
            raise ValueError("CORS origins must be exact; wildcards are not allowed")
        return v

    @model_validator(mode="after")
    def _model_ids_allowed(self) -> "Settings":
        for m in (self.GEMINI_MODEL_LITE, self.GEMINI_MODEL_FLASH, self.GEMINI_MODEL_PRO):
            if m is None:
                continue
            if any(bad in m for bad in ("preview", "exp", "latest")) or m not in self.GEMINI_ALLOWED_MODELS:
                raise ValueError(f"model id not allowed: {m} (DECISIONS #68)")
        return self

@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]   # values come from env
```
Rules:
- secrets are `SecretStr` and never logged or returned;
- a missing required setting fails at startup with the variable **name** only;
- secret values reach the process as env vars that Cloud Run maps from Secret Manager (P1-02/P1-05), so the skeleton never calls Secret Manager itself. Per-clinic Open Dental keys are fetched at runtime by P1-15.

### App factory and lifespan (`app/main.py`)
```python
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from fastapi import FastAPI
from app.core.config import Settings, get_settings
from app.core.errors import install_error_handlers
from app.core.request_id import RequestIdMiddleware
from app.core.logging import configure_logging
from app.core.redis import create_redis
from app.db.session import create_engine_and_sessionmaker
from app.api import health

def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine, sessionmaker = create_engine_and_sessionmaker(settings)
        redis = create_redis(settings)
        app.state.settings, app.state.engine = settings, engine
        app.state.sessionmaker, app.state.redis = sessionmaker, redis
        try:
            yield
        finally:
            await redis.aclose()
            await engine.dispose()

    app = FastAPI(
        title="dental-ai-api",
        lifespan=lifespan,
        debug=False,                                   # never True, in any environment
        docs_url=None if settings.is_prod else "/docs",
        redoc_url=None,
        openapi_url=None if settings.is_prod else "/openapi.json",
    )
    app.add_middleware(RequestIdMiddleware)
    install_error_handlers(app)
    app.include_router(health.router)
    return app

app = create_app()   # uvicorn app.main:app
```
`db/session.py` creates `create_async_engine(str(settings.DATABASE_URL), pool_size=settings.DB_POOL_SIZE, pool_pre_ping=True)` and `async_sessionmaker(engine, expire_on_commit=False)`. `core/redis.py` returns `redis.asyncio.Redis.from_url(str(settings.REDIS_URL), decode_responses=True, socket_timeout=2)`.

`api/deps.py` exposes the dependencies later tasks use:
```python
async def get_db(request: Request) -> AsyncIterator[AsyncSession]: ...
def get_redis(request: Request) -> Redis: ...
def get_settings_dep(request: Request) -> Settings: ...
```

### Health endpoints (`app/api/health.py`)
| Endpoint | Purpose | Checks | Response |
|---|---|---|---|
| `GET /healthz` | Liveness (process is up) | None | `200 {"status":"ok"}` |
| `GET /readyz` | Readiness (can serve traffic) | `SELECT 1` on Postgres and `PING` on Redis, each with `READINESS_TIMEOUT_S`, run concurrently | `200 {"status":"ready","checks":{"db":"ok","redis":"ok"}}`, or `503 {"status":"not_ready","checks":{"db":"ok","redis":"timeout"}}` |

Check values: `ok`, `timeout`, `error`. Exception text is never returned; it is logged with the request ID. Neither endpoint needs auth, and neither returns versions or hostnames. Both are excluded from request logging at INFO level, to avoid noise.

### Errors (`app/core/errors.py`)
```python
class AppError(Exception):
    """Base for all expected errors. Message must not contain PHI."""
    code: str = "internal_error"
    http_status: int = 500
    def __init__(self, message: str = "", *, details: dict[str, str] | None = None) -> None:
        super().__init__(message)
        self.message = message or self.code
        self.details = details or {}

class BadRequestError(AppError):
    code, http_status = "bad_request", 400

class UnauthorizedError(AppError):
    code, http_status = "unauthorized", 401

class ForbiddenError(AppError):
    code, http_status = "forbidden", 403

class NotFoundError(AppError):
    code, http_status = "not_found", 404

class ConflictError(AppError):
    code, http_status = "conflict", 409

class RateLimitedError(AppError):
    code, http_status = "rate_limited", 429

class DependencyUnavailableError(AppError):
    code, http_status = "dependency_unavailable", 503
```
Every error response has the same shape:
```json
{"error": {"code": "not_found", "message": "Case not found", "request_id": "3f6c1e0a9b0d4d7e8a1f2c3d4e5f6a7b"}}
```
Handlers:
- `AppError` → its status and code;
- `RequestValidationError` → `422` with `code: "validation_error"`, with `details` listing **field paths and error types only**, never the submitted values (they may be PHI);
- `StarletteHTTPException` → mapped to the same shape;
- any other `Exception` → `500 internal_error` with a fixed message. The stack trace is logged and never returned.

### Request ID (`app/core/request_id.py`)
- Read `X-Request-ID` if it matches `^[A-Za-z0-9-]{8,64}$`; otherwise generate `uuid4().hex`.
- Also parse `X-Cloud-Trace-Context` (`TRACE_ID/SPAN_ID;o=1`) into `trace_id`, for log correlation in Cloud Logging (P1-07).
- Store both in `contextvars`. Every log line includes them, and the response header `X-Request-ID` echoes the request ID.
- Pure ASGI middleware (not `BaseHTTPMiddleware`), so it works for WebSockets too.

### Minimal logging (`app/core/logging.py`; P1-07 replaces the formatter)
- JSON lines to stdout: `{"severity","message","request_id","trace_id","logger","time"}`.
- **Only messages and allow-listed fields are logged.** No request or response bodies, and no query strings.
- `print()` is banned by ruff rule `T20`.

### Local stack (`docker-compose.yml`)
```yaml
services:
  postgres:
    image: postgres:16
    environment: {POSTGRES_USER: app, POSTGRES_PASSWORD: app, POSTGRES_DB: app}
    ports: ["5432:5432"]
    healthcheck: {test: ["CMD-SHELL", "pg_isready -U app"], interval: 2s, retries: 20}
  redis:
    image: redis:7
    ports: ["6379:6379"]
    healthcheck: {test: ["CMD", "redis-cli", "ping"], interval: 2s, retries: 20}
  api:
    build: ./backend
    env_file: ./backend/.env.example
    environment:
      DATABASE_URL: postgresql+asyncpg://app:app@postgres:5432/app
      REDIS_URL: redis://redis:6379/0
    ports: ["8080:8080"]
    depends_on:
      postgres: {condition: service_healthy}
      redis: {condition: service_healthy}
```
`.env.example` contains only non-secret local defaults. It is the only committed env file, and `.gitignore` excludes `.env`.

### Dockerfile (backend; Proposed)
```dockerfile
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY app ./app
RUN useradd --uid 10001 --no-create-home appuser
USER appuser
ENV PORT=8080
CMD ["sh", "-c", "uv run --no-sync uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
```
**Verify:**
- pin the uv image by digest instead of `latest` before P1-06;
- `--forwarded-allow-ips` must be restricted, or replaced by trusting only the load balancer's headers, in P1-02.

### Makefile targets
```make
dev:        ## run the local stack
	docker compose up --build
test:       ## unit tests
	cd backend && uv run pytest -m "not integration"
test-int:   ## integration tests against docker compose
	cd backend && uv run pytest -m integration
lint:
	cd backend && uv run ruff check . && uv run ruff format --check .
typecheck:
	cd backend && uv run mypy app
fmt:
	cd backend && uv run ruff format . && uv run ruff check --fix .
```

### Pre-commit (`.pre-commit-config.yaml`; pin `rev`s to current tags at setup)
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: <tag>
    hooks: [{id: ruff, args: [--fix]}, {id: ruff-format}]
  - repo: https://github.com/gitleaks/gitleaks
    rev: <tag>
    hooks: [{id: gitleaks}]
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: <tag>
    hooks:
      - {id: check-added-large-files, args: ["--maxkb=500"]}
      - {id: check-merge-conflict}
      - {id: end-of-file-fixer}
      - {id: detect-private-key}
  - repo: local
    hooks:
      - {id: mypy, name: mypy, entry: bash -c "cd backend && uv run mypy app", language: system, pass_filenames: false, files: ^backend/}
```
`.gitleaks.toml` extends the default rules with a custom rule for the Open Dental auth header (`ODFHIR [A-Za-z0-9]+/[A-Za-z0-9]+`). The published hosted-test key (P0-12) is allow-listed by its exact value, with a comment.

### PR workflow (`.github/workflows/pr.yml`)
```yaml
name: pr
on: [pull_request]
permissions: {contents: read}
jobs:
  backend:
    runs-on: ubuntu-latest
    services:
      postgres: {image: "postgres:16", env: {POSTGRES_USER: app, POSTGRES_PASSWORD: app, POSTGRES_DB: app}, ports: ["5432:5432"],
                 options: "--health-cmd pg_isready --health-interval 2s --health-retries 20"}
      redis: {image: "redis:7", ports: ["6379:6379"], options: "--health-cmd 'redis-cli ping' --health-interval 2s --health-retries 20"}
    env:
      DATABASE_URL: postgresql+asyncpg://app:app@localhost:5432/app
      REDIS_URL: redis://localhost:6379/0
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6        # Verify current major version
      - run: cd backend && uv sync --frozen
      - run: cd backend && uv run ruff check . && uv run ruff format --check .
      - run: cd backend && uv run mypy app
      - run: cd backend && uv run pytest
  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
      - uses: actions/setup-node@v4
        with: {node-version: "22", cache: pnpm, cache-dependency-path: frontend/pnpm-lock.yaml}
      - run: cd frontend && pnpm install --frozen-lockfile && pnpm lint && pnpm typecheck
  compliance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: {fetch-depth: 0}
      - uses: gitleaks/gitleaks-action@v2   # Verify licence terms for org repos
        env: {GITHUB_TOKEN: "${{ secrets.GITHUB_TOKEN }}"}
      - uses: astral-sh/setup-uv@v6
      - run: uv run --with pyyaml --with jsonschema python scripts/compliance/check_vendors.py
      - run: uv run --with pyyaml --with jsonschema python scripts/messaging/check_templates.py --templates docs/messaging/templates.yaml --policy docs/compliance/messaging_policy.yaml
```
Required status checks: `backend`, `frontend` and `compliance`.

**Verify:**
- the action major versions;
- whether `gitleaks-action` needs a licence key for organization repos; if so, run the gitleaks binary directly instead.

### PR template (`.github/pull_request_template.md`)
```markdown
## What and why
<!-- Issue: #… · Summary of the change -->

## How to test
<!-- Commands, screenshots (synthetic data only) -->

## Checklist
- [ ] Tests added/updated and passing locally
- [ ] No secrets, keys or tokens in code, config, tests or this description
- [ ] Errors use `AppError` subclasses; no PHI in error messages or logs

<!-- The section below is copied verbatim from docs/compliance/pr-vendor-check.md (P0-10). Keep them identical. -->
### Vendor and PHI check
- [ ] This PR adds **no** new external service, SaaS, SDK that sends data out, or Google Cloud API. If it does: `docs/compliance/vendors.yaml` (and `infra/org/allowed_services.yaml` for Google APIs) is updated in this PR, and the compliance owner is a reviewer.
- [ ] This PR sends **no new kind of PHI** to an existing vendor. If it does: the vendor's row and the clinic BAA Annex A (P0-09) and `docs/architecture/phi-flows.md` (P0-14) are updated.
- [ ] No PHI in code, tests, fixtures, logs, screenshots or the PR description (synthetic data only).
- [ ] No Pre-GA (preview/experimental) model or feature receives PHI.
```

### CODEOWNERS and branch protection
```text
*                                     @<org>/backend-leads
/frontend/                            @<org>/frontend-leads
/docs/compliance/                     @<org>/compliance-owners
/docs/architecture/phi-flows.md       @<org>/compliance-owners
/infra/org/allowed_services.yaml      @<org>/compliance-owners
/backend/app/integrations/            @<org>/compliance-owners @<org>/backend-leads
/scripts/compliance/                  @<org>/compliance-owners
/docs/messaging/templates.yaml        @<org>/compliance-owners
/.github/                             @<org>/backend-leads
```
Branch protection on `main` (applied by an org admin; record screenshots in the PR):
- require a pull request with 1 approval;
- require review from Code Owners;
- dismiss stale approvals;
- require the `backend`, `frontend` and `compliance` status checks;
- require branches to be up to date;
- no force pushes or deletions;
- include administrators.

**Verify** the setting names in GitHub's current UI.

### Frontend shell (`frontend/`)
- Next.js (App Router) + TypeScript (strict) + Tailwind.
- Routes: `/widget` (placeholder "Assistant coming soon"), `/admin` (placeholder) and `/api/health` → `{"status":"ok"}`.
- Scripts: `pnpm dev`, `pnpm build`, `pnpm lint`, `pnpm typecheck` (`tsc --noEmit`).
- No analytics or third-party scripts (P0-14 F01 rule). `next.config` sets `poweredByHeader: false`.

## 7. Implementation guide
1. **Create the repo** (private) with the org admin; create the teams `backend-leads`, `frontend-leads` and `compliance-owners` (P0-10).
2. **Lay out the directories** (§6). Move the P0 artifacts in unchanged; use `git mv` if they were in a temporary repo, to keep history.
3. **Backend:**
   - `uv init` and edit `pyproject.toml` as in §6, then `uv add` the dependencies so that `uv.lock` is created;
   - write `config.py`, `errors.py`, `request_id.py`, `logging.py`, `redis.py`, `db/session.py`, `api/health.py`, `api/deps.py` and `main.py` as specified;
   - `alembic init` with the async template and an empty baseline revision.
4. **Tests** (§10). Fixtures:
   - `settings` (built with explicit values, never reading a real `.env`);
   - `app` (`create_app(settings)`);
   - `client` (`httpx.AsyncClient` with `ASGITransport`, running the lifespan).
5. **Local stack:** the Dockerfile, `docker-compose.yml`, `.env.example` and the `Makefile`. Check that `make dev` then `curl localhost:8080/readyz` returns 200, and that stopping Redis returns 503.
6. **Frontend shell:** `pnpm create next-app` (TypeScript, App Router, Tailwind, ESLint), the placeholder routes, and `typecheck`.
7. **Quality gates:**
   - pre-commit config, gitleaks config, the PR workflow, the PR template (copy P0-10's text exactly) and CODEOWNERS;
   - ask the org admin to apply branch protection;
   - open a test PR that adds a fake secret and check that gitleaks blocks it, then close it without merging.
8. **README:** a quick start (`make dev`, `make test`), the layout, links to the ADRs and architecture, and "how to add a setting" (field in `Settings` + `.env.example` + docs; secrets via Secret Manager only).
9. **Notify:**
   - P1-02 / P1-06: Dockerfile, port 8080, `/healthz` and `/readyz`, required env vars, the deploy criterion moved to P1-06;
   - P1-03: Alembic baseline and session factory;
   - P1-07: logging module to replace;
   - P1-13: error classes;
   - P1-15 / P2-03: settings fields;
   - every P1 and P2 owner: the repo is ready.

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| A required env var is missing | The process exits at startup with `ValidationError` naming the variable (no value). Cloud Run marks the revision failed. |
| `VERTEX_LOCATION=global` or a `-preview` model is configured | Startup fails (validators in `Settings`). |
| Postgres is down at startup | The app starts (lifespan creates the pool lazily); `/readyz` returns 503 with `db: error` until it recovers. |
| Redis responds slower than `READINESS_TIMEOUT_S` | `/readyz` returns 503 with `redis: timeout`. `/healthz` stays 200 (process alive). |
| A client sends a 2 KB `X-Request-ID` or one with odd characters | Ignored; a new ID is generated. |
| A validation error on a body containing a patient's name | The 422 response lists field paths and types only, and the log line has no values. |
| An unhandled exception | 500 with the fixed message and request ID; stack trace in logs (P1-07 redacts values). |
| A developer commits `.env` or a key | Pre-commit gitleaks blocks locally; the CI `compliance` job blocks the PR. If it was pushed, rotate the key (P0-12 edge case). |
| `ENV=prod` and someone requests `/docs` | 404. |
| CORS: request from an origin not in `CORS_ALLOWED_ORIGINS` | No CORS headers; the browser blocks it. Wildcards are not allowed (a validator rejects `*`). |

## 9. Security, HIPAA and PHI
- **No PHI is handled.** The skeleton has no patient data paths. It sets the rules every later task inherits:
  - error responses and 422 details never echo input values;
  - logs carry only messages and allow-listed fields, and `print` is banned;
  - `debug=False` everywhere, and no OpenAPI docs in prod;
  - secrets are `SecretStr`, injected from Secret Manager, never in env files committed to git;
  - the container runs as a non-root user.
- **Repository controls:**
  - gitleaks in pre-commit and CI;
  - the PR vendor/PHI checklist;
  - CODEOWNERS on compliance-sensitive paths;
  - branch protection.
- **Audit:** not applicable yet (P1-07). The git history and PR reviews are the change record.

## 10. Testing
Unit (`backend/tests/unit/`):
```python
async def test_healthz_ok(client):
    r = await client.get("/healthz")
    assert r.status_code == 200 and r.json() == {"status": "ok"}

async def test_request_id_echoed_and_generated(client):
    r = await client.get("/healthz", headers={"X-Request-ID": "abc12345"})
    assert r.headers["X-Request-ID"] == "abc12345"
    r2 = await client.get("/healthz", headers={"X-Request-ID": "bad id!"})
    assert r2.headers["X-Request-ID"] != "bad id!" and len(r2.headers["X-Request-ID"]) == 32

async def test_validation_error_hides_values(client_with_echo_route):
    r = await client_with_echo_route.post("/_test/echo", json={"name": 123})
    body = r.json()
    assert r.status_code == 422 and body["error"]["code"] == "validation_error"
    assert "123" not in r.text

async def test_unhandled_exception_is_generic(client_with_boom_route, caplog):
    r = await client_with_boom_route.get("/_test/boom")
    assert r.status_code == 500 and r.json()["error"]["code"] == "internal_error"
    assert "Traceback" not in r.text

def test_settings_reject_global_location():
    with pytest.raises(ValidationError):
        Settings(DATABASE_URL="postgresql+asyncpg://a:b@h/d", REDIS_URL="redis://h:6379/0", VERTEX_LOCATION="global")

def test_settings_reject_preview_model():
    with pytest.raises(ValidationError):
        Settings(DATABASE_URL="postgresql+asyncpg://a:b@h/d", REDIS_URL="redis://h:6379/0",
                 GEMINI_MODEL_FLASH="gemini-3.1-pro-preview", GEMINI_ALLOWED_MODELS=["gemini-3.1-pro-preview"])

def test_prod_disables_docs():
    app = create_app(make_settings(ENV="prod"))
    assert app.docs_url is None and app.openapi_url is None
```
The `/_test/*` routes are registered only by test fixtures, never in `create_app`.

Integration (`-m integration`, against docker compose or the CI services):
- `/readyz` → 200 with both checks `ok`;
- with Redis stopped (or `REDIS_URL` pointing at a closed port) → 503 with `redis` `error` or `timeout`, and `/healthz` still 200;
- the `get_db` dependency runs `SELECT 1` in a request.

CI:
- the workflow fails on a ruff error, a mypy error, a failing test, or a fake secret (the test PR in step 7);
- the frontend job fails on a type error.

## 11. Acceptance criteria
- [ ] The repo exists with the §6 layout; the P0 artifacts are moved in unchanged
- [ ] `make dev` starts api, Postgres and Redis; `GET /readyz` returns 200; with Redis stopped it returns 503 and `/healthz` stays 200
- [ ] `Settings`, `create_app`, the error hierarchy and handlers, request-ID middleware and health endpoints match §6; the §10 unit and integration tests pass
- [ ] In `ENV=prod`, `/docs` and `/openapi.json` return 404 and no error response contains a stack trace or input values
- [ ] Pre-commit (ruff, mypy, gitleaks, hygiene hooks) is configured; a fake secret is blocked locally and in CI
- [ ] The PR workflow runs backend (lint, type, tests), frontend (lint, typecheck) and compliance (gitleaks, `check_vendors.py`, `check_templates.py`) on every PR, and all three are required checks
- [ ] The PR template contains the P0-10 vendor/PHI check verbatim; CODEOWNERS and branch protection (Code Owner review required) are applied
- [ ] The Next.js shell builds with `/widget`, `/admin` and `/api/health`
- [ ] The P1-02, P1-03, P1-06, P1-07, P1-13, P1-15 and P2-03 issues are notified

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI
- [ ] PR reviewed (HIPAA review if labelled `phi`): tech lead review; no `phi` label (no PHI paths)
- [ ] No PHI in logs: error and logging tests above pass
- [ ] Docs / README updated: root README quick start, "how to add a setting"

## 13. Hand-off
| Task | Can rely on |
|---|---|
| P1-02 Terraform base | Dockerfile, port 8080, `/healthz` (liveness) and `/readyz` (startup/readiness), the env var list |
| P1-03 Cloud SQL + schema | `db/session.py`, the `Base` metadata, Alembic async baseline |
| P1-05 Secrets | The `SecretStr` settings and env var names to map from Secret Manager |
| P1-06 CI/CD | The PR workflow to extend with build/deploy; the "deploys to Cloud Run dev" criterion |
| P1-07 Logging/audit | `core/logging.py` to replace; `request_id`/`trace_id` contextvars |
| P1-13 Auth/sessions | `AppError` subclasses (401/403/429), `api/deps.py` pattern |
| P1-15, P2-03 and all later backend tasks | `get_settings`, `get_db`, `get_redis`, error classes, test fixtures |
| P2-25, P4-09 | The Next.js shell and its routes |

## 14. Open questions
| Question | Owner | Needed by |
|---|---|---|
| GitHub organization name, and who is the org admin for branch protection? | Project sponsor | Step 1 |
| Does `gitleaks-action` need a paid licence for our org? If yes, use the gitleaks binary in CI. | Tech lead | Step 7 |
| Node version policy: Node 22 LTS (Proposed)? | Tech lead | Step 6 |

## 15. References
- Plan §3.2, §1 principle 5, §6
- ADR 0006 (P0-14); CLAUDE.md "Proposed code conventions"
- FastAPI lifespan events: https://fastapi.tiangolo.com/advanced/events/
- Pydantic settings: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
- SQLAlchemy asyncio: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- uv: https://docs.astral.sh/uv/
- Ruff rules: https://docs.astral.sh/ruff/rules/
- gitleaks: https://github.com/gitleaks/gitleaks
- GitHub CODEOWNERS and protected branches: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository
- Related tasks: P0-06, P0-10, P0-12, P0-13, P0-14, P0-15, P1-02, P1-03, P1-05, P1-06, P1-07, P1-13, P1-15, P2-03, P2-25, P4-09
