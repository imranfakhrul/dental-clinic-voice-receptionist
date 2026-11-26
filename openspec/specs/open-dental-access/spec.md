# open-dental-access Specification

## Purpose

Define how the system and the team reach Open Dental: the Remote API with our developer key and one customer key per database, least-privilege permissions, the rate limits code must respect, which databases development may use, and how keys are kept out of code.

## Requirements

### Requirement: Development never touches a clinic's real data
Development and testing SHALL use only Open Dental's public hosted test database (read-only) or our own synthetic test database; a clinic's customer key SHALL NOT be used, or stored in any environment, until that clinic's BAA record says SIGNED, and then only in prod.

#### Scenario: Clinic key before the BAA
- **WHEN** the clinic BAA record says NOT SIGNED
- **THEN** no environment holds the clinic's customer key and no request is made to the clinic's database

#### Scenario: Copy of a clinic database proposed
- **WHEN** someone proposes testing against a copy of a clinic's real database
- **THEN** it is refused (DECISIONS #25)

### Requirement: Keys never enter the repository
Open Dental developer and customer keys SHALL live only in a secret store (a git-ignored local env file now, Secret Manager once cloud hosting exists), never in code, docs, logs, issues, chat or the frontend; the repository SHALL hold only placeholders.

#### Scenario: Repository scan
- **WHEN** the repository is searched for `ODFHIR ` followed by a key-like value
- **THEN** only placeholders are found

#### Scenario: Key exposed
- **WHEN** a key is exposed
- **THEN** it is disabled in the portal, replaced, and recorded as a security event (R12)

### Requirement: The public test database is read-only for us
Our tools SHALL only read from Open Dental's public hosted test database and SHALL NOT write any data to it.

#### Scenario: Seeding the hosted database
- **WHEN** the seed script is pointed at the hosted test database
- **THEN** it refuses and exits without sending a request

### Requirement: Smoke test output contains no patient details
The smoke test SHALL print only HTTP status codes, counts, IDs and timings, never names, dates of birth, phone numbers or addresses.

#### Scenario: Patients found
- **WHEN** a patient search returns rows
- **THEN** the output shows the count and PatNums only

### Requirement: Least-privilege permissions
The developer key request SHALL ask only for Read All, Patients create, Appointments create and update, and Comm update limited to breaking and confirming appointments (Open Dental puts `PUT /appointments/{AptNum}/Break` in the Comm group), and SHALL NOT ask for Payments, PayPlans, Insurance, Documents, Queries or Setup.

#### Scenario: Request drafted
- **WHEN** the vendor-relations email is drafted
- **THEN** its permission list matches this requirement exactly

### Requirement: Clients respect the rate limit
Code calling the Remote API SHALL send requests for one customer key one at a time at no more than the documented rate (1 per second with write permissions; 1 per 5 seconds with Read All only), and SHALL honour 429 `Retry-After`.

#### Scenario: 429 received
- **WHEN** the API answers 429 with `Retry-After`
- **THEN** the client waits that long before the next request to that customer key
