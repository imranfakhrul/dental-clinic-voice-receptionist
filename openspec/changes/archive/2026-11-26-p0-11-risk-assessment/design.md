# Design: P0-11 Risk assessment v1

## Context
See proposal.md (Why). Facts that shape the approach:
- DECISIONS #55–#59 already fix the method (HHS elements + NIST SP 800-30 style, 1–5 × 1–5, bands), the folder, the High/Critical rule, R29 and the gaps G1–G4 (pending a sponsor decision).
- **56 task IDs were merged** into survivors (e.g. P1-11 and P1-12 → P1-07, P2-14 → P2-12, P5-09 and P5-10 → P5-08, P5-13 → P5-12). The spec's initial register cites many merged IDs.
- P5-14's spec already covers G1–G3 (policies and training, access reviews, device policy) in `docs/compliance/policies/`.
- **Situation today:** hosting local-first (#302); Google Cloud projects in a personal account with no organization, so org policies and VPC-SC are written but not applied (#296); every vendor BAA NOT ACCEPTED; clinic BAA NOT SIGNED; no counsel; gate CLOSED (P0-10).
- The repo is public.

## Goals / Non-Goals
**Goals:** a register a reviewer can check mechanically; every High risk tied to a survivor task; gaps closed by decision; honest status.

**Non-Goals:** final sign-off (P5-14), the incident plan (P5-12), the data-flow diagram (P0-14), assessing the clinic's own Open Dental server.

## Decisions
1. **Start from the spec's 33 risks, keep their IDs.** IDs are never reused. New risks continue at R34. Scores start from the spec's Proposed values; the scoring session (tech lead) may change them, using the higher score on disagreement and noting it.
2. **Survivor IDs in the register, original in brackets.** E.g. "PHI-redacting logger (P1-07, was P1-11)". This keeps the link to the spec text while pointing owners at the task that will actually do the work.
3. **A small checker, `scripts/compliance/check_risk_register.py`** (standard library + `yaml`): parses the register table; checks that every cited task ID exists in `dental-ai-tasks/tasks/` and is not a `merged_into` stub; that score = L×I and the band matches; that every High/Critical row has a residual ≤ 9 or an entry in `accepted-risks.md`; and that every `vendors.yaml` row with `phi` yes/conditional is named in some risk. Spec §10's remaining checks (assets in flows, safeguard rows filled, gaps logged) are done by the reviewer and recorded.
4. **New risks from what we learned (Proposed, scored in the session):**
   - R34 (C/O) Real PHI enters before the org guardrails exist: Google Cloud in a personal account without an organization, so org policies and VPC-SC aren't enforced (#296). Control: PHI gate (P0-10), P0-05 Part C, P1-02.
   - R35 (V) The messaging vendor for WhatsApp isn't a business associate under its terms, so PHI over WhatsApp would lack a BAA (P0-07a). Control: `messaging_policy.yaml` gate, SMS fallback, P4-01.
   - R36 (V) The Open Dental API relay handles PHI without a BAA of ours (P0-09 open question). Control: counsel decision, `vendors.yaml` `under_review`, gate.
   - R37 (O) Hosting changes away from Google Cloud (#302) and the controls designed for Google Cloud (CMEK, VPC-SC, keyless email auth) no longer apply. Control: re-run this assessment (trigger), P0-14, P1-02.
   - R38 (C) Local development stores data on laptops (local-first Postgres/Redis) and real data slips in. Control: synthetic-only rule, PHI gate, P0-12 test DB, G3 device policy.
5. **Gap decisions (sponsor, Morgan Lead, mock):** G1–G3 → **P5-14** (its spec already includes them; no new task ID). G4 → **P5-12** (runbooks, backup/restore drill, retention; absorbed P5-13); the advisor confirms sufficiency at P5-14. Logged in DECISIONS.md, closing the "pending sponsor decision" in #59.
6. **R29 stays open.** Each `baa-*.md` record's "Legal review of terms" field is updated to "Pending: no counsel engaged; tracked as P0-11 R29" with the date, instead of "done". R29's residual can't be reached until counsel reviews.
7. **Sources verified during apply:** eCFR 164.308 (already downloaded in P0-09, L5), 164.310, 164.312, 164.316; the HHS Guidance on Risk Analysis page (elements list); the status of the January 2025 Security Rule NPRM (Federal Register / HHS). Rows added to `sources/README.md`; if the NPRM status can't be confirmed, it stays a Verify item for the advisor.
8. **Public-repo level of detail.** Risks name categories, assets and planned controls only. No hostnames, project numbers, keys or step-by-step attack detail. Logged as a deviation from spec §9 ("private repo").
9. **Sign-off:** v1 marked **"Draft v1, reviewed by compliance advisor (mock) 2026-11-26; final sign-off at P5-14"**. `accepted-risks.md` starts empty with its rules; no High risk is accepted in v1.

## Risks / Trade-offs
- [Mock reviews read as real] → The sign-off section names the personas' roles and says final review is P5-14; R29 and counsel stay pending.
- [Register drifts from tasks] → The checker runs on every change to the register or the task list.
- [Public register helps an attacker] → Category-level wording; no infrastructure identifiers.

## Migration Plan
Not applicable (documents only).

## Open Questions
- Has the 2025 Security Rule update been finalized? (advisor; may add requirements, doesn't change this structure)
- Who signs risk acceptances: sponsor alone or sponsor + advisor? (sponsor; affects only `accepted-risks.md`, which is empty in v1)
- Does Open Dental offer limited-permission keys (R12)? (P0-12)
