# Design: P0-12 Open Dental access and test database

## Context
See proposal.md (Why). Facts that shape the approach:
- **User decision 2026-11-26:** use the hosted test DB and drafts; no company email to Open Dental, no paid key, no VM now.
- **DECISIONS #60–#62** already chose the Remote API, the two-level test DB and the least-privilege permission set. **#302** (local-first) forbids cloud resources now, so test DB (B) can't be a VM in `dai-rcpt-dev`, and keys can't go to Secret Manager.
- **P0-01:** B1 says the clinic runs Open Dental 24.3 with the eConnector running; B2 says Jordan Example enables the key; B4 says the AI creates new patients but doesn't update existing ones.
- **P0-02 mapping:** 10-minute increment, providers DDS1/HYG1/HYG2, operatories 1–4, types New Patient Exam (#1), Recall (#2), Child Recall (#3), Limited Exam (#4).
- P1-18 is merged into P1-15 (survivor IDs used in hand-offs).

## Goals / Non-Goals
**Goals:**
- prove the Remote API contract (auth header, status codes, rate limiting) against a real server, at no cost;
- leave the developer-key request, test DB (B) and seed ready to run;
- keep keys and real data out of the repo.

**Non-Goals:** the HTTP client (P1-15), the adapters (P1-16), Terraform for a VM (P1-02), signing the clinic BAA (P0-09).

## Decisions
1. **Facts re-checked before use.** Open Dental's apisetup, apipermissions, apiimplementation, apilocal and apispecification pages are fetched during apply, and the parts we rely on (hosted test DB, auth header, tiers, rate limits, minimum versions, endpoint paths for the smoke test) are recorded in `sources/README.md` with dates and hashes. The **published test credentials are not copied** into the repo or the sources file: the docs link the page and say where to put them.
2. **Smoke test, standard library only.** `urllib` with explicit timeouts. It reads `OPEN_DENTAL_BASE_URL`, `OD_DEVELOPER_KEY` and `OD_CUSTOMER_KEY` from the environment, strips pasted whitespace, and refuses to print a value. Checks: `GET` patients (Simple search), providers, operatories, appointment types, appointments; one request with a wrong customer key (records 401 or 403); 10 sequential requests (latency and effective rate) and 5 parallel requests (records any 429 and `Retry-After`). It prints counts and IDs only, through a single print function that only accepts numbers and status strings. Exact endpoint paths come from the API spec page (Verify) and are kept in one table in the script.
3. **One manual run against the hosted DB, asked first.** About 20 read requests in total; the results (statuses, counts, latencies, 429 behaviour) go in `open-dental-access.md`. Because the database is public and shared, counts change over time and are recorded only as observations, not as test expectations.
4. **Seed as data plus a guarded loader.** `seed_patients.csv` holds ≥30 fictional patients (spec §6 cases, `555-01xx` numbers, a `case` column naming each edge case); appointments are described in the same doc with relative dates. `seed_test_db.py` validates the CSV (`--dry-run`), then would POST through the API, but refuses unless `OD_TARGET=testdb` and the key source is named `*-testdb`, and refuses any run where the base URL and key match the published hosted credentials. Writing to (B) needs (B) to exist, so the real load is pending.
5. **Comm update for Break (found during apply).** Open Dental's permission page puts `PUT /appointments/{AptNum}/Break` and `…/Confirm` under the **Comm** group, not Appointments. Cancelling through Break is the documented way (the appointment goes to the Unscheduled List and a CommLog entry is made), so Comm (update) is requested, limited in the request text to Break and Confirm. Tier stays $30. Supersedes the "no Comm" part of DECISIONS #62.
6. **Patients permission: create only.** P0-01 B4 creates new patients; nothing in the approved flows updates an existing patient's record (the "AI-booked" marker is an appointment note, Q2). Recorded as a refinement of DECISIONS #62.
7. **Secrets now vs later.** Now: a local `.env` (already git-ignored; `!.env.example` is allowed) with three variables; `.env.example` lists them with empty values. Later: the spec's Secret Manager names (`od-developer-key`, `od-customer-key-testdb`, `od-customer-key-<clinic>` in prod only after the BAA). Both are documented in `open-dental-access.md`.
8. **Test DB (B) design kept, location open.** The doc keeps the spec's design (Windows, Open Dental at the clinic's major version 24.x, eConnector, `data=synthetic-only`, snapshot reset) and lists the two possible homes: a local Windows VM on a team machine (needs Open Dental's licensing answer) or a VM in `dai-rcpt-dev` once hosting and billing exist. Pending either way.
9. **Vendor-relations email as a draft.** Written in `open-dental-access.md` with placeholders for company name, billing email and address, the permission table, an application description without patient data, and the questions from spec step 2 (tier, test-location billing, test-install licensing, Setup group for setup GETs, Enterprise throttle). Sent later by the sponsor or senior.

## Risks / Trade-offs
- [Public test DB data looks real] → Output prints IDs and counts only; nothing from it is copied into the repo.
- [Hosted credentials stop working] → Recorded as an observation; (B) remains the target.
- [Rate test seen as abuse] → Only ~20 requests in total, one run.
- [Endpoint paths differ from the spec's guesses] → Taken from the API spec page during apply; the table in the script is the single place to fix.

## Migration Plan
Not applicable.

## Open Questions
- Sponsor approval of fees and who sends the email (sponsor/senior; doesn't change the drafts).
- Open Dental's licensing answer for a developer test install (decides where (B) runs).
