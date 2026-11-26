# Architecture

The agreed MVP architecture (P0-14, issue #15). Every phase from P1 on builds against it. Decisions behind it are in [`docs/adr/`](../adr/README.md).

## 1. Reading order
| File | What it answers |
|---|---|
| [context.md](context.md) | Who uses the system and which outside systems it talks to |
| [containers.md](containers.md) | What runs where; local view; which module owns what; Google services used |
| [phi-flows.md](phi-flows.md) | **Where PHI may go**, with which fields, to which vendor, under which BAA (source of truth) |
| [network.md](network.md) | Network map, ingress, egress, private access, perimeters, open questions for P1-02 |
| [sequences.md](sequences.md) | Voice turn with latency budget, reconnect, booking, callback, reminder |

Glossary: [GLOSSARY.md](../../dental-ai-tasks/GLOSSARY.md). Facts: sources A1–A22 in [sources/README.md](../compliance/sources/README.md#p0-14-architecture-checked-2026-11-26).

## 2. Deployment views
| View | Runs | Data | Status |
|---|---|---|---|
| **Local** | `docker compose`: `api`, Postgres 16, Redis 7; Next.js dev server; Mailpit. Gemini through the Developer API (key) or Vertex; Meta WhatsApp test number; Open Dental test DB; a temporary tunnel for webhooks | Synthetic only | **Now** (DECISIONS #302) |
| **dev / staging** | The cloud design, same flows as prod | Synthetic only (rule R-C) | After hosting is chosen and billing exists |
| **prod** | The cloud design | Real PHI only after the PHI gate opens (BAAs signed, org guardrails applied) | Later |

## 3. Key rules recorded here
- The LLM talks; code acts. Gemini never calls Open Dental or any tool directly (CLAUDE.md rule 2).
- PHI only on the hops in [phi-flows.md](phi-flows.md); no PHI in URLs, logs, traces, errors, analytics or task payloads.
- Gemini only through our provider on Vertex AI `us`; no API-key path in any cloud environment, including through Pipecat.
- Load-balancer-only ingress; Google APIs through the restricted VIP or a Private Service Connect endpoint.
- Connections can drop at any time (60-minute WebSocket limit, instance loss): state lives in Redis and the client reconnects.

## 4. If hosting is not Google Cloud
Hosting is open (DECISIONS #302, risk R37). If the client chooses another cloud, these parts change; the rest (modules, state machine, flows, rules) stays.

| Part | Google Cloud design | What must be redone |
|---|---|---|
| Runtime | Cloud Run (ADR 0002, conditional) | Container service on the new cloud with WebSocket support and a reconnect-safe timeout |
| Database | Cloud SQL Postgres 16 (ADR 0005, conditional) | Managed Postgres 16 with encryption by our own key, private network, backups in the US |
| Gemini, Speech, TTS | Vertex AI `us`, Google STT and TTS | Re-open the AI and speech provider choice (ADR 0001 review trigger); new vendor rows and BAAs |
| Perimeter, restricted VIP, PSC | VPC-SC and private Google access | The new cloud's equivalents; re-run the risk assessment |
| Keys and secrets | KMS (CMEK), Secret Manager | Key and secret services of the new cloud |
| Queues | Cloud Tasks, Scheduler | A queue and scheduler service with authenticated delivery |
| Email | Gmail with keyless delegation from a Google Cloud service account | A key-based or workload-identity setup, re-checked by P0-08 |
| Flow table | `google-cloud` rows | New vendor ids, BAAs and an updated Annex A/B before any PHI |

## 5. Change rules
- A change to a PHI hop or field updates [phi-flows.md](phi-flows.md), `vendors.yaml` (if a vendor is added) and Annex A in the same change, and the compliance owner reviews it (rule R-B).
- Run `python3 scripts/compliance/check_phi_flows.py` after any change to the flow table, the P0-04 slot list, `vendors.yaml`, `allowed_services.yaml` or the services table in [containers.md](containers.md).
- A new architecture decision gets an ADR in `docs/adr/` and a DECISIONS row.
- Diagrams are Mermaid, so GitHub renders them; the PDF build shows them as code.
