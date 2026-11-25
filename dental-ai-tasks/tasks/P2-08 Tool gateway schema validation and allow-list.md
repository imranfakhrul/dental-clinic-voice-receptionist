---
id: P2-08
title: Tool gateway (allow-list, preconditions, confirmation binding, session budgets, idempotency keys)
milestone: P2
epic: E2.2
size: L
labels: area:ai, area:security, area:backend, type:feature, phi
depends_on: P0-04, P1-05, P1-07, P1-16, P1-20, P1-22, P2-01, P2-04
status: approved
---

# P2-08: Tool gateway (allow-list, preconditions, confirmation binding, session budgets, idempotency keys)

## 1. Summary
Build `ToolGateway`, the **only** way conversation code can run a backend tool. This task absorbs **P2-09 (state preconditions and session scoping)** and **P2-10 (idempotency keys)**.

Every call from a state handler goes through these checks in order, then into P1-22's `run_tool()`:
1. the tool is registered;
2. the tool is allowed in the current state (P0-04 `allowed_tools`);
   - 2b (added by P3-09, DECISIONS #238): no argument is built from a slot in `SlotMemory.unconfirmed()` (voice values not yet read back); otherwise refused `unconfirmed_slot` and audited;
3. the session, clinic and handles belong to this session;
4. the per-session tool budget is not used up;
5. the tool's preconditions hold (guards `verified`, `fresh_availability`, `confirmation_recorded`, …);
6. for writes: the **operation hash** of the arguments equals the hash of the confirmation card the patient said yes to (DECISIONS #174).

The task also implements the three core guards once, for both the state machine and the gateway, and puts all idempotency key rules in one module, so a retry never creates a second record.

Done means:
- a tool not allowed in the state, or with a failed precondition, never runs and is audited;
- booking without a matching, fresh, single-use confirmation is impossible;
- nothing can act on another session's patient, appointment or slot;
- search attempts per session are capped (no patient enumeration);
- every write retried with the same inputs creates exactly one record.

## 2. Why this matters
Plan §4.2: "Every tool call passes through a **Tool Gateway**: JSON-schema validation of inputs; **state preconditions** (`book_appointment` is allowed only when the patient is verified, the slot came from a fresh availability query, and an explicit confirmation is recorded); **session scoping** (tools can only act on the patient verified in *this* session); **idempotency keys** on create/modify operations."

This is the last line of defence before a real write in Open Dental. Even if a handler has a bug, the gateway refuses to book an unconfirmed slot, cancel an appointment the patient didn't confirm, or search patients without limit. Pilot targets helped: **0 double bookings**, **0 duplicate patients**, and the HIPAA rule that nothing is disclosed before verification (§4.5).

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P2, Text Chat Receptionist**.
- **Who calls tools:** the model is offered **no tools** (DECISIONS #164). State handlers (P2-12, P2-15, P2-16, P2-18, P2-20, P2-22, P4-02) return `HandlerResult.tool_calls`; P2-01's turn processor sends each one to this gateway. So a denial almost always means a bug in our code, not an attack, and is alerted in prod.
- **Idempotency key:** a string that names one intended write. The first call with a key does the write; a repeat with the same key returns the first result instead of writing again. GLOSSARY "Idempotency key".
- **Operation hash:** an HMAC of exactly what the patient confirmed (operation kind plus slot, appointment or details). GLOSSARY "Operation hash".
- **What already exists:**
  - **P1-22** (approved): `REGISTRY`, `run_tool(name, raw_args, ctx)` (input validation, handler, timeout, sanitizer, audit, envelope), `ToolContext` built server-side from `PatientPrincipal` (so the PatNum never comes from outside), handle store `tools:h:{session_id}` (`A1…` appointment handles, `cand` candidate list), error codes and `next` hints, idempotency keys used inside handlers: `create_patient:{session_id}`, `cancel:{session_id}:{apt_num}`.
  - **P1-20** (approved): offer store `avail:{session_id}` (TTL 900 s, `slot_id` → option JSON with `config_version`), `BookingService.book` / `move`, keys `book:{session_id}:{slot_hash}` and `reschedule:{session_id}:{apt_num}:{slot_hash}`.
  - **P1-16** (approved): `IdempotencyGuard` on Postgres `idempotency_keys` (`operation` ∈ `BOOK` / `RESCHEDULE` / `CANCEL` / `CREATE_PATIENT`, `request_hash`, `status`, `result_ref`, 24 h expiry), reconcile after an uncertain write.
  - **P2-01** (approved): `GuardRegistry.register(name, guard, owner_task)`, `GuardContext(state, slots, principal, config, redis)`, `StateDef.allowed_tools`, `HandlerResult.tool_calls`, the `confirmation` slot ("enum yes/no + operation hash").
  - **P2-04** (approved): `ConfirmationCard(kind, rows, op_hash)`, templates `confirm_summary`, `confirm_registration`, `confirm_callback`.
  - **P2-05** (approved): extraction in a confirmation step returns `yes` / `no` / `change` + `change_target`.
  - **P1-05** (approved): the `bidx-keyset` HMAC used for blind indexes.
  - **P1-07** (approved): `audit_now("security.tool_denied" | "security.rate_limited" | "security.clinic_mismatch", ...)`, log allow-list, alerts.

## 4. Scope
**In scope**
- **Package `backend/app/orchestrator/gateway/`:**
  - `gateway.py`: `ToolGateway.call()` and the decision order;
  - `preconditions.py`: the per-tool precondition table;
  - `guards.py`: `verified`, `fresh_availability`, `confirmation_recorded` (registered in P2-01's `GuardRegistry`);
  - `operation.py`: `PendingOperation`, `operation_hash()`, canonical payloads, single-use consumption;
  - `budgets.py`: per-session tool budgets in Redis.
- **`backend/app/tools/idempotency.py`:** `idempotency_key()` for every write tool; P1-20 and P1-22 handlers switch to it (same key formats, no behaviour change).
- **Additive changes to approved specs:**
  - P1-22 error codes: `unknown_tool`, `not_allowed_in_state`, `scope_mismatch`, `budget_exceeded`, `precondition_failed`, `confirmation_mismatch`;
  - P2-01 slot catalogue: system slot `pending_confirmation` (non-PHI);
  - P1-16 / P1-03: `idempotency_keys.operation` gains `CALLBACK` and `CONSENT` (Alembic migration here).
- **Prod alert** on any `security.tool_denied`.
- **Tests:** unit tests per check; end-to-end retry tests with `od_fake` (P1-15).
- **Docs:** `docs/tool-gateway.md`.

**Out of scope** (and which task covers it)
- Tool handlers and their own business checks → P1-22, P1-20, flow tasks
- Guards `outside_cancellation_window` → P2-18; `bookable` → P2-16; `consent_unknown` → P4-02 (they register in the same registry and the gateway uses them)
- Verification scoring and attempt limits → P2-12
- Building and showing the confirmation card → P2-04 (render), P2-25 (widget)
- Prompt-injection handling → P2-04
- HTTP-level rate limits → P1-13

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P1-22 (approved) | `REGISTRY`, `run_tool`, `ToolContext`, handles, envelope | Use the real registry with the P1-22 fakes |
| P1-20 (approved) | Offer store, `slot_hash`, key formats | Write offers into `avail:{session_id}` in fixtures |
| P1-16 (approved) | `IdempotencyGuard`, `idempotency_keys` | Postgres test container + `od_fake` |
| P2-01 (approved) | `GuardRegistry`, `GuardContext`, YAML `allowed_tools`, slot memory | Load the approved YAML; in-memory `SlotMemory` |
| P2-04 (approved) | `ConfirmationCard` | Build cards in tests with `operation_hash()` from this task |
| P1-05, P1-07 (approved) | HMAC keyset, audit, logger | Local Tink keyset fixture; P1-07 capture fixture |
| Flow tasks (parallel) | Real handlers | Tests use a fake handler returning `tool_calls` |

## 6. Interface contract

### Gateway (`gateway.py`)
```python
@dataclass(frozen=True)
class ToolCallRequest:          # from HandlerResult.tool_calls (P2-01)
    name: str
    args: Mapping[str, Any]

class ToolGateway:
    def __init__(self, registry: Mapping[str, ToolSpec], flow: FlowDefinition, guards: GuardRegistry,
                 budgets: BudgetStore, ops: OperationStore) -> None: ...

    async def call(self, req: ToolCallRequest, *, gctx: GuardContext, tctx: ToolContext) -> ToolEnvelope: ...
```
**Decision order** (first failure wins; nothing after it runs):

| Step | Check | Failure → `error.code` | `next` | Audit (`audit_now`) |
|---|---|---|---|---|
| 1 | `req.name` in `REGISTRY` | `unknown_tool` | `internal_error` | `security.tool_denied` (`reason_code=unknown_tool`) |
| 2 | `req.name` in `flow.state(gctx.state.state).allowed_tools` | `not_allowed_in_state` | `internal_error` | `security.tool_denied` |
| 3 | `tctx.principal.session_id == gctx.state.session_id` and `clinic_id` equal on principal, state and config; `tctx.state == gctx.state.state` | `scope_mismatch` | `internal_error` | `security.clinic_mismatch` or `security.tool_denied` |
| 4 | Budget for the tool's group not exhausted | `budget_exceeded` | `callback` | `security.rate_limited` (`tool`) |
| 5 | Every precondition guard for the tool returns true | `precondition_failed` (+ `data.failed_guard`) | per guard (below) | `security.tool_denied` (`reason_code=<guard>`) |
| 6 | Write tools: `operation_hash(args)` equals the recorded confirmation's `op_hash` | `confirmation_mismatch` | `confirm_again` | `security.tool_denied` (`reason_code=confirmation_mismatch`) |
| 7 | `run_tool(name, args, tctx)` (validation, handler, idempotency, sanitizer, audit) | P1-22 codes | P1-22 | P1-22 |
| 8 | On a successful write: consume the confirmation; increment the budget | n/a | n/a | n/a |

Budgets are incremented at step 7 for every call that reaches the handler (success or handler error), so failing calls also count.

`next` per failed guard: `verified` → `verify_first`; `fresh_availability` → `search_again`; `confirmation_recorded` → `confirm_again`; `outside_cancellation_window` → `callback`; `consent_unknown` → `skip`.

### Precondition table (`preconditions.py`)
| Tool | Preconditions (all must hold) | Confirmation kind |
|---|---|---|
| `search_patient` | none (allow-list limits it to `IDENTIFY` / `REGISTER`) | n/a |
| `verify_patient` | candidate list `cand` exists in the handle store | n/a |
| `create_patient` | not `verified`; `not_verification_locked` (registered by P2-12, DECISIONS #181); `confirmation_recorded` | `register` |
| `get_appointment_availability` | none | n/a |
| `get_patient_appointments` | `verified` | n/a |
| `book_appointment` | `verified`, `fresh_availability`, `confirmation_recorded` | `book` |
| `reschedule_appointment` | `verified`, `fresh_availability`, `confirmation_recorded`, `outside_cancellation_window` (added by P2-18, DECISIONS #199; reads `reschedule_min_notice_hours`) | `reschedule` |
| `cancel_appointment` | `verified`, `confirmation_recorded`, `outside_cancellation_window` | `cancel` |
| `create_callback_request` | `confirmation_recorded`, **except** (a) in `EMERGENCY` for `tier1` / `crisis` / `uncertain`, where P0-03 requires the URGENT case immediately without questions (P2-20 adds reason `emergency_tier2_no_slot`, where a phone read-back replaces the card; DECISIONS #203), and (b) staff-only reason codes such as `guarantor_link` that never contact the patient (DECISIONS #189) | `callback` |
| `record_consent` | `verified`, `consent_unknown` | n/a (the consent answer itself is the explicit act; P4-02) |
| `get_clinic_information`, `get_provider_information` | none | n/a |

A startup check fails if a precondition names a guard that is not registered (P2-01 `GuardRegistry.missing()`), so a missing P2-18 or P4-02 guard is caught in staging, not in production.

### Guards (`guards.py`, registered with `owner_task="P2-08"`)
```python
async def verified(g: GuardContext) -> bool:
    return g.principal.verified_patnum is not None          # set by P2-12 verify or P1-22 create_patient

async def fresh_availability(g: GuardContext) -> bool:
    # chosen_slot is a slot_id present in P1-20's offer store avail:{session_id}, offered under the session's
    # pinned config_version, and not removed as taken. TTL expiry (900 s) removes it automatically.
    ...

async def confirmation_recorded(g: GuardContext) -> bool:
    # confirmation slot == "yes" with an op_hash, recorded ≤ CONFIRMATION_TTL_S (600 s) ago,
    # for the kind of the current pending operation, and not yet consumed.
    ...
```
The same functions run at the `CONFIRM → BOOK` transition (P2-01) and again at the tool call (step 5). Step 6 then binds the confirmation to the exact arguments.

### Operations and the hash (`operation.py`)
```python
OpKind = Literal["book", "reschedule", "cancel", "register", "callback"]

class PendingOperation(BaseModel):            # stored in slot memory as the system slot pending_confirmation (non-PHI)
    kind: OpKind
    op_hash: str
    shown_at: datetime                        # when the card was shown

def canonical_payload(kind: OpKind, *, session_id: uuid.UUID, slot_id: str | None = None,
                      apt_num: int | None = None, details: Mapping[str, Any] | None = None) -> bytes: ...
    # JSON with sorted keys, no whitespace, normalized values:
    #   book:       {"kind","session_id","pat_num","slot_id"}          (pat_num = active verified patient, DECISIONS #185)
    #   reschedule: {"kind","session_id","pat_num","apt_num","slot_id"} (apt_num resolved from the handle server-side)
    #   cancel:     {"kind","session_id","pat_num","apt_num"}
    #   register:   {"kind","session_id","first_name","last_name","dob","mobile_phone","email","address"}  (normalized)
    #   callback:   {"kind","session_id","reason_code","urgency","phone","callback_time"}

def operation_hash(kind: OpKind, **parts) -> str:
    """Base64url HMAC-SHA256 with the P1-05 bidx-keyset over b"op|" + canonical_payload(...)."""
```
**Lifecycle:**
1. P2-04 renders a confirmation card from the same parts, sets `ConfirmationCard.op_hash = operation_hash(...)`, and the turn processor stores `pending_confirmation = PendingOperation(kind, op_hash, shown_at=now)`.
2. The patient says yes → P2-05 extraction `confirmation="yes"` → the `confirmation` slot is set to `{answer: "yes", op_hash: pending.op_hash, at: now}`.
3. The patient says `change` → `pending_confirmation` and `confirmation` are cleared (DECISIONS #174); a new card means a new hash.
4. Gateway step 6 recomputes the hash from the tool arguments (`slot_id`, the handle resolved to `apt_num`, the normalized details) and compares in constant time (`hmac.compare_digest`).
5. After a successful write, `confirmation` and `pending_confirmation` are cleared (**single use**). A second write needs a new card and a new yes.
6. Both slots are also cleared when the conversation leaves the confirmation's state family (`CONFIRM`/`BOOK`, `REGISTER`, `CALLBACK_REQUEST`) or after `CONFIRMATION_TTL_S`.

The hash covers PHI for `register` and `callback`, so it is an HMAC with a server key, never a plain SHA-256 (no dictionary attack on DOB or phone).

### Session budgets (`budgets.py`; Proposed, DECISIONS #177)
```python
BUDGETS: dict[str, int] = {               # calls per session; tune in P5 load and abuse tests
    "search_patient": 5,                  # per person; patient enumeration defence (session total cap below)
    "verify_patient": 5,                  # backstop; the real limit is config verification.max_attempts (P2-12)
    "create_patient": 1,
    "writes": 3,                          # per person; book + reschedule + cancel combined
    "create_callback_request": 2,
    "record_consent": 4,
    "get_appointment_availability": 15,
    "get_patient_appointments": 5,
    "get_clinic_information": 30,
    "get_provider_information": 10,
}
```
Household (DECISIONS #185): `search_patient`, `verify_patient`, `create_patient` and `writes` are counted **per person frame**; session-wide caps on top: `search_patient` 12, `writes` 8. All other budgets are per session.

Storage: Redis hash `gw:budget:{session_id}` (fields `p{index}:{tool}` and `session:{tool}`), `HINCRBY`, TTL = `PATIENT_SESSION_IDLE_S`. Over budget → `budget_exceeded`, `next="callback"`; the flow offers a callback and the patient is told the team will help (P2-04 template `budget_callback`).

### Idempotency keys (`backend/app/tools/idempotency.py`; DECISIONS #178)
```python
def idempotency_key(tool: str, *, session_id: uuid.UUID, **p: Any) -> str:
    match tool:
        case "book_appointment":        return f"book:{session_id}:{p['slot_hash']}"                       # P1-20
        case "reschedule_appointment":  return f"reschedule:{session_id}:{p['apt_num']}:{p['slot_hash']}"   # P1-20
        case "cancel_appointment":      return f"cancel:{session_id}:{p['apt_num']}"                        # P1-22
        case "create_patient":          return f"create_patient:{session_id}:{p['person']}"                 # P1-22; per person frame (DECISIONS #190)
        case "create_callback_request": return f"callback:{session_id}:{p['reason_code']}"                  # new
        case "record_consent":          return f"consent:{session_id}:{p['channel']}:{patnum}:{bidx_hex[:16]}"   # changed by P4-02 (DECISIONS #256): per patient and number
    raise ValueError(f"no idempotency key rule for {tool}")
```
- A unit test checks every registered tool with `writes=True` has a rule.
- `session_id` in every key: retries within a session are the same operation; a new session is a new operation.
- **Migration:** extend `idempotency_keys.operation` with `CALLBACK` and `CONSENT` (Alembic, additive; P1-03 defines whether it's a check constraint or enum type). P2-22 and P4-02 wrap their writes in `IdempotencyGuard` with these keys.
- No key contains PHI (IDs, hashes and codes only).

### New error codes (added to P1-22's envelope table)
| `error.code` | `next` | Meaning |
|---|---|---|
| `unknown_tool` | `internal_error` | Tool name not registered |
| `not_allowed_in_state` | `internal_error` | Tool not in the state's allow-list |
| `scope_mismatch` | `internal_error` | Session, clinic or state mismatch |
| `budget_exceeded` | `callback` | Per-session budget used up |
| `precondition_failed` | per guard | A guard returned false (`data.failed_guard`) |
| `confirmation_mismatch` | `confirm_again` | Arguments differ from what the patient confirmed |

### Logs, metrics and alert
| Item | Fields |
|---|---|
| `gateway.call` (debug) | `tool`, `state`, `result` (`allowed` / denial code), `turn_seq` |
| `gateway.denied` (warning) | `tool`, `state`, `reason_code`, `failed_guard` |
| `dai.gateway.decision` (counter) | `tool`, `result` |
| Alert `A-GW1` (prod) | any `gateway.denied` with `reason_code` in {`unknown_tool`, `not_allowed_in_state`, `scope_mismatch`, `confirmation_mismatch`} within 5 min → page the on-call channel (these are code bugs) |
| Alert `A-GW2` (prod) | `budget_exceeded` for `search_patient` > 10 sessions in 15 min → security channel (possible enumeration) |

### Example
State `BOOK`, verified patient, card shown for `slot_id="k3Q9xP2mTa"`, patient said yes 40 s ago.
```python
env = await gateway.call(ToolCallRequest("book_appointment", {"slot_id": "k3Q9xP2mTa"}), gctx=g, tctx=t)
# steps 1–6 pass → run_tool → {"ok": true, "data": {"booked": true, "when": "Tue Dec 8, 9:00 AM", ...}}
# confirmation consumed

env = await gateway.call(ToolCallRequest("book_appointment", {"slot_id": "Zz81LmQ0rB"}), gctx=g, tctx=t)
# → {"ok": false, "error": {"code": "precondition_failed", "next": "confirm_again",
#                            "data": {"failed_guard": "confirmation_recorded"}}}   (already consumed)
```

## 7. Implementation guide
1. **Operation module.** Implement `canonical_payload`, `operation_hash` (P1-05 HMAC keyset), `PendingOperation`, and an `OperationStore` facade over slot memory (`pending_confirmation`, `confirmation`). Add `pending_confirmation` to P2-01's slot catalogue (system, non-PHI, cleared with the confirmation).
2. **Guards.** Implement `verified`, `fresh_availability`, `confirmation_recorded`; register them in P2-01's `GuardRegistry`. Unit-test each against slot memory and offer store fixtures.
3. **Precondition table.** Data in `preconditions.py`; the startup check that all named guards are registered.
4. **Budgets.** `BudgetStore` with `check(tool)` and `incr(tool)`; tool → group mapping (`writes`).
5. **Gateway.** Implement the decision order exactly; one `audit_now` per denial; return P1-22 envelopes. Wire it into P2-01's turn processor so `HandlerResult.tool_calls` are executed only via `ToolGateway.call` (a test fails if any module other than the gateway imports `run_tool`).
6. **Idempotency module.** Add `idempotency_key()`; change P1-20 and P1-22 handlers to call it (same strings). Add the Alembic migration for `CALLBACK` / `CONSENT`.
7. **P2-04 integration.** P2-04's card renderer calls `operation_hash()` with the same parts; add the `budget_callback` template to its catalogue.
8. **Alerts.** Add the log-based metrics and alert policies `A-GW1`, `A-GW2` in P1-07's Terraform module.
9. **End-to-end retry tests** with `od_fake`: drop the response after Open Dental created the appointment, retry, and assert one appointment exists (§10).
10. **Docs and notifications.** `docs/tool-gateway.md` (decision order, how a flow requests a tool, how to add a precondition or budget). Notify P2-12, P2-15, P2-16, P2-18, P2-20, P2-22 (preconditions and `next` hints), P4-02 (`consent_unknown`, key), P2-04 (hash, template), P5-08 (security tests), P1-07 owners (alerts).

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| Handler calls `book_appointment` in `AVAILABILITY` | `not_allowed_in_state`; audited; prod alert (code bug) |
| Patient said yes to 9:00, handler books 9:30 | `confirmation_mismatch`; nothing written; flow shows a new card |
| Patient says yes twice quickly (two turns) | P2-01 serializes turns; the first books and consumes the confirmation; the second gets `precondition_failed(confirmation_recorded)` and the flow says it's already booked (from `booked` facts) |
| The same request is retried after a network drop | Same idempotency key → P1-16 returns the first result (`replayed=True`); one appointment |
| Offer expired (15 min) before yes | `fresh_availability` fails → `search_again`; new options and a new card |
| Confirmation older than 10 min | `confirmation_recorded` fails → `confirm_again`; card shown again |
| Patient says "change the time" | `confirmation` and `pending_confirmation` cleared; back to `AVAILABILITY` (DECISIONS #174) |
| Handle `A2` from another session | P1-22 resolution fails (`unknown_handle`); also step 3 if session IDs differ |
| Unverified session asks for appointments | `precondition_failed(verified)` → `verify_first`; nothing disclosed |
| 6th `search_patient` in a session | `budget_exceeded` → callback; `security.rate_limited`; A-GW2 if widespread |
| `create_patient` called twice in a session | Budget 1 → second call `budget_exceeded`; P1-22's key would also replay the first |
| Tier 1 emergency, no confirmation | `create_callback_request` allowed by the emergency exception |
| Guard `outside_cancellation_window` not registered yet (P2-18 not merged) | Startup readiness fails in staging/prod; local dev logs a warning |
| Redis unavailable during budget check | Fail closed: `internal_error` → callback; logged |
| Audit insert fails on a denial | Denial still returned; `dai.audit.write_failed` (P1-07 A11) |

## 9. Security, HIPAA and PHI
- **PHI handled:** tool arguments may contain PHI (names, DOB, phone, address for `search_patient`, `create_patient`, `create_callback_request`). The gateway reads them in memory to compute the operation hash and passes them to `run_tool`; it stores nothing but the HMAC hash.
- **Protection:** the operation hash is an HMAC with a KMS-wrapped key (P1-05), compared in constant time; budgets and confirmations are keyed by session ID; no PHI in Redis keys or idempotency keys.
- **Never logged:** arguments, hashes, slot values. Logs carry tool, state, codes and guard names only.
- **Controls provided:** least privilege per state; verification before any patient-scoped read (§4.5); explicit, exact and single-use confirmation before every write; enumeration limit on searches; idempotent writes.
- **Audit:** `security.tool_denied`, `security.rate_limited`, `security.clinic_mismatch` for every denial; successful tool audits stay in P1-22.

## 10. Testing
```bash
cd backend && pytest tests/unit/orchestrator/gateway tests/unit/tools/test_idempotency.py -q
pytest tests/integration/gateway -q        # Postgres + Redis containers, od_fake
```
| # | Case | Expected |
|---|---|---|
| T1 | Unknown tool | `unknown_tool`; audit; handler not called |
| T2 | Every state × every tool (from the YAML) | Allowed exactly when in `allowed_tools` |
| T3 | Principal from session A with state of session B; clinic mismatch | `scope_mismatch`; audit |
| T4 | Booking blocked without confirmation | `precondition_failed(confirmation_recorded)`; no Open Dental call |
| T5 | Booking with confirmation for another slot | `confirmation_mismatch` |
| T6 | Booking with expired offer / expired confirmation | `fresh_availability` / `confirmation_recorded` failures |
| T7 | Confirmation is single use | Second write after success fails |
| T8 | "change" answer clears confirmation | Next write fails until a new yes |
| T9 | Cannot read another patient's data: unverified `get_patient_appointments`; handle from another session; PatNum never accepted from args | Denied / `unknown_handle`; nothing returned |
| T10 | Budgets: 6th search, 2nd create, 4th write | `budget_exceeded`; `security.rate_limited` |
| T11 | Emergency tier1 callback without confirmation | Allowed |
| T12 | Operation hash: same parts → same hash; any changed field → different; PHI not recoverable without the key | Holds |
| T13 | Idempotency keys for every write tool | Rule exists; formats match P1-20 / P1-22; no PHI |
| T14 | **Retry creates exactly one record:** `od_fake` drops the response after creating the appointment; retry `book_appointment` | One appointment in `od_fake`; second envelope `booked` (replayed) |
| T15 | Same retry test for `reschedule`, `cancel`, `create_patient`, `create_callback_request` | One record / one change each |
| T16 | Startup with a precondition guard unregistered | Readiness fails (staging/prod mode) |
| T17 | Only the gateway imports `run_tool` | Import-lint test passes |
| T18 | Log capture with PHI arguments | No values or hashes in logs |
| T19 | Redis down during budget check | `internal_error`, nothing executed |

## 11. Acceptance criteria
- [ ] Unknown or disallowed tools are rejected and audited, and never reach a handler (T1, T2)
- [ ] Booking, rescheduling and cancelling are blocked without a fresh, matching, single-use confirmation (T4–T8)
- [ ] A session cannot read or change another patient's data (T3, T9)
- [ ] Search and write calls per session are capped, and exceeding them leads to a callback (T10)
- [ ] Every write tool has a deterministic idempotency key, and a retry creates exactly one record (T13–T15)
- [ ] The three core guards are implemented once and used by both the state machine and the gateway
- [ ] Only the gateway calls `run_tool` (T17)
- [ ] No PHI in logs (T18); prod alerts A-GW1 and A-GW2 exist

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI
- [ ] PR reviewed (HIPAA review: labelled `phi`)
- [ ] No PHI in logs
- [ ] `docs/tool-gateway.md` written; migration applied in dev; P1-22 error table and P2-01 slot catalogue updated
- [ ] Flow tasks, P2-04, P4-02, P5-08 and P1-07 owners notified

## 13. Hand-off
| Consumer | What they can rely on |
|---|---|
| Flow tasks (P2-12, P2-15, P2-16, P2-18, P2-20, P2-22) | Return `tool_calls`; get P1-22 envelopes with `next` hints; preconditions enforced for them |
| P2-04 Replies | `operation_hash()` for the card; `PendingOperation` stored by the turn processor; `budget_callback` template |
| P2-18 / P4-02 | Register `outside_cancellation_window` / `consent_unknown`; they are enforced at tool time |
| P2-22 / P4-02 | Idempotency keys and the `CALLBACK` / `CONSENT` operations |
| P5-08 Security tests | Denial codes, audit events, budgets, alerts |

## 14. Open questions
| # | Question | Recommended answer | Owner |
|---|---|---|---|
| 1 | Should budgets be per clinic in config? | Not for the MVP: constants in code; move to config only if P5 tests or the pilot show a clinic needs different values. | Tech lead |
| 2 | Is a 10-minute confirmation lifetime right? | Yes: longer than a normal pause, shorter than the 15-minute offer TTL, so a stale yes can't outlive its slot. | Tech lead |
| 3 | Should `record_consent` also need a card? | No: the consent question is itself the explicit act and its wording is fixed by P4-02. | P4-02 owner |

## 15. References
- Plan: §4.2, §4.5, §4.6, §4.9, §6
- OWASP Top 10 for LLM Applications, LLM06 Excessive Agency: https://genai.owasp.org/llmrisk/llm062025-excessive-agency/
- Python `hmac.compare_digest`: https://docs.python.org/3/library/hmac.html#hmac.compare_digest
- DECISIONS: #150, #155, #164, #174, #176, #177, #178, #179
- Related tasks: P0-03, P0-04, P1-03, P1-05, P1-07, P1-13, P1-15, P1-16, P1-20, P1-22, P2-01, P2-04, P2-05, P2-12, P2-15, P2-16, P2-18, P2-20, P2-22, P2-25, P4-02, P5-08
