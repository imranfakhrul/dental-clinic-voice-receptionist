---
id: P3-14
title: Voice latency and quality dashboard, nightly latency run, tuning to targets, and the Phase 3 demo
milestone: P3
epic: E3.3
size: L
labels: area:voice, area:infra, area:qa, type:feature
depends_on: P3-02, P3-03, P3-06, P3-09, P3-11, P1-07, P2-30
status: approved
---

# P3-14: Voice latency and quality dashboard, nightly latency run, tuning to targets, and the Phase 3 demo

## 1. Summary
Close Phase 3: measure the voice pipeline end to end, tune it until it meets the plan's targets, and show a full voice booking. This task absorbs **P3-15 (latency tuning to hit targets)** and **P3-16 (Phase 3 demo: voice-to-voice booking)**.

| Part | What it does |
|---|---|
| Measurement | The browser measures voice-to-voice on its own clock and reports it; the server times every stage; one `voice` dashboard with p50/p95, quality and cost panels; two new alerts |
| Nightly latency run | A replay client plays the P3-01 audio set into staging every night (200 turns, clean + noisy) and checks the targets; a small real-microphone study by the team |
| Tuning | Knobs as env vars, changed one at a time under decision rules fixed in advance; every change logged |
| Gap handling | If targets are still missed: a gap report and a product-owner decision; safety features are never removed |
| Demo | A recorded 3–5 minute voice booking on staging (synthetic patient, consenting speaker), accepted by the tech lead |

Done means:
- the dashboard shows every plan §4.4 stage;
- voice-to-voice ≤ 1.5 s p50 and ≤ 2.5 s p95 in the nightly run on 3 consecutive nights (or an approved gap decision);
- barge-in stop ≤ 200 ms p50;
- the demo is accepted by the tech lead.

## 2. Why this matters
Voice latency is a pilot success criterion (plan §11: voice-to-voice ≤ 1.5 s p50 / 2.5 s p95). Earlier P3 tasks left their thresholds as **Proposed** and named this task to settle them with data (endpoint silences, barge-in window, phrase boost, LLM deadlines, the speculative flag, echo checks). Without a repeatable measurement, every change is a guess, and regressions after a model or config change go unnoticed until patients complain.

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P3, Voice Pipeline & Avatar**.
- **Plan §4.4 targets:** endpoint ≤ 300–500 ms; LLM time to first token ≤ 300 ms; TTS first audio ≤ 250 ms; voice-to-voice ≤ 1.0–1.5 s p50; barge-in stop ≤ 200 ms; text first token ≤ 1 s.
- **p50 / p95:** the median, and the value 95% of turns are faster than.
- **What already exists:**
  - **P1-07** (approved): `stage_timer()`, `dai.stage.latency` histogram, `Stage` enum (incl. `ENDPOINT_DETECTED`, `BARGE_IN_STOP`), `latency` dashboard skeleton, alert A4 (voice-to-voice p95 > 2500 ms for 15 min).
  - **P3-01** (approved): spike report and baseline, 30 recorded synthetic utterances + noisy copies, replay mode, tuning backlog.
  - **P3-02 / P3-03 / P3-06 / P3-09 / P3-11** (approved): the pipeline and its metrics (`voice.endpoint`, `stt.utterance`, `tts.reply`, `voice.barge_in`, `voice.speculative`, `readback.result`, avatar marks, `channel_switches`).
  - **P2-30** (approved): Playwright staging scenarios, `X-DAI-E2E` test bypass (dev/staging only), `ZZTEST` patients, nightly job and report.
  - **P2-03** (approved): `LLM_TTFT_DEADLINE_MS_*` env vars.
  - **P1-02** (approved): `api` min instances 1 in prod, 0 in dev/staging.

## 4. Scope
**In scope**
- Client voice-to-voice measurement and the `playback_started` message.
- New `Stage` value `VOICE_TO_FIRST_SOUND`; the `voice` dashboard; alerts A-V2, A-V3.
- Replay client and the nightly `voice-latency` workflow on staging; critical-field accuracy check.
- Real-microphone study (team).
- Tuning knobs as env vars, decision rules, the tuning log, the gap report.
- The Phase 3 demo script, recording and sign-off.

**Out of scope** (and which task covers it)
- Load and soak testing at pilot scale → P5-03
- Production quotas, Provisioned Throughput → P5-06
- Conversation-quality evals → P5-01
- New transport (WebRTC, Opus) or an ML semantic-turn model → new task, only if the decision rules below trigger it

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P3-02 … P3-11 (approved) | Working pipeline and metrics | Build the dashboard against the metric names; the replay client against the fake server voice script (P3-11) |
| P2-30 (approved) | Staging test bypass, nightly job | Reuse `nightly.yml`; until then run the replay client by hand |
| P3-01 (approved) | Audio set | Use it as is; the 20 spelling recordings from P3-09 are added |

## 6. Interface contract

### Voice-to-voice, measured by the browser (DECISIONS #247)
Protocol v2 addition (C→S):
```json
{"type": "playback_started", "reply_id": 41, "utterance_id": 17, "filler": false,
 "v2v_ms": 1240, "output_latency_ms": 24}
```
- `v2v_ms` = time on the **browser clock** from the client VAD end of speech of utterance `utterance_id` to the moment the first sample of reply `reply_id` reaches the speaker (`AudioContext` scheduled start + `outputLatency`; **Verify** `outputLatency` support, else 0 and flagged).
- Sent once per reply on VOICE turns; `filler=true` for fillers (P3-06).
- Server records:
  - `Stage.VOICE_TO_VOICE` = first **non-filler** reply audio (the plan target; fillers must not hide slowness);
  - `Stage.VOICE_TO_FIRST_SOUND` (new) = first audio of any kind, filler included.
- Values > 30 000 ms or negative are dropped and counted (`dai.voice.v2v_invalid`).
- Server-side stage timers (P3-02/03/06) explain **where** the time goes; the client number is the truth for the target.

### Network share
`ping`/`pong` (P2-25) carry `t_client`; the client reports `rtt_ms` every 30 s in voice mode (`{"type":"net_stats","rtt_ms":…}`); dashboard panel "network RTT p50". Used by decision rule R6.

### `voice` dashboard (`infra/monitoring/dashboards/voice.json`; DECISIONS #247)
| Row | Panels (p50 and p95 lines with target lines) |
|---|---|
| Headline | Voice-to-voice (target 1500 / 2500), voice-to-first-sound, barge-in stop (200), text first chunk (1000) |
| Stages | Endpoint detected (500), STT first partial (300), STT final, LLM first token per tier (300), LLM total, tool calls per tool, Open Dental per endpoint, TTS first audio (250) |
| Endpointing | Rule mix (`base` / `unfinished` / `data_entry` / `spelling` / `cap`), utterances discarded by reason |
| Barge-in | Decisions (barge-in vs resume), echo barge-in rate, decision time |
| Quality | Read-back first-try confirm rate per field, corrections, spelling parse rate, STT final fallback rate, speculative hit rate and saved ms, voice stops by reason (`stt_unavailable`, `tts_unavailable`, `idle`, `limit`), channel switches |
| Network | RTT p50/p95, frames late |
| Cost | STT audio minutes, TTS characters, LLM tokens per tier (input/output) per day; estimated cost per voice session using the price table in `docs/voice/costs.md` |
Filter: environment, clinic, model tier. No PHI in any label.

### Alerts (additive to P1-07)
| ID | Condition | Severity |
|---|---|---|
| A4 (exists) | Voice-to-voice p95 > 2500 ms for 15 min | P2 |
| A-V2 | Barge-in stop p95 > 400 ms for 30 min | P3 (ticket) |
| A-V3 | Voice sessions ending with `stt_unavailable` or `tts_unavailable` > 5% in 15 min (min 20 sessions) | P2 |

### Nightly latency run (DECISIONS #248)
```bash
python scripts/voice/replay_client.py --env staging --audio evals/voice/audio --turns 200 \
  --scenarios evals/voice/scenarios.yaml --report out/voice-latency.json
```
- **Replay client** (Python, protocol v2): opens a session with the P2-30 `X-DAI-E2E` bypass, plays WAV files as 20 ms frames in real time, simulates client VAD from the known speech boundaries, measures v2v with the same definition as the browser, and plays the patient side of scripted conversations (`ZZTEST` patients).
- **Audio set** moves from the spike to `evals/voice/audio/` (P3-01 30 utterances + 10 dB noisy copies + P3-09's 20 spelling recordings), with ground-truth transcripts and expected slot values.
- **Scenarios:** 10 short scripted conversations (identify, book, reschedule, cancel, FAQ, spelling, barge-in with a real interruption, barge-in with "uh-huh"), 200 turns in total.
- **Workflow** `.github/workflows/voice-latency.yml`, nightly after the P2-30 E2E run; report artifact (JSON + HTML) with p50/p95 per stage, previous 7 nights for comparison.
- **Pass rule:** voice-to-voice ≤ 1500 ms p50 and ≤ 2500 ms p95, barge-in stop ≤ 200 ms p50, endpoint ≤ 500 ms p50, early cut-offs ≤ 5%, critical-field accuracy after read-back ≥ 98% (confirmed slot values equal the expected values). "Targets met" = pass on **3 consecutive nights**.
- **Regression:** after targets are met, a night that fails by > 10% on voice-to-voice p50 opens a ticket automatically.

### Real-microphone study (DECISIONS #248)
4–5 team members, 10 sessions each (laptop and phone, quiet and noisy rooms, at least one headset), following the demo script with variations. Measured through the normal production metrics on staging; results in `docs/voice/p3-14-report.md`. It confirms the replay numbers; it is not the pass rule.

### Tuning knobs (all env vars, no code changes; DECISIONS #249)
| Knob (env var) | Default | Owner task |
|---|---|---|
| `ENDPOINT_BASE_MS`, `ENDPOINT_UNFINISHED_MS`, `ENDPOINT_DATA_ENTRY_MS`, `ENDPOINT_SPELLING_MS` | 300 / 800 / 1200 / 1500 | P3-02 |
| `BARGE_IN_WINDOW_MS`, `BARGE_IN_SPEECH_ONLY_MS` | 700 / 1200 | P3-06 |
| `FILLER_FIRST_MS`, `FILLER_SECOND_MS` | 700 / 4000 | P3-06 |
| `VOICE_SPECULATIVE_EXTRACT` | false (prod) | P3-06 |
| `STT_PHRASE_BOOST` | 10 | P3-03 |
| `LLM_TTFT_DEADLINE_MS_*` | 1500 / 2000 / 4000 | P2-03 |
| `TTS_VOICE_NAME` (within the allow-list) | ADR 0007 default | P3-03 |
| `api` min instances (staging for the run) | 1 | P1-02 |

### Decision rules, fixed in advance (DECISIONS #249)
| # | Change | Only when | Keep the change if |
|---|---|---|---|
| R1 | Speculative extraction on in prod | Always evaluated | Hit rate ≥ 50% **and** median saved ≥ 150 ms **and** LLM tokens +≤ 20% |
| R2 | Lower `ENDPOINT_BASE_MS` (step 50 ms, min 200) | Endpoint p50 > 400 ms | Early cut-offs stay ≤ 5% |
| R3 | Raise endpoint silences (step 100 ms) | Early cut-offs > 5% | Cut-offs ≤ 5% and v2v p50 still ≤ 1500 |
| R4 | Evaluate an ML semantic-turn model (new task) | After R2/R3: endpoint p50 > 500 ms **or** cut-offs > 5% | - |
| R5 | Echo check ("partial matches the playing sentence", P3-06) | Echo barge-in rate > 2% | Echo rate ≤ 2% without missing real barge-ins in the scenarios |
| R6 | Evaluate WebRTC or Opus (new task) | Network RTT p50 > 150 ms from US test locations | - |
| R7 | Change `STT_PHRASE_BOOST` | Hint-phrase WER not better than without hints | WER on hint phrases improves and overall WER does not get worse |
| R8 | Low-confidence re-ask (P3-03 Q1) | Read-back corrections > 10% of read-backs | Corrections fall, turns per booking do not rise > 10% |
| R9 | Lower `LLM_TTFT_DEADLINE_MS_FLASH` for voice | LLM first token p95 > 1500 ms | Fallback rate stays < 2% |
| R10 | Barge-in window ± 100 ms | Backchannel resume rate < 90% or barge-in decision p50 > 700 ms | Both scenario sets pass |
Process: one change at a time; two nightly runs before and after; result and decision appended to `docs/voice/tuning-log.md` and to DECISIONS.md.

### Gap handling (DECISIONS #250)
If the targets are still missed after the rules are exhausted:
1. `docs/voice/p3-14-gap-report.md`: gap per stage (where the time goes), what was tried, options with expected gain and cost.
2. The product owner chooses one:
   - start the pilot with the measured latency (alert thresholds set to the measured p95 + 20%);
   - use a faster model tier for voice replies (`lite`) where evals (P5-01) allow;
   - open a new tuning task with a named owner.
3. **Never** removed or weakened to save time: emergency rules, read-back, confirmation cards, the output guard.

### Phase 3 demo (DECISIONS #250)
| Item | Value |
|---|---|
| Where | Staging, Chrome on a laptop, built-in mic and speakers (echo cancellation on) |
| Patient | Seeded `ZZTEST` returning patient; synthetic details only |
| Speaker | A team member with written consent for the recording |
| Script (3–5 min) | 1) "Hi, I'd like a cleaning" by voice → 2) identification: name, DOB, phone; read-back with one correction ("no, it's 504…") → 3) last name spelled ("S as in Sam…") → 4) options read out; patient interrupts ("actually, something on Thursday") → 5) confirmation card shown; "yes" by voice → 6) booked → 7) patient types "Do you take Delta Dental?" (text-only reply) |
| Recording | Screen + system audio + mic, with the dashboard's per-turn numbers shown at the end |
| Storage | Team Google Drive (Workspace, access limited to the project group); not in the repo |
| Sign-off | Tech lead accepts in the P3-14 issue with a link; issues found become tickets |

## 7. Implementation guide
1. **Client measurement**: `playback_started`, `net_stats`; `AudioPlayer` reports the scheduled start; protocol types (P3-02, P2-25).
2. **Server**: record `VOICE_TO_VOICE`, `VOICE_TO_FIRST_SOUND`; invalid-value counter; P1-07 `Stage` addition.
3. **Dashboard and alerts** in Terraform (`voice.json`, A-V2, A-V3); `docs/voice/costs.md` price table (from `PROJECT_OVERVIEW.md` §3, re-read the price pages on the day).
4. **Replay client** and the evals audio folder with ground truth; scenarios YAML.
5. **Nightly workflow** and HTML report; regression ticket.
6. **Baseline**: 3 nights with defaults; real-mic study.
7. **Tuning** by the rules; tuning log; DECISIONS rows.
8. **Gap report** if needed; decision recorded.
9. **Demo** rehearsal, recording, sign-off.
10. **Docs** `docs/voice/latency.md` (definitions, dashboard guide, how to run the replay). Notify P5-01, P5-03, P5-06, P6 (pilot monitoring).

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| Browser lacks `outputLatency` | `output_latency_ms: 0`, flagged; dashboard panel shows the share of flagged samples |
| Patient's clock jumps (sleep/wake) | Same-clock deltas only; negative or > 30 s values dropped |
| Staging cold start skews the first turns | Run uses min instances 1 and a 2-turn warm-up excluded from the stats |
| Open Dental test DB slow at night | Tool time shown separately; the report notes Open Dental p95; a run whose Open Dental p95 is > 3× the 7-night median is marked "infra-affected" and does not count toward the 3 nights |
| Google STT/TTS incident | Run fails with service errors; marked "provider incident", not counted |
| A tuning change helps p50 but hurts p95 | Not kept (both must meet the rule) |
| Model price or ID changes | `docs/voice/costs.md` updated; model changes follow the P0-13 runbook |
| Speaker withdraws consent for the demo | Recording deleted; re-record with another speaker |

## 9. Security, HIPAA and PHI
- **PHI handled:** none new. The replay uses synthetic recordings and `ZZTEST` patients on staging; the test bypass header is refused in prod (P2-30).
- **Metrics and dashboards:** numbers and codes only; no transcripts, slot values or audio.
- **Recordings:** team voices with written consent; demo video contains only synthetic data and is stored with restricted access.
- **Cost panel** uses counters only.

## 10. Testing
```bash
cd backend && pytest tests/unit/voice/test_v2v_metrics.py -q        # stage recording, invalid values
cd frontend && pnpm test -- voice/playback-started                     # scheduled-start maths
python scripts/voice/replay_client.py --env dev --turns 20 --dry-run   # client sanity
terraform -chdir=infra/envs/staging plan                               # dashboard + alerts
```
| # | Case | Expected |
|---|---|---|
| T1 | `playback_started` for a reply and a filler | `VOICE_TO_VOICE` from the reply only; `VOICE_TO_FIRST_SOUND` from the filler |
| T2 | Invalid `v2v_ms` (negative, 40 000) | Dropped, counted |
| T3 | Dashboard | Every §4.4 stage has a p50/p95 panel with its target line |
| T4 | Alerts A-V2, A-V3 | Fire with synthetic metric data in staging |
| T5 | Replay client accuracy | Its v2v differs from a browser run on the same audio by ≤ 50 ms p50 (10-turn comparison) |
| T6 | Nightly report | Per-stage p50/p95, 7-night trend, pass/fail per rule |
| T7 | Critical-field accuracy check | Confirmed values compared with ground truth; ≥ 98% |
| T8 | Regression ticket | Created on a > 10% worse night |
| T9 | Targets | 3 consecutive passing nights (or the approved gap decision) |
| T10 | Demo | Recorded, script followed, accepted by the tech lead |

## 11. Acceptance criteria
- [ ] Dashboard shows all plan §4.4 stages with p50/p95 and target lines (T3)
- [ ] Voice-to-voice ≤ 1.5 s p50 and ≤ 2.5 s p95, barge-in stop ≤ 200 ms p50, in the nightly run on 3 consecutive nights — or a recorded product-owner gap decision (T9)
- [ ] Critical-field accuracy after read-back ≥ 98% in the replay set (T7)
- [ ] Every tuning change follows a decision rule and is logged (tuning log + DECISIONS)
- [ ] Phase 3 demo accepted by the tech lead (T10)

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI; nightly workflow running
- [ ] PR reviewed
- [ ] No PHI in metrics, reports or recordings
- [ ] `docs/voice/latency.md`, `docs/voice/costs.md`, `docs/voice/p3-14-report.md`, `docs/voice/tuning-log.md` written
- [ ] P5-01, P5-03, P5-06 and P6 notified

## 13. Hand-off
| Consumer | What they can rely on |
|---|---|
| P5-03 Load tests | Replay client (scalable to many sessions), dashboards, baseline numbers |
| P5-06 Quotas | STT/TTS/LLM usage per session from the cost panel |
| P5-01 Evals | Voice scenarios and ground-truth audio |
| P6 Pilot | Dashboard, alerts, cost per session, the regression check |

## 14. Open questions
| # | Question | Recommended answer | Owner |
|---|---|---|---|
| 1 | Should the nightly run also test from a mobile network? | Not in CI; the real-mic study includes phones on cellular data. | Tech lead |
| 2 | Should patients' browsers send `net_stats` in prod? | Yes, every 30 s in voice mode (numbers only); it is the only way to see network problems at the clinic's patients. | Tech lead |
| 3 | Should the demo be shown live to the clinic? | Recorded for the tech lead first; a live clinic demo is part of P6 onboarding. | Product owner |

## 15. References
- Plan: §4.4, §8 Phase 3, §11
- DECISIONS: #63, #161, #224, #225, #227, #234, #236, #247, #248, #249, #250
- Related tasks: P0-13, P1-02, P1-07, P2-03, P2-25, P2-30, P3-01, P3-02, P3-03, P3-06, P3-09, P3-11, P5-01, P5-03, P5-06, P6-01
