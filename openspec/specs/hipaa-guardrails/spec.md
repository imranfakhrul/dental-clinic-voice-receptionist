# hipaa-guardrails Specification

## Purpose

Defines the technical guardrails that keep PHI inside HIPAA-covered Google Cloud services in US locations: one allow-list of services, US-only locations, baseline security constraints, VPC Service Controls perimeters per environment, no Gemini Developer API keys, Speech-to-Text data logging off, and the dated evidence and repeatable tests that prove each control.

## Requirements

### Requirement: One allow-list of services
`infra/org/allowed_services.yaml` SHALL be the single list of APIs allowed in the dental-ai projects. Each entry SHALL record its purpose and, from Google's sources with a check date, whether it is HIPAA-covered, controllable by the service-usage constraint and restrictable by VPC-SC. No entry SHALL keep the value `verify`. An API that isn't HIPAA-covered SHALL be dropped unless a DECISIONS row records that it never handles PHI.

#### Scenario: Non-covered API proposed
- **WHEN** a needed API is not on Google's HIPAA covered list
- **THEN** it is left out of the allow-list for PHI projects, or kept only with a DECISIONS exception proving it never handles PHI

### Requirement: Only allowed APIs are enabled
Every API enabled in the dental-ai projects SHALL be on the allow-list, or be one that Google always keeps enabled. Adding an API SHALL require a change to `allowed_services.yaml` plus a DECISIONS row. Where the service-usage constraint can be applied, it SHALL refuse every other API.

#### Scenario: Default APIs found
- **WHEN** a project has an enabled API that isn't on the allow-list
- **THEN** it is disabled, or recorded with the reason it can't be

### Requirement: No Gemini Developer API
Gemini SHALL be called only through Vertex AI. The Gemini Developer API (`generativelanguage.googleapis.com`) SHALL NOT be enabled in any project, SHALL be denied by policy wherever policy is available, and no API keys SHALL exist in the four projects.

#### Scenario: API-key check
- **WHEN** the API keys and enabled APIs of the four projects are listed
- **THEN** no key exists and the Gemini Developer API is not enabled

### Requirement: US-only locations
New resources SHALL be created only in US locations. Where the location constraint can be applied, creating a resource outside the US SHALL fail. Global endpoints SHALL be avoided for PHI; P0-13 picks a US regional Vertex AI endpoint.

#### Scenario: Non-US resource
- **WHEN** a bucket is requested in location `EU` in a project with the location constraint
- **THEN** creation fails with a resource-locations error

### Requirement: Baseline security constraints
Where org policy is available, these SHALL be enforced: no service-account key creation, IAM members limited to the company domain, no automatic Editor grants to default service accounts, uniform bucket-level access, public access prevention on buckets, no Cloud SQL public IP, and no VM external IPs.

#### Scenario: Service-account key
- **WHEN** someone tries to create a service-account key under the key-creation constraint
- **THEN** the request is refused

### Requirement: Perimeter per environment
When an organization exists, each of dev, staging and prod SHALL be in its own VPC-SC perimeter that restricts the allow-listed services VPC-SC supports. Prod SHALL be enforced; dev and staging SHALL start in dry-run until P1-02 enforces them. Ops SHALL be in no perimeter. An admin ingress rule SHALL keep administrators able to manage prod.

#### Scenario: Data leaves prod
- **WHEN** an identity outside the prod perimeter, not covered by the ingress rule, reads a prod bucket
- **THEN** VPC-SC refuses the request

### Requirement: Speech-to-Text data logging off
Speech-to-Text data logging SHALL be off in all four projects. The state SHALL be recorded with a date, or recorded as "API not enabled" and checked again when P3-03 enables the API.

#### Scenario: API not yet enabled
- **WHEN** the Speech-to-Text API isn't enabled in a project
- **THEN** the record says logging cannot be on and schedules a re-check for P3-03

### Requirement: Guardrails as validated code
The org policies, access policy and perimeters SHALL be defined as Terraform in `infra/org/`, using the allow-list file as the source of allowed APIs. The code SHALL pass `terraform fmt -check` and `terraform validate`. It SHALL be applied only after a reviewed plan, by a security admin, with state in the ops state bucket.

#### Scenario: Validation without an organization
- **WHEN** no organization or state bucket exists
- **THEN** the code is validated against example IDs, is not applied, and is listed as pending before real PHI

### Requirement: Evidence and repeatable tests
`docs/compliance/hipaa-controls.md` SHALL record which controls are enforced, pending or replaced by a project-level substitute, each check with its date and result, and the Assured Workloads decision. `docs/runbooks/org-guardrails-tests.md` SHALL hold the negative and positive tests to re-run after any guardrail change. A negative test SHALL be recorded as passed only if the request was refused for the stated reason.

#### Scenario: Control not yet possible
- **WHEN** a control needs an organization that doesn't exist yet
- **THEN** the evidence file marks it pending, names what it waits for, and the PHI gate stays closed
