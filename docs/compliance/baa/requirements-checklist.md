# Clinic BAA requirements checklist (v1)

> Draft, not legal advice. Counsel confirms the required terms. Prepared 2026-11-26 for P0-09.

Use this to review **any** clinic BAA: our [template v1](clinic-baa-template-v1.md) or the clinic's own. Every required term must pass. A fail goes to counsel before anyone signs. Every term must also have a row in [commitments.md](commitments.md).

Citations were checked against eCFR (text as of 2026-11-24) and the HHS sample provisions on 2026-11-26: sources L1–L7 in [sources/README.md](../sources/README.md#p0-09-clinic-baa-checked-2026-11-26). They match the task spec.

## Required terms (HIPAA)
Review of: **template v1**, 2026-11-26, by Sam Comply (compliance advisor).

| # | Term | Citation | Template v1 section | Result |
|---|---|---|---|---|
| R1 | Permitted and required uses and disclosures (= the Services in Annex A); no use or disclosure that would violate the Privacy Rule if done by the clinic | 164.504(e)(2)(i) | 4.1, 4.4, Annex A | Pass |
| R2 | No use or disclosure other than permitted by the agreement or required by law | 164.504(e)(2)(ii)(A) | 3.1, 4.2 | Pass |
| R3 | Appropriate safeguards; comply with the Security Rule for electronic PHI | 164.504(e)(2)(ii)(B); 164.314(a)(2)(i)(A) | 3.2 | Pass |
| R4 | Report uses or disclosures not provided for, including breaches of unsecured PHI (164.410) and security incidents | 164.504(e)(2)(ii)(C); 164.314(a)(2)(i)(C); 164.410 | 3.3.1–3.3.4 | Pass |
| R5 | Subcontractors that handle the PHI agree in writing to the same restrictions and conditions | 164.504(e)(2)(ii)(D); 164.314(a)(2)(i)(B); 164.502(e)(1)(ii); 164.308(b)(2) | 3.4.1 | Pass |
| R6 | Make PHI available for the patient's access requests (164.524) | 164.504(e)(2)(ii)(E) | 3.5 | Pass |
| R7 | Make PHI available for amendment (164.526) and provide information for an accounting of disclosures (164.528) | 164.504(e)(2)(ii)(F), (G) | 3.6, 3.7 | Pass |
| R8 | Where we carry out a clinic obligation under the Privacy Rule, comply with the requirements that apply to it | 164.504(e)(2)(ii)(H) | 3.8 | Pass |
| R9 | Make internal practices, books and records available to HHS | 164.504(e)(2)(ii)(I) | 3.9 | Pass |
| R10 | At termination, return or destroy all PHI; if not feasible, extend protections and limit further use | 164.504(e)(2)(ii)(J) | 5.3, 5.4 | Pass (backup wording: counsel to confirm) |
| R11 | The clinic may terminate if we violate a material term | 164.504(e)(2)(iii) | 5.2 | Pass |

## Our proposed terms
Proposed by the team; the sponsor and counsel decide. Values below are after the tech lead's feasibility check ([commitments.md](commitments.md)).

| # | Term | Proposed value | Template v1 section | Result |
|---|---|---|---|---|
| P1 | Breach-notice deadline to the clinic | Within **5 business days** of discovery, with details known then; updates as the investigation continues (HIPAA outer limit: 60 calendar days, L3) | 3.3.2, 3.3.3 | Present |
| P2 | Unsuccessful security incidents (pings, blocked scans) | Reported in aggregate on request, not one by one | 2.4, 3.3.4 | Present |
| P3 | No use of PHI to train or improve AI models; no sale of PHI | Explicitly prohibited, including at subcontractors | 4.5 | Present |
| P4 | Data location | Stored and processed in the US only | 3.10 | Present |
| P5 | Minimum necessary | Only the PHI listed in Annex A | 4.3 | Present |
| P6 | Access from outside the US | **Open question** (sponsor + tech lead); both options drafted | 3.11, Annex B | Open |
| P7 | Subcontractor changes | Clinic notified at least 30 days before a new subcontractor handles PHI | 3.4.2 | Present |
| P8 | Return/destroy at termination | Within 30 days; written certificate; backups expire on their normal schedule under continued protection | 5.3 | Present (counsel to confirm) |
| P9 | De-identified data | Not used for any purpose without the clinic's written consent | 4.6 | Present |

## Notes for counsel
- **Optional HHS provisions not used:** our own management and administration, and data aggregation (template 4.7). That keeps the simpler return/destroy wording (HHS Option 1).
- **Backups (R10, P8):** HHS Option 1 says "retain no copies". Encrypted backups can't be edited, so 5.3 uses the infeasibility path of 164.504(e)(2)(ii)(J). Please confirm.
- **Who notifies individuals (3.3.5):** drafted as the clinic. Please confirm.
- **Open Dental API relay:** see [Annex B](annex-b-subcontractors.md#open-questions).

## How to review a clinic's own BAA
1. Copy the two tables above into the review record and fill in the "section" column with the clinic's section numbers.
2. Mark each required term Pass or Fail. Any Fail goes to counsel.
3. For each term in the clinic's draft that isn't in the tables, add a row to [commitments.md](commitments.md) first. If no task can keep the promise, counter-propose.
