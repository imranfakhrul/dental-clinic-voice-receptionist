# Tasks: P0-14 Architecture doc and PHI data-flow diagram (issue #15)

## 1. Facts (read-only)

- [x] 1.1 Read Google's HTML pages for Cloud Run (WebSockets, request timeout, session affinity, billing, Direct VPC egress, ingress), the external Application Load Balancer with serverless NEG, VPC-SC supported products and the restricted VIP (does it serve `aiplatform.us.rep.googleapis.com`?), Cloud SQL private IP and IAM database auth, Memorystore for Redis encryption and CMEK, and Cloud Tasks OIDC to Cloud Run. Read Pipecat's docs for a Vertex AI LLM option and the location settings of `GoogleSTTService` / `GoogleTTSService`. Record A-rows (URL, date, fact) in `docs/compliance/sources/README.md`. Verify: every "Verify" item in the spec has an answer or a named open question.

## 2. Architecture documents

- [x] 2.1 Write `docs/architecture/context.md` (level 1) and `containers.md` (level 2, responsibilities table with survivor task IDs, "Google services used" table with API names, local docker-compose view). Verify: survivor IDs only; every service is in `infra/org/allowed_services.yaml`.
- [x] 2.2 Write `docs/architecture/phi-flows.md`: trust-boundary diagram (Developer API outside every boundary), flow table F01–F17 with P0-04 slot names as fields, vendor id, BAA and status, protections, environments, owner tasks; rules R-A to R-C; mapping from P0-11 F1–F9 and A01–A18. Verify: each PHI edge in the diagram names its BAA.
- [x] 2.3 Write `docs/architecture/network.md` (projects, VPC, subnet, ingress, egress, private services, restricted VIP, perimeters, admin access, resource list), with each fact's source ID or an open question for P1-02. Verify: no unanswered "Verify" without an owner.
- [x] 2.4 Write `docs/architecture/sequences.md`: S1 voice turn with latency budget and reconnect, S2 booking (no slot hold, re-check, idempotency key, verify), S3 callback (`link_only`), S4 reminder (IDs-only payload, re-fetch). Verify: matches DECISIONS #146, #290, #303.
- [x] 2.5 Write `docs/architecture/README.md`: reading order, deployment views (local, dev/staging, prod), "if hosting is not Google Cloud" table, change rules. Verify: links resolve.

## 3. ADRs

- [x] 3.1 Write `docs/adr/README.md` (index 0001–0006, template, status rules) and ADRs `0002-runtime-cloud-run.md` (Accepted, conditional on Google Cloud), `0003-pipecat.md` (Proposed), `0004-audio-transport.md` (Accepted), `0005-database.md` (Accepted, conditional on Google Cloud for Cloud SQL), `0006-code-conventions.md` (Accepted). Verify: every ADR has all template sections and review triggers.

## 4. Coverage check

- [x] 4.1 Write `scripts/compliance/check_phi_flows.py` (slots, PHI vendors, unknown vendor ids, services not allowed, empty BAA cells; exit 1 on a gap) and `test_check_phi_flows.py` with fixture files. Verify: tests pass offline, and the real repo passes.

## 5. Updates and records

- [x] 5.1 Update P0-11: the flow section in `risk-assessment-v1.md` links to `phi-flows.md` with the ID mapping; add new risks to `risk-register.md` (e.g. WebSocket reconnect losing a turn, a voice library's API-key Gemini path, inbound webhooks carrying phone numbers); bump the version note; run `check_risk_register.py`. Verify: checker passes.
- [x] 5.2 Add `docs/architecture/phi-flows.md` to the proposed CODEOWNERS entries in `docs/compliance/pr-vendor-check.md`. Check P0-09 Annex A against the table and note any mismatch. Verify: no live CODEOWNERS file is created.
- [x] 5.3 DECISIONS rows from #318 (architecture and flow IDs, ADR statuses, deviations from the spec); hand-off rows in `docs/compliance/README.md` for P1-01, P1-02, P1-03, P1-06, P2-01, P2-03, P3-01, P3-02, P4-04, P0-09, P0-10; update `docs/PROJECT_MAP.md` and `docs/phase-0-discovery-compliance/README.md`. Verify: merged-ID and link checks pass; public-repo scan clean; `openspec validate --strict` passes.

## 6. Finish (after the user's review)

- [x] 6.1 After the user has reviewed the work and said so: archive the change (sync the main spec), commit with a one-line descriptive message, ask, then push `feature/phase-0-discovery-compliance`, comment hand-offs, and close sub-issue #15 with the file list. Never close parent issue #17. Do none of this before the user says so.
