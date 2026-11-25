---
id: P3-02
title: Audio transport (WebSocket) browser <-> backend, with VAD and endpointing
milestone: P3
epic: E3.1
size: L
labels: area:voice, area:frontend, type:feature, phi
depends_on: P3-01, P2-25, P1-13, P1-07, P2-01
status: approved
---

# P3-02: Audio transport (WebSocket) browser <-> backend, with VAD and endpointing

## 1. Summary
Carry the patient's voice from the browser to the backend and the assistant's voice back, over the same session WebSocket the text chat already uses, and decide when the patient has finished speaking. This task absorbs **P3-04 (VAD + endpointing: client VAD, Silero on the server, semantic turn)**.

| Part | What it does |
|---|---|
| Capture | Mic with browser echo cancellation, noise suppression and auto gain; AudioWorklet → 16 kHz mono PCM16, 20 ms frames; client VAD sends only speech (with 300 ms pre-roll) |
| Transport | Protocol v2 on the P2-25 socket: binary audio frames both ways plus `voice_start`, `voice_stop`, `speech_start`, `speech_end`, `playback_*` control messages |
| Playback | Jitter buffer for TTS audio, instant `flush` (for barge-in, P3-06) |
| Endpointing | Server Silero VAD is authoritative; rule-based adaptive silence (300 / 800 / 1200 ms) stands in for semantic turn detection |
| Lifecycle | Hands-free mode after "Start voice", mute, auto-stop after 60 s silence, reconnect that resumes voice |

Done means:
- a 10-minute voice session runs without drops (including a forced reconnect);
- end of speech → endpoint ≤ 500 ms p50;
- reconnects never duplicate a turn;
- audio is never stored.

## 2. Why this matters
Voice is half the product (plan §2). Every voice stage after this one — STT, LLM, TTS, barge-in — depends on clean frames arriving on time, and on a good endpoint decision: too early and patients are cut off mid-phone-number; too late and the AI feels slow (plan §4.4 target ≤ 300–500 ms). Cloud Run cuts WebSockets at the request timeout and may move a reconnect to another instance (DECISIONS #72), so resuming has to be built in. Pilot targets: voice-to-voice ≤ 1.5 s p50, critical-field accuracy ≥ 98% after read-back.

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P3, Voice Pipeline & Avatar**.
- **AudioWorklet:** the browser API for processing audio off the main thread with low latency. <https://developer.mozilla.org/en-US/docs/Web/API/AudioWorklet>.
- **getUserMedia constraints:** `echoCancellation`, `noiseSuppression`, `autoGainControl` ask the browser to clean the mic signal; echo cancellation stops the assistant's own voice from being heard as the patient. <https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia>.
- **VAD (voice activity detection):** decides speech vs silence per frame. Client side we use a lightweight browser VAD (**Proposed:** `@ricky0123/vad-web`, Silero in ONNX/WASM; **Verify** licence and bundle size) only to gate sending; the server's Silero decision is the one that counts.
- **Endpointing:** deciding the turn is over. Plain silence timeouts cut people off when they pause ("my number is 503... 555..."), so the silence needed grows when the words so far look unfinished.
- **What already exists:**
  - **P3-01** (spike): ADR 0003 (Pipecat yes/no), measured Silero settings, endpoint latency and cut-off rate, `Stage.ENDPOINT_DETECTED`, `Stage.BARGE_IN_STOP`.
  - **P2-25** (approved): session WebSocket protocol v1 (`auth`, `user_turn`, `ping` / `ready`, `turn_ack`, `reply_chunk`, `typing`, `error`, `session_expired`), reconnect with backoff, `voice_enabled` flag, iframe `allow` attribute.
  - **P1-13** (approved): WebSocket auth (first message), close codes 4401 / 4408 / 4429, `voice_concurrent` limit (3 voice sockets per IP).
  - **P2-01** (approved): `UserTurn{text, channel, client_turn_id, choice_id}`, `channel_switched` keeps the state, duplicate `client_turn_id` ignored.
  - **P0-14** (approved): ADR 0004 WebSocket audio, 16 kHz PCM, 20 ms frames; Cloud Run `api` timeout 3600 s.

## 4. Scope
**In scope**
- Browser capture, client VAD gating, framing, sending; playback with jitter buffer and flush.
- Protocol v2 (additive to P2-25 v1) and its server handling.
- `AudioTransport`, `VoiceSession` and `TurnDetector` server interfaces, implemented with Pipecat or custom code per ADR 0003.
- Server Silero VAD and the adaptive-silence endpointing rules.
- Hands-free lifecycle (start, mute, auto-stop), permissions UX, reconnect and resume.
- Load/soak test for a 10-minute session; endpoint latency measurement.

**Out of scope** (and which task covers it)
- Speech-to-Text and Text-to-Speech services, phrase hints, SSML → P3-03
- Barge-in (stop TTS, cancel LLM), filler phrases, speculative LLM → P3-06 (this task provides `flush` and `speech_start`)
- Read-back and spelling mode → P3-09 (it sets the endpoint profile `spelling`)
- Avatar, live transcript, voice↔text UI switching → P3-11
- Dashboards and tuning → P3-14

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P3-01 | ADR 0003, Silero settings | Build behind the interfaces in §6; start with the custom implementation (it exists in the spike) |
| P3-03 | STT partials (for the adaptive rule) and TTS audio | `FakeStt` emits scripted partials; `FakeTts` emits a sine tone per sentence |
| P2-25 (approved) | Socket client and server | Extend both; protocol v1 tests must keep passing |
| P1-13 (approved) | Auth, limits | As specified |

## 6. Interface contract

### Protocol v2 (additive to P2-25; DECISIONS #226)
`auth` gains `protocol: 2`. A v1 client never receives v2 messages.

**Binary frames** (WebSocket binary type):
```
byte 0      : kind   0x01 = mic audio (client→server), 0x02 = TTS audio (server→client)
bytes 1-4   : seq    uint32 big-endian, per direction, per voice stream
bytes 5-8   : utterance_id (client→server) / reply_id (server→client), uint32
bytes 9..   : payload  PCM16 little-endian mono
              client→server: 16 kHz, exactly 320 samples (20 ms) per frame
              server→client: TTS sample rate announced in `playback_start` (e.g. 24000), any length ≤ 100 ms
```

**JSON control messages**
| Direction | `type` | Fields | Meaning |
|---|---|---|---|
| C→S | `voice_start` | `sample_rate: 16000`, `client_vad: true` | Enter voice mode; counted against `voice_concurrent` (over the limit → `voice_stopped limit`, socket stays open for text) |
| C→S | `voice_stop` | `reason: "user" \| "idle" \| "error"` | Leave voice mode (text continues) |
| C→S | `speech_start` | `utterance_id`, `preroll_ms: 300` | Client VAD heard speech; frames for this utterance follow |
| C→S | `speech_end` | `utterance_id`, `frames_sent` | Client VAD silence after speech (a hint; server decides) |
| C→S | `mute` | `muted: bool` | Mic muted / unmuted |
| C→S | `playback_ended` | `reply_id`, `played_ms` | The client finished (or flushed) playing a reply |
| S→C | `voice_ready` | `endpoint_profile` | Server accepted voice mode |
| S→C | `endpoint` | `utterance_id`, `turn_id` | Server decided the turn ended; the turn is now processed like a `user_turn` |
| S→C | `utterance_discarded` | `utterance_id`, `reason: "too_short" \| "noise" \| "reconnect"` | No turn created |
| S→C | `playback_start` | `reply_id`, `turn_id`, `sample_rate` | TTS audio for this reply follows |
| S→C | `playback_flush` | `reply_id` | Stop and drop buffered audio now (used by P3-06) |
| S→C | `voice_stopped` | `reason` | Server ended voice mode (e.g. `idle`, `limit`, `session_expired`) |
| C→S / S→C | `playback_paused` / `playback_pause`, `playback_resume` | `reply_id` (+ `played_ms`, `utterance_id` C→S) | Added by P3-06 (DECISIONS #234): barge-in pause and resume; `playback_start` gains `interruptible`, `utterance_discarded` gains reason `backchannel`; `AudioPlayer` gains `pause()` / `resume()` |
| C→S | `playback_started` / `net_stats` | `reply_id`, `utterance_id`, `filler`, `v2v_ms`, `output_latency_ms` / `rtt_ms` | Added by P3-14 (DECISIONS #247): voice-to-voice on the browser clock; RTT every 30 s. Endpoint silences become env vars `ENDPOINT_BASE_MS`, `ENDPOINT_UNFINISHED_MS`, `ENDPOINT_DATA_ENTRY_MS`, `ENDPOINT_SPELLING_MS` (defaults unchanged) |
| S→C | `transcript` | `utterance_id`, `text`, `final` | Added by P3-03 (DECISIONS #230): partial (≤ every 150 ms) and final STT transcript; reasons `stt_unavailable` / `tts_unavailable` also added to `voice_stopped` |

Text `reply_chunk`s still arrive in voice mode (the chat window shows them, DECISIONS #174); `playback_*` carries the matching audio.

### Browser modules (`frontend/lib/voice/`)
```ts
export class MicCapture {               // getUserMedia({audio:{echoCancellation:true, noiseSuppression:true, autoGainControl:true, channelCount:1}})
  start(): Promise<void>;               // throws MicPermissionDenied | MicUnavailable
  stop(): void;
  setMuted(m: boolean): void;
  onFrame(cb: (pcm16: Int16Array) => void): void;   // 16 kHz, 320 samples, from resampler-worklet.js
}
export class ClientVad {                // @ricky0123/vad-web (Proposed; Verify), thresholds from config
  onSpeechStart(cb: () => void): void; onSpeechEnd(cb: () => void): void;
}
export class AudioSender {              // ring buffer keeps the last 300 ms; on speech_start flushes pre-roll then streams;
  constructor(sock: ChatSocket);        // stops 400 ms after client speech_end unless speech resumes
}
export class AudioPlayer {              // AudioWorklet player with a 60–120 ms jitter buffer
  begin(replyId: number, sampleRate: number): void;
  push(replyId: number, pcm16: Int16Array): void;
  flush(): void;                        // < 20 ms to silence
  onEnded(cb: (replyId: number, playedMs: number) => void): void;
}
```
**Added by P3-11 (DECISIONS #270):** `MicCapture.levelNode(): AudioNode` and `AudioPlayer.levelNode(): AudioNode` expose a read-only node in the same `AudioContext` (mic after processing; player output) so the voice orb can measure loudness locally. Nothing is sent over the socket.

The iframe needs `allow="microphone"` (P2-25's `embed.js` switches it when `voice_enabled` is true); the clinic page must not block microphone via its own Permissions-Policy (documented in `embedding.md`).

### Server interfaces (`backend/app/voice/`)
```python
class AudioFrame(NamedTuple):
    utterance_id: int
    seq: int
    pcm16: bytes            # 640 bytes = 20 ms at 16 kHz

class VoiceSession(Protocol):            # one per socket in voice mode
    async def on_frame(self, f: AudioFrame) -> None: ...
    async def on_control(self, msg: dict) -> None: ...
    async def play(self, reply_id: int, turn_id: str, sample_rate: int, chunks: AsyncIterator[bytes]) -> None: ...
    async def flush(self, reply_id: int) -> None: ...                  # P3-06
    def set_endpoint_profile(self, profile: EndpointProfile) -> None: ...   # P3-09 / flows

class TurnDetector(Protocol):
    def on_vad(self, is_speech: bool, ts_ms: int) -> None: ...
    def on_partial(self, text: str, ts_ms: int) -> None: ...           # from P3-03 STT partials
    def endpoint_due(self, now_ms: int) -> bool: ...

EndpointProfile = Literal["normal", "data_entry", "spelling"]
```
Implementation per ADR 0003: Pipecat (`FastAPIWebsocketTransport` with a custom serializer for our frame format, `SileroVADAnalyzer`, a `TurnDetector` processor) or custom asyncio (`silero-vad` ONNX). Both expose the same interfaces; the rest of the backend never imports Pipecat directly.

### Endpointing rules (DECISIONS #227)
Server Silero (16 kHz, 32 ms windows; thresholds from P3-01) tracks speech; after speech stops, the turn ends when silence reaches the **required silence**:

| Condition (first match wins) | Required silence |
|---|---|
| Profile `spelling` (P3-09 spelling mode) | 1500 ms |
| Profile `data_entry` (states collecting `phone`, `dob`, `first_name`, `last_name`, `email`, `zip`, `address`) | 1200 ms |
| Latest STT partial looks unfinished: ends with a conjunction or filler (`and`, `or`, `but`, `so`, `because`, `um`, `uh`, `like`), ends mid-number (an odd count of digit groups for a phone, a month without a day), or ends with "my", "the", "at", "on", "is" | 800 ms |
| Otherwise | 300 ms |

- **Hard cap:** a single utterance longer than 30 s is ended at the next 300 ms silence (or force-ended at 45 s).
- **Too short:** speech < 200 ms with no STT text → `utterance_discarded` (`too_short`), e.g. a cough.
- The profile comes from the P2-01 state: P2-01's state YAML `collects` list decides `data_entry` (a small map in `voice/profiles.py`, tested against the YAML).
- When the endpoint fires: `endpoint` message, then a `UserTurn(text=<P3-03 final transcript>, channel="VOICE", client_turn_id=f"v-{session_id}-{utterance_id}")` goes to P2-01 — the same path as typed text.
- No ML semantic-turn model in the MVP; P3-14 may evaluate one (e.g. Pipecat smart-turn) against these rules with the P3-01 audio set.

### Lifecycle (DECISIONS #228)
| Event | Behaviour |
|---|---|
| Patient taps "Start voice" | Permission prompt (first time) → `voice_start` → `voice_ready`; mic indicator on; hands-free (no push-to-talk) |
| Mute button | `mute true`: capture stops sending; indicator shows muted; TTS keeps playing |
| 60 s with no speech and no assistant audio | Client sends `voice_stop idle`; the chat shows "Voice paused. Tap the mic to talk again." Text input stays available |
| Patient taps "Stop voice" / types | `voice_stop user`; typed messages work anytime (P3-11 handles the UI switch) |
| Permission denied | Message "Microphone access is blocked. You can keep typing, or allow the microphone in your browser settings." No retry loop |
| Tab hidden (mobile background) | Mic is stopped by the browser on some platforms → `voice_stop error`; resume needs a tap |
| Session expired | `voice_stopped session_expired` then P2-25 behaviour |

### Reconnect (DECISIONS #228)
- On socket loss in voice mode: the client stops sending, keeps the mic open (muted send), reconnects with P2-25 backoff, sends `auth (resume)` then `voice_start` automatically.
- Any utterance that was in flight is dropped (`utterance_discarded reconnect` server-side; client side it is simply abandoned). After `voice_ready` the assistant says the template `voice_missed_that`: "Sorry, I missed that. Could you say it again?" (spoken and shown).
- A reply that was playing is not resumed; its text is already in the chat (`reply_chunk`s).
- `client_turn_id` = `v-{session_id}-{utterance_id}` makes server-side duplicates impossible (P2-01).
- Cloud Run's 60-minute cut is handled the same way; voice sessions longer than 55 min get a proactive reconnect at a silence moment.

### Logs and metrics (no PHI, no audio)
| Item | Fields |
|---|---|
| `voice.start` / `voice.stop` | `reason`, `duration_s` |
| `voice.endpoint` | `profile`, `rule` (`base` / `unfinished` / `data_entry` / `spelling` / `cap`), `silence_ms`, `speech_ms` |
| `voice.utterance_discarded` | `reason` |
| `voice.reconnect` | `close_code`, `gap_ms` |
| `stage_timer(Stage.ENDPOINT_DETECTED)` | ms from Silero end-of-speech to endpoint |
| `dai.voice.frames_late` (counter) | frames arriving > 200 ms late |
Never logged or stored: audio frames, transcripts (P3-03 handles text the same way as typed text).

## 7. Implementation guide
1. **Protocol v2 types** in `ws_protocol.py` and `protocol.ts`; extend the schema-equality check (P2-25).
2. **Browser capture** (`resampler-worklet.js`: 48 kHz → 16 kHz with a low-pass filter; framing to 320 samples), `ClientVad`, `AudioSender` with ring-buffer pre-roll.
3. **Player** worklet with jitter buffer and `flush`.
4. **Server** `VoiceSession` and `TurnDetector` behind interfaces; implementation per ADR 0003; profile map from the state YAML.
5. **Endpoint integration** with P3-03 (final transcript) and P2-01 (`UserTurn` with `channel="VOICE"`).
6. **Lifecycle and reconnect** in the widget; `voice_missed_that` template (P2-04).
7. **Tests** (§10), including a 10-minute soak in staging and endpoint latency with the P3-01 audio set in replay mode.
8. **Docs** `docs/voice/transport.md` (protocol v2, frame format, endpoint rules). Notify P3-03, P3-06, P3-09, P3-11, P3-14.

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| Patient pauses while saying a phone number | `data_entry` profile (1200 ms) or "unfinished" rule (800 ms) keeps the turn open |
| Background TV | Client VAD may send it; server Silero + STT produce no text → discarded as `noise` |
| Assistant voice leaks into the mic | Browser echo cancellation; frames during playback still sent (needed for barge-in), P3-06 decides |
| Bluetooth headset switches the sample rate | Resampler adapts to `AudioContext.sampleRate`; frames stay 16 kHz |
| Frames arrive out of order or late | Server orders by `seq` within 100 ms; later frames dropped and counted |
| Socket drops mid-utterance | Utterance dropped; reconnect; "Sorry, I missed that…" |
| `voice_concurrent` exceeded (4 tabs from one IP) | Server replies `voice_stopped limit` to `voice_start`; the socket stays open, so text continues |
| Mobile Safari: AudioContext suspended until a tap | Start only from the "Start voice" tap handler |
| 10-minute continuous session | No drops; memory stable (buffers bounded) |
| Very long monologue | 30 s soft cap, 45 s hard cap |
| Muted patient types instead | Text turn; voice mode stays on unless they stop it |

## 9. Security, HIPAA and PHI
- **PHI handled:** the patient's voice (biometric-like and content PHI) in transit only: browser → TLS WebSocket → Cloud Run memory → STT (P3-03, BAA-covered). Not written to disk, logs, Redis or any storage (plan §5: raw audio not stored).
- **Client gating** sends only detected speech (plus 300 ms pre-roll), so room audio during silence isn't transmitted.
- **Mic indicator** always visible while capturing; mute stops sending immediately.
- **Limits:** `voice_concurrent` (P1-13); max frame rate 60 frames/s per socket (excess dropped, logged).
- **No third parties:** the client VAD model files are self-hosted (no CDN).

## 10. Testing
```bash
cd frontend && pnpm test -- voice          # worklets (via node test harness), sender pre-roll, player flush
cd backend && pytest tests/unit/voice -q   # protocol, turn detector rules, profiles vs state YAML
python scripts/voice/replay_endpointing.py --audio spikes/p3-01-voice-latency/audio --target dev   # endpoint latency
pnpm e2e -- --grep voice-soak              # 10-minute session with fake mic (Chromium --use-file-for-fake-audio-capture)
```
| # | Case | Expected |
|---|---|---|
| T1 | Frame format | 20 ms, 320 samples, correct header, seq increments |
| T2 | Pre-roll | First 300 ms before speech start are included |
| T3 | Endpoint rules table | Each condition gives the right silence; cap works |
| T4 | Endpoint latency on the P3-01 set (clean) | ≤ 500 ms p50 from end of speech |
| T5 | Cut-off rate on long/paused utterances | ≤ 5% cut early (report vs P3-01 baseline) |
| T6 | Profile map | Every `collects` slot of type phone/DOB/name/email/ZIP/address maps to `data_entry` |
| T7 | 10-minute soak in staging | No drops; memory and buffer sizes bounded |
| T8 | Forced reconnect mid-utterance and at the 55-min proactive reconnect | Voice resumes; one "missed that"; no duplicate turn |
| T9 | Permission denied | Message shown; text works |
| T10 | `voice_concurrent` over limit | `voice_stopped limit`; text continues |
| T11 | Player flush | Silence within 20 ms |
| T12 | Idle auto-stop | Voice paused after 60 s; mic tap resumes |
| T13 | No audio persisted | Static check: no file writes / storage calls in `voice/`; log capture has no audio or text |
| T14 | Protocol v1 client still works | P2-25 tests green |

## 11. Acceptance criteria
- [ ] Stable 10-minute session without drops, including a forced reconnect (T7, T8)
- [ ] End of speech → endpoint ≤ 500 ms p50 on clean audio, with ≤ 5% early cut-offs (T4, T5)
- [ ] Reconnect resumes voice automatically, never duplicates a turn and asks the patient to repeat (T8)
- [ ] Only detected speech is sent; audio is never stored or logged (T2, T13)
- [ ] Hands-free start, mute, idle auto-stop and permission errors behave as specified (T9, T12)
- [ ] Text chat keeps working in every voice failure case (T9, T10, T14)

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI; soak run linked in the PR
- [ ] PR reviewed (HIPAA review: labelled `phi`)
- [ ] No PHI in logs
- [ ] `docs/voice/transport.md` written; P2-25 protocol docs updated to v2
- [ ] P3-03, P3-06, P3-09, P3-11 and P3-14 issues notified

## 13. Hand-off
| Consumer | What they can rely on |
|---|---|
| P3-03 STT/TTS | Ordered 16 kHz frames per utterance; `TurnDetector.on_partial`; `VoiceSession.play()` for TTS chunks with `playback_start` |
| P3-06 Barge-in | `speech_start` during playback, `flush()` / `playback_flush`, `playback_ended.played_ms` |
| P3-09 Read-back | `set_endpoint_profile("spelling")` |
| P3-11 Avatar / switching | Voice lifecycle events and mic state |
| P3-14 Tuning | Endpoint metrics per rule, frames-late counter |

## 14. Open questions
| # | Question | Recommended answer | Owner |
|---|---|---|---|
| 1 | Should the endpoint silence values be clinic-configurable? | No: product constants, tuned in P3-14 with data. | Tech lead |
| 2 | Should we switch to Opus if mobile networks struggle? | Only if P3-14 shows uplink problems; PCM stays for the MVP. | Tech lead |
| 3 | Should voice mode show a short "I'm listening" earcon? | No sound; the visual mic indicator and avatar state (P3-11) are enough. | Product owner |

## 15. References
- Plan: §3.1, §3.2, §4.4, §5, §11
- DECISIONS: #72, #73, #122, #174, #209, #222, #226, #227, #228
- Related tasks: P0-14, P1-07, P1-13, P2-01, P2-04, P2-25, P3-01, P3-03, P3-06, P3-09, P3-11, P3-14
- AudioWorklet: <https://developer.mozilla.org/en-US/docs/Web/API/AudioWorklet>
- getUserMedia: <https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia>
- Silero VAD: <https://github.com/snakers4/silero-vad>
