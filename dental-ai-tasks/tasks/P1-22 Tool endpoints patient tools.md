---
id: P1-22
title: AI tool registry and handlers (patient, appointment, info tools) with JSON schemas, session scoping and audit
milestone: P1
epic: E1.4
size: L
labels: area:backend, area:ai, type:feature, phi
depends_on: P1-07, P1-13, P1-16, P1-19, P1-20
status: approved
---

# P1-22: AI tool registry and handlers (patient, appointment, info tools) with JSON schemas, session scoping and audit

## 1. Summary
Build the **tool layer**: the only backend functions the AI (Gemini) can ask to run. This task also absorbs **P1-23 (appointment tools)** and **P1-24 (info tools)**.

1. **Tool registry** (`backend/app/tools/`):
   - one `ToolSpec` per tool, with Pydantic input and output models;
   - from those models: the generated JSON Schemas, the Gemini function declarations and the docs;
   - one runner, `run_tool()`, that validates input, calls the handler with a **server-side `ToolContext`**, enforces a timeout, sanitizes and minimizes the output, records the audit entry and metrics, and returns a uniform result envelope.
2. **Twelve tools:** the 11 from plan §4.2 plus `record_consent` (P0-04).
   - **Implemented here (9):** `search_patient`, `create_patient`, `get_appointment_availability`, `get_patient_appointments`, `book_appointment`, `reschedule_appointment`, `cancel_appointment`, `get_clinic_information`, `get_provider_information`.
   - **Contract plus stub here (3):** `verify_patient` (P2-12), `create_callback_request` (P2-22), `record_consent` (P4-02). Those tasks register the real handlers.
3. **Session scoping by construction:**
   - The AI **never sends a PatNum, AptNum or slot details**. It uses short handles (`A1`, slot IDs) that resolve only inside its own session.
   - The verified PatNum comes from the session (P1-13 `PatientPrincipal`).
4. **Minimum disclosure:** `search_patient` tells the AI only what to do next, never whether, or which, records exist (§4.5). Outputs never include staff notes or Open Dental internals.
5. **New config section `clinic_info`** in P1-19 (address, insurers accepted, services, parking, languages, payment, new-patient notes; console-editable) feeds `get_clinic_information` with **no LLM call** (§4.3).

P2-08 (tool gateway) builds on this. It adds the per-state allow-list, the preconditions (verified, fresh availability, explicit confirmation) and the prompt-injection defences around `run_tool()`.

## 2. Why this matters
Plan principle: "the LLM talks, deterministic code acts" (§1, §4.2). The tools are the line between them. Everything the AI can do to a patient's record goes through here:
- if a tool trusts an identifier from the model, one injected sentence could read or cancel another patient's appointment;
- if a tool returns too much, the AI can leak a record before verification (§4.5);
- if a tool skips the audit, there is no answer to "who changed this appointment?" (HIPAA audit controls).

The conversation flows (P2-12, P2-16, P2-18, P2-20, P2-22) and both channels (text in P2, voice in P3) call the same tools, so one registry keeps behaviour identical across channels. Latency matters for voice, so tools run **in-process** (no extra HTTP hop).

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P1, Core Platform & Open Dental Adapter**.
- **Terms:**
  - **PatNum** and **AptNum** are Open Dental's numeric IDs for a patient and an appointment. They are the only patient identifiers we store (GLOSSARY).
  - **Tool calling:** the model returns a structured request ("call `book_appointment` with `{slot_id: …}`"); our code runs it and sends back a result.
  - **Function declarations:** Vertex AI Gemini receives tool definitions (name, description, parameters in an OpenAPI-style schema subset) and returns function calls. **Verify** the supported schema keywords for the GA model in use (https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/function-calling) and keep our schemas within that subset (P2 model work uses this).
- **What already exists:**
  - **P1-13:**
    - `PatientPrincipal` (`session_id`, `clinic_id`, `channel`, `verified_patnum`, `actor()`);
    - Redis `psess:{sid}` with `verify_attempts`;
    - `mark_verified()` (called only by verification or registration);
    - rate limits.
  - **P1-07:**
    - `audit()` (in the caller's transaction, fail closed) and `audit_now()` (own transaction; for reads, denials and failures);
    - actions `patient.search`, `patient.verify`, `patient.verify_failed`, `patient.create`, `appointment.book`/`.reschedule`/`.cancel`, `callback.create`, `consent.grant`/`.revoke`, `security.tool_denied`;
    - detail keys (`tool`, `reason_code`, `match_count`, `identifiers_used`, `channel`, `state`…);
    - `stage_timer(Stage.TOOL_CALL, tool=…)`.
  - **P1-16:** `OpenDentalPatients` (`search_by_name_dob`, `search_by_phone`, `get`, `create`), `OpenDentalAppointments` (`get`, `list_for_patient`, `cancel`), typed errors, `WriteResult`.
  - **P1-20:**
    - `AvailabilityService.find` → `AvailabilityResult` (options with `slot_id`, `local_label`, `provider_display`) and the offer store;
    - `BookingService.book` / `move` → `BookingOutcome` (`booked`, `slot_taken` + alternatives, `slot_busy`, `patient_conflict`, `offer_expired`, `in_progress`, `outcome_unknown`, `unavailable`).
  - **P1-19:** `ClinicConfigService.for_session()` with `hours`, `holidays`, `policies` (`cancel_min_notice_hours`, `reschedule_min_notice_hours`, `inside_notice_action`, `new_patient_auto_create`), `verification`, `clinic`, `appointment_types` (reason labels); P1-15 setup cache for providers and schedules.
  - **P0-04:** the states and the allowed tools per state; the `record_consent` tool proposal; the `fresh_availability` guard; "don't confirm 'you are a patient' before VERIFY".

## 4. Scope
**In scope**
- **Package `backend/app/tools/`:**
  - `registry.py` (`ToolSpec`, `ToolName`, `REGISTRY`, `register()`);
  - `runner.py` (`run_tool`);
  - `context.py` (`ToolContext` and its builder);
  - `envelope.py` (result envelope, error codes);
  - `handles.py` (session handle store);
  - `sanitize.py`;
  - one module per tool group: `patient_tools.py`, `appointment_tools.py`, `info_tools.py`, `stubs.py`.
- **Generated artefacts** (CI fails if stale):
  - `docs/tools/<tool>.input.schema.json`, `docs/tools/<tool>.output.schema.json`;
  - `docs/tools/README.md` (table of tools, generated);
  - `backend/app/tools/gemini_declarations.json`.
- **P1-19 extension:** new config section `clinic_info` (model, load-time rules, console-editable), a minor `schema_version` bump handled by a model migration (§6).
- **Session handle store** in Redis for candidates, appointments and the last search outcome.
- **Local and dev only:** `POST /internal/debug/tools/{name}`, to run a tool against a synthetic session from tests or curl. It is disabled when `ENV` is staging or prod (settings validator), and requires P1-13 internal auth.
- **Tests:** handlers, runner, scoping, schemas, audit, leak suite.

**Out of scope** (and which task covers it)
- Per-state allow-list, preconditions (verified, fresh availability, explicit confirmation), injection defences, `security.tool_denied` decisions → P2-08
- Matching and scoring logic behind `verify_patient`; nickname tables → P2-12 (registers the real handler)
- Callback case creation and admin email → P2-22 (registers `create_callback_request`)
- Consent recording → P4-02 (registers `record_consent`)
- Prompting, model choice and the tool-calling loop → P2 (model router and orchestration)
- Console screen for `clinic_info` → P4-11

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P1-16, P1-20 (approved) | Adapter and scheduling services | Use their signatures; unit tests use fakes of `OpenDentalPatients`, `AvailabilityService`, `BookingService`; integration tests use `od_fake` |
| P1-13 (approved) | `PatientPrincipal`, `mark_verified`, internal auth | Build `ToolContext` from a test principal factory |
| P1-19 (approved) | Pinned config, `clinic_info` (added here) | `seed/example-dental/` + the new section |
| P1-07 (approved) | `audit`, `audit_now`, timers | Spec signatures |
| P2-12, P2-22, P4-02 (later) | Real handlers for the 3 stub tools | Stubs return `{"ok": false, "error": {"code": "not_available", "next": "callback"}}`; contracts fixed here |

## 6. Interface contract

### Registry and runner
```python
class ToolName(StrEnum):
    SEARCH_PATIENT = "search_patient"
    VERIFY_PATIENT = "verify_patient"
    CREATE_PATIENT = "create_patient"
    GET_APPOINTMENT_AVAILABILITY = "get_appointment_availability"
    GET_PATIENT_APPOINTMENTS = "get_patient_appointments"
    BOOK_APPOINTMENT = "book_appointment"
    RESCHEDULE_APPOINTMENT = "reschedule_appointment"
    CANCEL_APPOINTMENT = "cancel_appointment"
    GET_CLINIC_INFORMATION = "get_clinic_information"
    GET_PROVIDER_INFORMATION = "get_provider_information"
    CREATE_CALLBACK_REQUEST = "create_callback_request"
    RECORD_CONSENT = "record_consent"

@dataclass(frozen=True)
class ToolSpec:
    name: ToolName
    description: str                         # shown to the model; ≤ 300 chars; no examples with real-looking PHI
    input_model: type[BaseModel]             # model_config = ConfigDict(extra="forbid", strict=True)
    output_model: type[BaseModel]            # extra="forbid"
    handler: Callable[[ToolContext, BaseModel], Awaitable[BaseModel]]
    writes: bool                             # True for create/book/reschedule/cancel/callback/consent
    phi_in_input: bool
    audit_action: AuditAction | None         # None for info tools
    timeout_s: float                         # see table below
    owner_task: str                          # "P1-22", "P2-12", …

REGISTRY: dict[ToolName, ToolSpec]
def register(spec: ToolSpec, *, replace_stub: bool = False) -> None: ...   # P2-12/P2-22/P4-02 replace stubs

async def run_tool(name: str, raw_args: Mapping[str, Any], ctx: ToolContext) -> ToolEnvelope: ...
```

### Tool context (built server-side; the model never supplies it)
```python
@dataclass(frozen=True)
class ToolContext:
    principal: PatientPrincipal              # session_id, clinic_id, channel, verified_patnum
    od: ClinicODContext                      # P1-15/P1-19
    config: ActiveConfig                     # pinned version (P1-19)
    state: str                               # current state name (P2-01), for audit details
    db: AsyncSession
    redis: Redis
    request_id: str
    client_ip: str | None

async def build_tool_context(principal: PatientPrincipal, state: str, *, db: AsyncSession, redis: Redis,
                             request_id: str, client_ip: str | None) -> ToolContext: ...
```

### Result envelope (what the model receives)
```json
{"ok": true,  "data": { "...output model..." }}
{"ok": false, "error": {"code": "slot_taken", "next": "offer_alternatives", "data": {"alternatives": []}}}
```
| `error.code` | `next` (hint for the flow) | Source |
|---|---|---|
| `invalid_arguments` | `ask_user` | Input validation (no echo of values) |
| `not_verified` | `verify_first` | Patient-scoped tool without `verified_patnum` |
| `unknown_handle` | `refresh` | Handle not in this session |
| `slot_taken`, `slot_busy` | `offer_alternatives` | P1-20 |
| `offer_expired` | `search_again` | P1-20 |
| `patient_conflict` | `ask_user` | P1-20 |
| `inside_notice_window` | `callback` | Cancel or reschedule inside the notice window with `inside_notice_action=callback` |
| `not_changeable` | `explain` | P1-16 `AppointmentNotChangeable` |
| `duplicate_risk`, `too_many_matches` | `callback` | P1-16 |
| `not_bookable` | `callback` or `explain` | P1-20 `when_not_bookable` |
| `in_progress` | `wait_and_check` | P1-16/P1-20 |
| `outcome_unknown` | `callback_confirm` | P1-16/P1-20 |
| `od_unavailable` | `callback` | P1-15 errors (unavailable, rate limited, timeout, queue timeout, auth, version) |
| `timeout` | `callback` | Runner timeout |
| `not_available` | `callback` | Stub tool not yet implemented |
| `internal_error` | `callback` | Anything else (logged with `error_code`, never the message) |

The flows (P2) decide the wording. `next` is only a hint for the state machine.

### Handles (`handles.py`)
- **Storage:** Redis hash `tools:h:{session_id}`, TTL = `PATIENT_SESSION_IDLE_S` (P1-13), refreshed on use.
- **Appointment handles:** `A1`, `A2`, … → `{apt_num, pat_num}` (only for appointments of the session's verified patient).
- **Candidate list:** `cand` → the PatNum list from the last `search_patient` + `search_fp` (an HMAC of the normalized last name, DOB and phone, using the P1-05 `bidx-keyset`; no plain values) + `outcome`.
- **Slots** use P1-20's `slot_id` and offer store (no second store).
- **Resolution:** a handle is resolved only for the same `session_id` **and** only if its `pat_num` equals the active `principal.verified_patnum` (household support, DECISIONS #185). Unknown or another person's handle → `unknown_handle`. Switching the active patient clears appointment handles.

### Tool table
| Tool | Input (model sends) | Output (model sees) | Writes | Audit | Timeout |
|---|---|---|---|---|---|
| `search_patient` | `last_name`, `dob` (YYYY-MM-DD), `first_name?`, `phone?` (E.164) | `{outcome: "no_match"\|"verify"\|"ambiguous", ask_for: ["mobile_phone"\|"zip_code"…]}` | no | `patient.search` (`audit_now`; `match_count`, `identifiers_used`) | 10 s |
| `verify_patient` (stub → P2-12) | `answers: {mobile_phone?, zip_code?, first_name?}` | `{verified: bool, attempts_left: int}` | session only | `patient.verify` / `patient.verify_failed` | 10 s |
| `create_patient` | `first_name`, `last_name`, `dob`, `mobile_phone`, `email?`, `address?{line1,line2,city,state,zip}` | `{created: true}` | yes | `patient.create` | 20 s |
| `get_appointment_availability` | `reason_code`, `urgent?`, `preferences?{earliest_date, latest_date, weekdays, parts_of_day, provider_name?}`, `later?: bool` | `{status, options: [{slot_id, when, provider, visit}], more: bool}` | no | none (no PHI read) | 9 s |
| `get_patient_appointments` | `{}` | `{appointments: [{handle, when, provider, visit, status}]}` (future, `Scheduled` only) | no | `patient.search` (`audit_now`, `reason_code=appointments_list`, `count`) | 10 s |
| `book_appointment` | `slot_id` | `{booked: true, when, provider, visit}` | yes | `appointment.book` | 45 s |
| `reschedule_appointment` | `handle`, `slot_id` | `{rescheduled: true, when, provider, visit}` | yes | `appointment.reschedule` | 45 s |
| `cancel_appointment` | `handle` | `{cancelled: true}` | yes | `appointment.cancel` | 30 s |
| `get_clinic_information` | `topics: [hours\|address\|phone\|parking\|insurance\|services\|languages\|payment\|new_patients\|website]` | `{answers: {topic: text}}` from config | no | none | 1 s |
| `get_provider_information` | `provider_name?` | `{providers: [{name, specialty, works_on: ["Mon","Tue"…]}]}` | no | none | 5 s |
| `create_callback_request` (stub → P2-22) | `reason_code`, `urgency`, `summary` (≤ 500 chars) | `{case_ref: "CB-7Q2M", promise: text}` | yes | `callback.create` | 10 s |
| `record_consent` (stub → P4-02) | `channel`, `granted: bool`, `template_id`, `address_source` (added by P4-02: `whatsapp_number`\|`mobile_phone`\|`phone`\|`household`; the number itself is never an argument, DECISIONS #256) | `{recorded: true, consent_id}` | yes | `consent.grant` / `consent.revoke` | 5 s |

`when` is P1-20's `local_label` (e.g. "Tue Dec 8, 9:00 AM"). `provider` is the provider's display name. `visit` is the P0-02 reason label.

### Handler rules (the parts that are not just pass-through)
**`search_patient`:**
1. Run `search_by_name_dob`, and `search_by_phone` if a phone was given (P1-16). Merge by PatNum.
2. Keep `counts_as_existing` and non-existing matches separately.
3. **Outcome until P2-12 replaces the scoring:**
   - 0 matches → `no_match`;
   - exactly 1 existing-status match → `verify`;
   - more than 1, any non-existing-status match, or `TooManyMatchesError` → `ambiguous`.
4. Store `cand` and `search_fp`. `ask_for` comes from `config.verification.one_of`.
5. **Never** return names, counts, statuses or PatNums.

**`create_patient`:**
1. Requires `cand.outcome == "no_match"` with a `search_fp` equal to the fingerprint of this input (the patient was searched with the same last name and DOB first), and `config.policies.new_patient_auto_create`. Otherwise → `duplicate_risk`.
2. Call P1-16 `create` with key `create_patient:{session_id}`.
3. On success call `mark_verified(session_id, pat_num)` (P1-13). The PatNum is not returned.

**Patient-scoped tools** (`get_patient_appointments`, `book`, `reschedule`, `cancel`) require `principal.verified_patnum`, else `not_verified`. They pass only that PatNum to P1-16 and P1-20.

**`get_patient_appointments`:**
- `list_for_patient(today, today + 365 days, statuses={SCHEDULED})`, sorted, at most 10;
- assigns handles `A1…A10` (replacing earlier ones).

**`get_appointment_availability`:**
- maps input to P1-20 `AvailabilityRequest`;
- `patient_type` = `"existing"` if `verified_patnum` else `"new"`; `age_years` from the verified patient's DOB (P1-16 `get`, in memory only);
- `provider_name` is matched against provider display names to a `prov_num`, else ignored with `status: "options"` plus `provider_not_found: true`;
- `later: true` uses the stored `next_cursor`.

**`book_appointment`:**
1. `BookingService.book(pat_num=verified, slot_id, is_new_patient = session created this patient)`.
2. On `booked`, `audit(appointment.book, SUCCESS, object_ref=apt_num, details={"channel", "reason_code": <reason code>})` in the tool's DB transaction.
3. If the audit insert fails, the appointment exists anyway (Open Dental is the truth). Return success to the patient, log `audit.write_failed` (alert A11), and leave a repair record: the P1-16 guard row already holds the AptNum.

**`reschedule_appointment` / `cancel_appointment`:**
1. Resolve the handle to `apt_num`.
2. **Notice window:** the appointment's start minus now < `reschedule_min_notice_hours` / `cancel_min_notice_hours`, and `inside_notice_action == "callback"` → `inside_notice_window` (no write).
3. Then call `BookingService.move` / P1-16 `cancel` (key `cancel:{session_id}:{apt_num}`).
4. Audit as above.

**`get_clinic_information`:** reads `clinic_info`, `clinic`, `hours` and `holidays` only.
- Hours are rendered as text from config: "Mon–Thu 8 AM–5 PM, Fri 8 AM–2 PM; closed Dec 25".
- Unknown or empty topic → `"I don't have that information"` text code `unknown`, and the flow may offer a callback.

**`get_provider_information`:**
- providers from the P1-15 cache, minus hidden ones, only those in the P0-02 mapping or with `clinic_info.provider_bios`;
- `works_on` from Provider schedules over the next 14 days (cached schedules).

### Sanitizing (`sanitize.py`, applied to every output)
- The output model is validated with `extra="forbid"`, so no field outside the declared model can leave.
- Strings: control characters stripped; max length per field (default 200); no `{`/`}` or `<`/`>` from Open Dental or config text (stops injected instructions from config or notes reaching the model as markup).
- **No Open Dental internals:** no PatNum, AptNum, ProvNum, OpNum, DefNum, notes or Open Dental error text in any output (test T14 scans outputs for integers that equal known IDs).

### Config extension (P1-19): `clinic_info`
```yaml
clinic_info:
  address: {line1: "100 Main St", line2: "Suite 200", city: "Portland", state: "OR", zip: "97201"}
  parking: "Free parking behind the building."
  insurers_accepted: ["Delta Dental", "Cigna", "Aetna", "MetLife"]      # names only; no coverage checks (P0-01 Q6)
  insurance_note: "We can't check your coverage in this chat; our team can help with that."
  insurer_aliases: {"Blue Cross Blue Shield": ["BCBS", "Blue Cross"]}   # optional, added by P2-18 (DECISIONS #199)
  services: ["Cleanings and checkups", "Fillings", "Crowns", "Emergency visits"]
  languages: ["English", "Spanish"]
  payment: "We accept cards, cash and CareCredit."
  new_patients: "New patients are welcome. Please arrive 15 minutes early."
  provider_bios: {}                      # optional: {"<od_prov_num>": "Dr. Lee has practised family dentistry since 2010."}
```
- **Rules:** every text ≤ 300 chars; no placeholders; list items ≤ 60 chars; `provider_bios` keys must be existing provider numbers (P1-19 Open Dental check, warning only).
- **Editing:** console-editable. The section is optional with empty defaults, so existing versions stay valid. `schema_version` stays 1 because the change is additive.

### Settings
```python
TOOLS_DEBUG_ENDPOINT: bool = False        # allowed True only with ENV in {local, dev}
TOOL_OUTPUT_MAX_STR: int = 200
```

### Log events and metrics
| Event / metric | Fields |
|---|---|
| `tool.call` | `tool`, `ok`, `error_code`, `duration_ms`, `state`, `channel`, `clinic_id` |
| `stage_timer(Stage.TOOL_CALL, tool=…)` | latency histogram per tool |
| `dai.booking.outcome` | already recorded by P1-20 |

### Example
```python
env = await run_tool("search_patient", {"last_name": "Lopez", "dob": "1985-03-14"}, ctx)
# -> {"ok": true, "data": {"outcome": "verify", "ask_for": ["mobile_phone", "zip_code"]}}
env = await run_tool("book_appointment", {"slot_id": "k3H9xQ2mPa"}, ctx)    # ctx.principal.verified_patnum = 48
# -> {"ok": true, "data": {"booked": true, "when": "Tue Dec 8, 9:00 AM", "provider": "Dr. Lee", "visit": "Cleaning and checkup"}}
env = await run_tool("cancel_appointment", {"handle": "A1", "pat_num": 312}, ctx)
# -> {"ok": false, "error": {"code": "invalid_arguments", "next": "ask_user"}}    # extra field rejected
```

## 7. Implementation guide
1. **Read** P0-04 (states, allowed tools, guards), P1-13 §6 (patient session), P1-16, P1-20 and P1-19 §6, P1-07 audit rules. **Verify** the Vertex AI function-declaration schema subset, and record it in `docs/tools/README.md`.
2. **Registry, envelope, runner:**
   - input validation (strict, `extra="forbid"`);
   - `asyncio.timeout(spec.timeout_s)`;
   - error mapping table;
   - sanitizer;
   - audit wrapper (`audit_now` for reads and failures, `audit` in the transaction for writes);
   - metrics (T1–T5).
3. **Handles store and context builder** (T6, T7).
4. **Patient tools:** `search_patient`, `create_patient` (T8–T10).
5. **Appointment tools:** availability, list, book, reschedule, cancel, including the notice-window rule (T11–T15).
6. **Info tools** and the `clinic_info` section added to P1-19's models, rules and seed (T16, T17).
7. **Stubs** for `verify_patient`, `create_callback_request`, `record_consent`, with their final input and output models (T18).
8. **Generators:** JSON Schemas, Gemini declarations, README table, plus the CI staleness check (T19).
9. **Debug endpoint** (local and dev only) and the leak suite run (T20).
10. **Notify:**
    - P2-08: `run_tool`, `ToolContext`, error codes, the stub replacement API;
    - P2-12: the `verify_patient` contract and the `search_patient` scoring hook;
    - P2-22, P4-02: stub contracts;
    - P2-16, P2-18, P2-20: tool outcomes and `next` hints;
    - P4-11: the `clinic_info` screen;
    - P3: the same tools for voice.

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| Model adds `pat_num` or `apt_num` to any tool call | `invalid_arguments` (extra field); event `tool.call` with `error_code=invalid_arguments` |
| Model invents a handle `A7` that was never issued | `unknown_handle` |
| Model sends a `slot_id` from another session | P1-20 offer store miss → `offer_expired` |
| `book_appointment` before verification | `not_verified` (P2-08 also blocks it earlier) |
| `create_patient` without a prior no-match search for the same name+DOB | `duplicate_risk`; no Open Dental call |
| `search_patient` finds an Archived patient with the same name+DOB | `ambiguous` → flow goes to a callback; nothing about the record revealed |
| Patient asks "Am I a patient there?" before verification | The tool output gives no yes or no; the AI can only say it needs to verify first |
| Cancel 3 hours before the appointment, 24 h policy, action `callback` | `inside_notice_window`; no Open Dental write |
| Booking succeeds but the audit insert fails | Patient told it is booked; `audit.write_failed` alert A11; guard row has the AptNum for repair |
| Open Dental down during availability | `od_unavailable` → callback |
| Tool exceeds its timeout | `timeout`; for writes the P1-16 guard row stays and a later retry reconciles |
| Config text contains `<script>` or `{instructions}` | Rejected by the P1-19 rule; the sanitizer also strips it at output |
| A stub tool is called before its task lands | `not_available` → callback |
| Provider name "Dr. Smith" matches two providers | Both returned in `get_provider_information`; availability asks the user to choose (`provider_not_found` only when 0 match) |

## 9. Security, HIPAA and PHI
- **PHI handled:**
  - inputs: names, DOB, phone, email and address (`search_patient`, `create_patient`, `verify_patient`), the callback summary;
  - outputs: appointment times, provider and visit type for the verified patient only.
- **Where it goes:** to P1-16 and P1-20 in memory. Redis handles hold PatNum or AptNum lists and an HMAC fingerprint only (Memorystore with TLS, AUTH and CMEK). The database gets audit rows with IDs and codes only.
- **What the model can see:**
  - no identifiers (PatNum, AptNum, ProvNum…);
  - no record details before verification;
  - no Open Dental notes or error text;
  - no other patient's data.

  The model's own inputs (what the patient said) are PHI already sent to Vertex AI under the Google Cloud BAA (P0-09). The tools add nothing beyond the minimum.
- **Session scoping:** the patient identity comes only from the session's `verified_patnum`, and handles resolve only within their session (T7, T12).
- **Audit:**
  - every patient read (`patient.search`) and every write (`patient.create`, `appointment.*`) is audited with actor `PATIENT_SESSION`, `tool` and `state` details;
  - denials and validation failures are logged (`tool.call`); P2-08 adds `security.tool_denied`.
- **Never logged:** tool arguments or outputs. Only tool name, ok, error code, duration, state and channel (P1-07 allow-list).
- **Debug endpoint:** refused in staging and prod by a settings validator, and protected by internal auth.
- **Risks reduced:** cross-patient access, disclosure before verification (§4.5), prompt-injection-driven actions (together with P2-08), PHI in logs (P0-11 R01).

## 10. Testing
| # | Test | Expected |
|---|---|---|
| T1 | Every `ToolSpec` input model rejects unknown fields and wrong types | `invalid_arguments`; values not echoed |
| T2 | Runner timeout (fake handler sleeps) | `timeout` within spec `timeout_s` + 0.5 s |
| T3 | Each error-mapping row (fake raises each typed error) | Matching `code` and `next` |
| T4 | Sanitizer: control chars, long strings, `<…>` | Stripped and truncated |
| T5 | `tool.call` event and `Stage.TOOL_CALL` timer for every call | Present; no argument values |
| T6 | Handles: list → `A1`, `A2`; other session uses `A1` | Resolves only in the issuing session |
| T7 | `ToolContext` built from a principal without `verified_patnum` → patient-scoped tools | `not_verified` |
| T8 | `search_patient` on `od_fake`: no match, one Patient, twins, Archived twin | `no_match`, `verify`, `ambiguous`, `ambiguous`; output has no names, counts or IDs |
| T9 | `create_patient` after `no_match` with the same name+DOB / with a different DOB | Created and session marked verified / `duplicate_risk`, no POST |
| T10 | `create_patient` with `new_patient_auto_create: false` | `duplicate_risk` → callback; no POST |
| T11 | `get_appointment_availability` → `book_appointment` with the returned `slot_id` | Booked; `appointment.book` audit row; output has `when`, `provider`, `visit` only |
| T12 | `book_appointment` with `pat_num` field; cancel with another session's handle | `invalid_arguments`; `unknown_handle` |
| T13 | `cancel_appointment` inside the 24 h window / outside | `inside_notice_window` (no write) / cancelled + audit |
| T14 | **ID leak scan:** run all tools on `od_fake`; search outputs for any PatNum, AptNum, ProvNum, OpNum present in the fake | None found |
| T15 | `reschedule_appointment` | Same appointment moved; `appointment.reschedule` audit |
| T16 | `get_clinic_information(["hours","insurance","parking"])` | Text from config; no Open Dental or LLM call |
| T17 | `get_provider_information()` | Non-hidden mapped providers with `works_on` from schedules |
| T18 | Stub tools | `not_available`; `register(..., replace_stub=True)` swaps the handler |
| T19 | Generated schemas and Gemini declarations | Match the models (CI staleness check); every schema uses only the Verify'd subset |
| T20 | Whole suite under P1-07's leak capture | No PHI in logs |

## 11. Acceptance criteria
- [ ] All 12 tools are registered with input and output models; JSON Schemas, Gemini declarations and the tools README are generated and current (T19)
- [ ] The 9 P1-22 tools work end to end against `od_fake`; the 3 stub tools return `not_available` and can be replaced by `register(..., replace_stub=True)` (T8–T18)
- [ ] No tool accepts a PatNum, AptNum or slot details from the model; patient identity comes only from the session; handles resolve only within their session (T1, T6, T7, T12)
- [ ] `search_patient` never reveals whether or which records exist; `create_patient` runs only after a matching no-match search (T8–T10)
- [ ] Cancel and reschedule respect the clinic's notice window (T13)
- [ ] Every patient read and write is audited with the right action, actor and details; booking success is never reported as failure because of an audit error (T11, T13, T15)
- [ ] Outputs pass the sanitizer and contain no Open Dental identifiers, notes or error text (T4, T14)
- [ ] `get_clinic_information` and `get_provider_information` answer from config and cache with no LLM call (T16, T17); the `clinic_info` section exists in P1-19's model and seed
- [ ] Errors map to the code table with `next` hints (T3); no PHI in logs (T20)

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI (T1–T20)
- [ ] PR reviewed (HIPAA review if labelled `phi`): labelled `phi`; tech lead + compliance owner review scoping, disclosure rules and audit
- [ ] No PHI in logs
- [ ] Docs / README updated: `docs/tools/README.md` (generated table + Verify notes), P1-19 `docs/clinic-config.md` (`clinic_info`)

## 13. Hand-off
| Task | Can rely on |
|---|---|
| P2-08 Tool gateway | `REGISTRY`, `run_tool`, `ToolContext`, envelope and error codes; wraps them with allow-list, preconditions and injection checks |
| P2-12 Matching and verification | `verify_patient` input and output contract; replaces the `search_patient` outcome rule with its scoring through a hook `set_search_scorer()`; calls `mark_verified` |
| P2-16 / P2-18 / P2-20 Flows | Tool outputs and `next` hints; handles `A1…`; `slot_id`s from availability |
| P2-22 Callback | `create_callback_request` contract to implement |
| P4-02 Consent | `record_consent` contract to implement |
| P4-11 Policies screens | `clinic_info` section is console-editable |
| P3 Voice | Same registry and envelope (channel only changes `ToolContext.principal.channel`) |
| P5-08 Security testing | Scoping tests T6, T7, T12 and leak scan T14 to extend with red-team prompts |

## 14. Open questions
| Question | Recommended answer | Owner | Needed by |
|---|---|---|---|
| Is `record_consent` a P4-02 tool (P0-04 open question)? | Yes: schema and stub here, handler in P4-02. | Tech lead | Before P2-08 |
| May the AI list the insurers the clinic accepts (P0-01 Q6)? | Yes, names only from `clinic_info.insurers_accepted`; never coverage checks; coverage questions go to a callback. | Clinic (P0-01) | Before pilot |
| Which JSON Schema keywords does Vertex AI function calling accept for the chosen GA model? | Keep schemas to types, enums, required, min/max length and simple formats; check the docs and one real call in dev. | Tech lead | Step 1 |

## 15. References
- Plan §1, §4.2, §4.3, §4.5, §4.6, §4.9
- P0-04 flows (states, allowed tools, guards), P1-13 patient session, P1-07 audit
- Vertex AI function calling: https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/function-calling
- Pydantic JSON Schema generation: https://docs.pydantic.dev/latest/concepts/json_schema/
- JSON Schema 2020-12: https://json-schema.org/draft/2020-12
- Related tasks: P0-01, P0-04, P1-05, P1-07, P1-13, P1-15, P1-16, P1-19, P1-20, P2-01, P2-08, P2-12, P2-16, P2-18, P2-20, P2-22, P3-02, P4-02, P4-11, P5-08
