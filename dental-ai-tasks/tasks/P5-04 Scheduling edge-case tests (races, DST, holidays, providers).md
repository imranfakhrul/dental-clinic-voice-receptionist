---
id: P5-04
title: Scheduling edge-case tests (races, DST, holidays, providers)
milestone: P5
epic: E5.1
size: M
labels: area:qa, area:scheduling, area:messaging, type:test
depends_on: P1-21, P1-20, P2-16, P2-18, P4-04, P4-17, P0-12
status: approved
---

# P5-04: Scheduling edge-case tests (races, DST, holidays, providers)

## 1. Summary
Add the hard scheduling and reminder test suites on top of the unit tests that P1-20, P1-21, P2-16, P2-18 and P4-04 already have. This task absorbs **P5-05 (reminder tests: timing, cancel/move, retries, opt-out)**.

| Suite | Where it runs | What it proves |
|---|---|---|
| S1 Race (fake) | Every PR (`pr.yml`), against `od_fake` | 200 concurrent confirmations of one slot → exactly 1 appointment |
| S2 Race (staging) | Before each prod promotion and on demand, real Open Dental test DB | 10 parallel widget sessions + a staff write through the API at the same moment → 0 double bookings |
| S3 Calendar edge cases | Every PR | DST (both directions), holidays, provider restrictions, outside hours, lead time, horizon, blockouts |
| S4 Reminder matrix (fake clock) | Every PR | ~40 combinations of cancel / move / retry / opt-out / timing → 0 reminders for cancelled appointments, right send time |
| S5 Reminder staging | Before each prod promotion | 10 chosen combinations through P4-17's run-now endpoints on the real stack |
| S6 Property tests | PR (200 examples), nightly (10,000) | No returned slot ever overlaps an appointment, blockout, holiday or closed hours |

Done means the two seed criteria hold: **0 double bookings under concurrency** and **0 reminders for cancelled appointments**.

## 2. Why this matters
Two pilot KPIs are zero-tolerance (plan §11):
- **0 double bookings caused by AI.** Sarah would have two patients in one chair.
- **0 reminders for cancelled appointments.** John would get "see you at 3" for a visit he cancelled.

Unit tests already cover the main paths: P1-21 T24 runs 20 concurrent bookings, and P4-04 has a 30-day fake-clock simulation. Plan §9 asks for more: races across real instances, DST transitions, holidays, provider restrictions, and reminder failures and retries. P0-11 lists race tests as the control for R17 and reminder tests as the control for R19.

Several approved specs pointed these tests at "P5-03": P1-20, P2-16, P2-18 and P2-01. Under the consolidation they belong to **P5-04**; P5-03 took load testing (DECISIONS #284).

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P5, Hardening, Testing & Security Review**.
- **Race condition:** two actions happen at nearly the same moment and the result depends on which one wins. Here it is two people confirming the same 10:00 slot.
- **DST (daylight saving time):** in `America/New_York` on 2026-11-01 the clock goes 01:59 → 01:00 (one hour happens twice). On 2027-03-14 it goes 01:59 → 03:00 (02:xx does not exist). We store UTC and convert with the clinic's IANA zone.
- **Property-based testing (Hypothesis):** instead of hand-written examples, the tool generates thousands of random schedules and checks that a rule (a "property") always holds.
- **What already exists (approved):**
  - **P1-21:** Redis slot lock + the booking sequence (re-check in Open Dental under the lock, then write); T24 runs 20 concurrent sessions.
  - **P1-20:** the pure availability engine (AI window, holidays, blockouts, grid, DST, lead times, horizon) and its tests T1–T12.
  - **P2-16 / P2-18:** booking, reschedule and cancel flows, `check_notice`, the `fresh_availability` guard.
  - **P4-04 / P4-05:** the `reminders` table (`PENDING`, `ENQUEUED`, `SENT`, `SKIPPED`, `FAILED`, `CANCELLED`), the hourly sweep, the pre-send Open Dental re-fetch (`VERIFY_FAILED`), the per-clinic offset 30–240, and the 30-day fake-clock simulation.
  - **P4-17:** `POST /internal/e2e/reminders/{id}/run-now`, `POST /internal/e2e/messaging/simulate`, `GET /internal/e2e/lifecycle/{aptnum}`, test clinic `e2e-clinic`, fake messaging provider (`messaging.provider_override: fake`).
  - **P0-12:** the synthetic Open Dental test DB, with appointments around the next DST change and a double-booking target.

## 4. Scope
**In scope**
- Suites S1–S6, their fixtures and CI wiring.
- `od_fake` fault injection used by the suites (latency, 409 conflict, 5xx, timeout after the write).
- A staging race runner (`scripts/qa/race_staging.py`).
- Report `out/sched-edge/report.json` and the promotion gate for S2 and S5.

**Out of scope** (and which task covers it)
- Load and latency → P5-03
- Conversation wording → P5-01
- Fixing bugs found → the owning task (P1-20, P1-21, P2-16, P2-18, P4-04)

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P1-20 / P1-21 (approved) | Engine, slot lock, booking sequence, `od_fake` | Built in P1; extend their test packages |
| P4-04 / P4-05 (approved) | Reminder planner, sweep, task handler | Fake clock harness already exists in P4-04's integration tests |
| P4-17 (approved) | Run-now and simulation endpoints on staging | Use them as specified; S5 waits for staging |
| P0-12 | Synthetic test DB with providers, DST appointments | S2 waits for it; S1/S3/S4/S6 do not |

## 6. Interface contract

### S1 Race (fake), `backend/tests/integration/scheduling/test_race_fake.py`
```python
@pytest.mark.parametrize("processes,tasks_per_process", [(4, 50)])   # 200 attempts
async def test_one_slot_many_confirmers(od_fake, redis_real, processes, tasks_per_process): ...
# Expect: exactly 1 BOOKED; every other result in {slot_taken, slot_busy}; od_fake has 1 appointment;
#         each loser was offered alternatives (P2-16) and none of the alternatives is the taken slot.
```
Variants:
- **S1b:** reschedule into the slot while another session books it.
- **S1c:** the Open Dental write times out *after* succeeding (fault `timeout_after_write`). The idempotency key prevents a second appointment (P2-10/P1-21).
- **S1d:** two different slots that overlap because of different appointment lengths (60 vs 30 min). Only one is written.

### S2 Race (staging), `scripts/qa/race_staging.py`
```bash
python scripts/qa/race_staging.py --env staging --sessions 10 --slot auto --with-staff-write
```
1. Pick a free slot on `e2e-clinic` from the availability API.
2. Drive 10 API sessions (P2-30 data factory, `ZZTEST<runid>` patients) up to the confirmation step.
3. Fire all 10 `confirm` messages within 50 ms, plus one direct Open Dental `POST /appointments` for the same operatory and time as a "staff write". **Verify** the test DB key may write.
4. Read the result in Open Dental through the verification client.

**Pass:** at most one appointment in that slot (either ours or the staff one), and every session got `booked` or `slot_taken` with alternatives. Cleanup per P2-30.

### S3 Calendar edge cases, `backend/tests/unit/scheduling/test_edge_calendar.py`
| ID | Case | Expected |
|---|---|---|
| C1 | Fall back 2026-11-01, clinic opens 08:00; slot request for 01:30 (ambiguous) | 01:xx is outside hours anyway; slots at 08:00 local are correct UTC (13:00Z) |
| C2 | Spring forward 2027-03-14, appointment 10:00 local | Stored 14:00Z (EDT); confirmation and reminder texts say 10:00 |
| C3 | A clinic in `America/Phoenix` (no DST) on the same dates | No shift |
| C4 | Holiday closed day; holiday with shortened hours | No slots; slots only inside the holiday hours |
| C5 | Provider who does not do the requested type (P1-19 mapping) | Not offered |
| C6 | Provider schedule ends 15:00, clinic hours 17:00 | No slots after 15:00 for that provider |
| C7 | Request at 16:50 with lead time 120 min | First option the next open day |
| C8 | Booking horizon 7 days; request "in 3 weeks" | `out_of_horizon` path → template + callback offer (P2-16) |
| C9 | Reserved new-patient blockout (P1-20) | Existing patient not offered; new patient offered |
| C10 | Appointment crossing lunch break | Not offered |
| C11 | Reschedule within the cancellation window (`check_notice`) | Refused per P2-18 policy, staff-only path |
| C12 | Clinic config changes hours while options are on screen | `fresh_availability` guard rejects the stale option at confirm |

### S4 Reminder matrix (fake clock), `backend/tests/integration/reminders/test_matrix.py`
Dimensions:
- **What happens to the appointment:** none / cancelled by patient (AI) / cancelled by staff in Open Dental / moved by patient / moved by staff;
- **When it happens:** > 1 h before the planned send / 1 min before / during the send task;
- **Consent:** granted / revoked (STOP) / never given;
- **Provider:** OK / 5xx then OK / 5xx until give-up;
- **Offset:** 30 / 60 / 240.

The full product is too large, so the 40 rows are chosen by pairwise coverage (`allpairspy`) plus 8 mandatory rows. Expectations per row:
- **Cancelled:** the reminder ends `CANCELLED` or `SKIPPED` and the provider fake has **0** sends for that appointment.
- **Moved:** the old reminder is cancelled or skipped; the new one is planned for the new start minus the offset at the offset that applies to it; exactly 1 send.
- **Consent revoked:** 0 sends, `SKIPPED` with the consent reason.
- **Transient provider error:** retried within the P1-02 queue policy; at most 1 delivered message (dedupe key).
- **Give-up:** `FAILED`, visible in the failed-messages list (P4-13a).
- **DST rows:** send time = local start − offset, computed in the clinic zone.

### S5 Reminder staging, `frontend/e2e/staging/phase5-reminders.spec.ts`
10 rows of S4 (one per dimension value), run on `e2e-clinic` with P4-17's run-now, simulate and lifecycle endpoints. Each row checks the lifecycle summary and the fake provider's sends.

### S6 Property tests, `backend/tests/property/test_availability_props.py`
```python
@given(schedule=schedules(), appts=appointments(), config=clinic_configs(), now=instants())
def test_no_option_conflicts(schedule, appts, config, now):
    options = compute_options(schedule, appts, config, now)
    assert all(not overlaps(o, a) for o in options for a in appts)
    assert all(inside_ai_window(o, config) and not on_closed_holiday(o, config) for o in options)
    assert all(o.start >= now + lead(config, o) for o in options)
```
Profiles: `ci` (200 examples) and `nightly` (10,000 examples, `--hypothesis-seed` printed for reproduction).

### CI and gates (additive to P1-06)
| Workflow | Job | Suites |
|---|---|---|
| `pr.yml` | `sched-edge` | S1, S3, S4, S6 (`ci` profile) |
| `nightly.yml` | `sched-props` | S6 (`nightly` profile) |
| `promote.yml` | gate step | The latest S2 + S5 run for the release digest must be green |
| manual | `sched-staging` | S2 + S5 on demand |

## 7. Implementation guide
1. **`od_fake` faults:** add `faults={"timeout_after_write": 1, "latency_ms": 200, "conflict_on_write": "..."}` to the fake (test-only).
2. **S1** with real Redis (testcontainers) and multiple processes, so the lock is really shared.
3. **S3** table tests with `time-machine` and the clinic fixtures `example-dental` (New York) and `example-phoenix`.
4. **S4** matrix generator plus the 8 mandatory rows; reuse P4-04's fake clock and the fake messaging provider.
5. **S6** Hypothesis strategies for schedules, appointments and configs, limited to realistic ranges.
6. **S2** script with the P2-30 data factory and cleanup; the staff write goes through the test DB key. If the key may not write appointments, use a second test key (**Verify** with P0-12).
7. **S5** Playwright spec reusing P4-17's helpers.
8. **CI wiring and promotion gate.**
9. **Docs** `docs/qa/scheduling-edge-tests.md` (how to reproduce a Hypothesis failure, read the matrix). Notify P6-01 (gate item).

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| S2 finds two appointments in one slot | Gate fails; P0 bug for P1-21 owner; cleanup still runs |
| Staff write is refused by Open Dental because our booking already took the slot | Valid outcome; counts as pass |
| Hypothesis finds a failing example | The test prints the seed and the minimal example; a regression test is added with that example |
| Test DB has no DST-week appointments | S2/S5 still run; DST is covered by S3/S4 |
| Staging run-now endpoint disabled (prod) | S5 runs only on staging; endpoints refuse in prod (P4-17) |
| Matrix row flakes because of timing in the fake clock | Fix the test (deterministic clock); no retries allowed for S1/S4 |

## 9. Security, HIPAA and PHI
- **No PHI:** synthetic `ZZTEST` patients on the synthetic test DB; fakes elsewhere.
- The staff-write in S2 uses the test DB key from Secret Manager (dev/staging only).
- Reports contain IDs, counts and timings only.

## 10. Testing
```bash
pytest backend/tests/integration/scheduling/test_race_fake.py -q
pytest backend/tests/unit/scheduling/test_edge_calendar.py backend/tests/integration/reminders/test_matrix.py -q
pytest backend/tests/property -q --hypothesis-profile=ci
python scripts/qa/race_staging.py --env staging --sessions 10 --with-staff-write
cd frontend && pnpm e2e:staging -- --grep phase5-reminders
```
| # | Case | Expected |
|---|---|---|
| T1 | S1 200 attempts | Exactly 1 appointment |
| T2 | S1c timeout after write | 1 appointment, idempotent replay |
| T3 | S2 with staff write | ≤ 1 appointment in the slot |
| T4 | S3 C1–C12 | As in the table |
| T5 | S4 40 rows | 0 sends for cancelled; correct send times; ≤ 1 delivered per reminder |
| T6 | S5 10 rows on staging | Lifecycle summaries match |
| T7 | S6 nightly 10,000 examples | No property violation |

## 11. Acceptance criteria
- [ ] 0 double bookings under concurrency in S1 (200 attempts) and S2 (10 sessions + staff write) (T1–T3)
- [ ] All calendar edge cases C1–C12 pass (T4)
- [ ] 0 reminders for cancelled appointments across the 40-row matrix and the 10 staging rows (T5, T6)
- [ ] Property tests run in PR and nightly without violations (T7)
- [ ] Prod promotion requires a green S2 + S5 run for the release digest

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI
- [ ] PR reviewed (scheduling owner + QA)
- [ ] No PHI in logs or reports
- [ ] `docs/qa/scheduling-edge-tests.md` written; P6-01 notified

## 13. Hand-off
| Consumer | What they can rely on |
|---|---|
| P6-01 Go-live | Gate "S2 + S5 green for the release digest" |
| P6-02 KPIs | The double-booking and cancelled-reminder KPIs have a test baseline of 0 |
| P5-12 Runbooks | The S2 staff-write case as the reference for "double booking reported" handling |

## 14. Open questions
| # | Question | Recommended answer | Owner |
|---|---|---|---|
| 1 | May the Open Dental test key write appointments directly for the staff-write case? | **Verify** with P0-12; otherwise use a second test key with write permission. | Tech lead |

## 15. References
- Plan: §9 (scheduling, reminders), §11 (zero-tolerance KPIs), §4.6, §4.7
- DECISIONS: #258, #274, #284
- Related tasks: P0-11, P0-12, P1-20, P1-21, P2-10, P2-16, P2-18, P4-04, P4-13a, P4-17, P5-03, P6-01
- Hypothesis: <https://hypothesis.readthedocs.io/> · allpairspy: <https://github.com/thombashi/allpairspy>
