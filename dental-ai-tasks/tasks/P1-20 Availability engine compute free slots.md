---
id: P1-20
title: Availability engine (real slots, clinic rules, 2–3 options) and safe booking sequence (slot lock, re-check, create, verify)
milestone: P1
epic: E1.4
size: L
labels: area:scheduling, area:backend, type:feature, phi
depends_on: P0-02, P0-03, P1-07, P1-15, P1-16, P1-19
status: approved
---

# P1-20: Availability engine (real slots, clinic rules, 2–3 options) and safe booking sequence (slot lock, re-check, create, verify)

## 1. Summary
Build the scheduling core. This task also absorbs **P1-21 (slot lock + booking sequence)**.

1. **Availability:**
   - Turn "this patient needs this kind of visit" into **2–3 real, bookable options**.
   - The base is Open Dental's own open-slot calculation (`GET /appointments/Slots`, one call per eligible provider).
   - A **pure, fully unit-tested rules function** then applies our clinic rules:
     - AI booking window and holidays;
     - lead times: 2 h routine, 30 min urgent (DECISIONS #142);
     - booking horizon (DECISIONS #86);
     - blockouts: reserved new-patient and emergency blockouts, and every other blockout closed;
     - appointment length from Open Dental;
     - eligible providers and operatories from the P0-02 mapping;
     - patient preferences and spreading of options.
   - Everything is computed in clinic local time and is DST-safe.
2. **Booking sequence** (plan §4.6):
   1. take a short Redis lock on the slot (operatory-day and provider-day);
   2. **re-check with Open Dental** (Slots for that day, plus fresh blockouts);
   3. create through P1-16 with an idempotency key;
   4. verify by reading back (P1-16 does this);
   5. always release the lock;
   6. return a typed outcome. On conflict the outcome includes fresh alternatives.

   Reschedule uses the same sequence with P1-16's in-place move.

Done means:
- no returned option overlaps an existing appointment, a closed blockout, a holiday or the outside of the AI window;
- a 20-way concurrent booking test on one slot produces **exactly one** booking;
- DST, holiday and out-of-hours cases are covered by unit tests;
- the whole flow runs against `od_fake` in CI.

## 2. Why this matters
- **"Offer only real slots"** is a core requirement (plan §1, §4.6), and **0 double bookings** is a pilot target (§11).
- The availability answer is what patients hear in the `AVAILABILITY` state (P0-04): it must be correct and fast enough for voice, with filler speech covering the 1–3 s Open Dental needs.
- The booking sequence is the only place where an AI conversation turns into a real appointment.

P2-16 (book), P2-18 (reschedule), P2-20 (Tier 2 urgent slot) and the `get_appointment_availability`, `book_appointment` and `reschedule_appointment` tools (P2-08) all call this task. P5-04 (which absorbed P5-05) later adds race, DST and holiday edge-case tests on top (DECISIONS #284 corrects the earlier "P5-03").

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P1, Core Platform & Open Dental Adapter**.
- **What already exists:**
  - **P1-15:**
    - `OpenDentalSetup`: `providers`, `operatories`, `appointment_types` (with `pattern`), `schedules` (cached 10 min, `ScheduleBlock` with `sched_type`, `blockout_def_num`, `op_nums`), `open_slots(ctx, start, end, prov_num, op_num, length_minutes)` (live, never cached), `blockout_types` (added by P1-19);
    - `Priority`, the pacer (≈ 1 request/s per clinic), typed errors.
  - **P1-16:**
    - `OpenDentalAppointments.create` / `reschedule` / `list_for_patient` / `list_for_operatory_day`;
    - `WriteResult`, `WriteOutcomeUnknown`, `IdempotencyInProgress`;
    - key format `book:<session_id>:<slot_hash>`.
  - **P1-19:** `ClinicConfigService.for_session()` (pinned version), with:
    - `hours` (AI booking window), `holidays`;
    - `scheduling.booking_horizon_days`, `min_lead_minutes` (120), `min_lead_minutes_urgent` (30), `options_per_offer`, `reserved_blockouts.{new_patient, emergency}`, `other_blockouts_block_booking`;
    - `appointment_types` (P0-02 mapping) and `od_check.disabled_variants`.
  - **P0-02:** each reason code has ordered variants (`patient_types`, `age_min`/`age_max`, `appointment_type.od_appointment_type_num`, `providers`, `operatory_nums` where empty means any) and `when_not_bookable`. The first matching variant wins. `od_time_increment_min` sets the time grid. Open Dental's appointment length wins over `duration_min` (DECISIONS #10).
  - **P0-03:** Tier 2 searches `emergency_exam` slots starting within `urgent_slot_max_hours` (default 24); no slot means an URGENT callback.
  - **P1-07:** `stage_timer`, `record_counter("dai.booking.outcome", …)`.
- **Open Dental facts** (docs read 2026-11-24; https://www.opendental.com/site/apiappointments.html, https://www.opendental.com/site/apischedules.html):
  - **`GET /appointments/Slots` (21.1):**
    - "looks at open schedule times, whether the schedules are attached to a provider or an operatory";
    - "returns entire open slots"; `lengthMinutes` "Ignores slots that are shorter than the supplied number of minutes";
    - `ProvNum` defaults to the practice default provider; `OpNum` is available from 22.1;
    - when a provider has appointments in several operatories, it "only returns slots that are available in all operatories for that provider simultaneously";
    - `date` must be today or later, and defaults to the next 14 days;
    - response items: `DateTimeStart`, `DateTimeEnd`, `ProvNum`, `OpNum` (local `yyyy-MM-dd HH:mm:ss`).
    - **Blockouts, holidays and a maximum range are not mentioned.** We therefore apply blockouts and holidays ourselves, and query in chunks of at most 14 days.
  - **`GET /schedules` blockout rows:** `SchedType: "Blockout"`, `BlockoutType` = definition DefNum (category 25), `operatories` = comma-separated operatory numbers, `ProvNum` = 0. **Verify** whether an empty `operatories` means "all operatories".
  - **`SlotsWebSched`** needs a paid Web Sched setup and pairs with a different create endpoint. Not used.
- **Pattern:** an appointment's length is its `Pattern` string, one character per 5 minutes (`X` = provider time, `/` = assistant time). The length in minutes is `len(pattern) * 5`.

## 4. Scope
**In scope**
- **Package `backend/app/domain/scheduling/`:**
  - `models.py`;
  - `rules.py` (pure engine);
  - `variants.py` (reason → variant selection);
  - `availability.py` (`AvailabilityService`: fetch + engine + offer store);
  - `locks.py` (`SlotLock`);
  - `booking.py` (`BookingService`: book and move).
- **Offer store:** the options shown to a patient are saved in Redis per session, so booking can only use a slot this session was actually offered (P0-04 guard `fresh_availability`).
- **Metrics and events:**
  - `dai.booking.outcome` with an `outcome` label;
  - a new histogram `dai.availability.duration_ms`;
  - `stage_timer(Stage.TOOL_CALL, tool="availability")`.
- **`od_fake` update:** `/appointments/Slots` computed from the fake's schedules and **current** appointments (so bookings change the answer), with a fault for "slot taken between offer and booking".
- **Tests:** engine unit tests (DST, holidays, windows, blockouts, grid, spreading), service tests against `od_fake`, the concurrency test.
- **Docs:** `docs/scheduling.md` covering the rules order, the booking sequence diagram and outcomes.

**Out of scope** (and which task covers it)
- Cancellation, and the notice-window rules for cancel and reschedule → P2-18 (uses P1-16 and P1-19 `policies`)
- Conversation wording, filler speech, reading options aloud → P2-16, P3
- Deciding Tier 2 → P2-20 (calls `find(urgent=True)`)
- Tool JSON schemas and audit → P2-08
- Extra edge-case tests → P5-04; load tests → P5-03 (DECISIONS #284)

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P1-15 (approved) | `OpenDentalSetup.open_slots`, `schedules`, `appointment_types` | `od_fake`; the engine itself needs no Open Dental at all (pure function on plain inputs) |
| P1-16 (approved) | `create`, `reschedule`, `list_for_operatory_day`, `list_for_patient`, `WriteResult`, errors | Use the signatures; fake the adapter in unit tests |
| P1-19 (approved) | Pinned `ActiveConfig` | Load `seed/example-dental/` directly into `ClinicConfig` in tests |
| P0-02, P0-03 (approved) | Mapping fixture, `urgent_slot_max_hours` | Fixtures under `backend/tests/fixtures/clinic_config/` |
| P1-07 (approved) | Metrics, timers | Spec signatures |

## 6. Interface contract

### Models (`models.py`)
```python
class PartOfDay(StrEnum):
    MORNING = "morning"       # start < 12:00 local
    AFTERNOON = "afternoon"   # 12:00 ≤ start < 17:00
    EVENING = "evening"       # start ≥ 17:00

class Preferences(BaseModel):
    earliest_date: date | None = None          # clinic local dates
    latest_date: date | None = None
    weekdays: set[int] | None = None           # 0 = Monday
    parts_of_day: set[PartOfDay] | None = None
    prov_num: int | None = None                # "with Dr. Lee"; only if eligible for the variant

class AvailabilityRequest(BaseModel):
    reason_code: str                           # P0-02 code, e.g. "recall_cleaning"
    patient_type: Literal["new", "existing"]
    age_years: int | None = None               # computed by the caller from DOB; never stored
    urgent: bool = False                       # Tier 2 path (P2-20)
    preferences: Preferences = Preferences()
    cursor: str | None = None                  # from a previous result: "something later"
    exclude_slot_ids: set[str] = set()
    anchor_local: datetime | None = None       # "nearest after" mode (DECISIONS #195): options start at or after this
                                               # clinic-local time, ordered earliest first, no spreading; other
                                               # preferences except prov_num are ignored in this mode

class SlotOption(BaseModel):
    slot_id: str                               # random 10 chars, valid only in this session's offer store
    start_utc: datetime
    end_utc: datetime
    local_label: str                           # "Tue Dec 8, 9:00 AM" in clinic tz (for the LLM to read)
    prov_num: int
    provider_display: str                      # "Dr. Lee" from P1-15 Provider (preferred/abbr), no PHI
    op_num: int
    appointment_type_num: int | None
    pattern: str
    reserved: Literal["none", "new_patient", "emergency"]

class AvailabilityResult(BaseModel):
    status: Literal["options", "none_in_range", "not_bookable"]
    reason_code: Literal["preference_too_narrow", "provider_not_eligible", "no_capacity"] | None = None   # for none_in_range
    options: list[SlotOption]                  # 0–3
    when_not_bookable: Literal["callback", "not_offered"] | None = None
    next_cursor: str | None                    # None = nothing later within the horizon
    config_version: int
    searched_until_utc: datetime
```

### Pure engine (`rules.py`, no I/O, no clock)
```python
@dataclass(frozen=True)
class EngineInputs:
    tz: ZoneInfo
    now_utc: datetime
    od_slots: Sequence[Slot]                   # from P1-15 (start_utc, end_utc, prov_num, op_num)
    blockouts: Sequence[ScheduleBlock]         # sched_type == "Blockout" for the range
    hours: WeeklyHours
    holidays: Sequence[Holiday]
    scheduling: SchedulingPolicy
    variant: Variant                           # resolved by variants.py
    length_minutes: int                        # len(Open Dental pattern) * 5
    grid_minutes: int                          # P0-02 od_time_increment_min
    urgent_max_hours: int                      # P0-03 urgent_slot_max_hours

def candidate_starts(inp: EngineInputs, req: AvailabilityRequest) -> list[Candidate]: ...
def pick_options(cands: list[Candidate], req: AvailabilityRequest, n: int) -> tuple[list[Candidate], str | None]: ...
def slot_still_valid(inp: EngineInputs, req: AvailabilityRequest, cand: Candidate) -> bool: ...   # used at booking
```
**Rules, applied in this order** (each a small, separately tested function):
1. **Search range:**
   - Routine: `[now + min_lead_minutes, end of local day (today + booking_horizon_days)]`.
   - Urgent: `[now + min_lead_minutes_urgent, now + urgent_max_hours]` (never beyond the horizon).
   - `Preferences.earliest_date` / `latest_date` narrow the range.
2. **Holidays:** drop closed holiday dates. A holiday with `hours` replaces that day's AI window.
3. **AI window:** intersect each Open Dental open interval with the day's `hours` ranges in local time. Days with no ranges are dropped.
4. **Blockouts:** for each blockout covering the interval's operatory (empty `op_nums` = all operatories until **Verify** says otherwise):
   - DefNum in `reserved_blockouts.new_patient` → open only when `patient_type == "new"`, else subtract;
   - DefNum in `reserved_blockouts.emergency` → open only when `urgent`, else subtract;
   - any other blockout → subtract when `other_blockouts_block_booking` (default true).
5. **Variant fit:**
   - provider in `variant.providers`;
   - operatory in `variant.operatory_nums` (empty = any operatory where the provider has a slot);
   - operatory not hidden.
6. **Grid:**
   - starts on the `grid_minutes` grid, measured from local midnight;
   - `start + length ≤ interval end`;
   - built from local wall-clock times and converted with `zoneinfo`. Non-existent local times (spring-forward) are skipped. Ambiguous times use the first occurrence (same as P1-15).
7. **Preferences:** weekdays, parts of day, provider. If a preference empties the list, the result is `none_in_range`, and the caller asks whether to relax it. The engine never relaxes it silently.
8. **De-duplicate** the same start time across operatories (keep the lowest `op_num` for the preferred provider, else the first provider in variant order).
9. **Spread** (`pick_options`):
   - take the earliest;
   - then the earliest in a **different local half-day** (date + morning/afternoon-evening);
   - then again a new half-day;
   - if there aren't enough half-days, fill with the earliest remaining options at least 60 min apart.

   `next_cursor` encodes the last offered start and the excluded IDs (base64 JSON, no PHI). "Something later" continues strictly after it.

### Variant selection (`variants.py`)
```python
def select_variant(mapping: AppointmentTypeMapping, disabled: frozenset[tuple[str, int]],
                   reason_code: str, patient_type: str, age_years: int | None) -> Variant | NotBookable: ...
```
- **Rule:** first variant (in file order) whose `patient_types` contains `patient_type`, whose age range contains `age_years`, and which is not disabled.
- **Age unknown:** if `age_years` is None and a variant has age limits, it is skipped.
- **No match**, `bookable_by_ai: false` or all variants disabled → `NotBookable(when_not_bookable)`.
- **Urgent:** an urgent request always uses reason `emergency_exam` (P0-03 `tier_actions.tier2.reason_code`).

### Availability service (`availability.py`)
```python
class AvailabilityService:
    async def find(self, ctx: ClinicODContext, session_id: uuid.UUID, req: AvailabilityRequest) -> AvailabilityResult: ...
    # Addition (P4-11, DECISIONS #264): preview_counts(ctx, *, current, proposed, reason_codes, window_days=7)
    # -> list[PreviewItem]; same slot computation as find() for a candidate config, counts only,
    # never writes offers or locks. Full contract in P4-11 §6.7.
    async def get_offered(self, session_id: uuid.UUID, slot_id: str) -> OfferedSlot | None: ...
```
1. **Config:** `cfg = config.for_session(session_id)` (pinned version), then `select_variant`.
2. **Length:** from the Open Dental appointment type's `pattern` (P1-15 cache). If there is no `od_appointment_type_num`, use `duration_min` rounded up to 5 minutes and a pattern of `X` × n.
3. **Fetch, progressively:**
   - Window 1 = the first `AVAILABILITY_FIRST_WINDOW_DAYS` (3) days of the range. Window 2 = the rest of the range, in chunks of ≤ 14 days.
   - For each window and each eligible provider (preferred provider first), call `open_slots(ctx, start, end, prov_num=…, op_num=None, length_minutes=length)` with interactive priority.
   - Blockouts come from `schedules(ctx, start, end, sched_type="Blockout")` (cached 10 min).
   - Stop as soon as `pick_options` returns `options_per_offer` options.
4. **Time budget:** the whole call must finish within `AVAILABILITY_BUDGET_S` (8 s, `asyncio.timeout`).
   - If time runs out with ≥ 1 option, return them.
   - With 0 options, raise `AvailabilityUnavailable` (→ callback in P2).
   - Open Dental errors pass through as P1-15 types.
5. **Offer store:** Redis hash `avail:{session_id}` (TTL `OFFER_TTL_S` = 900 s), field `slot_id`, holding the JSON of the option plus `config_version`, `reason_code`, `patient_type` and `urgent`. Each `find` adds new options and keeps the earlier ones until the TTL. The value contains times, provider and operatory numbers, and no names or contact details.

### Slot lock (`locks.py`)
```python
class SlotLock:
    async def acquire(self, clinic_id: uuid.UUID, keys: Sequence[str], *, ttl_ms: int, wait_s: float) -> LockToken: ...
    async def release(self, token: LockToken) -> None: ...   # Lua compare-and-delete per key
```
- **Lock keys:**
  - `slotlock:{clinic_id}:op:{op_num}:{local_date}`;
  - `slotlock:{clinic_id}:prov:{prov_num}:{local_date}`.

  They are acquired in sorted order (no deadlocks) with `SET key token NX PX ttl`. The day-level grain means two of our bookings for the same operatory or provider on the same day run one after another. This is cheap, because Open Dental is paced at about 1 request/s anyway.
- **Settings:** `SLOT_LOCK_TTL_MS` = 60000 (longer than the worst case: a pacer wait of 10 s plus a 15 s read plus a 15 s write). `SLOT_LOCK_WAIT_S` = 8, polling every 200 ms with jitter. If the lock can't be had in time, the outcome is `slot_busy`.
- **Release** always happens in `finally`. A crashed instance's lock expires at the TTL.

### Booking service (`booking.py`)
```python
class BookingOutcome(BaseModel):
    status: Literal["booked", "slot_taken", "slot_busy", "patient_conflict", "offer_expired",
                    "in_progress", "outcome_unknown", "unavailable"]
    apt_num: int | None = None
    start_utc: datetime | None = None
    local_label: str | None = None
    alternatives: list[SlotOption] = []        # filled for slot_taken / slot_busy
    replayed: bool = False

class BookingService:
    async def book(self, ctx: ClinicODContext, session_id: uuid.UUID, *, pat_num: int, slot_id: str,
                   is_new_patient: bool) -> BookingOutcome: ...
    async def move(self, ctx: ClinicODContext, session_id: uuid.UUID, *, pat_num: int, apt_num: int,
                   slot_id: str) -> BookingOutcome: ...
```
**Sequence for `book`:**
1. `offered = get_offered(session_id, slot_id)`. If it's missing or expired → `offer_expired` (the caller runs `find` again). It must belong to this clinic and the session's pinned `config_version`.
2. **Lock** (keys above).
3. **Re-check** (inside the lock):
   1. `open_slots(ctx, day, day, prov_num, op_num=op if version ≥ 22.1 else None, length_minutes=length)` must contain `[start, end)` for that operatory.
   2. **Fresh** blockouts for that day: `schedules(…, sched_type="Blockout")` with the cache bypassed (new `refresh=True` flag on P1-15 `schedules`).
   3. `slot_still_valid` (lead time, holiday, window and blockouts against the current time).
   4. If the Open Dental version is < 22.1: also `list_for_operatory_day` with no overlap allowed.
   5. `list_for_patient(pat_num, day, day)`: the patient has no `Scheduled` appointment overlapping `[start, end)`, else `patient_conflict`.

   Any failure → `slot_taken`, with up to 3 `alternatives` from a fresh `find` (same request, this slot excluded). The fresh `find` runs **after** the lock is released.
4. **Create:** `appointments.create(ctx, NewAppointment(...), idempotency_key=f"book:{session_id}:{slot_hash}", session_id=…)`. `slot_hash` = first 16 hex chars of SHA-256(`prov|op|start_utc|pattern`).
5. **Results:**
   - `WriteResult` → `booked` (with `replayed` if so);
   - `IdempotencyInProgress` → `in_progress`;
   - `WriteOutcomeUnknown` / `WriteVerificationFailed` → `outcome_unknown`;
   - `OpenDentalUnavailable` / `RateLimited` / `Timeout` / `QueueTimeout` → `unavailable`.
6. **Release** the lock (`finally`). Remove the slot from the offer store when booked.
7. **Metrics:** `record_counter("dai.booking.outcome", outcome=status, urgent=…)`; event `scheduling.booking` with `clinic_id`, `status`, `duration_ms`, `lock_wait_ms`.

**Sequence for `move` (reschedule):**
- Same steps 1–3. In the re-check, the patient's own appointment `apt_num` is ignored in the `patient_conflict` and operatory-overlap checks.
- Step 4 is `appointments.reschedule(ctx, apt_num, pat_num=…, move=AppointmentMove(...), idempotency_key=f"reschedule:{session_id}:{apt_num}:{slot_hash}")`.
- **Known limit:** Open Dental Slots treats the patient's current appointment as busy, so a new time overlapping the old one in the same operatory isn't offered. This is acceptable (the patient is asking for a different time).

### Settings (extends P1-01)
```python
AVAILABILITY_BUDGET_S: float = 8.0
AVAILABILITY_FIRST_WINDOW_DAYS: int = Field(default=3, ge=1, le=14)
OD_SLOTS_CHUNK_DAYS: int = Field(default=14, ge=1, le=14)
OFFER_TTL_S: int = 900
SLOT_LOCK_TTL_MS: int = 60000
SLOT_LOCK_WAIT_S: float = 8.0
```

### Example
```python
await availability.find(ctx, sid, AvailabilityRequest(reason_code="recall_cleaning", patient_type="existing",
                         age_years=41, preferences=Preferences(parts_of_day={PartOfDay.MORNING})))
# -> AvailabilityResult(status="options", options=[
#      SlotOption(slot_id="k3H9xQ2mPa", start_utc=2026-12-08T14:00Z, local_label="Tue Dec 8, 9:00 AM", prov_num=4, ...),
#      SlotOption(slot_id="Zp81LwQe0c", start_utc=2026-12-09T15:30Z, local_label="Wed Dec 9, 10:30 AM", ...),
#      SlotOption(slot_id="Ma77TtV2rb", start_utc=2026-12-10T14:00Z, local_label="Thu Dec 10, 9:00 AM", ...)],
#    next_cursor="eyJhZnRlciI6…", config_version=4, ...)
await booking.book(ctx, sid, pat_num=48, slot_id="k3H9xQ2mPa", is_new_patient=False)
# -> BookingOutcome(status="booked", apt_num=7713, local_label="Tue Dec 8, 9:00 AM")
```

## 7. Implementation guide
1. **Read** P0-02, P0-03, P0-04 (the `AVAILABILITY`/`CONFIRM`/`BOOK` states and the `fresh_availability` guard), P1-15, P1-16, P1-19 §6, and DECISIONS #10, #86, #126, #138, #142. **Verify** on test DB (B), and record the results in `docs/scheduling.md` and DECISIONS.md:
   - whether Slots excludes blockouts;
   - whether Slots honours Open Dental Practice-schedule closed days;
   - whether an empty blockout `operatories` means all operatories;
   - the longest `dateStart`–`dateEnd` range Slots accepts;
   - whether `DateTimeEnd` is exclusive.
2. **Engine first** (`rules.py`, `variants.py`): pure functions with table-driven tests T1–T12. This can be done in parallel with everything else.
3. **`od_fake` Slots:** compute open intervals per provider and operatory from the fake's provider schedules minus current appointments (not minus blockouts, matching the assumption until step 1 says otherwise). Add the fault `slot_taken_after_offer` (the fake inserts a staff appointment at that time).
4. **`AvailabilityService`:** progressive windows, time budget, offer store (T13–T16).
5. **`SlotLock`** with real Redis: ordering, TTL, release-only-own (T17, T18).
6. **`BookingService.book` and `move`:** re-check, outcomes, alternatives, metrics (T19–T23).
7. **Concurrency test** T24: 20 sessions with 20 asyncio tasks across 2 processes book the same slot.
8. **Add `refresh=True`** to P1-15's `OpenDentalSetup.schedules` (bypasses and refills the cache): a small extension, documented in P1-15's doc page.
9. **Docs and notify:**
   - P2-08: tool inputs and outputs map 1:1 to `AvailabilityRequest`/`Result` and `BookingOutcome`;
   - P2-16, P2-18, P2-20: outcomes and when to call `find` again;
   - P2-01: the offer store key and the `fresh_availability` guard;
   - P5-04: concurrency and DST suites to extend (DECISIONS #284);
   - P6-01: lead times and reserved blockouts to set at onboarding.

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| Two patients pick the same slot at the same time | Both lock in turn; the second re-check sees it taken → `slot_taken` + alternatives; exactly 1 appointment (T24) |
| Front desk books the slot in Open Dental after we offered it | Re-check fails → `slot_taken` + alternatives |
| Same patient confirms twice (double click / repeated "yes") | Same idempotency key → `booked` with `replayed=True`; one appointment |
| Patient already has an appointment at that time (e.g. booked earlier in the session) | `patient_conflict`; P2-16 asks whether they meant to reschedule |
| Offer older than 15 min | `offer_expired`; the flow searches again |
| Clinic config changed between offer and booking | Session is pinned, so the same version is used; the re-check still uses fresh Open Dental data |
| Holiday on a day where Open Dental has a schedule | Day not offered (holidays win, DECISIONS #138) |
| Spring-forward day: 02:30 local doesn't exist | Grid skips it; no slot at a non-existent time (T5) |
| Fall-back day: 01:30 local twice | First occurrence only, no duplicate options (T6) |
| Open interval 08:50–09:35, length 40 min, grid 10 min | Starts 08:50 only (08:50+40 = 09:30 ≤ 09:35; 09:00+40 > 09:35) |
| Emergency blockout 13:00–14:00, routine patient | Subtracted; urgent patient may get 13:00 |
| New-patient blockout, existing patient | Subtracted |
| Staff meeting blockout | Subtracted (`other_blockouts_block_booking`) |
| Urgent request at 16:50 with AI window ending 17:00 | Range now+30 min → 17:20 is outside today; looks up to `urgent_max_hours`; if nothing → `none_in_range` → P2-20 URGENT callback |
| Provider preference not eligible for this visit type | Not ignored silently: `none_in_range` with reason code `provider_not_eligible`, so the AI can explain and offer other providers |
| Open Dental slow: 8 s budget reached after 1 option | Return 1 option (`status=options`) rather than nothing |
| Open Dental down | P1-15 error passes through; P2 offers a callback |
| Lock holder crashes | Lock expires after 60 s; the next booking proceeds |
| Booking POST times out | P1-16 reconciles via the AI marker → `booked` or `outcome_unknown` (callback, "please confirm with the clinic") |
| Variant disabled by P1-19's Open Dental check | `not_bookable` with `when_not_bookable` |

## 9. Security, HIPAA and PHI
- **PHI handled:**
  - PatNum and AptNum (identifiers);
  - appointment date, time, provider and visit type tied to a patient's session (PHI when linked to a person);
  - age in years (derived, in memory only).

  Names, DOB and contact details are **not** used here.
- **Where it goes:**
  - Open Dental over TLS (P1-15);
  - Redis offer store `avail:{session_id}`: times, provider and operatory numbers, reason code and patient type, no names. TTL 15 min, Memorystore with TLS, AUTH and CMEK (P1-02).
  - Lock keys hold only clinic, operatory or provider numbers and dates.
- **Never logged:** PatNum together with a time, appointment times, `local_label`, preferences text. Logs carry `clinic_id`, status, counts and durations only (P1-07 allow-list).
- **Slot integrity:** booking only accepts a `slot_id` this session was offered, so the LLM can't make up a time or a provider (P0-04 `fresh_availability`). PatNum comes from the verified session (P2-12), never from the model.
- **Risks reduced:** double bookings (§11), booking on closed or reserved time, and PHI in logs (P0-11 R01).

## 10. Testing
Engine unit tests (`backend/tests/unit/scheduling/`, table-driven, fixed `now_utc`, tz `America/New_York`):

| # | Test | Expected |
|---|---|---|
| T1 | Search range: routine at 10:00 local with lead 120 | First start ≥ 12:00; last ≤ end of day+7 |
| T2 | Urgent with lead 30, `urgent_max_hours` 24 | Range now+30 min → now+24 h |
| T3 | Holiday closed / holiday with morning hours | No options that day / only morning |
| T4 | AI window with lunch break; open interval across it | Split; no option overlaps 12:00–13:00 |
| T5 | Spring-forward day (2026-03-08) grid | No 02:xx starts; times correct in UTC |
| T6 | Fall-back day (2026-11-01) | No duplicate 01:xx options |
| T7 | Blockouts: emergency/new-patient/other × routine/new/urgent | Matrix as in §6 rule 4 |
| T8 | Grid and length (08:50–09:35 case; length from pattern `/XXXXXX/` = 40 min) | Exactly 08:50 |
| T9 | Variant selection: new vs existing, age 12 with `age_max: 17`, disabled variant, age unknown | Correct variant / skip / `NotBookable` |
| T10 | Preferences filter to empty | `none_in_range`; no silent relaxing |
| T11 | Spread: 10 candidates on 2 days | Options in 3 different half-days where possible; else ≥ 60 min apart |
| T12 | Cursor: "something later" twice | Strictly later options; no repeats |

Service and booking tests (against `od_fake` and real Redis):
| # | Test | Expected |
|---|---|---|
| T13 | `find` with 2 eligible providers, enough slots in window 1 | ≤ 2 Slots calls; 3 options |
| T14 | Not enough in window 1 | Window 2 fetched; options found |
| T15 | Budget hit after 1 option (fake delay) | 1 option returned in ≤ 8 s |
| T16 | Offer store | `get_offered` returns the slot; unknown `slot_id` → None |
| T17 | Lock ordering: two bookings needing the same two keys in opposite order | No deadlock; both finish |
| T18 | Lock TTL and release | A foreign token can't release; expiry after TTL |
| T19 | `book` happy path | `booked`; appointment in the fake with AI marker; slot removed from offers |
| T20 | `slot_taken_after_offer` fault | `slot_taken` with ≤ 3 alternatives excluding the slot |
| T21 | Patient already has an overlapping appointment | `patient_conflict` |
| T22 | `book` after config change | Uses the pinned version |
| T23 | `move` | Same AptNum, new time; own old appointment ignored in conflict checks |
| T24 | **Concurrency:** 20 sessions book one slot (2 processes × 10 tasks) | Exactly 1 `booked`, 19 `slot_taken`/`slot_busy`; fake has 1 appointment |

```bash
cd backend
pytest tests/unit/scheduling -q
pytest tests/integration/scheduling -q            # od_fake + Redis + Postgres via docker compose
```

## 11. Acceptance criteria
- [ ] The engine is a pure function with unit tests covering range, holidays, AI window, blockouts, grid, DST, variants, preferences, spreading and cursor (T1–T12)
- [ ] `find` returns 2–3 options from real Open Dental slots, never overlapping an appointment, a closed blockout, a holiday or the outside of the AI window, within an 8 s budget (T13–T16)
- [ ] Routine and urgent lead times, booking horizon and `urgent_slot_max_hours` come from the session's pinned config (T1, T2, T22)
- [ ] Booking only accepts a slot offered to this session in the last 15 min (T16, T19)
- [ ] The booking sequence locks, re-checks with fresh Open Dental data, creates with an idempotency key, verifies (P1-16) and always releases the lock (T17–T20)
- [ ] 20 concurrent bookings of one slot produce exactly one appointment (T24)
- [ ] Every outcome in `BookingOutcome` is reachable and tested; conflicts return alternatives (T19–T23)
- [ ] Reschedule keeps the AptNum and uses the same sequence (T23)
- [ ] The Verify items in §7 step 1 are recorded; `docs/scheduling.md` describes the rules order and booking sequence
- [ ] No PHI in logs (P1-07 leak suite over T13–T24)

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI (T1–T24)
- [ ] PR reviewed (HIPAA review if labelled `phi`): labelled `phi`; tech lead reviews the locking and re-check logic
- [ ] No PHI in logs
- [ ] Docs / README updated: `docs/scheduling.md` (with a sequence diagram), P1-15 doc note on `schedules(refresh=True)`

## 13. Hand-off
| Task | Can rely on |
|---|---|
| P2-08 Tool gateway | `get_appointment_availability` ↔ `AvailabilityService.find`; `book_appointment` ↔ `BookingService.book`; `reschedule_appointment` ↔ `BookingService.move`; typed results to map |
| P2-01 State machine | Offer store `avail:{session_id}`; `fresh_availability` = `get_offered()` is not None |
| P2-16 Booking flow | Outcomes and when to call `find` again (`slot_taken` alternatives, `offer_expired`, `patient_conflict`) |
| P2-18 Reschedule | `move`; notice-window rules stay in P2-18 |
| P2-20 Emergency | `find(urgent=True)` → `none_in_range` means URGENT callback |
| P2-22 Callback | `outcome_unknown` and `unavailable` → callback reasons |
| P5-04 Tests (DECISIONS #284: these tests are in P5-04, not P5-03) | Concurrency (T24) and DST suites to extend; `od_fake` faults |
| P6-01 Onboarding | Set `min_lead_minutes`, `min_lead_minutes_urgent`, reserved blockouts, AI window |

## 14. Open questions
| Question | Recommended answer | Owner | Needed by |
|---|---|---|---|
| Does `GET /appointments/Slots` exclude blockouts and Open Dental's own closed days? | Assume not: we subtract blockouts and apply our holidays ourselves, which is correct either way. Check once on test DB (B). | Tech lead | Step 1 |
| Does an empty `operatories` value on a blockout row mean "all operatories"? | Assume yes (safer: blocks more). Check on test DB (B). | Tech lead | Step 1 |
| What is the longest date range Slots accepts? | Query in chunks of ≤ 14 days (the documented default range); with the default 7-day horizon that is one call per provider. | Tech lead | Step 1 |

## 15. References
- Plan §1, §4.6, §4.8, §11
- Open Dental Appointments API (Slots, create, update): https://www.opendental.com/site/apiappointments.html
- Open Dental Schedules API (blockouts): https://www.opendental.com/site/apischedules.html
- Python `zoneinfo` (DST, `fold`): https://docs.python.org/3/library/zoneinfo.html
- Redis `SET … NX PX` and safe release: https://redis.io/docs/latest/commands/set/ and https://redis.io/docs/latest/develop/use/patterns/distributed-locks/
- Related tasks: P0-02, P0-03, P0-04, P1-07, P1-15, P1-16, P1-19, P2-01, P2-08, P2-16, P2-18, P2-20, P2-22, P5-03, P6-01
