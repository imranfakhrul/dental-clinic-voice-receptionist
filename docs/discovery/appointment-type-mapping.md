# Appointment-type mapping: Example Dental Clinic

- **Mapping version:** 1.0 · **Status:** approved (SME and dentist, 2026-11-26), see [signoff-appointment-types-2026-11-26.pdf](signoff-appointment-types-2026-11-26.pdf)
- **Machine-readable source:** `backend/app/domain/clinic_config/seed/example-dental-clinic/appointment_types.yaml`. This table matches it row for row.
- **Schema:** `backend/app/domain/clinic_config/schemas/appointment_types.schema.json` · **Test fixture:** `backend/tests/fixtures/clinic_config/appointment_types.example.yaml`
- **Collected with:** [appointment-type-workbook.xlsx](appointment-type-workbook.xlsx) · **Decision-log input:** [Q3](clinic-decision-log.md) (what the AI may book)

> *Sample values: replace them with the clinic's real setup data, then bump `mapping_version` and get sign-off again.*

## How the mapping is used
1. The AI only classifies the patient's words into one of the 15 **reason codes** (P2-05). It never chooses an appointment type itself.
2. Code takes the **first** variant whose patient types include the patient (`new` / `existing`) and whose age range includes the patient's age on the appointment date. An unknown age skips age-limited variants.
3. If the reason isn't bookable by the AI, or no variant matches:
   - `callback`: a callback case is created (P2-22);
   - `not_offered`: the patient is told the clinic doesn't offer it, and is offered a callback.
4. Tier 1 emergencies (911) never reach this mapping. Tier 2 urgent visits book into `emergency_exam` (P0-03).

## Mapping (one row per variant)
Durations are in minutes. The Open Dental time increment is **10 minutes**. **Verify:** the clinic's increment and the meaning of the pattern characters, against the test database (P0-12).

| Reason code | Label | Patient types | Age | Open Dental type (#) | Duration | Providers (#) | Operatories | AI may book | If not bookable | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| `new_patient_exam` | New patient exam | new | any | New Patient Exam (#1) | 60 | DDS1 (#1) | 1, 2 | **Yes** | callback | Q3: AI may book. New-patient block Tue/Thu 08:00-10:00 is clinic config (P1-19) |
| `recall_cleaning` | Cleaning and checkup | existing | 0–17 | Child Recall (#3) | 40 | HYG1 (#2), HYG2 (#3) | 3, 4 | **Yes** | callback | Q3: AI may book. Child variant listed first |
| `recall_cleaning` | Cleaning and checkup | existing | 18–∞ | Recall (#2) | 60 | HYG1 (#2), HYG2 (#3) | 3, 4 | **Yes** | callback | Q3: AI may book. Child variant listed first |
| `child_visit` | Child checkup | - | - | - | - | - | - | **No** | callback | Q3: not a separate AI-bookable type; existing children use recall_cleaning |
| `toothache` | Toothache | - | - | - | - | - | - | **No** | callback | Staff triage; severe pain is emergency_exam (P0-03) |
| `sensitivity` | Tooth sensitivity | - | - | - | - | - | - | **No** | callback | - |
| `broken_tooth` | Broken or chipped tooth | - | - | - | - | - | - | **No** | callback | Severe cases are emergency_exam (P0-03) |
| `lost_filling_or_crown` | Lost filling or crown | - | - | - | - | - | - | **No** | callback | - |
| `gum_problem` | Gum problem | - | - | - | - | - | - | **No** | callback | - |
| `wisdom_tooth` | Wisdom tooth | - | - | - | - | - | - | **No** | callback | - |
| `denture_problem` | Denture problem | - | - | - | - | - | - | **No** | callback | - |
| `cosmetic_consult` | Cosmetic consultation | - | - | - | - | - | - | **No** | callback | Offered; staff book it |
| `ortho_consult` | Braces / aligners | - | - | - | - | - | - | **No** | not_offered | Clinic does not offer orthodontics |
| `emergency_exam` | Urgent dental visit | new, existing | any | Limited Exam (#4) | 30 | DDS1 (#1) | 1, 2 | **Yes** | callback | Q3: AI may book. Tier 2 urgent slot (P0-03); emergency block 11:00-12:00 (B5) |
| `treatment_followup` | Planned treatment | - | - | - | - | - | - | **No** | callback | Always a callback in the MVP |
| `other` | Other | - | - | - | - | - | - | **No** | callback | - |

## Clinic setup data (from the workbook)
**Verify:** the field names `AppointmentTypeNum`, `ProvNum` and `OperatoryNum`, and that the API exposes them (P1-18). Open Dental's own type length wins over `duration_min` at booking time.

| AppointmentTypeNum | Name | Default length (min) |
|---|---|---|
| 1 | New Patient Exam | 60 |
| 2 | Recall | 60 |
| 3 | Child Recall | 40 |
| 4 | Limited Exam | 30 |

| ProvNum | Abbreviation | Name | Role | Active |
|---|---|---|---|---|
| 1 | DDS1 | Dr. Casey Example | dentist | yes |
| 2 | HYG1 | Hygienist 1 | hygienist | yes |
| 3 | HYG2 | Hygienist 2 | hygienist | yes |

| OperatoryNum | Name | Hygiene |
|---|---|---|
| 1 | Op 1 - Doctor | no |
| 2 | Op 2 - Doctor | no |
| 3 | Op 3 - Hygiene | yes |
| 4 | Op 4 - Hygiene | yes |

## Review (spec §10)
Reviewer: Sam Comply, compliance advisor · Date: 2026-11-26

- [x] All 15 reason codes are present, each exactly once, in the seed and in the fixture.
- [x] Schema validation (`check-jsonschema`) passes for the seed and the fixture.
- [x] Negative checks on copies of the fixture:
  - (b) bookable with no variants, (c) unknown `when_not_bookable` and (d) an extra field all **fail** validation, as required;
  - (a) a missing code also fails, through `minItems: 15`;
  - a **duplicated** code keeps 15 items and **passes** the schema, so "each code exactly once" must be enforced by P1-19 at load time.
- [x] The rules the schema can't express hold: catch-all reasons are non-bookable callbacks, durations are multiples of 10, `age_min` ≤ `age_max`, and the approved file has no null IDs. A script reported 0 violations.
- [x] Agrees with decision-log Q3: only `new_patient_exam`, `recall_cleaning` and `emergency_exam` are bookable by the AI.
- [x] `emergency_exam` is bookable, so the Tier 2 path (P0-03) can book into it.
- [x] This table matches the seed YAML row for row (compared by a script).
- [x] No PHI: only clinic setup data and invented labels.

## Open items
| Item | Owner | Needed by |
|---|---|---|
| Confirm the Open Dental time increment and pattern meaning against the test DB (**Verify**) | Tech lead | P0-12 |
| Confirm the IDs above against the API (`AppointmentTypeNum`, `ProvNum`, `OperatoryNum`) | Tech lead | P1-18 |

## Pending notifications
These GitHub issues don't exist yet. When each one is created, comment on it with the file paths above and `mapping_version` 1.0.

| Task | What it relies on | Posted on issue (date) |
|---|---|---|
| P1-19 Clinic config | Schema, load-time rules (spec §6, including "each code exactly once"), fixture and seed | - |
| P1-20 Availability engine | Per reason: duration, eligible `od_prov_num`s, `operatory_nums` (empty = any) | - |
| P2-16 Booking flow | Variant-selection rule and `when_not_bookable` actions | - |
| P2-21 Tier 2 urgent path (now part of P2-20) | The `emergency_exam` reason (Limited Exam, 30 min, DDS1) | - |
| P4-11 Admin mapping screen | The same schema; the screen edits this structure | - |

## Changing the mapping
Edit the seed YAML and regenerate this table. Bump `mapping_version`: minor for wording, major for any type, provider or duration change. Then get SME and dentist approval again. Once P4-11 exists, changes go through the admin console.
