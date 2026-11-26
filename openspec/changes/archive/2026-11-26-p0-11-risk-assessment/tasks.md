# Tasks: P0-11 Risk assessment v1 (issue #12)

## 1. Sources (read-only)

- [x] 1.1 Verify against eCFR (current) 164.308(a)(1)(ii)(A)–(B), the standards in 164.308, 164.310, 164.312, 164.316, and the HHS Guidance on Risk Analysis elements; check the status of the January 2025 Security Rule NPRM. Add source rows to `docs/compliance/sources/README.md`. Verify: each citation used has a row; the NPRM status is stated or marked Verify.

## 2. Assessment documents

- [x] 2.1 Write `docs/compliance/risk/risk-assessment-v1.md` sections 1–4 (scope, method and scales, asset inventory, data flows F1–F9), from the inputs listed in the design. Verify: every inventory asset with ePHI appears in at least one flow.
- [x] 2.2 (role: Riley Tech, tech lead, scoring session) Write `docs/compliance/risk/risk-register.md`: R01–R33 from the spec plus R34–R38, with survivor task IDs, inherent and residual scores, owner, decision and status. Verify: the register checker passes.
- [x] 2.3 Write `scripts/compliance/check_risk_register.py` (task IDs exist and are survivors; score and band math; High/Critical residual ≤ 9 or accepted; every PHI vendor named). Run it on the register and on a broken copy. Verify: passes on the real register, fails on the broken one.
- [x] 2.4 Write `docs/compliance/risk/safeguard-coverage.md` (every standard → risks and controls or "not applicable because…") and `docs/compliance/risk/accepted-risks.md` (rules, empty table). Verify: every standard row is filled.
- [x] 2.5 Fill sections 5–8 of `risk-assessment-v1.md`: results summary (band counts inherent and residual, top risks), gaps G1–G4 with decisions, review triggers, sign-off. Verify: counts match the register.

## 3. Reviews and records

- [x] 3.1 (role: Morgan Lead, sponsor) Record the gap decisions (G1–G3 → P5-14, G4 → P5-12). (Role: Sam Comply, compliance advisor) Run the spec §10 checks and record the results and comments in section 8. Verify: each check has a result.
- [x] 3.2 Update the "Legal review of terms" field in each `docs/compliance/baa-*.md` record to pending under R29 (no counsel). Verify: all five records updated; none says done.
- [x] 3.3 Append DECISIONS rows (next number 309): register v1 result (counts, new risks R34–R38, survivor-ID rule, checker); gap decisions closing #59; deviations (mock reviews, R29 pending, public-repo detail level, sign-off is draft). Verify: rows present.
- [x] 3.4 Update `docs/compliance/README.md` (file table, pending items, notifications for P5-12, P5-14, P0-14 and the High-risk control owners), the Phase 0 README #12 status, and `docs/PROJECT_MAP.md`. Run the public-repo scan and the link check. Verify: scan clean, no broken links.

## Workflow follow-up

- After the user has reviewed the work and given the go-ahead: archive the change (sync the `risk-assessment` spec), commit with a one-line descriptive message, push `feature/phase-0-discovery-compliance`, comment the hand-offs on issues #15 (P0-14) and #13 (P0-12, R12), and close issue #12 with a comment listing the files. Do none of these before the user says so.
