# ADR 0004: Audio transport: WebSocket

| | |
|---|---|
| Status | **Accepted** (2026-11-26). Holds on any hosting that supports WebSockets |
| Date | 2026-11-26 |
| Task | P0-14 (issue #15) · DECISIONS #318; confirmed in P3-01 / P3-02 |
| Deciders | Riley Tech (tech lead), backend review (Riley Tech, second pass) |

## Context
The browser widget streams microphone audio to the backend and plays back synthesized speech. It must work through the load balancer and Cloud Armor, without extra media servers, and reach a voice-to-voice target of 1.0–1.5 s p50 (plan §4.4).

## Options considered
| Option | For | Against |
|---|---|---|
| **WebSocket (`wss://`)** | Works through the HTTPS load balancer and Cloud Run (A1); one connection for audio and events; simple | TCP: a lost packet delays later audio (head-of-line blocking) on bad networks |
| WebRTC (for example SmallWebRTC, LiveKit, Daily) | Built for real-time media, jitter buffers | Needs STUN/TURN (and often an SFU); UDP doesn't pass the HTTPS load balancer; another vendor (BAA) if hosted |
| HTTP chunked upload + server-sent events | Simple | Two channels; awkward barge-in |

## Decision
**WebSocket** over `wss://` through the load balancer to `api`:
- audio up: 16 kHz, 16-bit mono PCM, 20 ms frames;
- audio down: TTS chunks; control and transcript events on the same socket;
- the browser does echo cancellation and noise suppression; the server runs Silero VAD (16 kHz);
- the client reconnects with its session token when the socket closes (ADR 0002).

## Consequences
- No TURN or media servers, no extra vendor.
- Barge-in and cancel are messages on the same socket (P3-06).
- P3-02 implements the protocol and the reconnect; P3-14 measures jitter impact.

## Review triggers
- P3-01 or P3-14 shows network jitter breaks the latency targets: reconsider WebRTC (and its vendor and BAA).
- Hosting changes to a platform without long-lived WebSockets.
