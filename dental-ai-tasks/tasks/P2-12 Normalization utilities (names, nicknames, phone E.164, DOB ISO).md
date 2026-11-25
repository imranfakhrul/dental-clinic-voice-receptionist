---
id: P2-12
title: Patient identification and verification (normalization, candidate matching, no-oracle verification flow)
milestone: P2
epic: E2.3
size: L
labels: area:ai, area:backend, area:security, type:feature, phi
depends_on: P0-01, P0-04, P1-13, P1-16, P1-19, P1-22, P2-01, P2-04, P2-05, P2-08
status: approved
---

# P2-12: Patient identification and verification (normalization, candidate matching, no-oracle verification flow)

## 1. Summary
Find a returning patient in Open Dental and prove the person in the chat is that patient, following plan §4.5 and the clinic's policy (P0-01 Q1: full name + DOB + one of mobile phone or ZIP; never phone alone). This task absorbs **P2-13 (candidate matching and scoring)** and **P2-14 (verification flow)**.

It delivers:
1. **Normalization utilities** for names (case, accents, punctuation, suffixes, nicknames), DOB from typed and spoken forms, and phones from spoken digits. P2-05 and P2-15 reuse them.
2. **Candidate matching and scoring** behind the `search_patient` tool (replacing P1-22's interim rule): `strong`, `partial`, `multiple`, `none`, `blocked_status`.
3. **The real `verify_patient` handler** (replacing P1-22's stub) and `mark_verified`.
4. **IDENTIFY and VERIFY state handlers** with a **no-oracle** design (DECISIONS #181): all identifiers are collected **before** any search result is used, search and verification run in the same turn, and every failure (no record, wrong phone, wrong spelling) gets the **same** neutral reply. Nobody can learn whether a person is a patient here without proving it.

Done means:
- a patient who gives the right name, DOB and phone (or ZIP) is verified in one turn;
- a wrong or unknown person gets identical replies whether or not a record exists;
- phone alone never verifies; ambiguous or archived matches never auto-create and go to a callback;
- after `verification.max_attempts` (3) failures the session is locked and only a callback is offered.

## 2. Why this matters
Plan §4.5 requires: normalize, search by last name + DOB and by phone, score candidates, verify with at least two identifiers, never auto-create on ambiguity, and "don't reveal record details before verification (avoid confirming 'yes, you're a patient here' to an unverified caller)".

Everything patient-specific depends on this: seeing, booking, rescheduling and cancelling appointments (P2-08 guard `verified`). A weak check exposes appointments to strangers (a HIPAA breach); a strict but leaky check still tells strangers who is a patient; a sloppy match creates duplicate charts. Pilot targets helped: **0 duplicate patients**, 0 disclosures before verification, and ≥ 70% bookings without callback (returning patients verified in one turn).

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P2, Text Chat Receptionist**.
- **Terms:**
  - **Identification** = finding which Open Dental record(s) could be this person. **Verification** = proving the person is that record's patient with the clinic's required identifiers.
  - **Oracle:** any difference in the AI's behaviour that tells an unverified person whether a record exists. GLOSSARY "Verification oracle".
  - **Jaro-Winkler similarity:** a 0–1 string similarity that favours matching prefixes, good for typos in short names. GLOSSARY "Jaro-Winkler".
- **What already exists:**
  - **P1-16** (approved): `search_by_name_dob(ctx, last_name, birthdate)` and `search_by_phone(ctx, phone_e164)` returning exact matches (normalized), all statuses except Deceased, as `PatientRecord(pat_num, first_name, last_name, preferred_name, birthdate, phones_e164, email, status, counts_as_existing, clinic_num)`; `get(ctx, pat_num)`; `TooManyMatchesError`; `phone_search_mode`. **Additive change here:** `PatientRecord.zip5: str | None` (first 5 digits of the address ZIP, in memory only, never stored or logged; **Verify** the Open Dental field name for the ZIP in the Patients resource).
  - **P1-22** (approved): `search_patient` (input `last_name`, `dob`, `first_name?`, `phone?`; output `{outcome: no_match|verify|ambiguous, ask_for}`; stores the candidate list `cand` and `search_fp`), `verify_patient` stub (input `answers: {mobile_phone?, zip_code?, first_name?}`, output `{verified, attempts_left}`), `create_patient` precondition (`cand.outcome == "no_match"` with the same fingerprint), audit `patient.search`, `patient.verify`, `patient.verify_failed`.
  - **P1-13** (approved): `mark_verified(session_id, patnum)`, `record_verify_attempt(session_id) -> int` (locks the session after 3 failures: `verification_locked`).
  - **P1-19** (approved): `verification.required: [full_name, dob]`, `verification.one_of: [mobile_phone, zip_code]`, `verification.max_attempts: 3` (all file-only). **Additive here:** `verification.first_name_match`.
  - **P0-04** (approved): `IDENTIFY` collects `first_name`, `last_name`, `dob`, `phone`; `VERIFY` collects an extra identifier (`zip`); events `match_strong`, `match_partial`, `match_multiple_unresolved`, `match_none_confirmed`, `verified`, `verify_attempt_limit`.
  - **P2-01 / P2-04 / P2-05 / P2-08** (approved): handler registry and `HandlerResult`; reply templates and facts; extraction of names, DOB, phone, ZIP; gateway guard `verified` and budgets (`search_patient` 5, `verify_patient` 5 per session).

## 4. Scope
**In scope**
- **`backend/app/domain/patients/normalize.py`:** `normalize_name`, `name_key`, `first_name_matches`, `parse_dob`, `parse_phone`, nickname table loader; data file `backend/app/domain/patients/data/nicknames.csv`.
- **`backend/app/domain/patients/matching.py`:** `MatchQuery`, `score_candidates()` → `MatchResult`.
- **`backend/app/domain/patients/verification.py`:** `check_identifiers()`.
- **Tool handlers:** the scoring part of `search_patient` (P1-22 step 3) and the real `verify_patient` (`register(..., replace_stub=True)`).
- **Flow handlers** `backend/app/orchestrator/flows/identify.py`: `IdentifyHandler`, `VerifyHandler` (P2-01 `StateHandler`), reply intents and templates (added to P2-04's catalogue).
- **Additive changes:** `PatientRecord.zip5` (P1-16); `verification.first_name_match` (P1-19, file-only); guard `not_verification_locked` added to P2-08's `create_patient` preconditions.
- **Tests** (unit, handler, no-oracle suite) and `docs/identification.md`.

**Out of scope** (and which task covers it)
- New-patient registration flow and its card → P2-15
- Open Dental search calls themselves → P1-16
- Extraction prompts and schema → P2-05
- Session lock mechanics and rate limits → P1-13
- Callback case creation → P2-22
- Voice spelling mode (letter by letter) → P3-09

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P1-16 (approved) | Searches, `get`, `PatientRecord` | `od_fake` (P1-15) with seeded synthetic patients (§10 fixture) |
| P1-22 (approved) | `search_patient`, `verify_patient` contracts, handle store | Use the contracts; replace the stub via `register(replace_stub=True)` |
| P1-13 (approved) | `mark_verified`, `record_verify_attempt` | Fakeredis-backed session store fixture |
| P1-19 (approved) | `verification` section | Seed config `seed/example-dental/` |
| P2-01, P2-04, P2-05, P2-08 (approved) | Handlers, templates, extraction, gateway | Their fakes and in-memory stores |
| P0-01 Q1 (answered) | Clinic identifier policy | Already in the seed config |

## 6. Interface contract

### Normalization (`normalize.py`)
```python
def normalize_name(s: str) -> str: ...
    # NFKD + strip accents; casefold; ’ ‘ ` → '; remove characters other than letters, space, hyphen, apostrophe;
    # collapse spaces; trim. "  O’Brien-Smith " -> "o'brien-smith"
def name_key(s: str) -> str: ...
    # normalize_name, then drop suffixes (jr, sr, ii, iii, iv) and all spaces/hyphens/apostrophes:
    # "O'Brien Jr." -> "obrien"   (used for comparisons, never stored)
def first_name_matches(given: str, record_first: str, record_preferred: str | None,
                       mode: Literal["exact", "nickname", "fuzzy"]) -> bool: ...
    # exact: name_key equal (to first or preferred name)
    # nickname: exact OR same nickname group ("bob" ~ "robert", "liz" ~ "elizabeth")
    # fuzzy: nickname OR Jaro-Winkler(name_key) >= 0.92 and both keys >= 3 chars
def parse_dob(text: str, *, today: date) -> date | None: ...
    # ISO; US M/D/YYYY and M/D/YY ("5/3/90" -> 1990-05-03; YY > today's YY -> 19YY else 20YY);
    # "May 3 1990", "3rd of May 1990", "05031990"; spoken "may third nineteen ninety"; None if ambiguous or invalid
def parse_phone(text: str) -> str | None: ...
    # digits and spoken digits ("five five five oh one two three"; "oh" = 0; "double five" = 55) -> E.164 US via phonenumbers
```
- **Nickname table:** `nicknames.csv` with rows `canonical,variant` (e.g. `robert,bob`), built from a public dataset of US English given-name nicknames (Proposed: the `carltonnorthern/nicknames` CSV; **Verify** its license allows commercial use, else build our own list of ≈ 300 common names), reviewed by the team, versioned in the repo. Groups are symmetric (`bob` ~ `rob` ~ `robert`).
- **Jaro-Winkler:** from `rapidfuzz` (`rapidfuzz.distance.JaroWinkler.normalized_similarity`; **Verify** the function name in the pinned version).
- **Reuse:** P2-05's normalizers call `normalize_name`, `parse_dob` (when the model's value isn't ISO) and `parse_phone`; P2-15 uses them for registration.

### Matching (`matching.py`)
```python
class MatchQuery(BaseModel):
    model_config = ConfigDict(frozen=True)
    first_name: str
    last_name: str
    dob: date
    phone: str | None = None        # E.164
    zip5: str | None = None

class MatchOutcome(StrEnum):
    STRONG = "strong"                # exactly one existing-status record with last name + DOB + first name match
    MULTIPLE = "multiple"            # more than one such record (twins, duplicates in Open Dental)
    PARTIAL = "partial"              # records found, but not a strong match (first name differs, phone-only match)
    NONE = "none"                    # no records by name+DOB or phone
    BLOCKED_STATUS = "blocked_status"  # a strong match whose status doesn't count as existing (Archived, Prospective…)

class MatchResult(BaseModel):
    outcome: MatchOutcome
    strong_pat_nums: tuple[int, ...] = ()    # stays server-side (handle store), never returned to the model
    any_records: bool                        # for duplicate prevention only; never shown

async def score_candidates(q: MatchQuery, *, patients: PatientAdapter, ctx: ClinicODContext,
                           policy: VerificationPolicy) -> MatchResult: ...
```
**Algorithm (Proposed, DECISIONS #182):**
1. `A = search_by_name_dob(last_name, dob)` (exact last name after normalization, exact DOB). `P = search_by_phone(phone)` if a phone was given. `TooManyMatchesError` from either → `MULTIPLE`.
2. `strong = [r for r in A if first_name_matches(q.first_name, r.first_name, r.preferred_name, policy.first_name_match)]`.
3. If any `r in strong` has `counts_as_existing=False` → `BLOCKED_STATUS` (never create a new chart next to an archived one; P1-16).
4. `len(strong) == 1` → `STRONG`; `> 1` → `MULTIPLE`.
5. `strong` empty and (`A` or `P` non-empty) → `PARTIAL`.
6. Otherwise → `NONE`.

The last name is compared exactly (Open Dental's search is exact); a misspelt last name gives `NONE` or `PARTIAL` (phone hit), and the retry asks for the spelling.

### Identifier check (`verification.py`)
```python
class VerifyAnswers(BaseModel):
    mobile_phone: str | None = None   # E.164
    zip_code: str | None = None       # 5 digits

def check_identifiers(records: Sequence[PatientRecord], answers: VerifyAnswers,
                      policy: VerificationPolicy) -> PatientRecord | None: ...
    # Name and DOB already matched (required: [full_name, dob]).
    # A record passes if ANY one_of identifier matches:
    #   mobile_phone: answers.mobile_phone in record.phones_e164   (any phone on file; DECISIONS #183)
    #   zip_code:     answers.zip_code == record.zip5
    # Returns the single passing record, or None if zero or more than one pass.
```
Phone alone never verifies: `check_identifiers` is only called on records that already matched last name + DOB + first name.

### Tool handlers
**`search_patient`** (replaces P1-22 step 3; inputs and outputs unchanged):
- runs `score_candidates`; stores `cand = {outcome, strong_pat_nums}` and `search_fp` in the handle store;
- maps to the P1-22 output: `STRONG` / `MULTIPLE` → `verify`; `NONE` → `no_match`; `PARTIAL` / `BLOCKED_STATUS` → `ambiguous`; `ask_for = policy.one_of`;
- audit `patient.search` (P1-22) with `match_count` bucketed (`0`, `1`, `2+`) and `identifiers_used`.

**`verify_patient`** (real handler):
1. Requires `cand.outcome in {STRONG, MULTIPLE}`; otherwise returns `{verified: false}` **without** revealing why (and still counts an attempt, see below).
2. `records = [patients.get(ctx, n) for n in strong_pat_nums]` (in memory only).
3. `rec = check_identifiers(records, answers, policy)`.
4. Pass → `mark_verified(session_id, rec.pat_num)`; audit `patient.verify` (`SUCCESS`, `identifiers_used`); output `{verified: true, attempts_left}`.
5. Fail → `attempts = record_verify_attempt(session_id)`; audit `patient.verify_failed`; output `{verified: false, attempts_left: max_attempts - attempts}`.
6. Locked session (P1-13 403 `verification_locked`) → envelope error `verification_locked`, `next="callback"`.

### Flow handlers and the no-oracle sequence (DECISIONS #181)
```text
IDENTIFY.on_turn:
  missing = slots.missing_for("IDENTIFY")             # first_name, last_name, dob, phone
  if missing: reply ask_missing (one at a time); return
  # all four collected (phone may be replaced by zip on a retry)
  tool_calls: search_patient(last_name, dob, first_name, phone)
  on result:
    verify            -> event match_strong            -> VERIFY.on_enter runs in the same turn
    no_match          -> if flags.new_patient_declared: event match_none_confirmed (-> REGISTER, P2-15)
                         else: failure()               # neutral; counts an attempt
    ambiguous         -> failure()                     # neutral; counts an attempt

VERIFY.on_enter (same turn, no patient-visible step in between):
  tool_calls: verify_patient(answers={mobile_phone: slots.phone, zip_code: slots.zip})
    verified=true     -> event verified -> resume the intent's next state (APPOINTMENT_TYPE, CHECK_APPOINTMENT, ...)
    verified=false    -> back to IDENTIFY with failure()
    verification_locked -> event verify_attempt_limit -> CALLBACK_REQUEST

failure():
  attempt n (n = attempts so far, counted once per failed identifier set):
    n == 1 -> reply identify_retry       (same text whatever the cause); clear last_name, dob, phone; keep first_name
    n == 2 -> reply identify_new_or_returning; patient says new -> flags.new_patient_declared=True -> match_none_confirmed
                                               patient says returning -> identify_retry
    n >= max_attempts -> verify_attempt_limit -> CALLBACK_REQUEST (reply verify_locked)
```
- For `NONE`, `PARTIAL` and `BLOCKED_STATUS`, the handler calls `record_verify_attempt` itself so every failed identifier set counts the same as a wrong phone (no timing or counting difference).
- **New patient declared up front** ("it's my first visit"): IDENTIFY still collects and searches (duplicate prevention). `NONE` → `match_none_confirmed` with no failure message. Any other outcome → still `match_none_confirmed`; P2-15's `create_patient` then fails P1-22's duplicate precondition (`duplicate_risk`) and the patient gets P2-15's neutral "our team will finish your registration" callback. No attempt is counted for a declared new patient.
- **Locked session:** `create_patient` is denied by the new guard `not_verification_locked` (added to P2-08's precondition table), so failing to impersonate someone can't be followed by registering a duplicate.
- **`MULTIPLE` that the identifier can't resolve** (zero or several records pass) → treated as a failure; after the limit → callback (never guess between twins). If the patient says they are new while `MULTIPLE` exists → P2-15 duplicate precondition → callback.
- `BLOCKED_STATUS` (archived chart) is indistinguishable from other failures to the patient; when it ends in a callback, the case reason is `identity_needs_staff` so staff reactivate the chart.

### Household: several patients in one chat (DECISIONS #185)
A parent (or any verified person) can act for family members in the same chat:
1. The active person must be verified (or just registered). The patient says "I also want to book for my son" → extraction proposes `add_patient` (P0-04 global event) → `start_new_person(session_id)` (P1-13), a new empty person frame (P2-01) becomes active, state `IDENTIFY`, reply `add_patient_intro`.
2. The child is identified and verified exactly like anyone else: name + DOB + one of phone or ZIP on **the child's** record (often the parent's phone). An Open Dental guarantor link to the parent is **not** required. The no-oracle rules, templates and neutral failures are unchanged.
3. **Attempts are per session, shared by all persons** (P1-13 counter), so "adding a child" can't be used to try more identities. Search budgets are per person and capped per session (P2-08).
4. On success `mark_verified` adds the PatNum to `household` and makes it active; reply `active_patient_switched`.
5. A new child who isn't in Open Dental is registered through P2-15 in the same chat (contact phone may be the parent's); linking the parent as guarantor is left to staff, noted in the admin email.
6. `switch_patient` ("back to my appointment") calls `switch_active` to an earlier household member; no re-verification. Appointment handles and offered slots of the previous person are cleared (P1-22 handles; the P1-20 offer store `avail:{session_id}` is deleted on every switch).
7. Every confirmation card's first row names the patient, and the P2-08 operation hash includes that person's PatNum, so a yes for the child's card can never write to the parent's record.
8. Maximum 4 persons per chat → `household_full`.

### Reply intents and templates (added to P2-04's `templates.yaml`)
| Intent | Text |
|---|---|
| `identify_intro` | "To look up your details, I'll need your first and last name, date of birth and phone number." |
| `identify_retry` | "I wasn't able to confirm those details. Let's double-check: could you spell your last name and give me your date of birth again? You can also give me your home ZIP code instead of your phone number." |
| `identify_new_or_returning` | "I still can't confirm those details. Have you visited us before, or would this be your first visit?" |
| `verified_ok` | "Thanks, {first_name}. I've confirmed your details." |
| `verify_locked` | "I'm sorry, I wasn't able to confirm your details. I'll ask our team to call you back to help." |
| `add_patient_intro`, `active_patient_switched`, `household_full` | Household templates in P2-04 (DECISIONS #185) |

`identify_retry` and `identify_new_or_returning` are identical for every failure cause. They are templates (P2-03 R1), never LLM text.

### Config extension (P1-19, file-only)
```yaml
verification:
  required: [full_name, dob]
  one_of: [mobile_phone, zip_code]
  max_attempts: 3
  first_name_match: fuzzy        # exact | nickname | fuzzy (default fuzzy; DECISIONS #184)
```

### Logs and metrics (no names, DOBs, phones, PatNums)
| Item | Fields |
|---|---|
| `identify.outcome` (info) | `outcome` (`strong` / `multiple` / `partial` / `none` / `blocked_status`), `identifiers_used`, `turn_seq` |
| `identify.verify` (info) | `result` (`verified` / `failed` / `locked`), `attempt`, `identifier` (`mobile_phone` / `zip_code`) |
| `dai.identify.outcome` (counter) | `outcome` |
| `dai.identify.verify` (counter) | `result` |

### Example
Seeded `od_fake`: PatNum 812 "Robert Jones", DOB 1980-02-11, phones `+15035550142`, ZIP 97201, status Patient.
- Patient: "Bob Jones, Feb 11 1980, 503 555 0142" → extraction fills four slots → `search_patient` → `STRONG` → `verify_patient(mobile_phone=+15035550142)` → verified → reply `verified_ok` ("Thanks, Bob…" uses the given first name).
- Stranger: "Robert Jones, Feb 11 1980, 503 555 0199" → `STRONG` → verify fails → `identify_retry`.
- Stranger: "Robert Joans, Feb 11 1980, 503 555 0199" → `NONE` → `identify_retry` (same text, same attempt count).

## 7. Implementation guide
1. **Normalization.** Implement the functions with exhaustive unit tests (T1–T4). Build and review `nicknames.csv` (license **Verify**).
2. **P1-16 addition.** Add `zip5` to `PatientRecord` (mapped from the Open Dental patient ZIP field, **Verify** the name), kept in memory only; update P1-16's leak tests to include it.
3. **Config.** Add `first_name_match` to P1-19's `VerificationPolicy` (file-only, enum).
4. **Matching.** Implement `score_candidates`; run `A` and `P` searches concurrently (`asyncio.gather`), both through P1-15's pacer.
5. **Tool handlers.** Replace P1-22's interim scoring in `search_patient`; register the real `verify_patient` with `replace_stub=True`.
6. **Guard.** Register `not_verification_locked` (P1-13 session flag) and add it to P2-08's `create_patient` preconditions.
7. **Flow handlers.** Implement `IdentifyHandler` and `VerifyHandler` exactly per §6; register them in P2-01. Add the templates to P2-04.
8. **No-oracle suite** (T12–T15): for a fixed set of identities, compare replies, attempt counts, events, response timing class and log fields between "record exists, wrong phone", "no record", "archived record", "two records" — they must be identical to the patient.
9. **Docs and notifications.** `docs/identification.md` (sequence diagram, outcomes, templates). Notify P2-05 (normalizer reuse), P2-15 (new-patient flag, duplicate path), P2-22 (`identity_needs_staff` reason), P1-16 (zip5), P3-09 (spelling mode feeds `last_name`), P5-08 (no-oracle tests).

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| Correct name and DOB, phone not on file, correct ZIP | First attempt fails (phone) → `identify_retry` → patient gives ZIP → verified |
| Patient uses nickname "Liz" for "Elizabeth" | `first_name_matches` nickname → strong |
| First name typo "Jonh" | Jaro-Winkler ≥ 0.92 → strong (mode `fuzzy`) |
| Last name misspelt | `NONE` / `PARTIAL` → `identify_retry` asks for spelling |
| Hyphenated or two last names ("Garcia Lopez" vs "Garcia-Lopez") | `name_key` removes spaces and hyphens for comparison; the Open Dental search uses the normalized form given by the patient (**Verify** how Open Dental matches hyphens; if exact, retry with the other form once) |
| Twins with the same name and DOB | `MULTIPLE` → the second identifier picks one; if both share the phone → failure → callback after the limit |
| Family members sharing one phone | Phone search returns several; only the one matching name+DOB+first name is strong |
| Archived chart matches | `BLOCKED_STATUS` → neutral failure → callback with `identity_needs_staff` |
| DOB "5/3/90" | `parse_dob` → 1990-05-03 (US order) |
| Phone spoken "five oh three, five five five, oh one four two" | `parse_phone` → `+15035550142` |
| `TooManyMatchesError` (common name) | `MULTIPLE` → verification by identifier; else callback |
| Open Dental unavailable during search | P1-22 `od_unavailable` → `od_unavailable` event → callback (no attempt counted) |
| Verified parent wants to book for a child | `add_patient` → new person frame → IDENTIFY/VERIFY for the child with the same rules (§6 Household) |
| Fifth person in one chat | `household_full` template; no new frame |
| Parent switches back to their own booking | `switch_patient` → `switch_active`; no re-verification; the child's handles and offers are cleared |
| 6th search in the session | P2-08 `budget_exceeded` → callback |
| Locked session tries to register | `create_patient` denied by `not_verification_locked` → callback |

## 9. Security, HIPAA and PHI
- **PHI handled:** names, DOB, phone, ZIP from the patient (slot memory, encrypted, P2-01) and from Open Dental (`PatientRecord`, in memory for the duration of the tool call). PatNums go only to the server-side handle store and to `mark_verified`.
- **Never returned to the model:** names, DOBs, phones, ZIPs, PatNums, counts, statuses. The model sees only P1-22's `outcome` and `ask_for`, and the patient sees only the neutral templates.
- **Never logged:** any identifier value, PatNums, the reason a specific verification failed. Logs hold outcome codes and identifier **types**.
- **Controls:** ≥ 2 identifiers beyond phone (§4.5); no oracle (identical replies and attempt counting for every failure); attempt limit and lock (P1-13); search budget (P2-08); no create after lock or on ambiguity.
- **Audit:** `patient.search` (`match_count` bucket), `patient.verify`, `patient.verify_failed`, `security.rate_limited` on lock (P1-13).

## 10. Testing
```bash
cd backend && pytest tests/unit/domain/patients tests/unit/orchestrator/flows/test_identify.py -q
pytest tests/integration/identify -q          # od_fake with seeded synthetic patients
```
Fixture `tests/fixtures/patients_identify.yaml`: 20 synthetic patients covering nicknames, twins, shared family phones, archived and prospective statuses, hyphenated names, missing DOB, missing ZIP.

| # | Case | Expected |
|---|---|---|
| T1 | `normalize_name` / `name_key` with accents, apostrophes, suffixes, hyphens | Expected keys |
| T2 | Nicknames: Bob→Robert, Liz→Elizabeth, Bill→William, Peggy→Margaret; non-pairs rejected | Correct per mode |
| T3 | `parse_dob`: "5/3/90", "05/03/1990", "May 3 1990", "3rd of May 1990", "05031990", spoken forms, "2/30/1990" | 1990-05-03 … ; invalid → None |
| T4 | `parse_phone`: digits, separators, spoken with "oh" and "double", 11-digit with 1, invalid | E.164 or None |
| T5 | Scoring: each outcome (strong, multiple, partial, none, blocked_status) | Correct outcome |
| T6 | Ambiguous result never auto-creates | `create_patient` denied (`duplicate_risk`) for partial, multiple, blocked |
| T7 | `check_identifiers`: phone match, ZIP match, neither, two records pass | Record / None |
| T8 | Phone-only match (different name) | Never verified |
| T9 | Happy path in one turn | IDENTIFY → VERIFY → `verified` in a single `handle()`; `mark_verified` called |
| T10 | Three failures | Locked; `verify_attempt_limit`; `verify_locked` reply; callback |
| T11 | Unverified user gets no record details | Every reply before `verified` is one of the neutral templates; `get_patient_appointments` denied |
| T12 | **No oracle:** "record exists, wrong phone" vs "no record" | Identical reply text, events, attempt counts and log field sets |
| T13 | **No oracle:** archived record vs no record | Identical to the patient |
| T14 | **No oracle:** twins unresolved vs no record | Identical to the patient |
| T15 | Declared new patient with an existing record | REGISTER → `duplicate_risk` → neutral callback; no attempt counted |
| T16 | Locked session tries to register | Denied by `not_verification_locked` |
| T17 | Log capture with the PHI corpus | No identifier values or PatNums |
| T18 | `first_name_match: exact` | "Bob" does not match "Robert" |
| T19 | Household: verified parent adds a child, child verified, booking card shows the child, hash includes the child's PatNum | Booking written to the child only; a parent-card yes cannot book for the child |
| T20 | Household limits: shared attempt counter across persons, 5th person, switch back without re-verification, handles cleared on switch | Lock after 3 failures in total; `household_full`; `switch_active` only to household members; old handles → `unknown_handle` |

## 11. Acceptance criteria
- [ ] Normalization handles nicknames, typed and spoken DOBs and phones (T1–T4), including "Bob"→"Robert" and "5/3/90"
- [ ] Each match outcome is covered by tests, and ambiguous results never auto-create (T5, T6)
- [ ] Verification needs name + DOB + one of phone or ZIP per clinic policy; phone alone never verifies (T7, T8)
- [ ] A returning patient with correct details is verified in one turn (T9)
- [ ] An unverified user gets no record details, and the replies for every failure cause are identical (T11–T14)
- [ ] After `verification.max_attempts` failures the session is locked and only a callback is offered; a locked session cannot register (T10, T16)
- [ ] No identifier values or PatNums in logs (T17)
- [ ] A parent can verify and act for up to 3 family members in the same chat, each verified with the same rules, with attempts shared across the session and every write bound to the named patient (T19, T20)

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI
- [ ] PR reviewed (HIPAA review: labelled `phi`)
- [ ] No PHI in logs
- [ ] `docs/identification.md` written; nickname list license recorded; P1-16, P1-19, P2-04 and P2-08 updates merged
- [ ] P2-05, P2-15, P2-22, P3-09 and P5-08 issues notified

## 13. Hand-off
| Consumer | What they can rely on |
|---|---|
| All patient-scoped flows (P2-16, P2-18, P4) | After `verified`, `principal.verified_patnum` is set and the intent resumes |
| P2-05 Extraction | `normalize_name`, `parse_dob`, `parse_phone` |
| P2-15 Registration | `flags.new_patient_declared`; `match_none_confirmed`; duplicate path ends in a neutral callback; normalizers |
| P2-22 Callback | Reasons `identity_needs_staff`, `verification_locked` |
| P3-09 Spelling mode | Feeds `first_name` / `last_name` slots; identification is unchanged |
| P5-08 Security tests | No-oracle suite, lock and budget behaviour |

## 14. Open questions
| # | Question | Recommended answer | Owner |
|---|---|---|---|
| 1 | Should a verified patient be able to act for a family member (parent booking for a child) in the same chat? | **Resolved (user decision, DECISIONS #185):** yes, up to 4 people per chat, each verified with the same rules; see §6 Household. | - |
| 2 | Is Jaro-Winkler 0.92 the right threshold? | Start at 0.92; measure false matches on the fixture and pilot callbacks; it is a constant that can move to config. | Tech lead |
| 3 | Should the attempt counter survive a new session (same browser)? | No for the MVP (P1-13 counts per session); P1-13's IP and device rate limits cover repeated sessions. | Security owner |

## 15. References
- Plan: §4.5, §4.9, §6
- P0-01 Q1 (identifier policy)
- RapidFuzz Jaro-Winkler: https://rapidfuzz.github.io/RapidFuzz/Usage/distance/JaroWinkler.html
- `phonenumbers`: https://github.com/daviddrysdale/python-phonenumbers
- Nickname dataset (license to verify): https://github.com/carltonnorthern/nicknames
- DECISIONS: #164, #176, #177, #181, #182, #183, #184
- Related tasks: P0-01, P0-04, P1-13, P1-15, P1-16, P1-19, P1-22, P2-01, P2-04, P2-05, P2-08, P2-15, P2-16, P2-18, P2-22, P3-09, P5-08
