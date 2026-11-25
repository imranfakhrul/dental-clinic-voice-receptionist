---
id: P3-11
title: Voice UI - avatar states, mic controls, live transcript and seamless voice/text switching
milestone: P3
epic: E3.3
size: L
labels: area:frontend, area:voice, type:feature
depends_on: P3-02, P3-03, P3-06, P3-09, P2-25, P2-27, P2-01
status: approved
---

# P3-11: Voice UI - avatar states, mic controls, live transcript and seamless voice/text switching

## 1. Summary
Build everything the patient **sees** while using voice in the widget. This task absorbs **P3-12 (live transcript in the chat panel)** and **P3-13 (seamless voice ↔ text switching in one session)**.

| Part | What it does |
|---|---|
| Avatar (voice orb) | **Revised (DECISIONS #270):** an abstract, audio-reactive **voice orb** (no character, no 3D, no Rive) with four states: idle, listening, thinking, speaking; the state is driven by protocol events and changes within 100 ms; while listening the orb moves with the patient's microphone level, while speaking with the assistant's audio level |
| Mic controls | Mic button in the composer (start / stop voice), mute, a clear mic indicator, a one-time explanation before the browser's permission prompt |
| Live transcript | A grey "partial" bubble that updates while the patient speaks and becomes the patient's message (with a mic icon) when the turn ends |
| Voice ↔ text | Same session and memory; switch at any time; a reply is spoken only when the turn was spoken |
| Layout | Avatar 64 px in text mode, 160 px (desktop) / 120 px (mobile) in voice mode; hidden in text-only mode |

Done means:
- avatar (orb) state changes within 100 ms of the protocol event, and the orb visibly follows the audio level while listening and speaking;
- the final transcript shown equals the text the server processed;
- switching between voice and text in the middle of a booking keeps every filled detail;
- axe shows 0 critical / 0 serious issues in every voice state.

## 2. Why this matters
Plan §2 promises patients can talk with interruption (#1), switch between voice and text mid-conversation (#2) and see a live transcript (#3). Plan §3.1 places an avatar and voice panel next to the chat panel. Without clear visual states, patients don't know whether the assistant heard them, is working, or is waiting; without a transcript they can't spot a misheard word; without smooth switching, a patient who moves to a noisy place loses their booking.

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P3, Voice Pipeline & Avatar**.
- **Voice orb (DECISIONS #270):** a soft, glowing circle whose shape and brightness move with sound, the style many voice assistants use today. It replaces the illustrated Rive receptionist of DECISIONS #242. It is **our own design** drawn in code; no third-party orb asset, shader or brand look is copied.
- **Web Audio `AnalyserNode`:** a browser node that reports the current waveform or frequency data of an audio stream without changing it. We read it once per animation frame and compute a loudness value (RMS) from 0 to 1. <https://developer.mozilla.org/en-US/docs/Web/API/AnalyserNode>
- **WebGL fragment shader:** a small GPU program that colours every pixel of a canvas; used to draw the orb's moving gradient cheaply. A Canvas 2D fallback draws a simpler orb when WebGL is unavailable.
- **Permissions API:** `navigator.permissions.query({name: "microphone"})` tells whether the mic is `granted`, `denied` or `prompt` without asking. **Verify** support in Safari; fall back to "unknown".
- **What already exists:**
  - **P2-25** (approved): widget shell, `AvatarPanel` (64 px static placeholder), `Composer`, `MessageList`, `ChatSocket`, reducer state, `sessionStorage` session, CSP, `voice_enabled` flag, iframe `allow` attribute, display history `conv:{sid}:display`.
  - **P2-27** (approved): designed cards and chips, text-only mode toggle (`dai:ui` in `sessionStorage`), reduced motion, WCAG 2.2 AA with axe.
  - **P3-02** (approved): protocol v2 (`voice_start`, `voice_ready`, `speech_start`, `endpoint`, `utterance_discarded`, `playback_start`, `playback_ended`, `voice_stop`, `voice_stopped`, `mute`), `MicCapture`, `AudioPlayer`, lifecycle (hands-free, mute, 60 s idle auto-stop, permission-denied message, reconnect).
  - **P3-03** (approved): `transcript {utterance_id, text, final}` (partials at most every 150 ms).
  - **P3-06** (approved): `playback_paused`, `playback_pause`, `playback_resume`, `playback_flush`; fillers are audio only.
  - **P3-09** (approved): read-back items in chat with `rb:fix:<field>` choices.
  - **P2-01** (approved): one session across channels; `channel_switched` keeps the state and increments `channel_switches`.

## 4. Scope
**In scope**
- `VoiceOrb` (WebGL with a Canvas 2D and static fallback), `AudioLevelMeter` for mic and playback levels, the avatar state reducer, and the orb design spec (§6).
- `MicButton`, mute toggle, mic indicator, permission explanation sheet, unsupported-browser handling.
- `PartialTranscriptBubble` and voice-sourced message bubbles; display history marks voice messages.
- Reply-follows-channel rule (frontend and backend `speak.py`), typed message during playback.
- Voice-mode layout (desktop and mobile), text-only mode interaction, reduced motion.
- Accessibility (labels, focus, live-region announcements) and tests, including the mid-booking switch E2E.

**Out of scope** (and which task covers it)
- Audio capture, transport, VAD, endpointing → P3-02
- STT/TTS → P3-03
- Barge-in logic → P3-06 (this task only shows its events)
- Read-back logic → P3-09
- Character avatar, 3D avatar and lip-sync → not in the MVP (user decision, DECISIONS #270; plan §3.2 "lip-sync optional later")
- Visual polish of colours and motion curves by a designer → optional design review in the PR; the orb is complete without it

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P3-02 / P3-03 / P3-06 (approved) | Protocol v2 messages | Extend `scripts/dev/fake_chat_server.py` with scripted voice events (`--voice-script fixtures/voice_booking.json`) |
| P3-02 audio modules (approved) | `MicCapture` and `AudioPlayer` expose an analyser tap (§6, additive to P3-02) | Feed `VoiceOrb` from a local `<audio>` test file or an `OscillatorNode` in Storybook (`orb.stories.tsx`) |
| P2-25 / P2-27 (approved) | Shell, composer, text-only mode | Extend the existing components |

## 6. Interface contract

### Avatar state (DECISIONS #242)
```ts
// frontend/lib/voice/avatarState.ts
export type AvatarState = "idle" | "listening" | "thinking" | "speaking";
export interface VoiceUiState {
  voice: "off" | "explaining" | "starting" | "on" | "paused" | "unavailable";
  muted: boolean;
  avatar: AvatarState;
  partial: { utteranceId: number; text: string } | null;
  playingReplyId: number | null;
}
export function voiceUiReducer(s: VoiceUiState, e: VoiceUiEvent): VoiceUiState;   // pure, unit-tested
```
| Event (protocol v2 or local) | Avatar becomes |
|---|---|
| `voice_ready`, `playback_ended` (no more queued replies), `utterance_discarded` | `idle` |
| `speech_start` (client VAD), `transcript` partial, `playback_paused` | `listening` |
| `endpoint`; text mode: `typing on` | `thinking` |
| `playback_start` (including fillers), `playback_resume` | `speaking` |
| `playback_flush` with a new utterance in progress | `listening` |
| `voice_stopped`, `voice_stop` | `idle` (voice off) |
| Text mode, no typing indicator | `idle` |
| `muted = true` | keeps the state; adds the "muted" overlay |
Timing: the reducer runs synchronously on the WebSocket message; the orb reads the new state in the next animation frame. Target ≤ 100 ms from message arrival to the visible change (measured with `performance.mark`).

### Voice orb (revised by DECISIONS #270; replaces the Rive avatar of #242)
```ts
// frontend/components/voice/VoiceOrb.tsx
<VoiceOrb state={avatar} muted={muted} size={64 | 120 | 160} accent={accentColor}
          reducedMotion={bool} level={levelSource} />

// frontend/lib/voice/audioLevel.ts
export interface LevelSource { read(): number }            // 0..1, smoothed; called once per frame
export class AudioLevelMeter implements LevelSource {
  constructor(ctx: AudioContext, node: AudioNode);          // connects an AnalyserNode (fftSize 512) as a side tap
  read(): number;   // RMS of the time-domain buffer → dB → mapped -60..-10 dB → 0..1; attack 50 ms, release 200 ms
  dispose(): void;
}
export const SILENT: LevelSource = { read: () => 0 };
```
**Which level drives the orb**
| Avatar state | `level` source |
|---|---|
| `listening` | Mic level: `MicCapture.levelNode()` (post noise-suppression input); `SILENT` when muted |
| `speaking` | Playback level: `AudioPlayer.levelNode()` (the player's output, fillers included) |
| `idle`, `thinking`, text mode | `SILENT` (the orb uses its own slow motion) |

**Additive to P3-02:** `MicCapture.levelNode(): AudioNode` and `AudioPlayer.levelNode(): AudioNode` return a node in the existing `AudioContext` that the meter can tap. The tap is read-only and local: no level data leaves the browser.

**Look and motion (Proposed; our own design)**
| State | Orb |
|---|---|
| `idle` | Soft gradient sphere in the clinic accent colour; slow "breathing" scale 1.00 ↔ 1.03 over 4 s; gentle colour drift |
| `listening` | Edge ripples and scale follow the mic level: `scale = 1 + 0.12 × level`; brighter rim; a small mic glyph in the centre at sizes ≥ 120 px |
| `thinking` | Level ignored; gradient swirls slowly (one turn per 3 s); a faint shimmer |
| `speaking` | Surface deforms with the playback level: noise displacement amplitude `0.04 + 0.18 × level`, scale `1 + 0.10 × level`; most active of the four states |
| `muted` overlay | Saturation drops to 30%; a crossed-mic badge at the lower right; motion continues at idle speed |
- **Colours:** derived from the clinic `accent_color` (P4-13): base = accent, highlight = accent lightened 25%, depth = accent darkened 30%, all computed in OKLCH. The orb is decorative; nothing relies on its colour for meaning (the state label below carries it), so contrast rules apply only to the label.
- **Label:** under the orb, `conversation.assistant_name` + "Virtual assistant", and at 120/160 px the state text ("Listening", "Thinking", "Speaking", "Muted").
- **Rendering:** one `<canvas>` with a WebGL1 fragment shader (2D simplex noise displacement of a radial gradient; ≤ 120 lines of GLSL written in this repo). `devicePixelRatio` capped at 2. The animation loop uses `requestAnimationFrame`, stops when the widget is hidden (`document.visibilityState`) or voice and typing are idle for 30 s in text mode, and runs at 30 fps when `navigator.hardwareConcurrency ≤ 4`.
- **Fallbacks:** no WebGL → Canvas 2D (radial gradient circle scaled by the same level formula); `prefers-reduced-motion: reduce` or text-only mode → static gradient circle with the state label, no motion and no level reaction; any render error → the static circle (voice keeps working).
- **No third parties:** no animation library, no WASM; the widget CSP stays as in P2-25 (the `'wasm-unsafe-eval'` addition from #242 is withdrawn).
- **Budget:** `VoiceOrb` + shader + meter ≤ 12 KB gzip; main-thread cost ≤ 2 ms per frame on a mid-range phone (measured in T14).

### Mic controls and permission (DECISIONS #243)
| Element | Behaviour |
|---|---|
| `MicButton` in the composer (left of the send button) | Shown only if `voice_enabled` and the browser supports voice (`isSecureContext`, `navigator.mediaDevices.getUserMedia`, `AudioWorklet`); otherwise hidden (no error) |
| First tap | If `localStorage["dai:mic_explained"]` is unset and the Permissions API does not say `granted` → `MicExplainSheet`: "We'll use your microphone only while voice is on. Audio isn't recorded." buttons **Continue** / **Not now**. Continue sets the flag (no PHI) and calls `MicCapture.start()` |
| Permission `denied` | P3-02 message ("Microphone access is blocked…"); the button shows a crossed mic; no retry loop |
| Voice on | Button becomes "Stop voice" (red dot + "Listening" label); mute toggle appears next to it |
| Mute | `mute true`; indicator shows "Muted"; TTS keeps playing |
| Voice paused (60 s idle) | Chat shows P3-02's "Voice paused. Tap the mic to talk again."; button back to "Start voice" |
| Text-only mode (P2-27) | Mic button and avatar hidden; voice is stopped if it was on |
| Keyboard | Button reachable by Tab; `Space`/`Enter` toggle; `aria-pressed` reflects voice on/off; mute has its own `aria-pressed` |

**Live-region announcements** (`aria-live="polite"`, one region): "Voice on. I'm listening.", "Muted.", "Voice off.", "Voice paused." State changes listening/thinking/speaking are **not** announced (too noisy); the assistant's words are already in the chat.

### Live transcript (DECISIONS #244)
| Event | Chat panel |
|---|---|
| `transcript final=false` | One `PartialTranscriptBubble` (patient side, grey italic, mic icon, `aria-hidden="true"`) updated in place |
| `transcript final=true` | The bubble becomes a normal patient message with a mic icon (`MessageBubble source="voice"`) and is announced like any new message |
| `utterance_discarded` | The partial bubble is removed |
| Reconnect while a partial is shown | Removed; P3-02's "Sorry, I missed that" follows |
- The final text shown must equal `UserTurn.text` (the server sends the final `transcript` from the same value it passes to P2-01).
- Display history (`conv:{sid}:display`, P2-25) stores voice finals like typed messages, with `source: "voice"` so a reload shows the mic icon. Partials are never stored.
- No caption under the avatar: the assistant's spoken words already appear as `reply_chunk` text.

### Reply follows the channel (DECISIONS #245)
| Turn | Reply |
|---|---|
| Spoken (`UserTurn.channel == "VOICE"`) | Text in chat **and** audio |
| Typed or tapped choice while voice is on | Text only; the mic keeps listening (P3-02) |
| Typed message sent while a reply is playing | Client flushes playback at once; server treats it like a confirmed barge-in (cancel TTS and the LLM stream, P3-06), then processes the typed turn |
- Backend: `speak.py` (P3-03) speaks a reply only when the turn that produced it was VOICE. Fillers (P3-06) also only for VOICE turns.
- Switching never resets anything: one session, one slot memory (P2-01). `channel_switched` keeps the state; the `channel_switched` template ("Sure, let's continue.") is used only when the turn has no other content (e.g. "can I type instead?"), never as an extra reply mid-flow.

### Layout
| Mode | Desktop (400 × 640 panel) | Mobile (full screen) |
|---|---|---|
| Text | Avatar 64 px in the header area (P2-25) | Same |
| Voice on | Avatar panel expands to 160 px with state label and mic indicator; message list shrinks | Avatar 120 px; message list keeps at least 45% of the height; composer stays above the keyboard |
| Text-only mode | No avatar, no mic | Same |
Transition between sizes: 200 ms, none under reduced motion.

### Telemetry (no PHI)
| Item | Fields |
|---|---|
| `ui.voice` (client → existing P2-25 client-metrics endpoint, if present; else console in dev only) | `event` (`explain_shown`, `explain_continue`, `explain_not_now`, `permission_denied`, `unsupported`), `browser_family` |
| `ui.avatar_latency_ms` | p50/p95 from `performance.mark` in E2E runs (not sent from patients) |
Server metric `dai.session.channel_switches` comes from P2-01's counter.

## 7. Implementation guide
1. **Reducer** `voiceUiReducer` with the event table; unit tests for every row.
2. **Level taps**: add `levelNode()` to `MicCapture` and `AudioPlayer` (P3-02 additive); write `AudioLevelMeter` with the dB mapping and attack/release smoothing; unit-test it with an `OfflineAudioContext` and known sine amplitudes.
3. **VoiceOrb**: WebGL shader, Canvas 2D fallback, static fallback, state table, accent colours, label; Storybook stories for every state with an oscillator level source. No CSP change is needed.
4. **Mic controls**: `MicButton`, `MicExplainSheet`, mute toggle, indicator, feature detection, Permissions API with fallback.
5. **Transcript**: `PartialTranscriptBubble`, final conversion, removal; `source: "voice"` in display history (P2-25 store).
6. **Reply-follows-channel** in `speak.py` and the typed-during-playback path.
7. **Layout** for voice mode on desktop and mobile; text-only mode and reduced motion.
8. **Fake server voice script** and Playwright tests (§10), including Chromium fake audio for one real-pipeline run on staging.
9. **Docs** `docs/widget/voice-ui.md` (states, orb look-and-motion table, level mapping, how to tune the constants). Notify P3-14 (switch metric), P4-11 (none needed: no new config), P6 onboarding (iframe `allow="microphone"` and Permissions-Policy note).

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| WebGL unavailable or the shader fails to compile | Canvas 2D orb; if that fails too, the static circle with the state label; voice still works |
| Very loud room noise while listening | The meter clamps at 1.0, so the orb stops growing; muting sets the level to 0 |
| Low-power phone (frame time > 8 ms for 2 s) | Drops to 30 fps, then to the Canvas 2D orb |
| Safari without Permissions API support for `microphone` | Treated as `prompt`; explanation sheet shown once |
| Patient taps "Not now" | Sheet closes; nothing requested; next tap shows the sheet again until Continue is chosen once |
| Clinic page blocks the microphone via Permissions-Policy | `getUserMedia` fails with `NotAllowedError` → P3-02 blocked message; onboarding doc explains the fix |
| Patient types while speaking | Both arrive; P2-01 processes them in order (lock); the typed one gets a text-only reply |
| Switch mid-booking (text → voice after choosing a slot) | Same state; the confirmation card stays; saying "yes" works (P2-27 `confirm` by voice text) |
| Partial transcript shows a mistake | It is replaced by the final; read-back (P3-09) confirms critical values |
| Several quick utterances | Only one partial bubble at a time (the latest utterance id wins) |
| Reply audio and text arrive at different speeds | Text appears as it streams; avatar shows speaking only while audio plays |
| Emergency banner (P2-27) during voice | Banner shows as usual; the avatar keeps its state; nothing hides the banner |
| Reduced motion or text-only toggled during voice | Animation stops at once; text-only also stops voice |
| Mobile keyboard opens during voice | Avatar collapses to 64 px while the keyboard is open |

## 9. Security, HIPAA and PHI
- **PHI handled:** transcripts (may contain names, DOB, phone) are shown only in the patient's own widget, like typed text; partials are never stored; finals follow P2-25 display-history rules (encrypted in Redis, same TTL).
- **No PHI in browser storage:** only the flags `dai:mic_explained` (`localStorage`) and `dai:ui` (`sessionStorage`).
- **No third parties:** the orb is our own code; audio levels are computed in the browser and never sent anywhere; telemetry has no text.
- **Mic transparency:** a visible indicator whenever capture is on; mute stops sending immediately (P3-02).

## 10. Testing
```bash
cd frontend && pnpm test -- voice-ui          # reducer, components, transcript conversion
pnpm e2e -- --grep voice-ui                    # Playwright against the fake server voice script
pnpm e2e:staging -- --grep voice-switch        # real pipeline, Chromium fake mic (--use-file-for-fake-audio-capture)
```
| # | Case | Expected |
|---|---|---|
| T1 | Reducer table | Every event gives the listed state |
| T2 | Avatar latency (E2E, 50 events) | ≤ 100 ms p95 from message to the orb state / fallback label change |
| T3 | WebGL disabled; shader compile forced to fail | Canvas 2D orb; then static circle; no console errors leak text |
| T4 | Mic explanation | Shown once per browser; Continue requests permission; Not now requests nothing |
| T5 | Permission denied / unsupported browser | Message shown / button hidden; text works |
| T6 | Partial → final | Partial bubble updates; final equals the server's `UserTurn.text`; discard removes it |
| T7 | Reload | Voice messages come back with the mic icon; no partials |
| T8 | Reply follows channel | Spoken turn → audio + text; typed turn while voice on → text only |
| T9 | Typed during playback | Playback flushed ≤ 200 ms; reply cancelled; typed turn answered |
| T10 | Mid-booking switch both ways (staging) | All slots kept; booking completes; `channel_switches` = 2 |
| T11 | Layout | Desktop 160 px / mobile 120 px in voice; 64 px with keyboard open; hidden in text-only |
| T12 | Accessibility | axe 0 critical / 0 serious in every voice state; keyboard-only start/stop/mute; announcements as listed |
| T13 | Reduced motion | No animation; state still readable from the label |
| T14 | Audio reactivity | Sine input at -50, -30, -10 dB gives meter values ≈ 0.2, 0.6, 1.0 (±0.05); orb scale follows within 100 ms in listening and speaking; `SILENT` in idle/thinking/muted; ≤ 2 ms per frame (Chrome performance trace, 4× CPU throttle) |

## 11. Acceptance criteria
- [ ] Avatar (orb) state changes within 100 ms of the protocol event, and the orb follows the mic level while listening and the playback level while speaking (T1, T2, T14)
- [ ] The transcript shown matches what was spoken and processed (T6, T7)
- [ ] Switching voice ↔ text mid-booking keeps all filled slots and the booking completes (T10)
- [ ] A reply is spoken only for spoken turns; typing during playback stops the audio (T8, T9)
- [ ] Mic controls are clear, keyboard-accessible and explained before the first permission prompt (T4, T5, T12)
- [ ] Works without WebGL, with reduced motion and in text-only mode (T3, T11, T13)

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI; staging switch run linked in the PR
- [ ] PR reviewed (design review of the orb in all four states and muted)
- [ ] No PHI in logs or browser storage
- [ ] `docs/widget/voice-ui.md` written; P2-25 CSP and display-history changes merged
- [ ] P3-14 and P6 onboarding notified

## 13. Hand-off
| Consumer | What they can rely on |
|---|---|
| P3-14 Latency / demo | Avatar latency marks, `channel_switches`, the voice booking demo path |
| P5 accessibility / E2E | Voice-state axe runs and the switch scenario |
| P6 onboarding | Clinic page needs `allow="microphone"` on the iframe (set by `embed.js`) and no blocking Permissions-Policy |
| Designer | The look-and-motion table and constants in `VoiceOrb` to tune colours and motion without code changes elsewhere |

## 14. Open questions
| # | Question | Recommended answer | Owner |
|---|---|---|---|
| 1 | Should clinics choose between several orb styles? | Not in the MVP: one orb, coloured from the clinic accent colour. | Product owner |
| 2 | Should the avatar show a name ("Ava")? | Use `conversation.assistant_name` (P2-25) under the avatar with "Virtual assistant". | Product owner |
| 3 | Should we show the assistant's words as a caption under the avatar in voice mode? | No: the chat already shows them; a caption would duplicate text for screen readers. | Product owner |

## 15. References
- Plan: §2 (#1–#3), §3.1, §3.2, §8 Phase 3
- DECISIONS: #174, #175, #185, #209, #211, #226, #228, #230, #234, #238, #242 (avatar part replaced by #270), #243, #244, #245, #270
- Related tasks: P2-01, P2-25, P2-27, P3-02, P3-03, P3-06, P3-09, P3-14, P6-01
- Web Audio AnalyserNode: <https://developer.mozilla.org/en-US/docs/Web/API/AnalyserNode>
- WebGL fundamentals: <https://developer.mozilla.org/en-US/docs/Web/API/WebGL_API>
- Permissions API: <https://developer.mozilla.org/en-US/docs/Web/API/Permissions_API>
