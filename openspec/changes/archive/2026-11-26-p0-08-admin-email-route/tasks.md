# Tasks: P0-08 Admin email route (issue #9)

## 1. Verify the facts (read-only)

- [x] 1.1 Re-check Google's pages: Workspace HIPAA BAA acceptance (which editions qualify), Gmail on the covered-services list, TLS compliance setting, Gmail sending limits and API quota, and the documented keyless way for a backend to send as a Workspace user (domain-wide delegation with `signJwt`, SMTP relay, alternatives). Add source rows to `docs/compliance/sources/README.md` (URL, date, quote, SHA-256 or "n/a"). Verify: every fact used has a row.

## 2. Design and records

- [x] 2.1 Write `docs/integrations/admin-email/templates/link_only.txt` and `full_details.txt` (spec §6) and `scripts/email/check_templates.py` (allow-list for `link_only`, no patient fields in any subject). Run it on the real templates and on a broken copy. Verify: passes on the real ones, fails on the broken one.
- [x] 2.2 Write `docs/integrations/admin-email.md`: route and sender, OU lock-down, TLS rule, SPF/DKIM/DMARC records, limits, content modes, config keys and load-time rules, the verified auth design (including what changes if the backend isn't on Google Cloud), retention for `full_details`, logging rules, and a "pending before go-live" list. Verify: every spec §6 item is present with a source or a Proposed/Verify marker.
- [x] 2.3 Write `docs/compliance/baa-google-workspace.md` in the P0-05 format, status **NOT ACCEPTED**, with the acceptance path and the edition check. (Role: compliance advisor Sam Comply) Add a review line. Verify: every field present.
- [x] 2.4 Write `docs/runbooks/admin-email-add-clinic.md` (readiness check, TLS rule, config, test email).

## 3. Local test and readiness

- [x] 3.1 Write `scripts/email/docker-compose.mailpit.yml` (bound to 127.0.0.1) and `scripts/email/send_test_callback_email.py` (standard library; synthetic values; sends to Mailpit and reads it back through Mailpit's local API; checks the subject format and that no patient field appears). Start Mailpit, run the test, stop Mailpit. Verify: the script passes and the message is visible in Mailpit.
- [x] 3.2 (human) Real delivery test from the personal Gmail. **Deferred by the user (2026-11-26)** to a later date: an app password needs 2-Step Verification, which isn't on. Recorded as pending in `admin-email.md` §11.2 and §12, with two ways to run it later: the script with `--smtp gmail` (needs 2-Step Verification and an app password), or pasting the rendered email into Gmail web. SMTP sending by our script is already proven locally (task 3.1).
- [x] 3.3 (role: clinic SME Alex Sample for row 1) Run the readiness check on `frontdesk@example.com` (`dig MX`, a STARTTLS attempt where an MX exists) and write `docs/compliance/email-readiness-example-dental.md` with the honest result. Verify: each of the 5 rows has a result.

## 4. Records

- [x] 4.1 Append DECISIONS rows (next number 303): `link_only` as the default content mode with the config keys and load-time rules; and the deviations (no domain or Workspace, BAA on paper, local Mailpit test plus one real synthetic test from a personal Gmail instead of a test from our own domain, readiness pending until the clinic's real domain, auth design dependent on hosting). Verify: the rows are present.
- [x] 4.2 Update `docs/compliance/README.md` (file table; pending before real PHI: Workspace BAA, domain, DNS, TLS rule; pending notifications for P2-23, P2-22, P4-13, P4-14, P0-06, P1-05, P0-10), the Phase 0 README #9 status, and `docs/PROJECT_MAP.md` (new and changed files). Run the public-repo scan and the link check. Verify: the scan is clean and there are no broken links.

## 5. Finish (only after the user's review)

- [x] 5.1 After the user has reviewed the work and given the go-ahead: archive the change (sync the `admin-callback-email` spec), commit with a one-line descriptive message, push `feature/phase-0-discovery-compliance`, comment the hand-off on issue #11 (P0-10), and close issue #9 with a comment listing the files. Do none of these before the user says so. Verify: one commit, the branch matches origin, and #9 is closed under #17.
