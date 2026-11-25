---
id: P5-07
title: UAT with clinic staff on staging
milestone: P5
epic: E5.1
size: M
labels: area:qa, area:compliance, type:test
depends_on: P5-01, P4-17, P4-11, P4-13a, P0-03, P1-19
status: approved
---

# P5-07: UAT with clinic staff on staging

## 1. Summary
Run **user acceptance testing (UAT)** with the pilot clinic's staff on staging and get the clinic's **final sign-off on the emergency rules, scripts and policies**. This task absorbs **P5-15 (clinic sign-off on emergency scripts and policies)**.

| Part | What happens |
|---|---|
| Preparation | UAT script, persona cards with fictional patients, console accounts, a staging banner, an issue form |
| Guided session | 3 hours with the office manager, 1–2 front-desk staff and the dentist (emergency part only) |
| Self-paced week | Staff use staging for 1 week following the script; issues go through the form |
| Follow-up | 1 hour: triage results, open items, sign-off |
| Emergency sign-off | The dentist signs a generated PDF of the exact emergency rules version (with its SHA-256 hash and test results); a release PR then sets `status: approved` with two prod approvers |

Done means:
- the UAT sign-off form is signed by the office manager and the dentist with no open **Blocker**;
- the emergency rules are `approved` in the repository, and the signed PDF's hash matches the file that will go to prod.

## 2. Why this matters
Plan §9 requires "clinic staff run real-world scenarios on staging before pilot". The Definition of Done (plan §15) requires "the clinic has approved the emergency rules, scripts and policies". Engineers test what they built; the clinic tests whether it fits how Bright Smile actually works. Two examples of what only the clinic can catch:
- Sarah may notice that the AI offers 30-minute cleanings when hygienists need 60;
- the dentist may notice that "jaw is locked" is missing from the Tier 2 phrases.

Production only loads emergency rules with status `approved`, and only this task can set it (DECISIONS #14). Without this task, P6-01 can't go live.

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P5, Hardening, Testing & Security Review**.
- **UAT (user acceptance testing):** the future users try the system in realistic situations and decide whether it is acceptable. It is not a bug hunt by engineers.
- **Emergency rules (P0-03):** a YAML file with Tier 1 (call 911), Tier 2 (urgent slot or URGENT callback), Tier 3 (routine) and crisis (988) categories, trigger phrases and fixed scripts. Status lifecycle (DECISIONS #14):
  - `draft`;
  - `clinic_reviewed`: dentist OK for development, set at the end of P0-03;
  - `approved`: final, for production. Set only here.
- **Edit path for safety-critical config (DECISIONS #139, P1-19):** `emergency_rules`, `verification` and `privacy` are file-only. They change through a reviewed file and a release PR with prod approvals, never in the console. The console shows them read-only, with "Request a change" (P4-11).
- **Persona card:** a printed or PDF card with a fictional patient (name, DOB, phone, situation) that a tester uses instead of a real person.
- **What already exists (approved):**
  - **P4-17:** console test users and the scenario list. P4-11, P4-13 and P4-13a provide the console pages.
  - **P5-01:** the emergency case set result per `rules_version`.
  - **P0-01:** the clinic SME and the protocol owner (the dentist).
  - **P1-19:** `config_imports` in a release PR for the prod import.

## 4. Scope
**In scope**
- UAT plan, script (scenarios for patients and for staff), persona cards, issue form, severity rules, sign-off form.
- Staging preparation: `uat-clinic` config cloned from the pilot clinic's config, console accounts per tester (MFA), the staging banner, a feedback link.
- Running the three sessions, triage, fixes tracking, retest of fixed Blockers and Majors.
- Policy confirmation checklist (hours, appointment types and durations, cancellation window, new-patient rules, reminder offset, callback email recipients, AI marker text).
- Emergency rules sign-off: PDF generator, signature capture, evidence storage, the release PR that sets `approved`.

**Out of scope** (and which task covers it)
- Fixing what UAT finds → the owning task (tracked here until closed)
- Writing or changing the rules engine → P2-20 / P4-11
- Production staff accounts and training → P6-01

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P4-17 suite green on staging | A stable staging release | UAT starts only on a release whose P4-17 run is green |
| P5-01 | Emergency set results for the rules version | Run `python -m evals.run --set emergency_cases` for that version |
| P0-03 rules at `clinic_reviewed` | The rules file to sign | Already done in P0-03 |
| Clinic availability | Staff time | Book the dates at least 2 weeks ahead with the office manager |

## 6. Interface contract

### Participants and roles (DECISIONS #275)
| Role | Who (Bright Smile example) | Part |
|---|---|---|
| Clinic lead tester | Office manager (Sarah) | All sessions; signs the UAT form |
| Front-desk testers | 1–2 staff | Guided session + self-paced week |
| Clinical approver | Dentist (protocol owner from P0-01) | Emergency part of the guided session; signs the emergency PDF and the UAT form |
| UAT facilitator | QA engineer | Runs sessions, triages with the tech lead |
| Tech lead | - | Technical severity, fix plan, retest |
| Observer (notes) | Any team member, not the facilitator | Writes the session notes |

### Schedule
| Step | Length | Format |
|---|---|---|
| Kick-off and guided session | 3 h | On site at the clinic (preferred) or screen share |
| Self-paced week | 5 working days, ~30 min/day | Staff follow the script on staging |
| Follow-up and sign-off | 1 h | Same people |
| Retest of fixed Blockers/Majors | As needed | Clinic lead tester |

### UAT script (`docs/uat/script.md`)
Patient-side scenarios (testers act as patients using persona cards):
1. New-patient booking by chat.
2. Existing-patient booking by voice.
3. Reschedule.
4. Cancel inside and outside the window.
5. "When is my appointment?"
6. FAQ (parking, insurance).
7. Tier 2 emergency ("tooth knocked out").
8. Tier 1 emergency ("can't breathe").
9. A complaint.
10. Switching voice → text mid-booking.
11. Giving WhatsApp consent, receiving the confirmation, replying STOP.

Staff-side scenarios (in the console):
1. Read and work a callback case (contact, attempt, resolve).
2. Find the AI-booked appointments and mark them reviewed.
3. Find a failed message.
4. Check the AI marker in Open Dental.
5. Change clinic hours and a holiday.
6. Request a change to the emergency rules.
7. Send a test callback email.

### Persona cards (`docs/uat/personas.pdf`)
12 fictional patients (`ZZUAT` surnames, `+1555555…` phones, DOBs 1940–2005), each with a short situation. The first page states: **"Use only these people. Never type a real patient's details on staging."**

### Staging safeguards
- A banner on the widget and the console: "TEST SYSTEM – fictional data only".
- Real-data incident rule: if a tester types real patient data, the facilitator records it, the data is purged (session, callback rows, Open Dental test DB records) within 24 hours, and the event goes into the P5-12 incident log as a low-severity privacy event.

### Issue form and severity (DECISIONS #275)
Form fields: tester role, scenario number, what happened, what was expected, persona used, screenshot (no real data).

| Severity | Definition | Rule before go-live |
|---|---|---|
| Blocker | Wrong booking, wrong patient, emergency mishandled, data shown to the wrong person, a staff task impossible | Must be fixed and retested |
| Major | Works but with clear difficulty or risk of staff error | Fixed, or accepted in writing by the clinic lead tester with a target date |
| Minor | Cosmetic or convenience | Backlog |

Who decides: the clinic decides workflow severity ("this blocks our front desk"). The tech lead decides technical severity. When they disagree, the higher severity wins.

### Policy confirmation checklist (`docs/uat/policy-checklist.md`)
Each row is shown with its current staging value and marked **Confirmed** or **Change to …** by the office manager:
- clinic hours and holidays;
- appointment types, durations and Open Dental mapping;
- booking horizon and lead times;
- cancellation and reschedule window;
- new-patient policy;
- reminder offset and confirmation toggle;
- callback email recipients and email mode;
- the AI marker text in Open Dental notes;
- the "not understood" limit (P2-01: 2);
- assistant name and greeting.

Changes are applied through the usual paths: the console, or file + release PR for file-only keys.

### Emergency rules sign-off (DECISIONS #275)
```bash
python tools/compliance/render_emergency_signoff.py \
  --rules config/clinics/<slug>/emergency_rules.yaml \
  --eval-report out/evals/report.json --out docs/compliance/signoffs/emergency-<slug>-<rules_version>.pdf
```
The PDF contains:
- clinic, `rules_version`, file SHA-256, date;
- every category with tier, phrases and the exact script text;
- the tier actions;
- the P5-01 emergency set result (pass counts, 0 under-triage);
- known gaps (P0-03 step 4);
- the statement "The AI never diagnoses or gives treatment advice";
- a signature block (name, role, date).

Signing: e-signature (Workspace-compatible tool, **Verify** that it is covered by the Google Workspace BAA or that the PDF holds no PHI, which it doesn't), or wet ink plus a scan. The signed PDF is stored in `docs/compliance/signoffs/` (private repo) and in the compliance drive.

Release PR `release: approve emergency rules <rules_version>`:
- changes `status: clinic_reviewed` → `approved` and sets `reviewed_by` / `reviewed_on`;
- adds the `config_imports` entry for prod (P1-19);
- CI check `check_signoff.py` verifies that the PDF exists for this `rules_version` and that the hash printed in it equals the file's SHA-256 **after** the status change. The status line is excluded from the hash by normalization; the script documents how.
- Needs the two prod approvers (P1-06).

Any later change to the rules creates a new `rules_version` and needs a new signed PDF.

### Sign-off form (`docs/uat/signoff-<date>.md` + signed PDF)
Release digest tested, scenarios run, issue counts by severity, accepted Majors with dates, policy checklist result, emergency rules version approved, signatures of the clinic lead tester and the dentist, and the tech lead's countersignature.

## 7. Implementation guide
1. Agree dates and participants with the office manager; send the agenda.
2. Prepare `uat-clinic` on staging (clone of the pilot config with the synthetic Open Dental DB), tester console accounts with MFA (P1-13 invite flow), and the banner flag `UI_TEST_BANNER=true` (staging only).
3. Write the script, persona cards, issue form (a simple form that writes GitHub issues through a bot, or a shared sheet without PHI), the policy checklist and the sign-off form.
4. Write `render_emergency_signoff.py` and `check_signoff.py` (CI on `config/clinics/*/emergency_rules.yaml`).
5. Run the guided session; the observer writes notes in `docs/uat/notes-<date>.md`.
6. Self-paced week; daily triage (15 min) by the facilitator and the tech lead.
7. Follow-up: walk through every issue, the policy checklist, then the emergency PDF with the dentist.
8. Release PR for the approved rules; retest Blockers/Majors; collect signatures.
9. Notify P6-01 (sign-off done, rules version) and P5-14 (evidence).

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| The dentist wants a phrase added during the session | New `rules_version` in a PR (P0-03 process); P5-01 emergency set re-run; a new PDF; sign that one |
| A Blocker is found on the last day | Fix, deploy to staging, retest by the clinic lead tester before signing |
| Staff can't attend the guided session | Run it as two shorter remote sessions; the dentist part can be separate |
| Tester enters real patient data | Purge within 24 h; incident log entry; reminder of the rule |
| Clinic refuses to accept a Major | It becomes a must-fix before go-live |
| Hash mismatch in `check_signoff.py` | PR blocked; the PDF must be regenerated and re-signed |
| Staging release changes during the self-paced week | Only for fixes; announce in the feedback channel; record the digest in the sign-off |

## 9. Security, HIPAA and PHI
- **No PHI by design:** fictional personas on staging (DECISIONS #25); the banner and the incident rule handle accidents.
- Tester accounts are per person, with MFA, staging only; they are removed after UAT.
- The emergency PDF contains rules and scripts only (no PHI); it is a compliance record kept for 6 years with the other evidence.
- Audit: console actions by testers are in the staging audit log; the release PR is the record for the status change.

## 10. Testing
```bash
python tools/compliance/render_emergency_signoff.py --rules tests/fixtures/rules_v3.yaml --eval-report tests/fixtures/report.json --out /tmp/x.pdf
pytest tools/compliance/tests -q          # hash normalization, check_signoff pass/fail
```
| # | Case | Expected |
|---|---|---|
| T1 | PDF for rules v3 | Contains version, hash, every script verbatim, eval summary |
| T2 | `check_signoff.py` with matching PDF | Pass |
| T3 | Rules file edited after signing | Fail (hash mismatch) |
| T4 | Status set to `approved` without a PDF | Fail |
| T5 | UAT run | All script scenarios executed; issue list triaged |

## 11. Acceptance criteria
- [ ] All patient and staff scenarios in the script were executed by clinic staff on staging (T5)
- [ ] No open Blocker; every Major fixed or accepted in writing with a date
- [ ] Policy checklist completed and changes applied
- [ ] UAT sign-off form signed by the office manager and the dentist, countersigned by the tech lead
- [ ] Emergency rules set to `approved` by a release PR whose CI verified the signed PDF hash (T2–T4)

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI (sign-off tools)
- [ ] PR reviewed (two prod approvers for the rules PR)
- [ ] No PHI entered on staging (or incidents handled)
- [ ] `docs/uat/` complete; evidence filed; P6-01 and P5-14 notified

## 13. Hand-off
| Consumer | What they can rely on |
|---|---|
| P6-01 Go-live | Signed UAT form; `approved` emergency rules version; confirmed policies |
| P5-14 HIPAA review | Signed emergency PDF and UAT form as evidence |
| P6-04 Pilot | Accepted Majors list with dates; staff already know the console |

## 14. Open questions
| # | Question | Recommended answer | Owner |
|---|---|---|---|
| 1 | Which e-signature tool? | One the company already has under the Workspace agreement; the PDF has no PHI, so a BAA is not required for it. **Verify** with the advisor. | Compliance advisor |

## 15. References
- Plan: §9 (UAT), §15 (clinic approval), §4.8
- DECISIONS: #14, #16, #25, #139, #275
- Related tasks: P0-01, P0-03, P1-06, P1-13, P1-19, P2-20, P4-11, P4-13, P4-13a, P4-17, P5-01, P5-12, P5-14, P6-01
