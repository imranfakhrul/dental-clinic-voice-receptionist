---
id: P3-01
title: "Latency spike: STT -> Gemini Flash -> TTS prototype"
milestone: P3
epic: E3.1
size: M
labels: area:voice, type:spike
depends_on: P0-13, P0-14, P1-02, P1-07, P2-03
status: approved
---

# P3-01: Latency spike: STT -> Gemini Flash -> TTS prototype

## 1. Summary
Build a throw-away voice prototype — browser mic → WebSocket → Google Speech-to-Text (streaming) → endpointing → Gemini Flash on Vertex AI (through our P2-03 provider) → sentence chunker → Google Text-to-Speech (streaming) → browser playback — and measure every stage on real infrastructure in dev.

The spike produces three decisions:
- **latency report** with p50 / p95 per stage and voice-to-voice, over at least 200 turns;
- **ADR 0003 Pipecat** moved from Proposed to Accepted or Rejected, using pass criteria fixed in advance;
- **ADR 0007 Voice** with the allow-list of standard female en-US Google TTS voices and the default voice (user decision, DECISIONS #175).

It also chooses the streaming STT model and lists the tuning actions needed if a target is missed. The prototype code is not production code; P3-02 onward build the real pipeline using its findings.

## 2. Why this matters
The pilot target is **voice-to-voice ≤ 1.5 s p50 / ≤ 2.5 s p95** (plan §11). Plan §8 Phase 3 says: "Build an early latency prototype (STT → Gemini Flash → TTS) to validate the targets before building the full voice UI." If the cascade can't meet the targets, or Pipecat adds too much overhead or can't run with our Vertex AI and BAA rules, we must know before P3-02..P3-14 are built on top of it. The voice choice is fixed product-wide (DECISIONS #175), so it must be measured and agreed once, here.

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P3, Voice Pipeline & Avatar**.
- **Cascaded voice pipeline (plan §4.4):** speech is turned into text (STT), the text goes to the LLM, and the reply text is turned into speech (TTS). Each stage streams so the next can start early.
- **Endpointing:** deciding that the patient has finished speaking. Too early cuts people off; too late adds delay. Plan target ≤ 300–500 ms after the end of speech.
- **Silero VAD:** a small voice-activity-detection model that tells speech from silence in 16 kHz audio frames.
- **Pipecat:** an open-source Python framework for real-time voice agents (transports, VAD, STT/TTS services, interruption handling). <https://docs.pipecat.ai>. DECISIONS #73: we may use it only for the voice pipeline, never its Google LLM service or any API-key (AI Studio) path; LLM calls go through our P2-03 Vertex AI provider.
- **Google Cloud Speech-to-Text V2 streaming:** `StreamingRecognize` over gRPC with interim (partial) and final results. <https://docs.cloud.google.com/speech-to-text/v2/docs/streaming-recognize>.
- **Google Cloud Text-to-Speech streaming:** `StreamingSynthesize` returns audio while text is still arriving (supported voice families only, **Verify**). <https://docs.cloud.google.com/text-to-speech/docs/create-audio-text-streaming>.
- **What already exists:**
  - **P0-13** (approved): `GEMINI_MODEL_FLASH` (`gemini-3.8-flash` proposed), US endpoint rules, GA only; Live API noted as an alternative to decide here (DECISIONS #69).
  - **P0-14** (approved): ADR 0003 Pipecat (Proposed), ADR 0004 WebSocket audio transport (16 kHz PCM, 20 ms frames), Cloud Run `api` with 3600 s timeout.
  - **P2-03** (approved): `LlmProvider.stream()` with `vertexai=True`, TTFT deadlines, `cancel` ≤ 200 ms.
  - **P1-07** (approved): `stage_timer()`, `Stage` enum (`STT_FIRST_PARTIAL`, `STT_FINAL`, `LLM_FIRST_TOKEN`, `TTS_FIRST_AUDIO`, `VOICE_TO_VOICE`, …), Cloud Trace.
  - **P0-05 / P0-06** (approved): Speech-to-Text is BAA-listed with a footnote — never opt in to data logging; US-only locations.
  - **DECISIONS #175** (user): the voice is always a standard female American English voice; `TTS_LANGUAGE_CODE=en-US`, `TTS_VOICE_NAME` must be in `TTS_ALLOWED_VOICES`; chosen here.

## 4. Scope
**In scope**
- Prototype in `spikes/p3-01-voice-latency/` (excluded from production images): a minimal browser page, a FastAPI WebSocket server, two pipeline variants (Pipecat and custom baseline).
- Recording 30 synthetic test utterances and a noisy copy of each.
- Measurement harness, 200+ turns per variant, report.
- STT model comparison (two streaming models), TTS voice shortlist and listening test.
- ADR 0003 final status, ADR 0007 Voice, tuning backlog for P3-06 / P3-14.

**Out of scope** (and which task covers it)
- Production audio transport, reconnect, VAD + semantic turn detection → P3-02
- Production STT with phrase hints and TTS with SSML → P3-03
- Barge-in, filler phrases, speculative LLM calls → P3-06
- Read-back and spelling mode → P3-09
- Avatar and live transcript → P3-11
- Dashboards and tuning to target → P3-14
- Gemini Live API (speech-to-speech) → not evaluated (DECISIONS #223)

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P2-03 (approved) | `LlmProvider.stream()` on Vertex AI | Import the module; if not merged, a 30-line `google-genai` call with `vertexai=True` behind the same interface |
| P1-02 (approved) | Dev project, Cloud Run, service accounts | Deploy the spike server as a separate Cloud Run service `voice-spike` in dev only |
| P1-07 (approved) | `stage_timer`, tracing | Local timing with `time.perf_counter_ns()` written to the same JSONL format |
| P0-06 (approved) | APIs enabled in dev: `speech.googleapis.com`, `texttospeech.googleapis.com` | Request via the P0-06 exception process if blocked |

## 6. Interface contract

### Prototype layout
```
spikes/p3-01-voice-latency/
├── client/index.html, client/main.js     # getUserMedia (echoCancellation, noiseSuppression, autoGainControl on),
│                                         # AudioWorklet → 16 kHz mono PCM16, 20 ms frames; plays PCM from the server;
│                                         # "replay mode" streams a WAV file instead of the mic (for repeatable runs)
├── server/app.py                         # FastAPI, WS /spike/ws?variant=pipecat|custom
├── server/pipeline_pipecat.py            # Pipecat: WebSocket transport, SileroVADAnalyzer, GoogleSTTService,
│                                         #   VertexLlmProcessor (custom processor calling P2-03), GoogleTTSService
├── server/pipeline_custom.py             # asyncio: Silero (onnx) + STT V2 gRPC + P2-03 + TTS StreamingSynthesize
├── server/timing.py                      # event marks → JSONL
├── audio/utterances/*.wav, audio/noisy/*.wav, audio/manifest.yaml
├── run_bench.py                          # drives N turns in replay mode, writes results/*.jsonl
└── report.py                             # p50/p95 tables and charts → docs/spikes/p3-01-report.md
```
The spike is never deployed outside dev, never receives PHI and is deleted (code kept in git history) after the ADRs are accepted.

### Fixed prompt for the LLM step
To measure latency, not conversation quality, the LLM gets a short fixed system prompt and the utterance text, `max_output_tokens=96`, thinking budget 0 (P2-03 flash defaults), tier `flash`. One run also uses tier `lite` for comparison.

### Timing marks (per turn, `results/<variant>.jsonl`)
```json
{"run_id":"r1","variant":"pipecat","utt":"u07","noise":false,"stt_model":"chirp_3",
 "t_speech_end": 0, "t_vad_end": 412, "t_stt_first_partial": -1650, "t_stt_final": 468,
 "t_llm_request": 470, "t_llm_first_token": 742, "t_first_sentence": 905,
 "t_tts_request": 906, "t_tts_first_audio_server": 1088, "t_first_audio_client": 1131,
 "barge_in_stop_ms": null}
```
- All times in ms relative to `t_speech_end`, the true end of speech taken from the WAV manifest (replay mode) so the reference is exact.
- **Voice-to-voice** = `t_first_audio_client` (the client reports when the first audio buffer starts playing; clocks aligned by an NTP-style ping exchange at connect, error recorded).
- **Barge-in stop** (20 turns): the client replays speech 600 ms into the assistant's audio; measure until the last assistant audio frame is played.
- Server marks also emit `stage_timer` metrics with two additive `Stage` values: `ENDPOINT_DETECTED`, `BARGE_IN_STOP` (DECISIONS #224).

### Test audio (DECISIONS #224)
- **30 utterances**, recorded by at least 4 team members with different US English accents (at least one non-native speaker), 16 kHz mono WAV, read from a script:
  - 10 short (≤ 2 s): "Yes", "Tuesday at three", "The first one", …
  - 10 medium (2–5 s): "I'd like to book a cleaning next week", …
  - 6 data-heavy: names spelled, phone `555-0142`, DOB "March fourth, nineteen eighty-two";
  - 4 long (6–10 s) with pauses mid-sentence (to measure early cut-offs).
- **Noisy copies:** the same 30 mixed with café noise at 10 dB SNR.
- All content synthetic (invented names, `555` numbers). The recordings are team members' voices: stored in the repo under `spikes/…/audio/` with each speaker's written consent; deleted with the spike.

### Variants and runs
| Run | Variant | STT model | Turns | Where |
|---|---|---|---|---|
| A | Pipecat | model 1 | 120 (30 × clean/noisy × 2) | Cloud Run dev (`us-central1`) + laptop browser |
| B | Custom baseline | model 1 | 120 | same |
| C | Best of A/B | model 2 | 60 | same |
| D | Best of A/B | best model | 30, LLM tier `lite` | same |
| E | Best of A/B | best model | 20 barge-in turns | same |
Total ≥ 350 turns; every number also re-run server-side only (Cloud Run → Cloud Run client) to separate network from processing.

**STT models to compare** (**Verify** availability for streaming in the US multi-region or `us-central1`, and that data logging is off by default): `chirp_3` and `latest_short` (or the current recommended short-utterance model). Measure first-partial, final latency and word accuracy on the data-heavy utterances (manual check against the script).

### Pass criteria (fixed before running; DECISIONS #222)
**Pipeline targets (plan §4.4), on clean audio, laptop browser in the US:**
| Stage | Target |
|---|---|
| End of speech → endpoint | ≤ 500 ms p50 |
| LLM TTFT (flash) | ≤ 300 ms p50 (P2-03 deadlines are separate, larger guards) |
| TTS first audio | ≤ 250 ms p50 |
| Voice-to-voice | ≤ 1.5 s p50, ≤ 2.5 s p95 |
| Barge-in stop | ≤ 200 ms p50 |

**Pipecat is Accepted only if all hold:**
1. Overhead vs the custom baseline ≤ 50 ms p50 on voice-to-voice (same STT model, same voice).
2. `GoogleSTTService` and `GoogleTTSService` run with the Cloud Run service account (no API key) against a US location, with data logging not enabled (code and config checked).
3. The LLM step is our `VertexLlmProcessor` calling P2-03; nothing in the pipeline imports Pipecat's Google LLM, Gemini STT or GenAI TTS classes (a grep check in CI for the spike).
4. Interruption handling can call our `cancel` and stop TTS within the barge-in target.
5. License and maintenance acceptable (BSD-2; release cadence checked).
Otherwise the custom pipeline is chosen and ADR 0003 is Rejected with the measured reasons.

If the **voice-to-voice target is missed** by both variants, the report lists the gap per stage and the tuning backlog (e.g. speculative LLM on stable partials, shorter endpoint silence, warm gRPC channels, first-sentence-only TTS start, region change); P3-14 owns closing it. The cascade remains the architecture unless the report shows the gap can't be closed, which needs a new decision.

### Voice allow-list (ADR 0007, user decision #175)
1. List en-US voices from `voices.list` (languageCode `en-US`), filter `ssmlGender = FEMALE` and GA status (**Verify** each voice's GA/preview status in the TTS docs; preview voices are not allowed with PHI).
2. Shortlist **3** voices from at least two families (e.g. Chirp 3 HD and Neural2; **Verify** which families support streaming synthesis).
3. Measure TTS first audio for each (30 replies); drop any voice > 250 ms p50.
4. **Listening test:** the product owner and 3–5 team members rate the remaining voices on clarity and warmth with 10 standard replies (including a phone number and a date read-back), blind order.
5. ADR 0007 records `TTS_ALLOWED_VOICES` (all voices that passed 3 and scored acceptable in 4) and `TTS_VOICE_NAME` default (the best-rated; ties → the faster). `TTS_LANGUAGE_CODE=en-US`; startup rejects anything else (P3-03 implements).
6. P1-19 `voice.tts_voice` (null = default) must be null or a member of `TTS_ALLOWED_VOICES`; the load check is added by P3-03.

### Deliverables
| Path | Content |
|---|---|
| `docs/spikes/p3-01-report.md` | Method, environment, p50/p95 per stage per run, network vs processing split, STT accuracy notes, charts, gaps, tuning backlog |
| `docs/adr/0003-pipecat.md` | Status Accepted or Rejected, with the five criteria and measurements |
| `docs/adr/0007-voice.md` | Allow-list, default voice, test results, review trigger (voice retired or a new GA female voice) |
| `docs/adr/0001-gemini-models.md` | Note added: Live API not evaluated, reason (plan §4.4 cascade, cost, control) |

## 7. Implementation guide
1. **Setup:** dev Cloud Run service `voice-spike` with the `api` service account's Speech/TTS/Vertex roles; enable the two Speech APIs in dev (P0-06 list).
2. **Record audio** with the script; write `manifest.yaml` with exact speech-end offsets (trim with a waveform editor; offsets checked by a second person).
3. **Custom baseline first** (it defines the reference): Silero endpointing with 300 ms trailing silence; STT V2 streaming with interim results; first final or VAD end (whichever first) triggers the LLM; sentence chunker from P2-04 rules; TTS streaming per sentence.
4. **Pipecat variant** with the same models, silence setting and chunker; the `VertexLlmProcessor` wraps P2-03.
5. **Bench runs** A–E in replay mode, laptop on a normal US broadband connection plus server-only runs.
6. **Voice shortlist and listening test**.
7. **Report and ADRs**; review with the tech lead and product owner; set DECISIONS rows.
8. **Notify** P3-02 (transport and VAD settings), P3-03 (STT model, voice allow-list), P3-06 (barge-in numbers), P3-14 (baseline numbers and backlog).

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| A chosen STT model isn't available for streaming in a US location | Drop it; pick the next recommended model; record in the report |
| Streaming TTS isn't supported for a shortlisted voice | Measure it with non-streaming per-sentence synthesis and mark it; it may still pass if first audio ≤ 250 ms |
| Pipecat's Google services need an API key or a global endpoint | Criterion 2 fails → Pipecat Rejected |
| Silero cuts off long utterances with pauses | Recorded as early cut-offs; P3-02 adds semantic turn detection |
| Clock skew between client and server | Ping exchange at connect; turns with measured error > 20 ms are excluded and counted |
| Gemini 429 or slow responses during runs | Retried turns marked; reported separately; not counted in p50/p95 |
| Laptop network jitter | Server-only runs show processing time without the network |
| No female en-US GA voice passes 250 ms | Report it; the product owner chooses between the fastest passing-quality voice and a P3-14 tuning task; #175 (female en-US) is never relaxed |

## 9. Security, HIPAA and PHI
- **No PHI:** all utterances are scripted synthetic content; no real patients, no Open Dental access.
- **Team recordings:** voices of consenting team members, kept only in the spike folder, deleted with it.
- **Vendors:** Speech-to-Text, Text-to-Speech and Vertex AI are under the Google Cloud BAA; data logging is not enabled (P0-06); service-account auth only; no AI Studio keys.
- **Isolation:** dev project only; the spike service is not behind the public load balancer (IAP or `run.app` with authentication).

## 10. Testing
Spikes have no unit-test suite. Checks:
```bash
cd spikes/p3-01-voice-latency
python run_bench.py --variant custom --runs A --target dev      # writes results/custom.jsonl
python run_bench.py --variant pipecat --runs A --target dev
python report.py --out ../../docs/spikes/p3-01-report.md
grep -rnE "GoogleLLMService|GeminiSTTService|GOOGLE_API_KEY" server/ && exit 1 || echo "no forbidden paths"
```
| # | Check | Expected |
|---|---|---|
| C1 | ≥ 200 measured turns per main variant | Present in results |
| C2 | p50 and p95 per stage and voice-to-voice | In the report for every run |
| C3 | Forbidden-path grep | No matches |
| C4 | Data logging | STT recognizer config shows logging not enabled; recorded in the report |
| C5 | Voice allow-list | Only en-US female GA voices; each with measured first audio |
| C6 | Second reviewer | Tech lead reviewed the method and numbers |

## 11. Acceptance criteria
- [ ] p50/p95 numbers recorded for every stage and for voice-to-voice, clean and noisy, network and server-only (C1, C2)
- [ ] ADR 0003: Pipecat Accepted or Rejected against the five fixed criteria
- [ ] ADR 0007: `TTS_ALLOWED_VOICES` and the default voice chosen by latency and a listening test; all are standard female en-US GA voices (DECISIONS #175)
- [ ] STT model chosen with latency and accuracy evidence
- [ ] Gaps to the targets and a tuning backlog handed to P3-06 / P3-14
- [ ] No PHI used; no API-key or AI Studio paths (C3, C4)

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI: not applicable (spike); bench results and grep check committed with the report
- [ ] PR reviewed by the tech lead and the product owner (ADRs)
- [ ] No PHI in logs (none used)
- [ ] Report and ADRs merged; DECISIONS updated with the outcomes
- [ ] P3-02, P3-03, P3-06 and P3-14 issues notified

## 13. Hand-off
| Consumer | What they can rely on |
|---|---|
| P3-02 Transport + VAD | Pipecat yes/no, frame size, Silero settings, measured endpoint latency and cut-off rate |
| P3-03 STT + TTS | STT model, voice allow-list and default, streaming support per voice |
| P3-06 Barge-in | Measured stop time and what dominated it |
| P3-14 Instrumentation + tuning | Baseline numbers, `Stage` additions, tuning backlog |
| P0-13 / ADR 0001 | Live API not evaluated, with the reason |

## 14. Open questions
| # | Question | Recommended answer | Owner |
|---|---|---|---|
| 1 | Should the spike also test WebRTC transport (ADR 0004)? | Only if WebSocket network time is > 150 ms p50 from the laptop; otherwise no. | Tech lead |
| 2 | Should the noisy set include phone-speaker audio? | No: the MVP is web-only; phone calls are post-MVP (plan §14). | Tech lead |
| 3 | Which region hosts the voice path in prod? | The region of the main `api` (P0-14); revisit only if the report shows a large regional difference. | Tech lead |

## 15. References
- Plan: §3.2, §4.4, §8 Phase 3, §11, §12
- DECISIONS: #69, #72, #73, #115, #161, #175, #222, #223, #224
- Related tasks: P0-05, P0-06, P0-13, P0-14, P1-02, P1-07, P2-03, P2-04, P3-02, P3-03, P3-06, P3-14
- Pipecat docs: <https://docs.pipecat.ai>
- Speech-to-Text V2 streaming: <https://docs.cloud.google.com/speech-to-text/v2/docs/streaming-recognize>
- Text-to-Speech streaming: <https://docs.cloud.google.com/text-to-speech/docs/create-audio-text-streaming>
