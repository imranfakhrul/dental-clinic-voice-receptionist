# Admin callback email (P0-08)

| | |
|---|---|
| Task | P0-08 ([issue #9](https://github.com/imranfakhrul/dental-clinic-voice-receptionist/issues/9)) |
| Prepared by | Riley Tech (tech lead), 2026-11-26 |
| Status | **Designed; not live.** Route: Gmail from our company Google Workspace. No company domain or Workspace exists yet; they're bought for production (DECISIONS #304). Workspace BAA: **NOT ACCEPTED** ([baa-google-workspace.md](../compliance/baa-google-workspace.md)). Tested locally with Mailpit (passed); the real Gmail test with fake data is pending (§11). |
| Evidence | [sources/README.md](../compliance/sources/README.md), IDs E1–E15. All checked 2026-11-26. |
| Templates | [admin-email/templates/](admin-email/templates/), checked by `scripts/email/check_templates.py` |
| Clinic answers | P0-01 decision log: Q4b `frontdesk@example.com` (one mailbox, all hours), Q7 clinic uses Workspace with its BAA, B7 link only |

## 1. Why email, and what's at stake
- There is no live transfer (plan §4.9). Every unresolved conversation, URGENT emergency and failed booking becomes a callback case, and an email tells the clinic admin.
- **KPI:** 100% of callback emails delivered (plan §11).
- Email is also the easiest place to leak PHI: wrong recipient, unencrypted hop, copies in Sent folders. So the default email carries **no PHI**.

## 2. Route and sender
| Item | Value | Source |
|---|---|---|
| Route | Gmail, from our company Google Workspace. One vendor, already in the Google BAA. | E2, DECISIONS #40 |
| Why not SendGrid | Twilio's HIPAA eligible list has no email product | P2 |
| BAA | Workspace HIPAA BAA, accepted by a super administrator (Account settings > Legal and compliance). Without it, "must not use PHI". | E1 |
| Sender | `callbacks@<company domain>`, the only address the backend may send as | DECISIONS #40 |
| Sender OU | `system-senders`: 2-Step Verification enforced; POP/IMAP off; automatic forwarding off; no third-party apps or add-ons; auto-reply "This mailbox is not monitored." Nobody signs in interactively. | Proposed |
| Fallback | If our future Workspace edition can't accept the BAA: upgrade the edition (sponsor approves), or a HIPAA email provider with a BAA (new DECISIONS row). Until then no PHI in email; cases only in the console. | spec §8 |

## 3. Transport security and domain records (production)
| Item | Setting | Source |
|---|---|---|
| TLS compliance | Admin console > Apps > Google Workspace > Gmail > Compliance > "Secure transport (TLS) compliance" on the `system-senders` OU, listing each clinic's domain. Mail to a listed domain without TLS "aren't delivered, and will bounce" (one attempt, then a non-delivery report). **Never remove the rule to make a clinic work.** | E3 |
| SPF | TXT on the company domain: `v=spf1 include:_spf.google.com ~all` (Verify the include at setup) | Proposed |
| DKIM | Generate the key in Admin console > Apps > Gmail > Authenticate email; publish TXT `google._domainkey.<domain>` | Proposed (Verify at setup) |
| DMARC | TXT `_dmarc.<domain>`: start `v=DMARC1; p=none; rua=mailto:<team address>`; move to `p=quarantine` once reports are clean | Proposed |
| Check | `dig TXT <domain>`, `dig TXT google._domainkey.<domain>`, `dig TXT _dmarc.<domain>`; a test email shows TLS and `dkim=pass` | spec §10 |

## 4. Limits
| Limit | Value | Source |
|---|---|---|
| Per user per day | 2,000 messages (500 on trial accounts) | E4 |
| Gmail API | `messages.send` = 100 units; 6,000 units per minute per user per project, so about 60 sends a minute | E5 |

Far above our volume. P2-23 alerts on quota errors.

## 5. Content modes and templates
| Mode | When | Contents |
|---|---|---|
| **`link_only`** (default) | Always, unless approved otherwise | Urgency, received time, case ID, link. **No patient field.** Template: [link_only.txt](admin-email/templates/link_only.txt) |
| `full_details` | Only with `callback.full_details_approval` (the compliance advisor's written approval) **and** readiness row 5 | Plan §4.9 fields. Template: [full_details.txt](admin-email/templates/full_details.txt) |

- **Subjects** in both modes carry only the urgency and the case ID, never a name or reason.
- **`case_id`** is a random opaque ID (UUID). It's never a PatNum, a phone number or anything derived from patient data (P2-22).
- **Link format:** `{ADMIN_CONSOLE_BASE_URL}/cases/{case_id}`. It requires login, MFA and a role (P1-13, P4-09), so the link alone reveals nothing.
- **Before P4-14 exists**, staging links point to a placeholder page. Only synthetic data exists until the pilot.
- **Check:** `python3 scripts/email/check_templates.py` fails if `link_only` uses any field outside `urgency`, `received_at`, `case_id`, `admin_console_base_url`, or if any subject uses more than urgency and case ID.

## 6. Config keys (Proposed)
**Per clinic, in `clinic_config`** (edited in P4-13):
| Key | Type | Default | Meaning |
|---|---|---|---|
| `callback.admin_emails` | list of email | required | Clinic-controlled mailboxes |
| `callback.after_hours_emails` | list of email | same as `admin_emails` | Used outside clinic hours |
| `callback.email_mode` | `link_only` \| `full_details` | `link_only` | Content mode |
| `callback.full_details_approval` | string or null | null | Reference to the advisor's written approval |

**Environment** (P2-23):
| Key | Example | Meaning |
|---|---|---|
| `ADMIN_EMAIL_SENDER` | `callbacks@example.com` | The only mailbox the backend may send as |
| `ADMIN_EMAIL_SA` | `admin-email-sender@<project>.iam.gserviceaccount.com` | Service account for delegation (§7) |
| `ADMIN_CONSOLE_BASE_URL` | `https://admin.example.com` | Base for case links |

**Load-time rules** (P1-19 / P2-23):
- `full_details` without `full_details_approval` → treated as `link_only`, with a warning logged (no PHI).
- Every address must be on a domain that passed the readiness check (§9).
- Consumer webmail addresses (`gmail.com`, `yahoo.com`, `outlook.com`, `hotmail.com`, `icloud.com`, `aol.com`, …) are refused.

## 7. Backend authentication (verified design)
**Documented method:** domain-wide delegation (DWD).
1. A dedicated service account `admin-email-sender`, in a project used only for this (E8 best practice).
2. A super administrator authorizes its numeric client ID with **one scope**, `https://www.googleapis.com/auth/gmail.send` ("Send email on your behalf", E6). This is done in Admin console > Security > Access and data control > API controls > Manage Domain Wide Delegation (E7).
3. The backend builds a JWT assertion with `iss` = the service account, `sub` = `callbacks@<domain>`, `scope` = `gmail.send`, and `aud` = the OAuth token endpoint.
4. It gets the JWT **signed through the IAM Credentials `signJwt` API** (E9, E10), with no key file. Google's DWD best-practices page says: "Using service account keys is not necessary to perform domain-wide delegation. Use the signJwt API instead." (E8)
5. It exchanges the signed JWT for an access token and calls `users.messages.send` for `callbacks@` only.

**Hardening:**
- Only `callbacks@` is ever used as `sub`.
- Only the backend's runtime identity gets `iam.serviceAccounts.signJwt` on this service account.
- Key creation and upload are blocked for it (E8; P0-06 org policy once an organization exists).

**Depends on hosting (DECISIONS #302):**
| Backend runs on | How it calls `signJwt` without a key |
|---|---|
| Google Cloud (Cloud Run) | Its attached service account (no secret at all) |
| Another cloud or on-premises | Workload Identity Federation (E12): an external identity impersonates the service account. **Verify at that time** that a federated token can call `signJwt` for this account. Otherwise a new decision is needed. |
| Local development | No real sending. Mailpit (§11), or a personal Gmail with fake data for one-off tests |

**Alternative if DWD can't be used:** Workspace **SMTP relay** (`smtp-relay.gmail.com:587` with TLS; IP allow-list and/or SMTP AUTH, E11). It needs no Gmail API scope, but needs either a fixed egress IP or a stored SMTP credential. Second choice.

**APIs needed in the sending project:** `gmail.googleapis.com` and `iamcredentials.googleapis.com` (for P0-06 / P1-05). Whether `gcp.restrictServiceUsage` / VPC-SC affect the Gmail API: Verify when an organization exists.

## 8. Logging and audit
- **Log only:** case ID, Gmail message ID, status, timestamp, error code.
- **Never log** bodies, subjects with data, or recipient-specific patient data (P2-23, P1-11).
- Every send attempt and result is audited per case (P2-23 with P1-12).

## 9. Recipient readiness (per clinic, before any real case)
| # | Check | Pass when |
|---|---|---|
| 1 | Clinic-controlled address | On the clinic's own domain (not webmail); the SME confirms who reads it |
| 2 | Mail server supports TLS | `dig MX <domain>` has a real MX, and it accepts STARTTLS (`openssl s_client -starttls smtp -connect <mx>:25`, or an online TLS checker if port 25 is blocked) |
| 3 | TLS rule added | The domain is in the `system-senders` TLS compliance rule |
| 4 | Test email arrives | A synthetic `link_only` email arrives, not in spam; headers show TLS |
| 5 | Clinic mailbox is HIPAA-appropriate | The SME confirms the clinic's own email provider is covered by its own arrangements. Only needed for `full_details`. |

How to run it: [runbooks/admin-email-add-clinic.md](../runbooks/admin-email-add-clinic.md). Our clinic's result: [email-readiness-example-dental.md](../compliance/email-readiness-example-dental.md).

## 10. Retention (only if `full_details` is ever approved)
- The sender's Sent folder would hold PHI.
- **Proposed:** a retention rule deletes Sent items after 30 days.
- **Verify** that Vault or retention rules are available in the edition we buy. Compliance advisor to confirm the period.

## 11. Tests run
| Test | Result |
|---|---|
| Template check (`check_templates.py`) | Pass on the real templates; fails on a broken copy (patient name added) |
| Local SMTP test with Mailpit | See §11.1 |
| Real delivery from a personal Gmail, fake data | **Pending** (deferred by the user), §11.2 |

### 11.1 Local (Mailpit)
**Passed 2026-11-26.**
- Setup: Mailpit v1.34.0 (`axllent/mailpit`, pinned by digest in `scripts/email/docker-compose.mailpit.yml`), bound to `127.0.0.1` only.
- `python3 scripts/email/send_test_callback_email.py` rendered `link_only` with a random case ID and sent it by SMTP. It read the message back through Mailpit's API, and all checks passed:
  - message found;
  - stored subject matches;
  - the case link is present;
  - no patient field;
  - plain text only (no HTML part).
- Mailpit was stopped and the container removed afterwards.
- **To view the email yourself:** start Mailpit, run the script, and open http://127.0.0.1:8025.

### 11.2 Real delivery (personal Gmail)
**Pending: deferred by the user (2026-11-26).**
- **Why it's waiting:** a Google app password needs 2-Step Verification, which isn't turned on (E13).
- **Two ways to run it later:**
  1. Turn on 2-Step Verification, create an app password, and run `send_test_callback_email.py --smtp gmail` with `SMTP_USER`, `SMTP_APP_PASSWORD` and `TEST_TO` set in your own terminal.
  2. Without 2-Step Verification: paste the rendered `link_only` subject and text into Gmail web and send it to a team mailbox.
- **Either way:** check "Show original" for TLS and `dkim=pass`.
- **Already proven:** our script sends correctly by SMTP (§11.1).

## 12. Pending before go-live
- [ ] (Can be done any time) Real delivery test from a personal Gmail with fake data (§11.2).
- [ ] Buy the company domain and a Google Workspace edition that can accept the BAA (Verify the edition at purchase; E1 lists none).
- [ ] Accept the Workspace HIPAA BAA ([baa-google-workspace.md](../compliance/baa-google-workspace.md)).
- [ ] Create `callbacks@` in OU `system-senders` with the §2 lock-down.
- [ ] Publish SPF, DKIM and DMARC; check with `dig`.
- [ ] Add each clinic's domain to the TLS compliance rule.
- [ ] Set up DWD with `gmail.send` only, keyless (§7), in dev first (P2-23).
- [ ] A real test from `callbacks@` shows TLS and `dkim=pass` for our domain; a non-TLS domain bounces (if one is available).
- [ ] Run the readiness check with the clinic's **real** domain (the current address is a placeholder).
