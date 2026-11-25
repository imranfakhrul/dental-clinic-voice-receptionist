---
id: P2-05
title: Intent and slot extraction with per-state structured JSON output
milestone: P2
epic: E2.1
size: M
labels: area:ai, type:feature, phi
depends_on: P0-02, P0-04, P1-20, P2-01, P2-03, P2-04
status: approved
---

# P2-05: Intent and slot extraction with per-state structured JSON output

## 1. Summary
For every patient turn, one call to the `flash` tier turns the patient's words into a validated JSON object:
- the intent(s);
- the slot values the current state collects (name, DOB, phone, preferred time, reason);
- a proposed state-machine event from the state's closed list;
- a second-opinion emergency signal.

Code then validates and normalizes every value and returns P2-01's `Extraction`. The JSON schema is **built per state** (only that state's slots and events, as enums), so the model cannot return an event or slot the state doesn't allow.

Done means:
- `Extractor.extract()` returns a valid `Extraction` for every turn, or `understood=False` on any failure;
- invalid or uncertain values are never stored;
- relative dates ("next Tuesday after 3") become P1-20 `Preferences` checked by code;
- the model can only raise, never lower, the rule-based emergency result;
- on the 100-utterance eval set: intent accuracy ≥ 95%, slot accuracy ≥ 95%, emergency recall 100%.

## 2. Why this matters
Plan §4.1: the LLM handles "intent extraction, slot extraction (name, DOB, phone, preferred time)"; §4.3: "Intent and slot extraction → Gemini Flash-class model with structured (JSON) output". Every flow depends on this: a wrong intent sends the patient down the wrong path, a wrong DOB fails verification, a wrong date offers the wrong slots. It drives the pilot target of ≥ 70% bookings without callback.

Because "code decides" (DECISIONS #155), extraction only **proposes**; P2-01 rejects events not allowed in the state, and the slot catalogue rejects invalid values. This task makes those proposals as accurate as possible and keeps them inside the allowed set.

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P2, Text Chat Receptionist**.
- **Terms:**
  - **Intent:** what the patient wants overall (book, cancel…). One per conversation goal; a turn may carry two.
  - **Slot:** a piece of collected information (GLOSSARY "Slot memory"), not an appointment time.
  - **Structured output:** asking Gemini to answer with JSON that follows a given schema (`response_mime_type="application/json"` plus a schema). Docs: https://docs.cloud.google.com/vertex-ai/generative-ai/docs/multimodal/control-generated-output. **Verify:** which JSON Schema keywords are supported (`enum`, `format: date`, `nullable`/`anyOf`, `maxItems`, `propertyOrdering`), and the size limits on schemas.
- **What already exists:**
  - **P2-01** (approved): `Extraction(proposed_event, slots, understood, emergency_signal)`; `flow.events_for(state)`; the YAML `collects` per state; slot catalogue (type, validator, normalizer, PHI flag); `SlotMemory.set(name, value, source="patient")`; the turn processor (step 6 calls extraction).
  - **P2-03** (approved): `LlmProvider.structured(req, schema)`; `ModelRouter.route(RouteInput(purpose="extract", ...))` (R4–R7 escalate to `pro`); errors `LlmUnavailable`, `LlmBadOutput`, `LlmBlocked`; the caller contract: on those errors return `Extraction(understood=False)`.
  - **P2-04** (approved): `ContextBuilder.build_extract(state, slots, turns, user_text, system, tier)`; `base_rules_v1.md`; normalized user text.
  - **P0-04** (approved): states, `collects`, events, intents `book`, `reschedule`, `cancel`, `check_appointment`, `faq`, `talk_to_human`, `other`; two-intents rule (§8 there).
  - **P0-02** (approved): `reason_code` enum (`new_patient_exam`, `recall_cleaning`, `child_visit`, `toothache`, `sensitivity`, `broken_tooth`, `lost_filling_or_crown`, `gum_problem`, `wisdom_tooth`, `denture_problem`, `cosmetic_consult`, `ortho_consult`, `emergency_exam`, `treatment_followup`, `other`).
  - **P1-20** (approved): `Preferences(earliest_date, latest_date, weekdays, parts_of_day, prov_num)`; `PartOfDay` morning `< 12:00`, afternoon `12:00–17:00`, evening `≥ 17:00`.
  - **P1-19** (approved): `scheduling.booking_horizon_days` (default 7), clinic IANA time zone.
  - **P2-20** (later): the rule-based emergency detector, which runs **before** extraction.

## 4. Scope
**In scope**
- **Package `backend/app/orchestrator/extraction/`:**
  - `schema_builder.py`: builds and caches the per-state JSON schema and the matching Pydantic model;
  - `extractor.py`: `Extractor.extract()`;
  - `normalize.py`: converts the model's raw values into slot-catalogue values (dates, phones, names, preferences);
  - `prompt/extract_system_v1.md`: the extraction system prompt (includes P2-04's `base_rules_v1.md`).
- **P0-04 extension:** intent `complaint` added to the intent enum (DECISIONS #170); handled in `INTENT` by offering a callback.
- **Eval set** `evals/extraction/cases.yaml` (100 synthetic cases) and a runner `evals/extraction/run.py`.
- **Tests and docs:** unit tests with `FakeLlmProvider`; `docs/extraction.md`.

**Out of scope** (and which task covers it)
- LLM calls, retries, routing → P2-03
- Context frame, PHI scrubbing, injection handling → P2-04
- Deciding transitions, storing slots → P2-01
- Emergency rules and the final emergency policy → P2-20 (this task only supplies the model's signal)
- Name spelling read-back and phone read-back wording → P2-04 templates, flow tasks
- Voice-specific STT quirks (number words, spelled letters) beyond what the eval set covers → P3 (adds voice cases)
- Full eval harness and CI gating → P5-01 (reuses this set)

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P2-01 (approved) | `Extraction`, `events_for`, `collects`, slot catalogue | Load the approved `state_machine.yaml`; catalogue functions can be imported directly |
| P2-03 (approved) | `structured()`, router | `FakeLlmProvider` scripted with JSON values |
| P2-04 (approved) | `build_extract()`, `base_rules_v1.md` | Use the frame layout in P2-04 §6 |
| P1-20 (approved) | `Preferences`, `PartOfDay` | Import the models |
| P0-02 (approved) | `reason_code` enum | Import from the P0-02 schema |
| P2-20 (parallel) | Rule-based `emergency_signal` | Pass `"none"` in tests; the merge rule is defined here (§6) |
| Vertex AI in `<prefix>-dev` | Live eval runs | Unit tests need only the fake; live eval runs with synthetic data only |

## 6. Interface contract

### Public API (`extractor.py`)
```python
class Extractor:
    def __init__(self, llm: LlmProvider, router: ModelRouter, builder: ContextBuilder,
                 flow: FlowDefinition, schemas: SchemaCache) -> None: ...

    async def extract(self, *, st: ConversationState, slots: SlotMemory, turns: Sequence[Turn],
                      user_text: str, rule_emergency: EmergencySignal, today_local: date,
                      tz: ZoneInfo, horizon_days: int, channel: Literal["TEXT", "VOICE"]) -> ExtractionResult: ...

class ExtractionResult(BaseModel):
    extraction: Extraction               # P2-01 model, ready for the turn processor
    intents: tuple[str, ...] = ()        # primary first; ≤ 2 (feeds RouteInput.intent / intent_count)
    unclear_slots: tuple[str, ...] = ()  # asked again, never stored
    invalid_slots: tuple[str, ...] = ()  # failed validation; asked again
    reason_code: str = "ok"              # ok | llm_unavailable | bad_output | blocked | empty_input
```
`EmergencySignal = Literal["none", "tier1", "crisis", "tier2", "uncertain"]` (P2-01).

### What the model returns (per-state schema; example for `AVAILABILITY`)
Built by `schema_builder.build(state)` from the YAML, cached per `(flow_version, state)`:
```json
{
  "type": "object",
  "properties": {
    "intents": {"type": "array", "maxItems": 2,
                "items": {"type": "string", "enum": ["book", "reschedule", "cancel", "check_appointment",
                                                      "faq", "talk_to_human", "complaint", "other"]}},
    "proposed_event": {"type": "string", "nullable": true,
                       "enum": ["time_preference_given", "option_chosen", "want_later", "intent_changed",
                                "faq_asked", "human_requested"]},
    # Additive (P2-18, DECISIONS #199), FAQ state and the faq_asked interrupt only:
    #   "faq_topics": array (max 3) of hours|address|phone|parking|insurance|services|languages|payment|new_patients|website|providers|other
    #   "insurance_question": none|list|specific_insurer|coverage_or_cost;  "insurer_name": string (max 60)
    #   CANCEL state: "cancel_reason" is set from choices only (no LLM field)
    # Additive (P3-09, DECISIONS #238): READ_BACK state: "readback_answer": yes|no|correction|unclear;
    #   any voice state: "wants_to_spell": boolean ("let me spell it")
    "understood": {"type": "boolean"},
    "unclear_slots": {"type": "array", "items": {"type": "string", "enum": ["preferred_time", "chosen_slot"]}},
    "slots": {
      "type": "object",
      "properties": {
        "preferred_time": {"type": "object", "nullable": true, "properties": {
            "earliest_date": {"type": "string", "nullable": true, "description": "YYYY-MM-DD"},
            "latest_date":   {"type": "string", "nullable": true, "description": "YYYY-MM-DD"},
            "weekdays": {"type": "array", "items": {"type": "string", "enum": ["mon","tue","wed","thu","fri","sat","sun"]}},
            "parts_of_day": {"type": "array", "items": {"type": "string", "enum": ["morning","afternoon","evening"]}},
            "after_time":  {"type": "string", "nullable": true, "description": "HH:MM 24h"},
            "before_time": {"type": "string", "nullable": true, "description": "HH:MM 24h"},
            "provider_name": {"type": "string", "nullable": true}}},
        "chosen_slot_ref": {"type": "string", "nullable": true, "enum": ["1", "2", "3"]}
      }
    },
    "emergency_signal": {"type": "string", "enum": ["none", "tier1", "crisis", "tier2", "uncertain"]}
  },
  "required": ["intents", "proposed_event", "understood", "unclear_slots", "slots", "emergency_signal"]
}
```
Event names in this example and in the eval excerpt below (`time_preference_given`, `option_chosen`, `want_later`, `intent_given`) are illustrative; the builder always uses the exact names in `state_machine.yaml`.

Rules for the builder:
- `proposed_event.enum` = `flow.events_for(state)` minus events only code may fire (tool-result events such as `match_strong`, `commit_conflict`, `od_unavailable`, `not_understood_limit`, `idle_timeout`, `channel_switched`, and all `emergency_*` events). The list of code-only events lives in `schema_builder.CODE_ONLY_EVENTS`; a test checks every YAML event is in exactly one group.
- `slots` contains only the state's `collects` plus the global slots `intent` (via `intents`) and `reason_text`.
- Each slot uses a **raw** representation the model can fill reliably (table below); `normalize.py` converts it.
- `unclear_slots.enum` = the same slot names.
- The schema must use only the keyword subset verified for Vertex AI (reuse P1-22's schema-subset checker). If `enum` on a nullable string is not supported, use `anyOf: [{enum}, {type: null}]` per the **Verify** result.

### Raw slot representations and normalization (`normalize.py`)
| Slot | Model returns | Code does | Invalid when |
|---|---|---|---|
| `first_name`, `last_name` | string as said; spelled letters joined ("S-M-I-T-H" → "Smith") | trim, collapse spaces, title-case only if all lower/upper | empty, > 60 chars, digits |
| `dob` | `YYYY-MM-DD` | parse; age 0–120 at `today_local` | unparsable, future, age > 120 |
| `phone`, `mobile_phone`, `whatsapp_number` | digits only (10 or 11) | `phonenumbers` → E.164 US | not a valid US number |
| `zip` | 5 digits | regex | not `^\d{5}$` |
| `email` | string | lowercase, `email-validator` | invalid |
| `address` | `{line1, line2, city, state, zip}` | trim; state is a 2-letter US code | missing line1/city/state/zip |
| `reason_code` | P0-02 enum value | as is | not in enum |
| `reason_text` | short phrase, ≤ 300 chars | trim | empty |
| `preferred_time` | object above | → P1-20 `Preferences` (below) | rules below |
| `chosen_slot` | `chosen_slot_ref` "1"–"3" | → the offered `slot_id` from the offer store (P1-20 `avail:{session_id}`) | ref not offered |
| `confirmation` | `"yes"` / `"no"` / `"change"` / null, plus `change_target` ∈ `name`, `dob`, `phone`, `email`, `address`, `reason`, `time`, `provider`, `appointment`, `callback_time` (null if not said) | `yes` → confirmation slot with the card's `op_hash`; `change` → event `change_requested` with the target (DECISIONS #174); `no` without a target → the AI asks what to change | null |
| `apt_num` | appointment ref (`"A1"`) from the listed appointments | must be a P1-22 handle in this session | unknown handle |
| `callback_time` | free phrase ≤ 120 chars | trim | empty |
| `situation` | phrase ≤ 500 chars | trim | empty |
| `consent_whatsapp` | `"yes"` / `"no"` | bool | null |

**Preferences conversion (Proposed, DECISIONS #171):**
- The frame gives the model `today: 2026-11-24 (Tuesday)` and the clinic's time zone (added by `build_extract` via an `extra_context` argument, see §7 step 3).
- `earliest_date` / `latest_date` must be ISO dates with `today_local ≤ date ≤ today_local + horizon_days + 30`. Out of range → `invalid_slots=["preferred_time"]`.
- If both `weekdays` and a single date are given, the date's weekday must be in `weekdays`; otherwise the slot is **unclear** (the patient said "Tuesday the 3rd" but the 3rd is a Thursday).
- `after_time` / `before_time` map to `parts_of_day` only when they cover a whole part (after 12:00 → afternoon + evening). Otherwise they are kept as an extra filter `time_window=(after, before)` for P2-16 to apply on P1-20 results (P1-20 `Preferences` has no time window; P2-16 filters options).
- `provider_name` → `prov_num` by exact or case-insensitive match against the P1-15 setup-cache provider display names; no match → dropped, with `unclear_slots=["preferred_time"]` only if nothing else was given.

### Emergency merge rule (DECISIONS #172)
```python
SEVERITY = {"none": 0, "tier2": 1, "uncertain": 2, "tier1": 3, "crisis": 3}

def merge_emergency(rule: EmergencySignal, model: EmergencySignal) -> EmergencySignal:
    if rule != "none":
        return rule                       # the rules result always stands; the model never lowers it
    if model in ("tier1", "crisis"):
        return "uncertain"                # model alone never triggers 911 wording; it raises to "uncertain" (which includes the 911 safety line)
    return model                          # "tier2" or "uncertain" or "none"
```
P2-20 owns the final policy and may change this function; the contract (model can only raise) stays. **Replaced by P2-20 `safety/policy.decide()` (DECISIONS #201)**: a model `tier1`/`crisis` raises any lower rule result (including `tier2`/`tier3`) to `uncertain`.

### Validation pipeline (inside `extract`)
1. Empty text after normalization → `understood=False`, `reason_code="empty_input"`, no LLM call.
2. `decision = router.route(RouteInput(purpose="extract", state=..., not_understood_in_state=..., turn_chars=len(user_text)))`.
3. `req = builder.build_extract(...)`, `res = await llm.structured(req, schemas.model_for(state))`.
4. On `LlmUnavailable` / `LlmBadOutput` / `LlmBlocked` → `Extraction(understood=False)` and the matching `reason_code` (P2-03 contract).
5. Drop `proposed_event` if not in `events_for(state)` (defence in depth; P2-01 rejects it too).
6. For each slot in `slots` and not in `unclear_slots`: normalize; on failure add to `invalid_slots` and drop.
7. `intents[0]` sets the `intent` slot if the state collects it or the intent changed (`intent_changed` is proposed by the model; code checks the intent really differs from `st.flags["intent"]`, otherwise the event is dropped).
8. `emergency_signal = merge_emergency(rule_emergency, model_signal)`.
9. `understood = model.understood and (any slot accepted or proposed_event is not None or intents)`.

### Example
State `AVAILABILITY`, today 2026-11-24 (Tuesday), patient: "next tuesday works but only after 3, with dr lee if possible".
Model JSON:
```json
{"intents": ["book"], "proposed_event": "time_preference_given", "understood": true, "unclear_slots": [],
 "slots": {"preferred_time": {"earliest_date": "2026-12-01", "latest_date": "2026-12-01", "weekdays": ["tue"],
                              "parts_of_day": [], "after_time": "15:00", "before_time": null, "provider_name": "Dr Lee"},
           "chosen_slot_ref": null},
 "emergency_signal": "none"}
```
Result:
```python
ExtractionResult(
  extraction=Extraction(proposed_event="time_preference_given",
                        slots={"preferred_time": {"preferences": Preferences(earliest_date=date(2026,12,1),
                               latest_date=date(2026,12,1), weekdays={1}, prov_num=3),
                               "time_window": ("15:00", None)}},
                        understood=True, emergency_signal="none"),
  intents=("book",))
```

### Extraction system prompt v1 (`prompt/extract_system_v1.md`, outline)
```text
You read one message from a patient talking to a dental clinic's receptionist and fill in a JSON form.
{base_rules_v1}
- Fill only what the patient actually said in <patient_message>. Never guess or complete values.
- If a value is unclear or could mean two things, leave it null and list the slot in "unclear_slots".
- Dates: use "today" from <context> to turn words like "next Tuesday" into YYYY-MM-DD.
- Dates of birth: YYYY-MM-DD. Phones: digits only. Spelled names: join the letters.
- "proposed_event": choose only from the allowed values, or null if none fits.
- "emergency_signal": "tier1" or "crisis" for danger to life; "tier2" for urgent dental pain, swelling or trauma;
  "uncertain" if it might be urgent; otherwise "none". Do not give advice.
- If the patient says "no, I meant …", return the corrected value.
```
The full text is versioned (`extract-v1`) and logged as `prompt_version`.

### Logs and metrics (no text, no values)
| Event / metric | Fields |
|---|---|
| `extraction.done` (debug) | `state`, `intent`, `count` (intents), `event`, `understood`, `reason_code`, `turn_seq`, `prompt_version` |
| `extraction.slot_rejected` (info) | `state`, `slot`, `reason_code` (`invalid` / `unclear` / `not_offered`) |
| `dai.extraction.outcome` (counter) | `result` (`ok` / `not_understood` / `llm_error`), `model_tier` |
| `dai.extraction.emergency_raised` (counter) | `from_signal`, `to_signal` |

P1-07 allow-list additions: `slot` (slot **name** only), `intent`.

## 7. Implementation guide
1. **Code-only events.** List them in `CODE_ONLY_EVENTS`; write the test that every YAML event is either model-proposable or code-only.
2. **Schema builder.** For each state, build the JSON schema and a matching Pydantic model (`create_model`, `extra="forbid"`). Run P1-22's Vertex schema-subset checker in a unit test for every state. **Verify** in dev (live test) that every state's schema is accepted by Vertex AI.
3. **Context.** Call `build_extract()` with an `extra_context` dict `{"today": "2026-11-24 (Tuesday)", "time_zone": "America/Los_Angeles", "offered": [{"ref": "1", "label": "..."}], "appointments": [{"ref": "A1", "label": "..."}]}`. Add this optional argument to P2-04's `build_extract` (additive; values are non-PHI). Offered options and appointment handles are needed to resolve "the second one" or "my Tuesday appointment".
4. **Prompt.** Write `extract_system_v1.md`; include `base_rules_v1.md`; render the allowed events and slots list from the schema so the prompt and schema never disagree.
5. **Normalizers.** Implement the table in §6, reusing the P2-01 slot-catalogue validators. Spelled-letter joining: a run of single letters separated by spaces, dashes or dots becomes one word.
6. **Preferences.** Implement the conversion and its checks; unit-test relative dates around month and year ends and DST changes (use `today_local` in the clinic TZ, never server UTC).
7. **Extractor.** Implement the pipeline; wire it into P2-01's turn-processor step 6.
8. **`complaint` intent.** Add it to P0-04's intent enum in `state_machine.yaml` (through P0-04's review, as P2-01 requires) and to the router's R4. Behaviour in `INTENT`: reply intent `offer_callback_complaint` (template added to P2-04's catalogue); the patient's yes fires `human_requested`.
9. **Eval set.** Write `evals/extraction/cases.yaml` (format below) and `run.py`, which runs every case through the real `Extractor` against Vertex AI in `<prefix>-dev` and prints intent, slot and emergency scores, failing below the thresholds.
10. **Docs and notifications.** `docs/extraction.md`. Notify P2-01 (wired), P2-03 (`complaint` in R4), P2-04 (`extra_context`, new template), P2-12 / P2-15 / P2-16 / P2-18 (raw slot meanings, `time_window`), P2-20 (merge rule), P3 (voice cases to add), P5-01 (eval set).

### Eval set format (`evals/extraction/cases.yaml`)
```yaml
version: 1
today: "2026-11-24"          # fixed; cases use relative dates against this
time_zone: America/Los_Angeles
cases:
  - id: ex-001
    state: INTENT
    text: "hi i need to get my teeth cleaned sometime next week"
    expect:
      intents: [book]
      slots: {reason_code: recall_cleaning}
      event: intent_given
  - id: ex-042
    state: IDENTIFY
    text: "it's jane, j-a-n-e, doe, born march 4th 1988"
    expect:
      slots: {first_name: Jane, last_name: Doe, dob: "1988-03-04"}
  - id: ex-077
    state: AVAILABILITY
    text: "no not tuesday, wednesday morning"
    history: [{role: model, text: "I have Tuesday at 9 or Tuesday at 11."}]
    expect:
      slots: {preferred_time: {weekdays: [wed], parts_of_day: [morning]}}
  - id: ex-091
    state: AVAILABILITY
    text: "my face is really swollen and it's getting hard to breathe"
    expect:
      emergency_signal_at_least: tier1        # model alone → merged "uncertain"; the rules detector (P2-20) is off in this eval
```
Coverage (100 cases, all synthetic; names from a fixed fictional list, phones `555-01xx`):
- 50 intent cases across all 8 intents, including 10 with two intents and 5 complaints;
- 30 slot cases: spelled names, DOB in 8 spoken/typed forms, phones with words and separators, relative dates around month end, "the second one", corrections;
- 10 emergency cases (P0-03 categories, paraphrased, without the rule keywords so the model is tested on its own) plus 5 non-emergency look-alikes ("my tooth hurts a little when I drink cold water");
- 5 injection-flavoured texts (the extraction must stay schema-valid and propose nothing unexpected).

**Scoring:** intent = `intents[0]` exact; slot = per expected slot, exact after normalization; emergency recall = share of emergency cases whose merged signal is not `none`. Thresholds: intent ≥ 95%, slot ≥ 95%, emergency recall 100%, look-alike false alarms ≤ 1 of 5.

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| Model proposes `confirmed` while in `IDENTIFY` | Not in the state's enum; if it still appears, dropped in step 5 and rejected by P2-01 |
| DOB "3/4/88" (ambiguous day/month, two-digit year) | Model should mark `dob` unclear; if it returns a value, code accepts it only if the age is 0–120 and it is not in the future, and the identify flow reads it back. Unclear → asked again with a format hint |
| "Tuesday the 3rd" when the 3rd is Thursday | `preferred_time` unclear; reply asks which one |
| Date beyond the horizon + 30 days | `invalid_slots`; the booking flow explains how far ahead it can book |
| "The second one" with no offer in the store | `chosen_slot` invalid (`not_offered`) |
| Patient corrects a previous value ("no, it's 0123 at the end") | New value replaces the old one via `SlotMemory.set` |
| Two intents ("cancel Tuesday and book next week") | `intents=["cancel","book"]` → router R5 uses `pro` for the reply; P0-04 §8 rule decides the flow |
| Complaint ("you people cancelled on me twice") | `intents=["complaint"]`; `offer_callback_complaint` reply |
| Message is only "yes" in `CONFIRM` | `confirmation="yes"`, event `confirmed` proposed; guards still decide |
| Message is only "yes" in a state without a yes/no question | `understood=False` (nothing to apply) → counted by P2-01 |
| Empty or whitespace-only text | `empty_input`, no LLM call |
| Model returns schema-valid JSON with `understood=true` but nothing usable | `understood=False` (step 9) |
| LLM error or invalid JSON twice | `Extraction(understood=False)`; P2-01 counts it toward `not_understood_limit` |
| Model says `tier1`, rules say `none` | Merged `uncertain` (P2-20 handles it with the 911 safety line) |
| Rules say `tier1`, model says `none` | `tier1` stands |
| Provider name not found | Dropped; booking continues without a provider filter |
| Spanish text | Extraction still attempted (Gemini understands it); reply stays English (P2-04) |

## 9. Security, HIPAA and PHI
- **PHI handled:** the current patient message (raw, for extraction), and extracted names, DOB, phone, email, ZIP, address, reason and situation text. They go to Gemini on Vertex AI (BAA-covered, P2-03) inside P2-04's frame, and into P2-01's encrypted slot memory via `SlotMemory.set`.
- **Minimization:** past turns and known slots reach the model masked (P2-04); the schema asks only for the current state's slots.
- **Never logged:** text, slot values, the model's JSON. Logs carry slot **names**, intents, events, codes and counts.
- **Eval data:** synthetic only; fictional names and `555-01xx` numbers; results files hold IDs, scores and timings, no text output.
- **Safety:** the model cannot lower an emergency signal, cannot fire code-only events, and cannot store an invalid value.

## 10. Testing
```bash
cd backend && pytest tests/unit/orchestrator/extraction -q
VERTEX_LIVE_TESTS=1 python -m evals.extraction.run --cases evals/extraction/cases.yaml   # dev, synthetic
```
| # | Case | Expected |
|---|---|---|
| T1 | Schema per state for every YAML state | Only that state's slots; event enum = `events_for(state)` − code-only; passes the Vertex subset checker |
| T2 | Every YAML event classified | In exactly one of model-proposable / code-only |
| T3 | Fake returns an event outside the enum | Dropped; `extraction.done` shows `event=None` |
| T4 | Normalizers: names, spelled names, DOB forms, phones, ZIP, email, address | Table §6 results; invalid cases listed in `invalid_slots` |
| T5 | Preferences: next Tuesday, "this weekend", "after 3", "mornings", month end, DST week | Correct `Preferences` and `time_window` in clinic TZ |
| T6 | Weekday/date mismatch | `unclear_slots=["preferred_time"]` |
| T7 | `chosen_slot_ref` with and without an offer | `slot_id` from the offer store / `not_offered` |
| T8 | `unclear_slots` contains `dob` while `dob` has a value | Value not stored |
| T9 | `merge_emergency` truth table | Matches §6 |
| T10 | LLM errors (`LlmUnavailable`, `LlmBadOutput`, `LlmBlocked`) | `understood=False` with the right `reason_code` |
| T11 | Empty text | No LLM call |
| T12 | `intent_changed` proposed with the same intent | Dropped |
| T13 | Log capture with a PHI corpus | No values in logs or metrics |
| T14 | Live (dev): every state's schema accepted by Vertex AI | No 400 |
| T15 | Live eval run | Intent ≥ 95%, slot ≥ 95%, emergency recall 100%, look-alike false alarms ≤ 1/5 |

## 11. Acceptance criteria
- [ ] The schema is built per state, and the model can only propose events allowed and non-code-only in that state (T1–T3)
- [ ] Every slot value is normalized and validated before storing; unclear and invalid values are never stored (T4–T8)
- [ ] Relative dates use the clinic's local date and time zone (T5)
- [ ] The model's emergency signal can only raise the rules result (T9)
- [ ] LLM failures return `understood=False` and never raise to the turn processor (T10)
- [ ] The eval set of 100 synthetic cases scores intent ≥ 95%, slot ≥ 95%, emergency recall 100% (T15)
- [ ] `complaint` is a P0-04 intent, routed to `pro` and answered with a callback offer
- [ ] No text or values in logs (T13)

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI; the live eval run is linked in the PR
- [ ] PR reviewed (HIPAA review: labelled `phi`)
- [ ] No PHI in logs
- [ ] `docs/extraction.md` written; P0-04 YAML change reviewed; P1-07 allow-list updated
- [ ] P2-01, P2-03, P2-04, P2-12, P2-15, P2-16, P2-18, P2-20, P3 and P5-01 issues notified

## 13. Hand-off
| Consumer | What they can rely on |
|---|---|
| P2-01 Turn processor | `Extractor.extract()` returns a validated `Extraction`, never raises for LLM problems |
| P2-03 Router | `intents` for `RouteInput.intent` / `intent_count`; `complaint` intent |
| P2-12 Identify/verify | Normalized names (spelled letters joined), ISO DOB, E.164 phone, ZIP |
| P2-15 Register | Normalized email and address |
| P2-16 Booking | `Preferences` plus optional `time_window`; `chosen_slot` as a real `slot_id` |
| P2-18 Reschedule/cancel | `apt_num` as a session handle; `confirmation` |
| P2-20 Emergency | Model signal and `merge_emergency()` |
| P5-01 Evals | `evals/extraction/cases.yaml` and the runner |

## 14. Open questions
| # | Question | Recommended answer | Owner |
|---|---|---|---|
| 1 | Should extraction use `lite` for simple yes/no states (`CONFIRM`) to save latency? | Not at first: measure in P5-01; if `lite` scores the same on `CONFIRM` cases, add a router rule. | AI lead |
| 2 | Should the 30-day tolerance beyond the booking horizon be config? | No: it only decides "invalid" vs "explain the horizon"; keep it a constant. | Tech lead |
| 3 | Do voice transcripts need their own eval cases now? | Add 20 voice-style cases in P3 when real STT output exists; text-style cases are enough for P2. | P3 owner |

## 15. References
- Plan: §4.1, §4.3, §4.5, §4.8
- Vertex AI structured output: https://docs.cloud.google.com/vertex-ai/generative-ai/docs/multimodal/control-generated-output
- `phonenumbers`: https://github.com/daviddrysdale/python-phonenumbers
- DECISIONS: #155, #156, #160, #162, #164, #169, #170, #171, #172
- Related tasks: P0-02, P0-03, P0-04, P1-15, P1-19, P1-20, P1-22, P2-01, P2-03, P2-04, P2-12, P2-15, P2-16, P2-18, P2-20, P3-02, P5-01
