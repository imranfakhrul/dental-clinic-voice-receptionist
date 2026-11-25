# Phase 0: Discovery & Compliance Foundation

**Branch:** `feature/phase-0-discovery-compliance` · **GitHub parent issue:** #17 (sub-issues #1–#16)
**Plan reference:** `dental-ai-tasks/plan/AI_Dental_Receptionist_Project_Plan.md` §8 Phase 0

## Goal
Settle everything the build depends on before any code or patient data moves:
- **Clinic decisions:** verification policy, appointment types and emergency protocol.
- **Signed BAAs** with every vendor that will touch PHI, and the clinic ↔ company BAA.
- **A locked-down Google Cloud project:** BAA accepted, HIPAA-covered products only, US-only.
- **Open Dental API access** with a test database.
- **Technical decisions:** the Gemini model versions and the architecture, with a PHI data-flow diagram.

## Exit criteria (deliverables)
- [ ] Architecture doc + PHI data-flow diagram (P0-14)
- [ ] Vendor/BAA matrix (P0-10)
- [ ] Conversation flow designs (P0-04)
- [ ] Risk assessment v1 (P0-11)
- [ ] All 16 sub-issues closed

## Tasks
Status values: ✅ done · 🟡 in progress · ⬜ not started.

### E0.1 Clinic discovery
| Issue | Task | Size | Depends on | Main output | Status |
|---|---|---|---|---|---|
| #1 | P0-01 Run discovery workshop with pilot clinic | M | - | `docs/discovery/` (pre-read, questionnaire, decision log, sign-off) | ✅ |
| #2 | P0-02 Appointment-type mapping | S | #1 | `docs/discovery/appointment-type-mapping.md` | ⬜ |
| #3 | P0-03 Draft emergency protocol (Tier 1/2/3) | M | #1 | `docs/discovery/emergency-protocol.md`, `evals/emergency/` | ⬜ |
| #4 | P0-04 Conversation flow designs | M | #1 | `docs/flows/` (overview, state machine), `evals/golden/` | ⬜ |

### E0.2 Compliance foundation
| Issue | Task | Size | Depends on | Main output | Status |
|---|---|---|---|---|---|
| #5 | P0-05 Google Cloud org/project + Google Cloud BAA | S | - | `docs/compliance/baa-google-cloud.md`, `infra/bootstrap/` | ⬜ |
| #6 | P0-06 Restrict projects to HIPAA covered products | M | #5 | `infra/org/`, `docs/compliance/hipaa-controls.md` | ⬜ |
| #7 | P0-07a Patient messaging channel decision (memo) | S | - | `docs/compliance/patient-messaging-decision.md` | ⬜ |
| #8 | P0-07 Messaging provider that signs a BAA | S | #7 | `docs/integrations/messaging-provider.md` | ⬜ |
| #9 | P0-08 Admin email route + BAA | S | #1 | `docs/integrations/admin-email.md` | ⬜ |
| #10 | P0-09 Clinic ↔ company BAA | S | #1 | `docs/compliance/baa/` | ⬜ |
| #11 | P0-10 Vendor/BAA matrix | S | #5 | `docs/compliance/vendors.yaml`, `scripts/compliance/` | ⬜ |
| #12 | P0-11 Risk assessment v1 | M | #11 | `docs/compliance/risk/` | ⬜ |

### E0.3 Technical setup decisions
| Issue | Task | Size | Depends on | Main output | Status |
|---|---|---|---|---|---|
| #13 | P0-12 Open Dental API keys + test database | S | #1 | `scripts/open_dental/`, `docs/integrations/open-dental-test-db.md` | ⬜ |
| #14 | P0-13 GA Gemini model versions per tier | S | #6 | `docs/adr/0001-gemini-models.md`, `evals/spike/p0-13/` | ⬜ |
| #15 | P0-14 Architecture doc + PHI data-flow diagram | M | #4, #14 | `docs/architecture/` | ⬜ |
| #16 | P0-15 Messaging sender registration + templates | M | #8, #7, #1 | `docs/messaging/templates.yaml`, `scripts/messaging/` | ⬜ |

## Order of work
```text
#1 P0-01 ──► #2 P0-02, #3 P0-03, #4 P0-04, #9 P0-08, #10 P0-09, #13 P0-12
#5 P0-05 ──► #6 P0-06 ──► #14 P0-13 ──┐
         └─► #11 P0-10 ──► #12 P0-11  ├─► #15 P0-14   (also needs #4)
#7 P0-07a ─► #8 P0-07 ──► #16 P0-15   (also needs #1)
```
Tasks with no dependencies can start right away: **#1, #5, #7**.

## How to work on a task in this phase
1. Read the spec, `dental-ai-tasks/tasks/<ID> *.md`. Its acceptance criteria and definition of done are the contract.
2. On this branch, run `/opsx:propose <id>-<slug>`, review the result, then run `/opsx:apply`.
3. Commit with one line: task ID plus what was done.
4. Update the task's **Status** in the tables above.
5. Push this branch (ask first). The senior merges the phase into `main`.

## Rules for this phase
- **No PHI anywhere.** No BAA with the clinic exists until P0-09 is done, so all examples are made up.
- **No vendor receives data before its BAA is signed.** Record every vendor in the vendor/BAA matrix (P0-10).
- **US-only, HIPAA-covered Google Cloud products only** (P0-05, P0-06).
