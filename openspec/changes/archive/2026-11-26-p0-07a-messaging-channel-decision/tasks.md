# Tasks: P0-07a Patient messaging channel decision (issue #7)

## 1. Re-check the facts (read-only)

- [x] 1.1 Fetch and quote the Meta sources: Terms for WhatsApp Business Platform §4.2, WhatsApp Business Messaging Policy §3, Meta Hosting Terms for Cloud API §1.1/§2.2, and the WhatsApp template-category page (is an appointment reminder a "utility" template?). Record URL, date, the quote and SHA-256 per page; mark any page that can't be fetched "not re-checked". Verify: each source has an entry in the scratch notes.
- [x] 1.2 Check the published HIPAA/BAA pages of the SMS providers (Twilio, Vonage, Sinch, Infobip, Bird) and the WhatsApp providers (Twilio, 360dialog, Infobip, Sinch): exactly which products their BAA covers, and under what conditions. Note US SMS registration (10DLC or toll-free verification) and TCPA pointers for the advisor. Verify: at least 3 providers per channel have a recorded position.

## 2. The memo and the policy

- [x] 2.1 Write `docs/compliance/sources/README.md`: one row per source (URL, date, quote, SHA-256), with the note that full copies are kept outside the public repo. Verify: every fact in the memo has a row.
- [x] 2.2 Write `docs/compliance/patient-messaging-decision.md` sections 1–5: the question, the facts, the message-type table, the options A–D comparison, and the 5 advisor questions. Verify: about 3 pages; every fact has a source.
- [x] 2.3 (role: compliance advisor Sam Comply) Write the advisor's written answers to all 5 questions, following the facts. (Role: sponsor Morgan Lead) Approve the decision per message type and any scope change. Write memo section 6 with the decision, content rules, consent, conditions, signatures and date. Verify: every question has an answer, and the decision names one option per message type.
- [x] 2.4 (role: clinic SME Alex Sample) Inform the clinic with a two-line summary and record the reply and the date in memo section 6. Add a Q8 revision row to `docs/discovery/clinic-decision-log.md`. Verify: the date is recorded in both places.
- [x] 2.5 Write `docs/compliance/messaging_policy.yaml` to match the decision exactly, and `scripts/compliance/check_messaging_policy.py` (the spec §10 checks; exits non-zero on failure). Run it. Also run it once on a deliberately broken copy, to show it catches the error. Verify: it passes on the real file and fails on the broken copy.

## 3. Records

- [x] 3.1 Append the DECISIONS row (next number 297): the decision per message type, and the sponsor's acceptance of any scope change against plan §2 #9–10 / §4.7, naming the tasks to re-scope (P0-15 and the P4 messaging tasks). Verify: the row is present.
- [x] 3.2 Update `docs/compliance/README.md` (file table, and pending notifications for P0-07, P0-15, P4-01/02/03/07/08, P0-09, P0-10), the Phase 0 README #7 status, and `docs/PROJECT_MAP.md`. Run the public-repo scan and the link check. Verify: the scan is clean and there are no broken links.

## 4. Finish (only after the user's review)

- [x] 4.1 After the user has reviewed the work and given the go-ahead: archive the change (sync the `patient-messaging-policy` spec), commit with a one-line descriptive message, push `feature/phase-0-discovery-compliance`, comment the decision on issues #8 (P0-07) and #16 (P0-15), and close issue #7 with a comment listing the files. Do none of these before the user says so. Verify: one commit, the branch matches origin, and #7 is closed under #17.
