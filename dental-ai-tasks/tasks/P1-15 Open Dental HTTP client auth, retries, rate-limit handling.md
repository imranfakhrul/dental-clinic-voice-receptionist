---
id: P1-15
title: Open Dental client (auth, shared per-clinic pacing, retries, typed errors) and cached setup adapter
milestone: P1
epic: E1.3
size: L
labels: area:open-dental, area:backend, type:feature, phi
depends_on: P0-12, P1-01, P1-02, P1-05, P1-07
status: approved
---

# P1-15: Open Dental client (auth, shared per-clinic pacing, retries, typed errors) and cached setup adapter

## 1. Summary
Build the **only** code that talks to Open Dental, plus the read-only setup adapter on top of it. This task also absorbs **P1-18 (providers, appointment types, schedules, operatories, with cache)**.

1. **`OpenDentalClient`** (`backend/app/integrations/open_dental/client.py`):
   - async `httpx` calls with the `ODFHIR` auth header;
   - the developer key from settings; the customer key per clinic, fetched from Secret Manager at runtime;
   - timeouts;
   - **shared per-clinic pacing in Redis** (Open Dental allows 1 request per second per customer key), with two priorities: interactive before background;
   - retries for **reads only**;
   - **writes are never retried automatically.** An unclear result raises `OpenDentalUncertainWrite`;
   - typed errors, pagination, value parsing (string booleans and numbers, local datetimes converted with the clinic's time zone);
   - PHI-safe logging and metrics.
2. **`OpenDentalSetup`** (`setup.py`): typed, minimal models with Redis caching for:
   - providers, operatories, appointment types, clinics (cached 6 h);
   - schedules (cached 10 min);
   - open slots (never cached).

   Refresh paths: a daily job, a manual refresh (P4-11) and invalidation on clinic-config change.
3. **`od_fake`:** a small fake Open Dental server loaded with P0-12's synthetic seed data. It behaves like the real API: 100-item pages, 1 request/s throttle with 429, 504s and injectable faults. Developers and CI use it, so P1-16, P1-20 and P2 can be built in parallel without the throttle. The same contract tests run nightly against test DB (B).

Done means:
- every Open Dental call in the codebase goes through this client (enforced by a test);
- the pacing holds across instances;
- reads retry and writes don't;
- setup data is cached with hit/miss metrics;
- the contract suite passes against the fake in CI and against test DB (B) nightly.

## 2. Why this matters
Open Dental is the source of truth for patients and appointments. Every booking, reschedule and reminder depends on it. Its Remote API is slow and strict:
- one request per second per clinic;
- requests are processed one after another;
- 429 when too many are queued, and 504 after 60 s;
- keys can be suspended for excessive requests.

Several Cloud Run instances serve one clinic at the same time, so per-instance pacing would overrun the limit. Retrying a booking after a timeout could create **two appointments**, against the pilot target of 0 double bookings, because Open Dental has no idempotency keys.

Plan §12 lists Open Dental limits and latency as a risk. The mitigations are caching config data, filler speech and a callback when it is unavailable.

PHI: responses contain patient data (P1-16) and even provider SSNs and birthdates (provider records), so the client must never log bodies or URLs, and the models must drop fields we don't need. P0-11 R12 (Open Dental key leak, High) also depends on the key never leaving the client.

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P1, Core Platform & Open Dental Adapter**.
- **What already exists:**
  - **P0-12:**
    - Remote API base `https://api.opendental.com/api/v1`; header `Authorization: ODFHIR {DeveloperKey}/{CustomerKey}`;
    - secrets `od-developer-key`, `od-customer-key-testdb`, `od-customer-key-<clinic_slug>` (prod, after the BAA);
    - test DB (A) (public, read-only use) and test DB (B) (our VM, seeded);
    - `smoke_test.py`, `seed_test_db.py`, seed files in `infra/dev/open-dental-test-db/seed/`.
  - **P1-01:** settings `OPEN_DENTAL_BASE_URL` and `OD_DEVELOPER_KEY` (SecretStr); `AppError`; Redis client.
  - **P1-02:** egress allow-list includes `api.opendental.com`; Scheduler module (this task adds one job).
  - **P1-03:** `clinics.od_customer_key_secret` (secret name), `clinics.timezone`.
  - **P1-05:** `sa-api` can read `od-*` secrets.
  - **P1-07:** `log` with event names, `stage_timer(Stage.OPENDENTAL_API, endpoint=…)`, `record_counter`, alert A6 on `opendental.error` / `opendental.rate_limited`.
  - **DECISIONS #84:** per-clinic customer keys are fetched at runtime by this task.
- **Open Dental API facts** (docs read 2026-11-24; https://www.opendental.com/site/apiimplementation.html and the resource pages):
  - **Throttle:**
    - one request per second per customer key when we have any permission beyond Read All (one per five seconds with Read All only);
    - "Requests for a given CustomerKey are processed sequentially";
    - 429 means "Too many requests are queued for processing. Retry the request after the time specified in the Retry-After response header";
    - 504 means a request did not finish "within the 60 second time limit".
  - **Status codes:**
    - 200, 201, 400, 401, 404, 410, 429 (and 504);
    - 400 covers several cases: eConnector problems, "The version of the dental office is not high enough", network issues and request timeouts, and request formatting errors;
    - 401 covers invalid keys and missing permissions.
  - **Pagination:** "Limit… defaults to the hard limit of 100 items"; use `Offset` until a page has fewer than 100 items.
  - **Formats:**
    - dates `yyyy-MM-dd`, datetimes `yyyy-MM-dd HH:mm:ss`, times `HH:mm:ss`;
    - booleans are the strings `"true"`/`"false"`; enums are text;
    - examples show numbers as strings, e.g. `"ProvNum": "3"`;
    - `Content-Type: application/json` is required;
    - request bodies can be up to 16.8M characters.
    - The docs don't say which time zone datetimes are in. **Verify** with test DB (B) that they are the office's local time.
  - **No idempotency keys and no webhooks** are documented.
  - **Endpoints used here** (minimum Open Dental version in brackets):
    - `GET /providers` (21.1; `ClinicNum`, `DateTStamp` 21.3);
    - `GET /operatories` (21.1; `ClinicNum`);
    - `GET /appointmenttypes` (22.4.10);
    - `GET /clinics` (21.1; empty list = the Clinics feature is not used);
    - `GET /schedules` (22.1; `date`, `dateStart`, `dateEnd`, `SchedType` = Practice/Provider/Blockout/Employee/WebSchedASAP, `ProvNum`; sorted by StartTime; `operatories` is a comma-separated string);
    - `GET /appointments/Slots` (21.1; `date`/`dateStart`/`dateEnd`, `lengthMinutes`, `ProvNum`, `OpNum` 22.1). It returns "entire open slots", and with several operatories it "only returns slots that are available in all operatories for that provider simultaneously".
  - **Minimum clinic version for this task: 22.4.10.** Check it against the clinic's version from P0-01 B1.

## 4. Scope
**In scope**
- **Package `backend/app/integrations/open_dental/`:**
  - `client.py`, `pacer.py`, `errors.py`, `parsing.py` (values, datetimes);
  - `keys.py` (customer key provider), `models.py` (setup models), `setup.py` (cached adapter), `context.py` (`ClinicODContext` and its provider interface).
- **`od_fake`:**
  - `backend/tests/fakes/od_fake/` (FastAPI app, seed loader, fault injection), with a `docker-compose` profile `fake`;
  - P1-16 extends it with patient and appointment write endpoints.
- **Contract tests** `backend/tests/contract/open_dental/`: run against the fake in CI and against test DB (B) nightly (marker `opendental`, serial; P1-06 job `od-integration`).
- **New Scheduler job `od-setup-refresh`** (daily, 09:00 UTC) through P1-02's scheduler module, with the handler `POST /internal/jobs/od-setup-refresh` (protected by P1-13's internal auth).
- **`POST /v1/admin/opendental/refresh`:** an endpoint for P4-11's "Refresh from Open Dental" button. It needs `CONFIG_WRITE` (P1-13).
- **A test that forbids other Open Dental access:** no `httpx`/`requests` call to the Open Dental host outside this package.
- **Docs:**
  - `docs/integrations/open-dental-client.md`: pacing, errors, retries, cache, version table;
  - an update to `open-dental-access.md` with the minimum version.

**Out of scope** (and which task covers it)
- Patient search/get/create and appointment get/create/update/break → P1-16 (uses this client, its write rules and `od_fake`)
- Turning schedules and slots into offerable options (rules, horizon, buffers) → P1-20
- Clinic config schema, including `open_dental.clinic_num` → P1-19 (this task defines how it is read)
- Reminder pre-send re-fetch logic → P4-04 (uses `Priority.BACKGROUND`)
- The admin console button UI → P4-11

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P0-12 (approved) | Keys, test DB (B), seed data | Build against `od_fake` (loads the seed CSVs). Test DB (B) is needed only for the nightly contract run. |
| P1-01 (approved) | Settings, errors, Redis | Use the skeleton. |
| P1-02 (approved) | Egress to `api.opendental.com`, Scheduler module | Local development uses the fake; dev deploy needs the egress rule. |
| P1-05 (approved) | Secret access for `sa-api` | Locally, `OD_CUSTOMER_KEY_OVERRIDE` (local only, see §6) or the fake (any key accepted). |
| P1-07 (approved) | Logging, `stage_timer`, counters | Use the spec signatures. |
| P1-19 Clinic config | `open_dental.clinic_num` and the clinic's IANA time zone source | `ClinicODContextProvider` has a simple implementation reading `clinics` (P1-03) and an optional env value; P1-19 replaces it. |

## 6. Interface contract

### Clinic context
```python
@dataclass(frozen=True, slots=True)
class ClinicODContext:
    clinic_id: uuid.UUID
    customer_key_secret: str            # clinics.od_customer_key_secret, e.g. "od-customer-key-testdb"
    tz: ZoneInfo                        # clinics.timezone, e.g. ZoneInfo("America/New_York")
    od_clinic_num: int | None           # Open Dental ClinicNum if the office uses Clinics; from config (P1-19)

class ClinicODContextProvider(Protocol):
    async def get(self, clinic_id: uuid.UUID) -> ClinicODContext: ...
```

### Customer key provider (`keys.py`)
```python
class CustomerKeyProvider:
    """Reads the customer key secret version 'latest' via the Secret Manager async client.

    Caches it in memory for 10 min per clinic. On 401 from Open Dental, call invalidate(clinic_id) once and retry
    that request once (the key may have been rotated).
    """
    async def get(self, ctx: ClinicODContext) -> SecretStr: ...
    def invalidate(self, clinic_id: uuid.UUID) -> None: ...
```
- `OD_CUSTOMER_KEY_OVERRIDE` (SecretStr) is allowed **only with `ENV=local`**, enforced by a `Settings` validator. In cloud environments, keys come only from Secret Manager.
- Prod customer keys exist only after the BAA (P0-12, P0-09). A missing secret raises `OpenDentalNotConfigured`.

### Priorities and pacing (`pacer.py`)
```python
class Priority(StrEnum):
    INTERACTIVE = "interactive"   # a patient or staff member is waiting
    BACKGROUND = "background"     # reminders, cache refresh, sweeps, nightly checks

class Pacer:
    async def acquire(self, clinic_id: uuid.UUID, priority: Priority, *, max_wait_s: float) -> PacerLease: ...
    async def penalize(self, clinic_id: uuid.UUID, retry_after_s: float) -> None: ...   # after a 429, all instances wait

@dataclass
class PacerLease:
    waited_ms: int
    async def release(self) -> None: ...   # decrements in-flight
```
The pacing works across all instances, through Redis keys driven by one Lua script:
- `od:pace:{clinic_id}`: the next allowed send time (ms);
- `od:inflight:{clinic_id}`: a counter with a lease TTL of 70 s;
- `od:waiting:{clinic_id}:interactive`: the number of interactive waiters.

Rules:
- **Spacing:** consecutive requests to one clinic start at least `OD_MIN_INTERVAL_MS` (1050 ms: 1 s plus a margin) apart.
- **In flight:** at most `OD_MAX_INFLIGHT` (2) requests in flight per clinic. Open Dental processes them sequentially, so more would only queue on their side and cause 429s.
- **Background requests:**
  - take a slot only when no interactive waiter exists;
  - are spaced at least `OD_BACKGROUND_INTERVAL_MS` (2000 ms) apart, so background work never takes more than about half the capacity;
  - may wait up to `OD_BACKGROUND_QUEUE_TIMEOUT_S` (120 s).
- **Interactive requests** wait at most `OD_INTERACTIVE_QUEUE_TIMEOUT_S` (10 s). After that, the call raises `OpenDentalQueueTimeout`, and the conversation offers a callback (P2 flows).
- **After a 429:** `penalize` pushes `od:pace` to now + `Retry-After` (or 2 s if the header is missing) for every instance.
- **If Redis is unavailable:** fall back to a local in-process pacer at `OD_MIN_INTERVAL_MS × 2` per instance, and log `opendental.pacer_degraded` (alert via the P1-07 log metric). It degrades safely rather than failing patients.

### Client (`client.py`)
```python
class OpenDentalClient:
    def __init__(self, *, settings: Settings, http: httpx.AsyncClient, pacer: Pacer,
                 keys: CustomerKeyProvider) -> None: ...

    async def get(self, ctx: ClinicODContext, path: str, *, endpoint: str,
                  params: Mapping[str, str | int] | None = None,
                  priority: Priority = Priority.INTERACTIVE) -> Any: ...

    async def get_all(self, ctx: ClinicODContext, path: str, *, endpoint: str,
                      params: Mapping[str, str | int] | None = None,
                      priority: Priority = Priority.INTERACTIVE, max_pages: int = 20) -> list[dict[str, Any]]: ...
        # pages with Offset=0,100,200… until a page has < 100 items; raises OpenDentalTooManyPages past max_pages

    async def post(self, ctx: ClinicODContext, path: str, *, endpoint: str, json: Mapping[str, Any],
                   priority: Priority = Priority.INTERACTIVE) -> Any: ...
    async def put(self, ctx: ClinicODContext, path: str, *, endpoint: str, json: Mapping[str, Any] | None = None,
                  priority: Priority = Priority.INTERACTIVE) -> Any: ...
```
- **`endpoint`** is a fixed name such as `"appointments.slots"` or `"providers.list"`. It is the only thing logged and used as a metric label. **The URL, path parameters, query parameters and bodies are never logged.** A query can contain a last name or a birthdate, as in P1-16's patient search.
- **Headers:** `Authorization: ODFHIR {dev}/{customer}`, `Content-Type: application/json`, `Accept: application/json`. The `httpx` client has `event_hooks` that never log and never echo headers.
- **Timeouts** (httpx): connect 5 s; read `OD_INTERACTIVE_TIMEOUT_S` (15 s) for interactive calls and `OD_BACKGROUND_TIMEOUT_S` (65 s, above Open Dental's 60 s) for background calls. A total deadline per call, including retries, is passed by the caller where needed (`asyncio.timeout`).
- **Retries:**

| Outcome | GET | POST / PUT |
|---|---|---|
| 429 | Penalize, wait `Retry-After`, retry (counts as an attempt) | Penalize; **no retry**: raise `OpenDentalUncertainWrite`, so the caller reads back first (P1-16). The docs suggest a 429 request was never queued, but we don't rely on that (DECISIONS #129) |
| 504, read timeout, connection reset after sending | Retry with backoff | **No retry**: raise `OpenDentalUncertainWrite` |
| Connect error / DNS (request never sent) | Retry with backoff | Retry once (nothing was sent) |
| 400 eConnector / network text | Retry once after 2 s, then `OpenDentalUnavailable` | No retry: `OpenDentalUncertainWrite` if the text indicates a timeout, else `OpenDentalUnavailable` |
| 401 | Invalidate key, retry once, then `OpenDentalAuthError` | Same (no data was written on 401) |
| Other 4xx | No retry | No retry |

  GET backoff: 0.5 s, 1 s, 2 s with ±20% jitter; at most `OD_GET_MAX_RETRIES` (3) retries, within the caller's deadline.
- **Response parsing:**
  - JSON only. A list endpoint must return a list, otherwise `OpenDentalProtocolError`.
  - Values are converted by `parsing.py` (below) inside the typed models, never by callers.

### Errors (`errors.py`, all `AppError` with fixed messages)
| Class | HTTP from Open Dental / cause | Retry by caller? | User-facing handling (P2) |
|---|---|---|---|
| `OpenDentalNotConfigured` | Secret missing / clinic not onboarded | no | callback |
| `OpenDentalAuthError` | 401 after key refresh | no; alert A6 | callback |
| `OpenDentalNotFound` | 404 | no | depends (e.g. AptNum gone) |
| `OpenDentalBadRequest` | 400 (format/validation) | no; bug | callback |
| `OpenDentalVersionTooLow` | 400 with "version of the dental office is not high enough" (**Verify** exact text) | no; alert | callback |
| `OpenDentalUnavailable` | 400 eConnector/network after retry; 5xx | later | callback |
| `OpenDentalRateLimited` | 429 after retries | later | filler + callback if persists |
| `OpenDentalTimeout` | GET timeouts / 504 after retries | later | callback |
| `OpenDentalQueueTimeout` | Pacer wait exceeded | later | callback |
| `OpenDentalUncertainWrite` | Write outcome unknown (504, timeout after send) | **never blindly**; P1-16 reconciles by reading back | "Let me check that…" then confirm or callback |
| `OpenDentalGone` | 410 (method deprecated) | no; alert | callback |
| `OpenDentalProtocolError` | Unexpected shape | no; alert | callback |

The 400 classification reads the response text in memory and keeps only a **reason code** (`econnector`, `version`, `network`, `format`, `unknown`). The text is discarded and never logged or stored, because it may echo input.

### Parsing (`parsing.py`)
```python
def od_bool(v: str | bool) -> bool: ...                 # "true"/"false" (case-insensitive) -> bool; else OpenDentalProtocolError
def od_int(v: str | int) -> int: ...                    # "3" -> 3
def od_date(v: str) -> date: ...                        # "yyyy-MM-dd"; "0001-01-01" -> treated as None by callers via od_date_opt
def od_local_dt(v: str, tz: ZoneInfo) -> datetime: ...  # "yyyy-MM-dd HH:mm:ss" in office local time -> aware UTC datetime
def to_od_date(d: date) -> str: ...
def to_od_local_dt(dt: datetime, tz: ZoneInfo) -> str: ...   # aware -> office local "yyyy-MM-dd HH:mm:ss"
```
DST rules for `od_local_dt`:
- **Ambiguous times** (the fall-back hour) use `fold=0`, the first occurrence, and log `opendental.ambiguous_time` (count only).
- **Non-existent times** (the spring-forward gap) raise `OpenDentalProtocolError` for writes. For reads, they shift forward by the gap and log `opendental.nonexistent_time`.

Assumption to **Verify** in test DB (B): the datetimes are the office's local time. Contract test C9 checks it by creating an appointment at a known local time (P1-16) and reading it back.

### Setup models (`models.py`; only the fields we need, everything else dropped)
```python
class Provider(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)
    prov_num: int; abbr: str; first_name: str; last_name: str; preferred_name: str | None
    is_hidden: bool; is_secondary: bool; specialty: str | None; clinic_restricted: bool | None = None
    # never kept: SSN, StateLicense, NationalProvID, Birthdate, FeeSched, SigOnFile, billing fields

class Operatory(BaseModel):
    op_num: int; name: str; abbrev: str; is_hidden: bool; is_hygiene: bool
    prov_dentist: int | None; prov_hygienist: int | None; clinic_num: int | None; is_web_sched: bool

class AppointmentType(BaseModel):
    appointment_type_num: int; name: str; is_hidden: bool; pattern: str   # time pattern, e.g. "/XX/" (Verify meaning: 5-min units)
    blockout_types: list[int]                                              # parsed from comma-separated string

class OdClinic(BaseModel):
    clinic_num: int; description: str; abbr: str; is_hidden: bool          # address/phone not kept (not needed)

class ScheduleBlock(BaseModel):
    schedule_num: int; date: date; start_utc: datetime; stop_utc: datetime
    sched_type: Literal["Practice", "Provider", "Blockout", "Employee", "WebSchedASAP"]
    prov_num: int | None; blockout_def_num: int | None; blockout_name: str | None
    op_nums: list[int]                                                     # from "operatories": "5,6"
    note_present: bool                                                     # the Note text is NOT kept (may name people)

class Slot(BaseModel):
    start_utc: datetime; end_utc: datetime; prov_num: int; op_num: int
```
Code uses one field per line (ruff). The semicolons above are only to keep this spec short.

### Setup adapter (`setup.py`)
```python
class SetupKind(StrEnum):
    PROVIDERS = "providers"
    OPERATORIES = "operatories"
    APPOINTMENT_TYPES = "appointment_types"
    CLINICS = "clinics"
    SCHEDULES = "schedules"

class OpenDentalSetup:
    async def providers(self, ctx: ClinicODContext, *, include_hidden: bool = False) -> list[Provider]: ...
    async def operatories(self, ctx: ClinicODContext, *, include_hidden: bool = False) -> list[Operatory]: ...
    async def appointment_types(self, ctx: ClinicODContext, *, include_hidden: bool = False) -> list[AppointmentType]: ...
    async def clinics(self, ctx: ClinicODContext) -> list[OdClinic]: ...
    async def schedules(self, ctx: ClinicODContext, start: date, end: date, *,
                        sched_type: str | None = None, prov_num: int | None = None,
                        priority: Priority = Priority.INTERACTIVE) -> list[ScheduleBlock]: ...
    async def open_slots(self, ctx: ClinicODContext, start: date, end: date, *, prov_num: int,
                         op_num: int | None = None, length_minutes: int | None = None) -> list[Slot]: ...  # never cached
    async def refresh(self, ctx: ClinicODContext, kinds: set[SetupKind] | None = None) -> RefreshReport: ...
    async def invalidate(self, clinic_id: uuid.UUID, kinds: set[SetupKind] | None = None) -> None: ...
```
| Data | Cache key | TTL | Notes |
|---|---|---|---|
| Providers, operatories, appointment types, clinics | `od:cache:{clinic_id}:{kind}:v1` | `OD_CACHE_TTL_CONFIG_S` = 21600 (6 h) | Passes `ClinicNum` when `od_clinic_num` is set; stale copy kept 24 h for fallback |
| Schedules | `od:cache:{clinic_id}:schedules:{start}:{end}:{sched_type}:{prov}:v1` | `OD_CACHE_TTL_SCHEDULES_S` = 600 (10 min) | Requests longer than 31 days are split into 31-day chunks, each cached; max range = booking horizon (DECISIONS #86, ≤ 365 days) |
| Slots, appointments, patients | — | not cached | Always live (double-booking risk) |

Behaviour:
- **Stale-on-error:** if a refresh of a config kind fails with `OpenDentalUnavailable`, `RateLimited`, `Timeout` or `QueueTimeout`, serve the stale copy (≤ 24 h old) and log `opendental.cache_stale_served`. Schedules are never served stale for more than 1 h.
- **Single-flight:** concurrent misses for the same key on one instance share one fetch. Across instances, a Redis lock `od:cache:lock:{key}` (10 s) lets one instance fetch while the others wait up to 3 s, then read the cache.
- **Metrics:** `record_counter("dai.od.cache", kind=…, result="hit"|"miss"|"stale")` and `dai.od.pacer_wait_ms` (histogram). Both are new names, added to P1-07's allowed metric list.
- **Invalidation and refresh paths:**
  1. the daily job `od-setup-refresh` (09:00 UTC; `Priority.BACKGROUND`; all active clinics);
  2. `POST /v1/admin/opendental/refresh` (staff `CONFIG_WRITE`; rate-limited to 1 per 5 min per clinic; audit `config.update` with `reason_code=od_refresh`);
  3. P1-19 calls `invalidate(clinic_id)` when the clinic config changes.

### `od_fake` (fake Open Dental for development and CI)
```bash
docker compose --profile fake up od-fake          # http://localhost:8090/api/v1
OPEN_DENTAL_BASE_URL=http://localhost:8090/api/v1 make dev
```
- **Data:**
  - loads `infra/dev/open-dental-test-db/seed/seed_patients.csv` and the setup fixtures (`seed_setup.yaml`: providers, operatories, appointment types, schedules for a rolling 60 days, clinics `[]`);
  - all synthetic, never real data.
- **Endpoints now:** the GET endpoints listed in §3, with Open Dental field names and string-typed values exactly like the docs' examples, and `Offset` paging at 100 items. P1-16 adds patients and appointments.
- **Behaviour like the real API:**
  - 1 request/s per customer key, giving 429 with `Retry-After: 1` when exceeded (can be turned off with `OD_FAKE_THROTTLE=false` for fast unit runs);
  - any `ODFHIR x/y` header is accepted, except `ODFHIR bad/bad` → 401.
- **Fault injection** through `POST /_fake/faults` (accepted only by the fake):
```json
{"endpoint":"appointments.slots","fault":"status","status":504,"times":1}
{"endpoint":"appointments.create","fault":"timeout_after_commit","times":1}
{"endpoint":"providers.list","fault":"status","status":400,"text":"eConnector is not running","times":2}
```
- **Contract tests** (`tests/contract/open_dental/`) assert response **shapes and semantics** (fields, types, paging, error codes). They run against the fake on every PR and against test DB (B) nightly. If the real API and the fake disagree, the nightly run fails, and the fake is fixed.

### Settings additions (extends P1-01)
```python
OD_CUSTOMER_KEY_OVERRIDE: SecretStr | None = None      # ENV=local only
OD_MIN_INTERVAL_MS: int = Field(default=1050, ge=1000)
OD_BACKGROUND_INTERVAL_MS: int = Field(default=2000, ge=1000)
OD_MAX_INFLIGHT: int = Field(default=2, ge=1, le=4)
OD_INTERACTIVE_QUEUE_TIMEOUT_S: float = 10.0
OD_BACKGROUND_QUEUE_TIMEOUT_S: float = 120.0
OD_INTERACTIVE_TIMEOUT_S: float = 15.0
OD_BACKGROUND_TIMEOUT_S: float = 65.0
OD_GET_MAX_RETRIES: int = Field(default=3, ge=0, le=5)
OD_CACHE_TTL_CONFIG_S: int = 21600
OD_CACHE_TTL_SCHEDULES_S: int = 600
```

### Log events (all through P1-07; fields from its allow-list only)
| Event | Fields |
|---|---|
| `opendental.request` | `endpoint`, `status_code`, `duration_ms`, `attempt`, `queue` (= priority: `interactive`/`background`), `clinic_id` |
| `opendental.rate_limited` | `endpoint`, `retry_after_s`, `attempt`, `clinic_id` |
| `opendental.error` | `endpoint`, `error_code` (class name), `reason_code`, `clinic_id` |
| `opendental.uncertain_write` | `endpoint`, `clinic_id` |
| `opendental.cache_stale_served` | `endpoint`, `clinic_id` |
| `opendental.pacer_degraded` | `clinic_id` |

## 7. Implementation guide
1. **Read** P0-12 (keys, test DBs, seed), DECISIONS #84 and #86, P1-07 (logging, metrics), P1-13 (internal auth, `require`), and the Open Dental pages in §15. **Verify** the time zone assumption, and the 400 texts, using test DB (B) and vendor relations. Record the results in `open-dental-client.md`.
2. **`parsing.py` and `errors.py`** with unit tests (T1–T4).
3. **`od_fake`:**
   - seed loader and GET endpoints, paging, throttle, faults;
   - the compose profile.

   Write it early, because P1-16, P1-20 and P2 depend on it.
4. **`pacer.py`:**
   - the Lua script, priorities, penalize, degraded mode;
   - tests with real Redis (T5–T8), including a two-process test.
5. **`client.py`:**
   - auth header, timeouts, retry table, 400 classification, pagination, key invalidation on 401;
   - tests against the fake and `respx` (T9–T13).
6. **`keys.py`** with Secret Manager. Mock it in unit tests and check it in dev.
7. **`setup.py`:**
   - models, cache, stale-on-error, single-flight, chunked schedules, invalidation;
   - the internal job, the admin refresh endpoint, the scheduler job via P1-02 tfvars (T14–T17).
8. **Contract suite C1–C10:** run it against the fake in CI, and against test DB (B) by hand once (then nightly via P1-06).
9. **Boundary test** T18: no other module may call the Open Dental host.
10. **Docs, and notify:**
    - P1-16: client, write rules, `UncertainWrite`, fake extension points;
    - P1-19: `open_dental.clinic_num`, invalidation hook;
    - P1-20: setup adapter, slot semantics, schedule chunks, horizon;
    - P2 flows: error-to-callback mapping;
    - P4-04: background priority;
    - P4-11: refresh endpoint;
    - P6-01: minimum version 22.4.10;
    - P1-07: new metric names and events.

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| Two instances call Open Dental for the same clinic at once | Shared Redis pacer spaces them ≥ 1050 ms; at most 2 in flight. |
| A reminder sweep runs while a patient is booking | Background calls wait while interactive waiters exist; booking calls go first. |
| 429 storm (e.g. clinic staff tool also using the API, or Open Dental slow) | Penalize all instances by `Retry-After`; interactive calls past 10 s raise `QueueTimeout` → callback; alert A6. |
| A booking `POST` times out | `OpenDentalUncertainWrite`; P1-16 reads the patient's appointments to find the new one before saying anything to the patient. Never re-POST blindly. |
| eConnector at the office is offline (office computer off) | 400 classified `econnector` → `OpenDentalUnavailable` after one retry; config served stale from cache; patient gets callback path; alert A6 if repeated. |
| Clinic's Open Dental version too old for an endpoint | `OpenDentalVersionTooLow`; alert; onboarding check (P6-01) should have caught it. |
| Customer key rotated or disabled by the office | 401 → key cache invalidated → retry once → `OpenDentalAuthError` → alert; P6 runbook to re-enable. |
| A list has exactly 100 items | Client fetches the next page; empty page ends paging. |
| Schedule request for 120 days (booking horizon 120) | Split into four 31-day chunks (the last shorter), each paced and cached. |
| DST change day | Ambiguous/non-existent local times handled per `parsing.py` rules; contract test C9 covers a DST date in test DB (B). |
| Provider record contains SSN, birthdate | Dropped by the model (`extra="ignore"` + explicit field list); never cached or logged (T15). |
| Schedule `Note` contains a staff name or reason | Not kept (`note_present` only). |
| Redis down | Pacer degraded mode (local, slower); cache bypassed (live reads, paced); `opendental.pacer_degraded` logged. |
| Open Dental returns HTML or an unexpected shape | `OpenDentalProtocolError`; nothing logged from the body; alert. |
| Someone adds a direct `httpx.get("https://api.opendental.com/...")` elsewhere | T18 fails in CI. |

## 9. Security, HIPAA and PHI
- **PHI handled:** this task's own endpoints (setup data) carry no patient PHI. Provider records include provider SSN and birthdate, which are sensitive personal data and are dropped at parsing. The client transports patient PHI for P1-16, so the client-level rules apply to everything:
  - **never log** URLs, query strings, path parameters, request or response bodies, headers, or customer/developer keys;
  - only the fixed `endpoint` name, status codes, timings and counts are logged.
- **Storage:**
  - only setup data is cached, in Redis (TLS, AUTH, CMEK; P1-02), with the minimal fields;
  - the schedule `Note` text is not kept;
  - no patient data is cached by this task (P1-16 follows the same rule: no patient caching).
- **Keys:**
  - the developer key comes from `OD_DEVELOPER_KEY` (Secret Manager env);
  - customer keys are fetched at runtime per clinic, kept in memory for 10 min, and never in Redis, the database or logs;
  - the local override works only with `ENV=local`;
  - prod clinic keys exist only after the BAA (P0-09).
- **Network:** egress only to `api.opendental.com` through the FQDN allow-list (P1-02), over TLS 1.2+ (httpx default; `verify=True` always).
- **`od_fake`** uses synthetic data only and is never deployed to staging or prod. Its compose profile is local and CI only, and a deploy-time check refuses `OPEN_DENTAL_BASE_URL` values that aren't `https://api.opendental.com/...` when `ENV` is staging or prod.
- **Risks reduced:** P0-11 R12 (key leak), R01 (PHI in logs via the client).

## 10. Testing
Unit tests (`backend/tests/unit/open_dental/`):

| # | Test | Expected |
|---|---|---|
| T1 | `od_bool("TRUE")`, `od_bool("no")`, `od_int("3")` | True; `OpenDentalProtocolError`; 3 |
| T2 | `od_local_dt("2026-11-01 01:30:00", America/New_York)` (ambiguous) and `"2026-03-08 02:30:00"` (non-existent) | First occurrence (EDT) as UTC; read → shifted to 03:30 local, write → error |
| T3 | 400 texts "eConnector is not running", "The version of the dental office is not high enough", "Missing header" | `econnector`→Unavailable, `version`→VersionTooLow, `format`→BadRequest; the text not present in any log or exception string |
| T4 | Every error class message | Fixed text, no placeholders |
| T5 | Pacer: 5 interactive acquires for one clinic | Start times ≥ 1050 ms apart |
| T6 | Pacer: background and interactive waiting together | Interactive granted first; background spacing ≥ 2000 ms |
| T7 | Pacer across **two processes** sharing Redis (10 requests each) | Combined spacing ≥ 1050 ms; never > 2 in flight |
| T8 | `penalize(3 s)` then acquire from another instance; Redis stopped | Waits ≥ 3 s; degraded local pacer used and `opendental.pacer_degraded` logged |

Client tests against `od_fake` and `respx`:
| # | Test | Expected |
|---|---|---|
| T9 | GET with 504 once, then 200 | Returns data; 2 attempts logged |
| T10 | POST with `timeout_after_commit` fault | `OpenDentalUncertainWrite`; **exactly one** POST reached the fake |
| T11 | 429 with `Retry-After: 2` on GET; on POST | GET waits ≥ 2 s and retries; POST is **not** retried, raises `OpenDentalUncertainWrite`, exactly one POST reached the fake, pacer penalized |
| T12 | 401 then 200 after key invalidation | One retry with a refreshed key; then `OpenDentalAuthError` if 401 again |
| T13 | `get_all` on 250 schedules | 3 requests with `Offset=0,100,200`; 250 items |
| T14 | `providers()` twice within TTL | 1 request; metrics hit=1, miss=1 |
| T15 | Provider fixture with SSN and Birthdate | Model has no such attributes; cache JSON contains neither value |
| T16 | Refresh fails with `OpenDentalUnavailable` while a 3 h old cache exists | Stale data returned; `opendental.cache_stale_served` logged |
| T17 | `schedules(start, start+120 days)` | 4 chunks; each cached separately |
| T18 | **Boundary:** AST/grep scan for `api.opendental.com` and `ODFHIR` outside `integrations/open_dental/` and tests | None |
| T19 | Settings: `OD_CUSTOMER_KEY_OVERRIDE` with `ENV=dev`; staging with a non-Open-Dental base URL | `ValidationError` both |

Contract tests C1–C10 (fake in CI; test DB (B) nightly, serial):
- C1: providers list shape;
- C2: operatories, filtered by `ClinicNum` when set;
- C3: appointment types (22.4.10+);
- C4: clinics, where empty means no Clinics feature;
- C5: schedules by date range, each `SchedType`;
- C6: slots by provider and date range, `lengthMinutes` filter;
- C7: paging at 100;
- C8: 401 with a bad key;
- C9: local time round-trip, including a DST date (needs P1-16's appointment create; skipped until then);
- C10: 429 behaviour, observed by sending 3 requests at once (nightly only, run once).

## 11. Acceptance criteria
- [ ] All Open Dental calls go through `OpenDentalClient` (T18); the auth header uses the developer key and the clinic's customer key fetched at runtime; keys never appear in logs, Redis or the DB
- [ ] Pacing is shared across instances via Redis: ≥ 1050 ms spacing, ≤ 2 in flight, interactive before background, 429 penalizes all instances, safe degraded mode (T5–T8)
- [ ] GETs retry per the table; writes are never retried after they may have reached Open Dental and raise `OpenDentalUncertainWrite` (T9–T12)
- [ ] Errors are the typed classes in §6 with fixed messages; 400 reasons are classified without keeping the text (T3, T4)
- [ ] Paging, value parsing and local-time conversion with DST rules work (T1, T2, T13)
- [ ] The setup adapter returns minimal typed models (no provider SSN/birthdate, no schedule notes), caches config 6 h and schedules 10 min, never caches slots, serves stale on errors, and records hit/miss metrics (T14–T17)
- [ ] Refresh works via the daily `od-setup-refresh` job, the admin refresh endpoint and the `invalidate` hook
- [ ] `od_fake` runs with the seed data, throttle and fault injection; contract tests C1–C8 pass against it in CI and against test DB (B) at least once (then nightly)
- [ ] `open-dental-client.md` documents pacing, retries, errors, cache, the verified facts and the minimum version 22.4.10; the §7 step 10 issues are notified

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI (T1–T19, C1–C8 on the fake)
- [ ] PR reviewed (HIPAA review if labelled `phi`): labelled `phi`; tech lead + compliance owner review logging and key handling
- [ ] No PHI in logs: client logs only endpoint names, status codes and timings (checked with P1-07's leak suite using a patient-search URL with a name and DOB in the query)
- [ ] Docs / README updated: `open-dental-client.md`, `open-dental-access.md` (version), README "Running with the fake Open Dental"

## 13. Hand-off
| Task | Can rely on |
|---|---|
| P1-16 Patient and appointment adapters | `OpenDentalClient` (`get`, `get_all`, `post`, `put`), retry rules, `OpenDentalUncertainWrite` to reconcile, `parsing.py`, `od_fake` to extend with patients/appointments and the `timeout_after_commit` fault |
| P1-19 Clinic config | Must provide `open_dental.clinic_num` and call `OpenDentalSetup.invalidate()` on change; implements `ClinicODContextProvider` |
| P1-20 Availability engine | `providers`, `operatories`, `appointment_types`, `schedules` (chunked, cached), `open_slots` (live); slot semantics from the docs |
| P2 flows | Error classes → callback mapping; `QueueTimeout` after 10 s |
| P4-04 Reminders | `Priority.BACKGROUND` for pre-send re-fetches |
| P4-11 Policies screens | `POST /v1/admin/opendental/refresh` |
| P1-06 CI | Nightly `od-integration` = contract suite against test DB (B), serial |
| P1-07 Observability | Events in §6, metrics `dai.od.cache`, `dai.od.pacer_wait_ms` |
| P6-01 Onboarding | Minimum Open Dental version 22.4.10; eConnector must be running; customer key enabled after the BAA |

## 14. Open questions
| Question | Owner | Needed by |
|---|---|---|
| Are Remote API datetimes always in the office's local time (and what happens on DST days)? | Tech lead (test DB (B) + vendor relations) | Step 1 |
| Exact 400 message texts for eConnector-down and version-too-low | Tech lead (test DB (B)) | Step 2 |

## 15. References
- Plan §4.4, §4.5, §4.6, §8 Phase 1, §12
- Open Dental API implementation (throttling, paging, status codes, formats): https://www.opendental.com/site/apiimplementation.html
- Providers: https://www.opendental.com/site/apiproviders.html
- Appointment types: https://www.opendental.com/site/apiappointmenttypes.html
- Schedules: https://www.opendental.com/site/apischedules.html
- Operatories: https://www.opendental.com/site/apioperatories.html
- Clinics: https://www.opendental.com/site/apiclinics.html
- Appointments (Slots): https://www.opendental.com/site/apiappointments.html
- API setup and keys: https://www.opendental.com/site/apisetup.html
- httpx timeouts and transports: https://www.python-httpx.org/advanced/timeouts/
- respx: https://lundberg.github.io/respx/
- Related tasks: P0-01, P0-09, P0-11, P0-12, P1-01, P1-02, P1-05, P1-06, P1-07, P1-13, P1-16, P1-19, P1-20, P2-16, P2-18, P2-22, P4-04, P4-11, P6-01
