## Purpose

Define which Gemini models and endpoints the system may use for each routing tier, which backend may be used where, the startup checks that enforce it, the Gemini features and data settings that are forbidden or required, and how a model is changed over its lifecycle.

## ADDED Requirements

### Requirement: Only approved GA models, set by config
Each tier's model SHALL be set by config (`GEMINI_MODEL_LITE`, `GEMINI_MODEL_FLASH`, `GEMINI_MODEL_PRO`), SHALL be in `GEMINI_ALLOWED_MODELS` (the ADR's approved list), and SHALL be a GA model with a 12-month lifecycle; the application SHALL refuse to start if any model ID contains `preview`, `exp` or `latest` or is not in the allowed list.

#### Scenario: Preview model configured
- **WHEN** `GEMINI_MODEL_PRO` is set to an ID containing `preview`
- **THEN** startup fails with a configuration error

#### Scenario: Model outside the approved list
- **WHEN** a tier model is not in `GEMINI_ALLOWED_MODELS`
- **THEN** startup fails with a configuration error

### Requirement: PHI only through Vertex AI on a US endpoint
Any request that may contain PHI SHALL use the Vertex AI backend with `VERTEX_LOCATION` set to `us` or a `us-*` region; the application SHALL refuse to start with `VERTEX_LOCATION=global` or any non-US location.

#### Scenario: Global endpoint configured
- **WHEN** `VERTEX_LOCATION` is `global`
- **THEN** startup fails with a configuration error

### Requirement: Developer API only locally with synthetic data
The Gemini Developer API backend (`GEMINI_BACKEND=developer`, API key) SHALL be allowed only when `APP_ENV=local`, with synthetic data only, and SHALL never be used in a cloud environment or with PHI; its API key SHALL live only in a git-ignored local env file.

#### Scenario: Developer backend outside local
- **WHEN** `GEMINI_BACKEND=developer` and `APP_ENV` is not `local`
- **THEN** startup fails with a configuration error

#### Scenario: API key location
- **WHEN** the repository is searched for a Gemini API key value
- **THEN** none is found; only the empty placeholder in `.env.example` exists

### Requirement: Forbidden Gemini features
Requests SHALL NOT include grounding tools (Google Search or Google Maps), and projects SHALL NOT enable request-response logging; durable implicit caching SHALL be off (`cacheConfig` retention `EPHEMERAL`, or all caching off if the compliance advisor requires).

#### Scenario: Grounding tool in a request
- **WHEN** code builds a Gemini request with a `google_search` or `google_maps` tool
- **THEN** the provider rejects it before sending

### Requirement: Spike output holds no conversation text
The model spike SHALL record only item IDs, model, backend, endpoint, timings, token counts and scores, never prompt or response text, and SHALL use synthetic data only.

#### Scenario: Results file
- **WHEN** the spike writes its results CSV
- **THEN** no column contains prompt or response text

### Requirement: Model changes follow the lifecycle runbook
A tier's model SHALL change only through a new ADR revision, a passing eval run, and a config change deployed to staging before prod, never by editing code; a model whose retirement date has passed SHALL be treated as retired even if still listed as GA.

#### Scenario: Retirement date passed
- **WHEN** a model's documented retirement date is in the past
- **THEN** it is not used for any tier and is removed from `GEMINI_ALLOWED_MODELS`
