---
id: P2-25
title: Next.js widget shell, session handshake, streaming chat over WebSocket and bot protection
milestone: P2
epic: E2.6
size: L
labels: area:frontend, area:backend, area:security, type:feature, phi
depends_on: P1-01, P1-02, P1-07, P1-13, P1-19, P2-01, P2-04
status: approved
---

# P2-25: Next.js widget shell, session handshake, streaming chat over WebSocket and bot protection

## 1. Summary
Build the patient-facing chat widget that a clinic embeds on its website, and the WebSocket endpoint behind it. This task absorbs **P2-26 (chat messages with streaming replies)** and **P2-29 (bot protection on the public widget)**.

| Part | What it does |
|---|---|
| Embed | `embed.js` adds a launcher button to the clinic's page and opens our widget in an iframe, only on allowed sites |
| Handshake | reCAPTCHA Enterprise score → `POST /v1/sessions` → token in memory and `sessionStorage` → WebSocket `auth` |
| Chat | Message list, input, typing indicator, sentence-by-sentence streaming, reconnect, history after reload, idle warning, error states |
| Protocol | The JSON message contract between widget and `api`, including the card / choices / info-card payloads that P2-27 renders |

Done means:
- the widget works in an iframe on a test clinic page (desktop and mobile);
- the first reply chunk appears within 1 second (p50) on staging;
- no PHI ever appears in a URL;
- an automated abuse test is blocked by bot protection;
- no third-party script other than reCAPTCHA runs in the widget.

Designed cards, choice chips and the accessibility pass are **P2-27**; this task renders them in a plain, functional form.

## 2. Why this matters
The widget is the only way patients reach the AI in P2 (plan §3.1). Everything built so far — booking, identification, emergencies, callbacks — is invisible without it. It is also the public attack surface: anyone on the internet can open it, so bot protection, rate limits and "no PHI in URLs" are part of the HIPAA posture (plan §6 "bot protection on the public widget", §12 "abuse of public widget"). The streaming target (first text within 1 s) makes the chat feel responsive while Open Dental and Gemini calls run. Pilot targets helped: patient satisfaction ≥ 4.2/5, 0 PHI in logs.

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P2, Text Chat Receptionist**.
- **iframe embedding:** the clinic's page (e.g. `https://www.smiledental.com`) loads our page `https://app.<domain>/widget` inside an `<iframe>`. Our page decides which sites may frame it with the CSP header `frame-ancestors`. Docs: <https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Security-Policy/frame-ancestors>.
- **`postMessage`:** the only way the clinic page and the iframe talk; both sides must check `event.origin`. Docs: <https://developer.mozilla.org/en-US/docs/Web/API/Window/postMessage>.
- **reCAPTCHA Enterprise (score-based):** an invisible check in the browser returns a token; our backend asks Google for an assessment with a score from 0.0 (likely bot) to 1.0 (likely human). Docs: <https://cloud.google.com/recaptcha/docs/create-assessment-website>.
- **What already exists:**
  - **P1-01** (approved): one Next.js app (`frontend/`, TypeScript, Tailwind, pnpm) with `/widget` and `/admin`; Cloud Run service `web`.
  - **P1-13** (approved): `POST /v1/sessions` (`{clinic_slug, channel}` → `{session_id, token, idle_timeout_s, expires_at}`), hook `verify_bot_token(request)` (no-op until here), token never in URL or cookie, `sessionStorage` allowed (never `localStorage`), WebSocket `wss://api.<domain>/v1/sessions/{session_id}/ws` with first message `{"type":"auth","token"}` within 5 s, close codes 4401 / 4408 / 4429, rate limits `session_create` (10/min/IP), `patient_message` (30/min/session), `clinic_messages`.
  - **P2-01** (approved): `TurnProcessor.handle(principal, UserTurn{text, channel, client_turn_id, choice_id})`, duplicate `client_turn_id` ignored (reconnect replay), `start_session`, `conversation.max_turn_chars` (1000), idle expiry; state fully in Redis so a reconnect may land on any instance (DECISIONS #72).
  - **P2-04** (approved): `ReplyChunk{text, source, final, card, choices, info_card}` streamed one sentence per chunk; `session_expired` template.
  - **P2-16** (approved): `Choice{id, label}`, `InfoCard{kind, title, rows, actions}`; a tapped choice is sent back with `choice_id`.

## 4. Scope
**In scope**
- `frontend/public/embed.js` (launcher, iframe, open/close, mobile full screen).
- `/widget` page: layout (avatar panel placeholder + chat panel), clinic branding, message list, input, typing indicator, streaming, history, idle warning, errors, "start new chat".
- Public widget-config endpoint and per-clinic CSP `frame-ancestors`.
- Backend WebSocket endpoint `ws_chat.py` that runs P2-01 and streams P2-04 chunks, plus the display-history store.
- reCAPTCHA Enterprise integration behind `verify_bot_token` and the strict-mode rate limit.
- Plain renderers for cards, choices and info cards (functional, unstyled), with component boundaries P2-27 replaces.
- Playwright tests on a test clinic page; staging latency check.

**Out of scope** (and which task covers it)
- Designed slot cards, confirmation cards, chips; keyboard and screen-reader pass; text-only mode → P2-27
- Voice: mic, VAD, audio over the socket, avatar animation → P3 tasks
- Console editing of the `widget` config section → P4-11
- Load tests, Cloud Armor tuning → P5

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P1-13 (approved) | Sessions endpoint, token, WS auth, limits | Contract is fixed; a local backend with `FakeLlmProvider` and `od_fake` |
| P2-01 / P2-04 (approved) | Turn processor and reply stream | `scripts/dev/fake_chat_server.py` replays canned `ReplyChunk` streams over the same protocol |
| P1-19 (approved) | Config section `widget` (added here) | Seed `config/clinics/demo.yaml` |
| P2-27 (later) | Designed components | Plain renderers here; same props |
| reCAPTCHA Enterprise | Site key, API enabled | `BOT_PROTECTION=off` in local; test keys in dev (**Verify** Google's test-key behaviour for Enterprise) |

## 6. Interface contract

### Embed snippet (given to the clinic)
```html
<script src="https://app.<domain>/embed.js" data-clinic="pilot-clinic" async></script>
```
`embed.js` (plain JS, ≤ 10 KB gzipped, no dependencies):
- draws a launcher button bottom-right inside a Shadow DOM (label from widget config, default "Chat with us");
- on first click creates `<iframe src="https://app.<domain>/widget?clinic=pilot-clinic" title="{clinic} virtual assistant" allow="microphone 'none'">` (P3 changes `allow` to `microphone`);
- panel 400 × 640 px on desktop; full screen when the viewport is < 640 px wide;
- `postMessage` events from the iframe, accepted only when `event.origin === "https://app.<domain>"`: `{"type":"dai:close"}`, `{"type":"dai:unread","count":n}`. No PHI is ever sent through `postMessage`.

The only value in any URL is the clinic slug (and, in API paths, the random `session_id`).

### Public widget config (no PHI)
`GET /v1/public/clinics/{clinic_slug}/widget` (unauthenticated, cached 300 s, rate limited per IP):
```json
{"display_name": "Smile Dental", "accent_color": "#0F6CBD", "logo_url": "https://app.<domain>/assets/clinics/pilot-clinic/logo.png",
 "launcher_label": "Chat with us", "public_phone": "+15035550100", "recaptcha_site_key": "6Lc...", "voice_enabled": false}
```
Config section (additive to P1-19, console-editable later in P4-11; DECISIONS #211):
```yaml
widget:
  allowed_origins: ["https://www.smiledental.com", "https://smiledental.com"]   # exact https origins; required for prod
  accent_color: "#0F6CBD"            # hex; contrast with white checked at load (WCAG AA 4.5:1)
  logo_url: null                     # our asset path only; null = clinic name text
  launcher_label: "Chat with us"     # ≤ 24 chars
```
**CSP for `/widget`** (Next.js middleware, per request, from the slug's config):
```
Content-Security-Policy: frame-ancestors <allowed_origins>; default-src 'self';
  script-src 'self' 'nonce-<n>' https://www.google.com/recaptcha/ https://www.gstatic.com/recaptcha/;
  frame-src https://www.google.com/recaptcha/; connect-src 'self' https://api.<domain> wss://api.<domain>;
  img-src 'self' data:; style-src 'self' 'nonce-<n>'; font-src 'self'
```
~~**Added by P3-11 (DECISIONS #242):** `script-src` gains `'wasm-unsafe-eval'` for the self-hosted Rive avatar runtime.~~ **Withdrawn by DECISIONS #270:** the avatar is now a code-drawn voice orb (WebGL/Canvas, no WASM), so the CSP above stays unchanged.
Unknown slug or empty `allowed_origins` in prod → the page renders "This chat isn't available" and sends `frame-ancestors 'none'`. Dev and staging also allow the test clinic page origin.

### Bot protection (`app/auth/bot.py`, implements P1-13's hook; DECISIONS #210)
Browser: `grecaptcha.enterprise.execute(siteKey, {action: "session_create"})` → `bot_token`, sent in the `POST /v1/sessions` body.
```python
class BotVerdict(BaseModel):
    decision: Literal["allow", "strict", "block"]
    score: float | None                  # None when the check was skipped or unavailable
    reason: Literal["ok", "low_score", "invalid_token", "action_mismatch", "service_unavailable", "disabled"]

async def verify_bot_token(request: Request, body: SessionCreate) -> BotVerdict: ...
# projects.assessments.create with {event: {token, siteKey, expectedAction: "session_create"}}
```
| Condition | Decision |
|---|---|
| Valid token, action matches, score ≥ `BOT_SCORE_STRICT` (0.5) | `allow` |
| 0.3 ≤ score < 0.5 | `strict`: session flag `bot_suspect`; rate limit `patient_message_strict` (10/min) instead of 30/min |
| Script failed to load in the browser (`bot_token: null`, `client_reason: "script_unavailable"`) | `strict` |
| score < `BOT_SCORE_BLOCK` (0.3), invalid token, missing token without that reason, wrong action | `block` → 403 `bot_suspected`; widget shows "We couldn't start the chat. Please call us at {public_phone}." |
| reCAPTCHA API error or timeout (1.5 s) | `strict` (fail open with tight limits) + log + alert A-WG1 if > 5% in 15 min |
- Env: `BOT_PROTECTION=on|off` (off only when `ENV=local`), `RECAPTCHA_PROJECT_ID`, `BOT_SCORE_BLOCK`, `BOT_SCORE_STRICT`.
- Test bypass (added by P2-30, DECISIONS #220): in dev and staging only, header `X-DAI-E2E` matching `BOT_TEST_BYPASS_SECRET` → `allow` (reason `e2e_bypass`, session flagged `e2e`, audit `security.bot_bypass_e2e`); prod refuses to start if the secret is set.
- Audit `security.bot_blocked` (details `reason`, score rounded to 0.1); log the decision and score only, never the token.
- **Verify:** that reCAPTCHA Enterprise is on Google Cloud's HIPAA covered-products list. No PHI is sent to it in any case (only browser signals at session start, before the patient types anything), but record the answer in `docs/compliance/vendors.yaml` (P0-10).

### WebSocket protocol (`wss://api.<domain>/v1/sessions/{session_id}/ws`, version 1)
All frames are JSON text with a `type`. Max client frame 8 KB.

**Client → server**
| `type` | Fields | Notes |
|---|---|---|
| `auth` | `token`, `protocol: 1`, `resume: bool` | First frame within 5 s (P1-13) |
| `user_turn` | `client_turn_id` (UUID v4, made by the widget), `text` (≤ `max_turn_chars`), `choice_id?` | A tapped choice sends its `label` as `text` and its `id` |
| `ping` | `activity: bool` | Every 25 s; `activity=true` only after real user activity (refreshes the idle TTL) |

**Server → client**
| `type` | Fields | Notes |
|---|---|---|
| `ready` | `session_id`, `idle_timeout_s`, `resumed`, `history: Message[]` | After auth. New session → `history: []` and the greeting follows as `reply_chunk`s |
| `turn_ack` | `client_turn_id`, `turn_id` | Sent at once; the widget shows the typing indicator |
| `reply_chunk` | `turn_id`, `seq`, `text`, `final`, `card?`, `choices?`, `info_card?`, `style?` (`"emergency"`, added by P2-27) | One sentence per chunk (P2-04); `final=true` on the last |
| `typing` | `on: bool` | Off after `final` or on error |
| `error` | `code`, `retry_after_s?`, `client_turn_id?` | Codes: `rate_limited`, `busy`, `message_too_long`, `internal_error`, `protocol_error` |
| `session_expired` | `text` | P2-04 template text; then the server closes with 4408 |
| `pong` | - | Reply to `ping` |

`Message` (history entry and the widget's own model):
```ts
type Message = {
  id: string; role: "patient" | "assistant"; text: string; ts: string;   // ISO, display only
  source?: "voice";   // added by P3-11 (DECISIONS #244): final voice transcripts show a mic icon; partials are never stored
  card?: ConfirmationCard; choices?: Choice[]; infoCard?: InfoCard;      // same JSON as P2-04 / P2-16
};
```
Example exchange:
```json
→ {"type":"user_turn","client_turn_id":"6f1c…","text":"I need a cleaning next week"}
← {"type":"turn_ack","client_turn_id":"6f1c…","turn_id":"t-17"}
← {"type":"typing","on":true}
← {"type":"reply_chunk","turn_id":"t-17","seq":0,"text":"Sure, I can help with that.","final":false}
← {"type":"reply_chunk","turn_id":"t-17","seq":1,"text":"Are you a new or returning patient?","final":true,
   "choices":[{"id":"ptype:new","label":"New patient"},{"id":"ptype:existing","label":"Returning patient"}]}
← {"type":"typing","on":false}
```
Close codes: 4401 not authenticated, 4408 session expired, 4429 too many connections, 4400 protocol error (P1-13 plus 4400). Any other close → reconnect.

**Protocol v2 (added by P3-02, DECISIONS #226):** voice clients send `auth` with `protocol: 2` and may then use binary audio frames and the voice control messages (`voice_start`, `voice_stop`, `speech_start`, `speech_end`, `mute`, `playback_ended`, `voice_ready`, `endpoint`, `utterance_discarded`, `playback_start`, `playback_flush`, `voice_stopped`, `transcript` from P3-03, `playback_paused` / `playback_pause` / `playback_resume` from P3-06, and `playback_started` / `net_stats` from P3-14) on this same socket. Everything above is unchanged; a v1 client never receives v2 messages.

### Backend endpoint (`backend/app/api/ws_chat.py`)
```python
@router.websocket("/v1/sessions/{session_id}/ws")
async def chat_ws(ws: WebSocket, session_id: uuid.UUID) -> None:
    """auth (P1-13 helper) → ready (history from DisplayHistory) → loop:
       user_turn: rate_limit(patient_message | patient_message_strict) → turn_ack → typing on →
                  outcome = TurnProcessor.handle(principal, UserTurn(...)) →
                  async for chunk in ReplyGenerator.generate(outcome, …): send reply_chunk →
                  DisplayHistory.append(patient msg, assistant msg) → typing off
       ping: refresh idle TTL if activity → pong
       idle key gone (checked every 60 s and per frame) → session_expired + close 4408"""
```
- One turn at a time per session (P2-01 turn lock). A second `user_turn` while one is running → `error busy` (the widget disables the send button while `typing` is on, so this is rare).
- A reconnect that re-sends an un-acked `user_turn` with the same `client_turn_id` gets the stored outcome replayed (P2-01 duplicate rule) — the widget never shows a turn twice.

### Display history (additive to P2-01, DECISIONS #209)
| Redis key | Type | Content |
|---|---|---|
| `conv:{sid}:display` | list, max 30 (LTRIM) | Each entry `FieldCipher.encrypt(json(Message), ctx=EncContext(table=f"redis_session/{sid}", column="display", clinic_id))`; same TTL as the other `conv:*` keys; deleted on `end_session` |

Separate from `conv:{sid}:turns` (6 turns for the LLM). Only messages already shown to this session are stored; it holds PHI and is encrypted like slot memory.

### Widget client (`frontend/app/widget/`)
```ts
// lib/widget/session.ts
export async function getOrCreateSession(slug: string): Promise<StoredSession>;   // sessionStorage key "dai:s:<slug>" = {session_id, token, expires_at}
// lib/widget/socket.ts
export class ChatSocket {
  connect(s: StoredSession): void;                 // auth, resume flag
  sendTurn(text: string, choiceId?: string): string;   // returns client_turn_id; kept in an outbox until turn_ack
  on(event: "ready" | "chunk" | "typing" | "error" | "expired" | "status", cb: (...a: any[]) => void): void;
}
// components: WidgetShell, AvatarPanel (static placeholder), MessageList, MessageBubble, Composer,
//             TypingIndicator, IdleWarning, ConnectionBanner, CardView*, ChoiceChips*, InfoCardView*   (* replaced by P2-27)
```
State: React `useReducer` (no global store library). No message text is written to `localStorage`, `sessionStorage`, cookies or the console.

**Reconnect:** backoff 0.5, 1, 2, 4, 8 s, then every 15 s; after 2 minutes without success → banner "Connection lost" with "Try again". Outbox turns are re-sent after `ready`.

**Idle:** at `idle_timeout_s − 120` s without activity → `IdleWarning` ("Are you still there?" + "I'm here" → `ping activity=true`). On `session_expired` → show the text, disable input, button "Start a new chat" (clears `sessionStorage` and runs the handshake again).

**History on reload (same tab):** `sessionStorage` session found and not expired → connect with `resume=true` → render `ready.history` (choices on older messages are disabled; only the last assistant message's choices are active). New tab → new session.

### Layout
- Desktop panel: header (logo or clinic name, close button), avatar panel (64 px static avatar, assistant name from `conversation.assistant_name`), message list, composer (textarea, 1000-char counter after 800, send button, Enter to send, Shift+Enter newline).
- Mobile: full screen; composer sticks above the keyboard (`visualViewport` resize handling).
- Accent color from config; fonts self-hosted.
- Footer line: "Virtual assistant. In an emergency, call 911." (fixed text, P0-03 reviewer to confirm).

### Logs and metrics (no PHI)
| Item | Fields |
|---|---|
| `ws.connect` / `ws.close` (info) | `close_code`, `resumed`, `duration_s` |
| `ws.turn` (info) | `turn_id`, `first_chunk_ms`, `total_ms`, `chunks` |
| `dai.stage.latency{stage="chat_first_chunk"}` | turn received → first chunk sent |
| `dai.widget.bot` (counter) | `decision`, `reason` |
| Alert **A-WG1** | reCAPTCHA unavailable > 5% of session creates in 15 min |
| Alert **A-WG2** | `chat_first_chunk` p50 > 1 s for 15 min (prod) |

The widget sends no telemetry of its own in P2 (no analytics, no error-reporting service; DECISIONS #211).

## 7. Implementation guide
1. **Protocol types** shared by name: Pydantic models in `backend/app/api/ws_protocol.py`; TypeScript types in `frontend/lib/widget/protocol.ts`; a CI test compares the JSON Schemas generated from both (`pnpm protocol:check`).
2. **Backend WS endpoint** and `DisplayHistory`; test with `FakeLlmProvider` and the turn processor.
3. **Bot protection**: `verify_bot_token`, env keys, strict-mode limit (P1-13 additive row), audit and alert.
4. **Public config endpoint** and P1-19 `widget` section (load rules: https origins only, no wildcards, contrast check).
5. **Widget page**: middleware (CSP with nonce), session handshake, `ChatSocket`, reducer, components, plain card/choice renderers.
6. **`embed.js`** and the test clinic page `frontend/e2e/fixtures/clinic-page.html` (served on a different origin in tests).
7. **Playwright tests** (§10) on desktop and mobile viewports, against the fake chat server and against the local backend.
8. **Staging check** `pnpm e2e:staging -- --grep latency`: 20 turns, report p50 of send → first chunk.
9. **Docs:** `docs/widget/embedding.md` (snippet, allowed origins, troubleshooting) and `docs/widget/protocol.md`. Notify P2-27 (components and props), P3 (protocol version 1, audio frames to add), P4-11 (`widget` section), P6 onboarding (embedding steps).

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| Widget framed by a site not in `allowed_origins` | Browser blocks framing (CSP); nothing loads |
| Unknown or inactive clinic slug | "This chat isn't available"; no session created |
| Third-party storage blocked (Safari) | `sessionStorage` in the iframe may be partitioned or unavailable → keep the session in memory only; reload starts a new session |
| Cloud Run cuts the WebSocket (timeout or deploy) | Reconnect; `resume=true`; outbox re-sent; no duplicate turn |
| Reconnect lands on another instance | Works (state in Redis) |
| Token expired (`exp` after 2 h) | Close 4408 → "Start a new chat" |
| Patient sends while a reply is streaming | Send button disabled until `typing off`; typed text kept |
| Rate limited | `error rate_limited` → "You're sending messages quickly. Please wait a moment." with `retry_after_s` |
| Message > 1000 chars | Counter blocks sending; server also rejects with `message_too_long` |
| `internal_error` mid-stream | Stream stops; "Sorry, something went wrong. Please try again." with retry of the same `client_turn_id` |
| Bot score low | 403 `bot_suspected` → message with the clinic phone |
| reCAPTCHA script blocked by an ad blocker | The widget sends `bot_token: null, client_reason: "script_unavailable"` → `strict` (patients with blockers can still chat, with tight limits) |
| Two tabs open | Two sessions (`sessionStorage` is per tab) |
| Patient closes the panel and reopens | Same session continues (iframe kept, hidden) |
| Clinic page uses a strict CSP | The clinic must allow our script and frame origins; documented in `embedding.md` |
| Emergency script reply | Rendered like any reply, never cut off by length limits |

## 9. Security, HIPAA and PHI
- **PHI handled:** the patient's messages and the assistant's replies (names, DOB, phones, symptoms, appointments) in the browser memory of the iframe, over TLS on the WebSocket, and in the encrypted Redis display history.
- **Never:** PHI in URLs, query strings, `postMessage`, cookies, `localStorage`, `sessionStorage` (only the session token and IDs), browser console, server logs, or any third-party script. The only third-party script is reCAPTCHA, which runs before any patient input and receives no PHI.
- **Isolation:** the widget runs on our origin in an iframe, so the clinic page's scripts cannot read the chat; `postMessage` carries only open/close/unread events with origin checks.
- **Access:** session token scoped to one session and clinic (P1-13); WebSocket re-checks idle and expiry.
- **Audit:** `security.bot_blocked`; session create/end already audited by P1-13 / P2-01.

## 10. Testing
```bash
cd backend && pytest tests/unit/api/test_ws_chat.py tests/unit/auth/test_bot.py -q
cd frontend && pnpm test            # Vitest: reducer, socket, session storage, protocol
pnpm e2e                            # Playwright: embed page on another origin, desktop + mobile
pnpm e2e:staging -- --grep latency  # staging first-chunk check
```
| # | Case | Expected |
|---|---|---|
| T1 | Embed on the test clinic page (allowed origin) | Launcher, iframe, greeting streams in |
| T2 | Embed on a non-allowed origin | Framing blocked |
| T3 | URL and network audit (Playwright request log) | No PHI in any URL; only slug and `session_id` |
| T4 | Streaming | Chunks appear in order; typing indicator on/off |
| T5 | Choice tap | `user_turn` with `choice_id`; label shown as the patient's message |
| T6 | Card and info card payloads | Plain renderers show all rows |
| T7 | Reconnect mid-turn (socket killed) | Reconnects; no duplicate turn; reply completes |
| T8 | Reload in the same tab | History restored; only the last choices active |
| T9 | Idle warning and expiry | Warning at T−120 s; expired text; new chat works |
| T10 | Rate limit | `rate_limited` message; input recovers |
| T11 | Bot: low score / invalid token / API down / script blocked | 403 block / 403 block / strict / strict |
| T12 | Automated abuse test (headless script creating sessions without a valid token) | Blocked; `security.bot_blocked` audited |
| T13 | Mobile viewport | Full screen; composer above the keyboard |
| T14 | Storage audit | No message text in any web storage or cookie |
| T15 | Protocol schema check | Python and TypeScript schemas match |
| T16 | Server log capture with PHI corpus | No PHI in logs |
| T17 | Staging latency | p50 send → first chunk ≤ 1 s over 20 turns |

## 11. Acceptance criteria
- [ ] The widget works in an iframe on a test clinic page, desktop and mobile, only on allowed origins (T1, T2, T13)
- [ ] No PHI in URLs, web storage, cookies or `postMessage` (T3, T14)
- [ ] First reply chunk shown ≤ 1 s (p50) on staging (T17)
- [ ] Replies stream sentence by sentence with a typing indicator; reconnect and reload never duplicate or lose a turn (T4, T7, T8)
- [ ] An automated abuse test is blocked by bot protection (T12)
- [ ] No third-party script except reCAPTCHA; no analytics (CSP and request audit, T3)
- [ ] No PHI in server logs (T16)

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI (Vitest, pytest, Playwright)
- [ ] PR reviewed (HIPAA review: labelled `phi`)
- [ ] No PHI in logs
- [ ] `docs/widget/embedding.md` and `docs/widget/protocol.md` written; additive changes to P1-13, P1-19 and P2-01 merged
- [ ] P2-27, P3, P4-11 and P6 onboarding issues notified

## 13. Hand-off
| Consumer | What they can rely on |
|---|---|
| P2-27 Cards and accessibility | Component boundaries `CardView`, `ChoiceChips`, `InfoCardView`, `MessageBubble` with typed props; `sendTurn(text, choiceId)` |
| P2-30 Staging E2E | Playwright harness, test clinic page, latency check |
| P3 Voice | Protocol version 1, socket client, avatar panel slot, `voice_enabled` flag, iframe `allow` attribute to change |
| P4-11 Console | `widget` config section and its load rules |
| P6 Onboarding | Embed snippet and allowed-origins setup |

## 14. Open questions
| # | Question | Recommended answer | Owner |
|---|---|---|---|
| 1 | Should the footer emergency line be shown before the first message? | Yes, always visible in small text; dentist confirms the wording with P0-03. | Product owner + dentist |
| 2 | Should we collect a post-chat rating (plan KPI ≥ 4.2/5)? | Yes, but in P2-27 or P6 as a simple 1–5 tap with no free text; not here. | Product owner |
| 3 | Do we need a CSP report endpoint for widget violations? | Yes in P5 hardening (report-only first); not needed for P2. | Tech lead |

## 15. References
- Plan: §3.1, §3.2, §6, §11, §12
- DECISIONS: #72, #85, #174, #193, #209, #210, #211
- Related tasks: P1-01, P1-02, P1-07, P1-13, P1-19, P2-01, P2-04, P2-16, P2-27, P2-30, P3, P4-11
- reCAPTCHA Enterprise assessments: <https://cloud.google.com/recaptcha/docs/create-assessment-website>
- Cloud Run WebSockets: <https://docs.cloud.google.com/run/docs/triggering/websockets>
- CSP `frame-ancestors`: <https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Security-Policy/frame-ancestors>
