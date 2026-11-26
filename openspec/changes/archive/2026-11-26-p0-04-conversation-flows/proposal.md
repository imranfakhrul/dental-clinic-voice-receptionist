# Proposal: P0-04 Write conversation flow designs (GitHub issue #4)

## Why

The core design rule is "the LLM talks, deterministic code acts" (plan §1, §4.1). A deterministic state machine owns every conversation, and the model only understands and phrases. That works only if the state machine is fully specified before code starts.

Plan §4.1's state list is incomplete. It has no states for checking an appointment, FAQ, WhatsApp consent or ending the session, and it doesn't say how side branches return to the main flow.

Without this task:
- P2-01 would invent the state list;
- P2-08 (which tools each state may call, and the preconditions it absorbed from P2-09) would have nothing to enforce;
- P0-14 couldn't show where PHI is collected.

The only dependency is P0-01 (#1), which is closed. Its decision log supplies the clinic answers the flows depend on: Q1 (verification identifiers), Q2 (new-patient review), Q5 (24-hour cancellation window), Q6 (insurance goes to a callback), B4 (create new patients immediately) and B6 (callback promise). P0-02 supplies the reason codes, and P0-03 the emergency results and tier actions.

Source of truth: `dental-ai-tasks/tasks/P0-04 Write conversation flow designs.md` (approved).

Several decisions logged after the spec was written change P0-04's contract and are applied here:
- **DECISIONS #256:** WhatsApp consent is asked **before** the confirmation card (`AVAILABILITY → CONSENT → CONFIRM`). `BOOK → CONSENT` is removed, and cancel never asks.
- **DECISIONS #174:** every confirmation step shows a confirmation card, and a new event `change_requested` returns to the state that collects the changed field.
- **DECISIONS #185:** household booking, with global events `add_patient` and `switch_patient` and up to 4 persons per chat.
- **DECISIONS #170:** a new intent `complaint`.
- **DECISIONS #157:** the verification limit is config `verification.max_attempts` (not `conversation.verify_attempt_limit`).

## What Changes

**State machine (the contract P2-01 implements):**
- `docs/flows/state_machine.schema.json`: the JSON Schema, copied exactly from spec §6.
- `docs/flows/state_machine.yaml`: the authoritative table. It has the 18 states, the slots with PHI flags, the guards, every transition with its guards and action, and the global interrupts, with the later decisions above folded in.

**Flow documents, in `docs/flows/`:**
- `overview.md`: the full state diagram, the global-interrupt table, the slot list with PHI flags, the resume rules and the per-slot PHI list for P0-14.
- Eight flow documents: `book-existing-patient.md`, `book-new-patient.md`, `reschedule.md`, `cancel.md`, `check-appointment.md`, `faq.md`, `emergency.md` and `callback.md`. Each has its purpose and entry conditions, a Mermaid diagram generated from the YAML, a step table, failure branches, and clinic-dependent points marked `(P0-01 Qn)`.

**Golden conversations:**
- `evals/golden/<flow>.yaml`: eight synthetic conversations, one per flow, asserting states, slots and tool calls (not wording).

**Review and records:**
- `docs/flows/review-2026-11-26.md`: the consistency-check results, the tech lead's and the clinic SME's review comments item by item, and the answers to the 5 open questions in spec §14. There's no PR, so this file stands in for "recorded in the PR".
- A `DECISIONS.md` row for the resolved open questions.
- A "Pending notifications" table in `overview.md` for the surviving downstream tasks. They have no GitHub issues yet, so this follows the P0-01 to P0-03 pattern.
- Links from the root README and `docs/flows/`. Issue #4 marked ✅ in the Phase 0 README.

No application code. The consistency checker and the golden-file walker are scratchpad tools, because P2-01 automates both as unit tests.

## Capabilities

### New Capabilities
- `conversation-state-machine`: the authoritative conversation state machine. It covers the states, slots with PHI flags, guards, transitions, global interrupts and consistency rules, the flow documents derived from it, and the golden conversations that test it.

### Modified Capabilities
<!-- none: appointment-type-mapping and emergency-triage-rules are used as inputs, not changed -->

## Impact

- **New folders:** `docs/flows/` and `evals/golden/`.
- **Edited files:** `dental-ai-tasks/DECISIONS.md` (one row), the root `README.md` (link to `docs/flows/overview.md`) and `docs/phase-0-discovery-compliance/README.md` (#4 status).
- **Downstream contracts:**
  - P2-01 (which absorbed P2-02) loads this YAML.
  - P2-08 (which absorbed P2-09) enforces `allowed_tools` and guards.
  - P2-05 uses the intent values and event names.
  - P2-12, P2-15, P2-16, P2-18, P2-20 and P2-22 implement the flows.
  - P4-02 owns `CONSENT` and `record_consent`, and P1-22 must list `record_consent`.
  - P0-14 uses the PHI list, and P5-01 (which absorbed P5-02) imports the golden conversations.
- **No PHI:** all names, dates and numbers are synthetic, for example "Jane Test", ZIP 97201 and 555-01xx phone numbers.
