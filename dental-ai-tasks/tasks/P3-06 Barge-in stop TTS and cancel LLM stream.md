---
id: P3-06
title: Barge-in (pause, decide, stop TTS and cancel the LLM), filler phrases and warm connections, speculative extraction on stable partials
milestone: P3
epic: E3.1
size: L
labels: area:voice, area:ai, type:feature
depends_on: P3-02, P3-03, P2-01, P2-03, P2-04, P2-05, P2-20, P1-07
status: approved
---

# P3-06: Barge-in (pause, decide, stop TTS and cancel the LLM), filler phrases and warm connections, speculative extraction on stable partials

## 1. Summary
Make the voice conversation feel natural. This task absorbs **P3-07 (filler phrases + warm connections)** and **P3-08 (speculative LLM calls on stable partials)**.

| Part | What it does |
|---|---|
| Barge-in | When the patient speaks over the assistant, the browser **pauses** playback at once; within 700 ms the server decides: real words → **flush** audio, cancel TTS and the LLM stream; only "okay / uh-huh" or nothing → **resume** where it paused |
| Protected audio | Only the first sentence of the Tier 1 (911) script cannot be interrupted |
| Interrupted history | The turn history keeps only what was actually spoken, marked `interrupted` |
| Fillers | Audio-only phrases ("Let me check that for you.") if no reply audio 700 ms after the endpoint; a second one at 4 s; pre-synthesized, max 2 per turn |
| Warm connections | gRPC channels, Vertex AI keep-alive and filler audio ready before the first turn |
| Speculative extraction | At end of speech (before the endpoint fires) run P2-20 rules + P2-05 extraction on the latest partial; reuse the result if the final text matches; never tools, never saves; behind a flag |

Done means:
- barge-in stop ≤ 200 ms p50 (speech start → assistant audio paused);
- a filler plays whenever no reply audio has started 700 ms after the endpoint;
- the speculative gain is measured and recorded;
- no side-effect tool ever runs speculatively.

## 2. Why this matters
Plan §4.4 sets barge-in stop ≤ 200 ms and voice-to-voice ≤ 1.5 s p50, and lists fillers, warm connections and speculative LLM calls as the techniques to get there. Without barge-in the assistant talks over patients; with a naive barge-in every "uh-huh" or echo cuts the assistant off. Silence while Open Dental answers (1 request/s throttle, DECISIONS #63) sounds like a dropped call. The endpoint wait (300–1500 ms, DECISIONS #227) is idle time we can use for extraction.

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P3, Voice Pipeline & Avatar**.
- **Backchannel:** short listener sounds ("okay", "mm-hmm", "yeah", "right") that do not mean "stop talking".
- **Speculative execution:** starting work on a guess (the partial transcript) and throwing it away if the guess turns out wrong. Safe only for work without side effects.
- **What already exists:**
  - **P3-02** (approved): protocol v2 (`speech_start`, `playback_start`, `playback_flush`, `playback_ended{played_ms}`, `utterance_discarded`), `AudioPlayer.flush()` < 20 ms, client VAD, server Silero, endpoint rules, frames still sent during playback.
  - **P3-03** (approved): `SttPartial.stable`, `transcript` message, `TextToSpeech.speak()` / `cancel(reply_id)` (≤ 50 ms), warm STT gRPC channel, `SpeechNormalizer`.
  - **P2-03** (approved): `LlmStream.cancel()` ≤ 200 ms, `structured()` for extraction.
  - **P2-04** (approved): `ReplyGenerator.generate(..., cancel: asyncio.Event)`; no chunk after cancel.
  - **P2-05** (approved): `Extractor.extract(st, slots, turns, user_text, rule_emergency, ...) -> ExtractionResult` (structured call, no side effects).
  - **P2-01** (approved): `TurnProcessor.handle()` steps (lock, load, duplicates, emergency rules, extraction, handler, save); `conv:{sid}:turns` `{role, text, ts}`; `st.rev`.
  - **P2-20** (approved): rules detector on raw text before the LLM; Tier 1 script `tier1_911` from P0-03.
  - **P1-07** (approved): `Stage.BARGE_IN_STOP`, `stage_timer()`.

## 4. Scope
**In scope**
- Client local pause on speech during playback; `BargeInArbiter` on the server; protocol messages for pause/resume.
- Cancelling TTS, the reply generator and the LLM stream; recording what was spoken.
- Protected (non-interruptible) audio for the Tier 1 first sentence.
- Filler catalogue, pre-synthesis cache, trigger timing.
- Warm-up on `voice_start`.
- `SpeculativeExtractor` with reuse rules and the P2-01 hook; flag; hit-rate metrics.
- Tests and a measured report (barge-in stop, filler timing, speculative gain).

**Out of scope** (and which task covers it)
- Endpoint rules, transport → P3-02
- STT/TTS clients → P3-03
- Read-back → P3-09
- Avatar states during barge-in → P3-11 (uses the events defined here)
- Dashboards, final tuning of thresholds and the prod flag default → P3-14

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P3-02 / P3-03 (approved) | Player, VAD events, STT partials, TTS cancel | `FakeVoiceSession`, `FakeStt` (scripted partials with timestamps), `FakeTts` (sine tone per sentence) |
| P2-03 / P2-04 / P2-05 (approved) | Cancellable streams and extraction | `FakeLlmProvider` with configurable delays; real `Extractor` with the fake provider |
| P2-01 (approved) | `handle()` hook | Add the optional `prefetched` parameter (§6); unit-test with the in-memory state store |

## 6. Interface contract

### Protocol v2 additions (DECISIONS #234)
| Direction | `type` | Fields | Meaning |
|---|---|---|---|
| C→S | `playback_paused` | `reply_id`, `played_ms`, `utterance_id` | The client paused playback by itself because its VAD heard speech |
| S→C | `playback_pause` | `reply_id` | Server heard speech the client missed; pause now |
| S→C | `playback_resume` | `reply_id` | Not a barge-in; continue from where it paused |
| S→C | `playback_flush` | `reply_id` | (P3-02) Barge-in confirmed; drop buffered audio |
| S→C | `playback_start` | + `interruptible: bool` (default true) | Protected audio is sent as its own reply with `interruptible=false` |
| S→C | `utterance_discarded` | + reason `backchannel` | The overlapping speech was only a backchannel |

Client rule: on client VAD `speech_start` while an `interruptible` reply is playing → `AudioPlayer.pause()` immediately, send `playback_paused`. A paused reply that gets neither `resume` nor `flush` within 1500 ms is flushed by the client (safety net).

### Barge-in arbiter (`backend/app/voice/barge_in.py`)
```python
class BargeInDecision(StrEnum):
    BARGE_IN = "barge_in"        # flush + cancel
    RESUME = "resume"            # backchannel, echo or noise

class BargeInArbiter:
    WINDOW_MS = 700              # Proposed; env BARGE_IN_WINDOW_MS (P3-14, DECISIONS #249); fillers FILLER_FIRST_MS / FILLER_SECOND_MS
    SPEECH_ONLY_MS = 1200        # speech this long without a recognised word still counts as barge-in
    def __init__(self, backchannels: frozenset[str]): ...
    def on_pause(self, reply_id: int, utterance_id: int, now_ms: int) -> None: ...
    def on_partial(self, p: SttPartial, now_ms: int) -> BargeInDecision | None: ...
    def on_vad(self, is_speech: bool, now_ms: int) -> BargeInDecision | None: ...
    def on_tick(self, now_ms: int) -> BargeInDecision | None: ...   # window expiry
```
**Decision rules (first match wins), DECISIONS #234:**
| Situation within the window | Decision |
|---|---|
| A partial contains any word not in `backchannels` (after lowercasing, removing punctuation) | `BARGE_IN` at once |
| Server Silero hears continuous speech ≥ `SPEECH_ONLY_MS` | `BARGE_IN` |
| Window ends; partials empty or only backchannel words | `RESUME`; the utterance is discarded (`backchannel`) |
| Window ends; Silero heard no speech at all (echo or noise) | `RESUME`; discarded (`noise`) |

`backchannels` (`voice/backchannels.yaml`): okay, ok, mm-hmm, mhm, uh-huh, yeah, yep, yes, right, sure, alright, got it, um, uh, hmm. A "yes" spoken **over** a question is treated as a backchannel; the patient says it again after the question ends (the read-back/confirmation flows need an explicit answer anyway).

**On `BARGE_IN`:**
1. `playback_flush` to the client; `TextToSpeech.cancel(reply_id)`; set the reply's `cancel` event (P2-04 → P2-03 `cancel()`).
2. Record what was spoken (below).
3. The overlapping utterance continues as a normal utterance (P3-02 endpoint → `UserTurn`).
4. `stage_timer(Stage.BARGE_IN_STOP)` = client speech start → client pause (reported in `playback_paused` via `played_ms` timestamps); a second metric `barge_in_decision_ms` = pause → decision.

**Speech before playback starts:** if the patient starts a new utterance after the endpoint but before `playback_start` of the reply, the same window runs; `BARGE_IN` cancels reply generation (and any filler). State changes already saved by the earlier turn (e.g. a booking) stay saved; only the words are cancelled.

**Server-detected speech** (client VAD missed it): server Silero speech ≥ 200 ms during interruptible playback → `playback_pause`, then the same window.

### Protected audio (DECISIONS #235)
- The first sentence of P2-20's Tier 1 script (`tier1_911`) is sent as its own reply with `interruptible=false`: the client does not pause it and the server ignores overlapping speech until `playback_ended`. All later sentences, and every other reply (including `crisis` and confirmation replies), are interruptible.
- Text is never removed: every `reply_chunk` already sent stays in the chat, and confirmation cards stay visible (DECISIONS #174).

### Interrupted history (DECISIONS #235)
`conv:{sid}:turns` assistant entries gain `interrupted: bool` and store only the sentences whose audio had **started** playing (`played_ms` mapped to sentence boundaries; the TTS glue keeps per-sentence durations). P2-04 renders an interrupted turn in the context as `assistant (interrupted): <spoken part>` so the model does not assume the patient heard the rest.

### Fillers (`backend/app/voice/fillers.py`, `fillers.yaml`, DECISIONS #236)
```yaml
first:                       # rotated, never the same twice in a row
  - "Let me check that for you."
  - "One moment while I look that up."
  - "Sure, let me take a look."
  - "Okay, give me a second."
second:
  - "Still checking, one moment."
```
| Rule | Value |
|---|---|
| First filler | No `playback_start` for the turn 700 ms after the endpoint |
| Second filler | Still none at 4 s |
| Max per turn | 2 |
| Not played | In text-only turns; when the reply is a template already ready; during a Tier 1 / crisis reply |
| Shown in chat | No (audio only); the chat keeps the typing indicator |
| Real reply arrives during a filler | Filler finishes its phrase (≤ 1.5 s), then the reply plays; no overlap |
| Barge-in during a filler | Normal barge-in rules (fillers are interruptible) |

```python
class FillerCache:
    async def warm(self, voice: VoiceChoice) -> None: ...      # synthesizes all fillers once per (voice, speaking_rate); in-memory LRU, 20 entries
    def pick(self, kind: Literal["first", "second"], last: str | None) -> tuple[str, bytes]: ...
```
Fillers contain no PHI and may be cached freely.

### Warm connections (on app start and on `voice_start`)
| Item | How |
|---|---|
| STT gRPC channel | Created at app start (P3-03), keepalive |
| TTS gRPC channel | Created at app start; `FillerCache.warm()` on `voice_start` is the first real call |
| Vertex AI HTTP client | Shared client with HTTP/2 keep-alive (P2-03); no warm-up requests (cost) |
| Open Dental | P1-15 connection pool as is |

### Speculative extraction (`backend/app/voice/speculative.py`, DECISIONS #236)
```python
class SpeculativeExtractor:
    async def start(self, sid: str, utterance_id: int, partial_text: str) -> None: ...   # at Silero end-of-speech
    def take(self, utterance_id: int, final_text: str, rev: int) -> Prefetched | None: ...

class Prefetched(NamedTuple):
    text_norm: str
    rev: int                     # st.rev the extraction was based on
    rule_signal: EmergencySignal
    extraction: ExtractionResult
```
- **Trigger:** server Silero end-of-speech (the start of the endpoint silence wait), the latest partial is non-empty, flag `VOICE_SPECULATIVE_EXTRACT=true`, at most **1** per utterance. A new speech start cancels it.
- **Work done:** load state **read-only** (no lock), run P2-20 rules and P2-05 `extract()` on the partial. Nothing is saved, no tool, no handler, no reply.
- **Reuse:** `take()` returns the result only if `normalize(final) == text_norm` (lowercase, no punctuation, single spaces) **and** `st.rev` is unchanged. Otherwise it is discarded and `handle()` runs as usual.
- **P2-01 hook:** `TurnProcessor.handle(principal, turn, prefetched: Prefetched | None = None)`. Inside the lock, step 5 still runs the rules on the final text; if the rule signal differs from `prefetched.rule_signal` or `rev` changed, the prefetched extraction is ignored. Step 6 uses `prefetched.extraction` when valid.
- **Flag default:** `true` in dev and staging, `false` in prod until P3-14 records the gain and hit rate.

### Logs and metrics (no PHI)
| Item | Fields |
|---|---|
| `voice.barge_in` | `decision`, `trigger` (`client_vad` / `server_vad`), `decision_ms`, `played_ms`, `protected` |
| `voice.filler` | `kind`, `after_ms` |
| `voice.speculative` | `outcome` (`hit` / `miss_text` / `miss_rev` / `miss_rules` / `cancelled`), `saved_ms` |
| `stage_timer` | `BARGE_IN_STOP` |
| Counters | `dai.llm.speculative_calls` (cost), `dai.voice.barge_in` by decision |

## 7. Implementation guide
1. **Protocol additions** in `ws_protocol.py` / `protocol.ts`; `AudioPlayer.pause()` / `resume()`; client safety-net flush.
2. **Arbiter** with the rules table, fed by P3-02 VAD events and P3-03 partials; unit tests with timed scripts.
3. **Cancel path:** flush → TTS cancel → reply cancel event; spoken-sentence tracking in `speak.py`; `interrupted` turn record and P2-04 context rendering.
4. **Protected reply** for the Tier 1 first sentence (P2-20 script split by code, not by the model).
5. **Fillers:** YAML, cache, trigger timer per turn, ordering with the real reply.
6. **Speculative extractor** and the P2-01 `prefetched` hook; flag per environment.
7. **Measurement run** in dev with the P3-01 audio set: 30 barge-in turns, 20 backchannel turns, 20 slow-tool turns (fake Open Dental delay 1.5 s and 5 s), 100 speculative turns with the flag on and off. Report in `docs/voice/p3-06-report.md`.
8. **Docs** `docs/voice/barge-in.md`. Notify P3-11 (pause/resume/flush events for the avatar), P3-14 (metrics, flag decision), P2-20 owner (protected sentence).

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| Patient says "mm-hmm" while the assistant lists times | Pause ≤ 200 ms, resume within ~700 ms; utterance discarded (`backchannel`) |
| Patient says "wait, actually Thursday" | First partial "wait" → barge-in; reply flushed; the utterance becomes the next turn |
| Echo of the assistant's voice triggers client VAD | Usually Silero hears no speech or STT returns nothing → `RESUME`. Browser echo cancellation (P3-02) is the main defence; if echo leaks words, they would count as a barge-in, so P3-14 tracks the echo barge-in rate and adds a "partial matches the playing sentence" check if it exceeds 2% |
| Patient speaks during the 911 first sentence | Ignored until it ends; then normal handling (their utterance is still processed as a turn) |
| Patient talks while a booking tool runs | Tool and save finish (not cancelled); only the reply words are cancelled; the new turn waits for the lock (P2-01) |
| Barge-in during a filler | Filler flushed; reply generation cancelled; new turn |
| `playback_paused` arrives after the reply already ended | Ignored; utterance handled normally |
| Client never gets resume/flush (lost message) | Client flushes after 1500 ms |
| Speculative partial differs from final ("Tuesday" vs "Tuesday afternoon") | `miss_text`; normal extraction; one extra LLM call billed |
| Speculation still running when the endpoint fires | If the final text matches, `handle()` awaits the running extraction (it would have run anyway); if not, the speculation is cancelled and normal extraction starts |
| LLM unavailable during speculation | Treated as `miss`; normal path decides |
| Flag off | No speculative calls; behaviour identical to P3-02/P3-03 |

## 9. Security, HIPAA and PHI
- **PHI handled:** partial transcripts (may contain names, phone, DOB) go to the existing P2-05 extraction call (Vertex AI under the BAA, same masking as normal turns). Speculative results live in memory only and are dropped after the turn.
- **No side effects speculatively:** speculation never acquires the turn lock, never saves state, never calls the P2-08 tool gateway (unit test + static check that `speculative.py` imports neither the gateway nor the state store's write methods).
- **Interrupted turn records** follow P2-01 storage rules (encrypted, `recent_turns` limit).
- **Fillers** contain no PHI. Logs carry no transcript text.

## 10. Testing
```bash
cd backend && pytest tests/unit/voice/test_barge_in.py tests/unit/voice/test_fillers.py tests/unit/voice/test_speculative.py -q
cd frontend && pnpm test -- voice/player     # pause / resume / flush / safety net
python scripts/voice/measure_p306.py --audio spikes/p3-01-voice-latency/audio --target dev
```
| # | Case | Expected |
|---|---|---|
| T1 | Client pause on speech during playback | Paused ≤ 200 ms p50 from speech start (dev run) |
| T2 | Arbiter: real word | `BARGE_IN`; flush, TTS cancel and LLM cancel; no audio chunk after 50 ms |
| T3 | Arbiter: backchannel only / no speech | `RESUME`; audio continues from `played_ms`; utterance discarded |
| T4 | Long speech without words | `BARGE_IN` at 1200 ms |
| T5 | Protected Tier 1 first sentence | Not paused; later sentences interruptible |
| T6 | Interrupted history | Turn record holds only started sentences, `interrupted=true`; P2-04 context shows "(interrupted)" |
| T7 | Speech before playback starts | Reply generation cancelled; earlier saved state unchanged |
| T8 | Filler timing | First at 700 ms ±50, second at 4 s; max 2; not in chat; none for ready templates |
| T9 | Reply during filler | No overlap; reply starts after the filler phrase |
| T10 | Speculative hit | Prefetched extraction used; `saved_ms` recorded |
| T11 | Speculative miss (text, rev, rules) | Discarded; normal extraction |
| T12 | No side effects | Gateway and state writes never called from speculation (mock asserts + static import check) |
| T13 | Safety-net flush | Client flushes after 1500 ms without a decision |
| T14 | Measurement report | Barge-in stop p50/p95, backchannel resume rate, filler timing, speculative hit rate and median gain |

## 11. Acceptance criteria
- [ ] Barge-in stop ≤ 200 ms p50 in the dev measurement run (T1, T14)
- [ ] Real interruptions flush audio and cancel TTS and the LLM stream; backchannels resume playback (T2, T3)
- [ ] Only the Tier 1 first sentence is non-interruptible (T5)
- [ ] History records only what was spoken, marked interrupted (T6)
- [ ] A filler plays whenever no reply audio has started 700 ms after the endpoint (T8)
- [ ] Speculative latency gain and hit rate are measured and recorded (T14)
- [ ] No side-effect tool or state write ever runs speculatively (T12)

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI; measurement report linked in the PR
- [ ] PR reviewed
- [ ] No PHI in logs
- [ ] `docs/voice/barge-in.md` and `docs/voice/p3-06-report.md` written; P2-01 and P2-04 additive changes merged
- [ ] P3-11 and P3-14 notified

## 13. Hand-off
| Consumer | What they can rely on |
|---|---|
| P3-09 Read-back | Backchannel "yes" over a question is not an answer; confirmations need an explicit reply after the question |
| P3-11 Avatar / transcript | `playback_paused` / `resume` / `flush` events to show listening vs speaking |
| P3-14 Tuning | Window and threshold constants, metrics, the speculative flag decision |
| P2-01 / P2-04 | `prefetched` hook; `interrupted` turn records |

## 14. Open questions
| # | Question | Recommended answer | Owner |
|---|---|---|---|
| 1 | Should backchannel words be configurable per clinic? | No: a product constant list, tuned in P3-14. | Tech lead |
| 2 | Should the filler wording change by flow (e.g. "Let me book that")? | No for the MVP: generic fillers are safe in every state and never imply an outcome. | Product owner |
| 3 | Should speculation also prepare the reply (LLM stream) when no tool is needed? | No: the reply depends on the handler result; revisit in P3-14 only if voice-to-voice is still above target. | Tech lead |

## 15. References
- Plan: §4.4, §11
- DECISIONS: #63, #174, #203, #224, #226, #227, #230, #234, #235, #236
- Related tasks: P1-07, P1-15, P2-01, P2-03, P2-04, P2-05, P2-08, P2-20, P3-01, P3-02, P3-03, P3-09, P3-11, P3-14
