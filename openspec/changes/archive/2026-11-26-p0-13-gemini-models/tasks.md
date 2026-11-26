# Tasks: P0-13 Gemini models per routing tier (issue #14)

## 1. Facts (read-only)

- [x] 1.1 Fetch and read: Vertex model versions and lifecycle, models, locations, data residency, data governance (caching, logging, grounding, abuse monitoring), Vertex pricing, the Developer API model list, pricing and free-tier data-use terms, and the HIPAA covered-products list. Record G-rows in `docs/compliance/sources/README.md`. Decide the candidates per tier under DECISIONS #65, and note which model IDs exist on each backend. Verify: every tier has a primary and a fallback with a dated source.

## 2. Spike set and script

- [x] 2.1 Write `evals/spike/p0-13/extraction.yaml` (30), `replies.yaml` (20), `complex.yaml` (10) and `schema.json` (spike subset of the P0-04 slots). Synthetic only; phones `555-01xx`. Verify: counts match, every intent and the hard cases are covered, the YAML loads.
- [x] 2.2 Write `evals/spike/p0-13/run_spike.py` with three backends:
  - `vertex`;
  - `developer` (refused unless `APP_ENV=local`);
  - `fake`.

  It streams, measures TTFT and total time, scores, and writes a CSV and a summary with no text. Write `test_run_spike.py` against `fake` (scoring, no text in output, backend guard, global location refused). Verify: tests pass offline.
- [x] 2.3 Add the `GEMINI_*`, `VERTEX_*` and `APP_ENV` keys to `.env.example` (no values). Write `evals/spike/p0-13/README.md` (how to run, what's measured, Vertex vs Developer caveat). Verify: `.env` stays ignored; no key value in the repo.

## 3. Live run and documents

- [ ] 3.1 (human-assisted) The user creates a Google AI Studio API key and puts it in `.env`. **Ask before** installing `google-genai` into the scratchpad virtualenv and running the spike on `developer`. Commit `results/` (CSV and summary). If the user defers, record it. Verify: results have no text; no key in the output or repo. **Deferred by the user (2026-11-26):** key to be added later; steps in ADR 0001 §8. Left unticked.
- [x] 3.2 Write `docs/adr/0001-gemini-models.md` (status **Proposed**). Contents:
  - context and rules;
  - candidates with dates and results;
  - the per-tier Vertex choice and endpoint;
  - the two-backend config and startup checks;
  - the data settings and the `cacheConfig` commands (pending);
  - rejected options;
  - consequences;
  - review triggers;
  - what is needed for Accepted.

  Verify: every acceptance-criteria item is addressed or marked pending.
- [x] 3.3 Write `docs/runbooks/gemini-model-lifecycle.md`. Contents:
  - retirement reminders, 90 days before each date (listed);
  - the monthly check;
  - the model-change procedure;
  - the retired-but-listed rule;
  - the Developer API rules.

  Verify: dates match the ADR.

## 4. Records

- [x] 4.1 Append DECISIONS rows from #315:
  - the per-tier choice (confirms or supersedes #66);
  - the two-backend exception to CLAUDE.md rules 5–6 for local synthetic use;
  - the deviations: Vertex run, `cacheConfig` and ADR acceptance pending.

  Add the `google-ai-studio` vendor row and re-render the matrix. Verify: `check_vendors.py` and `check_risk_register.py` pass.
- [x] 4.2 Update:
  - `docs/compliance/README.md`: notes for P2-03 (incl. routing, was P2-06), P2-05, P3-01, P3-14, P5-01, P0-10, P0-11, P0-14;
  - the Phase 0 README (#14 status);
  - `docs/PROJECT_MAP.md`.

  Run the public-repo scan, a key scan and the link check. Cite survivor task IDs only. Verify: all clean.

## Workflow follow-up

- After the user has reviewed the work and given the go-ahead:
  - archive the change (sync the `gemini-models` spec);
  - commit with a one-line descriptive message and push `feature/phase-0-discovery-compliance`;
  - comment the hand-off on issue #15 (P0-14);
  - close issue #14 with a comment listing the files.

  Never close the phase parent issue #17. Do none of these before the user says so.
