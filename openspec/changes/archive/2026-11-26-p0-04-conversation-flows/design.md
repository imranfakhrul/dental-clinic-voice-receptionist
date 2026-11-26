# Design: P0-04 Conversation flow designs

## Context

- **Branch:** `feature/phase-0-discovery-compliance`. P0-01, P0-02 and P0-03 are archived. Their outputs are inputs here:
  - the decision log answers Q1, Q2, Q5, Q6, B4 and B6;
  - the 15 reason codes and `when_not_bookable` actions;
  - the emergency results and tier actions.
- **The spec predates several decisions** (see proposal.md, Why): #157, #170, #174, #185 and #256. In particular, the spec's example diagram still shows `BOOK → CONSENT`, which #256 removed.
- **Downstream specs already use event names.** These include `verify_attempt_limit` and `verification_locked` (P2-12), `slot_chosen`, `committed`, `commit_conflict` and `no_suitable_slot` (P2-16), `consent_done` (P4-02), `change_requested` (#174) and `emergency_resume` (P2-20). The YAML must match them, or P2-01 and its consumers won't line up.
- **Tools:** the scratchpad virtual environment has `check-jsonschema` (recreate it if it's gone). Node 22 and npx are available for a local Mermaid render check.

## Goals / Non-Goals

**Goals:**
- One authoritative YAML that validates, passes every consistency rule in spec §6, and includes the later decisions.
- Eight flow documents and eight golden conversations that provably agree with the YAML.
- A per-slot PHI list that P0-14 can use as is.
- Review by the tech lead and the SME recorded item by item, with all 5 open questions answered.

**Non-Goals:**
- No state machine code, slot storage, prompts or wording, tool schemas or guard enforcement. Those belong to P2-01, P2-05, P2-07, P1-22 and P2-08.
- No voice-specific timing (P3). The flows are the same for voice and text.

## Decisions

1. **The YAML is written by hand, and the diagrams are generated from it.**
   - A scratchpad script draws each flow's Mermaid diagram from the YAML, keeping only the transitions between that flow's states (plus its failure exits). The full overview diagram is drawn the same way.
   - The output is pasted into the documents. Diagrams therefore can't drift from the table, which carries out "the YAML wins" mechanically.
   - Step tables, failure branches and clinic points are written by hand.
   - *Alternative:* hand-drawn diagrams. Rejected: 8 diagrams × ~15 edges is where drift happens.
2. **Event names come from the downstream specs.** Before finishing the YAML, the event and action names in P2-01, P2-05, P2-12, P2-15, P2-16, P2-18, P2-20, P2-22 and P4-02 are collected.
   - Where a spec names an event, the YAML uses that name. Where specs disagree with each other or with P0-04's spec, the YAML picks one, and the review file lists each case for the owning task.
   - The spec §6 excerpt names are kept as written.
3. **The later decisions are applied directly, not left as open questions:**
   - **#256:** `AVAILABILITY --slot_chosen [consent_unknown]--> CONSENT --consent_done--> CONFIRM`, `BOOK --committed--> WRAP_UP`, and cancel never asks for consent.
   - **#174:** a `change_requested` transition from `CONFIRM` (and from the registration and callback confirmation steps) to each collecting state.
   - **#185:** global `add_patient` and `switch_patient`.
   - **#170:** the intent `complaint`. It's answered in `INTENT`, and a yes fires `human_requested`.
   - **#157:** config names `conversation.not_understood_limit` (2) and `verification.max_attempts` (3).
4. **Context values are slots with `phi: false`:** `intent`, `operation`, `urgent`, `resume_state` and `active_person`.
   - Person scoping (`p{index}:{slot}`, #185) is an engine concern for P2-01. It's described in `overview.md`, because the schema from spec §6 has no field for it and must be copied unchanged.
5. **Extra guards are added only when determinism needs them.** Examples: `urgent` to choose the urgent availability window, and `household_has_room` for `add_patient`.
   - Each extra guard is defined in `overview.md`, with the task that enforces it, and listed in the review file.
   - The 6 guards from the spec stay as defined.
6. **The consistency rules and golden walk-through are checked by throwaway scratchpad scripts**, the same approach as P0-03's matcher. P2-01 owns the real tests (DECISIONS #155).
   - **The checker** covers every rule in spec §6 "Rules the schema can't express": references, reachability, exits, `END` has no exits, no duplicates, the `BOOK` entry guards, the verified-only side states, and the 12-tool list.
   - **The golden walker** checks that each `expect_state` can be reached from the previous one through defined transitions. A path of several transitions is allowed, because one message can fill several slots at once (spec §8, first edge case). Each `expect_tools` entry must be allowed in a state on that path.
   - The results go into the review file.
7. **Mermaid rendering is checked locally** with `npx @mermaid-js/mermaid-cli`, run from the scratchpad. It's a dev-only tool that handles no PHI and isn't added to the repo. If it can't be installed, the user checks the diagrams in the editor's Markdown preview during review.
8. **Review: I play both roles.**
   - **Tech lead Riley Tech:** reviews the YAML and the guards.
   - **Clinic SME Alex Sample:** reviews the flow documents and the clinic-dependent points.
   - **Answers to the spec §14 open questions:**
     1. **When is consent asked?** Before the confirmation card. This is already settled by #256.
     2. **`record_consent`:** confirmed as owned by P4-02. P1-22 and P2-08 must list it.
     3. **Limits:** 2 failed understanding attempts and 3 failed verifications are kept. Both are configurable.
     4. **Two intents in one message:** the proposed behaviour in spec §8 is accepted.
     5. **Checking a family member's appointments:** allowed only after `add_patient` with that person's own verification (#185). It's never allowed without verifying.

     All of this, plus the comments and changes, is recorded in `docs/flows/review-2026-11-26.md`. `version` goes from "0.1" to "0.2" after the review.
9. **No PR, so records live in the repo.** The review file replaces "record in the PR". The spec §7 notification list is mapped to surviving tasks:
   - P2-02 → P2-01; P2-09 → P2-08; P2-14 → P2-12; P2-17 → P2-16; P2-21 → P2-20; P2-24 → P2-22; P5-02 → P5-01.

   They go in a "Pending notifications" table in `overview.md`.

## Risks / Trade-offs

- **[Downstream specs use conflicting event names]** → Decision 2 records each conflict and the name chosen. The owning task aligns when it's built. P2-01 loads the YAML, so the YAML is what counts.
- **[The overview diagram is too large to read]** → It's generated in full, as the spec requires. Each flow document shows only its own subset, which is the readable view.
- **[Allowing multi-step paths in the golden walker could hide a missing transition]** → Each `expect_tools` entry must be allowed on the path, and each golden file is also reviewed by hand against its step table.
- **[Generated diagrams lose hand-written labels]** → Edge labels are the event name plus guards in brackets, which is exactly what P2-01 needs. Readable explanations go in the step tables.

## Migration Plan

Not applicable: new files only, plus one DECISIONS row and two README edits.
