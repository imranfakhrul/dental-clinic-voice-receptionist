---
id: P6-04
title: Soft launch at pilot clinic
milestone: P6
epic: E6.1
size: L
labels: area:qa, area:ai, area:voice, type:chore
depends_on: P6-01, P6-02, P5-01, P5-12, P4-13a, P1-19, P1-03
status: approved
---

# P6-04: Soft launch at pilot clinic

## 1. Summary
Launch the assistant to real patients at the pilot clinic **in stages**, review what goes wrong every week, and tune it. This task absorbs **P6-05 (weekly review of callbacks and failed conversations)** and **P6-06 (tuning: prompts, vocabulary, routing, rules)**.

| Part | What happens |
|---|---|
| Staged launch | Stage A: **chat** only, clinic hours, 1 week, with a daily check-in. Stage B: add **WhatsApp reminders**. Stage C: add **voice**. Each next stage opens only when the stage gate KPIs are met |
| Pilot transcripts (optional) | Off by default. With the clinic's written consent, 14-day encrypted transcripts for reviewing failed conversations, visible only to two named reviewers, every view audited |
| Weekly review | Every Monday: label each failed conversation and callback with a cause, decide on fixes, write the weekly review document |
| Tuning | Prompt, vocabulary, routing and rule changes go through P5-01 evals and a two-person review; deployed on Thursdays; safety fixes on any day |
| Pause rules | Any safety event → the kill switch at once; weak quality → a review meeting |

Done means:
- the widget is live on the clinic website with all three channels;
- daily review notes exist for the first week and weekly review documents for every week after;
- the eval suite was green after every tuning change.

## 2. Why this matters
Plan §8 Phase 6:
- "Soft launch at one pilot clinic (e.g., limited hours or new bookings flagged for staff review)";
- "regular review of callback cases and failed conversations";
- "tune prompts, vocabulary, routing and rules".

Turning everything on at once would make it impossible to tell, for example, whether a drop in bookings came from voice latency or from a reminder confusing patients. A staged launch limits the harm of a surprise. Weekly reviews turn surprises into fixes, and the eval gate keeps those fixes from breaking something else.

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P6, Pilot Launch & Iteration**.
- **Transcript retention today:**
  - P0-01 Q9 agreed "no transcripts stored";
  - P1-19 has `privacy.transcript_retention_days` (0–30, currently 0);
  - nothing stores transcripts yet.

  Without transcripts, a review sees only codes, for example "ABANDONED in state CONFIRM after 2 not-understood". With them, the reviewer can see that the patient said "Thursday the 5th" and we offered Friday.
- **What already exists (approved):**
  - **P6-01:** pilot flags (`chat_enabled`, `voice_enabled`, `reminders_enabled`, `ai_hours`), the kill switch, the two-person turn-on, the staff guide.
  - **P6-02:** KPIs, the console insights page, the weekly digest.
  - **P4-13a:** the activity log (outcomes, states), callbacks, the AI-booked review, failed messages.
  - **P5-01:** evals, the fast set, the override rules.
  - **P5-03:** `voice-quality.yml`.
  - **P5-07:** the emergency rules sign-off process.
  - **P5-12:** runbooks, the alert watcher, the retention job.
  - **P2-04 / P2-05 / P3-03:** prompts, templates, phrase hints, router rules.

## 4. Scope
**In scope**
- Stage plan, stage gates, daily check-ins in week 1, the clinic communication for each stage.
- Optional pilot transcripts: storage, retention, viewer page, access control, audit.
- Weekly review process: failure taxonomy, review document template, issue filing.
- Tuning workflow: change types, review rules, release cadence, eval gates, emergency-rule changes through P5-07's process.
- Pause criteria and the link to the kill-switch runbook.

**Out of scope** (and which task covers it)
- KPI computation → P6-02
- The final report and the decision on wider rollout → P6-07
- New features requested by the clinic → backlog (post-MVP, plan §14)

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P6-01 | Go decision, flags, trained staff | Build the transcript feature and the review template in parallel |
| P6-02 | KPIs for the stage gates | Stage A can use the activity log counts until the page lands |
| Clinic consent | Written OK for pilot transcripts | Keep transcripts off (default) |

## 6. Interface contract

### Stages and gates (DECISIONS #282)
| Stage | Flags | Minimum length | Gate to move on (all must hold) |
|---|---|---|---|
| A: Chat | `chat_enabled: true` | 7 days and ≥ 50 conversations | 0 safety events; booking completion ≥ 60%; review lag ≤ 1 business day; Sarah agrees |
| B: + Reminders | `reminders_enabled: true` | 7 days and ≥ 30 reminders due | Above, plus reminder delivery ≥ 95%, 0 reminders for cancelled appointments, STOP handled |
| C: + Voice | `voice_enabled: true` | Continues to the end of the pilot | Above, plus voice latency p95 ≤ 2.5 s over the first 3 days |

- Every flag turn-on uses P6-01's two-person approval (tech lead + Sarah).
- The clinic places a short notice on its website for each stage, for example "New: book online with our virtual assistant"; the text is in `docs/pilot/clinic-comms.md`.
- Week 1 has a **daily check-in** of 15 minutes (team + Sarah): yesterday's numbers, callbacks, anything odd. Notes go in `docs/pilot/daily/<date>.md`.

### Pilot transcripts (optional; DECISIONS #282)
- **Default off.** Turned on only after the clinic signs `docs/pilot/transcript-consent.md`. The form states the purpose (quality review during the pilot), the retention (14 days), who can see transcripts (two named team reviewers), and the right to switch it off at any time.
- **Config:** `privacy.transcript_retention_days: 14`. This is file-only (P1-19 privacy section), so it changes through a release PR with prod approvals.
- **Storage (additive to P1-03):**

| Column | Type | Notes |
|---|---|---|
| `id` | uuid | PK |
| `clinic_id` | uuid | FK |
| `session_id` | uuid | FK `sessions` |
| `turn_index` | int | |
| `speaker` | text | `PATIENT`, `ASSISTANT` |
| `channel` | text | `TEXT`, `VOICE` |
| `text_enc` | bytea | Field-encrypted (P1-05) |
| `created_at` | timestamptz | |
| `expires_at` | timestamptz | `created_at + retention`; index for the purge |

  Table `conversation_transcripts`. Writes happen from P2-01's turn pipeline, only when the retention is > 0. Voice turns store the **final** transcript text, never audio.
- **Purge:** P5-12's retention job deletes rows past `expires_at` (new row in its policy table). Setting the retention to 0 deletes all rows at the next run.
- **Viewer:** console page `/admin/review/sessions/{id}`:
  - needs the new permission `TRANSCRIPT_READ`, held only by a new role `REVIEWER` (P1-13 additive);
  - the role is assigned to exactly two named team members, with MFA;
  - every view writes audit `transcript.view {session_id}`;
  - the page shows a "Confidential – PHI" banner and has no copy or export button (text selection is still possible, so the policy in P5-14 applies);
  - the P5-14 monthly access review covers the role.
- Clinic staff don't get `TRANSCRIPT_READ` (they already have the callback details they need).

### Weekly review (absorbs P6-05; DECISIONS #282)
Every Monday, 1 hour, with the AI lead, the tech lead and a QA engineer. Sarah joins for 15 minutes.
Inputs:
- the P6-02 weekly digest;
- the activity log filtered to CALLBACK, ABANDONED, ERROR and CHANGE_REFUSED;
- every callback case of the week (codes and summaries in the console);
- transcripts for sampled sessions, if enabled;
- failed messages;
- alerts.

**Failure taxonomy** (one label per failed session, `docs/pilot/taxonomy.md`):
| Label | Meaning |
|---|---|
| `NLU_MISUNDERSTOOD` | Intent or slot extracted wrongly |
| `STT_ERROR` | Voice transcription wrong |
| `POLICY_GAP` | Clinic rule missing or wrong in config |
| `NO_AVAILABILITY` | Genuine lack of slots |
| `IDENTITY_FAIL` | Could not verify (as designed or a bug) |
| `OD_ERROR` | Open Dental error or outage |
| `PATIENT_LEFT` | Abandoned without a system cause |
| `PROMPT_TONE` | Reply unclear or awkward |
| `ROUTING` | Wrong model tier or latency |
| `BUG` | Code defect |
| `EXPECTED_CALLBACK` | Callback was the right outcome (for example a billing question) |

Output: `docs/pilot/weekly/<yyyy-ww>.md` (template below) and GitHub issues labelled `pilot`, with `tuning` or `bug`, and the taxonomy label.
```markdown
# Pilot week 2027-W12
## Numbers (from P6-02 digest)            ## Stage / flags
## Failed sessions by label (counts)      ## Callbacks by reason_code (counts)
## Top 3 problems and decisions           ## Changes shipped last week and their effect
## Safety events (must be "none")         ## Clinic feedback (Sarah)
## Actions (issue links, owners, target release)
```
**No PHI in the document:** session references use the console's case reference (`case_ref`) or session short IDs only; quotes from transcripts are not copied in. Paraphrase without names, dates of birth or phone numbers.

### Tuning workflow (absorbs P6-06; DECISIONS #282)
| Change type | Example | Review | Gate |
|---|---|---|---|
| Prompt or template | Clearer slot offer wording | AI lead + one engineer | `evals-fast` green; full run before the Thursday deploy |
| STT vocabulary / phrase hints | Add local street names, surnames | Voice engineer + one engineer | `voice-quality.yml` re-run green (P5-03) |
| Routing | Move CONFIRM extraction to `lite` | AI lead + tech lead | Full eval run + latency check |
| Clinic config (console-editable) | Appointment duration, FAQ text | Sarah (ADMIN) | Console validation; noted in the weekly doc |
| Clinic config (file-only) | Verification rules | Tech lead + compliance advisor | Release PR, two prod approvers |
| Emergency rules | New Tier 2 phrase | Dentist sign-off | **P5-07 process:** new `rules_version`, P5-01 emergency set, signed PDF, release PR |
| Code fix | Bug | Normal PR review | CI + relevant suites |

**Release cadence:**
- one tuning release per week, on **Thursday** during clinic hours, so the alert watcher is present;
- safety and security fixes go out on any day;
- there is no deploy on Fridays unless it is a safety fix.

**Rule:** every tuning PR links its weekly-review issue. The weekly document records the effect a week later.

### Pause criteria (DECISIONS #282)
| Event | Action |
|---|---|
| Any AI double booking (P6-02 alert) | Kill switch for the affected channel at once (P5-12 `kill-switch.md`); SEV1 |
| Emergency mishandled (missed Tier 1/2, or wrong advice) | Kill switch for all channels; SEV1; dentist informed |
| Any PHI incident | SEV1 per the IR plan; kill switch if the source is still active |
| A reminder sent for a cancelled appointment | Reminders off; SEV2 |
| Booking completion < 50% for 2 weeks running | Review meeting (team + Sarah + sponsor): continue, fix, or pause |
| Clinic asks to pause | Kill switch; meeting within 2 business days |
Turning a channel back on after a pause needs the root cause fixed, an eval/test proving the fix, and P6-01's two-person approval.

## 7. Implementation guide
1. Write the stage plan, clinic comms, daily and weekly templates, taxonomy, pause table (`docs/pilot/`).
2. Transcript feature, built so that it does nothing while the retention is 0 (the default): migration, writer in the turn pipeline, retention job row, `REVIEWER` role and `TRANSCRIPT_READ`, viewer page, audit action, tests.
3. Stage A: set the flags with two approvals; daily check-ins; gate review at day 7.
4. Stage B, then C, each with a gate review recorded in the weekly doc.
5. Weekly reviews from week 1; tuning PRs; Thursday releases.
6. Hand the weekly docs and the pause history to P6-07.

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| Stage gate missed | Stay in the stage another week; actions in the weekly doc |
| Low volume (< 50 chats in week 1) | Extend stage A; ask the clinic to promote the widget (front desk mentions it on calls) |
| Clinic withdraws transcript consent | Set retention to 0 (release PR same day); the next retention run deletes all rows; record it |
| Reviewer leaves the team | Remove `REVIEWER` the same day; assign a replacement after training |
| A tuning release makes KPIs worse | Revert the change (rollback or a revert PR); note it in the weekly doc |
| Holiday week | The review still happens (shortened); Thursday release skipped if the watcher is away |
| Kill switch pressed by Sarah for a non-safety reason (for example staff overloaded) | Allowed; meeting within 2 business days |

## 9. Security, HIPAA and PHI
- **Real PHI from stage A onward.**
- **Transcripts** (if enabled) are PHI:
  - encrypted at field level and kept for 14 days at most;
  - visible to two people only, with every view audited;
  - deleted by the retention job;
  - enabled only with the clinic's written consent, and the minimum-necessary rule applies.
- The weekly docs, issues and chats contain **no PHI**: use case references and paraphrases.
- Tuning test data stays synthetic. Real conversations are never copied into eval scenarios. A reviewer writes a **new synthetic scenario** that reproduces the pattern.

## 10. Testing
```bash
pytest backend/tests/unit/transcripts backend/tests/integration/transcripts -q
cd frontend && pnpm e2e -- --grep review-transcript
```
| # | Case | Expected |
|---|---|---|
| T1 | Retention 0 | No transcript rows written |
| T2 | Retention 14 | Rows written per turn, `text_enc` encrypted, `expires_at` set |
| T3 | Retention job after 15 days | Rows deleted |
| T4 | ADMIN or FRONT_DESK opens the viewer | 403 |
| T5 | REVIEWER opens the viewer | Shown; audit `transcript.view` written |
| T6 | Retention changed 14 → 0 | All rows deleted at the next run |
| T7 | Weekly doc lint (`scripts/pilot/lint_weekly.py`) | Fails on phone-, DOB- or email-like patterns |

## 11. Acceptance criteria
- [ ] Widget live on the clinic site; stages A, B and C opened through recorded gate reviews
- [ ] Daily review notes for week 1 and a weekly review document for every pilot week (T7)
- [ ] Every failed session in the weeks reviewed carries a taxonomy label; issues filed for actions
- [ ] Every tuning change passed its eval or test gate before release
- [ ] Transcripts, if enabled, follow the consent, access, audit and 14-day retention rules (T1–T6)

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI (transcript feature, doc lint)
- [ ] PR reviewed (HIPAA review for transcripts)
- [ ] No PHI in logs, weekly docs or issues
- [ ] `docs/pilot/` complete; P6-07 has all weekly docs and the pause history

## 13. Hand-off
| Consumer | What they can rely on |
|---|---|
| P6-07 Pilot report | Weekly docs, stage dates, pause history, tuning log, label counts |
| P5-01 | New synthetic scenarios from pilot failures |
| P5-14 access reviews | `REVIEWER` role holders |

## 14. Open questions
| # | Question | Recommended answer | Owner |
|---|---|---|---|
| 1 | Will the clinic consent to 14-day transcripts? | Ask at go-live; recommend yes for the pilot only. Default stays off. | Sponsor + office manager |
| 2 | Should stage B (reminders) come before chat if the clinic cares most about no-shows? | No: reminders need consented bookings from chat first. | Product owner |

## 15. References
- Plan: §8 Phase 6, §11, §5 (transcript retention ≤ 30 days)
- DECISIONS: #14, #117, #139, #280, #281, #282
- Related tasks: P0-01, P1-03, P1-05, P1-13, P1-19, P2-01, P2-04, P2-05, P3-03, P4-13a, P5-01, P5-03, P5-07, P5-12, P5-14, P6-01, P6-02, P6-07
