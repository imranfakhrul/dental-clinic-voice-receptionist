# Open Dental test data (seed)

> **All synthetic.** Fictional names; phone numbers in the `555-0100`–`555-0199` range, which is reserved for fiction; emails at `example.com`. Never copy anything from a real practice or from Open Dental's public hosted database into these files.

| | |
|---|---|
| Task | P0-12 (issue #13) |
| Files | Setup: [`seed_setup.md`](../../infra/dev/open-dental-test-db/seed/seed_setup.md) · Patients: [`seed_patients.csv`](../../infra/dev/open-dental-test-db/seed/seed_patients.csv) (32) · Appointments: [`seed_appointments.csv`](../../infra/dev/open-dental-test-db/seed/seed_appointments.csv) (10) |
| Loader | `scripts/open_dental/seed_test_db.py`: test database (B) only. `--dry-run` checks the CSVs offline |
| Status | Seed **defined and checked** (dry run). **Not loaded**: test database (B) doesn't exist yet. The PatNum and AptNum columns below are filled in after the first load |

## Patient cases
`ref` is the seed's own ID. Tests use `ref` until PatNums exist, then this table maps them.

| Case (spec §6) | Refs | What it tests | Used by | PatNum |
|---|---|---|---|---|
| Plain returning patient | P01 (Maria Lopez, 1985-03-14) | Simple lookup and booking | P1-16, P2-12 | - |
| Same name, different DOB | P02, P03 (two John Smith) | DOB separates them | P2-12 | - |
| Same name **and** DOB, different phone | P24, P25 (two Sarah Johnson) | Must go to callback, never pick one. **Open Dental's own duplicate check may refuse P25** (D6: it compares name, DOB and email or phone); record what happens | P2-12 | - |
| Twins sharing a family phone | P05, P06 (guarantor P04) | Phone alone can't identify; name + DOB needed | P2-12, P2-15 | - |
| Nickname vs legal name | P07 (William "Bill" Turner) | `Preferred` field | P2-12 | - |
| Hyphen, apostrophe, accents | P08 (Anne-Marie O'Neil), P09 (José Núñez) | Normalization, UTF-8 | P2-12, P1-16 | - |
| Multi-part names | P28 (Mary Ellen Van Der Berg) | Spaces inside first and last names | P2-12 | - |
| Look-alike of another patient | P32 (Mario Lopez, same DOB as P01) | Fuzzy matching must not merge | P2-12 | - |
| Phone formats | P01 `5035550101`, P02 `(503) 555-0102`, P03 `503-555-0103`, P10 `503.555.0110`, P11 `+1 503 555 0111` | Phone normalization (P1-16 spike) | P1-16 | - |
| Missing DOB / missing phone | P12 / P13 | Partial records | P1-16 | - |
| Home phone only | P30 | Landline; no SMS/WhatsApp | P1-16, P4-04 | - |
| Inactive / Archived / Deceased | P14 / P15 / P16 | Status filter; Deceased never offered booking | P1-16 | - |
| Prospective / NonPatient | P26 / P27 | Status filter | P1-16 | - |
| Child with guardian | P18 (guardian P17) | Minors policy | P0-01, P2-15 | - |
| Age boundary 17→18 | P29 (turns 18 on 2026-12-15) | Child vs adult recall variant (P0-02) | P1-20 | - |
| Future appointments | P19 (A01, A02) | Reschedule and cancel; more than one | P1-16, P2-16 | - |
| Broken appointment | P20 (A03) | Unscheduled List | P1-16, P2-18 | - |
| Past appointment only | P21 (A04) | Nothing to cancel | P1-16, P2-18 | - |

## Appointments
Dates are relative to the load date, so the seed stays useful. The loader turns them into dates in America/New_York and skips weekends and holidays.

| Ref | Patient | When | Type, length, provider, op | Status | Purpose | AptNum |
|---|---|---|---|---|---|---|
| A01 | P19 | +10 business days 09:00 | Recall, 60, HYG1, Op 3 | Scheduled | Reschedule/cancel target | - |
| A02 | P19 | +25 business days 14:00 | Limited Exam, 30, DDS1, Op 1 | Scheduled | Second future appointment | - |
| A03 | P20 | +5 business days 10:00 | Recall, 60, HYG1, Op 3 | Broken | Broken (via Break) | - |
| A04 | P21 | −20 business days 08:00 | Recall, 60, HYG2, Op 4 | Complete | Past only | - |
| A05 | P22 | 2027-03-15 08:00 (first Monday after the DST change on 2027-03-14) | Recall, 60, HYG2, Op 4 | Scheduled | DST edge (P5-04) | - |
| A06 | P23 | +3 business days 13:00 | Limited Exam, 30, DDS1, Op 1 | Scheduled | Double-booking target | - |
| A07–A10 | P01, P31, P07, P28 | +2 to +6 business days | Various | Scheduled | Realistic gaps in availability | - |

Notes:
- **A03:** the loader creates it as Scheduled, then breaks it with `PUT /appointments/{AptNum}/Break` and `sendToUnscheduledList=true`.
- **A04:** created directly with `AptStatus=Complete`, which `POST /appointments` allows (D7).

## Rules for integration tests
- Don't assume a clean database unless the test runs right after a reset.
- Tests create their own patients with last names starting **`ZZTEST`**, and clean up by breaking their appointments.
- Run tests **one at a time per customer key** (1 request per second, processed sequentially; D3).
- Never run integration tests against the public hosted database.
