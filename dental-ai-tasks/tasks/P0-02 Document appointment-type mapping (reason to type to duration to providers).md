---
id: P0-02
title: Document appointment-type mapping (reason -> type -> duration -> providers)
milestone: P0
epic: E0.1
size: S
labels: area:scheduling, type:docs
depends_on: P0-01
status: approved
---

# P0-02: Document appointment-type mapping (reason -> type -> duration -> providers)

## 1. Summary
With the pilot clinic, define how each reason a patient may give for a visit maps to an Open Dental appointment type, its duration, the providers (and optionally operatories) who can take it, and whether the AI may book it at all. Deliver it as a clinic-approved table **and** as a YAML seed file validated by a JSON Schema. The schema is the contract that clinic config (P1-19), availability (P1-20), the booking flow (P2-16) and the admin screen (P4-11) build against. Done means: the YAML validates, the clinic SME and dentist have signed off the table, and a synthetic example file exists for other tasks to test with.

## 2. Why this matters
The AI must never diagnose (plan §1 principle 4, §4.8) and must never decide on its own what to book (principle 2: "the LLM talks, deterministic code acts"). This mapping is what makes both possible: the model only classifies the patient's words into a fixed **reason code**, and code looks up the appointment type, duration and eligible providers in this file.

Without it, P1-19 has nothing to seed (its acceptance criterion is "seeded from P0-02 mapping"), P1-20 can't compute slots of the right length with the right providers, and P2-16 can't turn "my tooth hurts" into a bookable appointment. A wrong mapping is visible to clinic staff straight away: wrong-length appointments, a hygienist booked for an emergency exam, or the AI booking something the clinic wanted staff to handle.

Plan references: §7 (appointment type mapping in clinic config), §4.6 (scheduling), §4.3 (deterministic booking logic), §4.8 (emergencies), §13 Q3.

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P0, Discovery & Compliance Foundation**.
- **Open Dental:** the clinic's practice-management software and our source of truth for schedules and appointments. See GLOSSARY.md.
- **Appointment type (Open Dental):** a named kind of appointment the clinic defines (e.g. "New Patient Exam", "Recall"), with a default length. Clinics are not required to use them. **Verify:** the field names (expected `AppointmentTypeNum`, `AppointmentTypeName`, `Pattern`) and whether the API exposes appointment types, in https://www.opendental.com/site/apispecification.html.
- **Pattern / time increment:** Open Dental stores an appointment's length as a pattern string where each character is one time increment set by the clinic (5, 10 or 15 minutes). **Verify:** the exact meaning of the pattern characters and where the increment is set, in the Open Dental docs and the test DB (P0-12).
- **Provider (ProvNum):** a dentist or hygienist in Open Dental, identified by an integer `ProvNum`. **Operatory (OperatoryNum):** a chair/room. Provider and operatory lists are clinic setup data, **not** patient data.
- **Reason code:** our own fixed list of visit reasons (e.g. `toothache`). The LLM picks one (P2-05); this file says what each one means for this clinic. Reason codes are the same for every clinic; the mapping is per clinic.
- **Clinic decision log:** P0-01's signed-off answers. **Q3** says which kinds of appointments the AI may book at all; this task turns that into exact rows.
- **Seed data:** the first version of the clinic configuration, loaded by P1-19 and later edited in the admin console (P4-11).

## 4. Scope
**In scope**
- The reason-code list (§6), with patient-facing example phrases.
- Per clinic, per reason: patient type, optional age range, Open Dental appointment type, duration, eligible providers, optional eligible operatories, `bookable_by_ai`, and what happens when the AI may not book it.
- JSON Schema for the file, a filled-in YAML seed for the pilot clinic, and a synthetic example file for tests.
- A clinic workbook (spreadsheet template) to collect the data without API access or PHI.
- A human-readable mapping table and written sign-off by the SME and the dentist.

**Out of scope** (and which task covers it)
- Opening hours, holidays, new-patient blocks, emergency blocks → P1-19 (data from P0-01 B5)
- Emergency detection, trigger phrases and scripts → P0-03. This task only defines the `emergency_exam` row that P0-03's Tier 2 rule books into.
- Classifying patient words into reason codes → P2-05
- Loading, versioning and validating the file at runtime → P1-19
- Reading appointment types, providers and operatories from the Open Dental API → P1-18
- Computing free slots → P1-20
- The admin screen that edits this mapping → P4-11
- Treatment-planned procedures (e.g. "the dentist said I need a filling"): always a callback in the MVP, no type mapping

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P0-01 Discovery workshop (approved spec) | Q3: which kinds of appointments the AI may book; the named SME and dentist; the clinic's Open Dental admin | Write the schema, the reason list and the synthetic example file now (steps 1–3 in §7). They don't need clinic answers. |
| P0-12 Open Dental keys + test DB (soft) | API access to read appointment types, providers, operatories | Not needed: the clinic's Open Dental admin copies these lists from the setup screens into the workbook. Numeric IDs may stay `null` in the draft and are filled in later from the API (P1-18). |
| P1-01 Product repo (soft) | A place to commit `backend/app/domain/clinic_config/...` | Proposed: keep the files in the same shared location as the P0-01 decision log until P1-01 exists, and move them in unchanged. |

## 6. Interface contract

### Files (Proposed)
| Path | Content |
|---|---|
| `backend/app/domain/clinic_config/schemas/appointment_types.schema.json` | JSON Schema (below) |
| `backend/app/domain/clinic_config/seed/<clinic_slug>/appointment_types.yaml` | Pilot clinic seed data |
| `backend/tests/fixtures/clinic_config/appointment_types.example.yaml` | Synthetic, complete example for tests (P1-19, P1-20, P2-16) |
| `docs/discovery/appointment-type-workbook.xlsx` | Workbook the clinic fills in |
| `docs/discovery/appointment-type-mapping.md` | Human-readable table for sign-off |
| `docs/discovery/signoff-appointment-types-YYYY-MM-DD.pdf` | SME + dentist approval email |

`<clinic_slug>` is a lowercase, hyphenated clinic identifier, e.g. `smile-dental-pdx`.

### Reason codes (fixed list, Proposed)
Every clinic file must contain **every** code below, even if it is not bookable. Adding or renaming a code is a product change (schema + P2-05 prompt), logged in DECISIONS.md.

| Code | Meaning | Example patient phrases |
|---|---|---|
| `new_patient_exam` | First visit at this clinic: exam (and usually cleaning) | "I'm new here", "I'd like to become a patient" |
| `recall_cleaning` | Routine cleaning and checkup for an existing patient | "I need a cleaning", "time for my six-month checkup" |
| `child_visit` | Checkup or cleaning for a child | "checkup for my 6-year-old" |
| `toothache` | Tooth pain, not described as severe | "my tooth hurts when I chew" |
| `sensitivity` | Sensitivity to hot, cold or sweet | "my teeth are sensitive to cold" |
| `broken_tooth` | Chipped, cracked or broken tooth | "I chipped my front tooth" |
| `lost_filling_or_crown` | A filling or crown came out or off | "my crown fell off" |
| `gum_problem` | Bleeding, sore or swollen gums (not facial swelling) | "my gums bleed when I brush" |
| `wisdom_tooth` | Wisdom tooth pain or a removal consultation | "my wisdom tooth is coming in" |
| `denture_problem` | Denture adjustment or repair | "my denture is loose" |
| `cosmetic_consult` | Whitening, veneers, smile makeover | "I want my teeth whiter" |
| `ortho_consult` | Braces or aligners | "do you do Invisalign?" |
| `emergency_exam` | Urgent dental problem (Tier 2 in P0-03): severe pain, facial swelling, knocked-out tooth, signs of infection | "the pain is unbearable", "my face is swollen" |
| `treatment_followup` | Continuing treatment a dentist already planned | "the dentist said I need a filling" |
| `other` | Anything that doesn't fit | - |

Example phrases are written by us and contain no real patient data. Tier 1 emergencies (911 cases) are never mapped to an appointment: P0-03 / P2-20 handle them before any booking.

### YAML format (excerpt, synthetic)
This excerpt shows 4 of the 15 required reasons, so on its own it fails `minItems: 15`. The full example file (§7 step 2) has all 15. **Quote dates** (`"2026-12-10"`): an unquoted YAML date is parsed as a date object, not a string, and fails the schema.
```yaml
schema_version: 1
clinic_slug: example-dental
mapping_version: "1.0"
status: approved                 # draft | approved
approved_by: ["J. Doe, office manager", "Dr. A. Smith, dentist"]
approved_on: "2026-12-10"
od_time_increment_min: 10        # Verify: clinic's Open Dental time increment
reasons:
  - code: recall_cleaning
    label: "Cleaning and checkup"
    bookable_by_ai: true
    variants:
      - patient_types: [existing]
        age_min: 18
        age_max: null
        appointment_type: {od_appointment_type_num: 3, od_name: "Recall", duration_min: 60}
        providers: [{od_prov_num: 4, od_abbr: "HYG1"}, {od_prov_num: 5, od_abbr: "HYG2"}]
        operatory_nums: [2, 3]   # empty list = any operatory
    when_not_bookable: callback
    notes: ""
  - code: emergency_exam
    label: "Urgent dental visit"
    bookable_by_ai: true
    variants:
      - patient_types: [new, existing]
        age_min: null
        age_max: null
        appointment_type: {od_appointment_type_num: 7, od_name: "Limited Exam", duration_min: 30}
        providers: [{od_prov_num: 1, od_abbr: "DDS1"}]
        operatory_nums: []
    when_not_bookable: callback
    notes: "Tier 2 urgent slot (P0-03)"
  - code: ortho_consult
    label: "Braces / aligners"
    bookable_by_ai: false
    variants: []
    when_not_bookable: not_offered
    notes: "Clinic does not offer orthodontics"
  - code: other
    label: "Other"
    bookable_by_ai: false
    variants: []
    when_not_bookable: callback
    notes: ""
```

**How a row is used (for P2-16 / P1-20):** given a reason code, the patient type (`new` or `existing`) and the patient's age on the appointment date, take the **first** variant whose `patient_types` contains the patient type and whose age range contains the age (`null` = no limit). If `bookable_by_ai` is false or no variant matches, apply `when_not_bookable`:
- `callback` → create a callback case with this reason (P2-22)
- `not_offered` → tell the patient the clinic doesn't offer this, and offer a callback

### JSON Schema
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "appointment_types.schema.json",
  "type": "object",
  "additionalProperties": false,
  "required": ["schema_version", "clinic_slug", "mapping_version", "status", "od_time_increment_min", "reasons"],
  "properties": {
    "schema_version": {"const": 1},
    "clinic_slug": {"type": "string", "pattern": "^[a-z0-9]+(-[a-z0-9]+)*$"},
    "mapping_version": {"type": "string", "pattern": "^[0-9]+\\.[0-9]+$"},
    "status": {"enum": ["draft", "approved"]},
    "approved_by": {"type": "array", "items": {"type": "string", "minLength": 1}},
    "approved_on": {"type": ["string", "null"], "format": "date"},
    "od_time_increment_min": {"enum": [5, 10, 15]},
    "reasons": {"type": "array", "minItems": 15, "items": {"$ref": "#/$defs/reason"}}
  },
  "$defs": {
    "reason_code": {"enum": ["new_patient_exam", "recall_cleaning", "child_visit", "toothache", "sensitivity",
      "broken_tooth", "lost_filling_or_crown", "gum_problem", "wisdom_tooth", "denture_problem",
      "cosmetic_consult", "ortho_consult", "emergency_exam", "treatment_followup", "other"]},
    "reason": {
      "type": "object",
      "additionalProperties": false,
      "required": ["code", "label", "bookable_by_ai", "variants", "when_not_bookable"],
      "properties": {
        "code": {"$ref": "#/$defs/reason_code"},
        "label": {"type": "string", "minLength": 1, "maxLength": 60},
        "bookable_by_ai": {"type": "boolean"},
        "variants": {"type": "array", "items": {"$ref": "#/$defs/variant"}},
        "when_not_bookable": {"enum": ["callback", "not_offered"]},
        "notes": {"type": "string"}
      },
      "if": {"properties": {"bookable_by_ai": {"const": true}}},
      "then": {"properties": {"variants": {"minItems": 1}}}
    },
    "variant": {
      "type": "object",
      "additionalProperties": false,
      "required": ["patient_types", "age_min", "age_max", "appointment_type", "providers", "operatory_nums"],
      "properties": {
        "patient_types": {"type": "array", "minItems": 1, "uniqueItems": true, "items": {"enum": ["new", "existing"]}},
        "age_min": {"type": ["integer", "null"], "minimum": 0, "maximum": 120},
        "age_max": {"type": ["integer", "null"], "minimum": 0, "maximum": 120},
        "appointment_type": {
          "type": "object",
          "additionalProperties": false,
          "required": ["od_appointment_type_num", "od_name", "duration_min"],
          "properties": {
            "od_appointment_type_num": {"type": ["integer", "null"], "minimum": 1},
            "od_name": {"type": "string", "minLength": 1},
            "duration_min": {"type": "integer", "minimum": 5, "maximum": 480}
          }
        },
        "providers": {
          "type": "array", "minItems": 1,
          "items": {
            "type": "object",
            "additionalProperties": false,
            "required": ["od_prov_num", "od_abbr"],
            "properties": {
              "od_prov_num": {"type": ["integer", "null"], "minimum": 1},
              "od_abbr": {"type": "string", "minLength": 1}
            }
          }
        },
        "operatory_nums": {"type": "array", "uniqueItems": true, "items": {"type": "integer", "minimum": 1}}
      }
    }
  }
}
```

### Rules the schema can't express (P1-19 enforces them at load time)
| Rule | On failure |
|---|---|
| Every reason code appears exactly once | Reject the file |
| `other` and `treatment_followup` have `bookable_by_ai: false` and `when_not_bookable: callback` | Reject the file |
| `status: approved` requires every `od_*_num` to be non-null, plus `approved_by` and `approved_on` | Reject the file |
| `duration_min` is a multiple of `od_time_increment_min` | Reject the file |
| `age_min` ≤ `age_max` when both are set | Reject the file |
| `od_appointment_type_num`, `od_prov_num` and `operatory_nums` exist and are active in Open Dental (via P1-18) | Disable that variant, log a warning (no PHI), raise an admin alert; the reason falls back to `when_not_bookable` |
| `duration_min` differs from the Open Dental appointment type's own length | Open Dental wins; log a warning |
| Two variants of one reason overlap (same patient type, overlapping ages) | Allowed (first match wins); log a warning |

## 7. Implementation guide
1. **Schema first.** Commit the JSON Schema above. Proposed: validate files with the `check-jsonschema` CLI (`pip install check-jsonschema`), so no code is needed yet.
2. **Synthetic example.** Write `appointment_types.example.yaml` with all 15 codes, fake Open Dental numbers, at least one reason with two variants (new vs existing), one age-limited variant (`child_visit`, `age_max: 17`), one `not_offered` and one `callback`. It must validate. This file lets P1-19, P1-20 and P2-16 start their tests now.
3. **Workbook.** Create `appointment-type-workbook.xlsx` with four tabs:
   - *Appointment types:* name, default length in minutes, number if visible.
   - *Providers:* abbreviation, role (dentist / hygienist), active yes/no, number if visible.
   - *Operatories:* name, hygiene yes/no, number if visible.
   - *Mapping:* one line per reason code, pre-filled with our proposal, for the clinic to correct.

   **Verify:** whether the Open Dental setup screens show numeric IDs. If not, leave numbers blank; P1-18 fills them from the API later.
4. **Collect.** Send the workbook to the clinic's Open Dental admin with one instruction: setup lists only, never patient screens. No BAA exists yet (P0-09).
5. **Review the mapping with the SME and the dentist** (Proposed: a 45-minute call). Walk through every reason code. Check it against P0-01 Q3. The dentist confirms clinical fit (which provider can do which visit, durations); the SME confirms operational fit (which types the AI may book).
6. **Convert** the workbook to `seed/<clinic_slug>/appointment_types.yaml` with `status: draft`, and run `check-jsonschema`. Write `appointment-type-mapping.md` as a readable table of the same data, one row per variant.
7. **Sign off.** Send the table to the SME and the dentist. Save their approval as `signoff-appointment-types-YYYY-MM-DD.pdf`. Set `status: approved`, `approved_by`, `approved_on` **only once all `od_*_num` values are filled**. Until then, keep `status: draft` and record "approved, waiting for IDs" in the mapping doc.
8. **Notify.** Comment on the GitHub issues of P1-19, P1-20, P2-16, P2-21 and P4-11 with the file paths and `mapping_version`.
9. **Later changes:** edit the YAML, bump `mapping_version` (minor for wording, major for any type/provider/duration change), and get SME approval again. After P4-11 exists, changes go through the admin console instead.

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| The clinic doesn't use Open Dental appointment types | `od_appointment_type_num: null`, `od_name` describes the visit, `duration_min` set explicitly. Tell the P1-17 owner, since creating an appointment then needs an explicit length (**Verify:** how the appointment POST sets length without a type). Such a file can't reach `status: approved` until the team logs an exception in DECISIONS.md. |
| One reason needs different types for new and existing patients (e.g. toothache) | Two variants with different `patient_types`. |
| Children have a different type or provider | A variant with `age_max: 17` listed **before** the adult variant. |
| The clinic doesn't offer a service (e.g. orthodontics) | `bookable_by_ai: false`, `when_not_bookable: not_offered`. |
| The clinic offers a service but wants staff to book it | `bookable_by_ai: false`, `when_not_bookable: callback`. |
| A provider in the mapping leaves or becomes inactive | P1-19 disables the affected variant at load time and alerts the admin; the reason falls back to `when_not_bookable`. The clinic updates the mapping. |
| The Open Dental length differs from `duration_min` | Open Dental wins at booking time; P1-19 logs a warning so the file gets corrected. |
| Age needed but the patient's DOB isn't known yet | Doesn't happen in the flow: identification/registration (DOB) comes before appointment-type selection (P2-01 state order). If it does, treat the age as unknown: skip age-limited variants and use the first variant with no age limits. |
| The patient's words fit no code, or the model isn't confident | Out of scope here; P2-05 asks again, then uses `other` → callback. |
| A Tier 1 emergency | Never reaches this mapping; the P2-20 detector routes to the 911 script first. |
| The SME and the dentist disagree on a row | Mark the row `bookable_by_ai: false`, `when_not_bookable: callback` until resolved; record it in the mapping doc as an open item. |
| The workbook arrives with patient names (e.g. a screenshot of the schedule) | Delete it, ask for a clean copy, and tell the compliance advisor (no BAA yet). |

## 9. Security, HIPAA and PHI
- **No PHI.** Appointment types, provider abbreviations and operatory names are clinic setup data. The example phrases are invented.
- Provider names and abbreviations identify clinic staff, not patients. Keep the files in the private repo.
- Never collect screenshots of Open Dental's schedule or patient screens: they contain PHI and no clinic ↔ company BAA exists yet (P0-09).
- **Audit events:** not applicable here. Changes after go-live are audited by P4-11 / P1-12.

## 10. Testing
No application code. Checks:
- `check-jsonschema --schemafile backend/app/domain/clinic_config/schemas/appointment_types.schema.json backend/app/domain/clinic_config/seed/<clinic_slug>/appointment_types.yaml backend/tests/fixtures/clinic_config/appointment_types.example.yaml` passes.
- Negative checks: save copies of the example with (a) a missing reason code, (b) `bookable_by_ai: true` with no variants, (c) an unknown `when_not_bookable` value, and (d) an extra unknown field. Schema validation must fail for (b), (c) and (d). Case (a) is a P1-19 load-time rule; note it for the P1-19 tests.
- Reviewer checklist (not the author): all 15 codes are present; the rules in "Rules the schema can't express" hold by inspection; `appointment-type-mapping.md` matches the YAML row for row; no PHI; the rows agree with P0-01 Q3.

## 11. Acceptance criteria
- [ ] The JSON Schema is committed at the path in §6
- [ ] The synthetic example file contains all 15 reason codes and validates against the schema
- [ ] The pilot clinic YAML validates against the schema and satisfies every rule in "Rules the schema can't express" (checked by the reviewer)
- [ ] Every reason the AI may book has at least one variant with an appointment type, a duration and at least one provider
- [ ] `emergency_exam` exists and is `bookable_by_ai: true`, or the P0-03 owner is told that Tier 2 always creates a callback
- [ ] The rows agree with P0-01 Q3 (which kinds of appointments the AI may book)
- [ ] The SME and the dentist approved the mapping in writing (PDF saved)
- [ ] The P1-19, P1-20, P2-16, P2-21 and P4-11 issues have a comment with the file paths and version

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI: not applicable (no code); schema validation was run as in §10. Adding it to CI happens in P1-06 / P1-19.
- [ ] PR reviewed (HIPAA review if labelled `phi`): reviewed; no `phi` label because no PHI is handled
- [ ] No PHI in logs: no PHI in any file of this task
- [ ] Docs / README updated: `appointment-type-mapping.md` written and linked from the clinic decision log

## 13. Hand-off
| Task | Can rely on |
|---|---|
| P1-19 Clinic config | The schema, the load-time rules table, the example fixture and the pilot seed file |
| P1-20 Availability engine | Per reason: duration, eligible `od_prov_num`s and `operatory_nums` (empty = any) |
| P2-05 Intent + slot extraction | The fixed reason-code enum with example phrases |
| P2-16 Booking flow | The variant-selection rule and the `when_not_bookable` actions |
| P2-21 Tier 2 urgent path | The `emergency_exam` reason code |
| P1-17 Appointments adapter | `od_appointment_type_num` and `duration_min` for creating an appointment |
| P4-11 Admin mapping screen | The same schema; the screen edits this structure |

## 14. Open questions
| Question | Owner | Needed by |
|---|---|---|
| Does the pilot clinic use Open Dental appointment types at all? | Clinic Open Dental admin | Step 3 |
| Can the clinic see numeric IDs (AppointmentTypeNum, ProvNum, OperatoryNum) in Open Dental's setup screens? (Verify) | Tech lead, with the test DB (P0-12) | Step 7 |
| What is the clinic's Open Dental time increment (5/10/15 min)? | Clinic Open Dental admin | Step 6 |
| Is the 15-code list right, or does the dentist want codes added before the schema is frozen? | Tech lead, with the dentist | Step 5 |

## 15. References
- Plan §1 (principles 2 and 4), §4.3 (model routing: booking is deterministic), §4.6 (scheduling), §4.8 (emergency tiers), §7 (clinic admin console: appointment type mapping), §13 Q3
- Open Dental API specification: https://www.opendental.com/site/apispecification.html
- JSON Schema 2020-12: https://json-schema.org/draft/2020-12/release-notes
- check-jsonschema: https://check-jsonschema.readthedocs.io/
- Related tasks: P0-01, P0-03, P0-12, P1-17, P1-18, P1-19, P1-20, P2-05, P2-16, P2-21, P2-22, P4-11
