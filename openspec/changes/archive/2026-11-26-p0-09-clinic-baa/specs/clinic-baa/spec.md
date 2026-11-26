## Purpose

Define what any business associate agreement between a clinic and our company must contain, what its annexes must list, how every promise is tied to the task that keeps it, and the gate that keeps real PHI out until the agreement is signed.

## ADDED Requirements

### Requirement: Every clinic BAA passes the requirements checklist
A clinic BAA, whether our template or the clinic's own, SHALL be accepted only if every required term R1–R11 in `docs/compliance/baa/requirements-checklist.md` is present and marked pass, and any gap has been sent to counsel.

#### Scenario: Clinic sends its own template
- **WHEN** a clinic sends its own BAA that has no subcontractor term (R5)
- **THEN** the checklist marks R5 fail and the gap goes to counsel before anyone signs

#### Scenario: Our template is reviewed
- **WHEN** the compliance advisor reviews template v1
- **THEN** each of R1–R11 is marked pass or fail with the section where it appears

### Requirement: Every promise has an owner task
No term SHALL go into a clinic BAA unless `docs/compliance/baa/commitments.md` has a row for it naming the task that implements it, where it is checked, and the tech lead's confirmation that it is feasible.

#### Scenario: Clinic asks for a 24-hour breach notice
- **WHEN** the clinic asks to change the breach-notice deadline to 24 hours
- **THEN** the change is accepted only if the owner task (P5-12) can deliver it, otherwise we counter-propose, and an agreed change is logged in DECISIONS.md

#### Scenario: A draft term has no row
- **WHEN** a draft term has no row in the commitments table
- **THEN** the review fails until a row with an owner task is added or the term is removed

### Requirement: Annex A matches the data we actually handle
Annex A SHALL list every PHI data category the system handles, with purpose, storage, subcontractor and retention, and SHALL match the PHI slots in `docs/flows/overview.md`, the messaging policy and the email mode, with no category missing and none invented.

#### Scenario: A PHI slot is added
- **WHEN** a new PHI slot is added to the conversation flows
- **THEN** Annex A is updated, counsel is asked whether an amendment is needed, and the clinic is told before the change goes live

#### Scenario: Data not kept
- **WHEN** a category is not stored (raw audio, transcripts under P0-01 Q9)
- **THEN** Annex A says "not stored" for it rather than leaving it out

### Requirement: Annex B shows each subcontractor's real BAA status
Annex B SHALL list every subcontractor that may receive the clinic's PHI with a link to its BAA record, and SHALL NOT show a BAA as signed unless that record says so.

#### Scenario: Subcontractor BAA still on paper
- **WHEN** a subcontractor's record says NOT ACCEPTED
- **THEN** Annex B shows it as pending and no PHI flows to that subcontractor until its record says accepted

#### Scenario: New subcontractor
- **WHEN** a new subcontractor will handle PHI
- **THEN** Annex B is updated and the clinic is told at least 30 days before any PHI flows to it (proposed term P7)

### Requirement: No real PHI before signature
Until the clinic BAA record says SIGNED by both parties, the system SHALL use only synthetic data, and the clinic's production Open Dental key SHALL NOT be requested or used.

#### Scenario: Record says NOT SIGNED
- **WHEN** `baa-clinic-<slug>.md` says NOT SIGNED
- **THEN** P0-12 may use only the Open Dental test database and no real patient data enters any environment

#### Scenario: Someone offers real data to test
- **WHEN** someone shares real patient data before signature
- **THEN** it is refused and deleted, and the compliance advisor is told (possible incident)

### Requirement: The BAA record is complete and honest
Each clinic SHALL have a record `docs/compliance/baa-clinic-<slug>.md` stating the template and annex versions, the signatory for each side, counsel and advisor review, status, and the gates still open; a signed copy SHALL be kept out of the public repo.

#### Scenario: Paper record
- **WHEN** no counsel has reviewed it and nobody has signed
- **THEN** the record says NOT SIGNED, names what is pending, and the PHI gate stays closed
