# Design: P0-09 Clinic ↔ company BAA

## Context
See proposal.md (Why). Facts that shape the approach:
- **No counsel is engaged** and the clinic is represented by our mock personas (P0-01: BAA signatory Dr. Casey Example, owner; SME Alex Sample). User decision 2026-11-26: draft everything, record it as a **paper record, NOT SIGNED**.
- **Every subcontractor BAA is NOT ACCEPTED** today: Google Cloud (P0-05), Google Workspace (P0-08), Meta WhatsApp and Twilio SMS (P0-07).
- **Hosting is open** (DECISIONS #302, local-first). Annex A describes the planned production setup on Google Cloud and says so.
- **P0-01 Q9:** no transcripts stored, raw audio never stored. **P0-08:** callback emails are `link_only` by default.
- The repo is public, so nothing confidential (a real signed PDF, negotiation emails) is committed.

## Goals / Non-Goals
**Goals:** documents a counsel could finalize without redoing our homework; every promise traceable to a task; the gate written so later tasks (P0-12, P0-10) can check it.

**Non-Goals:** final legal text; a signature; the main service / pilot agreement; the incident process (P5-12) and deletion jobs (P5-13) themselves.

## Decisions
1. **Template base: HHS sample provisions.** They are public, written for exactly this case, and map one-to-one to the required terms. Alternative: a commercial template (licence, not public) or writing from scratch (more risk). The template is plain Markdown with numbered sections, so the checklist can cite each section.
2. **Citations checked against eCFR during apply.** The spec's citations are marked Verify. Apply re-reads eCFR 45 CFR 164.504(e), 164.314(a), 164.410 and the HHS page, and records URL, date, quote and SHA-256 in `sources/README.md` (same as P0-07/P0-08). If a citation differs, the checklist follows eCFR and the difference is noted.
3. **Proposed terms P1–P9 kept as in the spec**, after the tech lead's feasibility check: 5 business days breach notice (achievable if P5-12 includes an on-call contact; 164.410's outer limit is 60 days), aggregate reporting of unsuccessful incidents, no AI training and no sale, US-only, minimum necessary, 30-day subcontractor notice, 30-day return/destroy with certificate, no de-identified use without consent. P6 (access from outside the US) stays an **open question** for the sponsor and is written in Annex B as "to be disclosed".
4. **Annex A built from sources, not memory.** Rows come from the PHI slot table in `docs/flows/overview.md` (11 PHI slots grouped into categories), `messaging_policy.yaml`, `admin-email.md` and Q9. A check lists each PHI slot and the Annex A row that covers it, so "none missing, none invented" is visible.
5. **Annex B lists both messaging vendors.** The clinic chooses SMS or WhatsApp at go-live (P0-07a), so the annex lists Twilio (SMS) and Meta (WhatsApp) with "only the one the clinic chooses is used". Open Dental's API relay goes in as an open question for counsel, not as a subcontractor.
6. **Versioning.** Template, annexes and checklist carry `v1` and a date in their header; the record cites those versions. Any change after a signature creates v2 and an amendment check.
7. **Reviews by mock personas, labelled as such inside the project convention.** Sam Comply (compliance advisor) checks R1–R11 and the commitments; Riley Tech (tech lead) signs off feasibility; Alex Sample and Dr. Casey Example read the draft for the clinic. Counsel review is **pending**, never simulated: the record says "no counsel engaged".
8. **Signed copy location.** When a real signature happens, the PDF goes in a private drive, not this public repo; the record keeps its file name, date and SHA-256. This differs from the spec's `docs/compliance/agreements/` path and is logged as a deviation.

## Risks / Trade-offs
- [Draft read as legal advice] → Every file starts with "Draft, not legal advice, counsel review pending".
- [Promise we can't keep, e.g. 5 business days] → Commitments row names P5-12 and its tabletop test; the value can change before signature.
- [Annex A drifts from the flows] → The slot-to-row check is repeatable; P0-11 and P5-14 re-run it.
- [Record mistaken for a real signature] → Status NOT SIGNED in the first line; no signature images.

## Migration Plan
Not applicable (documents only).

## Open Questions
- Who is our counsel, and who owns the main service agreement? (sponsor; needed before signing, doesn't change these documents)
- Is Open Dental's API relay covered by the clinic's own arrangement? (counsel)
- Will anyone access production PHI from outside the US? (sponsor + tech lead; fills term P6)
