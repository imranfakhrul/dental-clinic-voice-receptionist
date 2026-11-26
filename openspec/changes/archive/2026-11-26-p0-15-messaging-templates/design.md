# Design: P0-15 Patient-messaging sender and message templates

## Context

The P0-15 spec was written when SMS was the default and WhatsApp conditional. Since then:

| Spec says | Now true | Source |
|---|---|---|
| SMS first; WhatsApp only if P0-07a allows | WhatsApp is the testing channel now; each clinic picks SMS or WhatsApp at go-live; WhatsApp real data only after BAAs | `messaging_policy.yaml` v1.2, DECISIONS #299 |
| Policy has `channels.*.allowed` and a channel per type | Policy v1.2 has `integrated`, `enabled`, `allowed_with_phi` per channel and `environments.testing.active_channel`; message types list fields only | `messaging_policy.yaml` |
| T9: at least one template per type carries STOP/HELP | `opt_out_text_required: true`: **every** message carries opt-out text | policy |
| Provider chosen and BAA signed in P0-07 | Meta direct and Twilio chosen; BAAs paper records, NOT ACCEPTED; no Twilio account | DECISIONS #300, #301 |
| `send_test_sms.py` in `<prefix>-dev` with Secret Manager | Local-first: credentials from the shell or git-ignored `.env`; WhatsApp sender script exists (`send_test_message.py`) | DECISIONS #302, P0-07 |
| P4-01 addition: `phi_free_nudge` WhatsApp templates first | Policy v1.2 has no WhatsApp mode: WhatsApp with real data waits for the BAAs, and the clinic uses SMS until then. Testing uses synthetic data, so the normal-field templates are tested on WhatsApp now | DECISIONS #299 |
| Pilot clinic brand data | Example Dental placeholders (legal name, EIN, website unknown) | P0-01, P0-09 |

Mock roles: Riley Tech (tech lead) writes; Sam Comply (compliance advisor) reviews wording; Alex Sample (office manager) supplies the clinic details, which are placeholders.

## Goals / Non-Goals

**Goals:**
- Templates and texts that P4 uses unchanged, checked by code.
- A complete SMS registration package, ready to submit when a Twilio account and real business details exist.
- WhatsApp templates ready to submit to Meta, with a guarded script.

**Non-Goals:**
- Live submission to Meta, live test sends, or any Twilio registration in this apply (user decision; done later on request).
- The sending adapter, webhooks and opt-out sync (P4-01); consent capture (P4-02).

## Decisions

### 1. One template set, two channels
Four types × two channels (`sms`, `whatsapp`) = 8 templates, same fields per type (policy fields). WhatsApp entries add `whatsapp_category: UTILITY`, `provider_template_name`, `language: en_US`, `provider_status: DRAFT`. No `whatsapp_mode` field now: the policy has no mode; the schema leaves room to add it (P4-01) through a schema version bump. Alternative: only WhatsApp templates now. Rejected: SMS is the production fallback for every clinic until the WhatsApp gate, so SMS must be ready first.

### 2. Validator rules adapted to policy v1.2
| Rule | Check |
|---|---|
| T1 | JSON Schema valid |
| T2 | `policy_version` == policy `decision_version` |
| T3 | Body variables == declared variables |
| T4 | Every variable in the type's policy fields |
| T5 | No variable in `never_allowed_fields` |
| T6 | Channel exists in the policy with `integrated: true`; each integrated channel has all four types; the testing `active_channel` has all four |
| T7 | Denylist words absent from the rendered example (whole words, case-insensitive), except inside the clinic name |
| T8 | SMS: GSM-7 only; ≤ 160 ok, 161–306 warning, > 306 error |
| T9 | When `opt_out_text_required`, every template contains the opt-out phrase ("Reply STOP") |
| T10 | WhatsApp: `whatsapp_category: UTILITY`; body doesn't start or end with a variable; body ≤ 1024 |
| T11 | `system_replies` use only `clinic_name` and `clinic_phone` (new; from P4-01 §6.5) |

Output: rule, template ID, message; no example values printed. Standard library, PyYAML and `jsonschema` (already used by `check_vendors.py`).

### 3. Wording fits one SMS segment
Every message starts with the clinic name and carries "Reply STOP to opt out." Examples use "Example Dental" and `(503) 555-0100`. The validator measures the rendered example; long real clinic names may push to two segments (warning). HELP stays in the confirmation only, to keep reminders short; STOP is in every message (policy).

### 4. Facts re-checked on the day
Twilio A2P 10DLC (brand types, fields, use cases, review times, fees if published), toll-free verification, opt-out keywords and error 21610; Meta template categories, review time, variable rules, body limit and the template creation API. Recorded as sources (IDs M1…) using HTML pages. Spec "Verify" items are answered or listed as open questions.

### 5. Live-step scripts, prepared but not run
- `submit_whatsapp_templates.py`: reads `templates.yaml`, builds the Graph API template-creation payload for each `whatsapp` template (named parameters with examples), `--dry-run` default prints names and payload shape (no values beyond examples), `--submit` needs `WA_TOKEN` and `WA_WABA_ID` and asks for nothing interactive; prints name, ID and status only. Tests use a fake HTTP layer.
- `send_test_message.py` gains `--template <id>`: sends an **APPROVED** WhatsApp template with its example values only, to `WA_TEST_TO` only.
Both use the standard library (`urllib`), like the existing script. Credentials come from the environment; `.env.example` gains `WA_WABA_ID` (no value).

### 6. SMS registration as a draft record
`registration-example-dental.md` holds the brand and campaign JSON (Twilio field names), the use case choice (`LOW_VOLUME`, fallback `ACCOUNT_NOTIFICATION`), and a status table: customer profile, brand, campaign, number, Messaging Service = **not submitted** (blocker: no Twilio account, clinic legal name/EIN/website placeholders; owner and trigger). No EIN or real business data in the public repo.

## Risks / Trade-offs

- [Meta classifies a template as marketing or rejects it] → wording is transactional, no promotion; resubmit flow recorded; real review only when the user runs the script.
- [Carrier review rejects the campaign later] → samples equal the real templates; the record lists fallback use case and fixes.
- [Every message with STOP text is longer] → fits one segment with a short clinic name; warning otherwise.
- [Placeholders mistaken for real registration] → record says "not submitted" with blockers on every row.

## Open Questions

- Which A2P use case Twilio recommends for appointment notifications (answered from docs if stated, else open for go-live).
- Fees and who pays (sponsor), recorded from the pricing page if published.
- Who publishes the clinic's SMS terms and privacy text (clinic, at onboarding).
