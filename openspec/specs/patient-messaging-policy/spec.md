# patient-messaging-policy Specification

## Purpose

Defines where patient messages may go and what they may contain: the allowed channel for each message type (booking confirmation, reminder, reschedule notice, cancel notice), the fields each may carry, the fields no message may ever carry, and the consent rules, as decided in writing by the compliance advisor and the project sponsor and encoded in a machine-readable policy that messaging code enforces.

## Requirements

### Requirement: A signed, sourced channel decision
`docs/compliance/patient-messaging-decision.md` SHALL record the question, dated facts each with a URL and a quote of at most one sentence, the content of each message type, a comparison of options A–D, a written answer to every advisor question, and the decision per message type signed by the compliance advisor and the project sponsor, with the date the clinic SME was informed.

#### Scenario: Fact without a source
- **WHEN** the memo states a fact about a vendor's terms or BAA coverage
- **THEN** the fact has a URL, a date checked and an entry in the source record

### Requirement: Provider BAA coverage is checked per channel
For every channel considered, the memo SHALL record the published BAA position of at least three providers, naming exactly which of their products the BAA covers. A channel SHALL NOT be allowed to carry PHI unless at least one provider's documented BAA covers that product.

#### Scenario: No BAA covers a channel
- **WHEN** no provider's published BAA covers a channel
- **THEN** that channel is not allowed to carry PHI, and the decision picks another option

### Requirement: Testing uses WhatsApp with synthetic data only
While the system is in testing, WhatsApp SHALL be the active channel. It SHALL carry synthetic data only, and SHALL send only to the team's own test numbers. SMS SHALL be integrated but switched off. No real patient data SHALL be sent on any channel during testing.

#### Scenario: Test reminder
- **WHEN** a reminder is sent in a test environment
- **THEN** it goes by WhatsApp to a team test number and contains only synthetic data

### Requirement: Real PHI only on a channel with a BAA chain
A channel SHALL carry real PHI only if a signed BAA chain covers every vendor in its path. In production each clinic SHALL choose SMS or WhatsApp. WhatsApp SHALL carry real PHI only after BAAs with Meta and the WhatsApp provider are signed and recorded; until then a clinic that chooses WhatsApp SHALL use SMS or wait.

#### Scenario: Go-live with real patients
- **WHEN** a clinic that chose WhatsApp goes live and no signed Meta BAA is on file
- **THEN** its messages go by SMS through a provider with a BAA, not WhatsApp

### Requirement: Machine-readable content policy
`docs/compliance/messaging_policy.yaml` SHALL match the decision exactly. It SHALL name the testing channel and the channels a clinic may choose in production. The testing channel SHALL be integrated and enabled. A production channel not yet allowed with PHI SHALL name the gate that allows it and the fallback channel, and the fallback SHALL be allowed with PHI.

#### Scenario: Policy check
- **WHEN** the policy check script runs on the policy file
- **THEN** it passes only if those channel rules hold

### Requirement: Never-allowed fields
No field in any message type SHALL appear in `never_allowed_fields`. That list SHALL include at least last name, date of birth, reason, procedure, symptoms, provider name, insurance and the Open Dental IDs.

#### Scenario: Forbidden field in a message type
- **WHEN** a message type lists `procedure` among its fields
- **THEN** the policy check fails

### Requirement: Messaging code enforces the policy
Messaging code (P4-01 and later) SHALL refuse to send a message type whose channel isn't allowed, and SHALL refuse any template variable that isn't in that type's `fields` or that appears in `never_allowed_fields`.

#### Scenario: Forbidden template variable
- **WHEN** a template for a reminder uses the variable `procedure`
- **THEN** the message is refused and not sent

### Requirement: Consent before any patient message
No patient message SHALL be sent without the patient's consent for that channel. A risk notice SHALL be part of the consent when the policy requires it. The consent wording is owned by P4-02.

#### Scenario: No consent
- **WHEN** a patient declines messages
- **THEN** no confirmation or reminder is sent, and the booking itself is unaffected

### Requirement: Scope changes are recorded
Any change to the plan's messaging channels (plan §2 #9–10 and §4.7) SHALL be recorded in DECISIONS.md with the tasks that need re-scoping named.

#### Scenario: Two channels instead of one
- **WHEN** the decision keeps WhatsApp for testing and adds SMS for real patients
- **THEN** a DECISIONS row records it and names P0-07, P0-15 and the P4 messaging tasks for re-scoping
