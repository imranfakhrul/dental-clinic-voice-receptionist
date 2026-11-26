# Proposal: P0-03 Draft emergency protocol (Tier 1/2/3) for clinic review (GitHub issue #3)

## Why

Missing an emergency is the most serious safety risk in the project. The pilot target is **100% emergency escalation in tests** (plan §11, §12).

The design is **rules first, model second** (plan §4.3, §4.8):
- a deterministic phrase detector runs on every patient turn;
- a model may only *raise* the result, never lower it;
- when in doubt, the case becomes an URGENT callback.

This task writes those rules, the exact words the AI says, and a labelled test set that proves the target. The clinic's dentist must review them.

Without it:
- P2-20 (detector) has nothing to detect against;
- P2-21 (scripts, now part of P2-20) would get scripts written by developers instead of being clinically reviewed;
- there's no test set to measure the 100% target.

The only dependency was P0-01 (#1), which is closed. The decision log gives:
- **Q4a:** the protocol owner, Dr. Casey Example, and the headline rules;
- **B6:** the callback promise;
- **Q4b:** the after-hours mailbox.

Source of truth: `dental-ai-tasks/tasks/P0-03 Document draft emergency protocol (Tier 1-2-3) for clinic review.md` (approved).

## What Changes

**Schema and rules files:**
- **JSON Schema** `backend/app/domain/clinic_config/schemas/emergency_rules.schema.json`, copied exactly from spec §6.
- **Synthetic example rules** `backend/tests/fixtures/clinic_config/emergency_rules.example.yaml`. It holds every draft category: 5 Tier 1, crisis, 5 Tier 2 and 4 Tier 3. It also holds all 7 scripts and the tier actions, written in plain patient language with 5–15 phrases or co-occurrence groups per category.
- **Clinic rules** `backend/app/domain/clinic_config/seed/example-dental-clinic/emergency_rules.yaml`. These are the example rules after the dentist's feedback, at `status: clinic_reviewed`.

**Test set and dry run:**
- **Labelled test set** `evals/emergency/emergency_cases.yaml`: at least 60 synthetic utterances in the required mix. That's ≥20 Tier 1 (with negations and voice-transcript forms), ≥3 crisis, ≥15 Tier 2, ≥10 Tier 3, ≥10 none and ≥5 uncertain.
- **Dry run results** `evals/emergency/dry-run-results.csv`: every case, the result under the spec's matching rules, and pass or fail against the criteria. It also lists the cases the rules alone don't catch, which P2-20's model check must cover.

**Documents for the dentist:**
- **Readable protocol** `docs/discovery/emergency-protocol.md`, written for the dentist with no YAML in it. It has one section per tier, with the categories, example phrases, the exact scripts, what happens next, and a note that symptoms are PHI at runtime.
- **Feedback record** `docs/discovery/emergency-protocol-feedback-YYYY-MM-DD.md`. It records the dentist's review comments item by item, with our change or reason, and the answers to the 5 open questions in spec §14.

**Other updates:**
- **Decisions and links.** Resolved open questions go into `dental-ai-tasks/DECISIONS.md`. The decision log links to the protocol and the feedback file. If the dentist changes the meaning of decision-log row Q4a, it gets a revision row (`Q4a-r2`). The Phase 0 README marks #3.
- **Pending notifications** for P2-20 (absorbs P2-21), P4-12 (part of P4-11), P5-01 (absorbs P5-02) and P5-07 (absorbs P5-15). Those issues don't exist yet.

No application code: the detector is P2-20, and its runtime loading is P1-19.

## Capabilities

### New Capabilities
- `emergency-triage-rules`: the per-clinic emergency rules. This covers the tiers and categories, the deterministic matching rules, the precedence and negation handling, the tier actions and fixed scripts, the review-status lifecycle, and the labelled test set with its pass criteria.

### Modified Capabilities
- None. `appointment-type-mapping` is used unchanged: Tier 2 books into `emergency_exam`, and Tier 3 maps to existing reason codes.

## Impact

- **New paths:** `backend/app/domain/clinic_config/{schemas,seed}/…/emergency_rules*`, `backend/tests/fixtures/clinic_config/emergency_rules.example.yaml` and `evals/emergency/`. The `evals/` directory is new.
- **Downstream contract:** P2-20 (detector and scripts), P2-22 / P2-24 (URGENT callbacks), P4-12 (rules editor and status lifecycle), P5-01 (imports the test set) and P5-07 (final `approved` sign-off).
- **Safety:**
  - Scripts contain no medication, home-remedy or treatment advice; the spec's advice-words check enforces this.
  - Tier 1 and crisis matches can never be silenced by a negation word.
- **Privacy:** every phrase and test utterance is synthetic. At runtime, though, the symptoms a patient describes are PHI, so P2-20 must log only the category ID and tier.
