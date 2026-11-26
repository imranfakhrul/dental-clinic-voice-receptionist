# Proposal: P0-12 Open Dental API access and test database (issue #13)

## Why

Every Open Dental task depends on API access and a database with known data: P1-15 (HTTP client), P1-16 (adapters; P1-17 merged into P1-16, P1-18 into P1-15), P1-20 (availability), the P2 flows and the end-to-end test. Getting it wrong is a HIPAA risk: testing against a clinic's real database puts real PHI on dev machines (P0-11 R11), using a clinic key before the BAA handles PHI without a contract (P0-09, R36), and a leaked key exposes a whole clinic database (R12).

Our situation (user decision 2026-11-26): no company account with Open Dental yet, no clinic, and **local-first** (DECISIONS #302: no Google Cloud resources, so no Windows VM in `dai-rcpt-dev` and no Secret Manager). So this change does everything that needs no money and no company identity, and leaves the rest as ready-to-run drafts.

## What Changes

- **Hosted test database (A):** use Open Dental's free, **public** hosted test database with the credentials Open Dental publishes, for **read-only** smoke tests and a small rate-limit measurement. Credentials go only in a git-ignored local `.env` file, never in the repo. Nothing is written to the public database.
- **`scripts/open_dental/smoke_test.py`:** standard library only; read-only GETs; prints status codes, counts and IDs only (never names, DOBs or phones); `--target hosted|testdb`; records 401/403 for a wrong key and 429/`Retry-After` behaviour.
- **`docs/integrations/open-dental-access.md`:** API mode (Remote API), auth header, permissions to request (least privilege: Read All; Patients **create only**, since P0-01 B4 needs no update; Appointments create/update; Comm update for Break/Confirm, which Open Dental files under Comm), expected tier and fees (Verify), rate limits re-checked against Open Dental's pages, version notes (clinic on 24.3, P0-01 B1), the **vendor-relations email draft (not sent)**, the customer-key list (no values), the smoke-test and rate-limit results.
- **Secrets plan:** Secret Manager names from the spec for later; **now** a local `.env` with `OD_DEVELOPER_KEY`, `OD_CUSTOMER_KEY` and `OPEN_DENTAL_BASE_URL` (DECISIONS #302), plus a committed `.env.example` with placeholders only.
- **`docs/integrations/open-dental-test-db.md`:** design of our own test DB (B) (Open Dental + eConnector on a Windows machine, synthetic only, reset by snapshot), recorded as **pending**: needs the developer key, Open Dental's licensing answer and a place to run it (local or cloud, once hosting is decided).
- **`docs/integrations/open-dental-test-data.md`** with **`infra/dev/open-dental-test-db/seed/seed_patients.csv`** and `seed_setup.md`: synthetic seed (≥30 fictional patients with `555-01xx` numbers covering the spec's edge cases; setup mirroring the P0-02 mapping).
- **`scripts/open_dental/seed_test_db.py`:** loads the seed into test DB (B) only; refuses any target whose key name doesn't end in `-testdb`, and **refuses the hosted public DB**; `--dry-run` validates the CSV now.
- **Clinic key:** recorded as **pending**: generated only after the developer key exists, enabled by the clinic's Open Dental admin (Jordan Example, B2), and used only after the clinic BAA is signed (P0-09; gate CLOSED in P0-10).
- **Records:** DECISIONS rows; sources rows for Open Dental's pages; notifications (P0-02, P0-10, P0-11 and the P1 tasks via the README, as their issues don't exist); READMEs and `docs/PROJECT_MAP.md`.

## Capabilities

### New Capabilities
- `open-dental-access`: how we reach Open Dental (Remote API, keys, least-privilege permissions, rate limits), which databases development may use (hosted public test DB, our synthetic test DB; never a clinic's real data before the BAA), and how keys are stored.

### Modified Capabilities
None.

## Impact

- New: the three `docs/integrations/open-dental-*.md` files, the seed folder, `scripts/open_dental/smoke_test.py` and `seed_test_db.py`, `.env.example`.
- Updated: `dental-ai-tasks/DECISIONS.md`, `docs/compliance/sources/README.md`, `docs/compliance/README.md`, `docs/phase-0-discovery-compliance/README.md`, `docs/PROJECT_MAP.md`; possibly `docs/compliance/vendors.yaml` notes (Open Dental row: fees, permissions) with a re-render.
- Network: a few read-only HTTPS requests to Open Dental's public test database (asked before running). No cloud resources, no cost.
- Acceptance criteria met partly: developer key, test DB (B), seed load, secrets in Secret Manager and the clinic key stay pending (recorded).
