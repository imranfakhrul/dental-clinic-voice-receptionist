# architecture-phi-flows Specification

## Purpose

Define the agreed system architecture that all later phases build on, and make the PHI flow table the single source of truth for where PHI may travel, with which fields, to which vendor and under which BAA, kept consistent with the flow designs, the vendor matrix and the allowed Google services by an automated check.

## Requirements

### Requirement: Architecture documents
The repository SHALL contain `docs/architecture/` with a README (reading order, change rules, deployment views), a level-1 context view, a level-2 container view with a module responsibilities table, a PHI flow document, a network map and four sequence diagrams (voice turn, booking, callback, reminder), with diagrams in Mermaid so they render on GitHub; tasks SHALL be cited by their survivor IDs.

#### Scenario: Diagrams render
- **WHEN** a reviewer opens any file in `docs/architecture/` on GitHub
- **THEN** each Mermaid block renders as a diagram

#### Scenario: Merged task ID cited
- **WHEN** a document names a task that was merged into another
- **THEN** it names the survivor task (optionally with "was <old ID>")

### Requirement: PHI flow table is the source of truth
`docs/architecture/phi-flows.md` SHALL list every hop that PHI may take, each with an ID, from and to, the exact PHI fields, purpose, the `vendors.yaml` vendor id (or "our system"), the BAA that covers it, protections, environments and owner tasks; where the trust-boundary diagram and the table disagree, the table SHALL win, and the risk assessment (P0-11) and the clinic BAA Annex A (P0-09) SHALL point to or match the table.

#### Scenario: Hop without a BAA
- **WHEN** a flow row sends PHI to a vendor
- **THEN** the row names that vendor's BAA and its current status

#### Scenario: Risk assessment flows
- **WHEN** a reader opens the data-flow section of the risk assessment
- **THEN** it links to `docs/architecture/phi-flows.md` instead of keeping its own flow list

### Requirement: Coverage of PHI slots, vendors and services
Every PHI slot listed in `docs/flows/overview.md` SHALL appear in at least one flow row; every vendor in `vendors.yaml` with `phi: yes` or `conditional` SHALL appear in at least one flow row; every vendor id in a flow row SHALL exist in `vendors.yaml`; every Google Cloud service drawn in the architecture diagrams SHALL be in `infra/org/allowed_services.yaml`; an automated check SHALL report any gap and exit non-zero.

#### Scenario: New PHI slot without a flow
- **WHEN** a PHI slot is added to `docs/flows/overview.md` and no flow row lists it
- **THEN** the coverage check fails and names the slot

#### Scenario: Unknown vendor in a flow
- **WHEN** a flow row names a vendor id not in `vendors.yaml`
- **THEN** the coverage check fails and names the vendor id

#### Scenario: Service not allowed
- **WHEN** a diagram names a Google Cloud service missing from `allowed_services.yaml`
- **THEN** the coverage check fails and names the service

### Requirement: Paths that must never carry PHI
The architecture SHALL state that no PHI goes into URLs, logs, metrics, analytics, error responses or task-queue payloads (IDs only, re-fetched by the handler), and that the Gemini Developer API path exists only on developer machines with synthetic data, drawn outside the PHI boundary; Gemini SHALL be reached only through the project's own Vertex AI provider, never through a third-party library's API-key path.

#### Scenario: Task payload with a name
- **WHEN** a design proposes putting a patient name in a queued task payload
- **THEN** the flow table rule rejects it; the payload carries IDs and the handler re-fetches

#### Scenario: Library offers an API-key Gemini service
- **WHEN** a voice framework offers a Gemini service configured with an API key
- **THEN** the architecture forbids it in any cloud environment, and the LLM call goes through the project's provider

### Requirement: Network design and verified facts
`docs/architecture/network.md` SHALL describe projects, VPC and subnets, load-balancer-only ingress, egress, private access to the database and cache, Google API access through the restricted VIP, perimeters and admin access; each external fact marked "Verify" SHALL be either answered with the official page URL and the date read, or listed as an open question for the infrastructure task.

#### Scenario: Unanswered Verify item
- **WHEN** a "Verify" fact could not be confirmed from official docs
- **THEN** it is listed as an open question with its owner task

### Requirement: Sessions survive reconnects
The architecture SHALL state that a voice or chat connection can be cut (platform request timeout or instance loss) and that the client reconnects with its session token while the conversation state is restored from the session store, so no confirmed step is lost.

#### Scenario: Connection cut mid-conversation
- **WHEN** the WebSocket closes because of the request timeout or an instance restart
- **THEN** the sequence shows the client reconnecting and the orchestrator restoring state from the session store

### Requirement: Architecture decision records
`docs/adr/` SHALL contain an index of ADRs 0001–0006 and a template (title, status, date, context, options, decision, consequences, review triggers); ADRs whose decision holds on any hosting SHALL be Accepted, ADRs that depend on Google Cloud hosting SHALL be Accepted only on that condition and name the trigger that re-opens them, and the voice-framework ADR SHALL stay Proposed until the latency prototype.

#### Scenario: Hosting moves off Google Cloud
- **WHEN** the client chooses hosting other than Google Cloud
- **THEN** the conditional ADRs are re-opened per their review triggers, and the risk assessment is reviewed

### Requirement: Compliance review of the flow table
Any change that adds a PHI hop or a field to a hop SHALL update the flow table, `vendors.yaml` when a vendor is added, and the clinic BAA Annex A, and SHALL be reviewed by the compliance owner; the flow table path SHALL be listed for the compliance owners in the proposed code-owner entries.

#### Scenario: New field on an existing hop
- **WHEN** a pull request sends an extra PHI field to a vendor
- **THEN** the same pull request updates the flow table and Annex A, and the compliance owner reviews it
