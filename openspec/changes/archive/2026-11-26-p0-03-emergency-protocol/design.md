# Design: P0-03 Emergency protocol

## Context

- **Branch and existing files:** work happens on `feature/phase-0-discovery-compliance`. P0-02 already added `backend/app/domain/clinic_config/{schemas,seed/example-dental-clinic}` and the main spec `appointment-type-mapping`, whose reason codes this task reuses.
- **Decision-log inputs:**
  - **Q4a:** the owner is Dr. Casey Example. "Tier 2 → urgent slot today, else URGENT callback."
  - **B6:** URGENT callbacks are returned the same business day.
  - **Q4b:** one shared mailbox for all hours (relevant to Tier 2 after hours).
- **Tools:** the scratchpad virtual environment from P0-02 has `check-jsonschema` and `openpyxl`. Recreate it if it's gone.
- **The spec asks for a "hand dry run in a spreadsheet".** With at least 60 cases and 7 matching rules, doing it by hand is slow and error-prone.

## Goals / Non-Goals

**Goals:**
- The schema matches spec §6 exactly. Both rules files validate. The advice-words check is clean.
- The test set meets the required mix and the pass criteria, and every gap is listed for P2-20.
- The dentist review is recorded item by item, and all 5 open questions (spec §14) are answered.

**Non-Goals:**
- No production detector, model check, script runtime or callback creation (P2-20, P2-22).
- No `approved` status: that's P5-07 (which absorbed P5-15), through P4-12.

## Decisions

1. **The dry run uses a throwaway reference matcher in the scratchpad**, not a pen-and-paper pass.
   - It implements spec §6 matching rules 1–6 exactly: normalize, phrase, co-occurrence, negation, precedence.
   - It writes `evals/emergency/dry-run-results.csv`, the "spreadsheet" the spec asks for, with one row per case: expected, got, category, pass/fail.
   - The matcher isn't committed, because the real detector is P2-20's deliverable. Committing a second implementation would invite drift.
   - *Alternative:* a manual spreadsheet. Rejected as error-prone for a safety-critical check.
2. **Write the test set before tuning the phrases**, from the patient's side: everyday wording, transcripts without punctuation, filler words, symptoms described for a child or a parent. Then tune the phrase lists until the criteria hold.
   - A case is never "fixed" by adding a phrase that only fits that one sentence. Such cases are listed as gaps for P2-20's model check, so the test set keeps measuring what rules alone can do.
3. **Prefer multi-word phrases and co-occurrence groups over single words.** For example, "swollen" alone is never a phrase; it appears only in groups. This keeps over-triage of `none` and `tier3` cases at or under the proposed 10%.
4. **Separate example and clinic files**, following P0-02's pattern:
   - The example (`example-dental`, `rules_version` "0.1", `status: draft`) is the complete synthetic file for tests.
   - The clinic seed (`example-dental-clinic`) is the version after review: `rules_version` "0.2", `status: clinic_reviewed`, with `reviewed_by` and `reviewed_on` set. Version "1.0" is reserved for the `approved` sign-off in P5-07.
5. **The dentist review and its answers.** I play the clinic role, and the dentist is Dr. Casey Example. All answers are recorded in the feedback file:
   - **First-aid line for a knocked-out tooth:** no. We keep the "no advice" default, so every script has `contains_first_aid: false`.
   - **Crisis category and the 988 script:** kept.
   - **Urgent slot window:** **24 hours**. The dentist clarifies that decision-log Q4a's "today" means "within 24 hours", so a late-day request gets the next morning. This is recorded as revision row `Q4a-r2`, with the decision log bumped to v1.1, following the log's own rules.
   - **Clinic phone number in the Tier 1 / crisis scripts:** no. 911 and 988 are the only numbers given, so the patient isn't encouraged to call the clinic instead.
   - **Pain threshold:** 8–10 out of 10 is kept for Tier 2.
   - **Other feedback items:** the dentist also adds a few phrases, for example "dry socket" for post-extraction and "jaw locked" for trauma, and adjusts the wording of one script. Each item is logged with our change.
6. **Record decisions.** One `DECISIONS.md` row for the resolved open questions (crisis kept, no first-aid line, a 24-hour window, no clinic phone number in the emergency scripts).
7. **Notifications follow the P0-01/P0-02 pattern.** A "Pending notifications" table lists the surviving tasks, because those issues don't exist yet. It names P2-20 (absorbs P2-21), P4-11 (absorbs P4-12), P5-01 (absorbs P5-02) and P5-07 (absorbs P5-15), each with the paths, `rules_version` and the known gaps.
8. **Check the rules the schema can't express with a scratchpad script.** It covers unique IDs, script references, tier/prefix match, Tier 3 reason codes taken from the P0-02 list, the required URGENT and stop-booking flags, allowed placeholders, and reviewer fields. This mirrors P0-02's checker.

## Risks / Trade-offs

- **[The test set and phrases come from the same author, so the set may mirror the lists]** → Decision 2: the set is written first from the patient's side, single-sentence phrase fixes are banned, and the gaps are reported honestly.
- **[The rules can't catch every phrasing]** → That's expected and by design. Gaps go to P2-20's model check, which may raise results, and anything uncertain becomes an URGENT callback.
- **[Over-triage annoys patients and staff]** → It's tracked in the dry run against the proposed ≤10% limit. Over-triage is safe; under-triage target is 0.
- **[The reference matcher differs from P2-20's implementation]** → Both follow the same written rules in spec §6. P2-20 must reproduce the dry-run results on the same test set.

## Migration Plan

Not applicable: new files only, plus one decision-log revision row and one DECISIONS row.
