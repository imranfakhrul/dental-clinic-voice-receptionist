# Spec Delta

## Purpose

Defines how callback cases reach the clinic admin by email: the route and sender, the content modes and templates, the config keys and their load-time rules, the recipient readiness check, and the logging limits.

## ADDED Requirements

### Requirement: Link-only is the default content mode
Callback emails SHALL use the `link_only` mode unless the clinic's config sets `full_details` and names a written compliance-advisor approval. A `link_only` email SHALL contain no patient field. Its subject SHALL contain only the urgency and the case ID.

#### Scenario: Full details without approval
- **WHEN** a clinic's `callback.email_mode` is `full_details` and `callback.full_details_approval` is empty
- **THEN** the email is sent as `link_only`, and a warning without PHI is logged

### Requirement: Case IDs are opaque
The case ID in an email and its link SHALL be random. It SHALL NOT be a PatNum, a phone number, or derived from patient data.

#### Scenario: Link in a callback email
- **WHEN** a callback email is rendered
- **THEN** its link is `{ADMIN_CONSOLE_BASE_URL}/cases/{case_id}` with a random case ID, and opening it requires login

### Requirement: Mail only to ready, clinic-controlled recipients
Callback emails SHALL go only to addresses on a clinic-controlled domain that passed the readiness check. Consumer webmail addresses SHALL be refused. Delivery to a recipient domain SHALL require TLS, so mail to a server without TLS bounces.

#### Scenario: Consumer address
- **WHEN** a clinic's `callback.admin_emails` contains a `gmail.com` address
- **THEN** the config is rejected at load time

### Requirement: Email carries PHI only under a signed BAA
No real callback email SHALL be sent until the email route's BAA (Google Workspace) is accepted and recorded. Until then, only synthetic test emails SHALL be sent, and only to a local mail catcher or team mailboxes.

#### Scenario: Workspace BAA not accepted
- **WHEN** the Workspace BAA record says NOT ACCEPTED
- **THEN** no callback email with real data is sent, and cases stay visible only in the admin console

### Requirement: Keyless sending as one sender
The backend SHALL send only as the dedicated sender mailbox, with the narrowest Gmail send permission. It SHALL NOT use a stored service-account key.

#### Scenario: Send permission
- **WHEN** the backend obtains credentials to send a callback email
- **THEN** they allow only sending as the dedicated sender, and no key file exists

### Requirement: No PHI in email logs
Email sending SHALL log only the case ID, the provider message ID, the status, the timestamp and the error code. It SHALL never log email bodies or recipient-specific patient data.

#### Scenario: Failed send
- **WHEN** sending a callback email fails
- **THEN** the log line holds the case ID, status and error code, and no body text
