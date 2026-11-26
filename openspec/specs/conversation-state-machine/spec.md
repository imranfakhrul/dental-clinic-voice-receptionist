# conversation-state-machine Specification

## Purpose

Defines the deterministic state machine that owns every patient conversation: its states, slots, guards, transitions and global interrupts. Code decides every transition from this table; the LLM only understands and phrases. Flow documents and golden conversations are derived from it and must agree with it.

## Requirements

### Requirement: The state machine file validates against its JSON Schema
`docs/flows/state_machine.yaml` SHALL validate against `docs/flows/state_machine.schema.json` (JSON Schema 2020-12). Unknown fields SHALL be rejected. If the YAML and any diagram or document disagree, the YAML wins.

#### Scenario: Valid state machine
- **WHEN** the YAML is validated against the schema
- **THEN** validation passes

#### Scenario: Unknown field
- **WHEN** a state carries a field the schema doesn't define
- **THEN** validation fails

### Requirement: The machine has the 18 canonical states
The YAML SHALL define these states: `GREETING`, `INTENT`, `IDENTIFY`, `VERIFY`, `REGISTER`, `APPOINTMENT_TYPE`, `AVAILABILITY`, `CONFIRM`, `BOOK`, `CONSENT`, `WRAP_UP` (main); `CHECK_APPOINTMENT`, `RESCHEDULE`, `CANCEL`, `FAQ`, `EMERGENCY`, `CALLBACK_REQUEST` (side); and `END` (terminal). `initial_state` SHALL be `GREETING`.

#### Scenario: Every plan state is present
- **WHEN** the state names are listed
- **THEN** every plan §4.1 state and every added state appears, and each appears in at least one flow document

### Requirement: The table is complete and deterministic
Every `from`, `to`, `except` and `initial_state` SHALL name a defined state; every transition guard SHALL be a declared guard; every `collects` entry SHALL be a declared slot. Every state SHALL be reachable from `GREETING`, every non-terminal state SHALL have an outgoing transition, and `END` SHALL have none. No `(from, event, guards)` combination SHALL appear twice.

#### Scenario: Unreachable state
- **WHEN** a state has no path from `GREETING`
- **THEN** the consistency check fails

#### Scenario: Duplicate transition
- **WHEN** two transitions share the same `from`, `event` and guards
- **THEN** the consistency check fails

### Requirement: Writes happen only after an explicit, recorded confirmation
Every transition into `BOOK` SHALL come from `CONFIRM` and SHALL require guards `verified` and `confirmation_recorded`. Booking and rescheduling SHALL also require `fresh_availability`; cancelling SHALL instead require `outside_cancellation_window`. Only an explicit yes to exactly the read-back operation SHALL count as confirmation.

#### Scenario: Conditional yes
- **WHEN** the patient answers the read-back with "yes, but make it 3pm"
- **THEN** no confirmation is recorded and the conversation returns to `AVAILABILITY` with the new preference

#### Scenario: Slot taken before commit
- **WHEN** `BOOK` reports `commit_conflict`
- **THEN** the conversation returns to `AVAILABILITY` with fresh options

### Requirement: Changes on the confirmation card return to the collecting state
In every confirmation step (book, reschedule, cancel, registration, callback), a `change_requested` event SHALL clear the named field and return to the state that collects it, after which a new card is shown.

#### Scenario: Patient changes the time on the card
- **WHEN** the patient says the time on the card is wrong
- **THEN** `change_requested` returns to `AVAILABILITY` and a new card is shown after the new choice

### Requirement: Nothing about a patient record is revealed before verification
`CHECK_APPOINTMENT`, `RESCHEDULE` and `CANCEL` SHALL be entered only with guard `verified`; otherwise the conversation SHALL go through `IDENTIFY` and `VERIFY` first, keeping the intent. `IDENTIFY` replies SHALL be neutral and SHALL never confirm that a record exists.

#### Scenario: Unverified cancel request
- **WHEN** an unverified patient asks to cancel
- **THEN** the conversation goes to `IDENTIFY` with intent `cancel` kept, and no appointment details are given before `VERIFY` succeeds

### Requirement: Each state may call only its listed tools
Each state SHALL list its allowed tools. Every listed tool SHALL be one of the 11 plan §4.2 tools or `record_consent`, which belongs to P4-02.

#### Scenario: Tool outside the list
- **WHEN** the YAML lists a tool that isn't one of the 12 allowed tool names
- **THEN** the consistency check fails

### Requirement: Global interrupts work from every state
`emergency_tier1` and `emergency_crisis` SHALL go to `EMERGENCY` from every state, and that flow SHALL never resume. `emergency_uncertain` and `emergency_tier2` SHALL go to `EMERGENCY` from every state except `EMERGENCY`. `human_requested`, `not_understood_limit` and `od_unavailable` SHALL go to `CALLBACK_REQUEST`. `idle_timeout` SHALL go to `END` without committing anything, and `channel_switched` SHALL keep the state and slots.

#### Scenario: Emergency during booking
- **WHEN** a Tier 1 phrase is detected while in `AVAILABILITY`
- **THEN** the next state is `EMERGENCY` and the booking is never resumed

#### Scenario: Patient goes quiet
- **WHEN** `idle_timeout` fires in `CONFIRM`
- **THEN** the session ends and nothing is booked

### Requirement: Side branches resume where they left off
`FAQ` SHALL save `resume_state` and return there after answering. `intent_changed` SHALL return to `INTENT` keeping slots and verification, except from `EMERGENCY` and `CALLBACK_REQUEST`.

#### Scenario: Question mid-booking
- **WHEN** the patient asks for opening hours while in `AVAILABILITY`
- **THEN** `FAQ` answers and the conversation returns to `AVAILABILITY`

### Requirement: Unresolvable cases end in a callback
The conversation SHALL go to `CALLBACK_REQUEST` when: verification fails `verification.max_attempts` times (default 3, shared across the session); a patient match stays ambiguous; a new-patient record can't be created safely; the reason isn't bookable by the AI; no suitable slot exists; a reschedule or cancel is inside the notice window; an insurance question goes beyond the accepted-insurer list; or Open Dental is unavailable.

#### Scenario: Inside the cancellation window
- **WHEN** a verified patient asks to cancel an appointment that starts within the clinic's notice window
- **THEN** the conversation goes to `CALLBACK_REQUEST` and nothing is cancelled

### Requirement: WhatsApp consent is asked before the confirmation card
For booking and rescheduling, when no consent is on record (`consent_unknown`), a chosen slot SHALL lead to `CONSENT` and then to `CONFIRM`. When consent is on record, `CONSENT` SHALL be skipped. Cancelling SHALL never ask. Declining SHALL not affect the booking.

#### Scenario: Consent already on record
- **WHEN** a slot is chosen and consent exists for this patient
- **THEN** the next state is `CONFIRM`

### Requirement: Tier 2 emergencies continue as an urgent booking
A `tier2` result SHALL set `urgent=true` and `reason_code=emergency_exam` and offer the earliest slots within the urgent window. If the patient chooses one while not yet verified, the conversation SHALL pass through `IDENTIFY`/`VERIFY` (or `REGISTER`), keeping the urgent flag and the chosen slot, and then continue to the confirmation. With no slot, an URGENT callback case SHALL be created.

#### Scenario: Unverified Tier 2 patient
- **WHEN** an unverified patient reports a swollen cheek and picks the earliest urgent slot
- **THEN** the conversation goes `EMERGENCY` → `IDENTIFY` → `VERIFY` with `urgent=true`, then to `CONSENT` or `CONFIRM` with the chosen slot

### Requirement: Household members are handled one person at a time
`add_patient` SHALL go to `IDENTIFY` for a new person only when the active person is verified and fewer than 4 persons exist. `switch_patient` SHALL go to `INTENT` only for a person already verified in the session, without re-verification. Neither SHALL fire from `EMERGENCY` or `BOOK`; `add_patient` also SHALL not fire from `CALLBACK_REQUEST`.

#### Scenario: Parent books for a child
- **WHEN** a verified parent says "I also want to book for my son"
- **THEN** the conversation goes to `IDENTIFY` for a new person, who must be identified and verified separately

### Requirement: PHI slots are flagged and traceable
Every slot SHALL carry a `phi` flag. Every PHI slot SHALL be listed in `overview.md` with the state that collects it and the tools it is sent to, as input for P0-14.

#### Scenario: PHI list check
- **WHEN** the PHI slots in the YAML are compared with the list in `overview.md`
- **THEN** both lists are identical

### Requirement: Flow documents and golden conversations agree with the table
Eight flow documents SHALL exist (book existing, book new, reschedule, cancel, check appointment, FAQ, emergency, callback), each with a Mermaid diagram, a step table, failure branches and clinic-dependent points. One synthetic golden conversation per flow SHALL exist, and each `expect_state` SHALL be reachable from the previous state by a defined transition.

#### Scenario: Golden walk-through
- **WHEN** each golden conversation is walked against the YAML
- **THEN** every step follows a defined transition and the final state equals `end_state`

#### Scenario: Synthetic data only
- **WHEN** the golden files are scanned
- **THEN** they contain only made-up names, dates and 555-01xx phone numbers
