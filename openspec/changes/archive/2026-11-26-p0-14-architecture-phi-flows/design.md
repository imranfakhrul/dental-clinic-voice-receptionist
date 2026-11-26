# Design: P0-14 Architecture doc and PHI data-flow diagram

## Context

The P0-14 spec (`dental-ai-tasks/tasks/P0-14 Architecture doc and PHI data-flow diagram.md`) was written before several Phase 0 decisions. The apply must follow the decisions, not the older spec text:

| Spec says | Now true | Source |
|---|---|---|
| Messaging provider "SMS / WhatsApp", vendor `messaging-provider` | WhatsApp through **Meta Cloud API** now (synthetic only); **SMS through Twilio** per clinic at go-live; WhatsApp real data only after both BAAs | DECISIONS #299, #300; `vendors.yaml` ids `meta-whatsapp`, `twilio` |
| VPC-SC perimeter `dai_prod` enforced | Written in Terraform, **not applied**: no organization | DECISIONS #296; risk R34 |
| Google Cloud is the platform | **Hosting open**, local-first, no cloud resources now | DECISIONS #302; risk R37 |
| Gemini endpoint `us` | Confirmed; also a Developer API path on laptops (synthetic) | DECISIONS #315, #316 |
| Gmail `callbacks@` | `link_only` default; no Workspace until production | DECISIONS #303, #304 |
| S2 "Redis lock on the slot" | **No slot hold**; collisions caught by re-checking the slot before create | DECISIONS #146, #290; CLAUDE.md rule 9 |
| Task IDs P1-08, P1-09, P1-04, P2-02, P2-06, P2-23, P3-05, P1-17, P1-18 … | Merged; cite survivors (P1-01, P1-03, P1-02, P2-01, P2-03, P2-22, P3-03, P1-16, P1-15 …) | `_CONSOLIDATION.md` |
| CODEOWNERS entry for `phi-flows.md` | No CODEOWNERS file until production; proposed entries only | DECISIONS #308 |
| Notify P1/P2/P3/P4 issues | Those issues don't exist yet | Phase-by-phase issue creation |

Mock roles, as in earlier tasks: Riley Tech (tech lead, author), a backend engineer review by Riley Tech's second pass, Sam Comply (compliance owner) for `phi-flows.md` and `network.md`.

## Goals / Non-Goals

**Goals:**
- One architecture that P1–P4 can build against, for the Google Cloud target, with a clear local view for today.
- A PHI flow table that is complete (every slot, every PHI vendor) and machine-checked.
- ADRs 0002–0006 with statuses that match the hosting situation.
- "Verify" facts checked against Google and Pipecat docs on the day.

**Non-Goals:**
- Terraform, network or service creation (P1-02, P1-03, P1-05).
- The final Pipecat decision and the latency prototype (P3-01).
- The detailed data model (P1-03).

## Decisions

### 1. Google Cloud target, with deployment views and hosting deltas
The diagrams show the Google Cloud design from the plan, because every approved spec assumes it. `README.md` adds three deployment views:
- **Local** (today): docker compose (API, Postgres 16, Redis 7), synthetic data, Gemini Developer API or Vertex, Meta WhatsApp test number, Open Dental test DB through the relay.
- **dev / staging:** same flows as prod, synthetic data only (spec rule R-C).
- **prod:** the full design, real PHI only after the PHI gate opens.

A "if hosting is not Google Cloud" table lists what changes (CMEK, VPC-SC, restricted VIP, Cloud Tasks, keyless Gmail, Vertex/Speech providers). Alternative considered: a cloud-neutral diagram only. Rejected: too vague for P1-02, and the approved specs name Google services.

### 2. ADR status split (user decision)
| ADR | Status |
|---|---|
| 0001 Gemini models | Proposed (P0-13) |
| 0002 Runtime: Cloud Run | **Accepted, conditional on Google Cloud hosting** |
| 0003 Pipecat | **Proposed** until P3-01 |
| 0004 Audio transport: WebSocket | **Accepted** |
| 0005 Database: Cloud SQL Postgres | **Accepted, conditional on Google Cloud hosting**. PostgreSQL 16 itself is Accepted for any hosting |
| 0006 Code conventions | **Accepted** |

### 3. New flow IDs F01–F17 replace F1–F9
The spec's F01–F14 are kept, with these changes:
- F10 is split by channel: **F10a** WhatsApp (Meta Cloud API, now synthetic only; real data only after both BAAs) and **F10b** SMS (Twilio, at go-live).
- **F15** inbound messaging webhooks (delivery status, STOP replies: phone number, message ID) from Meta or Twilio to `api`. Missing in the spec; needed because a phone number is PHI in this context.
- **F16** Open Dental test DB (synthetic) for dev and staging, through the same relay (P0-12).
- **F17** Gemini Developer API: **not a PHI flow**. Laptops only, synthetic, drawn outside every boundary.

`phi-flows.md` includes a mapping from the P0-11 F1–F9 and A01–A18 to the new IDs, so the register's references stay valid.

### 4. Field names are the P0-04 slot names
The fields column uses the P0-04 slot names in backticks (`first_name`, `dob`, `whatsapp_number`, `situation`, …). This makes the coverage check exact. Non-slot data (audio, PatNum, AptNum, case summary) uses fixed names listed in the document.

### 5. Coverage checker `scripts/compliance/check_phi_flows.py`
Python standard library plus PyYAML, the same style as `check_vendors.py`. It:
1. reads the PHI slot table in `docs/flows/overview.md`;
2. reads the flow table in `docs/architecture/phi-flows.md`;
3. reads `docs/compliance/vendors.yaml` and `infra/org/allowed_services.yaml`;
4. reads a "Google services used" table in `containers.md` (one API name per row);
5. reports: slots without a flow, PHI vendors without a flow, unknown vendor ids, services not allowed, flow rows with an empty BAA cell; exit 1 on any gap.

Offline tests with temporary fixture files. Alternative: a manual checklist only (spec §10). Rejected: the table will change in every phase, and the checklist would drift.

### 6. "Verify" facts checked on the day
Cloud Run (WebSockets, request timeout, session affinity, billing, Direct VPC egress, ingress), the load balancer with serverless NEG, VPC-SC supported products and the restricted VIP (incl. whether it serves the Vertex AI `us` multi-region host), Cloud SQL private IP and IAM auth, Memorystore encryption and CMEK, Cloud Tasks OIDC, and Pipecat's Google services (Vertex AI option, STT/TTS location). Each answer is recorded as a source row (new section in `docs/compliance/sources/README.md`, IDs A1…), using the HTML pages. Unanswered items become open questions for P1-02 or P3-01.

### 7. Sequences follow the newer decisions
- S1 latency numbers from plan §4.4; P0-13's first-token numbers are pending (no live run yet), so S1 shows targets and says so.
- S2: confirm → **re-query Open Dental for the slot** → create with idempotency key and operation hash → verify → confirm. No hold or lock at offer or selection.
- S3: link-only email by default.
- S4: payloads carry IDs only; re-fetch before send.
- A reconnect sequence is added to S1 (60-minute cut or instance loss).

### 8. Records, not live config
- CODEOWNERS: add `docs/architecture/phi-flows.md` to the proposed entries in `pr-vendor-check.md`.
- Hand-offs: rows in `docs/compliance/README.md` for each downstream task; P0-11 and P0-09 updated or noted directly.

## Risks / Trade-offs

- [Cloud facts change after today] → each fact has a date and URL; P1-02 re-checks before building.
- [The client picks another cloud and much of this is re-done] → hosting-delta table and conditional ADRs make the re-work list explicit (R37).
- [The flow table and the diagram drift] → the table wins; the checker covers slots, vendors and services, not the diagram, so reviewers check the diagram by hand.
- [Mock reviews are not real reviews] → recorded as role-played reviews, like earlier P0 tasks; the senior reviews the whole phase.

## Open Questions

- Does the restricted VIP serve `aiplatform.us.rep.googleapis.com`? Answered in apply if Google's docs say; otherwise open for P1-02.
- Direct VPC egress or a Serverless VPC Access connector with Cloud NAT? Answered from Google's current advice, or open for P1-02.
- One `api` service, or a separate `voice` service? Proposed: one `api`; P3-01 or P5-03 (was P5-06) may split it.
