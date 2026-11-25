---
id: P2-16
title: Booking flow (reason → type → 2–3 options → confirm → book) and checking existing appointments
milestone: P2
epic: E2.4
size: L
labels: area:ai, area:scheduling, type:feature, phi
depends_on: P0-02, P0-04, P1-19, P1-20, P1-22, P2-01, P2-04, P2-05, P2-08, P2-12
status: approved
---

# P2-16: Booking flow (reason → type → 2–3 options → confirm → book) and checking existing appointments

## 1. Summary
Build the state handlers that turn "I'd like an appointment" into a real Open Dental appointment, plus "when is my appointment?". This task absorbs **P2-17 (check existing appointment flow)**.

| State | Handler does |
|---|---|
| `APPOINTMENT_TYPE` | Turns the patient's reason into a P0-02 `reason_code` with no diagnosis; asks one fixed clarifying question if unclear; checks `bookable` |
| `AVAILABILITY` | Gets 2–3 real options from P1-20, shows them as text plus tappable choices, handles "later" and preference changes |
| `CONFIRM` | Shows the confirmation card (patient named first) and waits for yes / change |
| `BOOK` | Calls `book_appointment` through the gateway and maps every P1-20 outcome |
| `CHECK_APPOINTMENT` | Lists the verified active patient's upcoming appointments as a card list with Reschedule / Cancel actions |

Done means:
- a verified patient can go from reason to a booked appointment in one conversation;
- the AI says "booked" only after Open Dental confirms;
- a conflict apologizes and re-offers fresh options;
- an uncertain outcome never claims success;
- only the active verified patient's appointments are ever listed;
- the end-to-end booking passes on staging.

## 2. Why this matters
Booking is the product's main job (plan §2, §4.6). Plan §4.6:
- "Offer 2–3 options at a time, phrased naturally";
- the booking sequence ends with "confirm to patient";
- "The appointment is only 'booked' once Open Dental confirms creation";
- "On conflict: apologize, re-fetch and offer alternatives."

Pilot targets driven here:
- **≥ 70% bookings without callback**;
- **0 double bookings**, together with P1-20 and P2-08;
- patients trusting what they see in the chat window: the user asked for every confirmation and result to be visible in writing (DECISIONS #174).

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P2, Text Chat Receptionist**.
- **What already exists:**
  - **P0-02** (approved): reason codes, each with `label`, `bookable_by_ai`, `variants` (patient type, age range, appointment type, duration, providers, operatories), and `when_not_bookable` ∈ `callback` / `not_offered`.
  - **P1-20** (approved):
    - `AvailabilityService` → `AvailabilityResult(status: options|none_in_range|not_bookable, reason_code, options[0–3], when_not_bookable, next_cursor)`;
    - `SlotOption.slot_id` and `local_label`;
    - offer store `avail:{session_id}` (15 min);
    - `BookingService.book` → `BookingOutcome(status: booked|slot_taken|slot_busy|patient_conflict|offer_expired|in_progress|outcome_unknown|unavailable, alternatives, local_label, replayed)`;
    - `Preferences(earliest_date, latest_date, weekdays, parts_of_day, prov_num)`.
  - **P1-22** (approved):
    - `get_appointment_availability` (`reason_code`, `urgent?`, `preferences?`, `later?`) → `{status, options: [{slot_id, when, provider, visit}], more}`;
    - `book_appointment(slot_id)`;
    - `get_patient_appointments()` → `{appointments: [{handle, when, provider, visit, status}]}` (future, `Scheduled`, ≤ 10, handles `A1…`).
  - **P2-08** (approved): gateway; `book_appointment` needs `verified`, `fresh_availability`, `confirmation_recorded`; operation hash `{kind, session_id, pat_num, slot_id}`; budgets (writes 3 per person).
  - **P2-04** (approved): reply templates, `ConfirmationCard`, `confirm_summary`, guardrail G1 (times must match facts), `ReplyFacts.options` / `chosen` / `appointments` / `outcome`.
  - **P2-05** (approved): extraction of `reason_code`, `reason_text`, `preferred_time` → `Preferences` + optional `time_window`, `chosen_slot_ref` → `slot_id`, `confirmation` yes/no/change.
  - **P2-12** (approved): verification; household; `verified` resumes the intent.
  - **P0-04** (approved): events `slot_chosen`, `no_suitable_slot`, `confirmed`, `declined`, `commit_conflict`, `committed`, `more_help`, `change_requested` (#174); guard `bookable`; `BOOK → CONSENT [consent_unknown]`.

## 4. Scope
**In scope**
- `backend/app/orchestrator/flows/booking.py`: `AppointmentTypeHandler`, `AvailabilityHandler`, `ConfirmHandler`, `BookHandler`.
- `backend/app/orchestrator/flows/check_appointment.py`: `CheckAppointmentHandler`.
- Guard `bookable` (registered here; P0-04 named P1-19/P2-16 as owner).
- **Additive P2-04 change:** `ReplyChunk.choices` (tappable quick replies) and `ReplyChunk.info_card` (booked card, appointment list).
- Templates for these states, added to P2-04's catalogue.
- Tests (handlers, end-to-end with `od_fake`, staging smoke script).
- `docs/flows/booking.md`.

**Out of scope** (and which task covers it)
- Slot calculation, locks, re-check, create → P1-20 / P1-16
- Reschedule and cancel → P2-18 (receives the `A1…` handle from the list)
- Tier 2 urgent booking → P2-20 (reuses these handlers with `urgent=True`)
- WhatsApp consent after booking → P4-02
- Rendering choices and cards in the widget → P2-25
- Waitlist → not in MVP

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P1-20, P1-22 (approved) | Availability, booking, tools | `od_fake` with seeded schedules (P1-20 fixtures) |
| P2-08 (approved) | Gateway, guards, hash | Real gateway with fakes |
| P2-04, P2-05 (approved) | Templates, cards, extraction | `FakeLlmProvider` with scripted extraction |
| P2-12 (approved) | Verified active patient | Test principal with `verified_patnum` set |
| P0-02, P1-19 (approved) | Reason mapping | Seed config |
| P2-25 (parallel) | Rendering of choices and cards | The JSON shapes in §6 are the contract |
| P4-02 (later) | Consent step | Guard `consent_unknown` unregistered → readiness warning in dev; skip `CONSENT` in tests |

## 6. Interface contract

### P2-04 extension: choices and info cards (additive, DECISIONS #193)
```python
class Choice(BaseModel):
    id: str                         # what the widget sends back, e.g. "opt:1", "later", "reason:recall_cleaning", "apt:A1:reschedule"
    label: str                      # "Tue, Dec 8 · 9:00 AM · Dr. Lee"  (≤ 60 chars, from facts only)
    parts: tuple[str, ...] = ()     # added by P2-27 (DECISIONS #213): the label's display parts, so the widget never parses text

class InfoCard(BaseModel):
    kind: Literal["booked", "appointment_list", "rescheduled", "cancelled"]   # last two added by P2-18 (DECISIONS #199)
    title: str                      # "You're booked" / "Your upcoming appointments"
    rows: tuple[CardRow, ...]       # P2-04 CardRow (label, value, field)
    actions: tuple[Choice, ...] = ()

class ReplyChunk(BaseModel):        # P2-04, extended
    ...
    choices: tuple[Choice, ...] = ()    # shown as tappable chips under the message (text channel; also visible during voice)
    info_card: InfoCard | None = None
```
- A tapped choice arrives as a normal user turn with `text` = the label and `choice_id` = `id` (P2-25 sends both). The turn processor maps `choice_id` directly to slots and events **without an LLM call** (`opt:2` → `chosen_slot_ref="2"`, `later` → `want_later`, `reason:<code>` → `reason_code`).
- Labels are built by code from `ReplyFacts`, so the guardrail never needs to check them.

### `APPOINTMENT_TYPE` (`AppointmentTypeHandler`)
1. If extraction gave a `reason_code` (not `other`) → set it; check guard `bookable` (P0-02 `bookable_by_ai` and a variant matching patient type and age).
2. If no code, or `other` on the first try → reply `reason_menu` with choices from the clinic's AI-bookable reason labels (at most 4, ordered by P0-02 file order, plus "Something else").
3. Second unclear answer, or "Something else" → `reason_code = "other"`.
4. Not bookable:
   - `when_not_bookable == "callback"` → event to `CALLBACK_REQUEST`, reason `not_bookable_by_ai`, with `reason_code` attached; reply `not_bookable_callback`;
   - `not_offered` → reply `not_offered` (the clinic doesn't offer it online), then ask if there's anything else.
5. Bookable → event `bookable` path → `AVAILABILITY`.

The handler never diagnoses: it only maps what the patient said to a code, and the clarifying question offers the clinic's own labels.

### `AVAILABILITY` (`AvailabilityHandler`)
- **On enter:** tool `get_appointment_availability(reason_code, preferences)`.
  - Filter the options by P2-05's `time_window` if present.
  - If the filter leaves 0 options and `more` → call again with `later=true` (counts as a round).
  - Reply `offer_options` with `facts.options` and `choices` = one per option plus `later` ("Later times") when `more`.
- **Specific time asked and not free → nearest after (DECISIONS #195, user decision).** When the patient asks for a specific time ("Tuesday at 3", "tomorrow morning at 10") and no option starts exactly then (± 0 min on the clinic grid):
  1. call P1-20 again with `anchor_local` = the requested local date and time (same reason, same provider if one was asked), which returns the openings at or after that time, earliest first;
  2. reply `nearest_after` naming the requested time and the closest opening after it: "Sorry, Tuesday at 3:00 PM isn't available. The closest opening after that is Tuesday at 3:40 PM with Dr. Lee. Would you like that time?";
  3. choices: the nearest opening (first), the next 1–2 openings, and "Other times";
  4. "yes" to the question = choose the nearest opening → `slot_chosen` → `CONFIRM` (the card still asks for the final yes);
  5. if nothing exists after the requested time within the booking horizon → reply `nothing_after` ("There's nothing after that within the next {horizon} days. The latest opening before it is …") using the closest opening before, from the normal search; if nothing at all → `no_suitable_slot` callback.

  If the requested time **is** free, it is offered alone as the first choice ("Tuesday at 3:00 PM is available. Shall I book it?") with "Other times" as the second choice.
- **Rounds:** a round is one offer shown. After **3 rounds** (DECISIONS #194), or when `more` is false, or on `none_in_range` → reply `no_suitable_slot_callback` → event `no_suitable_slot` → `CALLBACK_REQUEST` (reason `no_suitable_slot`, preference attached).
  - Exception: `none_in_range` with `reason_code=preference_too_narrow` on the first round → reply `widen_preference` (ask for another day or time) before counting a round.
- **On turn:**

  | Extraction / choice | Action |
  |---|---|
  | `chosen_slot` (ref or choice) | event `slot_chosen` → `CONFIRM` |
  | new `preferred_time` | new search (round counter reset once per new preference, max 2 resets) |
  | `want_later` | `later=true` search |
  | anything else | `not_understood` handling (P2-01) |

- `provider_not_found` from the tool → mention once that the dentist isn't available for this visit (template `provider_not_available`) and show the options found.

### `CONFIRM` (`ConfirmHandler`)
- **On enter:** build `PendingOperation(kind="book", pat_num=active, slot_id=chosen)` and reply `confirm_summary` with the `book` card. Rows: Patient, Visit, Date and time (with zone), Dentist, Location.
- **On turn:**
  - `yes` → `confirmed` (guards `verified`, `fresh_availability`, `confirmation_recorded`) → `BOOK`;
  - `change` + `time` / `provider` → `change_requested` → `AVAILABILITY` (keep the preference, clear `chosen_slot`);
  - `change` + `reason` → `APPOINTMENT_TYPE`;
  - `no` with no target → reply `what_to_change` with choices "Date or time", "Dentist", "Reason for visit", "Cancel booking".
- If the offer expired (> 15 min) before yes → `fresh_availability` fails → reply `offer_expired` → back to `AVAILABILITY` with a fresh search.

### `BOOK` (`BookHandler`)
Tool `book_appointment(slot_id)` through the gateway, then map the `BookingOutcome`:

| Outcome | Event / next | Reply | Info card |
|---|---|---|---|
| `booked` (also `replayed`) | `committed` → `WRAP_UP` (consent now runs before `CONFIRM`: `AVAILABILITY --slot_chosen [consent_unknown]--> CONSENT --consent_done--> CONFIRM`, and `CONFIRM` `on_enter` appends P4-02's `messaging_card_row()`; DECISIONS #256) | `booked` | `booked` card: Patient, Visit, Date and time, Dentist, Location (clinic address), note "New patient? Please arrive 15 minutes early." from `clinic_info.new_patients` when `is_new_patient` |
| `slot_taken` / `slot_busy` | `commit_conflict` → `AVAILABILITY` | `slot_taken` with the alternatives as new options and choices | - |
| `offer_expired` | `commit_conflict` → `AVAILABILITY` (fresh search) | `offer_expired` | - |
| `patient_conflict` | → `AVAILABILITY` | `patient_conflict` ("You already have an appointment at that time…") | - |
| `in_progress` / `outcome_unknown` | → `CALLBACK_REQUEST`, reason `booking_needs_confirmation` | `booking_needs_confirmation` ("I couldn't confirm the booking just now. Our team will check and confirm it with you.") | - |
| `unavailable` / `od_unavailable` | global `od_unavailable` → `CALLBACK_REQUEST` | callback templates (P2-22) | - |
| `budget_exceeded` | → `CALLBACK_REQUEST` | `budget_callback` | - |

**Never** `booked` text or card unless the outcome is `booked` (P2-04 G4 also enforces this).

**Addition (P4-03, DECISIONS #258):** on a confirmed `booked` outcome (not `outcome_unknown` / `in_progress`; a `replayed` outcome only if not already published), `BookHandler` publishes `AppointmentChanged(kind="booked", op_key=<P2-08 idempotency key>)` after the reply is decided (background task). The `booked` reply gets the `whatsapp_note_booked` sentence when consent is granted (P4-03 §6.6).

### `CHECK_APPOINTMENT` (`CheckAppointmentHandler`)
- Precondition `verified` (P0-04: entered only when verified, else via `IDENTIFY`/`VERIFY` keeping the intent).
- Tool `get_patient_appointments()` → up to 10 future `Scheduled` appointments within 365 days (P1-22).
- **Reply:**
  - Text `appointment_list`: "You have {n} upcoming appointment(s)." Voice reads the first 3 by date, time and dentist.
  - `info_card` (`appointment_list`): one row per appointment (`label` = date and time, `value` = visit with dentist).
  - Actions per row: `apt:A1:reschedule`, `apt:A1:cancel`.
  - Global choices: "Book another", "That's all".
- **Zero appointments** → `no_appointments` ("I don't see any upcoming appointments. Would you like to book one?") with choices "Book an appointment", "No, thanks".
- A tapped action fires `intent_changed` with `intent=reschedule|cancel` and `apt_num=A1` → P2-18.

### Templates (added to P2-04)
| Intent | Text |
|---|---|
| `reason_menu` | "Is this for {reason_options}, or something else?" (labels from config) |
| `not_bookable_callback` | "That type of visit needs our team to schedule it. I'll ask them to call you to set it up." |
| `not_offered` | "I'm sorry, that's not something I can book online. Is there anything else I can help with?" |
| `offer_options` | (P2-04) |
| `widen_preference` | "I don't see openings then. Would another day or time work?" |
| `nearest_after` | "Sorry, {requested} isn't available. The closest opening after that is {nearest}. Would you like that time?" (with choices) |
| `requested_available` | "{requested} is available. Shall I book it?" |
| `nothing_after` | "There's nothing after that within the next {horizon_days} days. The closest earlier opening is {nearest}. Would that work?" |
| `no_suitable_slot_callback` | "I couldn't find a time that works. Our team can find one for you. I'll ask them to call you." |
| `provider_not_available` | "That dentist isn't available for this visit, but here's what I have." |
| `what_to_change` | "What would you like to change?" |
| `offer_expired` | "Those times have just expired. Let me get fresh ones." |
| `slot_taken` | (P2-04) |
| `patient_conflict` | "You already have an appointment around then. Shall I look for a different time?" |
| `booked` | (P2-04) "You're all set for {when} with {provider}." + `booked` card |
| `booking_needs_confirmation` | "I couldn't confirm the booking just now. Our team will check and confirm it with you." |
| `appointment_list`, `no_appointments` | as above |

### Logs and metrics (no PHI)
| Item | Fields |
|---|---|
| `booking.step` (debug) | `state`, `step`, `round`, `reason_code`, `turn_seq` |
| `booking.outcome` (info) | `result` (`booked` / `conflict` / `unknown` / `no_slot` / `not_bookable`), `reason_code`, `rounds`, `is_new_patient`, `replayed` |
| `dai.booking.outcome` (P1-07 counter) | `result`, `channel` |
| `dai.booking.rounds` (histogram) | rounds until booked |

## 7. Implementation guide
1. **P2-04 extension.** Add `Choice`, `InfoCard`, `choices`, `info_card`. Turn-processor support for `choice_id` (P2-01 `UserTurn` gains optional `choice_id`, additive).
2. **Guard `bookable`.** Implement against P1-19's P0-02 mapping (reason, patient type, age); register it.
3. **Handlers.** Implement the five handlers per §6 and register them in P2-01. Each state's reply facts come only from tool outputs (P2-04 G1).
4. **Choices.** Build labels from `SlotOption.local_label` + provider display name (≤ 60 chars). Map `choice_id` deterministically.
5. **Booked card.** Rows from the outcome (`local_label`), offer store data (provider, visit) and config (`clinic.display_name`, `clinic_info.address`).
6. **Templates.** Add §6 templates to P2-04; wording reviewed by the product owner.
7. **End-to-end tests** with `od_fake` (§10), including the conflict path.
8. **Staging smoke test** `scripts/smoke/booking_e2e.py`: drives a synthetic patient through text chat against staging's Open Dental test database (P1-15 test DB), books, verifies the appointment exists, then cancels it through P1-16 to clean up.
9. **Docs and notifications.** `docs/flows/booking.md` (Mermaid diagram per P0-04 format). Notify P2-18 (handles and actions), P2-20 (`urgent=True` reuse), P2-25 (choices and cards contract), P4-02 (`CONSENT` entry), P5-03.

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| "My tooth hurts a bit" | P2-20 runs first; if no emergency → `toothache` → bookable variant → options |
| Reason maps to a code with no matching variant (age outside range) | `bookable` false → `when_not_bookable` |
| Patient taps option 2 | `choice_id=opt:2` → `slot_chosen` without an LLM call |
| Patient says "the Wednesday one" | P2-05 resolves `chosen_slot_ref`; ambiguous → asked again |
| Patient asks for "after 3" but only morning slots | `time_window` filter → 0 → automatic later search; still none → `widen_preference` |
| Patient asks "Tuesday at 3" and 3:00 is taken | `nearest_after`: "Tuesday 3:00 PM isn't available; the closest after is 3:40 PM. Would you like that?" with choices |
| Patient asks "Tuesday at 3" and 3:00 is free | `requested_available` with that time as the first choice |
| Nothing after the requested time in the horizon | `nothing_after` with the closest earlier opening |
| 3 rounds without a choice | `no_suitable_slot` → callback with preference |
| Two people book the same slot | P1-20 lock: one `booked`, the other `slot_taken` → apology + alternatives |
| Patient says yes after 16 minutes | `offer_expired` → fresh options |
| Network failure after Open Dental created the appointment | P1-16 reconcile → `booked` (`replayed`) or `outcome_unknown` → never "booked" without confirmation |
| Patient already has an appointment at that time | `patient_conflict` → other times |
| New patient booking | Variant for new patients; booked card includes the arrival note; AI-booked note in Open Dental (P1-16) |
| Household: parent booking for child | Card's first row "Patient: Sam Doe"; hash includes the child's PatNum (#185) |
| Patient checks appointments while unverified | Goes through `IDENTIFY`/`VERIFY` first; nothing listed before |
| More than 10 upcoming appointments | First 10 by date; text says "here are the next 10" |
| Patient taps "Cancel" on a listed appointment | `intent_changed` (cancel, A1) → P2-18 |
| Voice session | Choices and cards still appear in the chat window; the voice reads options and the result |

## 9. Security, HIPAA and PHI
- **PHI handled:** the reason text (encrypted slot), appointment times linked to the patient, the patient's name on cards (own session only). Options shown before verification contain no patient data. Appointment lists appear only after verification of the active patient.
- **Stored by us:** nothing new (P1-16 keeps AptNum references; offer store holds times and provider numbers without names).
- **Never logged:** reason text, names, labels with times tied to a patient. Logs use reason codes, rounds and outcome codes.
- **Controls:** every write through P2-08 (verified, fresh, exact confirmation); only the active patient's appointments; the model never writes card or choice text.

## 10. Testing
```bash
cd backend && pytest tests/unit/orchestrator/flows/test_booking.py tests/unit/orchestrator/flows/test_check_appointment.py -q
pytest tests/integration/booking -q                       # od_fake
python scripts/smoke/booking_e2e.py --env staging          # staging, synthetic patient
```
| # | Case | Expected |
|---|---|---|
| T1 | Happy path: reason → 3 options → tap option → card → yes → booked | One appointment in `od_fake`; `booked` text and card only after the outcome |
| T2 | Unclear reason twice | `reason_menu`, then `other` → `when_not_bookable` |
| T3 | Not bookable (`callback` / `not_offered`) | Callback with reason / `not_offered` reply |
| T4 | Choices map without LLM | `FakeLlmProvider.calls` unchanged for a tapped choice |
| T5 | `time_window` filtering and automatic later search | Only matching options shown |
| T6 | 3 rounds without choice | `no_suitable_slot` → callback with preference |
| T7 | Conflict path re-offers alternatives | `slot_taken` → apology + alternatives as new choices → second booking succeeds |
| T8 | Offer expired before yes | Fresh search; no booking from the old offer |
| T9 | `outcome_unknown` | No "booked" wording or card; `booking_needs_confirmation` callback |
| T10 | Change time on the card | Back to `AVAILABILITY`; preference kept |
| T11 | Patient conflict | `patient_conflict` reply; new search |
| T12 | Check appointments: 0, 3, 12 appointments | Correct list (max 10), actions, voice reads 3 |
| T13 | Only the verified active patient's appointments are shown | Household switch shows only the active person's list; unverified → none |
| T14 | New patient booking | Arrival note on the booked card |
| T15 | Guardrail: LLM phrasing of `offer_options` with a wrong time | Replaced by the template (P2-04 G1) |
| T16 | Staging smoke | Booked and cleaned up on staging |
| T17 | Log capture with PHI corpus | No reason text, names or labels in logs |
| T18 | Specific time taken: requested Tue 3:00 PM, free 3:40 and 4:20 PM | `nearest_after` names 3:00 PM and offers 3:40 PM first, 4:20 PM next, "Other times"; "yes" selects 3:40 PM |
| T19 | Specific time free | `requested_available`; that slot is the first choice |
| T20 | Nothing after the requested time | `nothing_after` with the closest earlier opening; none at all → callback |

## 11. Acceptance criteria
- [ ] End-to-end booking passes on staging (T16) and in CI with `od_fake` (T1)
- [ ] The conflict path apologizes and re-offers alternatives (T7)
- [ ] "Booked" is said and the booked card is shown only after Open Dental confirms; uncertain outcomes go to a callback (T1, T9)
- [ ] Reasons map to P0-02 codes without diagnosis; unclear reasons get one fixed question; non-bookable reasons follow `when_not_bookable` (T2, T3)
- [ ] Options appear as text and tappable choices; a tapped choice needs no LLM call (T4)
- [ ] After 3 rounds without a suitable time, a callback is created with the preference (T6)
- [ ] When the requested time is not free, the AI says so and offers the closest opening after it, asking whether the patient wants that time (T18–T20)
- [ ] Only the verified active patient's appointments are listed, at most 10, with Reschedule and Cancel actions (T12, T13)
- [ ] No PHI in logs (T17)

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI; staging smoke run linked in the PR
- [ ] PR reviewed (HIPAA review: labelled `phi`)
- [ ] No PHI in logs
- [ ] `docs/flows/booking.md` written; P2-04 and P2-01 extensions merged
- [ ] P2-18, P2-20, P2-25, P4-02 and P5-03 issues notified

## 13. Hand-off
| Consumer | What they can rely on |
|---|---|
| P2-18 Reschedule/cancel | Appointment list with handles and `apt:A1:reschedule|cancel` actions; `AVAILABILITY`/`CONFIRM` handlers reusable with `kind="reschedule"` |
| P2-20 Emergency | `AvailabilityHandler` with `urgent=True` and the Tier 2 templates |
| P2-22 Callback | Reasons `not_bookable_by_ai`, `no_suitable_slot`, `booking_needs_confirmation` with the reason code and preference |
| P2-25 Widget | `Choice` and `InfoCard` JSON shapes; `choice_id` sent back with the turn |
| P4-02 Consent | Entry into `CONSENT` after `committed` when `consent_unknown` |
| P5-04 Edge tests (DECISIONS #284: these tests are in P5-04, not P5-03) | Conflict, expiry and DST paths through the real handlers |

## 14. Open questions
| # | Question | Recommended answer | Owner |
|---|---|---|---|
| 1 | Should the AI offer a waitlist when nothing fits? | Not in the MVP; the callback with the preference covers it. | Product owner |
| 2 | Should the booked card offer "Add to calendar" (.ics)? | Yes later (P4 or post-MVP); the WhatsApp confirmation covers the MVP. | Product owner |
| 3 | Should 3 rounds be clinic config? | No: keep a constant; revisit with pilot data. | Tech lead |

## 15. References
- Plan: §2, §4.6, §4.9, §11
- P0-02 reason mapping; P0-01 Q2 (AI-booked flag)
- DECISIONS: #86, #142, #164, #174, #176, #185, #192, #193, #194
- Related tasks: P0-02, P0-04, P1-16, P1-19, P1-20, P1-22, P2-01, P2-04, P2-05, P2-08, P2-12, P2-18, P2-20, P2-22, P2-25, P4-02, P5-03
