# Open Dental API access

| | |
|---|---|
| Task | P0-12 (issue #13) · DECISIONS #60–#62, #312–#314 |
| Status | **Developer key: not requested** (email drafted, §6). **Hosted test database: smoke test ready, run deferred by the user** (§8). Our own test database: pending ([open-dental-test-db.md](open-dental-test-db.md)). Clinic key: pending the clinic BAA (§5) |
| Facts | Checked 2026-11-26 against Open Dental's pages, sources [D1–D8](../compliance/sources/README.md#p0-12-open-dental-api-checked-2026-11-26) |
| Related | [Test data](open-dental-test-data.md) · [Test database (B)](open-dental-test-db.md) · `scripts/open_dental/smoke_test.py` · `scripts/open_dental/seed_test_db.py` |

**No key value is ever written in this repository**, including the hosted test database's published key. Keys live in a git-ignored `.env` now and in Secret Manager later (§4).

## 1. API mode and authentication
- **Remote API** (DECISIONS #60): base URL `https://api.opendental.com/api/v1` (D3). Open Dental relays each request to the office's database through the office's **eConnector**. It needs Open Dental 21.1 or later (D4).
- Local API (22.1) and API Service (22.2) run on the clinic's network, so our backend can't reach them. Not used in the MVP.
- Every request sends `Authorization: ODFHIR {DeveloperKey}/{CustomerKey}` and `Content-Type: application/json` (D1).
  - **Developer key:** ours, one for all clinics, shown in the Developer Portal.
  - **Customer key:** one per office database. We generate it in the portal; the office adds it in **Setup > Advanced Setup > API > Add Key** and can enable or disable it, but can't change its permissions (D1).
- Open Dental says "API developers should have a Business Associate Agreement (BAA) in place with their clients" (D5). That is our clinic BAA (P0-09, NOT SIGNED).

## 2. Permissions to request (least privilege)
Permissions are set **per developer key**, by group (D2). Requested set (DECISIONS #62 as refined by #312):

| Group | Need | Methods we use | Used by |
|---|---|---|---|
| Read All | read | `GET /patients/Simple`, `GET /patients`, `GET /appointments`, `GET /appointments/Slots`, `GET /providers`, `GET /operatories`, `GET /appointmenttypes`, `GET /schedules` | P1-15, P1-16, P1-20 |
| Patients | **create only** | `POST /patients` | P1-16, P2-15 (P0-01 B4: new patients only; existing records are never updated) |
| Appointments | create, update | `POST /appointments`, `PUT /appointments/{AptNum}` (reschedule) | P1-16 |
| Comm | update, **limited to** Break and Confirm | `PUT /appointments/{AptNum}/Break` (cancel: sends it to the Unscheduled List), `PUT /appointments/{AptNum}/Confirm` | P1-16, P4-04 |
| Payments, PayPlans, Insurance, InsuranceSimple, Documents, Queries, Setup, ProcedureLogs, Enterprise, TextingASAP | **not requested** | - | - |

Notes:
- **Open Dental files Break and Confirm under Comm**, not Appointments (D2). DECISIONS #62 had said "no Comm"; #312 corrects it. Cancelling with `PUT /appointments` and `AptStatus=Broken` would avoid Comm, but skips the Unscheduled List and CommLog behaviour that staff expect.
- Setup GETs (providers, operatories, appointment types, schedules) are GET methods, so Read All covers them (D2: Read All is "All GET methods"). The spec's Verify question is answered; no Setup group is needed.
- API permissions "do not restrict the API from making changes" such as Open Dental's date restrictions (D2). Our code enforces clinic rules itself (P1-19, P2-08).

## 3. Fees, rate limits and versions
**Fees** (D2; prices last changed September 2020, per Open Dental). Per **location** per month, paid by us, from when a key is assigned and enabled until it is disabled ("billing stops automatically"):

| Tier | What | Throttle (Remote) |
|---|---|---|
| Free | Read All only | 1 request per 5 s |
| $15 | Comm, Documents, InsuranceSimple, Setup, Queries | 1 per s |
| **$30** | All except Payments, PayPlans and Special. **Our set (Patients and Appointments are not in the $15 tier)** | 1 per s |
| $35 | All except Special | 1 per s |
| Enterprise* (special) | Extra; lowers the Remote throttle to 500 ms, and lists to 1000 | 500 ms |

Expected cost: **$30 per location per month**: our test database (B), if billed (Verify, question in §6), plus each clinic. The sponsor approves before the request is sent.

**Rate limits and errors** (D3). P1-15 must build to these:
- **Throttle:** 1 request per second per **customer key** (any permission beyond Read All), including the request's own run time.
- Requests for one customer key are **processed one after another**; throttling is per customer key, not per developer key.
- Too many queued → **429** with `Retry-After`.
- A request running more than 60 s → **504**.
- Other statuses: 200, 201, 400 (also "version too low" and network problems at the office), 401, 404, 410.
- Lists return at most **100 items**. Page with `Limit` and `Offset` until fewer than 100 come back.
- Open Dental may suspend keys for "excessive requests" (D3).

**Versions** (D4, D6–D8): the office's version must be at least the version that added a method; otherwise the API returns 400. The clinic runs **24.3** (P0-01 B1).

| Method we use | Added in | OK on 24.3? |
|---|---|---|
| Remote API itself | 21.1 | Yes |
| `GET /patients/Simple` | 21.2 | Yes |
| `POST /patients` | 21.1 | Yes |
| `GET`/`POST`/`PUT /appointments`, `GET /appointments/Slots` | 21.1 | Yes |
| `PUT /appointments/{AptNum}/Break` | 21.3 | Yes |
| `GET /providers` (list) | 21.1 | Yes |
| `GET /providers/{ProvNum}` (single) | 24.4.17 | **No:** use the list |
| `GET /operatories` | 21.1 | Yes |
| `GET /appointmenttypes` (list) | 22.4.10 | Yes |
| `GET /appointmenttypes/{num}` (single) | 25.4.35 | **No:** use the list |
| `GET /schedules` | 22.1 | Yes |
| `GET /appointments?AptStatus=…` filter | 22.4.28 | Yes |

## 4. Keys and secrets
**Now (local-first, DECISIONS #302).** A git-ignored `.env` at the repo root, filled in by the developer in their own terminal (template: [`.env.example`](../../.env.example)):

| Variable | Value |
|---|---|
| `OPEN_DENTAL_BASE_URL` | `https://api.opendental.com/api/v1` |
| `OD_DEVELOPER_KEY` | The developer key: today the **published test key** from the apisetup page (D1); our own key once issued |
| `OD_CUSTOMER_KEY` | The customer key of the target database: today the published hosted-test customer key |
| `OD_TARGET` | `hosted` or `testdb` (the seed script requires `testdb`) |

**Later (cloud, when hosting exists).** The spec's Secret Manager design is unchanged:

| Secret | Project(s) | Value | Who can read |
|---|---|---|---|
| `od-developer-key` | dev, staging, prod | Our developer key (one secret per project) | That project's backend runtime SA (P1-05); tech lead via break-glass |
| `od-customer-key-testdb` | dev, staging | Customer key of test database (B) | Backend SA in dev/staging; CI SA (P1-06) |
| `od-customer-key-hosted-test` | dev | The published hosted-test key | Developers (it is public) |
| `od-customer-key-<clinic_slug>` | **prod only** | The clinic's customer key | Prod backend SA only. **First version only after the clinic BAA record says SIGNED** |

**Rules:**
- Key values never go in code, docs, `.env.example`, logs, CI output, issues, chat or the frontend. The LLM never sees them.
- Check: `git grep -n "ODFHIR "` finds only the placeholder `ODFHIR {DeveloperKey}/{CustomerKey}`.
- **A key is exposed:** disable it in the portal (or ask the clinic to), generate a new one, update the secret, and record a security event (R12, P5-12).

## 5. Customer keys (no values)
| Location | Environment | Status | Created | Enabled by | Notes |
|---|---|---|---|---|---|
| Open Dental hosted test database | dev (local) | **Read-only use planned** (smoke test deferred) | Published by Open Dental | Open Dental | Public and shared; never write to it (DECISIONS #313) |
| Test database (B) | dev, staging, CI | **Pending** | - | - | Needs our developer key and a place to run (B) |
| Example Dental (`example-dental`) | prod only | **Pending: blocked** | - | Jordan Example, OD admin (P0-01 B2) | Generate only after our developer key exists; create the prod secret only after [the clinic BAA record](../compliance/baa-clinic-example-dental.md) says SIGNED. Never in dev or staging. Give the key to the clinic by password-manager share or phone, not plain email |

## 6. Developer-key request (draft, not sent)
Owner: **Riley Tech** (tech lead) as portal owner, with a shared company mailbox, not a personal one. **Send after:**
- the sponsor (Morgan Lead) approves the fee (§3);
- the company details are filled in.

The required fields follow D1.

> **To:** vendor.relations@opendental.com
> **Subject:** API developer portal access request: [Company name]
>
> Hello,
>
> We would like Developer Portal access for the Open Dental API.
>
> - **Product/integration owner (company name):** [Company legal name]
> - **Contact phone number:** [company phone]
> - **Email address for long-term billing:** [billing@company domain] (shared mailbox)
> - **Physical mailing address for long-term billing:** [company address]
> - **3rd-party developer name / email:** none (built in-house)
> - **API resources and permissions:**
>   - Read All: read (patients, appointments, slots, providers, operatories, appointment types, schedules)
>   - Patients: **create only** (`POST /patients`); we do not update existing patient records
>   - Appointments: create and update (`POST /appointments`, `PUT /appointments`)
>   - Comm: update, **only** `PUT /appointments/{AptNum}/Break` and `PUT /appointments/{AptNum}/Confirm`
>   - No other permissions.
> - **Description of the application:** A website receptionist for dental offices. Patients use a chat or voice widget on the office's website to book, reschedule or cancel appointments; the system looks up or creates the patient and writes the appointment through the Remote API after the patient confirms. Office staff handle anything the system can't resolve. We sign a BAA with each office before using its key.
>
> Questions:
> 1. Which pricing tier applies to this permission set? We expect $30 per location.
> 2. Is a developer-owned test location billed?
> 3. May a developer run its own test installation of Open Dental with the eConnector (synthetic data only), and on what licensing terms?
> 4. Is the Enterprise throttle (500 ms) available to us later, and at what price?
> 5. Can the Comm permission be limited to Break and Confirm for our key, or is it granted as a whole group?
>
> Thank you,
> [Name], [Title]

**Answers (record here when they arrive):** pending.

## 7. Notes from the published hosted test database
The hosted test database is **public and shared**: anyone with the published credentials can read and change it. Its data must be treated as untrusted and possibly realistic-looking, so:
- we only read;
- outputs keep counts and IDs only;
- nothing from it is copied into this repository (DECISIONS #313).

## 8. Smoke test and rate-limit results
Command: `set -a; . ./.env; set +a; python3 scripts/open_dental/smoke_test.py --target hosted`.

**Hosted test database (A):** **pending: deferred by the user** (2026-11-26). The script is ready and tested offline against a mock server (13 tests). To run it later:
1. Copy `.env.example` to `.env` (git-ignored).
2. Paste the two halves of the published test credentials from the apisetup page (D1) into `OD_DEVELOPER_KEY` and `OD_CUSTOMER_KEY`.
3. Run the command above.
4. Record here: the statuses, counts, the wrong-key status, the latencies and the 429 behaviour.

P1-15 needs the wrong-key status and the measured rate; until then it uses D3's documented values (401, 1 request per second, 429 with `Retry-After`).

**Test database (B):** pending: (B) doesn't exist yet.
