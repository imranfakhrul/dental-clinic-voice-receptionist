# Tasks: P0-07 Select the patient-messaging providers (issue #8)

## 1. Evidence and comparison

- [x] 1.1 Read `messaging_policy.yaml` v1.2 and the P0-07a memo; list the channels and conditions at the top of `docs/integrations/messaging-provider.md`. Verify: testing = WhatsApp, production = per clinic (SMS / WhatsApp behind the `phi_gate`).
- [x] 1.2 Check the providers' own docs for criteria 2–9 (edition and price, US sender options and lead time, webhook signing, STOP handling, body retention, API/SDK/sandbox, status page and US processing, US price per message): WhatsApp = Meta Cloud API, Twilio, Vonage, Infobip, 360dialog; SMS = Twilio, Vonage, Sinch, Infobip. Add each new source to `docs/compliance/sources/README.md` (URL, date, quote, SHA-256 or "n/a"). Verify: every fact used has a source row.
- [x] 1.3 Write the comparison tables (one per channel; WhatsApp criterion 1 in two columns, testing and production), with yes / no / partial and an evidence link per cell, and the failed Must for each excluded provider. Verify: no empty cell.
- [x] 1.4 (role: tech lead Riley Tech; sponsor Morgan Lead for the price) Record the choice and reasons: WhatsApp = Meta Cloud API direct; SMS = the top scorer (Proposed: Twilio). Verify: the chosen providers meet every Must for their use.

## 2. BAA records (paper)

- [x] 2.1 Write `docs/compliance/baa-meta-whatsapp.md` and `docs/compliance/baa-<sms vendor>.md` in the P0-05 format plus covered products relied on, edition or plan, and channels allowed (policy decision version 1.2). Status **NOT ACCEPTED**. Each includes the short written BAA request to send later. Verify: both files have every field; Meta's request asks for explicit coverage of WhatsApp message content.
- [x] 2.2 (role: compliance advisor Sam Comply) Review that each record names the exact product and that no PHI may flow while it says NOT ACCEPTED. Record the review line in each file. Verify: the review line is present.

## 3. WhatsApp test account and proof

- [x] 3.1 Write `scripts/messaging/send_test_message.py` and `scripts/messaging/webhook_probe.py` (standard library; secrets and numbers from env vars; output never shows the token, the phone number or message text). Test the signature check locally with a self-made payload: right secret → pass, wrong secret → fail. Verify: both results shown.
- [x] 3.2 (human) Get WhatsApp test credentials. Done: the senior provided the access token and phone number ID of the team's existing Meta app with a WhatsApp **test number** (no new account was needed), and added the user's phone to the test number's recipient list after error 131030. Credentials stay in the user's password manager; nothing in the repo.
- [x] 3.3 (human) Send one test message to a team phone. Done 2026-11-26: `send_test_message.py` returned HTTP 200 (accepted) and the `hello_world` template arrived on the user's phone. **Webhook test deferred by the user's decision** to P4-06 (it needs the app secret, a change to the Meta app's webhook settings and a tunnel); the signature check is proven only locally by `webhook_probe.py --self-test`.
- [x] 3.4 Write the "Integration facts" section (both providers; WhatsApp marked proven by 3.3, SMS marked documented, not tested) and the sender-registration steps and lead times for P0-15 (WhatsApp test number now; production number, business verification, display name and templates later; SMS 10DLC or toll-free verification before go-live). List the secret names for P1-05 (names only). Verify: every row has a doc link.

## 4. Records

- [x] 4.1 Append DECISIONS rows (next number 300): the providers chosen; and the deviations from the spec (BAAs on paper and requests not yet sent, SMS test account deferred until SMS is switched on, temporary tunnel used for the webhook test). Verify: the rows are present.
- [x] 4.2 Update `docs/compliance/README.md` (file table; pending notifications for P0-10, P0-15, P4-01, P4-06, P4-07, P1-05; "pending before real PHI": messaging BAAs), the Phase 0 README #8 status, and `docs/PROJECT_MAP.md`. Run the public-repo scan (personal email, phone numbers, tokens) and the link check. Verify: the scan is clean and there are no broken links.

## 5. Finish (only after the user's review)

- [x] 5.1 After the user has reviewed the work and given the go-ahead: archive the change (sync the `messaging-provider` spec), commit with a one-line descriptive message, push `feature/phase-0-discovery-compliance`, comment the hand-off on issues #11 (P0-10) and #16 (P0-15), and close issue #8 with a comment listing the files. Do none of these before the user says so. Verify: one commit, the branch matches origin, and #8 is closed under #17.
