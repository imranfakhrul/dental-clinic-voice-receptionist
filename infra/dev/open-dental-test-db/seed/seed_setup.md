# Test database (B): setup entered in Open Dental's UI

> **Synthetic data only** (`data=synthetic-only`). Mirrors the clinic setup in [appointment-type-mapping.md](../../../../docs/discovery/appointment-type-mapping.md) (P0-02) and the hours in the [decision log](../../../../docs/discovery/clinic-decision-log.md) B5. These are entered by hand **before** `scripts/open_dental/seed_test_db.py` loads the patients and appointments, because our developer key has no Setup permission.

Status: **pending**: test database (B) doesn't exist yet ([open-dental-test-db.md](../../../../docs/integrations/open-dental-test-db.md)).

## Practice
- Time zone: **America/New_York**.
- Time increment: **10 minutes** (Setup > Appointments > Appts Preferences). **Verify** against the API's `Pattern` (documented in 5-minute steps) once (B) runs.
- One location, clinics feature **off** (P0-01 Q10).

## Providers
The mapping has 3 active providers plus one inactive dentist. That replaces the spec's "2 dentists, 1 hygienist" so the test database matches the clinic.

| ProvNum (expected) | Abbr | Name | Role | Active |
|---|---|---|---|---|
| 1 | DDS1 | Dr. Casey Example | Dentist | Yes |
| 2 | HYG1 | Jamie Sample, RDH | Hygienist | Yes |
| 3 | HYG2 | Taylor Example, RDH | Hygienist | Yes |
| 4 | DDS2 | Dr. Morgan Former | Dentist | **No** (inactive-provider case) |

## Operatories
| OperatoryNum (expected) | Name | Hygiene |
|---|---|---|
| 1 | Op 1 - Doctor | No |
| 2 | Op 2 - Doctor | No |
| 3 | Op 3 - Hygiene | Yes |
| 4 | Op 4 - Hygiene | Yes |

## Appointment types
All 13 rows of the mapping's "Clinic setup data", with the same names and lengths. The AI uses four of them:
- 1 New Patient Exam, 60 min;
- 2 Recall, 60 min;
- 3 Child Recall, 40 min;
- 4 Limited Exam, 30 min.

Enter each type's pattern so that its length matches.

## Hours, blocks and holidays
- **Hours:** Mon–Thu 08:00–17:00, Fri 08:00–14:00, closed weekends.
- **Lunch:** 12:00–13:00 Mon–Thu, entered as a blockout. Proposed: B5 names no lunch break, and the spec asks for one.
- **Blocks:**
  - emergency block 11:00–12:00 daily (blockout type "Emergency");
  - new-patient block Tue/Thu 08:00–10:00 (blockout type "New Patient").
- **Holiday:** 2026-12-25 (Christmas Day), plus 2027-01-01 if the provider schedules reach it.
- **Provider schedules:**
  - DDS1 in Op 1/Op 2;
  - HYG1 in Op 3;
  - HYG2 in Op 4;
  - for the next **8 weeks**, re-run monthly.

## After entering
1. Note the actual ProvNum, OperatoryNum and AppointmentTypeNum values. If they differ from "expected" above, update this file and `docs/integrations/open-dental-test-data.md`.
2. Run `seed_test_db.py`, then take the **post-seed snapshot** (reset procedure in `open-dental-test-db.md`).
