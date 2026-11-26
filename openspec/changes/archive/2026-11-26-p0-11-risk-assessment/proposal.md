# Proposal: P0-11 Risk assessment v1 (issue #12)

## Why

The HIPAA Security Rule requires a business associate to perform an accurate and thorough risk analysis of the ePHI it holds, and to reduce those risks to a reasonable level (45 CFR 164.308(a)(1)(ii)(A)–(B); verified against eCFR during apply). Without it the controls planned in P1–P5 have no documented reason, risks without an owning task stay unowned, P5-12 has no scenario list and P5-14 has nothing to finalize. Doing it before any code is cheap: a missing control found now becomes a task, not an incident.

Inputs now exist: Annex A (P0-09), `vendors.yaml` (P0-10), `hipaa-controls.md` (P0-06), the emergency tiers (P0-03), the state machine guards (P0-04) and the messaging and email rules (P0-07a, P0-08).

## What Changes

- **`docs/compliance/risk/risk-assessment-v1.md`:** scope, method and scales (DECISIONS #55), asset inventory, data-flow table F1–F9, results summary (heat-map counts, top risks), gaps and decisions, review triggers, sign-off.
- **`docs/compliance/risk/risk-register.md`:** the 33 initial risks from the spec, reviewed with the tech lead, plus risks found from what we've learned since (e.g. hosting not chosen and no organization guardrails, Meta not acting as a business associate, the Open Dental relay question). Every control cites a **survivor** task ID (merged IDs such as P1-11 → P1-07 are mapped), checked by a script against `dental-ai-tasks/tasks/`.
- **`docs/compliance/risk/safeguard-coverage.md`:** every Security Rule standard (164.308, 164.310, 164.312, plus 164.314/164.316) → risks and controls, or "not applicable because…". Standards list verified against eCFR.
- **`docs/compliance/risk/accepted-risks.md`:** the acceptance rules and an empty register (no High risk is accepted in v1).
- **Gaps G1–G4 decided (sponsor, mock):** G1–G3 go to P5-14, whose spec already covers policies, training, access reviews and device policy; G4 to P5-12 (which absorbed P5-13). Logged in DECISIONS.md; no new task ID needed.
- **R29 (legal review of vendor BAA terms):** recorded honestly as **pending** in each `baa-*.md` record, because no vendor BAA is accepted and no counsel is engaged.
- **Reviews (mock personas):** Riley Tech (tech lead) scoring session; Sam Comply (compliance advisor) review with the spec §10 checks; sign-off section filled as **v1 draft reviewed**, not final (final is P5-14).
- **Records:** DECISIONS rows, pending notifications (P5-12, P5-14, P0-14, High-risk control owners), READMEs and `docs/PROJECT_MAP.md`.
- No product code, no PHI, no cloud changes.

## Capabilities

### New Capabilities
- `risk-assessment`: the documented HIPAA risk analysis: what must be inventoried, how risks are scored, the rule that every High or Critical risk has an owned control or a signed acceptance, gap decisions, safeguard coverage and the triggers for re-review.

### Modified Capabilities
None.

## Impact

- New: `docs/compliance/risk/` (4 files) and a small check script `scripts/compliance/check_risk_register.py` (task IDs exist and are survivors; every High/Critical has controls and a residual ≤ Medium or an acceptance; every `phi: yes|conditional` vendor appears in a risk).
- Updated: `docs/compliance/baa-*.md` (R29 line), `docs/compliance/README.md`, `docs/compliance/sources/README.md`, `dental-ai-tasks/DECISIONS.md`, `docs/phase-0-discovery-compliance/README.md`, `docs/PROJECT_MAP.md`.
- The repo is public: the register is written at the level of categories and planned controls, with no hostnames, keys or exploit detail.
- Acceptance criteria met partly: R29 legal review and the advisor's final sign-off stay pending (no counsel; final review is P5-14).
