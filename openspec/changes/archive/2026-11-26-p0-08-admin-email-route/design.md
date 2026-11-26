# Design: P0-08 Admin email route

## Context

- See proposal.md, Why.
- **Decided earlier:**
  - **DECISIONS #40:** Gmail API from our company Google Workspace under the Workspace HIPAA BAA, with a dedicated sender `callbacks@<company domain>`.
  - **DECISIONS #302:** local-first; no cloud resources.
  - **BAAs stay on paper** (#293 approach), recorded NOT ACCEPTED.
- **Clinic answers (P0-01 decision log, 2026-11-25):**
  - **Q4b:** one shared mailbox for all hours, `frontdesk@example.com`.
  - **Q7:** the clinic uses Google Workspace with its BAA accepted.
  - **B7:** case ID + link only.

  `example.com` is a reserved placeholder domain, so recipient checks that need a real mail server can't pass on it.
- **We have no company domain or Workspace.** User decisions for this task (2026-11-26):
  - The domain and Workspace are **bought for production**, not now.
  - Now: design on paper, test locally with Mailpit, and send real email from the personal Gmail with **fake data only**.
  - Workspace, DNS and the TLS rule are pending before go-live.
- **People:** Riley Tech (tech lead), Sam Comply (advisor), Morgan Lead (sponsor), Alex Sample (clinic SME).
- **Local tools available:** Docker, `dig`, `openssl`.

## Goals / Non-Goals

**Goals:**
- A complete, verified design that P2-23 can build without re-deciding anything.
- Templates as files, with an automatic check that `link_only` holds no patient field.
- A local end-to-end test of rendering and SMTP delivery with synthetic data.
- An honest record of what's pending: Workspace, BAA, DNS, the TLS rule, real-clinic readiness.

**Non-Goals:**
- Buying a domain or Workspace, accepting any BAA, or creating `callbacks@`.
- Writing the sender (P2-23), case creation (P2-22) or the case page (P4-14).
- Sending any email to the internet except the one synthetic test to a team mailbox (decision 4a).

## Decisions

1. **Route stays Gmail from our company Workspace** (DECISIONS #40), with the fewest vendors.
   - SendGrid stays excluded: Twilio's eligible list has no email product (P2).
   - Fallback, if our future Workspace edition can't take the BAA: upgrade, or a HIPAA email provider with a BAA (spec §8).
2. **Content mode:** `link_only` by default, as the clinic agreed (B7). `full_details` needs `callback.full_details_approval` plus readiness check #5.
3. **Templates as plain-text files** in `docs/integrations/admin-email/templates/`, with `{placeholder}` fields. P2-23 loads them, so there's one source of truth.
   - `scripts/email/check_templates.py` fails if `link_only` (subject or body) uses any field outside an allow-list: `urgency`, `received_at`, `case_id`, `admin_console_base_url`.
   - It also fails if any subject uses a patient field.
4. **Local test with Mailpit:**
   - `scripts/email/docker-compose.mailpit.yml` runs the official `axllent/mailpit` image, bound to `127.0.0.1` only (SMTP 1025, web 8025).
   - `send_test_callback_email.py` (standard library) renders `link_only` with synthetic values (a random UUID case ID), sends it via SMTP to Mailpit, reads it back through Mailpit's local API, and checks the subject format and that no patient field appears.
   - **Why Mailpit:** it's local, open source, and nothing leaves the machine, which fits #302. It also serves P2-23's local development later.
   - **Not tested locally:** TLS to a real server, DKIM and DMARC.
4a. **Real delivery test from personal Gmail (user decision):**
   - The same script with `--smtp gmail` sends one synthetic plain-text `link_only` email.
     - **From:** the user's personal Gmail, through `smtp.gmail.com:587` with STARTTLS, logged in with a Google **app password** (needs 2-Step Verification; Verify that app passwords are still offered).
     - **To:** one team mailbox only.
     - **Credentials:** `SMTP_USER`, `SMTP_APP_PASSWORD` and `TEST_TO` come from env vars and are never printed or committed.
   - **Proves:** real delivery, TLS in transit, and `dkim=pass` for gmail.com, with the user reading the received headers ("Show original").
   - **Doesn't prove:** our own domain's SPF/DKIM/DMARC, the Workspace TLS rule, or the `callbacks@` sender. Those stay pending until a domain exists.
   - **Why it's allowed:** synthetic content only, to a team mailbox. A personal Gmail has no BAA, so real data never goes this way.
5. **Keyless auth design, verified during apply:**
   - A dedicated service account with domain-wide delegation, limited to `https://www.googleapis.com/auth/gmail.send`, impersonating only `callbacks@`.
   - Delegation tokens are signed through the IAM Credentials API (`signJwt`), with no key file.
   - Google's docs are checked for: the documented way to send as a Workspace user from a backend; keyless delegation with `signJwt`; alternatives (SMTP relay, OAuth for a dedicated user).
   - The verified answer is recorded with sources. Under #302 the runtime host is undecided, so the design also notes what changes if the backend isn't on Google Cloud: delegation then needs workload identity federation or a stored key, which needs a new decision.
6. **Readiness check for our clinic:**
   - Run row by row on `frontdesk@example.com`. Row 1 is confirmed by the SME (role-played).
   - Row 2 (`dig MX` and STARTTLS) is run for real and will show the placeholder has no mail server.
   - Rows 3–4 are pending (no TLS rule or Workspace). Row 5 is not applicable (`link_only`).
   - The result is "not ready: replace the placeholder with the clinic's real domain at onboarding". The runbook says how.
7. **The Workspace BAA record** follows the P0-05 format: status NOT ACCEPTED, the acceptance path (spec §3), and the edition question. Google's current page is re-checked during apply to see whether it lists qualifying editions.
8. **Retention for `full_details`:** Proposed, delete Sent items after 30 days. Vault/retention availability depends on the future edition (Verify at purchase); recorded as pending.

## Risks / Trade-offs

- **The real test uses gmail.com, not our domain** → delivery and TLS are proven, but our own SPF/DKIM/DMARC and spam placement under our domain stay unproven until a domain exists. They're listed as go-live gates.
- **The auth design depends on hosting** (#302) → the design records both cases and flags a decision if the backend runs outside Google Cloud.
- **Placeholder clinic address** → the readiness check can't pass; it's recorded honestly.
- **Mailpit is a third-party image** → it runs locally on `127.0.0.1`, carries synthetic data only, and isn't a vendor (no data leaves). It's recorded as a dev tool.
