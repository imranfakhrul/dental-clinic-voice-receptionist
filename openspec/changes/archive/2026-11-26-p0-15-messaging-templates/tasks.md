# Tasks: P0-15 Patient-messaging sender and message templates (issue #16)

## 1. Facts (read-only)

- [x] 1.1 Read Twilio's pages (A2P 10DLC overview, business info fields, direct standard onboarding review times, use cases, pricing if published, toll-free verification, advanced opt-out and error 21610) and Meta's pages (template categories and review, template creation API and parameter rules, body limit). Record M-rows in `docs/compliance/sources/README.md`. Verify: each spec "Verify" item has an answer or an open question.

## 2. Templates and validator

- [x] 2.1 Write `docs/messaging/templates.schema.json` and `docs/messaging/templates.yaml`: 4 SMS + 4 WhatsApp templates, `system_replies`, date and time formats, `policy_version: "1.2"`. Synthetic examples only (Example Dental, `555-01xx`). Verify: YAML loads; every example renders.
- [x] 2.2 Write `scripts/messaging/check_templates.py` (T1–T11) and `scripts/messaging/test_check_templates.py` (baseline: in-memory copies of the real templates and policy, so no fixture files drift) covering the spec §10 cases plus missing type, missing opt-out text and a system reply with `{first_name}`. Verify: tests pass offline; the real file passes with no errors.

## 3. Texts and registration record

- [x] 3.1 Write `docs/messaging/opt-in-and-help-texts.md`: consent checkbox text (risk-notice slot), HELP, STOP and START texts, SMS terms page text and privacy paragraph. Compliance advisor review recorded (mock). Verify: texts match `system_replies` and the policy.
- [x] 3.2 Write `docs/messaging/registration-example-dental.md`: WhatsApp (test number in use, templates DRAFT), SMS 10DLC brand and campaign drafts with placeholders, status table "not submitted" with blockers and owners. Verify: no secrets, no EIN, no phone number beyond `555-01xx`.

## 4. Live-step scripts (prepared, not run)

- [x] 4.1 Write `scripts/messaging/submit_whatsapp_templates.py` (dry run by default; `--submit` needs `WA_TOKEN` and `WA_WABA_ID`; prints name, ID, status only) and add `--template <id>` to `send_test_message.py` (APPROVED templates, example values, `WA_TEST_TO` only). Tests with a fake HTTP layer. Add `WA_WABA_ID` to `.env.example`. Verify: tests pass; no network call in tests; no live run.

## 5. Records

- [x] 5.1 Write `docs/messaging/README.md`. Add DECISIONS rows from #322 (template set and rules, deviations); hand-off rows in `docs/compliance/README.md` for P4-01, P4-02, P4-03, P4-04, P0-10, P0-14; update `docs/PROJECT_MAP.md` and `docs/phase-0-discovery-compliance/README.md`. Verify: `check_phi_flows.py` and `check_messaging_policy.py` pass; merged-ID and link checks pass; public-repo scan clean; `openspec validate --strict` passes.

## 6. Finish (after the user's review)

- [x] 6.1 After the user has reviewed the work and said so: archive the change (sync the main spec), commit with a one-line descriptive message, push `feature/phase-0-discovery-compliance`, comment hand-offs, and close sub-issue #16 with the file list. Never close parent issue #17. Do none of this before the user says so.
