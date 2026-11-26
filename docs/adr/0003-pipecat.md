# ADR 0003: Pipecat for the voice pipeline only

| | |
|---|---|
| Status | **Proposed** (2026-11-26). Decided in P3-01 after the latency prototype |
| Date | 2026-11-26 |
| Task | P0-14 (issue #15) · DECISIONS #318; final: P3-01 |
| Deciders | Riley Tech (tech lead); confirmed by the P3-01 owner |

## Context
Voice needs audio transport, voice activity detection (Silero VAD on the server), streaming STT and TTS, sentence chunking and barge-in. Pipecat is an open-source (BSD-2) Python framework for real-time voice agents. Our conversation logic must stay deterministic (state machine, tool gateway, router) and Gemini must be reached only through Vertex AI `us` (ADR 0001).

Pipecat docs read on 2026-11-26 (sources A17–A20):
- `GoogleVertexLLMService` exists (Vertex AI auth), but its `location` **defaults to `global`**, and the page says only `global` serves Gemini 3. Google's own model pages list the `us` multi-region (G2–G4), and `global` is forbidden for us.
- `GoogleLLMService`, `GeminiSTTService` and the GenAI backend of `GeminiTTSService` use an AI Studio **API key**.
- `GoogleSTTService` and `GoogleTTSService` use service-account credentials or ADC and take a `location` for regional endpoints.

## Options considered
| Option | For | Against |
|---|---|---|
| **Pipecat for transport, VAD, STT/TTS streaming and barge-in; our own LLM path** | Saves building audio plumbing; keeps logic ours | A dependency to vet and pin; its LLM services must never be used |
| Pipecat end to end, including its LLM service | Least code | Logic moves into a framework; LLM location and auth not under our control (A17, A18) |
| No Pipecat: our own pipeline | Full control | More code for VAD, chunking and barge-in |

## Decision (Proposed)
Use Pipecat **only** for the voice pipeline. The conversation logic stays in `backend/app/orchestrator/`, and the LLM call goes through our P2-03 Vertex AI provider (a custom Pipecat processor or a call-out). Conditions:
- **Never** `GoogleLLMService`, `GeminiSTTService` or `GeminiTTSService` on the GenAI backend; never set `GOOGLE_API_KEY` in any cloud environment.
- **Not** `GoogleVertexLLMService` either: its `global` default and claims conflict with ADR 0001; our provider owns location, models and checks.
- `GoogleSTTService` / `GoogleTTSService` only with service-account credentials (ADC) and an explicit US `location`; P3-01 confirms they can do that with our settings and that data logging stays off. If not, use our own STT/TTS integrations (P3-03) and keep Pipecat for transport and VAD only, or drop it.
- Pipecat added as a pinned dependency after a supply-chain check (P0-10 PR vendor check: no PHI to any new service).

## Consequences
- P3-01 builds the latency prototype with this split and records the result here.
- A test (P2-03 / P3-01) fails if `GOOGLE_API_KEY` is set outside `APP_ENV=local`.
- The flow table (R-E) already forbids the API-key paths.

## Review triggers
- P3-01 prototype result (accept, change, or drop Pipecat).
- A Pipecat release that changes its Google services' auth or location behaviour.
- ADR 0004 changes to WebRTC.
