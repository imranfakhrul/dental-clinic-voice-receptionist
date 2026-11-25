---
id: P3-03
title: Streaming Speech-to-Text with phrase hints, and streaming Text-to-Speech with speech normalization
milestone: P3
epic: E3.1
size: L
labels: area:voice, type:feature, phi
depends_on: P3-01, P3-02, P2-04, P1-19, P1-15, P1-07, P0-06
status: approved
---

# P3-03: Streaming Speech-to-Text with phrase hints, and streaming Text-to-Speech with speech normalization

## 1. Summary
Turn the patient's speech into text, and the assistant's reply text into speech, using Google Cloud Speech-to-Text V2 and Text-to-Speech, both streaming. This task absorbs **P3-05 (streaming TTS with sentence chunker and SSML)**.

| Part | What it does |
|---|---|
| `SpeechToText` | One streaming recognition per utterance (opened at `speech_start`, closed at the endpoint); partials feed P3-02's `TurnDetector`; the final transcript becomes a `UserTurn` |
| Phrase hints | Static dental vocabulary + the clinic's name and provider names + small per-state hints (email words, digit classes); never patient names |
| `transcript` message | Protocol v2 addition: partial and final transcripts sent to the widget (P3-11 renders partials) |
| `TextToSpeech` | One streaming synthesis per reply, fed sentence by sentence from P2-04; fallback to per-sentence synthesis |
| `SpeechNormalizer` | Turns display text into text that reads correctly aloud (digits one by one, times, "Dr.", clinic pronunciations); no SSML needed |
| Voice policy | `en-US` only, voice from the female allow-list (DECISIONS #175, ADR 0007), checked at startup and on config load |

Done means:
- partials arrive within 300 ms of speech p50;
- TTS first audio ≤ 250 ms p50;
- phone numbers are read digit by digit;
- data logging is off and checked in CI;
- no audio or transcript text is ever logged.

## 2. Why this matters
Every voice turn passes through both services, so they set much of the voice-to-voice budget (plan §4.4: TTS first audio ≤ 250 ms, voice-to-voice ≤ 1.5 s p50). STT accuracy on names, numbers and dental words decides how often patients must repeat themselves, and correct read-back ("5-0-3, 5-5-5…") is how critical data gets confirmed (plan §4.4, pilot target: critical-field accuracy ≥ 98% after read-back). Both services receive PHI, so they must run under the Google Cloud BAA in US locations with data logging never enabled (P0-05, P0-06).

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P3, Voice Pipeline & Avatar**.
- **Speech-to-Text V2 streaming:** `StreamingRecognize` over gRPC. The first request carries the config (recognizer, model, language, features, adaptation); later requests carry audio. With `interim_results` it returns partial results while the patient is speaking, then a final result. <https://docs.cloud.google.com/speech-to-text/v2/docs/streaming-recognize>. **Verify:** maximum stream duration and audio per request, and which features (`interim_results`, adaptation, automatic punctuation) the chosen model supports in streaming.
- **Model adaptation (phrase hints):** an inline `PhraseSet` of phrases with an optional boost, and class tokens (e.g. digit sequences, months) that bias recognition toward expected words. <https://docs.cloud.google.com/speech-to-text/v2/docs/adaptation-model>. **Verify** that the P3-01 model supports adaptation and which class tokens are available for `en-US`.
- **Data logging:** an opt-in programme per project; off by default; enabling it requires certifying there is no HIPAA BAA. P0-06 checks the project setting; this task makes sure the code never opts in.
- **Text-to-Speech streaming:** `StreamingSynthesize` accepts text as it arrives and returns audio chunks. **Verify** which voice families support it (P3-01 found this per voice) and whether streaming input accepts SSML (assume **not**; that is why we normalize plain text). <https://docs.cloud.google.com/text-to-speech/docs/create-audio-text-streaming>.
- **What already exists:**
  - **P3-01** (approved): STT model choice, ADR 0007 with `TTS_ALLOWED_VOICES` and the default voice, which voices stream, latency baseline, `Stage.ENDPOINT_DETECTED`.
  - **P3-02** (approved): protocol v2; `VoiceSession.play(reply_id, turn_id, sample_rate, chunks)`; `TurnDetector.on_partial(text, ts_ms)`; endpoint → `UserTurn(channel="VOICE", client_turn_id="v-{session_id}-{utterance_id}")`; `utterance_discarded`; pre-roll 300 ms.
  - **P2-04** (approved): `ReplyGenerator` yields `ReplyChunk(text, source, final, card, choices, info_card)` one sentence at a time after the guard; templates have `voice:` variants used when `channel="VOICE"`; read-back phone voice variant `5-0-3, 5-5-5, 0-1-2-3`; `cancel` event (barge-in).
  - **P1-19** (approved): `voice.language` (`en-US`), `voice.tts_voice` (null = default), `voice.speaking_rate` (0.8–1.2).
  - **P1-15** (approved): `Provider(prov_num, abbr, first_name, last_name, preferred_name)` from the Open Dental setup cache.
  - **P1-07** (approved): `stage_timer()`, `Stage.STT_FIRST_PARTIAL`, `STT_FINAL`, `TTS_FIRST_AUDIO`, `VOICE_TO_VOICE`; PHI-redacting logger.
  - **P0-06** (approved): APIs `speech.googleapis.com`, `texttospeech.googleapis.com` enabled, US-only locations, data logging off.

## 4. Scope
**In scope**
- `SpeechToText` (V2 streaming, per utterance) with phrase hints and the warm channel.
- `transcript` message (protocol v2 addition) for partials and finals.
- `TextToSpeech` (streaming per reply, per-sentence fallback), sample rate and speaking rate.
- `SpeechNormalizer` and the clinic `voice.pronunciations` map (new P1-19 key).
- Voice policy checks (language, allow-list) at startup and on config load.
- Failure handling (STT errors, TTS errors), metrics, no-logging checks.

**Out of scope** (and which task covers it)
- Audio transport, VAD, endpoint rules → P3-02
- Barge-in (stopping TTS, cancelling the LLM), filler phrases, speculative LLM → P3-06 (this task provides `TextToSpeech.cancel()`)
- Read-back flow and spelling mode → P3-09 (it uses `SpeechNormalizer.spell()`)
- Live transcript UI, avatar → P3-11
- Latency tuning and dashboards → P3-14
- Console editing UI for pronunciations → P4-11 (the key is console-editable)

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P3-01 (approved) | STT model, voice allow-list | Use `chirp_3` and a placeholder allow-list from the spike notes until ADR 0007 is merged |
| P3-02 (approved) | Frames per utterance, `on_partial`, `play()` | Unit tests feed recorded WAV frames directly; `FakeVoiceSession` collects played chunks |
| P2-04 (approved) | Sentence stream | `FakeReplyGenerator` yields scripted `ReplyChunk`s |
| P1-15 (approved) | Provider names | Fixture list of 3 providers |
| Google APIs | Real services | Unit tests use `FakeSttClient` / `FakeTtsClient`; integration tests run in dev against the real APIs with synthetic audio |

## 6. Interface contract

### Configuration (env, `backend/app/core/config.py`)
```bash
STT_LOCATION=us                         # Verify the model is served there for streaming
STT_MODEL=chirp_3                       # from P3-01 report
STT_LANGUAGE_CODE=en-US
STT_PHRASE_BOOST=10                     # Proposed; tuned in P3-14
TTS_LANGUAGE_CODE=en-US                 # startup rejects anything else (DECISIONS #175)
TTS_VOICE_NAME=<default from ADR 0007>
TTS_ALLOWED_VOICES=<comma list from ADR 0007>
TTS_SAMPLE_RATE_HZ=24000                # LINEAR16 output; Verify supported rates per voice
TTS_STREAMING_VOICES=<comma list>       # voices that support StreamingSynthesize (P3-01 finding)
```
Startup fails if `TTS_LANGUAGE_CODE != "en-US"`, if `TTS_VOICE_NAME` is not in `TTS_ALLOWED_VOICES`, or if `STT_LANGUAGE_CODE != "en-US"`.

### Clinic config (P1-19 additions, DECISIONS #232)
```yaml
voice:
  language: en-US
  tts_voice: null                 # null = TTS_VOICE_NAME; otherwise must be in TTS_ALLOWED_VOICES (load check added here)
  speaking_rate: 1.0
  pronunciations:                 # new, optional, console-editable, max 50 entries
    "Nguyen": "Win"
    "Wojcik": "Voy-chick"
    "Brightsmile": "Bright smile"
```
Load check: keys 1–40 chars, letters/spaces/`'`/`-`/`.` only; values 1–60 chars, letters, spaces, hyphens and apostrophes only (no digits, no markup). An invalid entry rejects the config save (P1-19 behaviour).

### Speech-to-Text (`backend/app/integrations/speech/stt.py`)
```python
class SttPartial(NamedTuple):
    utterance_id: int
    text: str
    stable: bool                 # stability ≥ 0.8 where the model reports it (Verify)
    ts_ms: int

class SttFinal(NamedTuple):
    utterance_id: int
    text: str                    # "" if nothing recognised
    confidence: float | None     # not all models return it (Verify)

class SpeechToText(Protocol):
    async def open(self, utterance_id: int, hints: PhraseHints) -> "SttStream": ...

class SttStream(Protocol):
    async def send(self, pcm16: bytes) -> None: ...          # 20 ms frames from P3-02, pre-roll first
    async def finish(self) -> SttFinal: ...                  # half-close; waits ≤ 700 ms for the final
    def partials(self) -> AsyncIterator[SttPartial]: ...
    async def abort(self) -> None: ...                       # reconnect / discard

class SttError(Exception): ...          # subclasses: SttUnavailable, SttTimeout, SttQuota
```
**Lifecycle (DECISIONS #230):** `speech_start` → `open()` (gRPC channel already warm) → pre-roll and frames → each partial goes to `TurnDetector.on_partial()` and to the widget as `transcript` → endpoint → `finish()` → final text → `UserTurn`. If the final is empty (or only punctuation) → `utterance_discarded noise`. If the final takes longer than 700 ms after half-close, the last partial is used as the final (logged `stt.final_fallback`).

Recognition config (sketch; field names **Verify** against the V2 API):
```python
StreamingRecognitionConfig(
    config=RecognitionConfig(
        explicit_decoding_config=ExplicitDecodingConfig(encoding=LINEAR16, sample_rate_hertz=16000, audio_channel_count=1),
        model=settings.STT_MODEL, language_codes=["en-US"],
        features=RecognitionFeatures(enable_automatic_punctuation=True, profanity_filter=False),
        adaptation=SpeechAdaptation(phrase_sets=[AdaptationPhraseSet(inline_phrase_set=hints.to_phrase_set())]),
    ),
    streaming_features=StreamingRecognitionFeatures(interim_results=True),
)
recognizer = f"projects/{PROJECT}/locations/{STT_LOCATION}/recognizers/_"
```
Authentication is the Cloud Run service account (no API keys). Nothing in the code sets any logging or data-sharing option.

### Phrase hints (`backend/app/integrations/speech/hints.py`, DECISIONS #231)
```python
class PhraseHints(BaseModel):
    phrases: list[str]           # ≤ 500 total (Verify the API limit)
    classes: list[str] = []      # class tokens, e.g. "$OOV_CLASS_DIGIT_SEQUENCE", "$MONTH" (Verify names)

def build_hints(clinic: ClinicConfig, providers: list[Provider], state: str, flow: FlowDefinition) -> PhraseHints: ...
```
| Source | Example | When |
|---|---|---|
| `speech/phrases/dental_en.yaml` (≈ 150 phrases, versioned) | cleaning, crown, filling, root canal, wisdom tooth, hygienist, Invisalign, x-ray, new patient exam, reschedule | Always |
| Clinic | clinic name, `clinic_info.insurers_accepted`, town name | Always |
| Providers (P1-15 cache) | "Dr. Patel", "Doctor Priya Patel", preferred names; hygienists' first names | Always |
| State `collects` (P2-01 flow YAML) | `email`: "at", "dot com", "gmail", "yahoo", "outlook"; `phone`, `dob`, `zip`: digit and month classes | Only in those states |
| Spelling mode (P3-09) | Letter names ("ess", "double-u"), NATO words, "as in", "dash", "apostrophe", "capital" | While `spelling_field` is set |

Never included: the patient's name, phone, DOB or any other slot value (spelling mode in P3-09 handles names). Hints are built once per utterance from cached data (< 1 ms) and not logged.

### Transcript message (protocol v2 addition, DECISIONS #230)
| Direction | `type` | Fields | Meaning |
|---|---|---|---|
| S→C | `transcript` | `utterance_id`, `text`, `final: bool` | Partial (`final=false`, at most every 150 ms) or final transcript |

The final transcript is shown in the chat as the patient's message (same bubble as typed text, marked with a mic icon by P3-11). If the utterance is discarded, the client removes any partial bubble.

### Text-to-Speech (`backend/app/integrations/speech/tts.py`)
```python
class TextToSpeech(Protocol):
    async def speak(self, reply_id: int, sentences: AsyncIterator[str], voice: VoiceChoice) -> AsyncIterator[bytes]: ...
    async def cancel(self, reply_id: int) -> None: ...   # P3-06 barge-in; stops within 50 ms

class VoiceChoice(NamedTuple):
    name: str                    # in TTS_ALLOWED_VOICES
    language_code: str           # always "en-US"
    speaking_rate: float         # clinic voice.speaking_rate (ignored if the voice does not support it; Verify)
    sample_rate_hz: int

class TtsError(Exception): ...          # TtsUnavailable, TtsTimeout, TtsQuota
```
- **Streaming voices** (`TTS_STREAMING_VOICES`): one `StreamingSynthesize` call per reply; each normalized sentence is written as it arrives; audio chunks are passed straight to `VoiceSession.play()`.
- **Other voices:** `SynthesizeSpeech` per sentence (LINEAR16), sentence N+1 requested while N plays.
- **Glue** (`backend/app/voice/speak.py`): replies to typed turns are never spoken, even with voice on (P3-11, DECISIONS #245); a typed message sent during playback is handled like a confirmed barge-in (P3-06). For each reply on a VOICE turn, take P2-04's `ReplyChunk`s, run `SpeechNormalizer.normalize(chunk.text)`, feed `speak()`, then `play()`. Text chunks still go to the widget unchanged as `reply_chunk`.
- **Deadline:** no first audio within 1.5 s → `TtsTimeout`.

### Speech normalizer (`backend/app/integrations/speech/normalize.py`, DECISIONS #231)
Pure function, deterministic, idempotent (normalizing twice gives the same text). Runs on every sentence before TTS, after the P2-04 guard.
```python
class SpeechNormalizer:
    def __init__(self, pronunciations: dict[str, str], clinic_tz: str): ...
    def normalize(self, text: str) -> str: ...
    def digits(self, s: str) -> str: ...      # "5035550123" → "5-0-3, 5-5-5, 0-1-2-3"
    def spell(self, s: str) -> str: ...       # "Kaur" → "K, A, U, R" (used by P3-09)
```
| Rule | Input | Output |
|---|---|---|
| Phone numbers (E.164 or US formats) | `(503) 555-0123` | `5-0-3, 5-5-5, 0-1-2-3` |
| Case references | `CB-4F7K2Q` | `C, B, 4, F, 7, K, 2, Q` |
| ZIP codes | `97201` | `9-7-2-0-1` |
| Times | `2:30 PM`, `10:00 AM` | `two thirty PM`, `ten AM` |
| Dates | `Tue, Mar 4` | `Tuesday, March fourth` |
| Titles | `Dr. Patel` | `Doctor Patel` |
| Money | `$120` | `120 dollars` |
| Clinic pronunciations | `Dr. Nguyen` | `Doctor Win` (whole-word, case-insensitive) |
| Symbols | `&`, `/`, `#` | `and`, `or`, `number` |
| Already normalized | `5-0-3, 5-5-5, 0-1-2-3` | unchanged |

No SSML is generated (works with every voice). If a later voice needs pauses, P3-14 may add markup behind the same function.

### Failure behaviour
| Error | Behaviour |
|---|---|
| `SttUnavailable` / `SttTimeout` on `open()` or mid-stream | Utterance discarded; template `voice_missed_that` spoken (if TTS works) and shown; 3 STT failures in 2 min → `voice_stopped stt_unavailable` and the chat shows "Voice isn't working right now. You can keep typing." |
| `SttQuota` / `TtsQuota` | As unavailable; prod alert **A-V1** (ticket, P1-07 alerting): any quota error in 10 min |
| `TtsUnavailable` / `TtsTimeout` | Text already shown; widget shows a small note "Audio unavailable for this reply"; next reply tries again; 3 failures in 2 min → `voice_stopped tts_unavailable` (text continues) |
| Config `voice.tts_voice` not in the allow-list (should be blocked at save) | Default voice used; `voice.config_invalid` error log |

### Logs and metrics (no PHI, no audio, no transcript text)
| Item | Fields |
|---|---|
| `stt.utterance` | `model`, `audio_ms`, `partials`, `final_chars`, `empty`, `final_fallback` |
| `stt.error` / `tts.error` | `error_class`, `grpc_code` |
| `tts.reply` | `voice`, `streaming`, `sentences`, `chars`, `audio_ms` |
| `stage_timer` | `STT_FIRST_PARTIAL` (from `speech_start`), `STT_FINAL` (from endpoint), `TTS_FIRST_AUDIO` (from first sentence to first chunk) |
| Counters | `dai.stt.requests`, `dai.tts.chars` (cost tracking) |
Never logged: audio, partial or final transcript text, normalized sentences, phrase hints.

## 7. Implementation guide
1. **Config and policy checks:** env settings, startup validation, P1-19 load check for `voice.tts_voice` and `voice.pronunciations`.
2. **STT client:** gRPC client with a warm channel created at app start (keepalive pings); `open()` / `send()` / `finish()` / `abort()`; mapping of gRPC errors to `SttError`s.
3. **Phrase hints:** `dental_en.yaml`, `build_hints()`, per-state map tested against the P2-01 flow YAML.
4. **Wire into P3-02:** `speech_start` → open with pre-roll; frames → `send`; partials → `on_partial` and `transcript`; endpoint → `finish` → `UserTurn`.
5. **Normalizer:** rules table, unit tests with ≥ 60 cases, idempotence property test.
6. **TTS client:** streaming and per-sentence paths, `cancel()`, `speak.py` glue with P2-04 and `play()`.
7. **Failure paths, metrics and alert A-V1.**
8. **CI checks:** grep test that `backend/app/integrations/speech/` never references logging/data-sharing options or API keys; static check that no transcript text reaches the logger (P1-07 log capture).
9. **Integration tests in dev** with the P3-01 synthetic audio set; WER report on the 30 utterances with and without hints.
10. **Docs** `docs/voice/speech.md` (models, hints, normalizer rules, how to add a pronunciation). Notify P3-06 (`cancel`), P3-09 (`digits`, `spell`), P3-11 (`transcript`), P3-14 (metrics), P4-11 (`voice.pronunciations`).

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| Patient says "five oh three" | STT returns "503" or "five oh three"; P2-05 extraction normalises; read-back confirms |
| Patient spells an email "j dot smith at gmail dot com" | Email-state hints help; P2-05 converts; read-back (P3-09) confirms |
| Provider name misheard ("Dr. Petal") | Provider hints; P2-16 matches names fuzzily; confirmation card shows the real name |
| Background noise produces a stray word ("uh") | Final with only a filler → treated as empty → discarded |
| Very long utterance (45 s cap) | Stream still within limits (Verify the per-stream limit is well above 45 s) |
| Endpoint fires but the final is late | Last partial used after 700 ms; logged |
| Barge-in while TTS streams | P3-06 calls `cancel()`; stream closed, no further `play()` chunks |
| Reply has a confirmation card | `voice` template variant spoken; card shown in chat (DECISIONS #174) |
| LLM writes a phone number in a sentence | Guard G3 normally blocks unrevealed digits; if allowed (clinic phone), normalizer reads it digit by digit |
| Clinic changes `voice.tts_voice` mid-session | Session keeps its pinned config (P2-01); new sessions use the new voice |
| Pronunciation key contains a provider's surname that is also a common word | Whole-word match only; the clinic tests it in the console preview (P4-11) |
| Streaming TTS unsupported for the configured voice | Per-sentence path used automatically (from `TTS_STREAMING_VOICES`) |

## 9. Security, HIPAA and PHI
- **PHI handled:** patient voice audio and transcripts (names, DOB, phone, email, address, symptoms) go to Speech-to-Text; reply text (may include first name, date, time, provider) goes to Text-to-Speech. Both are Google Cloud services under the BAA, US locations, service-account auth (P0-05, P0-06, data flows F03/F04 in P0-14).
- **Data logging:** never enabled; the code has no option for it; CI grep check; P0-06 checks the project setting.
- **Never stored or logged:** audio, transcripts, normalized text, phrase hints. Transcripts live only in memory and in the P2-01 turn (same handling as typed text; transcript retention per `privacy.transcript_retention_days`).
- **Phrase hints contain no patient data** (clinic and provider names only).
- **Pronunciations** are clinic-entered words (provider and place names), not PHI; validated against markup injection.

## 10. Testing
```bash
cd backend && pytest tests/unit/speech -q                       # normalizer, hints, policy checks, fake clients
pytest tests/integration/speech -q -m dev_gcp                    # real STT/TTS in dev with synthetic audio
python scripts/voice/wer_report.py --audio spikes/p3-01-voice-latency/audio --hints on,off
```
| # | Case | Expected |
|---|---|---|
| T1 | Startup with `TTS_LANGUAGE_CODE=en-GB` or a voice outside the allow-list | App refuses to start |
| T2 | Clinic config with `tts_voice` not allowed, or an invalid pronunciation | Save rejected |
| T3 | Normalizer rules table (≥ 60 cases) | Exact outputs; idempotent |
| T4 | Phone read-back | Digits one by one, grouped 3-3-4 |
| T5 | Hints per state | Email words only in email states; digit classes only in phone/DOB/ZIP states; no slot values ever |
| T6 | STT first partial (dev, P3-01 set) | ≤ 300 ms p50 from speech start |
| T7 | STT final after endpoint | ≤ 300 ms p50; fallback to last partial after 700 ms |
| T8 | WER with vs without hints on dental and provider phrases | Hints not worse overall; report attached |
| T9 | TTS first audio (dev, streaming voice) | ≤ 250 ms p50 |
| T10 | Per-sentence fallback path | Audio continuous between sentences (gap ≤ 150 ms) |
| T11 | `cancel()` during streaming | No chunk after 50 ms |
| T12 | STT and TTS failure paths | Messages and `voice_stopped` as specified; text keeps working |
| T13 | No logging | CI grep finds no data-logging option or API key; log capture contains no transcript text |
| T14 | `transcript` messages | Partials ≤ every 150 ms; final matches the `UserTurn` text |

## 11. Acceptance criteria
- [ ] Partials arrive in near real time: first partial ≤ 300 ms p50 from speech start (T6)
- [ ] TTS first audio ≤ 250 ms p50 on the default voice (T9)
- [ ] Phone numbers and reference codes are read digit by digit (T3, T4)
- [ ] Data logging is confirmed off in code and config; no API keys (T13)
- [ ] Only `en-US` and allow-listed female voices can run (T1, T2)
- [ ] Phrase hints include dental terms and provider names and never patient data (T5)
- [ ] STT or TTS failure never breaks the text chat (T12)

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI; dev integration run and WER report linked in the PR
- [ ] PR reviewed (HIPAA review: labelled `phi`)
- [ ] No PHI in logs
- [ ] `docs/voice/speech.md` written; P1-19 config docs updated (`voice.pronunciations`)
- [ ] P3-06, P3-09, P3-11, P3-14 and P4-11 notified

## 13. Hand-off
| Consumer | What they can rely on |
|---|---|
| P3-06 Barge-in | `TextToSpeech.cancel(reply_id)`; stable partials (`SttPartial.stable`) for speculative LLM calls |
| P3-09 Read-back | `SpeechNormalizer.digits()` and `spell()`; email-state hints |
| P3-11 Transcript UI | `transcript` messages (partial and final) |
| P3-14 Tuning | STT/TTS stage timers, `final_fallback` rate, WER script |
| P4-11 Console | `voice.pronunciations` key with its validation rules |

## 14. Open questions
| # | Question | Recommended answer | Owner |
|---|---|---|---|
| 1 | Should low STT confidence trigger a "could you repeat that?" | No: extraction and read-back already catch errors; P3-14 may revisit with data. | Tech lead |
| 2 | Should the profanity filter be on? | No: we need the exact words for emergency and complaint detection; nothing is logged. | Product owner |
| 3 | Should the console offer a "play preview" for pronunciations? | Yes, in P4-11, using the same `TextToSpeech` with a fixed sentence. | Product owner |

## 15. References
- Plan: §3.2, §4.4, §5, §11
- DECISIONS: #73, #175, #222, #224, #226, #228, #230, #231, #232
- Related tasks: P0-05, P0-06, P0-14, P1-07, P1-15, P1-19, P2-01, P2-04, P2-05, P3-01, P3-02, P3-06, P3-09, P3-11, P3-14, P4-11
- Speech-to-Text V2 streaming: <https://docs.cloud.google.com/speech-to-text/v2/docs/streaming-recognize>
- Model adaptation: <https://docs.cloud.google.com/speech-to-text/v2/docs/adaptation-model>
- Text-to-Speech streaming: <https://docs.cloud.google.com/text-to-speech/docs/create-audio-text-streaming>
