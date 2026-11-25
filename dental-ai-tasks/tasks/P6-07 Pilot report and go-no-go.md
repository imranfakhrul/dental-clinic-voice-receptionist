---
id: P6-07
title: Pilot report and go/no-go
milestone: P6
epic: E6.1
size: S
labels: area:compliance, type:docs
depends_on: P6-04, P6-02, P5-14, P5-11
status: approved
---

# P6-07: Pilot report and go/no-go

## 1. Summary
Write the pilot report and make the **go / conditional go / no-go** decision for a wider rollout. The report covers four things:
- KPI results against the plan §11 targets;
- incidents;
- what was tuned;
- open risks and lessons learned.

The pilot runs for at least **6 weeks of full operation** (from the day stage C opened in P6-04) **and** at least **300 conversations**. Below that, it is extended. **Safety KPIs are must-pass**: one failure means no-go. **Quality KPIs** may miss by a small margin, which leads to a conditional go with a fix list. The decision is made by the **sponsor, tech lead and compliance advisor**, with the clinic consulted. The clinic receives a version of the report without technical internals.

Done means the report is shared with the stakeholders and the signed decision record exists.

## 2. Why this matters
Plan §8 Phase 6's deliverables are "pilot report, go/no-go for wider rollout". Plan §15 includes "the pilot runs successfully with the agreed KPIs met". This task turns six weeks of data into a decision, written down with its reasons, so that a second clinic is added because the evidence supports it, not by default.

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P6, Pilot Launch & Iteration**.
- **Sources:**
  - P6-02: `kpi_daily`, the CSV export, `docs/kpi.md`;
  - P6-04: weekly docs, stage dates, pause history, tuning log;
  - P5-12: the incident log;
  - P5-14: exceptions and accepted risks;
  - P5-08 / P5-11: the findings register;
  - P5-01 / P5-03: the latest test reports.
- **Satisfaction KPI:** the rating widget was dropped by the user's decision (DECISIONS #281), so the report shows "not measured". If the sponsor wants a qualitative signal, Sarah's feedback on patient comments can be summarized without PHI.

## 4. Scope
**In scope**
- Pilot length and extension rule; data freeze date.
- Report (`docs/pilot/pilot-report.md` + PDF) and a clinic version (`docs/pilot/pilot-report-clinic.md`).
- Decision rules, the decision meeting, the signed record, and the follow-up plan (conditions for a conditional go; root-cause plan for a no-go).

**Out of scope** (and which task covers it)
- Onboarding a second clinic → post-MVP (plan §14)
- Fixes listed as conditions → new issues after the decision

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P6-04 | Weekly docs and pilot data | Draft the report skeleton and decision rules in week 1 |
| P6-02 | KPI data and export | Same |

## 6. Interface contract

### Pilot length (DECISIONS #283)
- Minimum: **6 weeks** after stage C opened **and** ≥ **300 conversations** in total (all channels).
- If the conversations are below 300 at 6 weeks, extend in 2-week steps, up to 12 weeks total. If still below 300 at 12 weeks, decide with the data available and state it as a limitation.
- Data freeze: the end of the last full week. The report uses that cut-off.

### KPI classes and decision rule (DECISIONS #283)
| Class | KPI | Target |
|---|---|---|
| **Safety (must-pass)** | Double bookings caused by AI | 0 |
| | Duplicate patients created by AI | 0 |
| | Emergency scenarios escalated (test suite, latest run) and no live emergency mishandled | 100% / 0 |
| | PHI-in-logs incidents | 0 |
| | Reminders for cancelled appointments | 0 |
| **Quality** | Booking completion | ≥ 70% |
| | Callback emails delivered | 100% |
| | Voice latency p50 / p95 | ≤ 1.5 s / ≤ 2.5 s |
| | Reminder delivery | ≥ 95% |
| | Critical-field accuracy (P5-03) | ≥ 98% |
| | No-show change vs baseline | A measurable reduction |
| **Not measured** | Patient satisfaction | (≥ 4.2/5): not measured, DECISIONS #281 |

| Decision | Rule |
|---|---|
| **Go** | All safety KPIs met **and** all quality KPIs met |
| **Conditional go** | All safety KPIs met; one or more quality KPIs missed by a small margin (booking completion ≥ 60%, latency p95 ≤ 3.0 s, reminder delivery ≥ 90%, email delivery ≥ 98% with every failure caught by the console); a fix list with owners and dates; the next clinic starts only after the listed fixes are verified |
| **No-go** | Any safety KPI missed, **or** a quality KPI below the conditional margin; the report includes a root-cause plan and whether the pilot continues or pauses |
| (any) | An open Critical/High security finding, or an open never-waived P5-14 item, means no-go regardless of KPIs |

### Report structure (`docs/pilot/pilot-report.md`)
1. Executive summary (one page): decision recommendation, key numbers, top risks.
2. Pilot setup: clinic (no patient data), dates, stages, flags, `ai_hours`, transcripts on/off.
3. KPI results table: value, target, class, status, with weekly trend charts from P6-02 data, and volumes by channel.
4. Safety: emergencies seen (counts by tier), callbacks marked URGENT, any pause events.
5. Incidents: from the P5-12 incident log (IDs, severity, summary without PHI, resolution).
6. Failures and tuning: taxonomy label counts over time; changes shipped and their effect.
7. Security and compliance: findings status (P5-08, P5-11), accepted risks and exceptions (P5-14), access-review results.
8. Clinic feedback: Sarah's and the dentist's view (from the weekly docs and an end-of-pilot interview).
9. Costs: cloud, LLM, STT/TTS and messaging cost per conversation (from billing exports; **Verify** the export is enabled).
10. Lessons learned and recommendations, including what changes before a second clinic (for example row-level security (#98), MDM, SMS on-call).
11. Appendix: definitions (link `docs/kpi.md`), data freeze date, limitations.

**No PHI anywhere in the report**: aggregates, case references and paraphrases only. A lint step (P6-04's `lint_weekly.py`, reused) runs on the report.

### Clinic version
Sections 1, 3 (business KPIs only), 4, 8 and 10, in plain language, without security internals.

### Decision meeting and record
- Participants: sponsor, tech lead and compliance advisor (deciders); office manager and dentist (consulted; they present their view first).
- Record `docs/pilot/decision-<date>.md`: decision, the rule that applied, the conditions with owners and dates, signatures of the three deciders, and the date the clinic was informed.
- Report shared with: deciders, the team, the clinic (clinic version), and any investor or stakeholder list the sponsor names.

## 7. Implementation guide
1. Week 1 of the pilot: create the report skeleton and fill section 2.
2. Weekly: copy the P6-02 numbers into a running draft (avoids a last-week rush).
3. At the freeze: export `kpi_daily` (CSV), compute final values, build the charts (script `scripts/pilot/report_charts.py` reading the CSV).
4. End-of-pilot interview with Sarah and the dentist (30 min).
5. Write the report and the clinic version; run the PHI lint; internal review by the tech lead and the compliance advisor.
6. Decision meeting; signed record; share the report; open issues for the conditions.

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| A safety event happened but was fully fixed during the pilot | Still a missed safety KPI → no-go for wider rollout **now**; the report can recommend a re-check period (for example 4 more weeks with 0 events) before a new decision |
| The pilot was paused for a while | Paused days are excluded from the 6 weeks; the pause is reported |
| KPI data incomplete for some days (P6-02 "check incomplete") | Report the gap; recompute if the source data still exists |
| Deciders disagree | The more cautious option wins (no-go over conditional, conditional over go); the disagreement is recorded |
| Clinic wants to continue even with a no-go for wider rollout | Allowed if all safety KPIs are met at the pilot clinic and the sponsor agrees; this is a separate decision recorded in the same document |

## 9. Security, HIPAA and PHI
- **No PHI:** the report, charts and decision record use aggregates only; PHI lint enforced.
- The report holds security information (findings, accepted risks), so the full version is confidential; the clinic version omits it.

## 10. Testing
| # | Check | Expected |
|---|---|---|
| T1 | PHI lint on the report | Passes |
| T2 | KPI values recomputed from the CSV by a second person | Match |
| T3 | Decision follows the rule table | Yes, the cited rule matches the values |

## 11. Acceptance criteria
- [ ] Pilot ran ≥ 6 weeks of full operation and ≥ 300 conversations, or the extension rule was applied and stated
- [ ] Report with all sections in §6, PHI lint passed (T1), values independently checked (T2)
- [ ] Decision made by the three deciders under the rule table and recorded with signatures (T3)
- [ ] Report shared with stakeholders; clinic version shared with the clinic

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Report reviewed by the tech lead and the compliance advisor
- [ ] No PHI in the report
- [ ] Condition issues opened (conditional go) or root-cause plan written (no-go)

## 13. Hand-off
| Consumer | What they can rely on |
|---|---|
| Sponsor / stakeholders | The report and the signed decision |
| Post-MVP roadmap (plan §14) | Lessons and the pre-second-clinic list |
| Pilot clinic | The clinic version and the decision |

## 14. Open questions
| # | Question | Recommended answer | Owner |
|---|---|---|---|
| 1 | Should cost per conversation have a target? | Not for the pilot; report it, and set a target before the second clinic. | Sponsor |

## 15. References
- Plan: §8 Phase 6, §11, §14, §15
- DECISIONS: #98, #281, #282, #283
- Related tasks: P5-01, P5-03, P5-08, P5-11, P5-12, P5-14, P6-01, P6-02, P6-04
