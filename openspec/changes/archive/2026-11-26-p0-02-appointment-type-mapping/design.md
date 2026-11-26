# Design: P0-02 Appointment-type mapping

## Context

- **Branch and repo:**
  - Work happens on `feature/phase-0-discovery-compliance`, which already holds P0-01's `docs/discovery/`.
  - The repo has no `backend/` yet; P1-01 will create the monorepo around the paths used here.
- **Decision-log inputs** (`docs/discovery/clinic-decision-log.md` v1.0):
  - **Q3:** the AI books new-patient exam, recall/cleaning and limited (emergency) exam only; everything else goes to a callback.
  - **B5:** America/New_York; new-patient block Tue/Thu 08:00–10:00; emergency block 11:00–12:00. These are P1-19 data, not part of this file.
  - **Staff:** the dentist/owner is Dr. Casey Example. No hygienists are named yet, so the clinic workbook adds them.
- **Tools on the machine:**
  - available: Python 3 with `PyYAML` and `jsonschema`;
  - missing: `check-jsonschema` and `openpyxl`.

## Goals / Non-Goals

**Goals:**
- The schema matches spec §6 exactly. Both YAML files validate, and the four negative checks from spec §10 behave as specified.
- The clinic seed agrees with Q3 and satisfies every rule in "Rules the schema can't express".
- The readable table matches the seed YAML row for row.

**Non-Goals:**
- No loader or runtime enforcement (P1-19), and no Open Dental API calls (P1-18 / P0-12).
- No new reason codes: the list of 15 stays fixed.

## Decisions

1. **Commit the files at their final paths now** (`backend/app/domain/clinic_config/...`, `backend/tests/fixtures/...`), not in a temporary shared location.
   - The repo exists, and P1-01 creates the rest of `backend/` around them.
   - *Alternative:* keep them under `docs/` and move them later. Rejected, because the paths would change twice.
2. **The clinic slug is `example-dental-clinic`**, derived from the decision-log clinic name and matching the schema pattern.
3. **The seed's Open Dental values come from the clinic workbook.**
   - Values: time increment 10 minutes; appointment types New Patient Exam 60, Recall 60, Child Recall 40 and Limited Exam 30; providers DDS1 (Dr. Casey Example), HYG1 and HYG2; operatories 1–4.
   - The seed carries numeric IDs, so it can be `status: approved` once signed off.
   - Every value is clinic setup data, and none is patient data.
4. **The example fixture is separate from the seed.** It uses the slug `example-dental` and deliberately different numbers. It exercises every structural case: two variants with different patient types, an age-limited child variant, `not_offered` and `callback`. Tests then don't depend on clinic data that may change.
5. **Bookability follows Q3 strictly.**
   - Bookable: `new_patient_exam`, `recall_cleaning` (adult variant plus a child variant) and `emergency_exam`.
   - `ortho_consult` is `not_offered`.
   - All other reasons are `callback`.
   - `child_visit` is a callback, because Q3 doesn't allow a separate child visit type. Children's recalls are booked through `recall_cleaning`'s child variant.
6. **Validate in a throwaway virtual environment.**
   - `python3 -m venv <scratchpad>/venv`, then `pip install check-jsonschema openpyxl` into it.
   - This runs the spec's own `check-jsonschema` command without adding project dependencies.
   - If installing fails, `python3 -c 'jsonschema.validate(...)'` (already installed) is the fallback, with the same Draft 2020-12 schema.
7. **Check the rules the schema can't express with a throwaway script.** Each rule is checked by a one-off script in the scratchpad (not committed). The result is recorded in the review section of the mapping doc. The real enforcement is written in P1-19.
8. **The workbook is generated with `openpyxl`** from the same data as the seed. It has four tabs, plus a "How to fill" note that says "setup lists only, never patient screens".
9. **Sign-off and notifications follow P0-01's pattern.**
   - The approval email is saved as a one-page PDF.
   - The downstream issues (P1-19, P1-20, P2-16, P2-21, P4-11) don't exist yet, so they go into a "Pending notifications" table in the mapping doc.
   - The decision log links to the mapping doc.

## Risks / Trade-offs

- **[Open Dental field names and pattern increments are unverified]** → Keep the spec's `Verify:` markers in the mapping doc. P0-12 / P1-18 confirm them against the test database.
- **[Durations may differ from Open Dental's own type lengths]** → Open Dental wins at booking time (rule in spec §6). The mapping doc records each duration's source.
- **[A virtual environment can't be created (no network)]** → Validate with the installed `jsonschema` library instead. Write the workbook as a hand-built `.xlsx` (a zip of XML) only if `openpyxl` can't be installed, and say so in the commit.
- **[Q3 later allows more types]** → Bump `mapping_version` (major) and get sign-off again (spec §7 step 9).

## Migration Plan

Not applicable: new files only. Rollback means deleting the new files and the decision-log link.
