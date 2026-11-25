---
id: P5-12
title: Incident response plan and outage runbooks
milestone: P5
epic: E5.2
size: M
labels: area:compliance, area:infra, type:docs, phi
depends_on: P0-11, P0-09, P1-03, P1-05, P1-07, P1-12, P5-03, P5-08
status: approved
---

# P5-12: Incident response plan and outage runbooks

## 1. Summary
This task delivers four things. It absorbs **P5-13 (backup/restore drill and retention deletion jobs)**.

| Part | What it delivers |
|---|---|
| Incident response (IR) plan | Roles, severity levels, the timeline for breach assessment and the clinic notice (BAA: 5 business days), communication templates, the incident log |
| Runbooks | Step-by-step guides for each alert and outage in `docs/runbooks/`: Open Dental, LLM, STT/TTS, WhatsApp, email, database, Redis, deploy, secret exposure, PHI found in logs, breach, patient access requests, Binary Authorization break-glass, kill switch |
| Alert handling during the pilot | Alerts stay **email only**. On-call SMS is fully configured but **stays disabled** (user decision, DECISIONS #278). A daily **alert watcher** rotation checks the alert inbox during clinic hours |
| Backup, restore and retention | Restore drill, with RPO ≤ 5 min and RTO ≤ 4 h as targets. Nightly retention jobs that blank the PHI columns of expired rows and delete what isn't needed. Two tabletop exercises before go-live |

Done means:
- the runbooks are in `docs/runbooks/` and linked from every alert;
- the restore drill succeeded and was timed;
- the retention job deletes expired data on staging;
- both tabletop exercises are done and recorded.

## 2. Why this matters
Plan §15 requires runbooks for outages (Open Dental, LLM, STT/TTS, WhatsApp) and incidents. Several commitments depend on this task:
- **The clinic BAA (P0-09):**
  - a breach notice within 5 business days;
  - forwarding patient access and amendment requests within 5 business days;
  - returning or destroying data within 30 days, with a certificate.
- **P0-11 risks:**
  - R31: a breach detected late;
  - R21 and R22: outages;
  - R24: data loss;
  - R14: data kept too long.

Without this task those promises are paper. For example, on a Tuesday morning Open Dental goes down, and nobody knows whether to tell Sarah, switch off booking, or wait.

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P5, Hardening, Testing & Security Review**.
- **Security incident vs. breach (HIPAA):** an incident is any attempted or successful unauthorized access, use or disruption. A **breach** is an impermissible use or disclosure of PHI that compromises it, unless a documented risk assessment shows a low probability of compromise (45 CFR 164.402; **Verify** the wording with the advisor). As a business associate, we must notify the clinic (the covered entity). The clinic notifies patients and HHS.
- **RPO / RTO:** the recovery point objective is how much data we may lose (time between the last good copy and the failure). The recovery time objective is how long the service may be down.
- **PITR (point-in-time recovery):** Cloud SQL can restore to any second inside the transaction-log window (P1-03: 7 days; 30 daily backups kept).
- **Tabletop exercise:** a meeting in which the team walks through an imagined incident step by step, to find gaps in the plan without anything actually breaking.
- **What already exists (approved):**
  - **P1-07:**
    - alert policies;
    - `infra/monitoring/notification_targets.yaml`: email is active; on-call SMS and chat are defined but disabled (DECISIONS #117);
    - `AUDIT_RETENTION_DAYS` (default 2190);
    - the weekly DB-vs-mirror audit count check;
    - the `data.retention_delete` audit action.
  - **P1-03:**
    - database roles; retention deletes run as `app_owner` and switch off the audit-table triggers only inside their own transaction (DECISIONS #96);
    - PITR and backups;
    - the `postgres` break-glass password in Secret Manager.
  - **P1-05:** PAM entitlements `ops-read`, `ops-write`, `key-admin`, `db-breakglass` (max 4 h, the approver is not the requester).
  - **P0-09:** the commitments table `docs/compliance/baa/commitments.md`.
  - **P0-11:** the risk list R01–R33.
  - **P1-19:** `privacy.transcript_retention_days` (0–30; currently 0).
  - **P5-03:** observed limits. **P5-08:** the secret-exposed and PHI-in-logs cases.

## 4. Scope
**In scope**
- `docs/compliance/incident-response-plan.md`, the incident log, communication templates.
- Runbooks (list in §6) with a fixed template; every P1-07 alert policy gets a `documentation` link to its runbook.
- The alert-watcher rotation and its handover note; on-call SMS kept configured but disabled.
- The retention policy table, the migration for purge markers, the nightly retention job, the retention report, and the return/destroy procedure with its certificate template.
- The restore drill (staging, then a prod clone into an isolated instance before PHI arrives) and its schedule.
- Two tabletop exercises before go-live.

**Out of scope** (and which task covers it)
- The kill switch implementation → P6-01 (this task writes its runbook)
- Fixing root causes found in drills → the owning task
- HIPAA policies beyond IR and contingency (training, access reviews, devices) → P5-14

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P1-07 alerts | Policy names and links | Approved; add `documentation.content` per policy |
| P1-03 schema | Tables and roles | Approved; the migration is additive |
| P5-08 | Secret and PHI-log cases | Write those runbooks from §6; refine after P5-08 |
| P6-01 kill switch | Flags `pilot.*_enabled` | Write the runbook against the flag names in DECISIONS #280 |

## 6. Interface contract

### Roles (DECISIONS #278)
| Role | Who | Duties |
|---|---|---|
| Incident Commander (IC) | The alert watcher of the day, until handed over | Declares the incident and its severity, owns the timeline, assigns tasks |
| Tech lead | Tech lead | Technical decisions, fixes, kill switch decisions |
| Communications | Sponsor | All contact with the clinic and vendors; uses the templates |
| Compliance | Compliance advisor | Breach risk assessment, notice content, records |
| Scribe | Any other engineer | Incident log entries with times |

### Severity
| Level | Examples | Response |
|---|---|---|
| SEV1 | Suspected PHI exposure; wrong-patient disclosure; emergency mishandled live; full outage during clinic hours | IC within 15 min in clinic hours; kill switch considered; clinic informed the same day (Sarah) |
| SEV2 | One channel down (voice, WhatsApp); Open Dental unreachable > 15 min; callback emails failing | IC within 1 h; workaround; clinic informed if staff action is needed |
| SEV3 | Degraded latency; a single failed job; non-PHI security finding | Next business day |

### Alert handling during the pilot (DECISIONS #278)
- **Alerts go to email only.** On-call SMS and chat stay configured in `notification_targets.yaml` and are validated in CI, but stay `enabled: false` (user decision).
- **Alert watcher rotation** `docs/runbooks/alert-watcher.md`:
  - one named engineer per day, Monday–Friday, during clinic hours plus 30 minutes;
  - checks the alert inbox at least every 30 minutes, with mail notifications on;
  - starts the day by reading the overnight alerts;
  - the rotation lives in `docs/runbooks/rotation.md`; swaps go by PR or a note in the team channel.
- Outside clinic hours, alerts are read the next morning. That is acceptable because the AI only answers during the pilot hours (P6-01).
- Turning SMS on later is a release PR changing `enabled: true` (two prod approvers). The runbook describes it.

### Runbooks (`docs/runbooks/`, one template)
```markdown
# <Title>
- Alert(s): <P1-07 policy names>    - Severity default: SEV2
- Symptoms / how to confirm (dashboards, log queries — no PHI in queries)
- Immediate actions (numbered, with exact commands)
- Patient impact and what patients see
- Clinic communication (template id)
- Recovery and verification
- Follow-up (incident log, post-incident review if SEV1/2)
```
| Runbook | Key actions |
|---|---|
| `open-dental-outage.md` | Confirm with `/internal/health/od`; booking paths already fall back to callbacks (P2-22/P2-24); tell Sarah; keep the AI on while callbacks still work (patients get a callback instead of a booking); use the kill switch only if callback creation or emails also fail; after recovery, check the callbacks created during the outage |
| `llm-outage.md` | Router fallback (P2-06); Vertex AI status; 429 → quota request (P5-03 limits); prolonged → kill switch per channel |
| `stt-tts-outage.md` | Text-only mode (P2-28) automatically; voice kill switch if errors persist |
| `whatsapp-outage.md` | Messages queue and retry (P4-01); give-ups appear in failed messages (P4-13a); clinic informed of reminders not sent |
| `email-outage.md` | Callback emails retry; console shows unsent (P2-22); Sarah told to check the console list |
| `database.md` | Cloud SQL failover / restore (PITR steps, below) |
| `redis.md` | Memorystore restart; sessions lost → patients see "please start again" |
| `bad-deploy.md` | `rollback.yml` (P1-06) |
| `secret-exposed.md` | Rotate (Open Dental key via portal or clinic, Google keys, BSP token), update Secret Manager, redeploy, audit review, incident log |
| `phi-in-logs.md` | Stop the source (hotfix), find the extent, delete entries (log bucket purge procedure; **Verify** the method), breach assessment |
| `breach.md` | §6 breach timeline |
| `patient-requests.md` | Access/amendment/accounting requests forwarded to the clinic within 5 business days; data we hold is listed per PatNum with a script run under `ops-read` |
| `break-glass.md` | `db-breakglass` and the Binary Authorization break-glass (P5-08): when allowed, approvals, audit |
| `kill-switch.md` | P6-01 flags: who, how, verification, how to turn back on (two people) |
| `alert-watcher.md` | Rotation duties |

### Breach timeline (DECISIONS #278)
| Step | When | Who |
|---|---|---|
| Discovery: first person aware writes the incident log entry | T0 | Anyone |
| IC declared, containment started | ≤ 1 h in clinic hours | IC |
| Facts gathered (what data, how many patients, how long) | ≤ 2 business days | Tech lead |
| Breach risk assessment (4 factors) | ≤ 3 business days | Compliance advisor |
| Written notice to the clinic | ≤ 5 business days from discovery (BAA) | Sponsor (Communications) |
| Post-incident review and fixes | ≤ 10 business days | Tech lead |
The clock starts at **discovery** (the first moment anyone on the team knows or should reasonably have known). The incident log records that time. Template `docs/compliance/templates/breach-notice-to-clinic.md` holds the facts only: what, when, which data types, the number of patients (PatNums are given to the clinic through a secure channel, not in email), and the mitigation.

### Incident log (`docs/compliance/incident-log.md`, private repo)
One entry per incident: ID, times (discovery, declared, contained, resolved), severity, summary **without PHI**, decisions, notice sent (yes/no, date), follow-up issues. Kept 6 years.

### Retention policy (DECISIONS #278; Proposed values, advisor to Verify)
| Data | Where | Kept | Action at expiry |
|---|---|---|---|
| Callback PHI (`contact_name_enc`, `contact_phone_enc`, `contact_phone_bidx`, `contact_dob_enc`, `contact_email_enc`, `preferred_time_enc`, `summary_enc`) | `callback_requests` | 90 days after `resolved_at` | Columns set to NULL, `phi_purged_at` set; row kept (codes and timestamps for KPIs) |
| Unresolved callbacks | same | Never purged automatically; flagged after 30 days in the console | - |
| `callback_attempts` | table | Same as their callback | Rows deleted with the purge |
| `config_change_requests.description_enc` | table | 1 year after closed | NULL |
| `sessions` | table | 1 year | Rows deleted |
| `appointment_refs` | table | 1 year after `updated_at` | Rows deleted |
| `outbound_messages` metadata | table | 1 year | Rows deleted |
| `reminders` | table | 1 year after `scheduled_for` | Rows deleted |
| `contact_prefs` | table | While consent is active; 1 year after consent revoked | Row deleted |
| `consents` | table | 6 years (proof of consent) | Rows deleted (as `app_owner`, audited) |
| `audit_log` | table + log bucket | `AUDIT_RETENTION_DAYS` = 2190 (6 years; DECISIONS #117) | Rows deleted; bucket lifecycle |
| Transcripts | - | 0 days (P0-01 Q9); if P6-04 enables pilot transcripts, `privacy.transcript_retention_days` (max 30) | Deleted |
| Redis sessions | Memorystore | Session TTL (P2-01) | Expire |
| Cloud SQL backups / PITR | Cloud SQL | 30 backups / 7 days (P1-03) | Automatic expiry (documented as the end of deletion) |
| Application logs | Cloud Logging | Per P1-07 bucket settings (no PHI by design) | Bucket retention |

Schema change (additive to P1-03): `callback_requests.phi_purged_at timestamptz NULL`. Every `NOT NULL` PHI column gets a check constraint `(<col> IS NOT NULL) OR (phi_purged_at IS NOT NULL) OR <existing URGENT rule>`. The same is done for `config_change_requests`.

### Retention job
```python
# backend/app/domain/retention/job.py   (Cloud Scheduler → Cloud Tasks → POST /internal/tasks/retention, daily 03:30 clinic time)
async def run_retention(now: datetime, dry_run: bool = False) -> RetentionReport:
    # runs as app_owner (separate DB connection with that role); each table in its own transaction;
    # batches of 500 rows; audit action data.retention_delete {table, action: purge|delete, count}
```
```json
{"run_at": "2027-03-02T08:30:00Z", "dry_run": false,
 "results": [{"table": "callback_requests", "action": "purge", "count": 14},
             {"table": "sessions", "action": "delete", "count": 1203}],
 "errors": []}
```
A failure raises alert `retention-job-failed` (new P1-07 policy, email). Retention periods are config: `RETENTION_*_DAYS` env vars with the defaults above, validated at startup (min/max per row).

### Return/destroy at contract end (BAA R10)
`docs/runbooks/contract-end.md`:
1. export what the clinic asks for (their data is in Open Dental already; we hold callbacks and consents);
2. run the purge for that `clinic_id` with `scope=all`;
3. delete secrets and config;
4. let backups expire, or delete the instance if the clinic was the only tenant;
5. issue the destruction certificate (`docs/compliance/templates/destruction-certificate.md`) within 30 days.

### Restore drill (DECISIONS #278)
| Item | Value |
|---|---|
| Targets | RPO ≤ 5 min, RTO ≤ 4 h |
| Frequency | Before go-live (on staging, then once on prod before PHI is enabled), then every 3 months |
| Method | `gcloud sql instances clone` / PITR restore to a **new** isolated instance at a chosen timestamp (**Verify** the command flags), run `scripts/ops/verify_restore.py` (row counts per table vs. source at that time, audit hash chain check from P1-12, a test login on a temporary `api` revision pointed to the clone), then delete the clone |
| Record | `docs/runbooks/drills/restore-<date>.md`: start, ready time, verification result, issues; RTO measured from start to verified |

### Tabletop exercises (before go-live)
1. **"PHI found in logs"** (R01/R31): team + compliance advisor; walks through `phi-in-logs.md` and the breach timeline.
2. **"Open Dental down for a whole clinic day"** (R21): team + Sarah; walks through the clinic side (callbacks, what to tell patients).

Records: `docs/compliance/tabletops/<date>.md` with participants, scenario, findings, actions.

## 7. Implementation guide
1. Write the IR plan, the severity table, the roles, the breach timeline, the templates and the incident log.
2. Write the runbooks with the template; add `documentation` links to every P1-07 alert policy (Terraform).
3. Alert-watcher rotation doc; confirm `notification_targets.yaml` keeps SMS disabled; CI still validates the disabled entries.
4. Migration for `phi_purged_at` and the check constraints; the retention job, its config, its alert and tests.
5. Contract-end runbook and certificate template.
6. Restore drill on staging; record it. Before PHI is enabled in prod (P6-01), repeat it on prod.
7. Tabletop 1 (team + advisor) and tabletop 2 (team + Sarah); record actions as issues.
8. Notify P5-14 (evidence), P6-01 (gate items), P0-09 commitments table (owner rows now point to real documents).

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| Alert at 07:00 before the watcher's day starts | Read at the start of the day; acceptable (the AI is off outside pilot hours) |
| Watcher is sick | Next person in the rotation covers; swap recorded |
| Retention job fails halfway | Each table is its own transaction; the next run continues; alert sent |
| A purged callback is reopened by staff | Not possible: reopen (P4-13a) needs PHI; the console shows "details removed under the retention policy" |
| Legal hold requested (for example a complaint) | `legal_hold` flag on the callback (Proposed: an ADMIN-only action, audited) skips purge until cleared |
| Restore drill exceeds 4 h | Drill fails; issue for the tech lead; re-drill after the fix |
| Breach suspected on a Friday evening | The 5 business days start at discovery; IC declared at once; work continues next business day unless SEV1 needs weekend work |
| Clinic asks for a 24-hour breach notice | Only if we can deliver it (P0-09 rule); with SMS off we can't, so counter-propose |

## 9. Security, HIPAA and PHI
- Runbooks and log queries never contain PHI. Investigations that need PHI use PAM grants and stay inside Google Cloud.
- The retention job is the main PHI-deletion control. It runs as `app_owner`, every run is audited, and the report holds counts only.
- The incident log and notices contain no PHI. Affected PatNums are shared with the clinic through a secure channel.
- Restore clones are created in the same project (CMEK, US region) and deleted after verification. Creating one needs `ops-write` through PAM.

## 10. Testing
```bash
pytest backend/tests/integration/retention -q
python -m app.domain.retention.job --dry-run --now 2027-06-01T00:00:00Z     # staging
python scripts/ops/verify_restore.py --source <instance> --clone <clone> --at <timestamp>
```
| # | Case | Expected |
|---|---|---|
| T1 | Callback resolved 91 days ago | PHI columns NULL, `phi_purged_at` set, row kept |
| T2 | Callback resolved 89 days ago / unresolved | Unchanged |
| T3 | Consent 6 years + 1 day old | Deleted, audited |
| T4 | Audit rows past `AUDIT_RETENTION_DAYS` | Deleted inside the job's transaction; trigger re-enabled; audit row for the deletion |
| T5 | Retention job error | Alert sent; other tables processed |
| T6 | Restore drill on staging | Verified, RTO ≤ 4 h, data at the chosen time (RPO ≤ 5 min) |
| T7 | Every P1-07 alert policy | Has a runbook link that resolves |
| T8 | Legal hold | Row skipped |

## 11. Acceptance criteria
- [ ] IR plan, breach timeline, templates and incident log exist and are reviewed by the compliance advisor
- [ ] All runbooks in §6 exist in `docs/runbooks/` and every alert links to one (T7)
- [ ] Alert-watcher rotation running; SMS on-call configured but disabled
- [ ] Retention job deletes and purges expired data on staging per the policy table (T1–T5, T8)
- [ ] Restore drill succeeded and was timed within RPO/RTO (T6)
- [ ] Both tabletop exercises done and recorded with actions

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI
- [ ] PR reviewed (HIPAA review: label `phi`)
- [ ] No PHI in runbooks, logs or reports
- [ ] P5-14, P6-01 notified; P0-09 commitments rows updated

## 13. Hand-off
| Consumer | What they can rely on |
|---|---|
| P5-14 HIPAA review | IR plan, contingency evidence (drill, tabletops), retention policy |
| P6-01 Go-live | Gate items: runbooks linked, watcher rotation staffed, restore drill on prod done |
| P6-04 Pilot | Runbooks in daily use; transcript retention hook if enabled |
| P4-13a console | "Details removed under the retention policy" state for purged callbacks |

## 14. Open questions
| # | Question | Recommended answer | Owner |
|---|---|---|---|
| 1 | Are the retention periods acceptable to the clinic and the advisor? | Use the table; confirm in P5-14 and with Sarah during UAT (P5-07 policy checklist). | Compliance advisor |
| 2 | When should SMS on-call be turned on? | When the pilot extends beyond clinic hours or a second clinic joins. | Sponsor |

## 15. References
- Plan: §15 (runbooks), §5, §6, §8 Phase 5
- DECISIONS: #45, #96, #102, #117, #278
- Related tasks: P0-09, P0-11, P1-03, P1-05, P1-07, P1-12, P1-19, P2-06, P2-22, P2-24, P2-28, P4-01, P4-13a, P5-03, P5-08, P5-14, P6-01, P6-04
- HHS Breach Notification Rule: <https://www.hhs.gov/hipaa/for-professionals/breach-notification/index.html>
- Cloud SQL PITR: <https://cloud.google.com/sql/docs/postgres/backup-recovery/pitr>
