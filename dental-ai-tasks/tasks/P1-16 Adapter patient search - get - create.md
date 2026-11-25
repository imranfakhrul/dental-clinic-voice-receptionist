---
id: P1-16
title: Open Dental patient and appointment adapters (search, get, create, reschedule, cancel) with safe writes
milestone: P1
epic: E1.3
size: L
labels: area:open-dental, area:backend, type:feature, phi
depends_on: P0-12, P1-03, P1-07, P1-15
status: approved
---

# P1-16: Open Dental patient and appointment adapters (search, get, create, reschedule, cancel) with safe writes

## 1. Summary
Build the typed adapters that every patient and appointment operation goes through. This task also absorbs **P1-17 (appointments get / create / update / break)**.

1. **`OpenDentalPatients`** (`patients.py`):
   - search by last name + date of birth, and by phone;
   - get one patient by PatNum;
   - create a new patient with no duplicates.
2. **`OpenDentalAppointments`** (`appointments.py`):
   - list a patient's appointments, get one by AptNum, list one operatory's appointments for a day;
   - **create**, **reschedule** (move in place, so the AptNum stays the same) and **cancel** (Open Dental "Break", sent to the Unscheduled list).
3. **`IdempotencyGuard`** (`idempotency.py`): makes every write safe to repeat.
   - It uses P1-03's `idempotency_keys` table in Postgres.
   - Combined with P1-15's rule that writes are never resent (`OpenDentalUncertainWrite`), it **reconciles** an unclear write by reading Open Dental back.
   - It finds AI-made appointments exactly through a PHI-free **AI marker** (`[AI-booked ref:7KQ2M9XA]`) in the appointment note. The same marker lets staff review AI bookings.
4. **`od_fake` extended** with the patient and appointment endpoints, the duplicate rule and write faults. Contract tests C9 and C11–C18 are added.

Done means:
- every call returns typed, minimal models;
- the same idempotency key never produces two Open Dental records, including under concurrency, timeouts and 429s;
- a write is only reported as done after Open Dental confirms it, by reading it back;
- the tests pass against `od_fake` in CI and against test DB (B) nightly.

## 2. Why this matters
Every conversation that books, reschedules or cancels starts by finding the right patient, and ends with a write to Open Dental, the clinic's record (plan §1, principle 1). Three pilot targets depend directly on this task (plan §11):
- **0 duplicate patients:** create must refuse when anyone similar already exists, and must never create twice on retry (§4.5).
- **0 double bookings:** a booking must never be sent twice. Open Dental has no idempotency keys and documents no overlap check on `POST /appointments`, so our own guard and the P1-20 re-check before booking carry this.
- **0 reminders for cancelled appointments:** reschedule keeps the same AptNum, so P4-04's reminder follows the appointment. Cancel is confirmed by reading back.

The plan's booking sequence (§4.6) requires: create with an idempotency key, verify the created record, and only then call it booked. P1-20 runs the lock and re-query steps; this task provides the create, verify and reconcile steps.

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P1, Core Platform & Open Dental Adapter**.
- **What already exists:**
  - **P1-15:**
    - `OpenDentalClient` (`get`, `get_all`, `post`, `put`), `ClinicODContext` (clinic_id, customer key secret, `tz`, `od_clinic_num`), `Priority`;
    - typed errors, including `OpenDentalUncertainWrite` (a write whose result is unknown: 504, timeout after send, or 429) and `OpenDentalBadRequest` with a `reason_code`;
    - `parsing.py` (`od_bool`, `od_int`, `od_date`, `od_local_dt`, `to_od_local_dt`);
    - `od_fake` with fault injection, including `timeout_after_commit`;
    - fixed `endpoint` names for logs.
  - **P1-03:**
    - `idempotency_keys` (`clinic_id`, `key`, `operation` ∈ `BOOK`/`RESCHEDULE`/`CANCEL`/`CREATE_PATIENT`, `request_hash`, `status` ∈ `IN_PROGRESS`/`SUCCEEDED`/`FAILED`, `result_ref`, `created_at`, `expires_at` = +24 h);
    - `appointment_refs` (`clinic_id`, `aptnum`, `patnum`, `created_by_session_id`, `status_cache`, `status_checked_at`);
    - `ClinicScopedRepository`.
  - **P1-07:** event-name logging and the field allow-list; the PHI leak suite.
  - **P0-12:**
    - test DB (B) seed cases: plain returning patient, hyphen/apostrophe/accent names, phone stored in different formats, missing DOB or phone, Inactive/Archived/Deceased statuses;
    - `seed_patients.csv`.
  - **P0-01 defaults** (Proposed until the workshop answers):
    - B3: `Patient` and `Inactive` count as existing patients; other statuses go to a callback;
    - B4: the AI may create a new patient when there is no doubt;
    - B8: mobile numbers are in `WirelessPhone`;
    - Q2: new-patient bookings are flagged for staff review through an AI note;
    - Q10: single location for the pilot.
- **Open Dental API facts** (docs read 2026-11-24; https://www.opendental.com/site/apipatients.html and https://www.opendental.com/site/apiappointments.html):
  - **Patients:**
    - `GET /patients/{PatNum}` (21.1).
    - `GET /patients/Simple` (21.2): `LName`, `FName` match partially and case-insensitively; also `Birthdate` (`yyyy-MM-dd`), `PatStatus` (Patient, NonPatient, Inactive, Archived, Deceased, Prospective), `ClinicNum`, `DateTStamp`. `HmPhone`, `WkPhone`, `WirelessPhone` were **added in 25.4.29**, and their match rule isn't stated. No single `Phone` parameter.
    - `GET /patients` (21.1) has a `Phone` parameter. "Most string parameters support partial match". The docs warn it "can be slow on large databases".
    - `POST /patients` (21.1):
      - required `LName`, `FName`; optional `Birthdate`, `WirelessPhone`, `HmPhone`, `Email`, `Address`, `Address2`, `City`, `State` (2 capitals), `Zip`, `PatStatus` (default Patient), `TxtMsgOk` (default Unknown), `ClinicNum`, `PriProv`, `Preferred`;
      - returns 201 with the full patient, including `PatNum`;
      - the docs say new patient data "is compared against existing patient information (LName, FName, Birthdate, and Email or phone numbers) to prevent duplicates". They don't say what happens on a match or what error text comes back.
    - Patients can't be deleted via the API.
  - **Appointments:**
    - `GET /appointments/{AptNum}` (21.1). The response includes `AptNum`, `PatNum`, `AptStatus`, `Pattern`, `Confirmed`, `Op`, `Note`, `ProvNum`, `ProvHyg`, `AptDateTime`, `ClinicNum`, `IsNewPatient`, `AppointmentTypeNum`, `DateTStamp`.
    - `GET /appointments` (21.1): `PatNum` (21.4), `date`, `dateStart`/`dateEnd` (inclusive), `ClinicNum`, `AptStatus` (22.4.28), `Op` (23.2.27), `DateTStamp`; paged with `Offset`.
    - `POST /appointments` (21.1):
      - required `PatNum`, `Op`, `AptDateTime` (`yyyy-MM-dd HH:mm:ss`);
      - optional `AptStatus` (default Scheduled), `Pattern` (5-minute units of `X` and `/`, default `/XX/`), `Confirmed` (DefNum of definition category 2), `Note`, `ProvNum`, `ProvHyg`, `ClinicNum`, `IsNewPatient` (21.3), `Priority` (22.1), `AppointmentTypeNum` (22.1);
      - returns 201 with the full appointment, including `AptNum`;
      - **no overlap or collision check is documented.**
    - `PUT /appointments/{AptNum}` (21.1): all fields optional, including `AptDateTime`, `Op`, `ProvNum`, `Pattern`, `AptStatus`, `Confirmed`. `Note` here **overwrites** the note. Rescheduling is done by updating `AptDateTime` and `Op`.
    - `PUT /appointments/{AptNum}/Break` (21.3):
      - only works on `Scheduled` appointments;
      - `sendToUnscheduledList` is required ("usually true");
      - `breakType` (`Missed`/`Cancelled`) adds procedure codes D9986/D9987 and is rarely used.
    - `PUT /appointments/{AptNum}/Note` (21.1) **appends** a line to the note.
    - `AptStatus` values: Scheduled, Complete, UnschedList, ASAP (GET filter only), Broken, Planned, PtNote, PtNoteCompleted.
- **Phone formats:** Open Dental stores phones as free text typed by staff (`5035550101`, `(503) 555-0102`, `503-555-0103`; P0-12 seed). We compare in E.164 (`+15035550101`) using the `phonenumbers` library with region `US`.

## 4. Scope
**In scope**
- **Package `backend/app/integrations/open_dental/`:**
  - `patients.py`, `appointments.py`, `idempotency.py`, `markers.py`, `policy.py` (`ClinicODPolicy` and its provider interface);
  - models added to `models.py`.
- **Exact-match filtering** on our side: names (normalized), DOB, E.164 phones. Statuses are tagged with whether they count as an existing patient.
- **Safe writes:** `IdempotencyGuard` (Postgres `idempotency_keys`), duplicate pre-check before patient create, reconciliation after `OpenDentalUncertainWrite`, and verification by reading back after every write.
- **The AI marker** in appointment notes, with config for the marker and the optional `Confirmed` DefNum.
- **Upkeep of `appointment_refs`** (insert on create; update `status_cache` on reschedule and cancel), in the same database as the guard.
- **`od_fake` extension:**
  - patients (`/patients/Simple`, `/patients`, `/patients/{n}`, `POST /patients` with the duplicate rule);
  - appointments (`GET`, `POST`, `PUT`, `PUT …/Break`, `PUT …/Note`);
  - faults on all writes.
- **Contract tests** C9 (local-time round-trip, carried over from P1-15) and C11–C18.
- **Docs:** a "Patients and appointments" section in `docs/integrations/open-dental-client.md`, with the Verify results.

**Out of scope** (and which task covers it)
- HTTP, auth, pacing, retries, base errors → P1-15
- Clinic config storage and admin editing of `open_dental.*` keys → P1-19 (this task defines the keys and defaults)
- Slot calculation, slot lock, re-query before booking, offering alternatives on conflict → P1-20
- Nickname matching, scoring (strong / partial / multiple / none), verification rules → P2-12
- Tool endpoints, audit entries for searches and writes, session scoping → P2-08 (tool gateway) and the flows P2-12, P2-16, P2-18
- Cancellation-window rules (how close to the appointment a patient may cancel) → P2-18 / P1-19
- Reminders and their re-fetch before sending → P4-04
- Updating patient demographics: not in the MVP

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P1-15 (approved) | Client, errors, parsing, `ClinicODContext`, `od_fake` base | Use the P1-15 signatures; the fake and the client can be built in parallel from the spec |
| P1-03 (approved) | `idempotency_keys`, `appointment_refs`, `ClinicScopedRepository`, `app_rw` role | Use the migration from P1-03; locally `docker compose up postgres` |
| P1-07 (approved) | Logging, leak suite | Use the spec signatures |
| P0-12 (approved) | Test DB (B), seed cases, phone-format cases | Build against `od_fake` with the same seed CSV |
| P1-19 Clinic config (not yet written) | Real values for `open_dental.*` keys (§6) | `StaticClinicODPolicyProvider` returns the defaults in §6; P1-19 replaces it with a config-backed provider |
| P0-01 workshop answers B3, B8, Q2, Q10 | Final statuses, phone field, note behaviour, locations | Defaults in §6 (all configurable) |

## 6. Interface contract

### Clinic policy (keys owned by P1-19; defaults here)
```yaml
# clinic config (P1-19), section open_dental
open_dental:
  clinic_num: null                        # P1-15
  phone_search_mode: legacy_phone         # legacy_phone | simple_fields (needs Open Dental >= 25.4.29)
  existing_patient_statuses: [Patient, Inactive]   # P0-01 B3
  new_patient_phone_field: WirelessPhone  # WirelessPhone | HmPhone (P0-01 B8)
  max_search_results: 25
  booking:
    note_marker: true                     # always true in the pilot; the marker is needed for reconciliation
    note_text_new_patient: "Booked online by the AI receptionist. New patient: please review."
    note_text_existing: "Booked online by the AI receptionist."
    confirmed_defnum_new_patient: null    # DefNum from GET /definitions?Category=2; null = Open Dental default
    confirmed_defnum_existing: null
  cancel:
    send_to_unscheduled_list: true
```
```python
@dataclass(frozen=True, slots=True)
class ClinicODPolicy:
    phone_search_mode: Literal["legacy_phone", "simple_fields"] = "legacy_phone"
    existing_patient_statuses: frozenset[str] = frozenset({"Patient", "Inactive"})
    new_patient_phone_field: Literal["WirelessPhone", "HmPhone"] = "WirelessPhone"
    max_search_results: int = 25
    note_text_new_patient: str = "Booked online by the AI receptionist. New patient: please review."
    note_text_existing: str = "Booked online by the AI receptionist."
    confirmed_defnum_new_patient: int | None = None
    confirmed_defnum_existing: int | None = None
    send_to_unscheduled_list: bool = True

class ClinicODPolicyProvider(Protocol):
    async def get(self, clinic_id: uuid.UUID) -> ClinicODPolicy: ...
```
The note texts are validated by P1-19 to contain no placeholders (they can never include patient data).

### Models (`models.py`)
```python
class PatientRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")
    pat_num: int
    first_name: str
    last_name: str
    preferred_name: str | None
    birthdate: date | None                # None when Open Dental has no DOB (Verify the "empty" value)
    phones_e164: list[str]                # wireless, home, work: normalized, valid only, de-duplicated
    email: str | None
    status: str                           # PatStatus as returned
    counts_as_existing: bool              # status in policy.existing_patient_statuses
    clinic_num: int | None
    # never kept: SSN, address, balances, insurance, guarantor, ChartNumber

class NewPatient(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    birthdate: date
    mobile_phone_e164: str               # validated E.164, US
    email: EmailStr | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")
    zip_code: str | None = Field(default=None, pattern=r"^\d{5}(-?\d{4})?$")

class AppointmentStatus(StrEnum):
    SCHEDULED = "Scheduled"
    COMPLETE = "Complete"
    UNSCHED_LIST = "UnschedList"
    BROKEN = "Broken"
    PLANNED = "Planned"
    PT_NOTE = "PtNote"
    PT_NOTE_COMPLETED = "PtNoteCompleted"

class Appointment(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")
    apt_num: int
    pat_num: int
    status: AppointmentStatus
    start_utc: datetime
    end_utc: datetime                     # start + len(pattern) * 5 min
    op_num: int
    prov_num: int | None
    prov_hyg: int | None
    clinic_num: int | None
    appointment_type_num: int | None
    is_new_patient: bool
    confirmed_defnum: int | None
    ai_ref: str | None                    # parsed from the note marker; the rest of the note is NOT kept

class NewAppointment(BaseModel):
    pat_num: int
    op_num: int
    start_utc: datetime                   # aware; converted to office local time
    pattern: str = Field(pattern=r"^[X/]{1,108}$")   # from P1-20 (appointment type length); 5-minute units
    prov_num: int
    prov_hyg: int | None = None
    appointment_type_num: int | None = None
    is_new_patient: bool = False
    is_hygiene: bool = False

class AppointmentMove(BaseModel):
    start_utc: datetime
    op_num: int
    prov_num: int | None = None           # None = keep
    pattern: str | None = None            # None = keep

@dataclass(frozen=True)
class WriteResult:
    ref: int                              # PatNum or AptNum
    replayed: bool                        # True when the same idempotency key already succeeded
    reconciled: bool                      # True when found by reading back after an uncertain write
```

### Patients (`patients.py`)
```python
class OpenDentalPatients:
    def __init__(self, client: OpenDentalClient, policies: ClinicODPolicyProvider,
                 guard: IdempotencyGuard) -> None: ...

    async def search_by_name_dob(self, ctx: ClinicODContext, last_name: str, birthdate: date, *,
                                 first_name: str | None = None) -> list[PatientRecord]: ...
    async def search_by_phone(self, ctx: ClinicODContext, phone_e164: str) -> list[PatientRecord]: ...
    async def get(self, ctx: ClinicODContext, pat_num: int) -> PatientRecord | None: ...
    async def create(self, ctx: ClinicODContext, new: NewPatient, *, idempotency_key: str) -> WriteResult: ...
```
- Searches return **all statuses except `Deceased`**, each tagged with `counts_as_existing`. A match with Archived, Prospective or NonPatient status must still stop an automatic create (P2-12 sends it to a callback). Otherwise we would create a duplicate chart.
- More than `max_search_results` exact matches raises `TooManyMatchesError`.
- `get` returns `None` on 404.

### Appointments (`appointments.py`)
```python
class OpenDentalAppointments:
    async def get(self, ctx: ClinicODContext, apt_num: int, *,
                  priority: Priority = Priority.INTERACTIVE) -> Appointment | None: ...
    async def list_for_patient(self, ctx: ClinicODContext, pat_num: int, *, start: date, end: date,
                               statuses: set[AppointmentStatus] | None = None,
                               priority: Priority = Priority.INTERACTIVE) -> list[Appointment]: ...
    async def list_for_operatory_day(self, ctx: ClinicODContext, op_num: int, day: date) -> list[Appointment]: ...
        # live, never cached; used by P1-20's re-query before booking

    async def create(self, ctx: ClinicODContext, new: NewAppointment, *, idempotency_key: str,
                     session_id: uuid.UUID | None) -> WriteResult: ...
    async def reschedule(self, ctx: ClinicODContext, apt_num: int, *, pat_num: int, move: AppointmentMove,
                         idempotency_key: str) -> WriteResult: ...
    async def cancel(self, ctx: ClinicODContext, apt_num: int, *, pat_num: int,
                     idempotency_key: str) -> WriteResult: ...
```
- **Ownership:** `reschedule` and `cancel` take the verified `pat_num` and refuse with `AppointmentNotOwned` if the appointment belongs to someone else, which prevents acting on another patient's record.
- **What can be changed:** only `Scheduled` appointments in the future can be changed (`AppointmentNotChangeable` otherwise). Cancelling an appointment that is already `Broken` or `UnschedList` returns success with `replayed=True`.
- **Status filter:** `list_for_patient` filters `AptStatus` on our side, so it works on versions before 22.4.10 too. It uses `PatNum` (21.4) plus `dateStart`/`dateEnd`.
- **Operatory filter:** `list_for_operatory_day` uses `date` + `ClinicNum`, sends `Op` only when the clinic version is ≥ 23.2.27 (a P1-19 flag), and always filters `Op` locally too.

### AI marker (`markers.py`)
```python
def ai_ref(clinic_id: uuid.UUID, idempotency_key: str) -> str:
    """8 chars, Crockford base32 of SHA-256(f"{clinic_id}|{idempotency_key}")[:5]. Same key -> same ref."""

def marker(kind: Literal["booked", "rescheduled", "cancelled"], ref: str) -> str:
    return f"[AI-{kind} ref:{ref}]"            # e.g. "[AI-booked ref:7KQ2M9XA]"

MARKER_RE = re.compile(r"\[AI-(booked|rescheduled|cancelled) ref:([0-9A-HJKMNP-TV-Z]{8})\]")
```
- **Create:** `Note` = `"[AI-booked ref:7KQ2M9XA] Booked online by the AI receptionist."`, with the `new_patient` text when `is_new_patient`.
- **Reschedule and cancel:** append through `PUT /appointments/{AptNum}/Note`, which keeps the staff's note. Example: `"[AI-rescheduled ref:Q3M8T1ZD] Moved online by the AI receptionist."`
- The ref is derived from our idempotency key, so it contains **no PHI** and is the same on every retry.

### Idempotency guard (`idempotency.py`)
```python
class Operation(StrEnum):
    BOOK = "BOOK"
    RESCHEDULE = "RESCHEDULE"
    CANCEL = "CANCEL"
    CREATE_PATIENT = "CREATE_PATIENT"

class IdempotencyGuard:
    async def run(self, ctx: ClinicODContext, *, key: str, operation: Operation, request: Mapping[str, Any],
                  write: Callable[[], Awaitable[int]],
                  reconcile: Callable[[], Awaitable[int | None]]) -> WriteResult: ...
```
`request` is hashed and never stored: `request_hash` = SHA-256 of canonical JSON. Keys are built by callers from IDs only, e.g. `book:<session_id>:<slot_hash>`, `cancel:<session_id>:<aptnum>`, `create_patient:<session_id>`, and must match `^[a-z_]+:[A-Za-z0-9:_-]{1,200}$` (no PHI).

Algorithm. Each step that touches the database runs in its own short transaction, committed **before** Open Dental is called:
1. `INSERT … (status='IN_PROGRESS') ON CONFLICT (clinic_id, key) DO NOTHING RETURNING …`.
2. **If the row already exists:**
   - `request_hash` differs → `IdempotencyKeyReused` (a bug).
   - `SUCCEEDED` → return `WriteResult(ref=result_ref, replayed=True)`.
   - `IN_PROGRESS` and younger than `OD_WRITE_SETTLE_S` (90 s) → `IdempotencyInProgress`. The caller says "still working on it" and re-checks.
   - `IN_PROGRESS` and older (the earlier attempt died mid-way) → run `reconcile()`. If found → `SUCCEEDED`; if not → take over the row and continue with step 3.
   - `FAILED` → take over the row and continue with step 3. FAILED is set only when Open Dental definitely did not write.
3. **Call `write()`:**
   - It returns the ref → set `SUCCEEDED` and `result_ref`, and return.
   - `OpenDentalUncertainWrite` → call `reconcile()` once, right away.
     - Found → `SUCCEEDED`, `reconciled=True`.
     - Not found → leave the row `IN_PROGRESS` and raise **`WriteOutcomeUnknown`**. A retry after 90 s reconciles again first. 90 s is longer than Open Dental's 60 s processing limit, so by then the outcome is settled.
   - A definite failure (any other typed error before or without the write being processed) → `FAILED`, and the error is re-raised.

The guard never retries the write itself. Repeating is always the caller's decision, using the same key.

### Write flows
**Patient create:**
1. **Pre-check:** `search_by_name_dob(last_name, birthdate)` across all statuses except Deceased. If any record matches on last name, DOB and (normalized) first name **or** preferred name, raise `DuplicatePatientError` and **send no POST**.
2. **`POST /patients`** with `LName`, `FName`, `Birthdate`, `{policy.new_patient_phone_field}` (format per the Verify spike, default `(503) 555-0123`), `Email`, `Address`, `Address2`, `City`, `State`, `Zip`, `TxtMsgOk: "Unknown"`, and `ClinicNum` when `od_clinic_num` is set. Consent to messages is ours (P4-02), not Open Dental's.
3. **400 handling:** a 400 whose text indicates a duplicate (**Verify** the text) → `DuplicatePatientError`. Any other 400 → `OpenDentalBadRequest`.
4. **Reconcile:** search by name and DOB again. Exactly one record with the same first name and phone → that PatNum. Otherwise `None`.
5. **Verify:** `GET /patients/{PatNum}`. Last name, first name and DOB must match what was sent, else `WriteVerificationFailed`.

**Appointment create:**
1. **`POST /appointments`** with:
   - `PatNum`, `Op`, `AptDateTime` (office local), `AptStatus: "Scheduled"`, `Pattern`, `ProvNum`;
   - `ProvHyg`, `IsHygiene`, `AppointmentTypeNum` (only when set; **Verify** that sending `Pattern` with `AppointmentTypeNum` keeps our pattern);
   - `IsNewPatient`, `ClinicNum`, `Note` (marker + text), and `Confirmed` when a policy DefNum is set.
2. **Verify:** `GET /appointments/{AptNum}`. `PatNum`, `AptDateTime`, `Op`, `AptStatus=Scheduled` and the marker must match, else `WriteVerificationFailed`.
3. **Record:** insert `appointment_refs` (`status_cache=SCHEDULED`, `created_by_session_id`).
4. **Reconcile:** `list_for_patient(pat_num, day, day)`. Exactly one appointment whose note carries this `ai_ref` → that AptNum.

**Reschedule:**
1. `get` → check owner, status and that it is in the future.
2. `PUT /appointments/{AptNum}` with `AptDateTime`, `Op`, and `ProvNum`/`Pattern` if given.
3. Append the marker with `PUT …/Note`. If this note call fails, only log it: the move itself is done.
4. **Verify:** `get` shows the new time and operatory.
5. Update `appointment_refs.status_cache`.
6. **Reconcile:** `get`. New time and operatory → done. Old time → `None`.

**Cancel:**
1. `get` → check owner. Already `Broken`/`UnschedList` → replayed success. Otherwise it must be `Scheduled` and in the future.
2. `PUT …/Break` with `{"sendToUnscheduledList": "true"|"false"}` per policy. **No `breakType`**, so no fee codes are added.
3. Append the marker note.
4. **Verify:** `get` shows a status that isn't `Scheduled`.
5. `appointment_refs.status_cache=CANCELLED`.
6. **Reconcile:** same as verify.

### Errors (added to `errors.py`; all `AppError` with fixed messages)
| Class | When | Caller handling (P2) |
|---|---|---|
| `DuplicatePatientError` | Pre-check found a similar patient, or Open Dental rejected the create as a duplicate | Callback; never create |
| `TooManyMatchesError` | Exact matches > `max_search_results` | Treat as ambiguous → callback |
| `AppointmentNotOwned` | Appointment's PatNum ≠ verified patient | Say "I can't find that appointment"; audit (P2-08) |
| `AppointmentNotChangeable` | Not `Scheduled`, or in the past | Explain; callback if needed |
| `IdempotencyKeyReused` | Same key, different request | Bug: alert; callback |
| `IdempotencyInProgress` | Same key still running (< 90 s) | "Still working on it", re-check |
| `WriteOutcomeUnknown` | Uncertain write and reconcile found nothing | Do **not** tell the patient it worked or failed; callback with "please confirm with the clinic" (P2-22) |
| `WriteVerificationFailed` | Written, but read-back doesn't match | Callback + alert (`opendental.write_mismatch`) |

### Settings (extends P1-01)
```python
OD_WRITE_SETTLE_S: int = Field(default=90, ge=65)   # > Open Dental's 60 s processing limit
```

### Endpoint names (for P1-15 logs and metrics)
`patients.simple`, `patients.search_legacy`, `patients.get`, `patients.create`, `appointments.list`, `appointments.get`, `appointments.create`, `appointments.update`, `appointments.break`, `appointments.note`.

### Log events (through P1-07; IDs and counts only)
| Event | Fields |
|---|---|
| `opendental.patient_search` | `clinic_id`, `mode` (`name_dob`/`phone_simple`/`phone_legacy`), `raw_count`, `match_count` |
| `opendental.write` | `clinic_id`, `operation`, `outcome` (`succeeded`/`replayed`/`reconciled`/`failed`/`unknown`), `duration_ms` |
| `opendental.write_mismatch` | `clinic_id`, `operation` |
| `opendental.duplicate_blocked` | `clinic_id`, `source` (`precheck`/`opendental`) |

### Example
```python
res = await appts.create(ctx, NewAppointment(pat_num=48, op_num=2,
        start_utc=datetime(2026, 12, 7, 15, 0, tzinfo=UTC), pattern="/XXXX/", prov_num=1,
        appointment_type_num=3), idempotency_key="book:6f1c…:a91e", session_id=sid)
# POST /appointments {"PatNum":48,"Op":2,"AptDateTime":"2026-12-07 10:00:00","AptStatus":"Scheduled",
#   "Pattern":"/XXXX/","ProvNum":1,"AppointmentTypeNum":3,"IsNewPatient":"false",
#   "Note":"[AI-booked ref:7KQ2M9XA] Booked online by the AI receptionist."}
# -> WriteResult(ref=7713, replayed=False, reconciled=False)
```

## 7. Implementation guide
1. **Spikes on test DB (B) first.** Record each result in `open-dental-client.md` and DECISIONS.md:
   - **Verify** which phone query format matches stored numbers for `GET /patients?Phone=` and, if the version allows, `/patients/Simple?WirelessPhone=`;
   - the value of a missing DOB (expected `0001-01-01`);
   - the 400 text when `POST /patients` hits Open Dental's duplicate rule;
   - whether `POST /appointments` rejects an overlapping appointment (and with what text);
   - whether `Pattern` sent with `AppointmentTypeNum` is kept;
   - the `Break` response on a non-Scheduled appointment.
2. **Models, `markers.py` and normalization helpers:**
   - `norm_name`: NFKC, casefold, trim, collapse spaces, keep hyphen and apostrophe, strip other punctuation;
   - `to_e164` with `phonenumbers`.

   Unit tests T1–T4.
3. **`idempotency.py`:** the guard against real Postgres (testcontainers), including concurrency and the stale `IN_PROGRESS` path (T5–T9).
4. **`patients.py`:** searches in both phone modes, get, create with pre-check, reconcile and verify (T10–T14).
5. **`appointments.py`:** get, lists, create, reschedule, cancel, ownership and status guards, `appointment_refs` (T15–T21).
6. **`od_fake` extension:**
   - in-memory patients and appointments seeded from `seed_patients.csv`;
   - partial `LName`/`FName` matching like the real API;
   - a duplicate rule that returns 400 with the text found in step 1;
   - `Break` allowed only on `Scheduled`;
   - Note append semantics;
   - write faults (`timeout_after_commit`, `status 429`, `status 504`) for `patients.create`, `appointments.create`, `appointments.update`, `appointments.break`.
7. **Contract tests** C9 and C11–C18 against the fake and once against test DB (B). Use synthetic last names with a random suffix (`Testpatient-7K2Q`) so runs don't collide.
8. **Leak check:** run P1-07's PHI leak suite over the whole test run. Names, DOBs, phones and emails from the fixtures must not appear in captured logs (T22).
9. **Notify:**
   - P1-19: policy keys and defaults; the version flags `simple_fields` and `Op` filter;
   - P1-20: `list_for_operatory_day`, `create`, `WriteResult`, the overlap-check spike result;
   - P2-12: `counts_as_existing`, the duplicate and too-many errors;
   - P2-16 and P2-18: key formats, `WriteOutcomeUnknown`, `IdempotencyInProgress`;
   - P2-22: the callback reasons;
   - P4-04: reschedule keeps the AptNum, and `get` with `Priority.BACKGROUND`;
   - P6-01: staff training on the AI marker.

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| "Smith" search returns "Smithson" (partial match in Open Dental) | Dropped by exact normalized last-name match |
| "O'Neil" vs "ONeil", "José" vs "Jose" | Apostrophe kept, accents kept (NFKC + casefold); accent-insensitive matching is P2-12's job, not here |
| Twins (same last name and DOB) | Both returned; P2-12 disambiguates by first name |
| Shared family phone returns 4 records | All 4 returned; phone alone never identifies (§4.5) |
| Match has status Archived or Prospective | Returned with `counts_as_existing=False`; create's pre-check still blocks a new chart |
| Deceased record matches | Excluded from results; count logged |
| Stored phone `555-0101` (no area code) or junk | Dropped from `phones_e164`; record still returned for name+DOB searches |
| DOB missing in Open Dental | `birthdate=None`; it can't match a name+DOB search; phone search still finds it |
| > 25 exact matches | `TooManyMatchesError` |
| Same create called twice (network retry from the browser) | Second call returns `replayed=True`; one POST total |
| Two instances create with the same key at the same moment | One inserts the guard row; the other gets `IdempotencyInProgress` |
| Booking POST times out (504) or gets 429 | `OpenDentalUncertainWrite` → reconcile by `ai_ref` → found: success (`reconciled=True`); not found: `WriteOutcomeUnknown`, row stays `IN_PROGRESS` |
| Retry of that key 2 minutes later | Row is stale → reconcile again → found or take over and POST |
| Open Dental accepts an overlapping appointment (no collision check) | Not this task's guard: P1-20 re-queries `list_for_operatory_day` under the slot lock before calling `create` |
| Created appointment reads back with a different time (time zone bug) | `WriteVerificationFailed` + alert; callback |
| Reschedule of an appointment that staff already completed or broke | `AppointmentNotChangeable` |
| Cancel of an already broken appointment | Success, `replayed=True` (no second Break) |
| Patient asks to cancel someone else's AptNum (from a guessed number) | `AppointmentNotOwned`; no detail revealed |
| Note append after Break fails | Break counts as done; `opendental.write` logged with `outcome=succeeded` and a warning event; staff still see the Broken status |
| Staff edit the note and remove the marker | Reconcile can't find it; only matters for in-flight uncertain writes; falls back to `WriteOutcomeUnknown` → callback |

## 9. Security, HIPAA and PHI
- **PHI handled:**
  - patient first and last name, preferred name, DOB, phones, email, address (create only), PatNum, AptNum;
  - appointment time, operatory, provider and appointment type (PHI when linked to a patient).
- **Where it goes:**
  - between our backend and Open Dental over TLS (P1-15);
  - models live in memory for the request only;
  - **stored by us:** `idempotency_keys.result_ref` (PatNum/AptNum), `appointment_refs` (AptNum, PatNum, status). No names, DOBs, phones, times or notes.
  - `request_hash` is a one-way hash, and the request itself is not stored.
- **Never logged:** names, DOB, phones, email, address, appointment times, notes, query strings, bodies. Only IDs, counts, outcomes and durations (P1-07 allow-list; leak suite T22).
- **Minimum data:** `PatientRecord` drops address, SSN, balances, insurance and guarantor. `Appointment` keeps only the marker ref from the note, never the staff's note text (it can contain clinical details).
- **Idempotency keys and AI refs contain no PHI**, enforced by the key regex. The ref is a hash of the key.
- **Ownership check** on reschedule and cancel prevents cross-patient actions. The adapter itself doesn't decide whether a person is verified; P2-12 does, and passes only a verified `pat_num`.
- **Audit:** the tool gateway (P2-08) writes `patient.search`, `patient.create`, `appointment.book`, `appointment.reschedule` and `appointment.cancel` around these calls. This adapter returns everything needed (refs, outcome) for that.
- **Fixtures and the fake** use synthetic data only (P0-12).
- **Risks reduced:** duplicate charts and double bookings (plan §11), and PHI in logs (P0-11 R01).

## 10. Testing
Unit tests (`backend/tests/unit/open_dental/`):

| # | Test | Expected |
|---|---|---|
| T1 | `norm_name("  Anne-Marie  O'Neil ")`, `norm_name("JOSÉ")` | `"anne-marie o'neil"`, `"josé"` |
| T2 | `to_e164` on `5035550101`, `(503) 555-0102`, `503-555-0103`, `555-0101`, `""` | First three valid E.164; last two dropped |
| T3 | `ai_ref(c, "book:s1:x")` twice; different key | Same 8-char ref; different ref; matches `MARKER_RE` |
| T4 | Raw patient JSON with SSN, address, balances → `PatientRecord` | Those fields absent; `counts_as_existing` per policy |
| T5 | Guard: same key twice sequentially | Second returns `replayed=True`; `write` called once |
| T6 | Guard: same key, 2 concurrent tasks | One `write`; the other `IdempotencyInProgress` |
| T7 | Guard: same key, different request | `IdempotencyKeyReused` |
| T8 | Guard: `write` raises `OpenDentalUncertainWrite`, `reconcile` returns 7713 / returns None | `reconciled=True` / `WriteOutcomeUnknown` with row `IN_PROGRESS` |
| T9 | Guard: stale `IN_PROGRESS` (> 90 s), reconcile None | Takes over; `write` called once |

Adapter tests (against `od_fake`):
| # | Test | Expected |
|---|---|---|
| T10 | Name+DOB search for "Smith" with "Smithson" in data | Only Smith returned |
| T11 | Phone search, both modes, on the three phone-format seed cases | Same PatNums found in both modes |
| T12 | Create when an Archived patient with the same name+DOB exists | `DuplicatePatientError`; **zero** POSTs reached the fake |
| T13 | Create with `timeout_after_commit` fault | `reconciled=True`; one POST; same PatNum on a second call with the same key |
| T14 | Create rejected by the fake's duplicate rule | `DuplicatePatientError` |
| T15 | Appointment create → read back | Note has the marker; `appointment_refs` row; `WriteResult` with the AptNum |
| T16 | Appointment create with `timeout_after_commit`; with `status 429` (fault leaves no write) | Reconciled by `ai_ref` / `WriteOutcomeUnknown`, then a retry after settle POSTs once |
| T17 | Reschedule | Same AptNum; new time and Op; marker appended; staff note text still there |
| T18 | Reschedule a `Complete` appointment; a past one | `AppointmentNotChangeable` |
| T19 | Cancel twice | One Break call; second `replayed=True`; status `UnschedList`/`Broken` per policy |
| T20 | Cancel with a different `pat_num` | `AppointmentNotOwned`; no write |
| T21 | `list_for_patient` filters statuses locally; `list_for_operatory_day` filters Op locally | Correct sets regardless of the server-side filter |
| T22 | Whole suite under P1-07's leak capture | No fixture name, DOB, phone or email in logs |

Contract tests (fake in CI; test DB (B) nightly, serial; marker `opendental`):
- C9: create an appointment at a known local time (including a DST-change date) and read it back, the same wall-clock time (time zone check from P1-15);
- C11: `/patients/Simple` partial name matching and the `Birthdate` filter;
- C12: phone search per the version available;
- C13: `POST /patients` returns 201 with `PatNum`; the duplicate rule's behaviour;
- C14: `GET /appointments?PatNum=&dateStart=&dateEnd=` shape and paging;
- C15: `POST /appointments` returns 201 with `AptNum` and keeps `Note`, `Pattern`;
- C16: `PUT /appointments/{n}` moves the time and Op, same AptNum;
- C17: `PUT …/Break` on Scheduled, and on non-Scheduled (error);
- C18: `PUT …/Note` appends.

```bash
cd backend
pytest tests/unit/open_dental -q
pytest -m opendental tests/contract/open_dental -q                       # against od_fake (CI)
OPEN_DENTAL_BASE_URL=https://api.opendental.com/api/v1 pytest -m opendental -p no:xdist tests/contract/open_dental  # test DB (B)
```

## 11. Acceptance criteria
- [ ] `OpenDentalPatients` and `OpenDentalAppointments` expose exactly the methods and models in §6; no other module parses Open Dental patient or appointment JSON
- [ ] Name+DOB and phone searches return only exact matches (normalized name, DOB, E.164), all statuses except Deceased, tagged `counts_as_existing` (T10, T11)
- [ ] Patient create sends no POST when the pre-check finds a similar record of any status, and maps Open Dental's duplicate rejection to `DuplicatePatientError` (T12, T14)
- [ ] For the same idempotency key, at most one Open Dental write is sent, including under concurrency, timeouts and 429s (T5–T9, T13, T16)
- [ ] Every write is reported as done only after read-back verification; uncertain writes are reconciled (by `ai_ref` for appointments) or end in `WriteOutcomeUnknown` (T8, T13, T15, T16)
- [ ] Reschedule keeps the AptNum; cancel uses Break with the policy's `sendToUnscheduledList` and no `breakType`; both check owner and status (T17–T20)
- [ ] Appointment notes carry the AI marker; staff note text is never overwritten or stored by us (T15, T17)
- [ ] `appointment_refs` is kept current on create, reschedule and cancel
- [ ] `od_fake` supports the new endpoints and faults; C11–C18 pass on the fake in CI and once on test DB (B); C9 passes on test DB (B)
- [ ] The six Verify spikes in §7 step 1 are resolved and recorded in DECISIONS.md and `open-dental-client.md`
- [ ] No PHI in logs (T22)

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI (T1–T22, C11–C18 on the fake)
- [ ] PR reviewed (HIPAA review if labelled `phi`): labelled `phi`; tech lead + compliance owner review data minimization, logging and the ownership check
- [ ] No PHI in logs (P1-07 leak suite)
- [ ] Docs / README updated: "Patients and appointments" section in `open-dental-client.md` (policy keys, write flows, Verify results); staff-facing note on the AI marker for P6-01

## 13. Hand-off
| Task | Can rely on |
|---|---|
| P1-19 Clinic config | The `open_dental.*` keys and defaults in §6; implements `ClinicODPolicyProvider`; version flags for `simple_fields` and the `Op` filter |
| P1-20 Availability, slot lock, booking sequence | `list_for_operatory_day` (live) for the re-query under lock; `create` → `WriteResult`; `WriteOutcomeUnknown` and `IdempotencyInProgress` semantics |
| P2-08 Tool gateway | Typed results and errors to audit and map to tool responses |
| P2-12 Matching and verification | `PatientRecord` with `counts_as_existing`; `DuplicatePatientError`, `TooManyMatchesError`; create only after P2-12 says "no match" |
| P2-16 Booking and check appointment | Key format `book:<session_id>:<slot_hash>`; `list_for_patient`; `appointment_refs` filled |
| P2-18 Reschedule and cancel | `reschedule`, `cancel` with ownership; replayed cancel is success |
| P2-22 Callback | Callback reasons for `WriteOutcomeUnknown`, `WriteVerificationFailed`, duplicates |
| P4-04 Reminders | AptNum is stable across reschedules; `get(…, priority=BACKGROUND)` before sending |
| P6-01 Onboarding | Staff guide: the AI marker, the new-patient review note, the Unscheduled list after AI cancellations |

## 14. Open questions
| Question | Owner | Needed by |
|---|---|---|
| Which phone query format matches stored numbers, and which Open Dental version does the pilot clinic run (decides `phone_search_mode`)? | Tech lead (test DB (B)) + clinic (P0-01 B1) | Step 1 |
| Does `POST /appointments` reject overlaps, and what does the duplicate-patient 400 say? | Tech lead (test DB (B)) | Step 1 |
| Is the clinic happy with the AI marker text in appointment notes, and should new-patient bookings use a specific "Confirmed" status? | Clinic (P0-01 Q2, P6-01) | Before the pilot |

## 15. References
- Plan §1, §4.5, §4.6, §4.7, §5, §11
- Open Dental Patients API: https://www.opendental.com/site/apipatients.html
- Open Dental Appointments API: https://www.opendental.com/site/apiappointments.html
- Open Dental Definitions API (Confirmed = category 2): https://www.opendental.com/site/apidefinitions.html
- Open Dental API implementation (formats, paging): https://www.opendental.com/site/apiimplementation.html
- phonenumbers (Python): https://github.com/daviddrysdale/python-phonenumbers
- PostgreSQL `INSERT … ON CONFLICT`: https://www.postgresql.org/docs/16/sql-insert.html
- Related tasks: P0-01, P0-11, P0-12, P1-03, P1-07, P1-15, P1-19, P1-20, P2-08, P2-12, P2-16, P2-18, P2-22, P4-02, P4-04, P6-01
