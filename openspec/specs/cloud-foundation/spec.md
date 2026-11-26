# cloud-foundation Specification

## Purpose

Defines the Google Cloud foundation the system runs on: one project per environment with fixed PHI rules, a protected Terraform state bucket, cost alerts, notification contacts, the access-control baseline, the recorded IDs, and the BAA status gate that keeps PHI out until Google's HIPAA BAA is accepted.

## Requirements

### Requirement: One project per environment
The system SHALL run in four Google Cloud projects, `<prefix>-dev`, `<prefix>-staging`, `<prefix>-prod` and `<prefix>-ops`. Each SHALL carry the labels `env=<env>` and `system=dental-ai` and SHALL be linked to the billing account. The prefix SHALL be the same for all four.

#### Scenario: Projects exist and are billed
- **WHEN** the projects with label `system=dental-ai` are listed
- **THEN** exactly the four environment projects are returned, and each has billing enabled

### Requirement: Real PHI only in prod, and only after every gate
Real PHI SHALL never be stored or processed in `dev`, `staging` or `ops`. It SHALL enter `prod` only after the Google Cloud BAA is accepted, the covered-products restriction (P0-06) is in place, the clinic BAA (P0-09) is signed and the vendor matrix (P0-10) shows it. Until then, all projects SHALL use synthetic data only.

#### Scenario: BAA not accepted
- **WHEN** the BAA record has status `NOT ACCEPTED`
- **THEN** no project may receive real PHI, and tests use synthetic data only

### Requirement: The BAA status is recorded and is the gate
`docs/compliance/baa-google-cloud.md` SHALL record the BAA status. While it isn't accepted, the status SHALL be `NOT ACCEPTED` and the acceptor, date, version and scope SHALL be empty. When it is accepted, all of those SHALL be filled in, together with the authority confirmation and a saved copy reference. A BAA SHALL never be recorded as accepted unless the acceptance actually happened.

#### Scenario: Paper-only BAA
- **WHEN** the BAA hasn't been accepted in the console
- **THEN** the record says `NOT ACCEPTED` and lists the steps and the person needed to accept it

### Requirement: Covered-products snapshot is dated and complete
The BAA record SHALL contain a snapshot, dated and with a source link, of Google's HIPAA supported-services list for every service in plan §3.2. The entry that covers our Gemini calls and the text of every footnote SHALL be resolved, with no remaining "Verify". A service that isn't listed SHALL be marked "not covered" and logged in DECISIONS.md.

#### Scenario: Service not on the list
- **WHEN** a planned service doesn't appear on Google's list
- **THEN** the snapshot marks it "not covered" and a DECISIONS row says it must not process PHI

### Requirement: Terraform state bucket is protected
The bucket `gs://<prefix>-ops-tfstate` SHALL exist in `<prefix>-ops`, in location `US`, with object versioning on, uniform bucket-level access, and public access prevention enforced.

#### Scenario: Bucket settings
- **WHEN** the bucket is described
- **THEN** versioning is enabled and public access prevention is `enforced`

### Requirement: Spending is watched
A monthly budget SHALL cover the four projects, with alert thresholds at 50%, 90% and 100%.

#### Scenario: Budget present
- **WHEN** the budgets on the billing account are listed
- **THEN** a `dental-ai monthly` budget with the three thresholds is returned

### Requirement: Google can reach us
Essential contacts for the security, technical, billing, legal and suspension categories SHALL be set, at organization level when an organization exists, otherwise on each of the four projects.

#### Scenario: Contacts per project
- **WHEN** the essential contacts of any of the four projects are listed
- **THEN** all five categories are covered

### Requirement: Access-control baseline
No service-account keys SHALL be created. When an organization exists, IAM SHALL be granted only to groups, with no individual `user:` bindings and no domain-wide project-creator or billing-creator grants. Two break-glass super-admins with hardware keys SHALL exist, and 2-step verification SHALL be enforced. While there is no organization, the only individual binding allowed is the account owner's, and the org-level controls SHALL be listed as pending before real PHI.

#### Scenario: Personal-account setup
- **WHEN** the setup runs without an organization
- **THEN** the project IAM has only the owner account, and the pending list names the organization, folder, groups, org IAM and break-glass admins

### Requirement: IDs are recorded without personal data
`infra/bootstrap/foundation.yaml` SHALL record the project IDs and numbers, the state bucket, the budget amount and the BAA record path. Because the repository is public, it SHALL NOT contain personal email addresses, and the billing account ID SHALL be masked to its last six characters. Org, folder and group fields SHALL be `null` while there is no organization.

#### Scenario: Public repo scan
- **WHEN** the committed infra and compliance files are scanned
- **THEN** no personal email address or full billing account ID is found
