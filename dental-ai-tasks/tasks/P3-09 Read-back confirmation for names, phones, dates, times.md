---
id: P3-09
title: Voice read-back of critical details (state-machine enforced) and spelling mode
milestone: P3
epic: E3.2
size: M
labels: area:voice, area:ai, type:feature, phi
depends_on: P3-02, P3-03, P3-06, P2-01, P2-04, P2-05, P2-08, P2-12, P2-22
status: approved
---

# P3-09: Voice read-back of critical details (state-machine enforced) and spelling mode

## 1. Summary
In voice, speech recognition can mishear "Smith" as "Smyth" or "503" as "513". Identification in Open Dental is an exact search (P2-12), so one wrong letter means "no record found". This task makes the assistant **read back** every critical detail heard by voice and get a clear "yes" before any code uses it. It also adds a **spelling mode**, so patients can spell names letter by letter. It absorbs **P3-10 (spelling mode)**.

| Part | What it does |
|---|---|
| Read-back gate | Critical slots filled from a VOICE turn are marked `unconfirmed`; the state machine enters the side state `READ_BACK` and resumes only after "yes". The tool gateway refuses any call that uses an unconfirmed slot |
| Batched read-back | All newly heard critical details from one turn are read back together (max 3), rendered by code only |
| Answers | Yes / no / correction ("no, it's 504…"); "no" alone asks which part, with quick-reply buttons |
| Failure ladder | 1st no → ask again; 2nd → spelling mode (names, email) or slow three-part phone / month-day-year DOB; 3rd → "you can type it in the chat"; then callback offer or the clinic phone |
| Spelling mode | Deterministic `SpellingParser`: plain letters, NATO words, "S as in Sam", "double T", dash / apostrophe / space; endpoint profile `spelling`; letter hints |

Done means:
- read-back is required by the state machine, not by the prompt;
- no tool ever runs with an unconfirmed voice value;
- spelled names match in tests;
- the text channel is unchanged (no read-back).

## 2. Why this matters
Plan §4.4: "Names, phone numbers, dates and times are read back … before use. Names can be spelled out letter by letter." The pilot target "critical-field accuracy ≥ 98% after read-back" and "0 duplicate patients" depend on it: a misheard last name either fails identification (frustrating) or, in registration, could create a near-duplicate record. The confirmation card (DECISIONS #174) catches errors before writes, but identification (P2-12) searches Open Dental **before** any card, so the read-back must happen at capture time.

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P3, Voice Pipeline & Avatar**.
- **NATO phonetic alphabet:** Alfa, Bravo, Charlie, Delta, Echo, Foxtrot, Golf, Hotel, India, Juliett, Kilo, Lima, Mike, November, Oscar, Papa, Quebec, Romeo, Sierra, Tango, Uniform, Victor, Whiskey, X-ray, Yankee, Zulu. Many US callers instead say "B as in boy".
- **What already exists:**
  - **P2-01** (approved): slot catalogue (`first_name`, `last_name`, `dob`, `phone`, `mobile_phone`, `zip`, `email`, …), `SlotMemory.set(name, value, source)`, side states with `resumes: true` and `resume_state`, `REVEAL_BY_STATE`, `UserTurn.channel`, `choice_id`.
  - **P2-04** (approved): templates `read_back` (text and voice variants), `{read_back_value}`, phone voice rendering `5-0-3, 5-5-5, 0-1-2-3`; "DOB is never read back" (changed here for voice, DECISIONS #239).
  - **P2-05** (approved): normalizers (spelled letters joined, DOB forms, phones with words), `invalid_slots`, corrections.
  - **P2-08** (approved): tool gateway checks 1–6.
  - **P2-12** (approved): IDENTIFY collects first name, last name, DOB, phone (or ZIP) before searching; `identify_retry` asks for the spelling.
  - **P2-22** (approved): reason registry, callback flow and card.
  - **P3-02 / P3-03 / P3-06** (approved): `set_endpoint_profile("spelling")`, `SpeechNormalizer.digits()` / `spell()`, phrase hints per state, backchannel "yes" over a question is not an answer.

## 4. Scope
**In scope**
- `readback` flag in the slot catalogue; `unconfirmed` tracking in `SlotMemory`.
- Side state `READ_BACK` (flow YAML), its handler, the resume rule, the gateway check.
- `ReadBackRenderer` (code-built sentence and chat text), templates and quick replies.
- `ReadBackAnswerParser` (yes / no / correction / unclear).
- Failure ladder with per-field counters; callback reason `voice_capture_failed`.
- `SpellingParser`, spelling mode entry/exit, endpoint profile and hints.
- Unit, flow and voice-replay tests.

**Out of scope** (and which task covers it)
- Confirmation cards for writes → P2-27 / P2-04 (unchanged)
- STT accuracy and hints in general → P3-03
- Transcript and avatar UI → P3-11
- Read-back in the text channel → not done (the patient sees what they typed; DECISIONS #238)

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P2-01 / P2-04 / P2-05 / P2-08 (approved) | State machine, templates, extraction, gateway | Additive changes listed in §6; test with the in-memory store and `FakeLlmProvider` |
| P3-02 / P3-03 (approved) | Endpoint profile, normalizer, hints | Call the interfaces; unit tests use fakes |
| Voice pipeline end to end | Real audio | Flow tests send `UserTurn(channel="VOICE")` text directly; replay tests use the P3-01 audio set plus 20 new spelling recordings |

## 6. Interface contract

### Which slots, when (DECISIONS #238)
| Slot | Read back in voice | Rendered as (voice) |
|---|---|---|
| `first_name` | yes | "Priya" (spelled only after a correction: "Priya, P-R-I-Y-A") |
| `last_name` | yes | "Smith, S-M-I-T-H" (always spelled: Open Dental search is exact) |
| `dob` | yes (DECISIONS #239) | "born March fourth, nineteen eighty-five" |
| `phone`, `mobile_phone` | yes | "phone 5-0-3, 5-5-5, 0-1-2-3" |
| `email` | yes | local part spelled, common domains said: "j, dot, S-M-I-T-H, at gmail dot com" |
| `zip` | yes | "ZIP code 9-7-2-0-1" |

- Applies only when the slot was set from a turn with `channel="VOICE"` and `source="patient"`. Values from tools (Open Dental) or typed turns are confirmed at once.
- Appointment date, time and dentist are **not** read back here: the confirmation card and `{spoken_summary}` cover them (DECISIONS #174).
- `address` is not read back by voice (too long); the registration card shows it, and the voice flow invites typing for it (P2-15 asks it once, skippable).

### Slot memory additions (P2-01)
```python
# slot_catalogue.py: new column
READBACK_SLOTS: frozenset[str] = frozenset({"first_name", "last_name", "dob", "phone", "mobile_phone", "email", "zip",
                                           "whatsapp_number"})   # whatsapp_number: P4-02, DECISIONS #254

class SlotMemory:
    def set(self, name, value, *, source, channel: Literal["TEXT", "VOICE"] = "TEXT") -> None: ...
        # VOICE + patient + name in READBACK_SLOTS → also add name to the person frame's `unconfirmed` set
    def unconfirmed(self) -> frozenset[str]: ...
    def confirm(self, names: Iterable[str]) -> None: ...
```
Redis: hash field `p{index}:_unconfirmed` (JSON list of slot names, not PHI). Clearing a slot also removes it from `unconfirmed`.

### State machine (P2-01 flow YAML addition)
```yaml
READ_BACK:
  kind: side
  resumes: true
  collects: [readback_answer]
  allowed_tools: []
  reply: template_only            # never an LLM reply in this state
events:
  readback_needed: {from: "*voice_capturing", to: READ_BACK}   # fired by the turn processor, see below
```
**Turn processor rule (new step 6b, after extraction and slot validation):** if `turn.channel == "VOICE"` and `slots.unconfirmed()` is not empty → fire `readback_needed` (saves `resume_state`), **skip the state's handler for this turn**, reply `read_back`. A pending `proposed_event` from the same extraction is kept in `ConversationState.deferred_event` and re-proposed on resume.

**On confirmation:** `slots.confirm(fields)`, fire `resume`, then call the resumed state's `on_turn` with `Extraction(understood=True, slots={}, proposed_event=deferred_event)` in the same turn, so the flow continues without the patient repeating anything (e.g. IDENTIFY now has all four identifiers → search).

**Gateway (P2-08, new check 2b):** a tool call whose arguments are built from any slot in `slots.unconfirmed()` is refused with `GatewayRefusal("unconfirmed_slot")` and audited. This holds even if a handler bug skips the state.

**Emergency first:** P2-20 still runs before everything; an emergency during `READ_BACK` leaves it as any side state does.

### Rendering (`backend/app/voice/readback.py`)
```python
class ReadBackItem(NamedTuple):
    field: str
    voice: str                 # "Smith, S-M-I-T-H"
    text: str                  # "Last name: Smith"

class ReadBackRenderer:
    def items(self, slots: SlotMemory, fields: Sequence[str], spelled: frozenset[str]) -> list[ReadBackItem]: ...
    def sentence(self, items: list[ReadBackItem]) -> tuple[str, str]: ...    # (voice, chat text)
```
- At most 3 items per read-back (order: `last_name`, `first_name`, `dob`, `phone`, `mobile_phone`, `zip`, `email`); more → a second read-back right after the first is confirmed.
- Values come from `SlotMemory` in code; they never pass through the LLM. `REVEAL_BY_STATE["READ_BACK"]` = the pending fields, used only by the template renderer.
- Chat text shows the same items as a short list (the patient can read and tap).

### Templates (P2-04 additions)
```yaml
read_back:
  text:  "Let me check I have that right: {read_back_value}. Is that correct?"
  voice: "Let me check I have that right: {read_back_value}. Is that correct?"
readback_which:        {text: "Sorry about that. Which part should I fix?"}               # with one choice per item
readback_ask_again:    {text: "{slot_question}"}                                           # P2-04 slot_questions
readback_spell:        {text: "Could you spell it for me, letter by letter?"}
readback_phone_slow:   {text: "Could you say the number slowly, in three parts? First the area code."}
readback_dob_parts:    {text: "Could you tell me the month, then the day, then the year?"}
readback_type_it:      {text: "You can also type it in the chat below, if that's easier."}
readback_call_us:      {text: "I'm sorry I'm having trouble with that. You can reach our team at {public_phone}."}
```
**Quick replies (P2-16 `Choice`):** `rb:yes` "Yes, that's right"; `rb:fix:<field>` "Fix last name", etc. (one per item). Mapped by code, no LLM.

### Answer parsing (`ReadBackAnswerParser`)
| Input (normalized) | Result |
|---|---|
| `rb:yes` choice; "yes", "yeah", "yep", "correct", "that's right", "right", "yes it is" | `yes` |
| `rb:fix:<field>` | `fix(field)` → ask that field again |
| "no" / "nope" / "that's wrong" with nothing else | `no` → `readback_which` (single item → ask it again directly) |
| "no" + a value, or a value alone ("it's 504 555 0123", "S-M-Y-T-H") | `correction` → P2-05 extraction for the pending fields → new value set (still unconfirmed) → read back again |
| Anything else | P2-05 extraction with `readback_answer ∈ {yes, no, correction, unclear}`; `unclear` → repeat the read-back once, then treat as `no` |
A "yes" heard over the read-back question is a backchannel (P3-06) and never counts.

### Failure ladder (per person, per field; DECISIONS #240)
| Failed read-backs for the field | Next step |
|---|---|
| 1 | Ask the field again (`readback_ask_again`) |
| 2 | Names / email → spelling mode (`readback_spell`); phone → `readback_phone_slow`; DOB → `readback_dob_parts`; ZIP → ask again |
| 3 | `readback_type_it` (text input is always open); a typed value is confirmed at once |
| 4 | Outside the callback flow: offer a callback (P2-22 reason `voice_capture_failed`). Inside the callback flow (its own contact fields failing): `readback_call_us` with the clinic `public_phone`, and the session continues in text |
Counters live in `ConversationState.readback_failures` (`{field: n}`, no PHI) and reset when the field is confirmed.

### Spelling mode (`backend/app/voice/spelling.py`)
```python
class SpellingParser:
    MAX_LEN = 40
    def parse(self, text: str) -> str | None: ...        # None = no letters found
```
| Input | Output |
|---|---|
| "S M I T H", "s-m-i-t-h", "S. M. I. T. H." | `Smith` |
| "Sierra Mike India Tango Hotel" | `Smith` |
| "S as in Sam, M as in Mary, I T H" | `Smith` |
| "B for boy O double T" | `Bott` |
| "O apostrophe B R I E N" | `O'Brien` |
| "M A R Y dash J O" / "hyphen" | `Mary-Jo` |
| "D E space L A" | `De La` |
| "capital M C capital D O N A L D" | `McDonald` ("capital" keeps the next letter upper case) |
| "Smith" (a whole word, no letters) | `Smith` (accepted; read back spelled) |
| Digits or > 40 letters | `None` → ask again |
Casing: first letter and letters after `-`, `'` or space upper case; others lower unless "capital".

**Entry:** failure ladder step 2; P2-12 `identify_retry`; the patient says "let me spell it" / "I'll spell it" (P2-05 extraction flag `wants_to_spell`). **While active:** `ConversationState.spelling_field = <field>`; P3-02 `set_endpoint_profile("spelling")` (1500 ms); P3-03 hints add the letter class and NATO words. **Exit:** after the spelled value is read back and confirmed, or the ladder moves on.

### Logs and metrics (no PHI)
| Item | Fields |
|---|---|
| `readback.asked` | `fields` (names only), `items`, `attempt` |
| `readback.result` | `field`, `outcome` (`yes` / `fix` / `correction` / `unclear` / `typed`), `attempt` |
| `readback.spelling` | `field`, `parsed` (bool), `style` (`letters` / `nato` / `as_in` / `word`) |
| `gateway.refused` | reason `unconfirmed_slot` (P2-08 audit) |
| Counter `dai.readback.corrections` | by field (P3-14 reports "critical-field accuracy after read-back") |
Never logged: the values, the spelled letters, the rendered sentence.

## 7. Implementation guide
1. **Slot memory:** `READBACK_SLOTS`, `channel` on `set()`, `unconfirmed()` / `confirm()`, Redis field, clearing rule.
2. **Flow YAML and turn processor:** `READ_BACK` side state, step 6b, `deferred_event`, resume-and-continue.
3. **Gateway check 2b** and audit.
4. **Renderer, templates, choices** (P2-04 / P2-16 additions).
5. **Answer parser** with the table above; P2-05 extraction fields `readback_answer`, `wants_to_spell`.
6. **Failure ladder** and the P2-22 reason `voice_capture_failed`.
7. **Spelling parser** and mode entry/exit (endpoint profile, hints).
8. **Tests** (§10) including 20 new consented spelling recordings in the replay set (synthetic names).
9. **Docs** `docs/voice/read-back.md`. Notify P2-12, P2-15, P2-22, P3-11, P3-14.

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| Patient gives name, DOB and phone in one breath | One read-back with 3 items; "yes" → IDENTIFY searches in the same turn |
| Patient corrects only the phone ("no, 504…") | Phone updated; name and DOB stay unconfirmed (a "no" confirms nothing); the next read-back repeats all pending items (max 3) and one "yes" confirms them all |
| Patient says "yes, but my last name is Smyth" | Correction wins over yes |
| Patient switches to typing during `READ_BACK` | Typed "yes" works; a typed corrected value is confirmed at once |
| Value heard in voice, then the patient types the same field | Typed value replaces it, confirmed; removed from `unconfirmed` |
| Household (DECISIONS #185): parent gives a child's details | Read-back per person frame; item text names the person ("Your son's date of birth…") using the frame's first name |
| Emergency words during read-back | P2-20 runs first; `READ_BACK` is left like any side state |
| A handler bug calls a tool with an unconfirmed slot | Gateway refuses (`unconfirmed_slot`), audited; turn replies `rephrase_please` |
| STT turns letters into a word ("ess em eye tee aitch") | Parser maps letter names (ess, em, eye, tee, aitch, double-u, zed, …) |
| Spelled name with an accent ("José") | Letters only; read back "J-O-S-E"; Open Dental search behaviour for accents is P2-12's concern (**Verify**) |
| Barge-in during the read-back sentence | P3-06 rules; the patient's words are processed as the answer |

## 9. Security, HIPAA and PHI
- **PHI handled:** first and last name, DOB, phone, ZIP, email — read from slot memory (encrypted in Redis, P2-01), rendered by code, sent to Text-to-Speech (BAA, P3-03) and shown in the patient's own chat.
- **Never to the LLM:** read-back values (rendered by template in `READ_BACK`, where replies are template-only). Extraction in `READ_BACK` still sees only the masked view.
- **DOB exception (DECISIONS #239):** DOB is spoken back only in voice and only by this template, a few seconds after the patient said it; text read-back never shows it (the text channel has no read-back; cards show DOB as before).
- **Logs:** field names and outcomes only.
- **Defence in depth:** the gateway refuses unconfirmed values even if the state machine is bypassed.

## 10. Testing
```bash
cd backend && pytest tests/unit/voice/test_readback.py tests/unit/voice/test_spelling.py -q
pytest tests/flows/test_readback_flows.py -q          # VOICE UserTurns through the real state machine
python scripts/voice/replay_readback.py --audio spikes/p3-01-voice-latency/audio --target dev
```
| # | Case | Expected |
|---|---|---|
| T1 | VOICE turn sets last name, DOB, phone | `READ_BACK` entered; handler not called; one read-back with 3 items |
| T2 | "Yes" | Slots confirmed; resume; IDENTIFY searches in the same turn |
| T3 | TEXT turn sets the same slots | No read-back |
| T4 | Gateway with an unconfirmed slot (forced) | Refused `unconfirmed_slot`, audited |
| T5 | Correction with value | New value, read back again |
| T6 | "No" alone with 3 items | `readback_which` with 3 fix choices |
| T7 | Failure ladder | Steps 1–4 per field as in the table |
| T8 | Spelling parser table (≥ 40 cases) | Exact outputs |
| T9 | Spelling mode | Profile `spelling` set and cleared; hints include letters |
| T10 | DOB rendering | Voice "born March fourth, nineteen eighty-five"; never in LLM context |
| T11 | Replay: 20 spelled names | ≥ 95% parsed correctly (spelled names match) |
| T12 | Backchannel "yes" during the question | Not counted |
| T13 | Household frames | Read-back per active person |
| T14 | Logs | No values in logs (log capture) |

## 11. Acceptance criteria
- [ ] Read-back is required by the state machine, not the prompt: voice-captured critical slots cannot reach a handler or tool until confirmed (T1, T2, T4)
- [ ] Corrections update slot memory and are read back again (T5, T6)
- [ ] Spelled names match in tests (T8, T11)
- [ ] The failure ladder ends in typing, a callback or the clinic phone, never a loop (T7)
- [ ] Text-channel behaviour is unchanged (T3)
- [ ] No read-back value goes to the LLM or the logs (T10, T14)

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI; replay report linked in the PR
- [ ] PR reviewed (HIPAA review: labelled `phi`)
- [ ] No PHI in logs
- [ ] `docs/voice/read-back.md` written; P2-01, P2-04, P2-05, P2-08 and P2-22 additive changes merged
- [ ] P2-12, P2-15, P3-11 and P3-14 notified

## 13. Hand-off
| Consumer | What they can rely on |
|---|---|
| P2-12 / P2-15 | In voice, identifiers reach the handler only after confirmation; spelling mode for `identify_retry` |
| P2-22 | Reason `voice_capture_failed`; contact fields are read back too |
| P3-11 | Read-back items in chat with fix buttons |
| P3-14 | `readback.result` metrics for critical-field accuracy |

## 14. Open questions
| # | Question | Recommended answer | Owner |
|---|---|---|---|
| 1 | Should a confirmed returning patient skip read-back of values Open Dental already confirmed? | Yes: values that came from a tool are confirmed by definition; only voice-heard values are read back. | Tech lead |
| 2 | Should the read-back list in chat hide the DOB? | No: it is the patient's own session and the card shows it anyway. | Product owner |
| 3 | Should we support "B as in boy" for every letter or only common words? | Every letter: take the first letter of the word after "as in" / "for". | Tech lead |

## 15. References
- Plan: §4.4, §4.5, §11
- DECISIONS: #174, #181, #185, #227, #231, #234, #238, #239, #240
- Related tasks: P2-01, P2-04, P2-05, P2-08, P2-12, P2-15, P2-16, P2-20, P2-22, P3-02, P3-03, P3-06, P3-11, P3-14
