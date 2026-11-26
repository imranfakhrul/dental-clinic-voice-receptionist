# Proposal: P0-08 Decide the admin email route (issue #9)

## Why

There is no live transfer to a human (plan §4.9). Every unresolved conversation, every URGENT case and every failed booking ends in a callback case plus an email to the clinic admin. P2-23 (the email sender), P4-13 (callback settings) and P4-14 (cases list) need these defined first:
- the route;
- the sender;
- the content mode and templates;
- the config keys;
- the backend authentication;
- the per-clinic readiness check.

Plan route (DECISIONS #40): Gmail API from our company Google Workspace, under the Workspace HIPAA BAA.

Our situation: we have **no company domain or Workspace yet**, and hosting is **local-first** (DECISIONS #302). So the route is designed in full now, and the setup that needs a domain is recorded as pending before go-live.

## What Changes

- **Route and design `docs/integrations/admin-email.md`:**
  - Gmail from our company Workspace; sender `callbacks@<company domain>` in OU `system-senders`, locked down;
  - the TLS compliance rule, and SPF/DKIM/DMARC;
  - sending limits;
  - the **keyless backend authentication design**, verified against Google's docs during apply;
  - Sent-folder retention for `full_details`;
  - logging rules.
- **Content mode:** `link_only` is the default (case ID + link, no PHI), as the clinic agreed in P0-01 B7. `full_details` only per clinic, with written advisor approval.
- **Templates:** `link_only` and `full_details` stored as text files in `docs/integrations/admin-email/templates/`, for P2-23 to reuse.
- **Config keys and load-time rules** for `clinic_config` and the environment.
- **Workspace BAA record `docs/compliance/baa-google-workspace.md`:** paper, **NOT ACCEPTED**, with the acceptance steps and the edition check.
- **Runbook `docs/runbooks/admin-email-add-clinic.md`:** readiness check, TLS rule, config.
- **Readiness record `docs/compliance/email-readiness-<clinic>.md`** for our clinic, run as far as a placeholder address allows.
- **Local test:**
  - Mailpit (a local mail catcher in Docker, nothing leaves the computer);
  - `scripts/email/send_test_callback_email.py` renders the `link_only` template with synthetic values, sends it to Mailpit, reads it back, and checks that no patient field appears;
  - `scripts/email/check_templates.py` checks both templates against the field rules.
- **Real delivery test (user decision 2026-11-26):** the same script with `--smtp gmail` sends one synthetic plain-text `link_only` email from the user's personal Gmail (SMTP with an app password, held only in the shell) to a team mailbox. The received headers are checked for TLS and `dkim=pass` (for gmail.com, not our future domain).
- **Records:** DECISIONS rows, pending notifications (P2-23, P2-22, P4-13, P4-14, P0-06, P1-05, P0-10), and links from the READMEs and `docs/PROJECT_MAP.md`.
- **No product code. No PHI. No cloud or Workspace changes.**

## Capabilities

### New Capabilities
- `admin-callback-email`: how callback cases reach the clinic admin by email. Covers the route and sender, content modes and templates, the config keys and their load-time rules, the recipient readiness check, the keyless authentication design, and the logging limits.

### Modified Capabilities
- None.

## Impact

- **New files:**
  - `docs/integrations/admin-email.md`
  - `docs/integrations/admin-email/templates/link_only.txt`, `full_details.txt`
  - `docs/compliance/baa-google-workspace.md`
  - `docs/runbooks/admin-email-add-clinic.md`
  - `docs/compliance/email-readiness-<clinic>.md`
  - `scripts/email/send_test_callback_email.py`, `scripts/email/check_templates.py`
  - `scripts/email/docker-compose.mailpit.yml`
- **Edited files:**
  - `dental-ai-tasks/DECISIONS.md`
  - `docs/compliance/README.md`
  - `docs/compliance/sources/README.md`
  - `docs/phase-0-discovery-compliance/README.md`
  - `docs/PROJECT_MAP.md`
- **Downstream:**
  - P2-23 builds the sender from the templates, keys and auth design.
  - P2-22 keeps case IDs random.
  - P4-13 and P4-14 use the keys and the link format.
  - P0-10 imports the BAA record.
