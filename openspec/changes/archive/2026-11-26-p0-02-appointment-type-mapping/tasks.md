# Tasks: P0-02 Appointment-type mapping (issue #2)

## 1. Schema and test fixture

- [x] 1.1 Create a throwaway virtual environment in the scratchpad and install `check-jsonschema` and `openpyxl` into it. Verify: `check-jsonschema --version` runs. Use the fallback from design Decision 6 if installing fails.
- [x] 1.2 Create `backend/app/domain/clinic_config/schemas/appointment_types.schema.json`, copied exactly from spec §6. Verify: it parses as JSON and passes `check-jsonschema --check-metaschema`.
- [x] 1.3 Create `backend/tests/fixtures/clinic_config/appointment_types.example.yaml`. It needs all 15 codes with fake numbers, a reason with separate new/existing variants, a `child_visit` variant with `age_max: 17`, one `not_offered` reason and one `callback` reason, and quoted dates. Verify: `check-jsonschema` passes on it.
- [x] 1.4 Run the 4 negative checks from spec §10 on copies of the example in the scratchpad: (a) missing code, (b) bookable with no variants, (c) unknown `when_not_bookable`, (d) an extra field. Verify: (b), (c) and (d) fail validation, and (a) is noted as a P1-19 load-time rule.

## 2. Clinic mapping data

- [x] 2.1 Create `docs/discovery/appointment-type-workbook.xlsx` with the tabs Appointment types, Providers, Operatories and Mapping (15 reason rows), plus a "How to fill" note ("setup lists only, never patient screens"). Fill it with the clinic's setup data. Verify: the file opens with `openpyxl` and has 4 data tabs and 15 mapping rows.
- [x] 2.2 Create `backend/app/domain/clinic_config/seed/example-dental-clinic/appointment_types.yaml` from the workbook.
  - Only `new_patient_exam`, `recall_cleaning` (child variant before the adult one) and `emergency_exam` are bookable.
  - `ortho_consult` is `not_offered`; every other reason is `callback`.
  - Verify: `check-jsonschema` passes, and the bookable set matches decision-log Q3.
- [x] 2.3 Check the rules the schema can't express with a scratchpad script: each code exactly once, catch-all reasons not bookable, durations a multiple of the increment, `age_min` ≤ `age_max`, and an approved file has no null IDs. Verify: the script reports 0 violations for both YAML files.

## 3. Readable mapping, sign-off and links

- [x] 3.1 Create `docs/discovery/appointment-type-mapping.md` with one row per variant (reason, patient types, ages, type, duration, providers, operatories, bookable, fallback). Keep the spec's `Verify:` markers and add a review section with the results of 1.4 and 2.3. Verify: the table matches the seed YAML row for row (compared by a script).
- [x] 3.2 Save the SME and dentist approval as `docs/discovery/signoff-appointment-types-YYYY-MM-DD.pdf`. Set the seed to `status: approved` with `approved_by` and `approved_on` (quoted). Verify: the seed still validates, and the 2.3 script reports 0 violations.
- [x] 3.3 Add a "Pending notifications" table to the mapping doc for P1-19, P1-20, P2-16, P2-21 and P4-11 (file paths and `mapping_version`), link the mapping doc from `docs/discovery/clinic-decision-log.md`, and set #2 to ✅ in `docs/phase-0-discovery-compliance/README.md`. Verify: the links resolve.

## 4. Finish

- [x] 4.1 Commit with a one-line descriptive message, ask the user before pushing `feature/phase-0-discovery-compliance`, and after the push close issue #2 with a comment listing the files. Verify: `git log -1 --format=%s` is one line, and #2 shows as closed under #17.

## Workflow follow-up

- The senior merges the phase into `main` after all of Phase 0. After that, run `/opsx:archive p0-02-appointment-type-mapping`.
