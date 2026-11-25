---
id: P2-20
title: Emergency detector v1 (rules first, model second), emergency scripts and the Tier 2 urgent-slot path
milestone: P2
epic: E2.5
size: L
labels: area:ai, area:scheduling, type:feature, phi
depends_on: P0-03, P0-04, P1-19, P1-20, P1-22, P2-01, P2-03, P2-04, P2-05, P2-08, P2-12, P2-16
status: approved
---

# P2-20: Emergency detector v1 (rules first, model second), emergency scripts and the Tier 2 urgent-slot path

## 1. Summary
Build the safety layer that runs on **every** patient turn: a deterministic rule detector that implements P0-03's matching rules exactly, a merge policy with the model's second-opinion signal, and the `EMERGENCY` state handler that says the clinic-approved script and takes the tier action. This task absorbs **P2-21 (emergency scripts and Tier 2 urgent-slot path)**.

| Result | What happens |
|---|---|
| `tier1` | Rules alone trigger it. The 911 script is said at once (no LLM call that turn), an URGENT case is created without questions, booking stops for the rest of the session |
| `crisis` | 988 script, URGENT case, booking stops |
| `uncertain` | Safety script with the 911 line, URGENT case, then the previous flow resumes |
| `tier2` | Short intro, earliest urgent slot offered right away, then identification and booking; no slot → URGENT case |
| `tier3` | No interruption; the matched `reason_code` is pre-filled for normal booking |

Done means:
- every Tier 1 and crisis case in P0-03's test set gets the right script (100%), with 0 under-triage overall and ≥ 95% exact tier;
- the rules come from clinic config (prod loads only `approved` rules);
- script text comes only from config, never from the LLM;
- the patient's words never appear in logs.

## 2. Why this matters
Missing an emergency is the most serious safety risk in the project (plan §12: "Emergency misclassification → patient safety"). Plan §4.8 and §4.3 require:
- rules-first detection, with the model only as a second check;
- "when uncertain, create an URGENT callback request";
- fixed, pre-approved scripts with no diagnosis and no treatment advice;
- Tier 2: "offer the earliest urgent slot; if none is available, create an URGENT callback request and email the admin".

Pilot target: **100% emergency escalation in tests** (plan §11). Patients see or hear these exact scripts; clinic staff receive the URGENT cases these rules create (via P2-22's email and P4's console).

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P2, Text Chat Receptionist**.
- **Emergency tiers (P0-03, plan §4.8):** Tier 1 life-threatening (call 911), `crisis` (suicide or self-harm → 988), Tier 2 urgent dental (urgent slot or URGENT callback), Tier 3 routine (normal booking). `uncertain` = possibly Tier 1 but not certain; it is handled cautiously.
- **Under-triage:** treating an emergency as less serious than it is. Target 0. Over-triage (too cautious) is acceptable.
- **What already exists:**
  - **P0-03** (approved): `emergency_rules.yaml` (categories with `phrases` and `all_of_groups`, `matching.negation_words`, `negation_window_words`, `urgent_slot_max_hours`, `tier_actions`, `scripts`), the exact matching rules (§6 there, quoted in §6 here), status lifecycle `draft` → `clinic_reviewed` → `approved`, and the test set `evals/emergency/emergency_cases.yaml` (≥ 60 cases) with pass criteria.
  - **P1-19** (approved): `emergency_rules` section embedded in the pinned config version; prod activates only `approved`, staging `clinic_reviewed` or `approved`, local may use `draft`; file-only (not console-editable); every change is a new config version.
  - **P2-01** (approved): turn processor step 5 "Emergency first"; `Extraction.emergency_signal`; global interrupts; `flags.urgent`; `resume_state` (cleared for Tier 1 / crisis).
  - **P0-04** (approved): `EMERGENCY` side state; global events `emergency_tier1`, `emergency_crisis` (from any state, never resume) and `emergency_uncertain`, `emergency_tier2` (not from `EMERGENCY` itself); Tier 2 path sets `urgent=true` and `reason_code=emergency_exam`.
  - **P2-05** (approved): the model's `emergency_signal` from the same extraction call and the provisional `merge_emergency` ("model can only raise"); P2-20 owns the final policy.
  - **P2-03** (approved): emergency replies are templates; router purpose `emergency_check` → `flash`.
  - **P2-04** (approved): templates `emergency_tier1: {script: tier1_911}`, `crisis: {script: crisis_988}` rendered from the pinned `emergency_rules.scripts`; placeholders `{first_name}`, `{clinic_name}`, `{callback_phone}`.
  - **P1-20** (approved): `find(urgent=True)` with `reason_code=emergency_exam`, range `[now + min_lead_minutes_urgent, now + urgent_slot_max_hours]`, emergency blockouts open for urgent requests; `none_in_range` means URGENT callback.
  - **P2-08** (approved): `create_callback_request` needs a confirmed card, except in `EMERGENCY` for `tier1` / `crisis` / `uncertain` (DECISIONS #179).
  - **P1-03** (approved): `callback_requests` (`reason_code` incl. `URGENT_DENTAL`, `urgency` `ROUTINE` / `URGENT`, `summary_enc`, contact columns).

## 4. Scope
**In scope**
- `normalize()` and `EmergencyDetector` implementing P0-03 matching exactly, compiled per config version.
- `EmergencyPolicy` (final merge of rule and model signals, session stickiness); replaces P2-05's provisional `merge_emergency`.
- Turn-processor integration: rules before the LLM; Tier 1 / crisis from rules skip extraction for that turn.
- `EmergencyHandler` for all results, including the Tier 2 urgent-slot path (former P2-21).
- Immediate URGENT case creation and the minimal contact collection (name, phone with read-back) for emergency cases.
- Templates and script rendering hooks; audit, logs, metrics, prod alert.
- CI runner for the P0-03 test set (rules only) and a nightly run with the live model.

**Out of scope** (and which task covers it)
- Writing or changing rules and scripts → P0-03 (draft), P4-12 (editor), P5-15 (final approval)
- Case storage, admin email, case reference wording → P2-22
- Voice playback details (no barge-in over the Tier 1 script, TTS) → P3-03 / P3 voice tasks
- The 100+ scenario conversation eval suite → P5-02
- Console display of URGENT cases → P4-09

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P0-03 (approved) | Rules schema, example rules, test set | `backend/tests/fixtures/clinic_config/emergency_rules.example.yaml`, `evals/emergency/emergency_cases.yaml` |
| P1-19 (approved) | Pinned `emergency_rules` per session | Load the fixture through `ClinicConfigService` test double |
| P2-01 / P2-05 (approved) | Turn processor hook, extraction signal | Unit-test the policy with plain values; `FakeLlmProvider` for extraction |
| P1-20 (approved) | `find(urgent=True)` | `od_fake` with emergency blockouts |
| P2-12 / P2-15 / P2-16 (approved) | Identify, register, confirm and book with `urgent` | Reuse their handlers; tests with `od_fake` |
| P2-22 (not written) | `CallbackService.create_urgent()` and `update_contact()` | `FakeCallbackService` recording calls; the interface is defined in §6 |
| P2-08 (approved) | Gateway exceptions | Additive exception for Tier 2 (§6) |

## 6. Interface contract

### Normalization and matching (`backend/app/orchestrator/safety/detector.py`)
Implements P0-03 §6 exactly:
1. Lowercase; straight apostrophes; collapse whitespace.
2. Contractions: `can't`, `cant`, `can not` → `cannot`; `won't`, `wont` → `will not`; `don't`, `dont` → `do not`.
3. Remove punctuation except `.`, `?`, `!`, which split sentences.
4. **Phrase:** words appear consecutively on word boundaries within one sentence.
5. **Co-occurrence:** each group in `all_of_groups` has at least one term in the same sentence, any order.
6. **Negation:** a word from `negation_words` within `negation_window_words` words **before** the match in the same sentence → Tier 2 / 3 match ignored; Tier 1 / crisis match becomes `uncertain` (never ignored). Phrases that already contain a negation word are not negation-checked.
7. **Precedence:** `tier1` / `crisis` > `uncertain` > `tier2` > `tier3` > `none`; tier 1 and crisis together → both scripts, crisis first.

```python
RuleSignal = Literal["none", "tier3", "tier2", "uncertain", "tier1", "crisis"]

class RuleMatch(BaseModel):
    category_id: str                 # "t1_airway"
    tier: Literal["1", "2", "3", "crisis"]
    negated: bool

class RuleResult(BaseModel):
    signal: RuleSignal
    both_tier1_and_crisis: bool = False
    matches: tuple[RuleMatch, ...] = ()
    tier3_reason_code: str | None = None   # from the matched tier-3 category (P0-02 code)
    rules_version: str

class CompiledRules:
    @classmethod
    def compile(cls, rules: EmergencyRules) -> "CompiledRules": ...   # one regex per phrase / group term, word-bounded
    # cached per (clinic_id, config_version); LRU 64 entries

class EmergencyDetector:
    def detect(self, text: str, rules: CompiledRules) -> RuleResult: ...   # pure; p99 < 5 ms for 1000 chars
```
Example:
```python
detector.detect("No trouble breathing, but my face is swollen", rules)
# RuleResult(signal="uncertain", matches=(RuleMatch(category_id="t1_airway", tier="1", negated=True),
#            RuleMatch(category_id="t2_facial_swelling", tier="2", negated=False)), rules_version="0.2")

detector.detect("No, I can't breathe", rules)
# RuleResult(signal="tier1", ...)   # "cannot breathe" contains its own negation word, so it is not negation-checked (rule 6)
```

### Final policy (`safety/policy.py`, DECISIONS #201, #202)
```python
EmergencySignal = Literal["none", "tier3", "tier2", "uncertain", "tier1", "crisis"]
SEVERITY = {"none": 0, "tier3": 1, "tier2": 2, "uncertain": 3, "tier1": 4, "crisis": 4}

def decide(rule: RuleResult, model: EmergencySignal | None) -> tuple[EmergencySignal, Literal["rule", "model", "both"]]:
    """model is None when extraction was skipped or failed."""
    r = rule.signal
    if r in ("tier1", "crisis"):
        return r, "rule"                              # rules alone; extraction is skipped this turn
    if model in ("tier1", "crisis"):
        return "uncertain", "model"                   # model may raise any lower rule result, but only to "uncertain" (never the 911 script on its own)
    if model is not None and SEVERITY[model] > SEVERITY[r]:
        return model, "model"                         # e.g. rule none/tier3 + model tier2 → tier2; + model uncertain → uncertain
    if model is not None and model == r and r != "none":
        return r, "both"
    return r, "rule"
```
- The model can only raise, never lower (P0-03 rule 7, DECISIONS #172 kept).
- Extraction failure or LLM outage → `model=None`; the rule result alone stands. Rules never need the LLM.

### Session stickiness (`ConversationState.emergency`, additive to P2-01)
```python
class EmergencyRecord(BaseModel):
    highest: EmergencySignal = "none"        # most severe result already acted on this session
    case_ref: str | None = None              # URGENT case created for it (P2-22)
    contact_collected: bool = False
    tier2_stage: Literal["none", "offered", "identifying", "confirming", "booked", "callback"] = "none"
```
- An emergency event fires only when the new result is **more severe** than `highest` (tier 2 mentioned again during the urgent booking does not restart it; `uncertain` after tier 2 does fire; tier 1 always fires unless `highest` is already tier 1 / crisis).
- `tier3` never fires an event: it only pre-fills `reason_code` when the slot is empty.

### Turn-processor integration (P2-01 step 5, made precise)
1. `rule = detector.detect(turn.text, compiled)` on the raw text (typed text or final STT transcript). A tapped `choice_id` turn is also checked (its label text).
2. `rule.signal in (tier1, crisis)` and more severe than `highest` → fire `emergency_tier1` / `emergency_crisis` **immediately**; skip extraction for this turn (no LLM call, fastest reply).
3. Otherwise run extraction (P2-05) → `signal, source = decide(rule, extraction.emergency_signal)`.
4. `signal` more severe than `highest` → fire `emergency_uncertain` / `emergency_tier2` (global interrupts) before the state handler; `tier3` → pre-fill `reason_code`.
5. Write audit `safety.emergency_detected` and metrics for every non-`none` result (even when not fired).

### `EMERGENCY` handler (`flows/emergency.py`)

**Tier 1 and crisis (DECISIONS #202, user-approved answer 2):**
1. Reply the script (`tier1_911`; crisis → `crisis_988`; both → crisis then tier 1). Rendered from the pinned config; no LLM, no guardrail rewrite.
2. In the same turn, `CallbackService.create_urgent(reason="emergency_tier1" | "emergency_crisis", …)` with what the session knows (verified PatNum and Open Dental phone, or nothing). No confirmation card (P2-08 exception #179). `resume_state` cleared; `stop_booking` = true.
3. **Every later turn** in this session stays in `EMERGENCY`:
   - contact unknown → ask `emergency_name` then `emergency_phone`, read the phone back (P2-04 `read_back`), then `CallbackService.update_contact(case_ref, …)`; then `tier1_repeat`;
   - patient wants to book or says it was a misunderstanding → `tier1_booking_handoff` ("Our team has been told and will call you. They can help with the appointment too.") + `tier1_repeat`; the AI does **not** return to booking;
   - anything else → `tier1_repeat`.
4. Session ends normally (idle or the patient leaves). The widget keeps showing the script text.

**Uncertain:**
1. Reply `uncertain_urgent` (contains the 911 safety line).
2. `create_urgent(reason="emergency_uncertain")` immediately; contact unknown → collect name and phone (read-back) and update the case.
3. Then `resume` to `resume_state` (P0-03 `stop_booking: false`) with reply `emergency_resume` ("I've marked this as urgent for our team. Shall we continue?").

**Tier 2 (former P2-21; DECISIONS #202, answers 3 and 4):**
1. Reply `tier2_intro`; set `flags.urgent=true`, `reason_code=emergency_exam`.
2. **Before identification**, call `get_appointment_availability(reason_code="emergency_exam", urgent=true)` (no patient data in the result; P1-20 uses the routine/new-patient-neutral urgent variant).
3. Options → reply `tier2_earliest` ("The earliest urgent opening is {nearest}. Would you like it?") with choices: the earliest, up to 2 more, and "Please call me instead". `tier2_stage=offered`.
4. Patient picks a slot:
   - verified active patient → `CONFIRM` (book card) → `BOOK` (P2-16 handlers with `urgent=true`);
   - not verified → `IDENTIFY` (P2-12) / `REGISTER` (P2-15), keeping `urgent` and the chosen `slot_id`; after `verified` / `registered` → `CONFIRM`. `fresh_availability` re-checks the slot; if it was taken → fresh urgent search, earliest again.
5. **No slot** (`none_in_range`), patient chooses "Please call me instead", identification ends in a lock or `identity_needs_staff`, or `BOOK` ends in `outcome_unknown`:
   - contact known (verified: Open Dental phone) → `create_urgent(reason="emergency_tier2_no_slot")` at once, no card;
   - contact unknown → ask name and phone, read the phone back, then create;
   - then reply `tier2_no_slot` (its `{callback_phone}` is the read-back or Open Dental phone, masked as `(•••) •••-0123` in text).
6. Booked → P2-16 `booked` reply and card, followed by the script `tier2_safety_net` (no advice, only the safety sentence) ("If it gets worse, for example swelling spreading to your eye or neck, trouble breathing or swallowing, or bleeding that won't stop, call 911 or go to the nearest emergency room.") taken from config.
7. A patient asking for medication or home-care advice → `tier3_routine` (no advice), then continue.

**Tier 3:** no state change. If the patient asked for advice → `tier3_routine`; the matched category's `reason_code` pre-fills booking.

### Callback service interface used here (implemented by P2-22)
```python
class CallbackService(Protocol):
    async def create_urgent(self, *, session_id: uuid.UUID, reason: EmergencyCallbackReason,
                            pat_num: int | None, contact_name: str | None, contact_phone_e164: str | None,
                            situation: EmergencySituation) -> str: ...          # returns case_ref "CB-7Q2M"; idempotent per (session_id, reason)
    async def update_contact(self, case_ref: str, *, contact_name: str, contact_phone_e164: str) -> None: ...

EmergencyCallbackReason = Literal["emergency_tier1", "emergency_crisis", "emergency_uncertain", "emergency_tier2_no_slot"]

class EmergencySituation(BaseModel):          # becomes summary_enc (encrypted) — DECISIONS #202 answer 5
    tier: EmergencySignal
    category_labels: tuple[str, ...]          # from config, e.g. ("Facial swelling",)
    trigger_text: str                         # the patient's message that triggered it, ≤ 500 chars, PHI
    source: Literal["rule", "model", "both"]
```
- All four reasons map to P1-03 `reason_code=URGENT_DENTAL`, `urgency=URGENT` (P2-22 owns the mapping).
- Idempotency key `callback:{session_id}:{reason}` (P2-08 registry form), so a retry never creates a second case.
- The admin email follows P0-08 (`link_only` by default: no situation text in email).

### Additive changes to approved specs (DECISIONS #203)
- **P2-08:** the confirmation exception for `create_callback_request` in `EMERGENCY` also covers reason `emergency_tier2_no_slot`; the phone read-back replaces the card.
- **P1-03:** `contact_name_enc`, `contact_phone_enc`, `contact_phone_bidx` become NULLable, with a check constraint: NULL allowed only when `urgency = 'URGENT'` and `reason_code = 'URGENT_DENTAL'` (an emergency case created before contact details are known).
- **P2-05:** `merge_emergency` is replaced by P2-20's `decide()`; the extraction field is unchanged.
- **P2-01:** `ConversationState.emergency: EmergencyRecord`; step 5 skips extraction on rule Tier 1 / crisis.
- **P1-07:** audit action `safety.emergency_detected`.

### Templates (added to P2-04; scripts come from config)
| Intent | Source / text |
|---|---|
| `emergency_tier1`, `crisis`, `tier1_repeat`, `uncertain_urgent`, `tier2_intro`, `tier2_no_slot`, `tier3_routine`, `tier2_safety_net` | `{script: <id>}` from the pinned `emergency_rules.scripts` |
| `tier1_booking_handoff` | "Our team has been told and will call you. They can help with the appointment too." |
| `tier2_earliest` | "The earliest urgent opening is {nearest}. Would you like it?" (choices) |
| `emergency_name` | "So our team can reach you, what's your first and last name?" |
| `emergency_phone` | "And the best phone number to reach you?" |
| `emergency_resume` | "I've marked this as urgent for our team. Shall we continue?" |

`tier2_safety_net` is a new script id for P0-03's file (text taken from the existing `tier2_no_slot` safety sentence; the dentist reviews it with the rest).

### Audit, logs, metrics, alert (no PHI)
| Item | Fields |
|---|---|
| Audit `safety.emergency_detected` | object session / session_id; details `signal`, `source`, `category_ids`, `rules_version`, `fired` (bool) |
| Log `emergency.detected` (info) | `signal`, `source`, `category_ids`, `negated_count`, `rules_version`, `fired` |
| `dai.emergency.detected` (counter) | `signal`, `source`, `channel` |
| `dai.emergency.detect_ms` (histogram) | - |
| `dai.emergency.tier2_outcome` (counter) | `result` (`booked` / `callback` / `abandoned`) |
| Prod alert **A-EM1** (page) | `create_urgent` failed after retries for an emergency (P1-07 alerting): the script was still shown; on-call checks the case queue |

Never logged: the patient's text, matched phrases, names, phones.

## 7. Implementation guide
1. **Detector.** `normalize`, `CompiledRules.compile`, `detect`. Table tests from P0-03's examples first, then the whole test set. Benchmark p99.
2. **Test-set runner.** `backend/tests/evals/test_emergency_rules.py` loads `evals/emergency/emergency_cases.yaml` and asserts the P0-03 pass criteria: 100% Tier 1 / crisis, 0 under-triage, ≥ 95% exact. Fails CI otherwise.
3. **Policy.** `decide()` and stickiness; table tests over every (rule, model) pair (6 × 7).
4. **Turn processor.** Hook steps 1–5 of §6; the extraction skip on rule Tier 1 / crisis; P2-05 calls `decide()`.
5. **Handler.** Tier 1 / crisis / uncertain / tier 2 / tier 3 paths; reuse P2-12, P2-15 and P2-16 handlers with `urgent=true`.
6. **Callback integration.** `FakeCallbackService` until P2-22; P1-03 migration for nullable contact columns (with P2-22's owner).
7. **Templates.** Script references; load-time check that every script id used exists in the pinned rules (P2-04 check).
8. **Audit, metrics, alert A-EM1.**
9. **Nightly live-model run** `scripts/evals/emergency_live.py` (staging, synthetic text only): the same test set through rules + real extraction; report raises by the model and any under-triage.
10. **Docs.** `docs/flows/emergency.md` (Mermaid) and `docs/safety/emergency-detector.md` (how to add a category; why the model only raises). Notify P2-22 (interface), P3 voice (no barge-in over Tier 1 script), P4-12, P5-02, P5-15.

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| "No, I can't breathe" | `tier1` (the phrase contains its own negation, so no negation check) |
| "No trouble breathing, just a swollen cheek" | Tier 1 match negated → `uncertain`; never silenced |
| "No swelling, just sensitive" | Tier 2 ignored by negation; `tier3` sensitivity |
| Tier 1 phrase mid-booking during `BOOK` | Fired after the running tool call returns (P2-01); booking stops; if the booking succeeded it stays booked and the script still plays |
| Symptoms about a child or parent | Same rules and scripts |
| Rule `tier2`, model says `tier1` | `uncertain` (safety script + URGENT case), then continue Tier 2 |
| Rule `none`, model says `tier2` | `tier2` path |
| LLM down | Rules still work; scripts and case creation need no LLM |
| Patient says "it was a joke, just book me" after Tier 1 | `tier1_booking_handoff` + `tier1_repeat`; no booking |
| Tier 2 repeated ("still hurts") during urgent booking | No re-fire (stickiness) |
| Tier 2 then Tier 1 phrase | Tier 1 fires; Tier 2 booking stops |
| Tier 2, unverified, patient picks a slot, identity fails 3 times | Lock → URGENT case (reason `emergency_tier2_no_slot`) with collected contact, no card |
| Tier 2, slot taken while identifying | Fresh urgent search; earliest offered again |
| Tier 2 after hours, no urgent slot within 24 h | `tier2_no_slot` + URGENT case (after-hours mailbox per P0-08) |
| `create_urgent` fails (DB down) | Script still shown; retry 3 times with backoff inside the turn budget; then alert A-EM1; the patient is not told the case exists unless created |
| Patient refuses to give a phone after Tier 1 | Case stays without contact; `tier1_repeat`; staff see an URGENT case with the session's details |
| Very long message (1000 chars) with an emergency phrase at the end | Detected (whole text scanned) |
| Emergency phrase inside a tapped choice label | Checked like text (labels are ours, so this is defensive only) |
| Prod config with `clinic_reviewed` rules | Not activatable (P1-19); the session never starts with unapproved rules in prod |
| Voice transcript with STT error ("can't bree") | Not matched by rules; the model may raise to `uncertain`; P5-02 evals track voice cases |

## 9. Security, HIPAA and PHI
- **PHI handled:** the patient's message (symptoms = health information), name and phone collected for the case, the case situation. 
- **Where it goes:** the trigger text and category labels go into `callback_requests.summary_enc` (encrypted, P1-05); name and phone into the encrypted contact columns. Detection runs in-process; only the normal extraction call sends text to Vertex AI (covered by the Google Cloud BAA).
- **Never logged:** the text, matched phrases, names, phones. Logs and audit carry only signal, source, category IDs and rules version.
- **Admin email:** `link_only` by default (P0-08); no symptoms in email unless the clinic approved `full_details`.
- **Safety controls:** rules first, model only raises, scripts from clinic-reviewed config, no advice (P0-03 advice-words check), Tier 1 never resumes booking.

## 10. Testing
```bash
cd backend && pytest tests/unit/orchestrator/safety -q
pytest tests/evals/test_emergency_rules.py -q                 # P0-03 test set, rules only (CI gate)
pytest tests/integration/emergency -q                          # od_fake + FakeCallbackService
python scripts/evals/emergency_live.py --env staging           # nightly, live model, synthetic text
```
| # | Case | Expected |
|---|---|---|
| T1 | Normalization table (contractions, punctuation, sentences) | As P0-03 |
| T2 | Phrase, co-occurrence, negation, precedence examples | As P0-03 |
| T3 | Full P0-03 test set, rules only | 100% Tier 1 / crisis, 0 under-triage, ≥ 95% exact |
| T4 | `decide()` over all rule × model pairs | Never lower than rule; model tier1/crisis → `uncertain` |
| T5 | Rule Tier 1 | No LLM call that turn (`FakeLlmProvider.calls` unchanged); script reply; `create_urgent` called once without a card |
| T6 | Tier 1 then "just book me" | `tier1_booking_handoff`; no booking tool allowed |
| T7 | Tier 1 contact collection | Name, phone, read-back, `update_contact` |
| T8 | Uncertain mid-booking | Script, case, then resume to the saved state |
| T9 | Tier 2 verified, slot available | Earliest offered before anything else; booked with `urgent=true`; safety-net sentence |
| T10 | Tier 2 unverified | Earliest shown → identify → confirm → booked |
| T11 | Tier 2 no slot | URGENT case without a card (phone read-back when unknown); `tier2_no_slot` |
| T12 | Stickiness | Tier 2 repeated → no re-fire; Tier 1 after Tier 2 → fires |
| T13 | Emergency from every non-terminal state | Correct event and state (P2-01 T7 extended) |
| T14 | LLM unavailable | Rules path still works |
| T15 | Script rendering | Exact config text; unknown script id fails at load |
| T16 | `create_urgent` failure | Script shown; retries; alert A-EM1 |
| T17 | Detector performance | p99 < 5 ms for 1000-char input |
| T18 | Log capture with PHI corpus | No text, phrases, names or phones in logs or audit |
| T19 | Nightly live model | Report: model raises listed; any under-triage fails the run |

## 11. Acceptance criteria
- [ ] Tier 1 and crisis test phrases get the 911 / 988 script 100% of the time; 0 under-triage and ≥ 95% exact on the P0-03 test set (T3)
- [ ] Rules come from the clinic config (prod only `approved`); a rule change needs no code change (T3, T15)
- [ ] Scripts come from config, never from the LLM (T5, T15)
- [ ] The model signal can only raise the result, and alone never triggers the 911 script (T4)
- [ ] Tier 1 / crisis create an URGENT case immediately without a card and never resume booking (T5, T6)
- [ ] Tier 2 offers the earliest urgent slot first; no slot or no booking → URGENT case (T9–T11)
- [ ] Emergencies interrupt every non-terminal state (T13) and work with the LLM down (T14)
- [ ] No PHI in logs or audit (T18)

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI; the test-set runner is a required CI check
- [ ] PR reviewed (HIPAA review: labelled `phi`) and by the clinical safety reviewer for template wording
- [ ] No PHI in logs
- [ ] `docs/flows/emergency.md` and `docs/safety/emergency-detector.md` written; additive changes to P1-03, P1-07, P2-01, P2-05, P2-08 merged
- [ ] P2-22, P3 voice, P4-12, P5-02 and P5-15 issues notified

## 13. Hand-off
| Consumer | What they can rely on |
|---|---|
| P2-22 Callback | `create_urgent` / `update_contact` interface, reasons, `EmergencySituation`, idempotency per (session, reason), nullable contact for URGENT cases |
| P3 voice | Emergency events and script replies arrive like other replies; the Tier 1 script must play in full (no barge-in) |
| P4-12 Rules editor | Detector compiles any valid rules file; new categories need no code |
| P5-02 Scenario evals | Test-set runner and the live nightly runner to extend |
| P5-15 Clinic sign-off | Test-set results per `rules_version` for the approval record |

## 14. Open questions
| # | Question | Recommended answer | Owner |
|---|---|---|---|
| 1 | Should `tier2_safety_net` be a separate script the dentist reviews? | Yes; add it to P0-03's file before staging. | Dentist + tech lead |
| 2 | Should staff get a different email subject for Tier 1 vs Tier 2 URGENT cases? | Yes, "URGENT (911 advised)" vs "URGENT" with the case ID only; P2-22 decides the format. | Product owner |
| 3 | Should voice transcripts be checked on partial (interim) STT results too? | Not in P2; P3 decides after measuring false alarms. Final transcripts are always checked. | Tech lead |

## 15. References
- Plan: §1 principle 4, §4.3, §4.8, §4.9, §11, §12
- P0-03 matching rules, scripts, test set; P0-01 Q4a
- DECISIONS: #14, #15, #16, #17, #142, #148, #162, #172, #179, #201, #202, #203
- Related tasks: P0-03, P0-04, P1-03, P1-07, P1-19, P1-20, P2-01, P2-03, P2-04, P2-05, P2-08, P2-12, P2-15, P2-16, P2-22, P3-03, P4-12, P5-02, P5-15
