---
id: P5-03
title: "Voice test sets: accents, noise, mic quality; WER on critical fields"
milestone: P5
epic: E5.1
size: L
labels: area:qa, area:voice, type:test
depends_on: P3-16, P3-14, P3-15, P3-09, P3-03, P1-02, P1-13
status: approved
---

# P5-03: Voice test sets: accents, noise, mic quality; WER on critical fields

## 1. Summary
Build the **voice quality test set** and the **load and latency test**. This task absorbs **P5-06 (load and latency tests, concurrent sessions)**.

| Part | What it delivers |
|---|---|
| Voice test set | About 900 synthetic + 600 human utterances covering accents, background noise, phone-quality audio, barge-in and silence; each has ground truth |
| Accuracy measure | Raw WER per field type (report only) and **critical-field accuracy after read-back** with a simulated caller (gate ≥ 98%) |
| Load test | 1× and 3× pilot peak on staging (5 voice + 15 chat at 1×; 15 voice + 45 chat at 3×), 30 minutes steady plus a spike; latency per stage under load |
| Tuning output | Recommended Cloud Run, Cloud SQL, Redis and rate-limit values for prod, recorded in a report and applied by PR |

Done means:
- critical-field accuracy after read-back is ≥ 98% on the full set;
- voice-to-voice latency holds p50 ≤ 1.5 s and p95 ≤ 2.5 s at 1× and 3× load;
- the error rate under load is < 1%.

## 2. Why this matters
Plan §9 asks for voice test sets across accents, noise and phone mics, WER on names, numbers and dates, and a load test for concurrent sessions. Plan §11 sets two pilot targets measured here:
- critical-field accuracy (after read-back) ≥ 98%;
- voice latency p50 ≤ 1.5 s and p95 ≤ 2.5 s.

Without these tests we would find out at the pilot clinic that John's surname is misheard for every Spanish-accented caller, or that latency doubles when three people call at once. Several approved specs left values for this task to tune:
- P1-02: Cloud Run concurrency and max instances;
- P1-03: Cloud SQL tier;
- P1-07: alert thresholds;
- P1-13: rate limits;
- P2-03: circuit breaker.

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P5, Hardening, Testing & Security Review**.
- **WER (word error rate):** (substitutions + deletions + insertions) / words in the reference. A WER of 10% means about one word in ten is wrong. For names and numbers we also use **field accuracy**: the whole value is right or wrong.
- **SNR (signal-to-noise ratio):** how much louder speech is than background noise, in dB. 20 dB is a quiet room, 10 dB a café, 5 dB a busy street.
- **Phone-band audio:** many callers use cheap headsets or speakerphones. We simulate this with an 8 kHz low-pass and the G.711 μ-law codec.
- **Read-back (P3-09):** the AI repeats critical values ("That's K-O-W-A-L-S-K-I, right?") and the caller corrects them. What counts for the KPI is the value after this loop.
- **Simulated caller:** a script that plays recorded patient turns into the real voice pipeline. When the read-back is wrong, it plays a pre-recorded correction.
- **What already exists (approved):**
  - **P3-14:**
    - `scripts/voice/replay_client.py` (scales to many sessions);
    - `evals/voice/audio/` (P3-01's 30 utterances, noisy copies and P3-09's 20 spelling recordings) with ground truth;
    - `evals/voice/scenarios.yaml`;
    - the latency dashboard and per-stage metrics;
    - the `voice-latency.yml` workflow;
    - T7, the critical-field check.
  - **P3-15:** latency tuning levers.
  - **P3-16:** Phase 3 voice booking demo.
  - **DECISIONS #122:** rate limits (`voice_concurrent` 3 per IP, …) with `RATE_LIMIT_OVERRIDES`.

## 4. Scope
**In scope**
- Recording kit and consent form for human volunteers; TTS generation of synthetic utterances; noise and phone-band augmentation pipeline.
- Ground-truth format, the field-accuracy scorer, WER reports per accent, noise level and field type.
- Simulated-caller mode in `replay_client.py` (read-back aware), barge-in and silence cases.
- Load test with `locust` driving `replay_client` sessions and text chat sessions; per-stage latency under load; resource and quota observations.
- Tuning report and the PRs that apply the agreed prod values (Cloud Run, Cloud SQL tier, Redis, rate limits, alert thresholds).
- Workflow `voice-quality.yml` (manual) and extension of `voice-latency.yml` with a `load` job (manual).

**Out of scope** (and which task covers it)
- Conversation logic evals in text → P5-01
- Double-booking races → P5-04
- Fixing STT phrase hints and vocabulary → P3-03 owner now, P6-04 during the pilot
- Production quotas and Provisioned Throughput purchase → decided from this report by the tech lead; requested by P6-01

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P3-14 replay client and audio set | Protocol v2 client, ground-truth layout | Approved; extend it |
| P3-09 read-back | Read-back prompts and the `rb:fix:<field>` flow | Approved; the simulated caller keys off `readback` events |
| Staging stack (P1-02) | Cloud Run `api`, `web`, Redis, Cloud SQL | Approved; run the load test on dev with reduced numbers first |
| Volunteers | Recorded human audio | Start with TTS-only sets; human audio is added when recorded |

## 6. Interface contract

### Test-set layout (`evals/voice/`)
```
evals/voice/
├── audio/                         # existing P3-14 set (kept)
├── sets/
│   ├── synthetic/<voice_id>/<utt_id>.wav       # 16 kHz mono PCM, clean
│   ├── human/<speaker_id>/<utt_id>.wav         # 16 kHz mono PCM, clean
│   └── augmented/<snr>/<band>/<src>/<utt_id>.wav  # generated; not committed (built in CI from a seed)
├── ground_truth.yaml
├── speakers.yaml                  # speaker_id → accent group, age band, consent_id (no names)
└── noise/                         # noise clips with licence notes (Verify licences)
```
```yaml
# ground_truth.yaml (one entry per utterance)
- utt_id: name-spell-017
  text: "My last name is Kowalski, K O W A L S K I"
  fields: {last_name: "Kowalski"}
  kind: name            # name | dob | phone | date_time | email | free
  correction_utt: name-spell-017-fix   # audio the simulated caller plays if read-back is wrong
```

### Coverage (DECISIONS #273)
| Dimension | Values |
|---|---|
| Sources | TTS: 300 utterances × 3 voices (Google TTS voices from different locales, **Verify** availability) = 900; humans: ~10 volunteers × 60 lines = 600 |
| Accent groups (humans) | US General, US Southern, Hispanic-English, South Asian-English, East Asian-English, African-American, older speaker (65+), non-native fast speech; at least one speaker per group |
| Content | Names (common, hyphenated, rare surnames, spelled), DOB (spoken many ways), US phone numbers, dates and times ("next Tuesday at 3"), emails, yes/no, free reason text, emergency phrases from P0-03 |
| Noise (augmented) | Clean, 20 dB (quiet room), 10 dB (café, TV), 5 dB (street, car) |
| Mic/band | Wideband 16 kHz, phone band (8 kHz low-pass + G.711 μ-law), low-quality laptop mic (band-pass 300–3400 Hz + light clipping) |
| Behaviour | Barge-in during a reply (20 cases), long silence (10), very short answers ("yes", "nope") (20), coughs and fillers ("um") (10) |

Human recordings use **fictional** names, DOBs and phones from a provided script. Volunteers sign `docs/qa/voice-consent.md` (purpose, storage in the private repo, right to withdraw); `speakers.yaml` stores only a consent ID.

### Scorer
```python
# evals/voice/score.py
def wer(ref: str, hyp: str) -> float: ...                        # jiwer, normalized (lowercase, digits)
def field_correct(kind: str, expected: str, confirmed: str) -> bool: ...  # uses P2-12 normalizers
@dataclass
class VoiceQualityReport:
    raw_wer: dict[str, float]           # by kind, accent group, snr, band
    raw_field_accuracy: dict[str, float]
    final_field_accuracy: dict[str, float]   # after read-back (the gate)
    readback_turns_mean: float          # how many correction rounds were needed
    bargein_stop_ms_p95: int
    silence_handling_pass: float
```
**Gate (plan §11):** `final_field_accuracy` overall ≥ 0.98, **and** ≥ 0.95 for every accent group and every noise level of 10 dB and above. The 5 dB street level is reported but not gated.

### Simulated caller (extension of `replay_client.py`)
```bash
python scripts/voice/replay_client.py --env staging --mode simulated-caller \
  --set evals/voice/sets --augment snr=10,band=phone --sessions 1 --report out/voice-quality.json
```
- Plays the utterance; waits for the `readback` item; compares the read-back value with ground truth. If it is wrong, it plays `correction_utt` (at most 2 rounds, like a real caller), then reads the confirmed slot value from the session summary endpoint (P2-30 verification client).
- Barge-in cases: starts the next utterance 800 ms into a reply. Measures the time from speech start to `playback_flush` (P3-06 target).
- Silence cases: plays nothing for 8 s / 20 s / 60 s and checks the P3-02 prompts and the 60 s auto-pause.

### Load test (DECISIONS #273)
| Profile | Voice sessions | Chat sessions | Duration |
|---|---|---|---|
| `1x` (pilot peak; **Verify** against P0-01 call volume) | 5 | 15 | 30 min steady |
| `3x` | 15 | 45 | 30 min steady |
| `spike` | 0 → 15 voice + 45 chat in 60 s | | 10 min |

```bash
locust -f loadtest/locustfile.py --headless --host https://api.staging.<domain> \
  --profile 3x --od-mode fake-latency --report out/load-3x.json
```
- Voice users run the `replay_client` session loop (booking scenario, 6–10 turns, think time 2–6 s); chat users run P2-30's booking flow through the API with the bot bypass header.
- **Open Dental:** staging uses `od_fake` with simulated latency (`OD_FAKE_LATENCY_MS=300±100`), because the shared Open Dental test database must not be hammered. One extra 1× run of 10 minutes uses the real test DB.
- **Rate limits:** the load run sets `RATE_LIMIT_OVERRIDES` on staging for the load generator's IPs only (`voice_concurrent: 50`), through a release PR that is reverted after the run.
- **Measured** (from P3-14 metrics and Cloud Monitoring): voice-to-voice p50/p95, per-stage p95 (endpoint, STT final, LLM TTFT, TTS first audio), error rate, WebSocket drops, Cloud Run instances, CPU, memory, Cloud SQL CPU and connections, Redis ops, Vertex AI 429s and quota use.

**Pass:** at 1× and 3×, voice-to-voice p50 ≤ 1.5 s and p95 ≤ 2.5 s, error rate < 1%, 0 dropped sessions caused by the server. Spike: p95 ≤ 3.5 s during the first 2 minutes, then back within the targets.

### Tuning output (`docs/perf/load-report-<date>.md`)
Recommended prod values with evidence:
- `api` concurrency and min/max instances (P1-02 placeholders 80 / 20);
- Cloud SQL tier (P1-03);
- Redis size;
- rate limits (DECISIONS #122);
- alert thresholds (P1-07);
- whether P2-03 needs a circuit breaker;
- the Vertex AI quota and whether Provisioned Throughput is needed (**Verify** quota names in the console).

The values are applied by Terraform and config PRs, which need the usual two prod approvers (P1-06).

### Workflows
- `voice-quality.yml` (manual; also required before prod promotion when files under `backend/app/voice/**` or `config/stt*` changed since the last green run): builds the augmented set, runs the simulated caller, uploads the report.
- `voice-latency.yml` gains a `load` job (manual only, because of cost); a run needs the inputs `profile` and `confirm_cost: yes`.

## 7. Implementation guide
1. **Scripts and consent.** Write the line script (60 lines per speaker covering all `kind`s), `docs/qa/voice-consent.md`, and the recording guide (phone or laptop, quiet room, WAV export).
2. **TTS generation** `evals/voice/gen_tts.py`: 300 lines × 3 voices with Google TTS in the dev project, 16 kHz mono.
3. **Augmentation** `evals/voice/augment.py`: noise mixing at the listed SNRs, phone band (scipy low-pass + μ-law), laptop profile; deterministic seed; the output is not committed. Noise clips: **Verify** the licence of each source (for example MUSAN, freesound CC0) and record it in `noise/LICENSES.md`.
4. **Ground truth** for every utterance, plus correction utterances for names, phones and DOBs.
5. **Scorer** with `jiwer` and P2-12 normalizers.
6. **Simulated-caller mode** in `replay_client.py`, including barge-in and silence cases.
7. **Run the quality set** on staging; file issues per failing group (for example phrase hints for rare surnames, P3-03).
8. **Load test** `loadtest/locustfile.py` with voice and chat users; `od_fake` latency mode (`OD_FAKE_LATENCY_MS`) in the fake adapter. **Proposed:** a new env-only switch, refused when `ENV=prod`.
9. **Run** 1×, 3× and spike on staging; one 1× run on the real test DB; collect the dashboards.
10. **Tuning report and PRs**, reviewed by the tech lead and a second engineer.
11. **Docs** `docs/qa/voice-tests.md` and `docs/perf/load-testing.md`; notify P6-01 (prod values, quota request) and P6-04 (re-run after STT tuning).

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| A volunteer withdraws consent | Delete their files and `speakers.yaml` row in a PR; re-run the reports |
| TTS voice not available in the project's location | Pick another voice from the same accent locale; record it in `ground_truth.yaml` metadata |
| Accuracy passes overall but one accent group < 95% | Gate fails; issue labelled `voice-accent`; fix through phrase hints or read-back prompts |
| Read-back still wrong after 2 correction rounds | Counts as wrong (a real caller would give up or go to callback) |
| Vertex AI 429 during the load test | Count as errors; note the quota; this is a finding, not a test failure to retry |
| Load generator itself saturates (CPU > 80%) | Results invalid; add workers (locust distributed mode) |
| Real Open Dental test DB slows under the 1× run | Stop after 10 minutes; note the observed limit for P6-01 |
| Cost of a 3× run | About 30 min × 60 sessions of STT, TTS and LLM; the workflow asks for `confirm_cost`; estimate shown in the job summary (**Verify** prices) |

## 9. Security, HIPAA and PHI
- **No PHI:** synthetic TTS, and human volunteers reading fictional data. Volunteer voices are personal data, so they live in the private repo only, under the consent form, and are never sent outside Google Cloud (STT/TTS under the Google Cloud BAA). No vendor outside the BAA chain receives them.
- Load tests run against staging (synthetic data only, DECISIONS #25).
- The temporary rate-limit override is scoped to the load generator IPs and removed after the run (tracked in the PR).
- Reports contain metrics and utterance IDs only.

## 10. Testing
```bash
pytest evals/voice/tests -q                      # scorer, normalizers, augmentation determinism
python evals/voice/augment.py --seed 7 --check   # reproducible augmented set
python scripts/voice/replay_client.py --env dev --mode simulated-caller --sessions 1 --limit 20
locust -f loadtest/locustfile.py --headless --profile smoke --host https://api.dev.<domain>
```
| # | Case | Expected |
|---|---|---|
| T1 | WER on a known pair | Matches hand calculation |
| T2 | Field scorer: "555-0101" vs "+15555550101" | Correct (normalized) |
| T3 | Read-back wrong once, corrected | Final correct; `readback_turns` = 1 |
| T4 | Full quality set on staging | Overall ≥ 98%; every accent group and SNR ≥ 10 dB ≥ 95% |
| T5 | Barge-in set | `playback_flush` p95 within P3-06 target |
| T6 | Silence set | P3-02 prompts and auto-pause at 60 s |
| T7 | Load 1× and 3× | Latency targets met; error rate < 1% |
| T8 | Spike | p95 ≤ 3.5 s in the first 2 min, then within targets |
| T9 | `OD_FAKE_LATENCY_MS` set with `ENV=prod` | App refuses to start |

## 11. Acceptance criteria
- [ ] Voice test set with ≥ 1,400 utterances across the accent, noise, band and behaviour dimensions in §6, with ground truth and consent records (T4)
- [ ] Critical-field accuracy after read-back ≥ 98% overall and ≥ 95% per accent group and per SNR ≥ 10 dB (T4)
- [ ] Barge-in and silence behaviour verified (T5, T6)
- [ ] Latency targets hold at 1× and 3× pilot load with < 1% errors (T7, T8)
- [ ] Tuning report written and the prod values applied through reviewed PRs

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI
- [ ] PR reviewed (tech lead + voice engineer)
- [ ] No PHI in audio, reports or logs
- [ ] `docs/qa/voice-tests.md`, `docs/perf/load-testing.md`, load report written; P6-01 and P6-04 notified

## 13. Hand-off
| Consumer | What they can rely on |
|---|---|
| P6-01 Go-live | Prod sizing values, quota request, "voice quality and load reports green for the release" checklist item |
| P6-04 Tuning | `voice-quality.yml` to re-run after vocabulary or prompt changes |
| P1-07 alerts | Tuned thresholds |
| P5-12 Runbooks | Observed limits (Vertex AI 429 point, Open Dental test DB limit) for the outage runbooks |

## 14. Open questions
| # | Question | Recommended answer | Owner |
|---|---|---|---|
| 1 | What is the real pilot peak (calls and chats at once)? | Ask the clinic (P0-01 numbers); until then use 5 voice + 15 chat. | Product owner |
| 2 | Do we need Provisioned Throughput for the pilot? | Only if the 3× run shows Vertex AI 429s at the default quota. | Tech lead |

## 15. References
- Plan: §9 (voice, performance), §11 (latency, critical-field accuracy), §8 Phase 5
- DECISIONS: #25, #108, #122, #273
- Related tasks: P1-02, P1-03, P1-07, P1-13, P2-03, P2-12, P2-30, P3-02, P3-03, P3-06, P3-09, P3-14, P3-15, P3-16, P5-01, P6-01, P6-04
- jiwer: <https://github.com/jitsi/jiwer> · Locust: <https://docs.locust.io/>
- G.711: <https://www.itu.int/rec/T-REC-G.711>
