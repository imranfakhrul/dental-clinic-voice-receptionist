# Runbook: add a clinic to callback email (P0-08)

Use this before any real callback case goes to a new clinic. Design: [admin-email.md](../integrations/admin-email.md). Record the result in `docs/compliance/email-readiness-<clinic_slug>.md` (example: [email-readiness-example-dental.md](../compliance/email-readiness-example-dental.md)).

**Prerequisites:** the Workspace BAA is accepted ([baa-google-workspace.md](../compliance/baa-google-workspace.md)) and `callbacks@` exists. Until then, only steps 1–2 can run.

## 1. Get the address (readiness row 1)
- Ask the clinic SME for the callback mailbox(es), including after hours (P0-01 Q4b).
- Refuse consumer webmail (`gmail.com`, `yahoo.com`, `outlook.com`, …). Ask for an address on the clinic's own domain.
- Record who reads it.

## 2. Check the mail server supports TLS (row 2)
```bash
dig +short MX clinic-domain.com
# for the lowest-priority MX host:
openssl s_client -starttls smtp -connect mx.clinic-domain.com:25 -crlf -brief </dev/null
```
- **Pass:** a real MX exists and the handshake shows a TLS protocol and cipher.
- If your network blocks port 25, use an online STARTTLS checker and note which one.
- A null MX (`0 .`) or no MX means the domain can't receive mail: **fail**.

## 3. Add the TLS rule (row 3)
- Admin console > Apps > Google Workspace > Gmail > Compliance.
- On OU `system-senders`, open "Secure transport (TLS) compliance", and add the clinic's domain.
- **Never remove a domain from this rule to make delivery work.**

## 4. Send a synthetic test (row 4)
- Send one `link_only` email with fake values (`scripts/email/send_test_callback_email.py`, once it can send as `callbacks@`) to the clinic address.
- Ask the SME to confirm it arrived and isn't in spam.
- Check the headers ("Show original") for TLS and `dkim=pass`.

## 5. Full details only (row 5)
- Only if the clinic wants `full_details`: the SME confirms its own email provider is covered by its arrangements, **and** the compliance advisor approves in writing.
- Record the approval reference.

## 6. Configure
Set `callback.admin_emails`, `callback.after_hours_emails`, `callback.email_mode` (default `link_only`) and, only with approval, `callback.full_details_approval` (P4-13 screen, or `clinic_config` before P4).
