# Spec Delta

## Purpose

Defines which provider carries each patient-messaging channel, the BAA gate each provider must pass before real PHI, how test accounts are used, and the integration facts that messaging code relies on.

## ADDED Requirements

### Requirement: Providers compared with dated evidence
The provider comparison SHALL score at least three providers per channel allowed by `messaging_policy.yaml` against the nine criteria of task P0-07 §6. Every cell SHALL hold yes, no or partial with an evidence link and the date checked. A provider that fails a Must criterion SHALL show which one.

#### Scenario: Incomplete row
- **WHEN** a provider row has a cell without a value or an evidence link
- **THEN** the comparison is incomplete and the task is not done

### Requirement: BAA coverage is judged per product and per use
Criterion 1 (BAA covers the product) SHALL be judged on the provider's published coverage list for the exact product, never on a verbal statement. It SHALL be a Must for any use with real PHI. For testing with synthetic data only, a provider MAY be chosen without that coverage, and the comparison SHALL say so.

#### Scenario: WhatsApp product not on any coverage list
- **WHEN** no WhatsApp provider's published BAA coverage names WhatsApp
- **THEN** WhatsApp may be used for testing only, and production WhatsApp stays behind the `phi_gate` in `messaging_policy.yaml`

### Requirement: BAA records follow the P0-05 format
Each chosen provider SHALL have a BAA record in `docs/compliance/` with the P0-05 fields plus the covered products relied on, the edition or plan required, and the channels allowed by P0-07a with the policy's decision version. A BAA that isn't signed SHALL be recorded as NOT ACCEPTED, and no PHI SHALL reach that provider.

#### Scenario: Paper BAA
- **WHEN** a provider's BAA hasn't been signed by both parties
- **THEN** its record shows NOT ACCEPTED, and the vendor matrix (P0-10) treats the provider as not allowed to receive PHI

### Requirement: Test accounts carry synthetic content only
A provider test account SHALL send only synthetic content, and only to the team's own phones. Its credentials and phone numbers SHALL be kept outside the repository and SHALL NOT appear in commits, issues or logs.

#### Scenario: Test send
- **WHEN** a test message is sent from the test account
- **THEN** it goes to a team phone with fake content, and the repository contains neither the token nor the phone number

### Requirement: Integration facts are proven before use
The comparison SHALL include an "Integration facts" section for the chosen providers: product, API base and SDK, webhook signature method, status values, opt-out behaviour, sender type and registration steps, and the names of the secrets needed. For the active testing channel, one test message and one signed delivery webhook SHALL have been received and the signature verified before the facts are marked proven.

#### Scenario: Webhook signature check
- **WHEN** a delivery webhook arrives at the test receiver
- **THEN** the receiver verifies its signature with the documented method and reports pass or fail without printing message content or phone numbers
