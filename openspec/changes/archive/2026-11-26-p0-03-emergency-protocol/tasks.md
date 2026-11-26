# Tasks: P0-03 Emergency protocol (issue #3)

## 1. Schema, example rules and test set

- [x] 1.1 Create `backend/app/domain/clinic_config/schemas/emergency_rules.schema.json`, copied exactly from spec §6. Verify: `check-jsonschema --check-metaschema` passes.
- [x] 1.2 Write `evals/emergency/emergency_cases.yaml` before the phrase lists, from the patient's side.
  - It needs ≥ 60 cases: ≥ 20 tier1 (≥ 3 per Tier 1 category, ≥ 3 negated, ≥ 3 voice-transcript style), ≥ 3 crisis, ≥ 15 tier2 (every category), ≥ 10 tier3, ≥ 10 none and ≥ 5 uncertain.
  - Verify: a script counts the mix and confirms every minimum is met.
- [x] 1.3 Create `backend/tests/fixtures/clinic_config/emergency_rules.example.yaml` (`status: draft`, `rules_version` "0.1"). It holds all 15 draft categories with 5–15 phrases or co-occurrence groups each, the 5 tier actions and the 7 scripts from spec §6. Verify: `check-jsonschema` passes.
- [x] 1.4 Check the rules the schema can't express with a scratchpad script: unique IDs, script references, tier/prefix match, Tier 3 reason codes from the P0-02 list, URGENT and `stop_booking` flags, allowed placeholders, reviewer fields. Also run the advice-words grep from spec §10 on the `text:` lines. Verify: 0 violations and no advice-word matches.

## 2. Dry run

- [x] 2.1 Build a throwaway reference matcher in the scratchpad that implements spec §6 matching rules 1–6, and run it over the test set. Tune the phrases (never with single-sentence fixes) until the pass criteria hold:
  - 100% of tier1 and crisis cases correct;
  - 0 under-triage;
  - ≥ 95% exact;
  - over-triage reported.

  Verify: the matcher's summary shows the criteria met, or each failing case is listed as a gap.
- [x] 2.2 Write `evals/emergency/dry-run-results.csv` (id, utterance, expected, accept_also, got, category, pass) and a summary of the gaps. Verify: the CSV has one row per test case.

## 3. Readable protocol and dentist review

- [x] 3.1 Write `docs/discovery/emergency-protocol.md` for the dentist, with no YAML.
  - One section per tier: the categories, example phrases, the exact scripts and what happens next.
  - The status lifecycle, a note that symptoms are PHI at runtime (log only category ID and tier), and the open questions.

  Verify: every category and script in the example file appears in the document.
- [x] 3.2 Dentist review (Dr. Casey Example, protocol owner per decision-log Q4a; copy to the compliance advisor). Record every comment and our change, plus the answers to all 5 open questions from spec §14, in `docs/discovery/emergency-protocol-feedback-2026-11-26.md`. Verify: each item has a "change made" or "not changed because".
- [x] 3.3 Apply the feedback. Update the phrases, scripts and test set as agreed (rerun 1.4 and 2.1–2.2), and create `backend/app/domain/clinic_config/seed/example-dental-clinic/emergency_rules.yaml` with `rules_version` "0.2", `status: clinic_reviewed` and `reviewed_by`/`reviewed_on`. Verify: schema validation, the rules check, the advice check and the dry-run criteria all pass on the seed.

## 4. Decisions, links and notifications

- [x] 4.1 Append a `DECISIONS.md` row for the resolved open questions. Add revision row `Q4a-r2` to the clinic decision log ("urgent slot within 24 hours") and bump the log to v1.1. Verify: the decision log keeps the original Q4a row unchanged.
- [x] 4.2 Link `emergency-protocol.md` and the feedback file from the decision log and `docs/discovery/README.md`. Add a "Pending notifications" table in the protocol doc for P2-20, P4-11, P5-01 and P5-07 (paths, `rules_version` 0.2, known gaps). Set #3 to ✅ in the Phase 0 README. Verify: all relative links resolve.

## 5. Finish

- [x] 5.1 Commit with a one-line descriptive message, ask the user before pushing `feature/phase-0-discovery-compliance`, and after the push close issue #3 with a comment listing the files and the known gaps. Verify: `git log -1 --format=%s` is one line, and #3 shows as closed under #17.

## Workflow follow-up

- Archive with `/opsx:archive p0-03-emergency-protocol` when the user asks (sync the `emergency-triage-rules` spec).
