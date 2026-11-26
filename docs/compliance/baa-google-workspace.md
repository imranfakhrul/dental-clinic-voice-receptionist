# Google Workspace HIPAA BAA record

> **Status: NOT ACCEPTED.** We have no company domain or Google Workspace yet; both are bought for production (DECISIONS #304). **No PHI may be sent by email.** Callback emails exist only as synthetic tests (local Mailpit; a test from a personal Gmail with fake data is planned).

| Field | Value |
|---|---|
| Vendor | Google (Google Workspace) |
| Agreement name | Google Workspace/Cloud Identity HIPAA Business Associate Amendment |
| Status | **NOT ACCEPTED** (paper record, as for Google Cloud, DECISIONS #293) |
| Workspace edition | - (not bought). Must be an edition that offers the BAA; Google's help page lists none (E1). **Verify at purchase** with Google sales or support. The legacy free edition can't accept it (task spec §3). |
| Document version / date | - |
| Accepted on | - |
| Accepted by | - (a super administrator with authority to bind the company; still to be named) |
| Authority confirmed by | - |
| Scope | Workspace services on Google's list, including **Gmail** (E2). Third-party add-ons aren't covered. |
| Saved copy | - (decide before accepting whether the PDF goes in the repo or a private drive; the repo is public) |
| Legal review of terms | Pending (compliance advisor), P0-11 |
| Used for | Callback emails to clinic admins, from `callbacks@<company domain>` ([admin-email.md](../integrations/admin-email.md)) |

## How to accept (when the company decides to)
Source: E1 (Google, last updated 2026-11-10).
1. Sign in to the Admin console **from a super administrator account**.
2. Go to **Account settings > Legal and compliance > Security and Privacy Additional Terms**, open the **HIPAA Business Associate Amendment**, choose **Review and Accept**, and answer the covered-entity questions.
3. Save the accepted text as a PDF; note the date and the edition.
4. Fill in every field above, set the status to **ACCEPTED**, add a DECISIONS row, and update the vendor matrix (P0-10).

## Gates before any PHI in email
- [ ] This BAA is accepted and recorded.
- [ ] `callbacks@` exists with the lock-down, and the TLS rule covers the clinic's domain ([admin-email.md §12](../integrations/admin-email.md#12-pending-before-go-live)).
- [ ] The clinic passes the readiness check with its real domain.
- [ ] The clinic ↔ company BAA covers Google as a subcontractor (P0-09), and the vendor matrix lists it (P0-10).

## Review
Reviewed by Sam Comply (compliance advisor), 2026-11-26: "The product (Gmail under the Workspace BAA) is named. While this record says NOT ACCEPTED, no PHI may be emailed; the default `link_only` mode keeps PHI out of email even after acceptance."
