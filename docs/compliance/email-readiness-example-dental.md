# Callback email readiness: our clinic (P0-08)

| | |
|---|---|
| Clinic | Example Dental (P0-01 SME: Alex Sample, office manager) |
| Address | `frontdesk@example.com` (P0-01 Q4b: one shared mailbox for all hours) |
| Content mode | `link_only` (P0-01 B7) |
| Checked | 2026-11-26 by Riley Tech (tech lead), following [admin-email-add-clinic.md](../runbooks/admin-email-add-clinic.md) |
| **Result** | **NOT READY.** `example.com` is a reserved placeholder domain with a null MX, so it can't receive email. Re-run with the clinic's real domain at onboarding. |

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | Clinic-controlled address | **Pass (SME-confirmed)**: Alex Sample confirms the front-desk team reads `frontdesk@`, a clinic domain address, not webmail. The clinic uses Google Workspace with its BAA (P0-01 Q7). | Decision log Q4b, Q7 |
| 2 | Mail server supports TLS | **Fail**: `dig +short MX example.com` returns `0 .` (null MX: the domain accepts no mail). The STARTTLS tool itself works from our network: tested on a Gmail inbound MX, it negotiated TLSv1.3. | Command output, 2026-11-26 |
| 3 | TLS rule added | **Pending**: no Workspace or `system-senders` OU yet (bought for production) | [admin-email.md §12](../integrations/admin-email.md#12-pending-before-go-live) |
| 4 | Test email arrives | **Pending**: needs a real clinic domain and `callbacks@`. The template and SMTP path are tested locally (Mailpit) and through a personal Gmail with fake data. | [admin-email.md §11](../integrations/admin-email.md#11-tests-run) |
| 5 | Clinic mailbox HIPAA-appropriate | **Not applicable**: `link_only` mode. (For the record, the SME says the clinic's Workspace BAA is accepted, Q7.) | - |

**Next step:** at onboarding, get the clinic's real domain, then re-run rows 2–4 and update this file.
