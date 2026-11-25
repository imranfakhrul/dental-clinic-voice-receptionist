# Design: P0-01 Discovery workshop

## Context

- The repo has only planning material (`dental-ai-tasks/`, `openspec/`) and no `docs/` folder yet. P1-01 will build the monorepo later and keep `docs/discovery/` as it is.
- On GitHub only the Phase 0 issues exist (#1–#16, with parent #17). Issues for later phases (P1-16, P2-14, …) have not been created yet.
- The spec's "Feeds tasks" columns still list seed task IDs, some of which were merged into other tasks (e.g. P2-14 → P2-12, P1-17 → P1-16; see `dental-ai-tasks/tasks/_CONSOLIDATION.md`).

## Goals / Non-Goals

**Goals:**
- The pre-read, questionnaire, log template and review checklist are complete enough to send to the clinic as they are.
- The question IDs and the log format match spec §6 exactly, so that downstream tasks can cite "P0-01 Q10".
- Every human step is visible in `tasks.md`, so the issue cannot be closed before the clinic signs off.

**Non-Goals:**
- Any application code or automation.
- Contacting the clinic. That is a human step.
- Filling in real answers. These come from the workshop and are never guessed.

## Decisions

1. **Keep everything in `docs/discovery/`.** The template, the filled-in log and the sign-off PDF all live in the repo, so there is a single source that downstream tasks can cite. The log holds only clinic staff's work contacts, never PHI.
2. **Copy the questionnaire text from spec §6, not from memory.** Every question, Proposed default and "Feeds tasks" entry is copied exactly as written, including its `Verify:` markers. The IDs are never renumbered.
3. **Keep seed IDs in "Feeds tasks", and resolve them to surviving tasks only when notifying.**
   - The table keeps the spec's wording, so the documents stay consistent.
   - The notify step (spec §7 step 8) looks up each surviving task's issue in `_CONSOLIDATION.md`.
   - For phases whose issues don't exist yet, the notification is recorded in a "Pending notifications" section at the end of the log. It is posted when that phase's issues are created.
4. **Write the pre-read from plan §1–§2 in plain language.**
   - It has no jargon and fits on at most 2 pages.
   - It uses only made-up examples ("Jane Test, born 1985-03-14").
   - It explains "no live transfer" and the callback flow, and asks the clinic not to share real patient data.
5. **Turn spec §10 into a checklist file.** The reviewer works through `docs/discovery/review-checklist.md` before the log goes to the SME. That review is the "testing" for this documents-only task.

## Risks / Trade-offs

- [Real patient data is mentioned during the workshop] → The pre-read and agenda repeat the no-PHI rule. Spec §8 explains how to handle it, and the review checklist catches leftovers.
- [An answer conflicts with a task spec's Proposed default (e.g. B3 vs P1-16)] → The Notes column records "differs from default", and the notification states the conflict explicitly.

## Migration Plan

Not applicable: these are new documents only. Rollback means deleting `docs/discovery/` and the README link.

## Open Questions

These come from spec §14. Answering them changes who does the human steps and when, but not the documents:
- Which clinic is the pilot clinic, and is it confirmed? (project sponsor)
- Who from our team runs the workshop? Proposed: the tech lead and the compliance advisor. (tech lead)
- Remote or on site? Proposed: a remote video call, with the clinic's Open Dental admin at a clinic computer. (tech lead with the SME)
