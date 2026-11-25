---
id: P6-02
title: KPI instrumentation and pilot dashboard
milestone: P6
epic: E6.1
size: M
labels: area:infra, area:admin, type:feature
depends_on: P3-14, P4-13a, P4-09, P1-07, P1-15, P4-01, P4-04
status: approved
---

# P6-02: KPI instrumentation and pilot dashboard

## 1. Summary
Measure the pilot KPIs from plan §11 and show them in two places:
- **Business KPIs** go on a console page, `/admin/insights`, for the clinic's ADMIN users: bookings, callbacks, reminders, review lag and no-shows.
- **Technical KPIs** go on a Cloud Monitoring dashboard for the team: latency, errors and PHI-in-logs.

A nightly job writes PHI-free daily aggregates into a new table, `kpi_daily`. A monthly job pulls no-show **counts** from Open Dental for the baseline.

This task absorbs **P6-03 (post-chat rating widget)**, and by the user's decision **the rating widget is not built** (DECISIONS #281). As a result, the satisfaction KPI (≥ 4.2/5) is reported as "not measured".

Done means every §11 KPI except satisfaction is visible with its target, computed from data, for any date range.

## 2. Why this matters
Plan §8 Phase 6 says "monitor KPIs (§11)". The pilot report (P6-07) and its go/no-go decision depend on these numbers. Without them, the decision becomes "it felt fine".

Sarah also needs a simple view: how many bookings the AI made this week, how many callbacks it left her, and whether the reminders are reaching patients.

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P6, Pilot Launch & Iteration**.
- **KPI (key performance indicator):** a number with a target that tells whether the pilot is succeeding. For example, "booking completion ≥ 70%".
- **No-show:** a patient who doesn't come to the appointment and doesn't cancel. In Open Dental this is usually recorded as a "Broken" appointment, or with a broken-appointment procedure code. **Verify** how the clinic records it, and which API fields expose it.
- **What already exists (approved):**
  - **P4-13a:** the activity log built from `audit_log` PATIENT_SESSION rows, with outcomes BOOKED / RESCHEDULED / CANCELLED / CALLBACK / EMERGENCY / CHANGE_REFUSED / ABANDONED / ERROR; the totals query; the AI-booked list with `reviewed_at`.
  - **P3-14:** per-stage latency metrics and the dashboard; `dai.voice.v2v_ms`.
  - **P1-07:** Cloud Monitoring baseline, log-based metrics, alerts.
  - **P4-01 / P4-04:** `outbound_messages` and `reminders` statuses.
  - **P2-15 / P1-16:** the duplicate-patient barriers and the AI marker.
  - **P5-08:** the PHI pattern scan counts.
  - **P6-01:** pilot flags (stage dates).

## 4. Scope
**In scope**
- KPI definitions (numerator, denominator, source, target) in one place: `backend/app/domain/kpi/definitions.py`.
- `kpi_daily` table, the nightly aggregation job, and backfill.
- The no-show monthly pull (counts only) and the 6-month baseline.
- Console page `/admin/insights` (ADMIN only) with date range, targets, trend sparklines and CSV export of aggregates.
- Cloud Monitoring dashboard "Pilot KPIs (technical)" in Terraform.
- A weekly KPI email digest to the team (aggregates only), feeding P6-04's weekly review.
- A no-op stub for P6-03: the stub file notes that the rating is dropped.

**Out of scope** (and which task covers it)
- Post-chat rating widget → **not built** (user decision, DECISIONS #281)
- Weekly review process → P6-04
- Pilot report → P6-07

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P4-13a | Outcome mapping and the totals query | Approved; reuse its query module |
| P3-14 | Latency metrics | Approved |
| P1-15/P1-16 | Open Dental client for the appointment count query | Use `od_fake` with seeded broken appointments |

## 6. Interface contract

### KPI definitions (DECISIONS #281)
| KPI | Definition | Source | Target (§11) | Where shown |
|---|---|---|---|---|
| Booking completion | Sessions with intent `book` and outcome BOOKED ÷ sessions with intent `book` (excluding EMERGENCY and sessions ended within the first turn) | `audit_log` session outcomes + first intent code | ≥ 70% | Console + report |
| Callback rate | Sessions with outcome CALLBACK ÷ all sessions | same | (tracked; no target) | Console |
| Callback emails delivered | `callback_requests.email_status = SENT` ÷ all callbacks; plus count `FAILED` | `callback_requests` | 100% | Console |
| Voice-to-voice latency p50/p95 | `dai.voice.v2v_ms` distribution | Cloud Monitoring (P3-14) | ≤ 1.5 s / ≤ 2.5 s | Team dashboard; daily value copied into `kpi_daily` |
| Double bookings caused by AI | Appointments in `appointment_refs` that overlap another appointment in the same operatory when we wrote them, found by the nightly check (re-fetch from Open Dental for yesterday's AI writes) | Open Dental + `appointment_refs` | 0 | Console + alert |
| Duplicate patients created | Patients created by the AI (`create_patient` audit) for whom staff later merged or flagged a duplicate (staff report in the console "Report duplicate" action on the AI-booked list; **Proposed** small addition to P4-13a) | audit | 0 | Console |
| Reminder delivery success | Reminders `SENT` with a delivered status ÷ reminders due with GRANTED consent (excluding those `CANCELLED`/`SKIPPED` because the appointment changed) | `reminders`, `outbound_messages` | ≥ 95% | Console |
| Reminders for cancelled appointments | Reminders sent where the appointment was cancelled before the send time (nightly re-check of yesterday's sends) | `reminders` + Open Dental | 0 | Console + alert |
| Critical-field accuracy | From the P5-03 test report (not measured live) | P5-03 | ≥ 98% | Report only |
| Emergency escalation (test suite) | From the latest P5-01 emergency set run | P5-01 | 100% | Report only |
| PHI-in-logs incidents | Count of confirmed incidents (P5-12 incident log) + weekly pattern-scan count (P5-08) | Incident log | 0 | Team dashboard + report |
| Patient satisfaction | **Not measured** (rating widget not built, DECISIONS #281) | - | (≥ 4.2/5) | Report shows "not measured" |
| No-show rate change | (Broken ÷ scheduled) per month, pilot vs 6-month baseline; and reminded vs not reminded during the pilot | Open Dental counts | Measurable reduction | Console + report |
| Review lag (P6-01) | Median and max hours from AI booking to `reviewed_at` | `appointment_refs` | ≤ 1 business day | Console |

### `kpi_daily` table (additive to P1-03)
| Column | Type | Notes |
|---|---|---|
| `clinic_id` | uuid | PK part |
| `day` | date | PK part, clinic-local day |
| `kpi` | text | PK part, key from `definitions.py` |
| `numerator` | bigint | NULL for distributions |
| `denominator` | bigint | |
| `value` | numeric | Ratio or p50/p95 ms |
| `details` | jsonb | Counts by channel (`text`/`voice`), by outcome; **no IDs** |
| `computed_at` | timestamptz | |
No PatNum, AptNum or session IDs, so the table holds no PHI and is kept indefinitely.

### Jobs
```python
# backend/app/domain/kpi/jobs.py
async def compute_day(clinic_id: UUID, day: date) -> list[KpiRow]: ...     # idempotent upsert
async def nightly_checks(clinic_id: UUID, day: date) -> NightlyCheckResult: ...  # double-booking + cancelled-reminder re-checks
async def monthly_noshow(clinic_id: UUID, month: date) -> NoShowCounts: ...
```
- `POST /internal/tasks/kpi/daily`: Cloud Scheduler at 02:30 clinic time computes yesterday, then runs `nightly_checks`. Any double booking or cancelled-reminder hit raises alerts `kpi-double-booking` / `kpi-cancelled-reminder` (email, SEV1 per P5-12).
- `POST /internal/tasks/kpi/noshow`: on the 2nd of each month. A **backfill** run at go-live loads the previous 6 months.
- `python -m app.domain.kpi.backfill --from 2027-01-01 --to 2027-02-15`.

### No-show counts (DECISIONS #281)
Query Open Dental for appointments in the month, grouped by status: complete, broken, scheduled. **Verify** the endpoint and filters (for example `GET /appointments` with date range and `AptStatus`), and how the clinic marks no-shows (status Broken vs. procedure codes D9986/D9987). Store **only counts** in `kpi_daily` (`kpi = noshow_month`, `details = {"scheduled": 412, "broken": 37, "reminded_broken": 9, "reminded_total": 160}`). The reminded split uses our `reminders` table joined by AptNum in memory; only the counts are stored. The clinic's written OK to use these counts is part of P6-01 onboarding (Sarah confirms in the UAT policy checklist).

### Console page `/admin/insights` (ADMIN only; P4-09 NAV additive)
```
GET /v1/admin/kpi?from=2027-03-01&to=2027-03-31   → {"kpis":[{"key":"booking_completion","value":0.74,"target":">=0.70",
                                                     "status":"ok","trend":[0.68,0.71,...],"numerator":148,"denominator":200}, ...],
                                                     "not_measured":["patient_satisfaction"]}
GET /v1/admin/kpi/export.csv?from=...&to=...       → aggregates only
```
Layout:
- top tiles (booking completion, callbacks, reminder success, no-show change, review lag), each with its target and a green/amber/red status;
- a weekly trend chart;
- a table by channel;
- a footnote explaining each definition.

Permission: a new `KPI_READ` for ADMIN (P1-13 additive). FRONT_DESK can't see the page.

### Team dashboard (Terraform `infra/monitoring/dashboards/pilot-kpis.json`)
Panels:
- voice-to-voice p50/p95 against targets;
- per-stage p95;
- error rate;
- sessions per hour;
- callbacks per hour;
- the nightly-check alerts;
- the PHI pattern-scan count (custom metric pushed by the P5-08 weekly job);
- Vertex AI 429s.

### Weekly digest
Monday 07:00, an email to the team list containing last week's KPI table, with deltas and red items. Aggregates only, so it needs no PHI handling. It is the input for P6-04's weekly review.

## 7. Implementation guide
1. Write `definitions.py` with the table above as code (key, compute function, target, unit) and unit tests on fixtures.
2. Migration for `kpi_daily`.
3. Daily job with idempotent upserts; nightly checks with the Open Dental re-fetch (batch by date range, respecting P1-15 rate limits); alerts in P1-07.
4. Add the "Report duplicate" action to the AI-booked list (P4-13a additive): ADMIN or FRONT_DESK, audited `appointment.duplicate_reported`.
5. No-show pull after the Verify step; backfill 6 months at go-live.
6. API and console page; CSV export.
7. Terraform dashboard and the weekly digest (Cloud Scheduler → task → Gmail API sender from P2-22, team list only).
8. Update the P6-03 stub with the "not built" note (DECISIONS #281).
9. Docs `docs/kpi.md` (definitions, sources, known limits). Notify P6-04 and P6-07.

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| Open Dental unreachable during the nightly checks | Retry 3 times; then mark the day's check `incomplete` (tile shows "check incomplete"); next run re-checks 2 days |
| A booking that staff later moved into an overlap | Not counted as an AI double booking. An overlap counts only if the other appointment already existed when we wrote ours: compare its creation timestamp in Open Dental (**Verify** the field, for example `DateTStamp`/`SecDateTEntry`) with `appointment_refs.created_at`. If the timestamp isn't available, count the overlap and let staff mark it "staff-caused" in the console |
| Low volume (denominator < 20 in the range) | Tile shows the value with "low volume" and no status colour |
| No-show recording differs at the clinic | Configurable mapping `kpi.noshow_definition` (status or codes) set at onboarding |
| Day boundary and DST | Days are clinic-local; DST days have 23/25 hours, which is fine for counts |
| Backfill reruns | Idempotent upserts |

## 9. Security, HIPAA and PHI
- `kpi_daily`, the API, the CSV and the digest hold **aggregates only**: no PatNum, AptNum, names or session IDs. This is checked by a unit test that scans `details` for keys other than allowed counters.
- The nightly checks and the no-show pull read PHI-bearing data (appointments) from Open Dental in memory only. Nothing but counts is written, and nothing is logged except counts and error codes.
- The console page needs `KPI_READ` (ADMIN). Access is audited by P1-12's standard read audit for admin routes.

## 10. Testing
```bash
pytest backend/tests/unit/kpi backend/tests/integration/kpi -q
cd frontend && pnpm test -- insights && pnpm e2e -- --grep insights
```
| # | Case | Expected |
|---|---|---|
| T1 | Fixture day with 10 booking sessions, 7 BOOKED | booking_completion 0.70 |
| T2 | Reminder sent for an appointment cancelled 2 h before | Counted; alert raised |
| T3 | Overlapping AI write in `od_fake` | Double-booking KPI 1; alert |
| T4 | `details` contains `patnum` | Unit test fails |
| T5 | FRONT_DESK opens `/admin/insights` | 403 |
| T6 | No-show backfill 6 months | 6 rows with counts only |
| T7 | Satisfaction KPI | Listed under `not_measured` |
| T8 | Re-run of the same day | Same values, no duplicates |

## 11. Acceptance criteria
- [ ] Every KPI in §6 except satisfaction is computed and visible with its target (T1–T3, T6)
- [ ] Satisfaction is shown as "not measured" (T7)
- [ ] Nightly double-booking and cancelled-reminder checks alert on any hit (T2, T3)
- [ ] No PHI in `kpi_daily`, the API, the CSV or the digest (T4)
- [ ] Console page restricted to ADMIN (T5); team dashboard deployed by Terraform

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI
- [ ] PR reviewed (HIPAA review for the Open Dental reads)
- [ ] No PHI in logs
- [ ] `docs/kpi.md` written; P6-03 stub updated; P6-04 and P6-07 notified

## 13. Hand-off
| Consumer | What they can rely on |
|---|---|
| P6-04 Weekly review | Weekly digest and the console page |
| P6-07 Pilot report | `kpi_daily` for the whole pilot; CSV export; definitions doc |
| P6-01 | Review lag KPI |
| P5-12 | SEV1 alerts for double booking and cancelled reminders |

## 14. Open questions
| # | Question | Recommended answer | Owner |
|---|---|---|---|
| 1 | How does Bright Smile record no-shows in Open Dental? | Ask Sarah at onboarding; set `kpi.noshow_definition`. **Verify** the API fields. | Office manager |

## 15. References
- Plan: §11, §8 Phase 6
- DECISIONS: #134, #216, #281
- Related tasks: P1-03, P1-07, P1-12, P1-13, P1-15, P2-15, P2-22, P3-14, P4-01, P4-04, P4-09, P4-13a, P5-01, P5-03, P5-08, P5-12, P6-01, P6-03, P6-04, P6-07
