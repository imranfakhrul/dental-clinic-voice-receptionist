# appointment-type-mapping Specification

## Purpose

Defines, per clinic, how each fixed visit-reason code maps to an Open Dental appointment type, duration and eligible providers, and whether the AI may book it. Deterministic code, not the LLM, decides what gets booked.

## Requirements

### Requirement: Mapping files validate against the appointment-types JSON Schema
Every clinic mapping file and the shared test fixture SHALL validate against `appointment_types.schema.json` (JSON Schema 2020-12). Unknown fields at any level SHALL be rejected.

#### Scenario: Valid clinic seed
- **WHEN** the clinic seed file is validated against the schema
- **THEN** validation passes

#### Scenario: Unknown field
- **WHEN** a mapping file contains a field the schema does not define
- **THEN** validation fails

#### Scenario: Unknown fallback action
- **WHEN** a reason's `when_not_bookable` is not `callback` or `not_offered`
- **THEN** validation fails

### Requirement: Every reason code appears exactly once
Each mapping file SHALL contain every one of the 15 fixed reason codes exactly once, even if the reason is not bookable. The codes are `new_patient_exam`, `recall_cleaning`, `child_visit`, `toothache`, `sensitivity`, `broken_tooth`, `lost_filling_or_crown`, `gum_problem`, `wisdom_tooth`, `denture_problem`, `cosmetic_consult`, `ortho_consult`, `emergency_exam`, `treatment_followup` and `other`.

#### Scenario: Complete file
- **WHEN** the reason codes of a mapping file are listed
- **THEN** all 15 codes are present, each once

#### Scenario: Missing code
- **WHEN** a reason code is missing from a file
- **THEN** the file is rejected (by the schema's `minItems` or by the P1-19 load-time check)

### Requirement: Bookable reasons have at least one complete variant
A reason with `bookable_by_ai: true` SHALL have at least one variant. Each variant SHALL name an appointment type with a duration of 5–480 minutes and at least one provider.

#### Scenario: Bookable reason without variants
- **WHEN** a reason has `bookable_by_ai: true` and an empty `variants` list
- **THEN** validation fails

### Requirement: Catch-all reasons are never bookable
`other` and `treatment_followup` SHALL have `bookable_by_ai: false` and `when_not_bookable: callback`.

#### Scenario: Patient describes treatment already planned by a dentist
- **WHEN** the reason code is `treatment_followup`
- **THEN** no appointment type is looked up and a callback case is created

### Requirement: Durations fit the Open Dental time increment
Every `duration_min` SHALL be a multiple of the file's `od_time_increment_min` (5, 10 or 15).

#### Scenario: Misaligned duration
- **WHEN** a variant's duration is 45 minutes and the increment is 10
- **THEN** the file is rejected by the reviewer check now, and by P1-19 at load time later

### Requirement: Approved files have complete Open Dental IDs and approvers
A file with `status: approved` SHALL have every `od_appointment_type_num` and `od_prov_num` non-null, and SHALL have `approved_by` and `approved_on` (a quoted ISO date) set. Otherwise it SHALL stay `status: draft`.

#### Scenario: Approved file with a missing ID
- **WHEN** a file is `approved` and some `od_prov_num` is null
- **THEN** the file is rejected

### Requirement: First matching variant decides the appointment
Given a reason code, a patient type (`new` or `existing`) and the patient's age on the appointment date, the first variant whose `patient_types` contains the patient type and whose age range contains the age SHALL be used. A null `age_min` or `age_max` means no limit.

#### Scenario: Child before adult
- **WHEN** a reason lists a variant with `age_max: 17` before an adult variant and the patient is 9
- **THEN** the child variant is selected

#### Scenario: Unknown age
- **WHEN** the patient's age is unknown
- **THEN** age-limited variants are skipped and the first variant with no age limits is used

### Requirement: Non-bookable reasons fall back to a defined action
When `bookable_by_ai` is false or no variant matches, the system SHALL apply `when_not_bookable`. `callback` SHALL create a callback case for that reason. `not_offered` SHALL tell the patient the clinic doesn't offer the service and offer a callback.

#### Scenario: Service the clinic doesn't offer
- **WHEN** the reason is `ortho_consult` with `when_not_bookable: not_offered`
- **THEN** the patient is told it isn't offered and is offered a callback

#### Scenario: Service staff must book
- **WHEN** the reason is `cosmetic_consult` with `bookable_by_ai: false` and `when_not_bookable: callback`
- **THEN** a callback case is created and no slot is offered

### Requirement: Clinic mapping agrees with the clinic decision log
The clinic seed SHALL mark as `bookable_by_ai: true` only the reasons whose appointment kinds the clinic allowed in P0-01 Q3, and `emergency_exam` SHALL be bookable so the Tier 2 urgent path (P0-03) can book into it.

#### Scenario: Q3 allows exams, recall and limited exams only
- **WHEN** the clinic seed is compared with decision-log row Q3
- **THEN** only `new_patient_exam`, `recall_cleaning` and `emergency_exam` are bookable by the AI

### Requirement: No PHI in mapping files
Mapping files, the workbook and the readable table SHALL contain only clinic setup data (appointment types, provider abbreviations, operatory names) and invented example phrases, never patient data.

#### Scenario: Review for PHI
- **WHEN** a reviewer checks the files before sign-off
- **THEN** no patient names, dates of birth, phone numbers or appointment details are found
