# patient-message-templates Specification

## Purpose

Define the patient message templates for confirmations, reminders and reschedule/cancel notices, the content rules that keep them within the messaging policy and free of sensitive details, the consent, HELP and STOP texts, and the guards on registering senders and sending test messages.

## Requirements

### Requirement: Templates as checked data
Patient message templates SHALL live in `docs/messaging/templates.yaml`, valid against `docs/messaging/templates.schema.json`, with one template for each of the four message types (booking confirmation, reminder, reschedule notice, cancel notice) on every channel the policy integrates, and with the date and time formats used to render them.

#### Scenario: Missing message type
- **WHEN** a channel has templates for only three of the four message types
- **THEN** the validator reports an error for that channel

#### Scenario: Schema violation
- **WHEN** a template lacks its example values or has an unknown field
- **THEN** the validator reports a schema error and exits non-zero

### Requirement: Only policy fields, never sensitive fields
Every variable in a template SHALL be listed for its message type in `messaging_policy.yaml`, no variable SHALL be in `never_allowed_fields`, every `{variable}` in the body SHALL be declared and every declared variable used, and the template's `policy_version` SHALL equal the policy's `decision_version`.

#### Scenario: Reason added to a template
- **WHEN** a template body uses `{reason}`
- **THEN** the validator reports an error and exits non-zero

#### Scenario: Policy version changed
- **WHEN** the policy's `decision_version` changes and the templates are not updated
- **THEN** the validator reports a version mismatch

### Requirement: No visit details in the wording
The rendered example of every template SHALL contain none of the denylisted service, symptom, payment or provider words (whole words, case-insensitive), except inside the clinic name.

#### Scenario: Service word in the body
- **WHEN** a body contains the word "cleaning"
- **THEN** the validator reports an error

#### Scenario: Word only in the clinic name
- **WHEN** the word appears only inside the example clinic name
- **THEN** no error is reported

### Requirement: Channel and format rules
A template's channel SHALL be a channel the policy integrates; every template SHALL carry opt-out text when the policy requires it; SMS templates SHALL render to GSM-7 text of at most two segments (a warning above one); WhatsApp templates SHALL be utility templates whose body neither starts nor ends with a variable.

#### Scenario: Non-GSM character in SMS
- **WHEN** an SMS body contains a curly apostrophe
- **THEN** the validator reports an error

#### Scenario: WhatsApp body ends with a variable
- **WHEN** a WhatsApp body ends with `{clinic_phone}`
- **THEN** the validator reports an error

#### Scenario: Missing opt-out text
- **WHEN** the policy requires opt-out text and a template has none
- **THEN** the validator reports an error

### Requirement: PHI-free system replies
STOP, START, HELP and auto-reply texts SHALL contain only the clinic name and clinic phone as variables.

#### Scenario: Name in a system reply
- **WHEN** a system reply uses `{first_name}`
- **THEN** the validator reports an error

### Requirement: Consent and website texts
The repository SHALL contain the consent checkbox text (unchecked by default, naming message types, frequency, rates, STOP and HELP, and stating consent is not required to book, with a slot for the policy's risk notice), the HELP and STOP texts, and the clinic website texts for an SMS terms page and a privacy paragraph.

#### Scenario: Risk notice required
- **WHEN** the policy sets `risk_notice_required: true`
- **THEN** the consent text has a marked place for the advisor-approved risk sentence

### Requirement: Registration record without secrets
Each clinic SHALL have a registration record listing channel, provider, sender IDs, template IDs and statuses with dates; it SHALL never contain API keys, tokens or real patient data.

#### Scenario: Registration not yet possible
- **WHEN** a registration step can't be submitted (no provider account or missing business details)
- **THEN** the record shows the step as not submitted, with the blocker and its owner

### Requirement: Guarded live steps
Scripts that submit templates or send test messages SHALL default to a dry run or refuse without explicit credentials from the environment, SHALL send only the template's example values to the configured team test number, and SHALL print only IDs, names and statuses, never tokens, phone numbers or rendered bodies with other values.

#### Scenario: Run without credentials
- **WHEN** the submission script runs without the Meta token and account ID
- **THEN** it performs a dry run and makes no network call

#### Scenario: Non-example values
- **WHEN** a test send is asked to use values other than the template's example
- **THEN** it refuses
