---
id: P2-01
title: Conversation state machine engine and encrypted slot memory (Redis session state, turn serialization)
milestone: P2
epic: E2.1
size: L
labels: area:ai, area:backend, type:feature, phi
depends_on: P0-04, P1-05, P1-07, P1-13, P1-19, P1-22
status: approved
---

# P2-01: Conversation state machine engine and encrypted slot memory (Redis session state, turn serialization)

## 1. Summary
Build the deterministic core that runs every patient conversation. This task also absorbs **P2-02 (slot memory)**.

1. **State machine engine** (`backend/app/orchestrator/`):
   - loads P0-04's authoritative `state_machine.yaml`;
   - validates it (JSON Schema + P0-04's consistency rules as unit tests);
   - executes it. **Code decides every transition.** The LLM only proposes an event from a closed, per-state list, and tool results are mapped to events by code.
   - It also provides: global interrupts, side branches with `resume_state`, guard evaluation (fail closed), and per-state entry handlers that the flow tasks register.
2. **Conversation state and slot memory** in Redis:
   - state, flags, counters, revision;
   - every PHI slot encrypted with P1-05's `FieldCipher`;
   - the last N turns, encrypted;
   - TTL = the session idle timeout;
   - compare-and-set writes, so two instances never overwrite each other.

   It also provides "what's still missing" for each state (no re-asking) and masked views for the LLM context (P2-04).
3. **Turn processor skeleton:**
   - one turn at a time per session (Redis lock), across voice and text and across instances;
   - session start (config pinning) and session end (Postgres `sessions` row).

Done means:
- the YAML loads and passes all consistency tests;
- illegal transitions are rejected;
- slot values are never stored in plain text in Redis;
- a slot that is filled is never asked again;
- a voice and a text message arriving together are processed in order;
- a session continues seamlessly on another instance.

## 2. Why this matters
Plan §4.1: "A deterministic state machine owns the workflow". This is what makes the AI safe:
- booking is reachable only through `CONFIRM`, with the `verified` and `confirmation_recorded` guards;
- emergencies interrupt anything;
- the model can't skip steps.

Every P2 flow (P2-12 identify/verify, P2-15 register, P2-16 booking, P2-18 reschedule/cancel/FAQ, P2-20 emergency, P2-22 callback) plugs into this engine, and P3 voice reuses it unchanged. Slot memory is what makes the conversation feel competent ("only missing fields are requested"). It also holds the most PHI outside Open Dental, so its encryption and TTL are HIPAA-critical. Pilot targets helped by this task: 100% emergency escalation in tests, and 0 PHI in logs.

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P2, Text Chat Receptionist**.
- **Terms:**
  - **State machine:** the conversation is always in exactly one **state**. An **event** (from the patient's turn or a tool result) plus **guards** (yes/no conditions) pick a **transition** to the next state.
  - **Slot** here means a piece of collected information (name, DOB, reason), **not** an appointment time slot (GLOSSARY "Slot memory").
- **What already exists:**
  - **P0-04** (approved), `docs/flows/state_machine.yaml` + `state_machine.schema.json`:
    - 18 states (main, side, terminal) with `allowed_tools` and `collects`;
    - slots with PHI flags;
    - guards `verified`, `fresh_availability`, `confirmation_recorded`, `outside_cancellation_window`, `bookable`, `consent_unknown`;
    - transitions with optional `guards` and `action`;
    - `global_transitions` with `except`;
    - side states with `resumes: true`.

    Consistency rules to automate:
    - every state is reachable and named;
    - deterministic `(from, event, guards)`;
    - `BOOK` only from `CONFIRM` with `verified` + `confirmation_recorded`;
    - `CHECK_APPOINTMENT`/`RESCHEDULE`/`CANCEL` only with `verified`;
    - tools ⊆ the 12 tools;
    - every PHI slot is listed in P0-14.

    Global interrupts:
    - `emergency_tier1`/`crisis` from any state, never resuming;
    - `emergency_tier2`/`uncertain`;
    - `human_requested`, `not_understood_limit`, `od_unavailable` → `CALLBACK_REQUEST`;
    - `intent_changed` → `INTENT` (slots kept);
    - `faq_asked` → `FAQ` (then resume);
    - `idle_timeout` → `END`;
    - `channel_switched` → same state.
  - **P1-13:**
    - `PatientPrincipal` (`session_id`, `clinic_id`, `channel`, `verified_patnum`);
    - Redis `psess:{sid}` (TTL `PATIENT_SESSION_IDLE_S`, default 900 s);
    - `mark_verified(session_id, patnum)`, `end_session(session_id, reason)`;
    - verification attempt limit.
  - **P1-05:** `FieldCipher.encrypt/decrypt(…, ctx=EncContext(table, column, clinic_id))` (AES-GCM via Tink, AAD binds the location); a planned use "`EncContext(table="redis_session", column=<field>, clinic_id)`".
  - **P1-19:** `pin_session()`, `for_session()`; this task adds a `conversation` config section.
  - **P1-22:** `ToolName`, `ToolEnvelope` (`ok`, `error.code`, `error.next`), `ToolContext.state`.
  - **P1-20:** offer store `avail:{session_id}` (used by the `fresh_availability` guard, implemented in P2-08).
  - **P1-03:** `sessions` row (`status`, `end_reason`, `verified_patnum`, `channel_switches`, `config_version`).
  - **DECISIONS #72:** WebSockets on Cloud Run are cut at the request timeout and may reconnect to another instance, so conversation state must be fully in Redis.

## 4. Scope
**In scope**
- **Package `backend/app/orchestrator/`:**
  - `flow.py`: load and validate `FlowDefinition`;
  - `machine.py`: `StateMachine.fire`;
  - `guards.py`: guard registry, fail closed;
  - `handlers.py`: entry and turn handler registry for flows;
  - `state.py`: `ConversationState`;
  - `store.py`: `ConversationStore`, Redis CAS and lock;
  - `slots.py`: `SlotMemory`, encryption, masking, missing fields;
  - `turn.py`: `TurnProcessor` skeleton;
  - `lifecycle.py`: start, end, expiry.
- **Flow file packaging:** `backend/app/orchestrator/flows/state_machine.yaml` is a copy of `docs/flows/state_machine.yaml` made by `make sync-flows`. CI fails if they differ.
- **Consistency test suite** for the YAML (P0-04 §6 rules) and the engine tests.
- **Slot catalogue** `backend/app/orchestrator/slot_catalogue.py`: type, validator, normalizer, PHI flag and mask rule for every slot in the YAML.
- **P1-19 extension:** config section `conversation` (`not_understood_limit`, `recent_turns`, `max_turn_chars`), console-editable.
- **Docs:** `docs/orchestrator.md` with a turn sequence diagram, how a flow registers handlers and guards, and the storage layout.

**Out of scope** (and which task covers it)
- The state machine content itself (states, transitions) → P0-04 (YAML changes go through P0-04's review)
- LLM provider and model routing → P2-03
- Compact context building, prompts, injection defences → P2-04 (uses `SlotMemory.masked_view()`)
- Intent and slot extraction with JSON output → P2-05 (produces `Extraction`, defined here)
- Tool allow-list and guard implementations `verified`, `fresh_availability`, `confirmation_recorded` → P2-08
- Each flow's handlers → P2-12, P2-15, P2-16, P2-18, P2-20, P2-22; `consent_unknown` → P4-02
- Widget and WebSocket transport → P2-25; voice transport → P3

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P0-04 (approved) | `state_machine.yaml`, schema, consistency rules | Use the approved file; the excerpt in P0-04 §6 is enough for first tests |
| P1-05 (approved) | `FieldCipher` | Tests use a local Tink keyset fixture (P1-05 test helper) |
| P1-13 (approved) | `PatientPrincipal`, `end_session`, idle TTL | Test principal factory |
| P1-19 (approved) | `pin_session`, `conversation` section | Seed config + section defaults |
| P1-22 (approved) | Tool names, envelope | Fakes |
| P2-05 / P2-08 / flow tasks (parallel) | Extraction, guards, handlers | This task defines their interfaces; tests register fake handlers and guards |

## 6. Interface contract

### Flow definition and engine
```python
@dataclass(frozen=True)
class StateDef:
    name: str
    kind: Literal["main", "side", "terminal"]
    allowed_tools: frozenset[str]
    collects: tuple[str, ...]
    resumes: bool

@dataclass(frozen=True)
class TransitionDef:
    from_state: str
    event: str
    to_state: str
    guards: tuple[str, ...]
    action: str | None

@dataclass(frozen=True)
class FlowDefinition:
    version: str
    initial_state: str
    states: Mapping[str, StateDef]
    slots: Mapping[str, SlotDef]            # name -> phi flag (+ catalogue entry)
    transitions: tuple[TransitionDef, ...]
    global_transitions: tuple[GlobalTransitionDef, ...]
    def events_for(self, state: str) -> frozenset[str]: ...   # local + applicable global events

def load_flow(path: Path) -> FlowDefinition: ...  # JSON Schema + consistency checks; raises FlowDefinitionError

class StateMachine:
    def __init__(self, flow: FlowDefinition, guards: GuardRegistry) -> None: ...
    async def fire(self, st: ConversationState, event: str, gctx: GuardContext) -> TransitionResult: ...

@dataclass(frozen=True)
class TransitionResult:
    accepted: bool
    from_state: str
    to_state: str
    action: str | None
    reason: Literal["ok", "unknown_event", "not_allowed_in_state", "guard_failed", "no_matching_transition"]
    failed_guard: str | None = None
```
**`fire` rules:**
1. **Unknown event:** an event not in `flow.events_for(st.state)` → `accepted=False`, `reason="not_allowed_in_state"`. The state is unchanged and the event `orchestrator.transition_rejected` is logged.
2. **Global transitions first.** If the event matches a global transition and the current state is not in its `except` list:
   - entering a `side` state with `resumes: true` (`FAQ`) saves `resume_state = current`;
   - `EMERGENCY` from `emergency_tier1`/`emergency_crisis` clears `resume_state` (never resumes, P0-04);
   - `channel_switched` keeps the state and increments `channel_switches`.
3. **Local transitions:**
   - candidates `(from=state, event)`, tried in file order;
   - the first whose guards all pass wins;
   - a guard that isn't registered **fails** (fail closed);
   - if none passes → `guard_failed` with the first failing guard.
4. **Event `resume`** (raised by a side-state handler when done) goes to `resume_state` and clears it. Without a `resume_state` it goes to `INTENT`.
5. **Counters:** entering a new state resets `not_understood[state]`.
6. **Persistence:** every accepted transition appends to `st.history` (state names only, max 50) and bumps `st.rev`.

**Guards:**
```python
class Guard(Protocol):
    async def __call__(self, gctx: GuardContext) -> bool: ...

@dataclass(frozen=True)
class GuardContext:
    state: ConversationState
    slots: SlotMemory
    principal: PatientPrincipal
    config: ActiveConfig
    redis: Redis

class GuardRegistry:
    def register(self, name: str, guard: Guard, *, owner_task: str) -> None: ...   # name must be in flow.guards
    def missing(self) -> set[str]: ...      # startup log + readiness check fails in staging/prod if non-empty
```

### Conversation state (`state.py`)
```python
class ConversationState(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: uuid.UUID
    clinic_id: uuid.UUID
    flow_version: str
    config_version: int
    state: str
    resume_state: str | None = None
    flags: dict[Literal["operation", "urgent", "intent"], str | bool | None] = {}   # operation: book|reschedule|cancel
    not_understood: dict[str, int] = {}           # per state
    active_person: int = 0                        # index into the person frames (household, DECISIONS #185)
    person_count: int = 1                         # max 4; no names or PatNums here
    history: list[str] = []                       # state names only
    channel: Literal["TEXT", "VOICE"]
    channel_switches: int = 0
    turn_seq: int = 0
    rev: int = 0
    started_at: datetime
    last_activity_at: datetime
```
No PHI in `ConversationState`. PHI lives only in `SlotMemory` and the turn buffer.

### Slot memory (`slots.py`)
```python
class SlotMemory:
    def get(self, name: str) -> SlotValue | None: ...            # decrypted, in memory only
    def set(self, name: str, value: Any, *, source: Literal["patient", "tool", "system"]) -> None: ...   # validate + normalize
    def clear(self, names: Iterable[str]) -> None: ...
    def missing_for(self, state: str, flow: FlowDefinition) -> list[str]: ...   # collects − filled
    def masked_view(self, *, reveal: Iterable[str] = ()) -> dict[str, str]: ...  # for P2-04 context
```
**Slot catalogue** (excerpt; one entry per slot in the YAML; a CI test checks there is one entry per YAML slot and the PHI flags match):

| Slot | Type / normalizer | PHI | Mask in LLM context |
|---|---|---|---|
| `first_name`, `last_name` | str, trimmed, ≤ 60 | yes | `"provided"` |
| `dob` | ISO date, plausible (age 0–120) | yes | `"provided"` |
| `phone`, `mobile_phone` | E.164 US (`phonenumbers`) | yes | `"…23"` (last 2 digits) |
| `zip` | `^\d{5}$` | yes | `"provided"` |
| `email` | email, lowercased | yes | `"provided"` |
| `address` | object {line1, line2, city, state, zip} | yes | `"provided"` |
| `reason_text` | str ≤ 300 | yes | `"provided"` |
| `situation` | str ≤ 500 | yes | `"provided"` |
| `reason_code` | P0-02 code | no | value |
| `preferred_time` | object (Preferences of P1-20) | no | value |
| `chosen_slot` | P1-20 `slot_id` | no | value |
| `confirmation` | enum yes/no + operation hash | no | value |
| `apt_num` | P1-22 handle (`A1`) | no | value |
| `intent` | enum | no | value |
| `consent_whatsapp`, `whatsapp_number` | bool / E.164 | yes (number) | `"…45"` |

**Reveal rules** (which PHI may go to the LLM unmasked, for read-back):
- `CONFIRM`: `first_name`, plus the slot option labels (non-PHI);
- `REGISTER`: all new-patient fields;
- `CALLBACK_REQUEST`: `first_name`, `last_name`, `mobile_phone`;
- `CONSENT`: `whatsapp_number`.

The list lives in `slot_catalogue.REVEAL_BY_STATE`. P2-04 must not reveal anything else.

**Person frames (household, DECISIONS #185):** every slot except `intent` is person-scoped. Redis hash fields are stored as `p{index}:{slot}` and `SlotMemory` always reads and writes the active person's frame (`SlotMemory.for_person(index)`). `add_patient` creates a new empty frame and makes it active; `switch_patient` changes `active_person` to an earlier frame. `masked_view()`, `missing_for()` and `REVEAL_BY_STATE` apply to the active frame only.

**Clearing rules:**
- `verify_failed` (handled in P2-12): clear `first_name`, `last_name`, `dob`, `phone`, `zip`;
- `intent_changed`: keep everything;
- `END`: delete everything;
- `REGISTER` success: keep (needed for read-back).

### Storage layout (`store.py`; all keys TTL = `PATIENT_SESSION_IDLE_S`, refreshed on every turn)
| Key | Type | Content |
|---|---|---|
| `conv:{sid}:state` | string (JSON) | `ConversationState` (no PHI) |
| `conv:{sid}:slots` | hash | field = slot name, value = base64(`FieldCipher.encrypt(json(value), ctx=EncContext(table=f"redis_session/{sid}", column=slot, clinic_id))`) for PHI slots; plain JSON for non-PHI slots |
| `conv:{sid}:turns` | list | last `conversation.recent_turns` turns, each encrypted (`column="turn"`); `{role, text, ts}`; assistant entries gain `interrupted: bool` and hold only the spoken part when cut off by barge-in (P3-06, DECISIONS #235) |
| `conv:{sid}:lock` | string | turn lock token |
| `conv:{sid}:display` | list (max 30) | messages already shown to the patient, each encrypted (`column="display"`), for history after a reload; added by P2-25 (DECISIONS #209) |

- **Binding:** the AAD includes the session ID (through `table`), so a ciphertext copied to another session or clinic fails to decrypt (`security.decrypt_failed`, P1-07).
- **Compare-and-set save:** one Lua script checks that `state.rev` equals the loaded `rev`, then writes state, slots (HSET/HDEL) and turns atomically, and sets the TTLs. A mismatch → `ConversationConflict`; the turn processor reloads and re-applies the event once, then fails with `internal_error`.

```python
class ConversationStore:
    async def create(self, principal: PatientPrincipal, flow: FlowDefinition, config_version: int) -> ConversationState: ...
    async def load(self, sid: uuid.UUID, clinic_id: uuid.UUID) -> tuple[ConversationState, SlotMemory, list[Turn]] | None: ...
    async def save(self, st: ConversationState, slots: SlotMemory, new_turns: list[Turn]) -> None: ...   # CAS on rev
    async def lock_turn(self, sid: uuid.UUID, *, ttl_s: int = 30, wait_s: float = 5.0) -> LockToken: ...
    async def delete(self, sid: uuid.UUID) -> None: ...
```

### Turn processor skeleton (`turn.py`)
```python
@dataclass(frozen=True)
class UserTurn:
    text: str                    # chat text or final STT transcript; ≤ conversation.max_turn_chars (default 1000)
    channel: Literal["TEXT", "VOICE"]
    client_turn_id: str          # from the client; duplicate IDs are ignored (reconnect replay)
    choice_id: str | None = None # a tapped quick reply (P2-16, DECISIONS #193); mapped to slots/events by code, no LLM call
                                 # P2-27 adds confirm:yes:<op_hash> (confirmation, checked by P2-08) and change:<field> (DECISIONS #213, #214)

class Extraction(BaseModel):    # produced by P2-05
    proposed_event: str | None   # must be in flow.events_for(state); else ignored
    slots: dict[str, Any] = {}   # only slots in the current state's collects + global ones (intent, reason_text)
    understood: bool
    emergency_signal: Literal["none", "tier1", "crisis", "tier2", "uncertain"] = "none"   # P2-20 rules run first

class StateHandler(Protocol):    # registered by flow tasks
    async def on_enter(self, hctx: HandlerContext) -> HandlerResult: ...
    async def on_turn(self, hctx: HandlerContext, extraction: Extraction) -> HandlerResult: ...

@dataclass(frozen=True)
class HandlerResult:
    events: tuple[str, ...] = ()          # e.g. ("match_none",) from a tool result
    reply_intent: str | None = None       # what to say next (P2-04 phrases it), e.g. "ask_missing", "read_back"
    tool_calls: tuple[ToolCallRequest, ...] = ()   # run through P2-08 gateway

class TurnProcessor:
    async def handle(self, principal: PatientPrincipal, turn: UserTurn,
                     prefetched: "Prefetched | None" = None) -> TurnOutcome: ...
    # prefetched: added by P3-06 (DECISIONS #236): a speculative extraction for voice; used in step 6 only if
    # the normalized text matches, st.rev is unchanged and the step-5 rule signal is the same; otherwise ignored
```
**`handle` steps:**
1. `lock_turn`. If the lock is busy for 5 s → `TurnOutcome(busy=True)`; the client retries.
2. `load`. If the state is missing: new session → `create` + `pin_session` (P1-19); expired → raise `SessionExpired` (P1-13 rules).
3. **Duplicates:** a `client_turn_id` already seen (kept in state, last 20 IDs) → return the stored outcome reference.
4. **Channel:** a different channel than `st.channel` → fire `channel_switched`.
5. **Emergency first:** P2-20's rules detector runs on the raw text **before** the LLM. Its signal fires the emergency event. A rule `tier1`/`crisis` skips extraction for that turn; other results are merged with the extraction signal by P2-20 `decide()`, and `ConversationState.emergency` (P2-20 `EmergencyRecord`) stops repeated firing (DECISIONS #203).
6. **Extraction:** P2-05 extraction → validate and normalize slots into `SlotMemory` (invalid values dropped and listed as `invalid_slots`).
   - **6b (added by P3-09, DECISIONS #238):** `SlotMemory.set(..., channel)` marks voice-heard `READBACK_SLOTS` (`first_name`, `last_name`, `dob`, `phone`, `mobile_phone`, `email`, `zip`) as `unconfirmed` (hash field `p{index}:_unconfirmed`). If the turn is VOICE and any slot is unconfirmed → fire `readback_needed` into the side state `READ_BACK` (`resumes: true`, template-only replies), skip the state handler, keep the extraction's `proposed_event` in `ConversationState.deferred_event`. On "yes": `confirm()`, `resume`, then call the resumed state's `on_turn` with `Extraction(understood=True, slots={}, proposed_event=deferred_event)` in the same turn. New state fields: `deferred_event`, `readback_failures` (`{field: n}`), `spelling_field`. **P4-02 (DECISIONS #256)** adds `consent_step` (`ask`|`number_check`|`number_ask`|`saving`), `consent_handled` (patient keys, max 4) and `household_consent_bidx` (hex or null), and moves `CONSENT` to between `AVAILABILITY` and `CONFIRM`.
7. **Not understood:** `understood=False` → `not_understood[state] += 1`. At `conversation.not_understood_limit` (default 2), fire `not_understood_limit`.
8. **Handler:** call the state's `on_turn` handler. Its `events` and the validated `proposed_event` are fired in order. After each accepted transition, the new state's `on_enter` runs. At most 5 transitions per turn (loop guard → `internal_error`).
9. `save` (CAS), release the lock, return `TurnOutcome(state, reply_intent, missing_slots, allowed_tools, masked_slots)` for P2-04 to phrase the reply.

**Lifecycle (`lifecycle.py`):**
- **`start_session(principal)`** creates the state and pins the config. It is called by the widget handshake (P2-25) and voice connect (P3).
- **`end_session(sid, reason)`:**
  - deletes the `conv:*` keys;
  - updates `sessions` (`status`, `end_reason`, `channel_switches`, `ended_at`);
  - calls P1-13 `end_session`.
- **Idle expiry:** keys expire by TTL. A sweeper (part of P1-13's existing idle handling) marks the row `EXPIRED`. There is nothing extra to delete, because Redis has already dropped the PHI.

### Config extension (P1-19): `conversation`
```yaml
conversation:
  not_understood_limit: 2        # P0-04 proposal; 1–5
  recent_turns: 6                # turns kept and given to the LLM; 2–12
  max_turn_chars: 1000           # longer input is truncated with a note to the model; 200–4000
```
- **Editing:** console-editable. The section is optional with defaults, an additive change, so `schema_version` stays 1.
- **Verification attempts:** the limit stays `verification.max_attempts` (file-only, P1-19).

### Log events (IDs, states and codes only)
| Event | Fields |
|---|---|
| `orchestrator.transition` | `clinic_id`, `state` (from), `to_state`, `event`, `turn_seq` |
| `orchestrator.transition_rejected` | `clinic_id`, `state`, `event`, `reason`, `failed_guard` |
| `orchestrator.turn` | `clinic_id`, `state`, `duration_ms`, `transitions`, `channel` |
| `orchestrator.conflict` | `clinic_id` |
| `orchestrator.guard_missing` | `guard` (startup) |

`to_state`, `event`, `failed_guard` and `turn_seq` are added to P1-07's field allow-list.

### Example
```python
st = await store.create(principal, flow, config_version=4)          # state GREETING
r = await machine.fire(st, "intent_book", gctx)                     # -> INTENT/IDENTIFY per YAML
r = await machine.fire(st, "faq_asked", gctx)                       # -> FAQ, resume_state = IDENTIFY
r = await machine.fire(st, "resume", gctx)                          # -> IDENTIFY
r = await machine.fire(st, "confirmed", gctx)                       # in IDENTIFY: not_allowed_in_state
slots.set("dob", "03/14/1985", source="patient")                    # normalized to "1985-03-14"
slots.masked_view()                                                 # {"dob": "provided", "reason_code": "recall_cleaning"}
slots.missing_for("IDENTIFY", flow)                                 # ["last_name"]
```

## 7. Implementation guide
1. **Read** P0-04 (the YAML, schema, consistency rules, global interrupts), P1-05 `FieldCipher`, P1-13 patient session, P1-19 pinning, P1-22 envelope, DECISIONS #18, #72, #121, #140.
2. **`flow.py`:** load the YAML, validate it with `jsonschema` against `state_machine.schema.json`, then run the consistency checks as functions. Add `make sync-flows` and the CI diff check (T1–T4).
3. **`machine.py` and `guards.py`:** `fire` with global-first order, `resume`, the `except` lists, fail-closed guards, history and `rev` (T5–T10).
4. **`slots.py`, `slot_catalogue.py`:** normalizers (reuse P2-12's normalizers when ready; until then local ones with the same signatures), masks, reveal rules, clearing (T11–T14).
5. **`store.py`:** key layout, encryption, Lua CAS, lock, TTL refresh (T15–T18).
6. **`turn.py`, `handlers.py`, `lifecycle.py`:** the skeleton with fake extraction and fake handlers; duplicate turn IDs; transition loop guard (T19–T22).
7. **The `conversation` config section** in P1-19's model, rules and seed.
8. **Multi-process test:** two app processes, the same session, interleaved text and voice turns (T23).
9. **Notify:**
   - P2-04: `masked_view`, `REVEAL_BY_STATE`, `TurnOutcome`;
   - P2-05: `Extraction`, `events_for`;
   - P2-08: `GuardRegistry` and the three guards it must register;
   - the flow tasks (P2-12, P2-15, P2-16, P2-18, P2-20, P2-22): `StateHandler`, `HandlerResult`;
   - P2-25, P3: `start_session`, `TurnProcessor.handle`, `client_turn_id`;
   - P4-02: `consent_unknown`;
   - P4-11: the `conversation` section.

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| LLM proposes `confirmed` while in `IDENTIFY` | Rejected (`not_allowed_in_state`); state unchanged; logged |
| `confirmed` in `CONFIRM` but `verified` guard not registered yet | Fail closed: `guard_failed` (`verified`); startup readiness reports missing guard |
| Patient mentions chest swelling during `BOOK` | P2-20 signal → `emergency_tier1` after the running tool call returns; `resume_state` cleared |
| FAQ mid-flow ("what are your hours?") in `AVAILABILITY` | → `FAQ`, then `resume` → `AVAILABILITY`; `chosen_slot` kept |
| Patient changes mind ("actually cancel instead") | `intent_changed` → `INTENT`; slots kept, so identity is not asked again |
| Two misunderstandings in the same state | `not_understood_limit` → `CALLBACK_REQUEST` |
| Voice and text turns arrive within 100 ms | Second waits on the lock; processed after the first, in order |
| WebSocket reconnects to another instance and replays the last turn | Same `client_turn_id` → ignored; no double processing |
| Two instances save at once (lock expired during a slow Open Dental call) | CAS conflict → reload, re-apply once; else `internal_error` (callback path) |
| Redis loses the session (failover) | `load` returns None → `SessionExpired`; widget starts a new session (P1-13); patient told politely |
| Ciphertext moved between sessions | Decrypt fails → slot treated as missing; `security.decrypt_failed` audited |
| Patient types 5,000 characters | Truncated to `max_turn_chars`; P2-04 tells the model it was shortened |
| DOB "02/30/1990" | Invalid → dropped, listed in `invalid_slots`; handler asks again for DOB only |
| Transition loop (handler keeps firing events) | Stops at 5 per turn → `internal_error`, logged |
| YAML edited with an unreachable state | `load_flow` fails at startup and in CI (T2) |

## 9. Security, HIPAA and PHI
- **PHI handled:** every PHI slot in the catalogue (names, DOB, phones, ZIP, email, address, reason text, situation, WhatsApp number) and the recent turns (free text).
- **Where it goes:** Redis only (Memorystore with TLS, AUTH and CMEK, P1-02), with each value **encrypted at the application layer** (P1-05 `FieldCipher`, AAD bound to session, slot and clinic).
  - TTL = idle timeout (15 min default), deleted at session end.
  - Nothing goes to Postgres except the `sessions` row fields (IDs, status, counters).
  - The LLM receives only `masked_view()` plus the reveal list for the state (P2-04 enforces it; T13).
- **Never logged:** slot values, turn text, the extraction contents. Logs hold state names, events, codes, counts and durations (P1-07 allow-list).
- **Integrity:**
  - deterministic transitions; the LLM can only propose events from a closed list;
  - unregistered guards fail closed;
  - `BOOK` reachable only via `CONFIRM` with guards (consistency test).
- **Availability vs. safety:** if Redis or the cipher fails, the session fails safe (`SessionExpired` or `internal_error` → callback). It never continues without its state.
- **Risks reduced:** model-driven unsafe actions, PHI at rest in plain text, PHI in logs (P0-11 R01), lost emergencies (global interrupts are tested from every state).

## 10. Testing
| # | Test | Expected |
|---|---|---|
| T1 | `load_flow` on the approved YAML | Loads; version recorded |
| T2 | Mutated YAML copies: unreachable state, duplicate `(from,event,guards)`, `BOOK` entered not from `CONFIRM`, unknown tool, slot not declared | `FlowDefinitionError` naming the rule |
| T3 | `docs/flows/state_machine.yaml` vs packaged copy | Identical (CI) |
| T4 | Every PHI slot is in P0-14's data-flow list (parsed from `docs/architecture/…`) | True |
| T5 | Every legal transition in the YAML (table-driven from the file) | Accepted with the right `to_state` |
| T6 | Every state × every event not allowed there | Rejected `not_allowed_in_state` |
| T7 | `emergency_tier1` from every non-terminal state | → `EMERGENCY`, `resume_state` None |
| T8 | `faq_asked` then `resume` from each main state | Returns to the same state |
| T9 | Guards: pass, fail, unregistered | Accept / `guard_failed` / `guard_failed` (fail closed) |
| T10 | `except` lists (e.g. `human_requested` in `EMERGENCY`) | Not applied there |
| T11 | Slot normalizers: dates, phones, ZIP, email; invalid values | Normalized / dropped into `invalid_slots` |
| T12 | `missing_for(state)` after partial fills; a filled slot is never in the list (re-ask prevention) | Correct lists |
| T13 | `masked_view()` per state with `REVEAL_BY_STATE` | Only listed fields unmasked; DOB never unmasked |
| T14 | Clearing on `verify_failed`; keep on `intent_changed` | As specified |
| T15 | Redis raw read of `conv:{sid}:slots` after setting DOB and phone | Values are ciphertext; plaintext not found anywhere in Redis (`SCAN` + search) |
| T16 | Ciphertext copied to another session's hash | Decrypt fails; slot missing; audit `security.decrypt_failed` |
| T17 | CAS: two saves from the same `rev` | One succeeds; other `ConversationConflict` |
| T18 | TTL refresh on each turn; expiry after idle | Keys gone after TTL |
| T19 | Duplicate `client_turn_id` | Processed once |
| T20 | `not_understood` twice in one state | `CALLBACK_REQUEST` |
| T21 | Handler firing 6 events | Stops at 5; `internal_error` |
| T22 | `end_session` | Keys deleted; `sessions` row updated |
| T23 | Two processes, one session, interleaved voice/text turns (20 turns) | All processed in order; final `rev` = number of saves; no lost slot |

```bash
cd backend
pytest tests/unit/orchestrator -q
pytest tests/integration/orchestrator -q     # real Redis (docker compose)
```

## 11. Acceptance criteria
- [ ] The engine loads P0-04's YAML; all P0-04 consistency rules run as automated tests; a broken YAML fails CI and startup (T1–T4)
- [ ] Every legal transition is accepted and every illegal one rejected, table-driven from the YAML (T5, T6)
- [ ] Global interrupts work from every applicable state; emergencies never resume; side states resume correctly (T7, T8, T10)
- [ ] Guards are pluggable and fail closed when missing (T9)
- [ ] PHI slots and turns are encrypted in Redis with session-bound AAD; no plaintext PHI in Redis (T15, T16)
- [ ] Filled slots are never asked again: `missing_for` drives the questions (T12); the LLM gets only masked slots plus the state's reveal list (T13)
- [ ] One turn at a time per session across instances and channels; duplicate turns ignored; CAS prevents lost updates (T17, T19, T23)
- [ ] Session start pins the config; end and expiry remove all PHI from Redis and update the `sessions` row (T18, T22)
- [ ] The `conversation` section exists in P1-19 with defaults and rules
- [ ] No PHI in logs (P1-07 leak suite over T11–T23)

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI (T1–T23)
- [ ] PR reviewed (HIPAA review if labelled `phi`): labelled `phi`; tech lead + compliance owner review encryption, masking and the reveal list
- [ ] No PHI in logs
- [ ] Docs / README updated: `docs/orchestrator.md` (turn sequence diagram, handler and guard registration, storage layout)

> **Addition (P6-04, DECISIONS #282):** when `privacy.transcript_retention_days` > 0, the turn pipeline writes each patient turn's final text and each assistant reply to `conversation_transcripts` (field-encrypted, with `expires_at`). At 0 (the default) nothing is written.

## 13. Hand-off
| Task | Can rely on |
|---|---|
| P2-03 / P2-04 Model + context | `TurnOutcome` (state, reply intent, missing slots, allowed tools), `masked_view()`, `REVEAL_BY_STATE`, recent turns (`conversation.recent_turns`) |
| P2-05 Extraction | `Extraction` model; `flow.events_for(state)`; slot catalogue for validation |
| P2-08 Tool gateway | `ConversationState.state` + `StateDef.allowed_tools`; `GuardRegistry` to register `verified`, `fresh_availability`, `confirmation_recorded` |
| P2-12, P2-15, P2-16, P2-18, P2-20, P2-22 Flows | `StateHandler`, `HandlerResult`, `SlotMemory`, clearing rules, `resume` event |
| P2-25 Widget / P3 Voice | `start_session`, `TurnProcessor.handle(principal, UserTurn)`, `client_turn_id` replay safety, `busy` retry |
| P4-02 Consent | Register `consent_unknown` guard and `CONSENT` handler |
| P4-11 Console | `conversation` config section |
| P5-04 / P5-08 Tests (DECISIONS #284: these tests are in P5-04, not P5-03) | Engine test tables to extend; slot encryption tests |

## 14. Open questions
| Question | Recommended answer | Owner | Needed by |
|---|---|---|---|
| How many recent turns should the LLM see? | 6 (3 patient + 3 AI): small context, low latency, enough to follow the thread; configurable 2–12 | Tech lead (with P2-04 latency tests) | P2-04 |
| How many "not understood" in one state before a callback? | 2, per P0-04's proposal; configurable 1–5 | Clinic (P6-01) | Before pilot |
| Should the AAD binding use `table="redis_session/{sid}"` (this spec) instead of P1-05's example `table="redis_session"`? | Yes: binding to the session stops ciphertext reuse across sessions; it is a refinement, not a change to `FieldCipher` | Tech lead | Step 5 |

## 15. References
- Plan §4.1, §4.2, §4.4, §4.5, §4.8, §5, §6
- P0-04 (`docs/flows/state_machine.yaml`, schema, consistency rules), P0-14 data flows (F02, F07)
- Redis Lua scripting (atomic CAS): https://redis.io/docs/latest/develop/interact/programmability/eval-intro/
- Tink AEAD with associated data: https://developers.google.com/tink/aead
- JSON Schema 2020-12: https://json-schema.org/draft/2020-12
- Related tasks: P0-04, P0-14, P1-03, P1-05, P1-07, P1-13, P1-19, P1-20, P1-22, P2-03, P2-04, P2-05, P2-08, P2-12, P2-15, P2-16, P2-18, P2-20, P2-22, P2-25, P3-02, P4-02, P4-11, P5-03, P5-08
