---
id: P0-12
title: Get Open Dental API keys and a test database
milestone: P0
epic: E0.3
size: S
labels: area:open-dental, type:chore
depends_on: P0-01
status: approved
---

# P0-12: Get Open Dental API keys and a test database

## 1. Summary
Get API access to Open Dental and a database to develop against:
1. **Developer key:** ours, requested from Open Dental vendor relations with least-privilege permissions.
2. **Test databases, in two levels:**
   - (A) Open Dental's **hosted shared test database**, usable on day 1 for smoke tests;
   - (B) **our own test database** (Open Dental + eConnector on a Windows VM in `<prefix>-dev`), seeded with documented synthetic data and resettable. This is the integration DB for dev, staging and CI.
3. **Customer keys:**
   - one for our test DB;
   - one for the pilot clinic, which is generated now but **put into use only after the clinic BAA is signed** (P0-09).
4. **Secrets:** all keys go in Secret Manager, never in code.

We also record the API's rate limits (one request per second per clinic on the Remote API) and hand them to the client, caching and latency tasks.

Done means:
- the developer key works;
- the test DB is reachable through the Remote API from `<prefix>-dev`;
- the seed data is loaded and documented;
- keys are in Secret Manager;
- the dependent tasks are notified.

## 2. Why this matters
Every Open Dental task depends on this one: P1-15 (HTTP client), P1-16 to P1-18 (adapters), P1-20 (availability engine), the P2 flows and the P2-30 end-to-end test. Without a test DB with known data, developers can't write integration tests, and edge cases such as duplicate names or phone formats can't be reproduced.

Getting it wrong is also a HIPAA risk:
- If developers test against the clinic's real database, real PHI reaches dev machines and logs (P0-11 R11).
- If the clinic key is used before the BAA, we are handling PHI without a contract (P0-09).
- A leaked key gives access to a whole clinic database (P0-11 R12).

Open Dental access also takes time (vendor relations needs 1–3 business days, and the clinic must enable the key), so it must start in P0.

Plan references: §8 Phase 0 ("Get Open Dental API access… and set up a test database"), §3 (Secret Manager: "Open Dental keys never reach the frontend"), §6 (least privilege for the Open Dental API key), §12 (Open Dental API limits risk).

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P0, Discovery & Compliance Foundation**.
- **API modes** (https://www.opendental.com/site/apilocal.html, https://www.opendental.com/site/apisetup.html):
  - **Remote API** `https://api.opendental.com/api/v1`: cloud-hosted by Open Dental, which relays each request to the office's database through the office's **eConnector**. Needs Open Dental 21.1+ and a running eConnector. **This is the mode we use.** Our backend runs in Google Cloud and can't reach a clinic's LAN.
  - **Local API** (port 30222, on a workstation, 22.1+) and **API Service** (port 30223, on the clinic's database server, 22.2+ with eConnector 22.2.16+): these run inside the clinic's network, so they are not reachable from Cloud Run. Not used in the MVP.
- **Authentication:** every request sends `Authorization: ODFHIR {DeveloperKey}/{CustomerKey}` and `Content-Type: application/json` (apisetup.html, apiimplementation.html).
  - The **developer key** is ours, one key for all clinics.
  - A **customer key** identifies one office database.
- **How keys are obtained** (apisetup.html):
  - **Developer key:** email `vendor.relations@opendental.com` with:
    - company name;
    - billing email and mailing address;
    - for each permission group, whether we need read, create or update;
    - a description of the application.

    Processing takes 1–3 business days. After that we log into the **Developer Portal**, where the developer key is shown.
  - **Customer key:** we generate it in the portal. The office's Open Dental admin adds it in **Setup > Advanced Setup > API > Add Key** and ticks **Enabled**. The office can enable or disable the key but can't change its permissions.
- **Permissions and fees** (https://www.opendental.com/site/apipermissions.html):
  - Permissions are set **per developer key**, by permission group (Read All, Patients, Appointments, Setup, …).
  - Fees are paid **by the developer, per location, per month**, once a key is assigned and enabled; billing stops when the key is disabled. Tiers:
    - Free: Read All only;
    - $15;
    - $30: "all except Payments, PayPlans, and Special";
    - $35.

    **Verify** with vendor relations which tier our permission set falls into (we expect $30, because Patients and Appointments are not in the $15 bundle), and whether a developer-owned test location is billed.
  - Permissions don't enforce Open Dental's own UI restrictions ("date restrictions do not apply"), so our code must enforce clinic rules itself (P1-19, P2-09).
- **Rate limits** (https://www.opendental.com/site/apiimplementation.html):
  - Remote API with only Read All: **1 request per 5 seconds**.
  - Remote API with any other permission: **1 request per second**.
  - Enterprise: 500 ms.
  - Throttling is **per customer key** (i.e. per clinic), not per developer key, and requests for one customer key are processed **one after another**.
  - Too many queued requests return **429** with `Retry-After`.
  - A request running longer than 60 s returns **504**.
  - Lists return up to 100 items per request.
  - Open Dental may suspend keys for excessive requests.
- **Hosted test database:** "Open Dental hosts a test database for developers to test against", at the same base URL, with credentials published on apisetup.html. It is **public and shared** by all developers. Anyone may read or change its data, and the page doesn't say whether it is reset or what permissions the published key has (**Verify**).
- **Versions:** the API URL stays `v1`. A method works only if the office's Open Dental version is at least the version that added it; otherwise the API returns 400 (apiimplementation.html). P0-01 B1 records the clinic's version.
- **BAA:** Open Dental states that "API developers should have a Business Associate Agreement (BAA) in place with their clients" (apispecification.html). That is our clinic BAA (P0-09).

## 4. Scope
**In scope**
- The developer key request (permissions, tier, billing contact) and the portal login.
- Test DB (A): verify that the hosted test DB works with our developer key, and use it for read-only smoke tests.
- Test DB (B): a Windows VM in `<prefix>-dev` running Open Dental, MySQL (as installed by Open Dental) and the eConnector; a customer key for it; synthetic seed data; reset procedure.
- Seed data definition and documentation.
- Generate the pilot clinic's customer key and get it enabled by the clinic's Open Dental admin, gated by the BAA.
- Secret Manager secrets and access rules.
- Recording the rate limits and the fee in DECISIONS.md and notifying the dependent tasks.

**Out of scope** (and which task covers it)
- The HTTP client, throttling queue and retries → P1-15
- Patient, appointment and setup adapters → P1-16, P1-17, P1-18
- Terraform for the VM (the first version is manual and documented; P1-02 may import it later)
- Secret Manager / KMS / service-account baseline → P1-05 (this task creates only the Open Dental secrets)
- Signing the clinic BAA → P0-09
- Copying the clinic's appointment types and providers → P0-02

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P0-01 Discovery workshop (approved spec) | B1 (Open Dental version, hosting, eConnector), B2 (who enables API access at the clinic) | Request the developer key and build test DB (B) now; neither needs the clinic. Only the clinic customer key waits for B1/B2. |
| P0-05 Google Cloud foundation (approved spec, soft) | `<prefix>-dev` and `<prefix>-staging` projects | Until they exist, keep keys in a password manager shared by the tech lead only, and move them to Secret Manager when the projects exist (step 8). Never in code or chat. |
| P0-06 Guardrails (approved spec, soft) | `compute.googleapis.com` allowed in dev; CMEK requirement if Assured Workloads is chosen | If the VM is blocked by policy, log an exception in DECISIONS.md (synthetic data only, never PHI) or run test DB (B) in the `ops` project. Decide with the tech lead. |
| P0-09 Clinic BAA (approved spec) | Signature, before using the clinic's key | Generate and enable the key, but don't create the prod secret version until `baa-clinic-<clinic_slug>.md` exists. |
| P0-02 Appointment-type mapping (approved spec, soft) | Appointment types, providers, durations to mirror in the seed | Use the 15 reason codes and the example mapping from the P0-02 spec. |

## 6. Interface contract

### Files
| Path | Content |
|---|---|
| `docs/integrations/open-dental-access.md` | Developer key request (permissions requested and granted, tier, date, billing contact), portal owner, customer keys list (location name, environment, created, enabled by; **no key values**), rate limits, version notes |
| `docs/integrations/open-dental-test-db.md` | Test DB (B): VM details, how to connect (IAP), Open Dental version, eConnector status check, reset procedure, cost |
| `docs/integrations/open-dental-test-data.md` | Seed data definition (below) |
| `infra/dev/open-dental-test-db/seed/seed_patients.csv`, `seed_setup.md` | The seed source (synthetic) |
| `scripts/open_dental/smoke_test.py` | Read-only checks through the Remote API (§10) |
| `scripts/open_dental/seed_test_db.py` | Loads the synthetic patients and appointments through the API into test DB (B); refuses to run unless the customer-key secret name ends with `-testdb` |

### Requested permissions (Proposed; least privilege)
| Permission group | Need | Used by |
|---|---|---|
| Read All | read | Every GET (patients, appointments, providers, operatories, schedules, appointment types) |
| Patients | create, update | P1-16 registration (create); update only if P0-01 decides staff-approved updates are allowed. Otherwise request create only. |
| Appointments | create, update | P1-17 book, reschedule, break/cancel |
| Setup | none beyond Read All | (Read All covers the GETs). **Verify** with vendor relations whether setup GETs need the Setup group. |
| Payments, PayPlans, Insurance, Documents, Queries, Comm | **not requested** | — |

### Secret Manager (Proposed names)
| Secret | Project(s) | Value | Who can read |
|---|---|---|---|
| `od-developer-key` | dev, staging, prod | Our developer key (separate secret per project, same value) | The backend runtime service account of that project (P1-05); the tech lead via break-glass |
| `od-customer-key-testdb` | dev, staging | Customer key of test DB (B) | Backend SA in dev/staging; CI SA for integration tests (P1-06) |
| `od-customer-key-hosted-test` | dev | The published key of Open Dental's hosted test DB | Developers (it is public anyway) |
| `od-customer-key-<clinic_slug>` | **prod only** | The pilot clinic's customer key | Prod backend SA only. **First version created only after the P0-09 BAA is signed.** |

Config key the backend reads (P1-08 / P1-15): `OPEN_DENTAL_BASE_URL` (default `https://api.opendental.com/api/v1`), and per clinic the secret name `od_customer_key_secret` in the `clinics` settings (plan §5). Key values are never written to env files, logs, the database or the frontend.

### Test DB (B): the VM (Proposed)
- **Project and network:**
  - `<prefix>-dev`, region `us-central1` (or the region chosen in P0-05);
  - no external IP;
  - outbound internet through Cloud NAT, which the eConnector needs to reach Open Dental HQ (**Verify** the eConnector's network requirements);
  - administration over RDP via IAP TCP forwarding only.
- **Machine:** Windows Server (a version supported by Open Dental, **Verify**), e2-standard-2, 100 GB disk (CMEK if P0-06 requires it), nightly snapshot.
- **Software:** Open Dental at the same major version as the pilot clinic (P0-01 B1), its MySQL/MariaDB, and the eConnector.
- **Licensing (Verify):** ask vendor relations, in the same email as the key request, whether developers may run a test installation with the eConnector, and on what terms.
- **Label:** `data=synthetic-only`. The VM must never receive real patient data, including from a clinic backup.

### Seed data (`open-dental-test-data.md`; all synthetic)
**Setup (entered in Open Dental's UI, documented in `seed_setup.md`):**
- 3 providers: 2 dentists, 1 hygienist;
- 4 operatories;
- clinic hours Mon–Fri 08:00–17:00 with a lunch block;
- one holiday;
- provider schedules for the next 8 weeks (re-run monthly);
- appointment types matching the P0-02 example mapping (new patient exam, recall cleaning, emergency exam, …), with their patterns;
- time increment as at the pilot clinic.

**Patients (`seed_patients.csv`; at least 30, all fictional, `555-01xx` phone numbers):**
| Case | Example | Used by |
|---|---|---|
| Plain returning patient | Maria Lopez, 1985-03-14 | P1-16, P2-14 |
| Same name, different DOB | Two "John Smith" | P2-13 matching |
| Same name and DOB (twins) / same family phone | Twin siblings sharing a guardian phone | P2-13, P2-14 |
| Nickname vs legal name | "Bill" vs "William" Turner | P2-12 |
| Hyphenated / apostrophe / accented names | "Anne-Marie O'Neil", "José Núñez" | P2-12, P1-16 |
| Phone stored in different formats | `5035550101`, `(503) 555-0102`, `503-555-0103` | P1-16 phone-format spike |
| Missing DOB / missing phone | | P1-16 |
| Inactive / archived / deceased status | | P1-16 status filter |
| Child with guardian | | P0-01 minors policy, P2-15 |
| Patient with future appointments; with a broken appointment; with a past appointment only | | P1-17, P2-17, P2-18 |

**Appointments:** booked slots that create realistic availability gaps, one double-booking attempt target, and appointments around the next DST change (P5-04).

**Reset:** restore the post-seed snapshot (procedure in `open-dental-test-db.md`). Integration tests must not assume a clean DB unless they run right after a reset. They create their own uniquely named patients (prefix `ZZTEST`) and clean up by breaking their appointments.

## 7. Implementation guide
1. **Prepare the request.** Fill in the permissions table (§6). The sponsor approves the monthly fee (per location: the test DB and each clinic). Name the portal owner, normally the tech lead, with a shared company mailbox, not a personal one.
2. **Email vendor relations** (`vendor.relations@opendental.com`) with the required fields. In the same email, ask:
   - which tier applies;
   - whether test locations are billed;
   - test-installation licensing;
   - whether Setup GETs need the Setup group;
   - whether Enterprise throttling (500 ms) is available and at what cost.

   Record the answers in `open-dental-access.md`.
3. **Hosted test DB (A).** With the developer key from the portal (or the published test credentials until then), run `smoke_test.py` read-only against the hosted DB. Record what works and the permissions of the published key (**Verify**). Never write identifying-looking data there; it is public.
4. **Build test DB (B):**
   - create the VM (§6), install Open Dental (pilot clinic's major version) and the eConnector;
   - confirm the eConnector status is running;
   - generate a customer key in the portal for this location, add it in **Setup > Advanced Setup > API**, and tick Enabled;
   - document every step in `open-dental-test-db.md`.
5. **Seed:**
   - enter the setup data in the UI;
   - run `seed_test_db.py` for patients and appointments;
   - take the post-seed snapshot.

   Record the resulting PatNums and AptNums of the named cases in `open-dental-test-data.md`, so tests can reference them.
6. **Run `smoke_test.py` against (B)** from `<prefix>-dev` (Cloud Shell or a dev Cloud Run job), using the Secret Manager secrets.
7. **Measure the rate limit:**
   - send 10 sequential GETs and record the latency and the effective rate;
   - send 5 in parallel and record whether any return 429 with `Retry-After`.

   Save the numbers in `open-dental-access.md`.
8. **Create the secrets** (§6) with access only for the named service accounts (P1-05 creates the SAs; until then the secrets exist with no accessors except the tech lead).
9. **Pilot clinic key:**
   - after P0-01 B1/B2, generate the clinic's customer key in the portal and give it to the clinic's Open Dental admin by a secure channel (not plain email; a password manager share or read it out by phone);
   - they add it and tick Enabled, or leave it disabled until go-live;
   - **only after `baa-clinic-<clinic_slug>.md` exists**, create the secret version in prod and set the P0-10 `clinics` row's gate condition.

   No dev or staging environment ever gets the clinic key.
10. **Notify:**
    - P1-15: base URL, headers, rate limits, 429/504 behaviour, per-key sequential processing;
    - P1-16, P1-17, P1-18: test DB, seed cases, PatNums;
    - P1-20: config caching need;
    - P3-15: Open Dental latency numbers;
    - P0-02: numeric IDs visible in setup;
    - P0-10: Open Dental row and fees;
    - P0-11: R12 answer on least-privilege keys.

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| Vendor relations takes longer than 3 business days | Use the hosted test DB (A) with the published credentials for read work; P1-15 and P1-16 continue against mocks (`respx`). Follow up by email. |
| The VM is blocked by an org policy (P0-06) | Don't weaken the policy for prod. Log a dev-only exception in DECISIONS.md, or host (B) in `ops`. Tech lead decides. |
| Licensing doesn't allow a developer test install with eConnector | Fall back to (A) only, plus a second request to Open Dental for a private developer test database. Record it as a project risk (seed data can't be controlled). |
| The pilot clinic's Open Dental is older than 21.1, or has no eConnector (P0-01 B1) | Blocked: the Remote API can't work. Escalate to the sponsor; the clinic must upgrade or enable the eConnector (Open Dental support). |
| The clinic's version is older than a method we need (400 "version too low") | Record which methods are affected; P1-17/P1-18 need a fallback or the clinic upgrades. |
| Somebody proposes testing against a copy of the clinic's real database | Refuse. Real PHI only in prod after the gate (DECISIONS #25). |
| 429 during seeding or tests | Respect `Retry-After`; run integration tests serially per customer key (P1-06). |
| The published hosted-test key stops working | Use (B); update the docs. |
| A key is exposed (committed, pasted in chat) | Disable it in the portal (or ask the clinic to disable it), generate a new one, update the secret, record it as a security event (P0-11 R12, P5-12). |
| Billing contact leaves the company | The portal login uses a shared company mailbox (step 1), so access isn't lost. |

## 9. Security, HIPAA and PHI
- **This task handles no PHI.** Test DBs contain only synthetic data. The clinic's key isn't used until the BAA is signed, and then only in prod.
- **Keys are credentials:**
  - Secret Manager only;
  - never in code, env files, CI logs, tickets, chat or the frontend;
  - the LLM never sees them (plan §4.2);
  - access is limited to the runtime SA of each environment.
- **Least privilege:** only the permission groups in §6; no Payments, Insurance or Queries.
- The hosted test DB (A) is **public**. Never put realistic-looking real data there, even "test" data copied from anywhere real.
- **Test DB VM:** no external IP, IAP-only admin, label `data=synthetic-only`, snapshot retention 7 days.
- **Audit:**
  - Secret Manager access is in Cloud Audit Logs (P0-06/P1-07);
  - key creation and enablement are recorded in `open-dental-access.md` (who, when, which location; no values).

## 10. Testing
`scripts/open_dental/smoke_test.py --target hosted|testdb` (read-only; prints counts and IDs only, never names or DOBs):
- `GET /patients/Simple` with a seed last name → returns ≥ 1, the status is 200;
- `GET /providers`, `/operatories`, `/appointmenttypes`, `/schedules` (**Verify** exact paths in the API spec) → 200 with the seeded counts;
- `GET /appointments` for a seeded patient → matches `open-dental-test-data.md`;
- a request with a wrong customer key → 401/403 (record the actual status for P1-15);
- 5 parallel requests → record 429 and `Retry-After` if they occur.

Manual checks:
- the reviewer confirms there are no key values in the repo (`git grep -n "ODFHIR "` shows only docs placeholders);
- the secrets' IAM bindings are listed;
- the VM has no external IP.

## 11. Acceptance criteria
- [ ] The developer key is issued with the §6 permissions; the granted permissions, tier and fees are recorded in `open-dental-access.md`
- [ ] Test DB (B) runs in `<prefix>-dev` with the eConnector running, and is reachable through the Remote API with its customer key from the dev project
- [ ] Seed data is loaded and documented, with PatNums for every named case; a post-seed snapshot and reset procedure exist
- [ ] `smoke_test.py` passes against (B); results against (A) are recorded
- [ ] The secrets in §6 exist with the listed accessors only; no key value is in the repo
- [ ] Rate-limit measurements are recorded and sent to P1-15 and P3-15
- [ ] The pilot clinic's key is generated and enabled by the clinic, and its prod secret is created only after the P0-09 BAA record exists (or is explicitly pending with that condition)
- [ ] The P1-15, P1-16, P1-17, P1-18, P1-20, P3-15, P0-02, P0-10 and P0-11 issues are notified

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI: `smoke_test.py` runs manually now; P1-06 adds it as a nightly job against (B)
- [ ] PR reviewed (HIPAA review if labelled `phi`): reviewed by the tech lead; no `phi` label (synthetic data only)
- [ ] No PHI in logs: the smoke test prints IDs and counts only
- [ ] Docs / README updated: the three `docs/integrations/open-dental-*.md` files

## 13. Hand-off
| Task | Can rely on |
|---|---|
| P1-15 HTTP client | Base URL, auth header, secrets names, rate limits (1 req/s per customer key, sequential, 429 + `Retry-After`, 504 after 60 s), error statuses seen |
| P1-16, P1-17, P1-18 Adapters | Test DB (B), seed cases with PatNums, the phone-format cases, version notes |
| P1-20 Availability engine | The throttle: cache providers, operatories, appointment types and schedules; minimize calls per availability query |
| P3-15 Latency tuning | Measured Open Dental latency per request |
| P1-06 CI/CD | `od-customer-key-testdb` for integration tests; run them serially; nightly smoke test |
| P0-02 Mapping | Whether numeric IDs are visible in setup screens |
| P0-10 Vendor matrix | Open Dental row: fees, permissions, keys per location |
| P0-11 Risk assessment | R12 answer (least-privilege permissions granted) |

## 14. Open questions
| Question | Owner | Needed by |
|---|---|---|
| Will the sponsor approve the monthly per-location fees (test DB + each clinic), and the Enterprise throttle if needed? | Project sponsor | Step 1 |
| Does Open Dental allow a developer test installation with the eConnector, and is that location billed? | Tech lead, via vendor relations | Step 2 |
| Is 1 request/second per clinic enough for our concurrency and latency targets, or do we need Enterprise (500 ms)? Answered by step 7 numbers plus P1-20 design. | Tech lead | Before P1-20 |
| Does registration need `Patients: update`, or is `create` enough? (Depends on P0-01 decisions about updating existing records.) | Tech lead + clinic SME | Step 1 |

## 15. References
- Plan §8 Phase 0, §3, §4.2, §5, §6, §12
- Open Dental API setup and keys: https://www.opendental.com/site/apisetup.html
- Permissions and fees: https://www.opendental.com/site/apipermissions.html
- Implementation notes (throttling, errors, versions): https://www.opendental.com/site/apiimplementation.html
- Local API / API Service: https://www.opendental.com/site/apilocal.html
- API specification: https://www.opendental.com/site/apispecification.html
- Google Cloud IAP TCP forwarding: https://cloud.google.com/iap/docs/using-tcp-forwarding (Verify current URL)
- Related tasks: P0-01, P0-02, P0-05, P0-06, P0-09, P0-10, P0-11, P1-02, P1-05, P1-06, P1-08, P1-15, P1-16, P1-17, P1-18, P1-19, P1-20, P2-12, P2-13, P2-14, P2-15, P3-15, P5-04
