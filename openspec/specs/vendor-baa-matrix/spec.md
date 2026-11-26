# vendor-baa-matrix Specification

## Purpose

Keep one checked record of every third party that may receive data from our system or team, with its PHI flag and BAA status, and compute the PHI gate that says whether real PHI may enter production.

## Requirements

### Requirement: Every vendor has a validated row
Every third party that receives, stores or can access data from our system or our team's work SHALL have a row in `docs/compliance/vendors.yaml`, and the file SHALL validate against `vendors.schema.json` with unique vendor IDs and clinic slugs.

#### Scenario: Duplicate ID
- **WHEN** two vendor rows share the same `id`
- **THEN** the checker exits 1 and names the duplicate ID and rule C2

#### Scenario: Valid file
- **WHEN** the committed `vendors.yaml` is checked
- **THEN** the checker exits 0

### Requirement: PHI flags match BAA status
A vendor with `phi` "yes" or "conditional" SHALL NOT have BAA status `not_required`; a vendor with `phi` "no" SHALL name its `no_phi_control`; a conditional vendor SHALL state its `phi_condition`; and a `signed` BAA SHALL have a date and an existing record file.

#### Scenario: PHI vendor without BAA
- **WHEN** a row has `phi: "yes"` and `baa.status: not_required`
- **THEN** the checker exits 1 naming the vendor and rule C4

#### Scenario: Signed without record
- **WHEN** a row says `signed` but its record file doesn't exist
- **THEN** the checker exits 1 naming the vendor and rule C3

### Requirement: The PHI gate is computed, not asserted
`check_vendors.py --gate` SHALL print GATE OPEN (exit 0) only when every gate item is done with existing evidence, every prod vendor with `phi: "yes"` is signed, at least one clinic is signed, and every prod API in the product list is HIPAA-covered or has a recorded exception; otherwise it SHALL print GATE CLOSED (exit 2) with each reason.

#### Scenario: Today
- **WHEN** `--gate` runs on the committed file
- **THEN** it prints GATE CLOSED and lists the pending BAAs and gate items

#### Scenario: Everything done
- **WHEN** a test fixture has all items done and all PHI vendors and one clinic signed with existing records
- **THEN** it prints GATE OPEN and exits 0

#### Scenario: Product list missing
- **WHEN** the `product_list` file is missing
- **THEN** the checker warns and the gate is CLOSED

### Requirement: Conditional vendors block only themselves
A vendor with `phi: "conditional"` and an unsigned BAA SHALL NOT close the global gate, and the rendered matrix SHALL show "PHI blocked for this vendor" for it.

#### Scenario: Workspace pending
- **WHEN** Google Workspace is conditional and pending
- **THEN** the matrix shows "PHI blocked for this vendor" and the gate reasons don't include it

### Requirement: The matrix is generated
`docs/compliance/vendor-matrix.md` SHALL be generated from `vendors.yaml` by `--render`, say so in its header, and the checker SHALL fail when the committed file differs from what `--render` would write.

#### Scenario: Hand edit
- **WHEN** someone edits `vendor-matrix.md` by hand
- **THEN** the checker exits 1 with rule C8 until it is re-rendered

#### Scenario: Stale review
- **WHEN** `reviewed_on` is more than 100 days old
- **THEN** the checker warns (rule C9) and still exits 0

### Requirement: New vendors are caught in review
Every change that adds an external service, an SDK that sends data out, a Google API, or a new kind of PHI to a vendor SHALL update `vendors.yaml` in the same change, as asked by the PR checklist in `docs/compliance/pr-vendor-check.md`.

#### Scenario: Error tracker added
- **WHEN** a change adds an error-tracking SaaS SDK without a vendor row
- **THEN** the PR checklist item fails in review and the change is blocked until the row (and, if it gets PHI, a BAA) exists
