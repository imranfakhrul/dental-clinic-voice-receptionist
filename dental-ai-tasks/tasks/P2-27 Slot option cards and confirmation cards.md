---
id: P2-27
title: Slot option cards, confirmation cards and the widget accessibility pass
milestone: P2
epic: E2.6
size: M
labels: area:frontend, type:feature, phi
depends_on: P2-25, P2-04, P2-08, P2-16, P2-20
status: approved
---

# P2-27: Slot option cards, confirmation cards and the widget accessibility pass

## 1. Summary
Replace P2-25's plain renderers with the designed, accessible components patients actually use, and make the whole widget accessible. This task absorbs **P2-28 (accessibility pass: keyboard, screen reader, text-only mode)**.

| Component | What it shows | What a tap sends |
|---|---|---|
| `SlotOptionCards` | 2–3 real openings: day and date, time with zone, dentist | `choice_id = "opt:N"` (P2-16) |
| `ChoiceChips` | Other quick replies ("Later times", reason menu, "Skip") | the choice's `id` |
| `ConfirmationCard` | Every detail before a write, patient first (DECISIONS #174) | "Yes, that's correct" → `confirm:yes:<op_hash>`; row "Change" → `change:<field>` |
| `InfoCard` | Booked / rescheduled / cancelled result; appointment list with Reschedule / Cancel | list actions `apt:A1:reschedule` / `apt:A1:cancel` |
| `EmergencyBanner` | Emergency script replies | `tel:911` link (no message sent) |

Done means:
- a tapped card goes through exactly the same confirmation rule as a typed or spoken "yes" (P2-08 operation hash);
- a stale or mismatched card can never cause a write;
- the widget meets WCAG 2.2 AA with an axe scan of 0 critical and 0 serious issues;
- everything works by keyboard and with VoiceOver and NVDA;
- a text-only mode exists.

## 2. Why this matters
Plan §2 #3 wants the patient to pick from 2–3 real options, and plan §3.1 asks for a "keyboard-accessible, text-only mode" chat panel. The cards are where patients check what will be written to Open Dental, so they carry the trust the user asked for: "all details written in the chat window, check them, say yes or tell me what to change" (DECISIONS #174). Taps also remove LLM calls (faster, no misunderstanding). Accessibility matters legally for US healthcare websites (ADA expectations) and practically for older patients and screen-reader users.

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P2, Text Chat Receptionist**.
- **WCAG 2.2 AA:** the W3C accessibility standard; level AA covers contrast (4.5:1 text), keyboard access, visible focus, target size (24 × 24 px minimum), and status messages announced without moving focus. <https://www.w3.org/TR/WCAG22/>.
- **ARIA live region:** an element whose changes screen readers announce automatically (`aria-live="polite"` waits for a pause; `"assertive"` interrupts). <https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Guides/Live_regions>.
- **axe-core:** an automated accessibility checker; `@axe-core/playwright` runs it inside Playwright tests. <https://github.com/dequelabs/axe-core-npm/tree/develop/packages/playwright>.
- **What already exists:**
  - **P2-25** (approved): widget shell, protocol v1, `sendTurn(text, choiceId)`, component boundaries `MessageBubble`, `CardView`, `ChoiceChips`, `InfoCardView`, history after reload (older choices disabled), clinic accent color (contrast-checked).
  - **P2-04** (approved): `ConfirmationCard{kind, title, rows[CardRow{label, value, field}], op_hash}`; card kinds `book`, `reschedule`, `cancel`, `register`, `callback`; `ReplyChunk.source`; emergency replies come from scripts.
  - **P2-16** (approved): `Choice{id, label}` with ids `opt:N`, `later`, `reason:<code>`, `apt:A1:reschedule|cancel`; `InfoCard{kind: booked|appointment_list|rescheduled|cancelled, title, rows, actions}`; a tapped choice maps to slots/events without an LLM call.
  - **P2-08** (approved): a write needs the `confirmation` slot `{answer: "yes", op_hash, at}` whose `op_hash` equals the operation's hash; mismatch → `confirmation_mismatch` / `confirm_again`; single use, 10 minutes.
  - **P2-05** (approved): typed confirmation answers `yes` / `no` / `change` + `change_target`.

## 4. Scope
**In scope**
- Components in §6 with Tailwind styling, the clinic accent color, light theme only (dark theme not in MVP).
- Two new choice-id families and their server-side mapping (`confirm:yes:<op_hash>`, `change:<field>`), with the same P2-08 checks.
- Card and choice states: active, submitted, stale (superseded).
- Accessibility across the whole widget: keyboard, focus, live regions, labels, contrast, target sizes, reduced motion, zoom to 200%, text-only mode.
- axe in CI and a manual screen-reader test script.

**Out of scope** (and which task covers it)
- Post-chat rating → P6-02 (absorbed P6-03)
- Voice controls and the animated avatar → P3
- Admin console accessibility → P4 console tasks
- Translations (English only in MVP)

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P2-25 (approved) | Shell, socket, component props | Storybook-style fixtures in `frontend/app/widget/__fixtures__/` with recorded `ReplyChunk` JSON |
| P2-04 / P2-16 (approved) | Card and choice JSON | Same fixtures |
| P2-08 (approved) | Confirmation check | Server unit tests with the gateway's test double |

## 6. Interface contract

### Choice-id families (complete list, additive to P2-16; DECISIONS #213)
| `choice_id` | Sent by | Server mapping (turn processor, no LLM call) |
|---|---|---|
| `opt:N` | Slot card | `chosen_slot_ref = "N"` (P2-16) |
| `later` | Chip | `want_later` (P2-16) |
| `reason:<code>` | Reason chip | `reason_code` (P2-16) |
| `apt:A1:reschedule` / `apt:A1:cancel` | Appointment list action | `intent_changed` (P2-16, P2-18) |
| `cr:<code>` | Cancel-reason chip | `cancel_reason` (P2-18) |
| **`confirm:yes:<op_hash>`** | Confirmation card button | `confirmation = {answer: "yes", op_hash: <from the id>, at: now}` — the gateway then compares it with the pending operation's hash exactly as for a spoken "yes" |
| **`change:<field>`** | Row "Change" link | `confirmation = "change"`, `change_target = <field>` → event `change_requested` (P2-05 / P2-16 rules) |
| any other id defined by a flow (e.g. `ptype:new`) | Chip | the owning flow's mapping |

Rules:
- `<op_hash>` is the card's `op_hash` (hex, no PHI: it is an HMAC). If it differs from the current `pending_confirmation.op_hash` (stale card, or the details changed), the turn processor does **not** record a confirmation; it replies `confirm_again` and shows the current card. A forged id therefore cannot write anything the patient wasn't shown (DECISIONS #214).
- `<field>` must be one of the card's own `CardRow.field` values; otherwise the id is ignored and treated as text.
- Unknown `choice_id` → ignored; the label text goes through normal extraction.

### Components (`frontend/app/widget/components/`)
```ts
type SlotOption = { id: string; dayLabel: string; dateLabel: string; timeLabel: string; dentist?: string };   // parsed from Choice.label parts (see below)

function SlotOptionCards(p: { options: SlotOption[]; extra: Choice[]; state: CardState; onPick(id: string, label: string): void }): JSX.Element;
function ChoiceChips(p: { choices: Choice[]; state: CardState; onPick(id: string, label: string): void }): JSX.Element;
function ConfirmationCardView(p: { card: ConfirmationCard; state: CardState; onConfirm(): void; onChange(field: string, label: string): void }): JSX.Element;
function InfoCardView(p: { card: InfoCard; state: CardState; onAction(id: string, label: string): void }): JSX.Element;
function EmergencyBanner(p: { text: string }): JSX.Element;

type CardState = "active" | "submitted" | "stale";
```
- **Slot labels:** P2-16 builds `Choice.label` as `"Tue, Dec 8 · 9:00 AM PST · Dr. Lee"`; the component splits on `" · "` for layout only. Additive to P2-16: `Choice.parts?: string[]` (the same three parts) so the frontend never parses free text; the label stays the accessible name.
- **Which choices are cards:** ids starting `opt:` → `SlotOptionCards`; everything else in the same message → chips under the cards.
- **State:** the last assistant message's controls are `active`. After a tap → `submitted` (the chosen one shows a check mark, the rest disabled). When a newer message arrives → all earlier controls `stale` (disabled, `aria-disabled="true"`, visually muted, tooltip "No longer available").
- **Emergency:** a chunk whose reply intent is an emergency script (P2-25 adds `style: "emergency"` to `reply_chunk`, set by the server for P0-03 script replies) renders as `EmergencyBanner`: red border, warning icon with text label "Emergency", body text, a `tel:911` link "Call 911" (and `tel:988` for the crisis script), not dismissible.

### Confirmation card layout
```
┌ Please check your appointment details ─────────────┐
│ Patient        Jane Doe                    Change  │
│ Visit          Cleaning and checkup        Change  │
│ Date and time  Tue, Dec 8, 2026, 9:00 AM PST Change│
│ Dentist        Dr. Lee                     Change  │
│ Location       Smile Dental, 100 Main St   (none)  │
│                                                    │
│ [ Yes, that's correct ]                            │
│ You can also type or say what to change.           │
└────────────────────────────────────────────────────┘
```
- Implemented as a `<section aria-labelledby>` with a `<dl>` (label/value pairs); "Change" links are `<button>`s named "Change {label}" (e.g. "Change Date and time").
- Rows whose field can't be changed from the card (`location`) have no Change button.
- DOB is shown as `MM/DD/YYYY` (as P2-04 renders it); nothing is hidden or masked on the card (it is the patient's own session).

### Accessibility requirements (DECISIONS #215)
| Area | Requirement |
|---|---|
| Structure | Widget is a `role="dialog"` with `aria-label="{clinic} virtual assistant"`; message list is a `role="log"` with `aria-live="polite"`; each message has a visually hidden "Assistant:" / "You:" prefix |
| Announcements | New assistant messages announced once when `final` arrives (not per chunk); emergency banner `aria-live="assertive"`; errors and connection banners `role="status"` (or `alert` for session expiry) |
| Focus | Focus stays in the composer after sending; never moved automatically to new cards; `Tab` reaches cards in reading order; visible focus ring 2 px, 3:1 contrast |
| Keyboard | All controls are native buttons/links; slot cards are a group (`role="group"`, `aria-label="Available times"`) of buttons; Enter/Space activate; Escape closes the widget (sends `dai:close`); no keyboard traps |
| Target size | ≥ 44 × 44 px for cards, chips and the send button (exceeds AA's 24 px) |
| Contrast | Text 4.5:1, large text and UI parts 3:1, including the clinic accent color (P2-25 load check) and stale/muted states that still carry text (stale text ≥ 4.5:1; only borders are muted) |
| Motion | Typing dots and transitions disabled when `prefers-reduced-motion: reduce` or text-only mode |
| Zoom | Usable at 200% zoom and 320 px CSS width without horizontal scrolling |
| Text-only mode | Header toggle "Text only": hides the avatar panel and all animation; adds a "Larger text" option (base font 18 px → 22 px); state kept in `sessionStorage` (`dai:ui`, no PHI) |
| Labels | Composer has a visible label ("Type your message"); character counter announced only when ≤ 50 left |
| Language | `lang="en"` |

### Server-side changes (small, additive)
- P2-01 turn processor: the two new choice-id families (§6 table).
- P2-25 protocol: `reply_chunk.style?: "emergency"`; `Choice.parts?` passthrough.

## 7. Implementation guide
1. **Fixtures**: record one `ReplyChunk` stream per card kind, each info card, chips, emergency script and stale history (from P2-16/P2-18/P2-20 tests).
2. **Components** with Tailwind; reuse the accent color via a CSS variable; snapshot tests (Vitest + Testing Library).
3. **Choice-id mapping** on the server (P2-01) with unit tests for match, mismatch (stale), forged field, unknown id.
4. **State handling** in the P2-25 reducer: active / submitted / stale.
5. **Accessibility pass** across the whole widget (§6 table), including P2-25's components.
6. **axe in CI**: Playwright test opens each fixture state and runs `AxeBuilder({page}).withTags(["wcag2a","wcag2aa","wcag21a","wcag21aa","wcag22aa"]).analyze()`; fail on any `critical` or `serious` violation.
7. **Manual screen-reader script** `docs/widget/a11y-test-script.md`: book an appointment with VoiceOver (Safari, macOS and iOS) and NVDA (Firefox or Chrome, Windows), keyboard only; record results in the PR.
8. **Notify** P2-30 (E2E uses taps), P3 (banner and live region rules for voice transcript), P6-02 (rating component will follow these rules).

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| Patient taps "Yes" on a card, then the card in history again after reload | History card is `stale` (disabled); a forged replay is rejected by hash or single use |
| Details changed (patient said "change the time") and an old card is tapped by a script | Hash mismatch → `confirm_again`, new card shown, nothing written |
| Confirmation expired (> 10 min) | Gateway `confirm_again` (P2-08); new card |
| Patient taps two slot cards quickly | First tap sends; the rest disabled immediately (`submitted`) |
| Patient types "yes" instead of tapping | Same rule (P2-05 extraction) |
| A row value is long (address) | Wraps; no truncation of confirmation details |
| Three options plus "Later times" on a 320 px screen | Cards stack vertically; chip below |
| Appointment list with 10 rows | Each row its own group with two action buttons named "Reschedule Tue Dec 8 9:00 AM" / "Cancel …" |
| Emergency script arrives during an active confirmation | Banner shown; card becomes `stale` (the state machine left `CONFIRM`) |
| Screen reader user while replies stream | One announcement per message at `final`, not per sentence |
| Clinic accent color fails contrast | Load check rejected it in P1-19/P2-25; default color used |
| Voice session (P3) | Same components; spoken "yes" and taps both work |

## 9. Security, HIPAA and PHI
- **PHI shown:** card values (names, DOB, phone, appointment details) in the patient's own session only, rendered as text nodes (no `dangerouslySetInnerHTML`).
- **No PHI** in `choice_id` values: `op_hash` is an HMAC (P2-08), fields are names, appointment handles are session-local (`A1`). Nothing new is stored in web storage except the UI preference (`dai:ui`).
- **Integrity:** a write still requires the exact operation hash; a tap is just another way to say yes and cannot widen what is written.
- **Logs:** taps are logged as `choice_family` (e.g. `confirm`, `opt`), never labels.

## 10. Testing
```bash
cd frontend && pnpm test                       # component and reducer tests
pnpm e2e -- --grep a11y                        # axe on every fixture state
cd ../backend && pytest tests/unit/orchestrator/test_choice_ids.py -q
```
| # | Case | Expected |
|---|---|---|
| T1 | Slot cards render 2–3 options with day, date, time + zone, dentist | Matches fixture |
| T2 | Tap a slot card | `user_turn` with `opt:N` and the label; others disabled |
| T3 | Confirmation card tap "Yes" | `confirm:yes:<op_hash>`; booking proceeds through P2-08 (integration with `od_fake`) |
| T4 | Stale card tap (hash differs) | No write; `confirm_again`; new card |
| T5 | Forged `change:<field>` not on the card | Ignored as an id; text extraction |
| T6 | Row "Change Date and time" | `change_requested` with `time`; back to availability |
| T7 | Info cards (booked, list with actions) | Rows and actions correct; actions send `apt:*` ids |
| T8 | Emergency banner | Red banner, `tel:911`, assertive region, cannot be dismissed |
| T9 | Keyboard-only booking (Playwright) | Whole flow without a mouse; no trap; Escape closes |
| T10 | axe on every state (cards active/submitted/stale, errors, idle, emergency, text-only, mobile) | 0 critical, 0 serious |
| T11 | Live region | One announcement per assistant message |
| T12 | 200% zoom and 320 px width | No horizontal scroll; all controls reachable |
| T13 | Reduced motion / text-only | No animation; avatar hidden; larger text works |
| T14 | Manual VoiceOver + NVDA script | Completed and recorded in the PR |

## 11. Acceptance criteria
- [ ] Card selection goes through the same confirmation rule as a typed or spoken yes; a stale or forged tap never writes (T3, T4, T5)
- [ ] Slot options appear as cards and confirmations as full cards with per-row Change, matching DECISIONS #174 (T1, T6)
- [ ] axe scan: 0 critical and 0 serious issues on every widget state (T10)
- [ ] The full booking flow works by keyboard only and with VoiceOver and NVDA (T9, T14)
- [ ] Text-only mode and reduced motion work (T13)
- [ ] Emergency replies show the non-dismissible banner with a call link (T8)

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI; axe check is a required CI step
- [ ] PR reviewed (HIPAA review: labelled `phi`)
- [ ] No PHI in logs
- [ ] `docs/widget/components.md` and `docs/widget/a11y-test-script.md` written; additive changes to P2-01, P2-16 and P2-25 merged
- [ ] P2-30, P3 and P6-02 issues notified

## 13. Hand-off
| Consumer | What they can rely on |
|---|---|
| P2-30 Staging E2E | Stable `data-testid`s on cards, chips, Yes and Change buttons |
| P3 Voice | Components work during voice; banner and live-region rules for the transcript |
| P6-02 Rating | **Not built** (user decision, DECISIONS #281); nothing to reuse |
| P4 console | The same accessibility checklist as a starting point |

## 14. Open questions
| # | Question | Recommended answer | Owner |
|---|---|---|---|
| 1 | Should the widget offer a dark theme? | Not in the MVP; light theme with AA contrast only. | Product owner |
| 2 | Should the confirmation card include an "Add to calendar" button after booking? | Not here; tracked with P2-16's open question (post-MVP). | Product owner |
| 3 | Do we need an external accessibility audit before the pilot? | Recommended in P5 hardening (one expert review), not blocking P2. | Tech lead |

## 15. References
- Plan: §2 #3, §3.1, §4.4, §4.6
- DECISIONS: #174, #193, #209, #213, #214, #215
- Related tasks: P2-01, P2-04, P2-05, P2-08, P2-16, P2-18, P2-20, P2-25, P2-30, P3, P6-02
- WCAG 2.2: <https://www.w3.org/TR/WCAG22/>
- ARIA live regions: <https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Guides/Live_regions>
- axe-core Playwright: <https://github.com/dequelabs/axe-core-npm/tree/develop/packages/playwright>
