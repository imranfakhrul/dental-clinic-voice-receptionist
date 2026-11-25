---
id: P0-08
title: Decide admin email route and sign BAA
milestone: P0
epic: E0.2
size: S
labels: area:compliance, area:messaging, type:chore
depends_on: P0-01
status: approved
---

# P0-08: Decide admin email route and sign BAA

## 1. Summary
Set up the channel that carries **callback-request emails to the clinic admin** (plan §4.9):
- Gmail API from our company's **Google Workspace**, after accepting the **Workspace HIPAA BAA**;
- a dedicated sender mailbox with TLS enforced to each clinic's mail domain, and SPF/DKIM/DMARC on our domain;
- a designed (not yet built) keyless way for the backend to send.

Also record the default content mode, **case ID + link only, with no PHI in the email**. Full details are an opt-in per clinic, allowed only with the compliance advisor's written approval. Finally, define a per-clinic readiness check for the recipient mailbox. Done means: the BAA is accepted and recorded, a synthetic test email arrives over TLS with DKIM passing, the templates and config keys are documented for P2-23, and the pilot clinic's readiness check has been run.

## 2. Why this matters
There is no live transfer to a human (§4.9): every unresolved conversation, every URGENT emergency case (§4.8) and every failed booking ends in a callback case plus an email to the admin. If the email doesn't arrive, a patient in pain may never be called back. The plan's KPI is 100% of callback emails delivered (§11).

The plan's email template contains PHI (name, phone, DOB, situation). Email is the easiest place to leak it: wrong recipient, unencrypted hop, copies in Sent folders. This task picks the route with the fewest vendors (§1 principle 6), makes TLS mandatory, and makes the safest content mode the default.

P2-23 (admin email sender) depends on this task. P4-13 (callback settings screen) and P4-14 (cases list, unsent alerts) use its config keys and link format.

Plan references: §3.2, §3.3, §4.8, §4.9, §7 (callback settings), §11, §13 Q4 and Q7.

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P0, Discovery & Compliance Foundation**.
- **Callback case (§4.9):** a record in our database (`callback_requests`) with reason, urgency, patient details (encrypted), status OPEN/CONTACTED/RESOLVED and `email_status`. Created by P2-22; the email is sent by P2-23.
- **Google Workspace HIPAA BAA:** accepted by a **super administrator** in the Admin console: Menu → Account → Account settings → Legal and compliance → "Security and Privacy Additional Terms" → "Google Workspace/Cloud Identity HIPAA Business Associate Amendment" → Review and Accept → answer the three covered-entity questions → OK. Not available on the legacy free edition. Source: https://knowledge.workspace.google.com/admin/compliance/hipaa-compliance-with-google-workspace-and-cloud-identity. **Verify:** which current paid editions qualify; the page doesn't list them.
- **Gmail is covered** (listed under Google Workspace supported services: https://docs.cloud.google.com/docs/security/compliance/hipaa). Third-party add-ons are not covered. Google says customers without a BAA "must not use PHI in Google Workspace".
- **TLS compliance setting:** Admin console → Apps → Google Workspace → Gmail → Compliance → "Secure transport (TLS) compliance". With a rule for a recipient domain, mail to a server without TLS **bounces** (one attempt, then a non-delivery report). Without the rule, Gmail falls back to sending without TLS. Source: https://knowledge.workspace.google.com/admin/gmail/advanced/send-email-over-a-secure-tls-connection
- **Limits:** 2,000 messages per user per day (https://knowledge.workspace.google.com/admin/gmail/gmail-sending-limits-in-google-workspace). The Gmail API's `messages.send` costs 100 quota units, against 6,000 units per user per minute, roughly 60 sends per minute (https://developers.google.com/workspace/gmail/api/reference/quota). That is far above our volume.
- **SPF / DKIM / DMARC:** DNS records that prove our domain is allowed to send, so callback emails don't land in spam.
- **Not an option:** Twilio SendGrid. Twilio's HIPAA Eligible Services list (2026-06-30) contains no email product.
- **Service-account keys are blocked** by org policy (P0-06), so any backend authentication must be keyless.

## 4. Scope
**In scope**
- Confirming the company's Workspace edition can accept the BAA; accepting it; recording it.
- Sender mailbox `callbacks@<company domain>` in its own organizational unit (OU), with a locked-down configuration.
- TLS compliance rule for each clinic's domain (pilot clinic now; a runbook for later clinics).
- SPF, DKIM, DMARC for the sending domain.
- The **design** of backend authentication to Gmail (keyless), documented for P2-23.
- The default content mode and both email templates (link-only, full details).
- The config keys for callback email settings.
- A per-clinic recipient readiness check, run for the pilot clinic.
- One synthetic end-to-end test email.

**Out of scope** (and which task covers it)
- Writing the sender code, retries, unsent alerts → P2-23
- Creating callback cases → P2-22
- The case page that the link opens, login and MFA → P4-14, P4-09, P1-13
- The settings screen for emails and mode → P4-13
- Patient-facing email (P0-07a option D) → only if P0-07a chooses it; it would reuse this Workspace and BAA
- Vendor matrix → P0-10; clinic ↔ company BAA → P0-09

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P0-01 Discovery workshop (approved spec) | Q4b: admin address(es), including after hours; Q7: does the clinic use Workspace; B7: content mode preference | Do everything on our side (steps 1–7) now. Use a team mailbox as the test recipient. Run the clinic readiness check (step 9) once Q4b is answered. |
| P0-05 Google Cloud org (approved spec, soft) | Company domain and super-admin process; prod project for the sending service account | The Workspace BAA is separate from the Cloud BAA and can be accepted at any time. Design the service account now; P1-05 creates it. |
| P0-06 Guardrails (approved spec, soft) | Allowed APIs | Tell P0-06's owner that `gmail.googleapis.com` and `iamcredentials.googleapis.com` must be allowed in prod (step 6). **Verify:** whether the Gmail API is affected by `gcp.restrictServiceUsage` and VPC-SC at all. |

## 6. Interface contract

### Config keys (Proposed; per clinic in `clinic_config`, edited later in P4-13)
| Key | Type | Default | Meaning |
|---|---|---|---|
| `callback.admin_emails` | list of email | - (required) | Clinic-controlled mailboxes receiving callback emails (P0-01 Q4b) |
| `callback.after_hours_emails` | list of email | same as `admin_emails` | Used outside clinic hours |
| `callback.email_mode` | `link_only` \| `full_details` | `link_only` | Content mode |
| `callback.full_details_approval` | string or null | null | Reference to the compliance advisor's written approval; required when `email_mode = full_details` |

Environment variables (P2-23, Proposed):
| Key | Example | Meaning |
|---|---|---|
| `ADMIN_EMAIL_SENDER` | `callbacks@example.com` | The only mailbox the backend may send as |
| `ADMIN_EMAIL_SA` | `admin-email-sender@<prefix>-prod.iam.gserviceaccount.com` | Service account used for keyless delegation |
| `ADMIN_CONSOLE_BASE_URL` | `https://admin.example.com` | Base for case links |

**Load-time rules (P1-19 / P2-23):**
- `full_details` without `full_details_approval` → treat as `link_only` and log a warning (no PHI in the log).
- Every address must be on a domain that passed the readiness check (§6, below).
- No consumer addresses (`gmail.com`, `yahoo.com`, …).

### Templates
**`link_only`** (default; no PHI anywhere in the email):
```
Subject: [ACTION NEEDED] Patient callback request – {URGENT|Normal} – Case {case_id}

A patient needs a callback from your team.

Urgency:   {URGENT|Normal}
Received:  {received_at, clinic time zone}
Case ID:   {case_id}

Open the case (login required): {admin_console_base_url}/cases/{case_id}

This email intentionally contains no patient details.
This mailbox is not monitored. Do not reply.
```
`case_id` is a random opaque ID (e.g. UUID). It is never a PatNum, a phone number or anything derived from patient data.

**`full_details`** (only with approval): the plan §4.9 template (name, phone, WhatsApp number, patient type with PatNum, DOB, email, reason category, situation, preferred time, urgency, received time, case ID and link). The subject still contains **no** patient name or reason, only urgency and case ID.

### Backend authentication (design for P2-23; Proposed, Verify before build)
- A dedicated service account `admin-email-sender` in `<prefix>-prod`, attached to the Cloud Run service that sends email.
- **Workspace domain-wide delegation** for that service account, limited to the single scope `https://www.googleapis.com/auth/gmail.send`. It is used only to impersonate `callbacks@`.
- **Keyless:** no JSON key (blocked by P0-06). The service signs the delegation token through the IAM Credentials API (`signJwt`) as its own identity.
- **Verify:**
  - that this is Google's documented method for sending as a Workspace user from a backend;
  - that keyless delegation via `signJwt` works for Gmail;
  - whether a Google-recommended alternative exists (e.g. OAuth for a dedicated user, or Workspace SMTP relay).

  Record the answer in `docs/integrations/admin-email.md`.

### Records
| Path | Content |
|---|---|
| `docs/compliance/baa-google-workspace.md` | Same format as the P0-05 BAA record (edition, date, acceptor, saved copy) |
| `docs/integrations/admin-email.md` | Route, sender, OU settings, DNS records, auth design, templates, limits |
| `docs/runbooks/admin-email-add-clinic.md` | Steps to add a clinic: readiness check, TLS rule, config |
| `docs/compliance/email-readiness-<clinic_slug>.md` | Readiness check result per clinic |

### Recipient readiness check (per clinic, before any real case)
| # | Check | Pass when |
|---|---|---|
| 1 | Address is clinic-controlled | On the clinic's own domain (not a consumer webmail address); the SME confirms who reads it |
| 2 | Mail server supports TLS | The domain's MX accepts STARTTLS (check with an online TLS checker or `openssl s_client -starttls smtp -connect <mx>:25`) |
| 3 | TLS rule added | The domain is in the sender OU's TLS compliance rule |
| 4 | Test email arrives | A synthetic link-only email arrives, not in spam; the received headers show TLS |
| 5 | Clinic's own mailbox is HIPAA-appropriate | The SME confirms the clinic's email provider is covered by the clinic's own arrangements (the clinic is the covered entity). Required only for `full_details`. |

## 7. Implementation guide
1. **Edition check.** Confirm the company's Workspace edition can accept the BAA (**Verify** against Google's current list or with Google support). If it can't, upgrade the edition (sponsor approves the cost) or fall back to a HIPAA email provider with a BAA (log it in DECISIONS.md).
2. **Accept the BAA** as super admin (path in §3). Save the accepted text as a PDF. Write `docs/compliance/baa-google-workspace.md`.
3. **Sender mailbox.** Create the user `callbacks@<company domain>` in a new OU `system-senders`, then:
   - enforce 2-step verification;
   - turn off POP/IMAP and automatic forwarding;
   - allow no third-party apps or add-ons;
   - set an auto-reply: "This mailbox is not monitored."

   Nobody uses it interactively.
4. **TLS compliance rule** on the `system-senders` OU, with the pilot clinic's domain (and a team test domain). Mail to listed domains must use TLS or bounce.
5. **Email authentication.**
   - Publish SPF including Google.
   - Enable DKIM signing in the Admin console.
   - Publish DMARC: start at `p=none` with reports to a team address, move to `p=quarantine` once reports are clean (Proposed).
6. **Auth design.** Write the delegation design (§6) in `docs/integrations/admin-email.md`, after verifying it against Google's docs. Tell P0-06 / P1-05 which APIs and which service account are needed. Don't create the delegation in production yet; P2-23 does it in dev first.
7. **Synthetic end-to-end test.** From a team member's machine, send one link-only test email as `callbacks@` (Gmail web or an API script under a dev OAuth client) to a team mailbox on a TLS-enforced domain. Check the received headers show TLS and `dkim=pass`. Then send to a domain **without** TLS (if one is available for testing) and confirm it bounces.
8. **Content mode.** Record `link_only` as the default in DECISIONS.md and in `admin-email.md`, with both templates. Full details only per clinic, with an advisor approval reference.
9. **Pilot clinic readiness.** Once P0-01 Q4b is answered, run the readiness check, add the domain to the TLS rule, and save the result.
10. **Retention note for `full_details`.** If a clinic is ever approved for full details, the sender's Sent folder holds PHI. Proposed: a retention rule deletes Sent items after 30 days. **Verify:** Vault or retention availability in our edition. Record this in `admin-email.md`.
11. **Notify** P2-23 (templates, config, auth design), P4-13 (config keys), P4-14 (link format `/cases/{case_id}`), P0-06 / P1-05 (APIs, service account) and P0-10 (BAA record).

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| The company's Workspace edition can't accept the BAA | Upgrade (sponsor approves the cost) or use a HIPAA email provider with a BAA. Until then, no PHI in email, and callback cases are visible only in the console. |
| The clinic's mail server doesn't support TLS | The email bounces. P2-23 marks it unsent and shows an alert. The clinic must fix TLS or give another clinic-controlled address. Never remove the TLS rule. |
| The clinic gives a consumer address (e.g. Gmail) | Refuse. Ask for a clinic-domain address. |
| The clinic wants full details in the email | Allowed only with written advisor approval and readiness check #5. Record `full_details_approval`. |
| An urgent case after hours | Send to `after_hours_emails` (P0-01 Q4b). The subject carries "URGENT". |
| The link is opened by someone who isn't authorized | The console requires login + MFA + role (P1-13, P4-09); the link alone reveals nothing. |
| The admin console doesn't exist yet (before P4) | Only synthetic data exists before the pilot; staging emails link to a placeholder page. Real PHI starts only at the pilot (P6), after P4-14. |
| Someone replies to the callback email | The auto-reply says the mailbox isn't monitored. Replies are never read and must not contain PHI. |
| Callback emails land in spam | Check SPF/DKIM/DMARC alignment; the readiness test (#4) catches it before go-live. |
| The Gmail API or Workspace is down | P2-23 retries with backoff, and shows an unsent alert after the final failure. The case is always visible in the console. |
| The daily sending limit is reached | Practically impossible at our volume (2,000/day). P2-23 alerts if quota errors occur. |

## 9. Security, HIPAA and PHI
- **PHI in this task:** none. Only synthetic test emails.
- **PHI in production (designed here):**
  - **`link_only`:** no PHI leaves our system by email. The case ID is random.
  - **`full_details`:** name, phone, WhatsApp number, DOB, email, situation and PatNum travel through Google Workspace (under the BAA) over enforced TLS to a clinic-controlled mailbox. Copies stay in the sender's Sent folder (retention rule, §7 step 10).
- **Never log:** email bodies or recipient-specific PHI. Log only case ID, Gmail message ID, status, timestamp and error code (P2-23, P1-11).
- **Access:** nobody signs in to `callbacks@` interactively. The backend may send only as `callbacks@`, only with `gmail.send`, and keyless.
- **Audit:** every send attempt and result is audited per case (§4.9; P2-23 with P1-12).

## 10. Testing
No application code. Checks, with results recorded in `admin-email.md`:
- BAA status in the Admin console shows accepted; the PDF is saved.
- `dig TXT <domain>` shows SPF; `dig TXT google._domainkey.<domain>` shows DKIM; `dig TXT _dmarc.<domain>` shows DMARC.
- The synthetic test email (§7 step 7) arrives with TLS and `dkim=pass` in the headers. The non-TLS test bounces (if a test domain is available).
- The pilot clinic readiness check passes all applicable rows.
- The reviewer confirms the `link_only` template contains no patient field and the subject has no name or reason.

## 11. Acceptance criteria
- [ ] The Workspace HIPAA BAA is accepted by a super admin and recorded in `docs/compliance/baa-google-workspace.md` with a saved copy
- [ ] `callbacks@` exists in OU `system-senders` with 2SV, no POP/IMAP, no forwarding, no add-ons, and a not-monitored auto-reply
- [ ] The TLS compliance rule covers the pilot clinic's domain; a non-TLS recipient would bounce (tested where possible)
- [ ] SPF, DKIM and DMARC are published, and a test email shows `dkim=pass`
- [ ] Both templates and the config keys are documented; `link_only` is the recorded default
- [ ] The keyless delegation design is verified against Google's docs (or replaced by the documented alternative) and handed to P2-23
- [ ] The pilot clinic readiness check is run and saved
- [ ] The P2-23, P4-13, P4-14, P0-06, P1-05 and P0-10 issues are notified

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI: not applicable (no code); the §10 checks are recorded
- [ ] PR reviewed (HIPAA review if labelled `phi`): reviewed by the tech lead and the compliance advisor; no `phi` label because no PHI is handled
- [ ] No PHI in logs: synthetic data only
- [ ] Docs / README updated: `admin-email.md`, the runbook and the BAA record linked from `docs/`

## 13. Hand-off
| Task | Can rely on |
|---|---|
| P2-23 Admin email sender | Sender address, templates, config keys and load-time rules, auth design, limits, logging rules |
| P2-22 Callback cases | `case_id` must be random and opaque (it appears in emails) |
| P4-13 Callback settings | The config keys and their validation rules |
| P4-14 Cases list | Link format `{ADMIN_CONSOLE_BASE_URL}/cases/{case_id}`; unsent-email alerts |
| P0-06 / P1-05 | APIs (`gmail.googleapis.com`, `iamcredentials.googleapis.com`) and the `admin-email-sender` service account |
| P0-10 Vendor matrix | `baa-google-workspace.md` |
| P0-07a | If option D (patient email) is chosen, the same Workspace + BAA route |

## 14. Open questions
| Question | Owner | Needed by |
|---|---|---|
| Which Workspace edition does the company have, and can it accept the BAA? | Company owner | Step 1 |
| Which super admin accepts the BAA (authority to bind the company)? | Company owner | Step 2 |
| Is domain-wide delegation (keyless) Google's documented way to send as a Workspace user from a backend, or is there a preferred alternative? | Tech lead | Step 6 |
| Does the Gmail API fall under `gcp.restrictServiceUsage` / VPC-SC in the prod project? | Tech lead | Step 6 |
| Retention period for Sent items if `full_details` is ever used (Proposed 30 days)? | Compliance advisor | Before any clinic uses full details |

## 15. References
- Plan §1 (principle 6), §3.2, §3.3, §4.8, §4.9 (template and safeguards), §7, §11, §13 Q4 and Q7
- HIPAA with Google Workspace (BAA acceptance): https://knowledge.workspace.google.com/admin/compliance/hipaa-compliance-with-google-workspace-and-cloud-identity
- Google Cloud / Workspace HIPAA supported services: https://docs.cloud.google.com/docs/security/compliance/hipaa
- Gmail TLS compliance: https://knowledge.workspace.google.com/admin/gmail/advanced/send-email-over-a-secure-tls-connection
- Gmail sending limits: https://knowledge.workspace.google.com/admin/gmail/gmail-sending-limits-in-google-workspace
- Gmail API quotas: https://developers.google.com/workspace/gmail/api/reference/quota
- Related tasks: P0-01, P0-05, P0-06, P0-07a, P0-09, P0-10, P1-05, P1-11, P1-12, P1-13, P1-19, P2-22, P2-23, P4-09, P4-13, P4-14
