# ADR 0002: Runtime: Cloud Run

| | |
|---|---|
| Status | **Accepted, if hosting is Google Cloud** (2026-11-26). Re-opened if the client chooses other hosting |
| Date | 2026-11-26 |
| Task | P0-14 (issue #15) · DECISIONS #318, #320 |
| Deciders | Riley Tech (tech lead), backend review (Riley Tech, second pass), Sam Comply (compliance owner) |

## Context
We need a runtime for two deployables: the Next.js frontend (`web`) and the FastAPI backend (`api`) with REST, a long-lived WebSocket for voice and streaming chat, webhooks and queue handlers. It must be HIPAA-covered, US-located, inside a VPC-SC perimeter, and cheap at pilot scale. Facts: sources A1–A9.

## Options considered
| Option | For | Against |
|---|---|---|
| **Cloud Run** | Managed; scales to need; WebSockets supported; VPC-SC supported (extra setup); Direct VPC egress; HIPAA-covered | WebSocket cut at the request timeout (max 60 min); session affinity only best effort; instance-based billing while a WebSocket is open (A1–A4) |
| GKE Autopilot | Long connections without a timeout; full control | Cluster operations, more security work (node pools, policies), higher base cost for a small team |
| Compute Engine VMs | Full control | Patching, scaling and hardening by us |

## Decision
**Cloud Run** for `web` and `api`, behind an external Application Load Balancer (ingress "Internal and Cloud Load Balancing").

Settings for `api`:
| Setting | Value | Why |
|---|---|---|
| Request timeout | 3600 s (maximum) | Longest WebSocket before a forced reconnect (A2) |
| Billing | Instance-based | Any open WebSocket is billed that way anyway (A1) |
| Session affinity | On | Fewer cross-instance reconnects; best effort only (A3) |
| Min instances | ≥ 1 in prod (staging 0 or 1) | Avoid cold starts on voice; absorbs Direct VPC egress start-up delay (A5) |
| Memory | ≥ 512 MiB | Required for instance-based billing |
| Concurrency | Start at 80; tuned in P5-03 (load tests, was P5-06) | Voice sessions are CPU-heavy (VAD) |
| Egress | Direct VPC egress, all traffic | Serverless VPC Access isn't on the HIPAA list (A21) |
| Startup probe | HTTP, with retries | Direct VPC egress connections can take a minute at start (A5) |

`web` uses request billing and default settings.

## Consequences
- **Sessions must survive reconnects.** State lives in Redis after every turn (P2-01); the client reconnects with its session token (P3-02); [sequences.md S1b](../architecture/sequences.md#s1b-reconnect-websocket-cut-at-60-minutes-or-instance-loss).
- One `api` service holds REST, WebSocket, webhooks and task handlers. A separate `voice` or `worker` service is added only if P3-01 or P5-03 shows a need.
- Cloud Run continuous deployment can't be used inside a perimeter (A9); CI deploys from `ops` with a perimeter ingress rule (P1-06).
- Cost: instance-based billing for `api` around the clock in prod (min 1 instance).

## Review triggers
- The client chooses hosting other than Google Cloud (DECISIONS #302).
- P3-01 or P3-14 shows latency targets can't be met on Cloud Run.
- P5-03 load tests show concurrency or reconnect problems.
- Google changes WebSocket, timeout or billing behaviour.
