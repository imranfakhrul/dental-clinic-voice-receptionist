# Proposal: P0-02 Appointment-type mapping (GitHub issue #2)

## Why

The AI must never diagnose, and it must never decide on its own what to book. The design that makes this possible:
- the model only classifies the patient's words into a fixed **reason code**;
- deterministic code looks up the appointment type, duration and eligible providers in a clinic-approved mapping.

Without that mapping, other tasks are stuck:
- P1-19 (clinic config) has nothing to seed;
- P1-20 (availability) can't compute slots of the right length with the right providers;
- P2-16 (booking flow) can't turn "my tooth hurts" into a bookable appointment.

The only dependency was P0-01 (#1), which is now closed. Its decision-log answer to Q3 (which kinds of appointments the AI may book) is the input for this task.

Source of truth: `dental-ai-tasks/tasks/P0-02 Document appointment-type mapping (reason to type to duration to providers).md` (approved).

## What Changes

- **JSON Schema** `backend/app/domain/clinic_config/schemas/appointment_types.schema.json`. It is the contract that P1-19, P1-20, P2-16 and P4-11 build against. Copied exactly from spec §6.
- **Synthetic example** `backend/tests/fixtures/clinic_config/appointment_types.example.yaml`. It contains all 15 reason codes, at least one reason with separate new/existing variants, an age-limited `child_visit` variant, one `not_offered` reason and one `callback` reason. It is for tests in later tasks.
- **Clinic seed** `backend/app/domain/clinic_config/seed/example-dental-clinic/appointment_types.yaml`. It holds the pilot clinic's mapping, consistent with the decision log:
  - Q3: the AI books only new-patient exams, recall/cleaning and limited (emergency) exams;
  - providers: Dr. Casey Example and the hygiene team.
- **Workbook** `docs/discovery/appointment-type-workbook.xlsx` with four tabs (Appointment types, Providers, Operatories, Mapping), filled with the clinic's setup data.
- **Readable mapping table** `docs/discovery/appointment-type-mapping.md`, one row per variant, plus a written sign-off `docs/discovery/signoff-appointment-types-YYYY-MM-DD.pdf`.
- **Notifications:**
  - The clinic decision log links to the mapping.
  - The P1-19, P1-20, P2-16, P2-21 and P4-11 issues don't exist yet, so their notifications go into a "Pending notifications" list.
  - The Phase 0 README shows #2's status.

No application code: loading and enforcing the mapping at runtime is P1-19.

## Capabilities

### New Capabilities
- `appointment-type-mapping`: the per-clinic mapping from reason code to Open Dental appointment type, duration, eligible providers and operatories, plus the AI-bookability rule. Its file format is fixed by a JSON Schema and it covers the 15 fixed reason codes.

### Modified Capabilities
- None (no existing specs).

## Impact

- **New directories:** `backend/app/domain/clinic_config/{schemas,seed}` and `backend/tests/fixtures/clinic_config/`. These are the first files under `backend/`, at the paths P1-01's layout uses, so P1-01 keeps them unchanged.
- **Downstream contract:** P1-19 (load-time rules), P1-20 (durations, providers), P2-05 (reason-code enum), P2-16 (variant-selection rule), P2-21 (`emergency_exam`), P1-17 (type and duration on create) and P4-11 (the admin screen edits this structure).
- **Changing the reason-code list later** is a product change: it needs a schema change and an update to the P2-05 prompt, recorded in `DECISIONS.md`.
- **Privacy:** no PHI. Appointment types, provider abbreviations and operatory names are clinic setup data, and the example phrases are invented.
- **Tooling:** validation uses `check-jsonschema`. It runs from a temporary virtual environment, and no project dependencies are added. Adding it to CI happens in P1-06 / P1-19.
