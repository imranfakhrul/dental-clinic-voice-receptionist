# Clinic BAA record: Example Dental

> **Status: NOT SIGNED.** No counsel is engaged and nobody has signed (user decision 2026-11-26, DECISIONS #306). **No real PHI may enter any environment, and the clinic's production Open Dental key may not be requested or used.** All work uses synthetic data and the Open Dental test database (P0-12).

| Field | Value |
|---|---|
| Covered entity | Example Dental (single location, P0-01 Q10) |
| Business associate | Our company (legal name to be filled in by the sponsor) |
| Agreement | Business Associate Agreement, [template v1](baa/clinic-baa-template-v1.md) (2026-11-26) |
| Annexes | [Annex A v1](baa/annex-a-data-and-purposes.md), [Annex B v1](baa/annex-b-subcontractors.md) |
| Checklist and commitments | [requirements-checklist.md](baa/requirements-checklist.md) v1, [commitments.md](baa/commitments.md) v1 |
| Underlying service / pilot agreement | - (not drafted; owner: sponsor + counsel) |
| Status | **NOT SIGNED** (paper record) |
| Clinic signatory | Dr. Casey Example, dentist/owner (P0-01 decision log) |
| Our signatory | - (a person with authority to bind the company; to be named by Morgan Lead, sponsor) |
| Counsel review | **Pending: no counsel engaged.** Not simulated. Checked 2026-11-26 in P0-11 (risks R29, R30 in the [risk register](risk/risk-register.md)). |
| Compliance advisor review | Sam Comply, 2026-11-26 (below) |
| Tech lead feasibility | Riley Tech, 2026-11-26 (in [commitments.md](baa/commitments.md)) |
| Sent to clinic | Draft shared for comment with Dr. Casey Example (signatory) and Alex Sample (SME), advisor copied, 2026-11-26. Not sent for signature. |
| Clinic's messaging channel | Not chosen yet (chosen at go-live, P0-07a). Annex B lists both options |
| Signed on | - |
| Signed copy | - (when signed: kept in the company's **private** drive, not this public repo; this record keeps the file name, date and SHA-256) |

## Reviews (spec §10)
**Compliance advisor (Sam Comply), 2026-11-26:**

| Check | Result |
|---|---|
| R1–R11 present in template v1 | **Pass**: 11 of 11, each with a section ([checklist](baa/requirements-checklist.md#required-terms-hipaa)). R10 backup wording goes to counsel. |
| Every term in the template has a commitments row | **Pass**: C1–C22 cover every term section (3.1–3.11, 4.1–4.7, 5.2, 5.3, 7.2) |
| Annex A matches the PHI slot list and messaging policy | **Pass**: 11 of 11 PHI slots mapped; message fields match `messaging_policy.yaml`; audio and transcripts "not stored" |
| Annex B matches the existing records | **Pass**: four rows, four records, all NOT ACCEPTED, none shown as signed |

Advisor's note: "The draft covers the required terms and our promises are traceable. It can't be signed until counsel finalizes it, and even signed, no PHI flows to a subcontractor until its own BAA is accepted."

**Tech lead (Riley Tech), 2026-11-26:** every commitment is feasible with the planned tasks, except C17 (outside-US access), which is open, and C4, where a 24-hour deadline is not feasible without on-call outside clinic hours.

## Clinic comments on the draft (2026-11-26)
| # | From | Comment | Response | Change |
|---|---|---|---|---|
| 1 | Dr. Casey Example | "Can you tell us about a breach within 24 hours instead of 5 business days?" | Checked against C4 first: a 24-hour deadline needs on-call outside clinic hours, which is disabled today (DECISIONS #278). Counter-proposal: keep 5 business days, and send an **initial heads-up the same business day** a suspected breach is confirmed by the incident commander, with details to follow. | Proposed for v2 if the clinic accepts; not in v1. Owner P5-12 to confirm the same-day heads-up is feasible |
| 2 | Alex Sample | "Who tells the patients if something happens?" | Template 3.3.5: the clinic notifies patients and HHS; we give all the details and templates (P5-12). | None |
| 3 | Dr. Casey Example | "We'll use your template; we don't have our own." | Noted. No clinic template to review. | None |
| 4 | Alex Sample | "Does Open Dental need to be listed? Our data goes through their servers." | Open question for counsel (Annex B). | None until counsel answers |

## Gates before signature
- [ ] Counsel engaged; finalizes the template (including the R10 backup wording, 3.3.5, 4.7).
- [ ] Sponsor decides P6 (access from outside the US) and names our signatory.
- [ ] Service / pilot agreement drafted.
- [ ] Clinic comment 1 resolved (v2 or keep v1).

## Gates before any real PHI (DECISIONS #25)
- [ ] This BAA signed by both parties; this record says **SIGNED**, with the signed copy's file name, date and SHA-256.
- [ ] Google Cloud BAA accepted ([baa-google-cloud.md](baa-google-cloud.md)).
- [ ] Messaging BAA for the clinic's chosen channel accepted ([baa-twilio.md](baa-twilio.md) or [baa-meta-whatsapp.md](baa-meta-whatsapp.md)).
- [ ] Workspace BAA accepted, if `full_details` email is ever used ([baa-google-workspace.md](baa-google-workspace.md)).
- [ ] Vendor matrix complete (P0-10).
- [ ] Then, and only then: P0-12 may request the clinic's **production** Open Dental key.

## When it is signed
1. Save the PDF in the private drive; record the file name, date and SHA-256 here.
2. Fill in every field above and set the status to **SIGNED**.
3. Add a DECISIONS row and notify P0-10, P0-12, P1-07, P5-12 and P5-14, and the sponsor (clinic item of the PHI gate closed).
