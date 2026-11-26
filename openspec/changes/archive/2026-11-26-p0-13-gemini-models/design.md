# Design: P0-13 Gemini models per routing tier

## Context
See proposal.md (Why). Facts that shape the approach:
- **DECISIONS #65–#69** already set the selection rules, proposed tiers, data settings, config keys and the Live API note. This task checks them against today's pages and measures what it can.
- **No Vertex AI now:**
  - no project has billing (#293);
  - trial credit excludes Vertex;
  - local-first (#302) forbids cloud resources.
- **User decision 2026-11-26:** keep **two setups**: Vertex AI (production, PHI) and the Gemini Developer API (local, synthetic only).
- **P0-06 control:** the Developer API (`generativelanguage.googleapis.com`) is "never allowed" in our Google Cloud projects. An AI Studio key is created in Google AI Studio and may live in a separate AI Studio project, so it doesn't touch the `dai-rcpt-*` projects. Recorded as an exception.
- The P0-04 flows define the slots and intents (`docs/flows/overview.md`). P0-03 defines the emergency tiers and the no-medical-advice rule.

## Goals / Non-Goals
**Goals:**
- a defensible model choice per tier from today's documentation;
- a reusable synthetic spike set and script;
- real (indicative) measurements on the Developer API;
- the config and startup-check contract for P2-03;
- a lifecycle runbook.

**Non-Goals:**
- the provider code (P2-03), routing (P2-03, which absorbed P2-06), the production extraction schema (P2-05), the eval harness (P5-01) and the voice architecture (P3-01);
- creating any Google Cloud resource.

## Decisions
1. **Two backends behind one config key.** `GEMINI_BACKEND=vertex|developer`. The `google-genai` SDK supports both: `vertexai=True` with project and location, or an `api_key`.
   - **Startup checks (spec for P2-03):**
     - `developer` requires `APP_ENV=local`;
     - `vertex` requires `VERTEX_LOCATION` of `us` or `us-*`;
     - model IDs must be in `GEMINI_ALLOWED_MODELS` and contain no `preview`, `exp` or `latest`;
     - no grounding tools.
   - Alternative rejected: Developer API only. It has no BAA and no US-only processing statement, so it can't carry PHI.
2. **Same model IDs on both backends where they exist.** Apply checks the Developer API's model list. If a tier's Vertex model isn't offered there, the spike uses the nearest GA equivalent for that tier and labels it.
   - The ADR choice is always stated for **Vertex**.
   - Developer API numbers are indicative for quality and only roughly for latency: a different serving path, from a laptop, not from `us-central1`.
3. **Re-check the pages on the day.** Sources:
   - model versions;
   - models;
   - locations and data residency;
   - data governance;
   - Vertex pricing;
   - Developer API models, pricing and the free-tier data-use terms;
   - HIPAA covered products.

   Recorded as a new sources block (G-rows). A retired-but-listed model is treated as retired (#65).
4. **Spike set from the P0-04 slots.** YAML files:
   - `extraction.yaml`: 30 items with an utterance, prior-context hint and expected JSON. Covers intents book, reschedule, cancel, check, FAQ, emergency, callback; slots name, DOB in spoken forms, phone, preferred day/time, reason; corrections, two intents, spelled names.
   - `replies.yaml`: 20 situations with rubric flags, including demands for medical advice.
   - `complex.yaml`: 10 multi-part or complaint conversations.

   All names fictional, phones `555-01xx`. The spike's JSON schema is a small subset of the P0-04 slots; P2-05 owns the real one.
5. **Spike script.**
   - **Calls:** streaming for every call, to measure time to first token. `response_schema` (JSON mode) for extraction.
   - **Scoring:**
     - extraction: automatic exact match after normalization (lower-case, digits-only phone, ISO date);
     - replies and complex: automatic proxy checks (length limit; no advice keywords; must offer a callback when asked for medical advice), plus a column for the two-person human rubric pass, filled in by hand.
   - **Output:** CSV and a summary markdown, no text.
   - **Pacing:** requests are paced to stay under free-tier rate limits (Verify the limits); a 429 is recorded and retried after a delay.
   - **Offline tests:** a `fake` backend lets them run in CI.
6. **Live run size.** About 600 small requests at most: 60 items × 3 runs × the candidates available. Asked before running. The API key is entered by the user in `.env` only.
7. **ADR stays Proposed.** It records the per-tier choice (Vertex IDs, `us` endpoint, release and retirement dates, HIPAA entry), the Developer API measurements, rejected options, consequences and review triggers. Acceptance needs:
   - the Vertex run;
   - `cacheConfig` set in the three projects;
   - the advisor's answers on in-memory caching and abuse monitoring.
8. **`cacheConfig` pending.** The exact PATCH/GET commands and host are documented in the ADR and runbook (Verify the `us` multi-region host). Not run: Vertex isn't enabled anywhere.
9. **Vendor row.** Add `google-ai-studio` (Gemini Developer API) to `vendors.yaml` with `phi: no`, environment `local`, and a no-PHI control. The checker enforces that it has no BAA claim. Re-render the matrix.

## Risks / Trade-offs
- **Developer API latency ≠ Vertex latency.** The ADR labels the numbers; P3-14 re-measures on Vertex.
- **Free-tier data use:** Google may use free-tier prompts to improve its products. Synthetic data only; recorded in the vendor row.
- **Someone later points the Developer API at real data:** the startup check (`APP_ENV=local` only), the vendor row `phi: no`, and the DECISIONS exception guard against it.
- **Model pages change monthly:** the review triggers and the monthly check in the runbook cover this.
- **The `pro` candidate is uncertain:** the fallback to flash with a higher thinking budget is already in #66.

## Migration Plan
Not applicable.

## Open Questions
- Whether `gemini-4-argon` is Pro-class and available on `us` (answered from the pages in apply where possible).
- The advisor on in-memory caching and abuse monitoring.
- The sponsor on the pilot start date (for the 6-month retirement rule): today unknown, so assume within 2027-Q1 and record it.
