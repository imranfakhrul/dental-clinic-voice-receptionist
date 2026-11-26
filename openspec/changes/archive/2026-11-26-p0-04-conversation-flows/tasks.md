# Tasks: P0-04 Conversation flow designs (issue #4)

## 1. Schema, states and slots

- [x] 1.1 Create `docs/flows/state_machine.schema.json`, copied exactly from spec §6. Verify: `check-jsonschema --check-metaschema` passes.
- [x] 1.2 Collect the event and action names that downstream specs already use (P2-01, P2-05, P2-12, P2-15, P2-16, P2-18, P2-20, P2-22, P4-02, plus DECISIONS #157, #170, #174, #185, #256) into a scratchpad list. Note each name conflict for the review file. Verify: every flow's key events (identify outcomes, verify results, slot choice, consent, confirm, commit, conflict, emergency, callback) have a chosen name.
- [x] 1.3 Start `docs/flows/state_machine.yaml` (`version` "0.1"):
  - the 18 states from spec §6 with `kind`, `allowed_tools`, `collects` and `resumes`;
  - every slot with its `phi` flag, including the context slots `intent`, `operation`, `urgent`, `resume_state` and `active_person`;
  - the 6 spec guards, plus any extra guards that determinism needs (design decision 5);
  - the global transitions, including `add_patient` and `switch_patient`.

  Verify: `check-jsonschema` passes.

## 2. Flows (transitions and documents, in spec order)

Each task adds the flow's transitions to the YAML and writes `docs/flows/<flow>.md`: purpose and entry conditions, a Mermaid diagram generated from the YAML, a step table (state → what the AI asks or says → tools → slots with PHI marked → exits), failure branches, and clinic points marked `(P0-01 Qn)`.

- [x] 2.1 `book-existing-patient`:
  - neutral `IDENTIFY` and the match outcomes;
  - `VERIFY` with the shared attempt limit;
  - `APPOINTMENT_TYPE` with `bookable` / not bookable (P0-02);
  - `AVAILABILITY → CONSENT → CONFIRM` (#256);
  - `change_requested` (#174);
  - `BOOK` with `commit_conflict`, then `WRAP_UP`.
- [x] 2.2 `book-new-patient`: no match, then confirm spelling and DOB once more, then `REGISTER` with a registration card. Create immediately (P0-01 B4); if the create is refused or ambiguous, go to `CALLBACK_REQUEST`. The booking is flagged for staff review (P0-01 Q2).
- [x] 2.3 `reschedule`: verified-only entry, pick the appointment, check the 24-hour window (P0-01 Q5), then the shared `AVAILABILITY`, `CONSENT`, `CONFIRM` and `BOOK` with `operation=reschedule`.
- [x] 2.4 `cancel`: verified-only entry, pick the appointment, check the window. `CONFIRM → BOOK` uses guards `[verified, confirmation_recorded, outside_cancellation_window]`, with no consent step.
- [x] 2.5 `check-appointment`: verified-only entry. Family members only through `add_patient` with that person's own verification (#185).
- [x] 2.6 `faq`: `resume_state` saving and returning. Insurance beyond the accepted-insurer list goes to `CALLBACK_REQUEST` (P0-01 Q6).
- [x] 2.7 `emergency`:
  - Tier 1 / crisis: run the script, create the URGENT case, repeat the script until `END`, and never resume;
  - uncertain: URGENT callback;
  - Tier 2 urgent path: `urgent=true` and `emergency_exam`, through `IDENTIFY`/`VERIFY` if needed, then urgent `AVAILABILITY`. With no slot, an URGENT callback (P0-03).
- [x] 2.8 `callback`: collect details (new or existing patient), read back name and phone on a card, create one case per session and reason, then tell the patient the promise (P0-01 B6). Include `complaint` (#170).

## 3. Overview, golden conversations and checks

- [x] 3.1 Write `docs/flows/overview.md`:
  - the full state diagram, generated;
  - the global-interrupt table;
  - the slot list with PHI flags and person scoping (#185);
  - guard definitions, with the enforcing task for each;
  - the resume rules;
  - the PHI list for P0-14 (slot → collecting state → tools it's sent to).

  Verify: the PHI slots in the list exactly match the YAML slots with `phi: true`.
- [x] 3.2 Write 8 synthetic golden conversations `evals/golden/<flow>.yaml` in the spec §6 format. `book-existing-patient` covers the "everything in one message" case. Use only "Jane Test"-style names, ZIP 97201 and 555-01xx numbers. Verify: a PHI scan finds no real-looking data.
- [x] 3.3 Run the scratchpad consistency checker (every rule in spec §6 "Rules the schema can't express") and the golden walker (design decision 6). Fix the YAML until both pass. Verify: 0 violations, and all 8 golden files walk to their `end_state`.
- [x] 3.4 Render every Mermaid diagram locally (`npx @mermaid-js/mermaid-cli` in the scratchpad). Verify: 9 diagrams render without errors. If the tool can't be installed, note that and list it for the user's review.

## 4. Review and records

- [x] 4.1 Review, playing both roles:
  - **Tech lead Riley Tech:** the YAML and the guards.
  - **Clinic SME Alex Sample:** the flow documents and the clinic points.

  Apply the changes, bump `version` to "0.2", and rerun 3.3–3.4. Record every comment with "change made" or "not changed because", the consistency-check results, the event-name conflicts from 1.2 and the answers to the 5 open questions in spec §14 in `docs/flows/review-2026-11-26.md`. Verify: every item has an outcome, and the checks pass on v0.2.
- [x] 4.2 Append a `DECISIONS.md` row for the resolved open questions and the extra guards or events added. Verify: the new row is the last row, and no existing row changed.
- [x] 4.3 Add a "Pending notifications" table to `overview.md` for P2-01, P2-05, P2-08, P2-12, P2-15, P2-16, P2-18, P2-20, P2-22, P4-02 (and P1-22 for `record_consent`), P0-14 and P5-01, with paths and version 0.2. Link `docs/flows/overview.md` from the root `README.md`. Set #4 to ✅ in the Phase 0 README. Verify: all relative links resolve.

## 5. Finish (only after the user's review)

- [x] 5.1 Stop and wait for the user's review. They may edit or finish the work. Only after they give the go-ahead, archive the change (sync the `conversation-state-machine` spec), `git add`, make **one** commit with a one-line descriptive message (the work and the archive together), push `feature/phase-0-discovery-compliance`, and close issue #4 with a comment listing the files. Verify: one commit for the task, the branch matches origin, and #4 is closed under #17.
