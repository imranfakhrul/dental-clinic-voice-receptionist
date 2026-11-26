# Sequences

Four main paths plus the reconnect. Plain-language notes follow each diagram.

## S1: Voice turn and latency budget (plan §4.4)

```mermaid
sequenceDiagram
  participant B as Browser (mic, VAD)
  participant A as api (orchestrator)
  participant S as Speech-to-Text
  participant G as Gemini (us)
  participant T as Text-to-Speech
  B->>A: audio frames, 20 ms, 16 kHz PCM (WSS)
  A->>S: stream audio
  S-->>A: partials, then final
  Note over A: end of speech detected (300-500 ms)
  A->>G: stream request (masked context)
  G-->>A: first token (target 300 ms)
  A->>T: first sentence
  T-->>A: first audio (target 250 ms)
  A-->>B: audio chunks
  Note over B,A: voice-to-voice target 1.0-1.5 s p50
  B->>A: patient speaks again (barge-in)
  A->>T: stop playback
  A->>G: cancel stream (within 200 ms)
```

| Stage | Target | Measured |
|---|---|---|
| End of speech detection | 300–500 ms | P3-03, P3-14 |
| Gemini first token | ≤ 300 ms (flash tier) | Pending: P0-13 live run deferred; Vertex `us` not measured (ADR 0001 §4) |
| TTS first audio | ≤ 250 ms | P3-03 |
| Voice to voice | 1.0–1.5 s p50 | P3-14 |

### S1b: Reconnect (WebSocket cut at 60 minutes or instance loss)

```mermaid
sequenceDiagram
  participant B as Browser
  participant LB as Load balancer
  participant A1 as api instance 1
  participant A2 as api instance 2
  participant R as Redis (session state)
  B->>LB: WSS with session token
  LB->>A1: connect (session affinity, best effort)
  A1->>R: save state after every turn
  Note over A1: request timeout (3600 s) or instance stops
  A1--xB: connection closed
  B->>LB: reconnect with the same session token
  LB->>A2: may land on another instance
  A2->>R: load state (slots, step, last turns)
  A2-->>B: resume ("Sorry, I lost you for a second...")
```

Every confirmed step is in Redis before the reply is sent, so a reconnect never loses it (P2-01, P3-02). A write that was in flight when the connection broke is resolved by its idempotency key (S2).

## S2: Booking (plan §4.6; no slot hold, DECISIONS #146, #290)

```mermaid
sequenceDiagram
  participant P as Patient
  participant A as api (state machine, tool gateway)
  participant O as Open Dental (1 request/s per clinic)
  A->>O: get free slots
  O-->>A: slots
  A-->>P: 2-3 options (no hold)
  P->>A: picks one
  A-->>P: confirmation card
  P->>A: confirms
  A-->>P: filler ("One moment while I book that")
  A->>O: re-check that the slot is still free
  alt slot taken
    A-->>P: offer the next options
  else slot free
    A->>O: create appointment (idempotency key, operation hash)
    O-->>A: AptNum
    A->>O: read back the created appointment
    A-->>P: booked: day, time
  end
```

- Nothing is held at offer or selection. A collision shows up at the re-check, or as a conflict on create, and the patient gets new options.
- The create uses exactly what the patient confirmed (operation hash) and an idempotency key, so a retry after a timeout can't double-book (P2-08).
- Calls to Open Dental queue behind the 1 request/second limit (P1-15); the filler phrase covers the wait.

## S3: Callback (P2-22, `link_only` email, DECISIONS #303)

```mermaid
sequenceDiagram
  participant P as Patient
  participant A as api
  participant D as Cloud SQL
  participant Q as Cloud Tasks
  participant M as Gmail API
  P->>A: wants a person / can't be resolved
  A-->>P: collect name, phone, situation; read back
  P->>A: confirms
  A->>D: insert callback case (encrypted fields)
  A->>Q: enqueue email task (case ID only)
  A-->>P: "The clinic will call you back"
  Q->>A: run task (OIDC)
  A->>D: load case
  A->>M: send link_only email (urgency, time, case ID, link)
  alt sent
    A->>D: email_status = sent
  else retries exhausted
    A->>D: email_status = failed
    A->>A: unsent alert to staff (console + monitoring)
  end
```

## S4: Reminder (P4-04, appointment − 60 minutes, DST-aware)

```mermaid
sequenceDiagram
  participant A as api
  participant Q as Cloud Tasks
  participant O as Open Dental
  participant D as Cloud SQL
  participant W as Messaging (Meta or Twilio)
  A->>Q: schedule at appointment - 60 min (AptNum, reminder ID only)
  Q->>A: task fires (OIDC)
  A->>O: re-fetch the appointment
  alt cancelled or moved
    A->>D: cancel or reschedule the reminder
  else still on
    A->>D: check consent and opt-out
    alt consent and channel allowed by messaging_policy.yaml
      A->>W: send template (first name, clinic, date, time)
      W-->>A: status webhook (F15a / F15b)
    else no consent or opted out
      A->>D: mark skipped
    end
  end
```

The task payload carries IDs only; the handler re-fetches everything (F13).
