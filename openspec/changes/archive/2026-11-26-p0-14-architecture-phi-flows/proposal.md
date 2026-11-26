# Proposal: P0-14 Architecture doc and PHI data-flow diagram (issue #15)

## Why

Every developer from P1 on needs the same answers: where does this code run, what can it reach, and which PHI may it send where. Without one agreed picture, people make conflicting choices: a WebSocket on a platform that cuts it at 5 minutes, a library that calls Gemini with an API key, a debug path that sends transcripts to an unlisted vendor.

The PHI flow table is also compliance evidence:
- the risk assessment (P0-11) uses interim flows F1–F9 and asset list A01–A18 that this task replaces;
- the HIPAA readiness review (P5-14) checks that every PHI hop has a BAA;
- the clinic BAA Annex A (P0-09) must match it.

Our situation on 2026-11-26 shapes the result:
- **Hosting is open** (DECISIONS #302, senior's local-first rule). The design targets Google Cloud, as the plan says, and marks what changes if the client picks another cloud (risk R37).
- **No organization** (DECISIONS #296): org policies and VPC-SC perimeters are written but not applied. The architecture shows them as required before real PHI.
- **Messaging:** WhatsApp through the Meta Cloud API now (synthetic data), SMS through Twilio at go-live per clinic (DECISIONS #299, #300).
- **Gemini:** Vertex AI on the `us` multi-region; the Developer API only on developer machines with synthetic data (DECISIONS #315, #316). P0-13 asked us to show that path outside the PHI boundary.

**User decision (2026-11-26), ADR status split by dependency:**
- 0004 (audio transport) and 0006 (code conventions) hold on any hosting: **Accepted**.
- 0002 (Cloud Run) and 0005 (Cloud SQL) are **Accepted on condition that hosting is Google Cloud**; they re-open if the client chooses otherwise.
- 0003 (Pipecat) stays **Proposed** until P3-01.

## What Changes

- **`docs/architecture/`** with Mermaid diagrams:
  - `README.md`: reading order, change rules, deployment views (local, dev/staging, prod);
  - `context.md`: level 1, actors and external systems;
  - `containers.md`: level 2, deployables, stores and Google services, plus a module responsibilities table using **survivor task IDs**; also a local docker-compose view;
  - `phi-flows.md`: trust-boundary diagram and the **PHI flow table** (single source of truth), with field-level coverage of every P0-04 PHI slot and every PHI vendor in `vendors.yaml`; the Developer API drawn outside the PHI boundary;
  - `network.md`: network map and resource list, with each "Verify" item answered from Google's docs (with URL and date) or listed as an open question for P1-02;
  - `sequences.md`: S1 voice turn with the latency budget, S2 booking (no slot hold, re-check before create, DECISIONS #146/#290), S3 callback, S4 reminder.
- **`docs/adr/`:** `README.md` (index 0001–0006 and template) and ADRs 0002–0006, with facts on Cloud Run, VPC-SC and Pipecat checked on the day and recorded as sources.
- **Checker script** `scripts/compliance/check_phi_flows.py` with offline tests: every P0-04 PHI slot appears in a flow row, every PHI vendor appears in a flow, every flow vendor id exists in `vendors.yaml`, every Google service in the diagrams is in `infra/org/allowed_services.yaml`.
- **P0-11 update:** the flow section points to `phi-flows.md`; new risks found here are added; version note bumped.
- **CODEOWNERS:** the `phi-flows.md` path is added to the **proposed** entries in `pr-vendor-check.md` (no live CODEOWNERS file until production, DECISIONS #308).
- **Records:** DECISIONS rows, sources, hand-off notes for P1-01, P1-02, P1-03, P1-06, P2-01, P2-03, P3-01, P3-02, P4-04, P0-09 and P0-10 (no issues exist yet; notes go in `docs/compliance/README.md`), READMEs and `docs/PROJECT_MAP.md`.

No application code, no cloud resources, no PHI.

## Capabilities

### New Capabilities
- `architecture-phi-flows`: the agreed system architecture (context, containers, network, sequences), the PHI flow table as the single source of truth for where PHI may go and under which BAA, the ADR set 0001–0006, and the automated coverage check that keeps the table consistent with the flow designs, the vendor matrix and the allowed Google services.

### Modified Capabilities
- (none; the risk-assessment main spec's requirements don't change, only its document is updated)

## Impact

- **New:** `docs/architecture/` (6 files), `docs/adr/README.md`, `docs/adr/0002`–`0006`, `scripts/compliance/check_phi_flows.py` and its tests.
- **Updated:** `docs/compliance/risk/risk-assessment-v1.md` and `risk-register.md`, `docs/compliance/pr-vendor-check.md`, `docs/compliance/sources/README.md`, `docs/compliance/README.md`, `dental-ai-tasks/DECISIONS.md`, `docs/PROJECT_MAP.md`, `docs/phase-0-discovery-compliance/README.md`.
- **Downstream:** P1-01 follows ADR 0006; P1-02 and P1-03 build the network map; P2-01 must restore sessions after a reconnect; P2-03 owns the only Gemini path; P3-01/P3-02 confirm ADRs 0003/0004; P4-04 keeps task payloads ID-only; P0-09 Annex A is checked against the table.
