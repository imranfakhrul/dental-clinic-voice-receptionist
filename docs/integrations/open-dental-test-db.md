# Open Dental test database (B)

| | |
|---|---|
| Task | P0-12 (issue #13) · DECISIONS #61, #302, #314 |
| Status | **Pending.** Designed, not built |
| Data | **Synthetic only** ([test data](open-dental-test-data.md)). Never a clinic backup or copy (DECISIONS #25) |

## Why it is pending
1. **No developer key yet.** A customer key for (B) is generated in the Developer Portal, which needs our developer key ([open-dental-access.md](open-dental-access.md) §6, email not sent).
2. **Licensing unknown.** Whether a developer may run its own Open Dental installation with the eConnector, and whether that location is billed, is a question in the vendor-relations email.
3. **Where it runs is open.** Local-first (DECISIONS #302) forbids a VM in `dai-rcpt-dev` now. See "Where it can run" below.

Until (B) exists:
- read work uses the public hosted test database (A) through `smoke_test.py`;
- P1-15 and P1-16 build against mocks (`respx`), as the spec's edge-case table allows.

## Design (same as the task spec, location aside)
| Item | Value |
|---|---|
| OS | Windows (a Server or desktop version Open Dental supports: **Verify** on Open Dental's system requirements page when building) |
| Open Dental | Same major version as the clinic: **24.x** (clinic on 24.3, P0-01 B1), with its bundled MySQL/MariaDB |
| eConnector | Installed and **running**; it needs outbound internet to Open Dental HQ (**Verify** its network requirements) |
| Size | 2 vCPU, 8 GB RAM, 100 GB disk |
| Network | No inbound ports from the internet. Admin over RDP only through a private path (IAP TCP forwarding in the cloud; local network only on a team machine) |
| Label | `data=synthetic-only` (cloud label or the machine name) |
| Customer key | `od-customer-key-testdb`; added in Setup > Advanced Setup > API, Enabled |
| Backups | Post-seed snapshot, plus a nightly snapshot kept 7 days |
| Cost | Open Dental fee $30/month if the location is billed (Verify), plus the machine |

## Where it can run
| Option | When | Notes |
|---|---|---|
| **Local VM on a team machine** (e.g. a Windows VM in VirtualBox or Hyper-V) | Now, if Open Dental's licensing allows it | Fits local-first. The eConnector only needs outbound internet. Snapshots come from the hypervisor. Disk encryption on the host is required (device policy, R38). |
| **VM in `dai-rcpt-dev`** (e2-standard-2, no external IP, Cloud NAT, IAP) | After the hosting decision and billing | The original spec design. P1-02 may import it into Terraform. If an org policy blocks it, log a dev-only exception in DECISIONS (synthetic only). |

The tech lead (Riley Tech) chooses when the licensing answer arrives.

## Build steps (when unblocked)
1. Create the machine (above). Install Open Dental 24.x and the eConnector, and confirm the eConnector status is **running** in Open Dental.
2. Generate a customer key in the Developer Portal for this location. Add it in **Setup > Advanced Setup > API > Add Key** and tick **Enabled**. Record the date and who did it in [open-dental-access.md](open-dental-access.md) §5, without the value.
3. Enter the setup data by hand ([seed_setup.md](../../infra/dev/open-dental-test-db/seed/seed_setup.md)).
4. Put the key in `.env` (`OD_CUSTOMER_KEY`, `OD_TARGET=testdb`), then run:

   ```bash
   python3 scripts/open_dental/seed_test_db.py --dry-run
   python3 scripts/open_dental/seed_test_db.py --key-name od-customer-key-testdb
   ```
5. Fill in the PatNum and AptNum columns of [open-dental-test-data.md](open-dental-test-data.md).
6. Take the **post-seed snapshot**.
7. Run `python3 scripts/open_dental/smoke_test.py --target testdb` and record the results in [open-dental-access.md](open-dental-access.md) §8.

## Reset procedure
1. Stop Open Dental and the eConnector, or shut down the machine.
2. Restore the **post-seed snapshot**.
3. Start the machine and confirm the eConnector is running.
4. Run the smoke test.
5. Monthly: extend the provider schedules by 8 weeks, re-run the appointment part of the seed (relative dates), and take a new post-seed snapshot.

## Never
- Restore a clinic backup or any real data into it.
- Use a clinic's customer key against it, or its key against a clinic.
- Expose RDP or MySQL to the internet.
