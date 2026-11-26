# Proposal: P0-13 Choose GA Gemini models per routing tier (issue #14)

## Why

The plan routes each conversation turn to one of three Gemini tiers (plan §4.3): `lite` for greetings and acknowledgements, `flash` for intent and slot extraction in JSON, and `pro` for ambiguous or complaint conversations. Picking a preview or short-lived model, the global endpoint, or a feature that stores prompts would send PHI outside what the BAA and the US-only rules cover (CLAUDE.md rules 5–6, DECISIONS #65–#68). Model choice also drives voice latency (≤ 1.5 s p50) and extraction accuracy, so it must be measured, not guessed.

Our situation on 2026-11-26:
- the Google Cloud projects have no billing (DECISIONS #293);
- the $300 trial credit can't pay for Vertex AI;
- the senior's local-first rule forbids cloud resources now (DECISIONS #302).

**User decision (2026-11-26): keep two setups.**
- **Vertex AI** stays the only path for production and any PHI.
- The **Gemini Developer API** (Google AI Studio API key) may be used **now, locally, with synthetic data only**, to run the spike and to develop.

## What Changes

- **Facts re-checked on the day:** model versions and lifecycle, models, locations and data residency, data governance (caching, logging, grounding, abuse monitoring), Vertex AI and Developer API pricing, the Developer API's model list and data-use terms, and the HIPAA covered-products list. Each fact is recorded as a source row.
- **Selection** per tier, using DECISIONS #65 rules applied to today's pages, with fallbacks.
- **Two backends, one config:**
  - `GEMINI_BACKEND=vertex|developer`.
  - Vertex settings: `VERTEX_PROJECT` and `VERTEX_LOCATION` (`us` or `us-*` only).
  - Developer settings: `GEMINI_API_KEY`, in the git-ignored `.env` only.
  - Models: `GEMINI_MODEL_LITE/FLASH/PRO` and `GEMINI_ALLOWED_MODELS`.
  - Startup-check spec for P2-03. **`developer` is refused unless `APP_ENV=local`**, so it can never run in dev, staging or prod in the cloud, or with PHI.
- **Spike set** `evals/spike/p0-13/`: 30 extraction, 20 reply and 10 complex synthetic items, built on the P0-04 slot list.
- **Spike script** `run_spike.py`, using the `google-genai` SDK. Backends: `vertex`, `developer` and an offline `fake`. It measures time to first token and total time, checks JSON validity and field accuracy, and records token counts. The CSV holds IDs, timings and scores only, never prompt or response text. Offline tests run against the fake backend.
- **Live run on the Developer API (human-assisted):** the user puts an API key in `.env`, and the run is asked for first. Its latencies are labelled "Developer API, not Vertex": they are indicative only. The Vertex run stays **pending** until billing or hosting is decided.
- **ADR** `docs/adr/0001-gemini-models.md` with status **Proposed**. It becomes Accepted only after the Vertex run and the advisor's answers.
- **Lifecycle runbook** `docs/runbooks/gemini-model-lifecycle.md`.
- **Data settings** (`cacheConfig` EPHEMERAL, request-response logging off, no grounding): the commands and checks are documented, and recorded as **pending**, because no project has Vertex enabled.
- **Records:**
  - DECISIONS rows, including the Developer API exception to rules 5–6;
  - a `vendors.yaml` row for the Developer API (no PHI, local, synthetic only), re-rendered;
  - `.env.example` keys;
  - notes for P2-03 (incl. routing, was P2-06), P2-05, P3-01, P3-14, P5-01, P0-10, P0-11 and P0-14;
  - READMEs and `docs/PROJECT_MAP.md`.

## Capabilities

### New Capabilities
- `gemini-models`: which Gemini models and endpoints the system may use per tier, the two backends and when each is allowed, the startup checks, the forbidden features and data settings, and how models are changed over their lifecycle.

### Modified Capabilities
None.

## Impact

- **New:**
  - `docs/adr/0001-gemini-models.md`
  - `docs/runbooks/gemini-model-lifecycle.md`
  - `evals/spike/p0-13/`: sets, script, tests, README, results
- **Updated:**
  - `.env.example`
  - `dental-ai-tasks/DECISIONS.md`
  - `docs/compliance/sources/README.md`
  - `docs/compliance/vendors.yaml` and `vendor-matrix.md`
  - `docs/compliance/README.md`
  - `docs/phase-0-discovery-compliance/README.md`
  - `docs/PROJECT_MAP.md`
- **Network:**
  - reading Google's public docs pages;
  - installing `google-genai` into the scratchpad virtualenv;
  - a live Developer API run of about 600 small requests on the free tier, asked first.

  No Google Cloud resources or billing.
- **Acceptance criteria partly met:**
  - Vertex spike, `cacheConfig` in the three projects and ADR acceptance stay pending;
  - retirement reminders are written in the runbook (no shared calendar exists).
