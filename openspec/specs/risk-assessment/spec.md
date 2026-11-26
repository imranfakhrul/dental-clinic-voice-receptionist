# risk-assessment Specification

## Purpose

Keep a documented HIPAA security risk analysis of the ePHI our system handles: what is inventoried, how risks are scored, who owns each control, which gaps were decided, and when the analysis is reviewed again.

## Requirements

### Requirement: Every ePHI asset and PHI vendor is assessed
Every asset that stores, processes or transmits ePHI SHALL appear in at least one data flow and at least one risk, and every vendor in `vendors.yaml` with `phi` "yes" or "conditional" SHALL appear in at least one risk.

#### Scenario: Vendor added
- **WHEN** a vendor with `phi: "yes"` is added to `vendors.yaml`
- **THEN** the register gets a risk naming it before the next review is signed off

#### Scenario: Check run
- **WHEN** the register check runs on v1
- **THEN** it reports no PHI vendor without a risk

### Requirement: Risks are scored on fixed scales
Each risk SHALL have an inherent likelihood and impact on the 1–5 scales, a score L×I with its band (Low 1–4, Medium 5–9, High 10–16, Critical 20–25), and a residual score after planned controls.

#### Scenario: Disagreement on a score
- **WHEN** the team disagrees on a score
- **THEN** v1 uses the higher score and notes the disagreement in the row

### Requirement: High and Critical risks are owned
Every High or Critical risk SHALL name planned or existing controls whose task IDs exist as survivor tasks, and SHALL have a residual of Medium or lower, or a sponsor-signed entry in `accepted-risks.md`; a Critical risk SHALL NOT be accepted before real PHI.

#### Scenario: Merged task ID
- **WHEN** a control cites a task that was merged into another
- **THEN** the register check fails until the survivor ID is used

#### Scenario: No task can control a High risk
- **WHEN** no existing task can bring a High risk to Medium
- **THEN** it becomes a gap with a decision logged in DECISIONS.md, and can't stay open without one

### Requirement: Every Security Rule standard is covered
`safeguard-coverage.md` SHALL list each administrative, physical and technical standard with the risks and controls that address it, or a written reason it does not apply.

#### Scenario: Physical safeguards
- **WHEN** a physical standard is covered by Google's data centres under its BAA
- **THEN** the row says so and lists our team's own part (devices)

### Requirement: Status is honest
The assessment SHALL show what is planned versus in place, and SHALL NOT mark the vendor BAA legal review (R29) done or the assessment final until the review has actually happened.

#### Scenario: No counsel
- **WHEN** no vendor BAA is accepted and no counsel is engaged
- **THEN** each BAA record says the legal review is pending, and R29 stays open

### Requirement: The assessment is re-reviewed on triggers
The assessment SHALL be reviewed again when the P0-14 data-flow diagram lands, a vendor or Google API is added, a PHI field is added, before go-live, after any security incident, and at least yearly.

#### Scenario: New PHI field
- **WHEN** Annex A gains a data category
- **THEN** the asset inventory, flows and risks are updated in the same change
