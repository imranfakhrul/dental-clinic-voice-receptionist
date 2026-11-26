# Patient messaging: templates and sender registration

Created by P0-15 (issue #16). The rules come from [messaging_policy.yaml](../compliance/messaging_policy.yaml) (P0-07a); the providers from [messaging-provider.md](../integrations/messaging-provider.md) (P0-07).

| File | What it's for |
|---|---|
| [templates.yaml](templates.yaml) | **The only source of message text.** 4 SMS + 4 WhatsApp templates (confirmation, reminder, reschedule, cancel), keyword replies, date and time formats. P4 code renders these and never builds text itself |
| [templates.schema.json](templates.schema.json) | JSON Schema for `templates.yaml` |
| [opt-in-and-help-texts.md](opt-in-and-help-texts.md) | Consent checkbox text (P4-02), STOP/START/HELP handling, the clinic's SMS terms page and privacy paragraph |
| [registration-example-dental.md](registration-example-dental.md) | Sender registration record per clinic: IDs and statuses only, never secrets |

## Scripts (`scripts/messaging/`)
| Script | Network | What it does |
|---|---|---|
| `check_templates.py` | No | Rules T1–T11: schema, policy version, variables only from the policy, never-allowed fields, denylisted words, GSM-7 length, opt-out text, WhatsApp rules, PHI-free replies. Exit 1 on any error |
| `submit_whatsapp_templates.py` | Only with `--submit` | Creates the `DRAFT`/`REJECTED` WhatsApp templates on the team's WhatsApp Business Account. Dry run by default; refuses if `check_templates.py` fails |
| `send_test_message.py --template <id>` | Yes | Sends one **APPROVED** WhatsApp template with its own example values to `WA_TEST_TO` (team phone) |
| `test_check_templates.py`, `test_live_scripts.py` | No | 33 offline tests (fake HTTP layer) |

```bash
python3 scripts/messaging/check_templates.py
pytest -q scripts/messaging/
set -a; . ./.env; set +a          # WA_TOKEN, WA_WABA_ID, WA_PHONE_NUMBER_ID, WA_TEST_TO (never committed)
python3 scripts/messaging/submit_whatsapp_templates.py            # dry run
python3 scripts/messaging/submit_whatsapp_templates.py --submit   # only when agreed; then set provider_status: SUBMITTED
```

## Changing a template
1. Never edit an approved template in place: add `<type>_<channel>_v<N+1>` and keep the old one until P4 stops using it.
2. Use only the fields the policy lists for that message type; no service, reason, symptom, payment or provider words.
3. Run `check_templates.py` and the tests; the compliance advisor reviews the wording.
4. WhatsApp: submit the new version (Meta review up to 24 hours). SMS: if the wording changes materially, update the campaign samples with the provider.
5. Update the registration record and its change log.

If `messaging_policy.yaml` changes its `decision_version`, the check fails until `policy_version` here is updated after a review.

## Status (2026-11-26)
- WhatsApp templates: **DRAFT**, not yet submitted (waits for the user's go-ahead and `WA_WABA_ID`).
- SMS: brand and campaign **drafts only** (no Twilio account; clinic business details are placeholders).
- No real patient data anywhere; examples are fictional (Example Dental, 555-01xx numbers).
