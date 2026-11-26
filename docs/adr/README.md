# Architecture decision records

One file per decision. A decision is changed by a new ADR (or a new revision of the same ADR) that says what it supersedes; old text is kept. Each ADR also gets a DECISIONS row.

## Index
| ADR | Decision | Status | Task |
|---|---|---|---|
| [0001](0001-gemini-models.md) | Gemini models per routing tier, two backends, data settings | **Proposed** (Vertex spike and `cacheConfig` pending) | P0-13 |
| [0002](0002-runtime-cloud-run.md) | Runtime: Cloud Run for `web` and `api` | **Accepted, if hosting is Google Cloud** | P0-14 |
| [0003](0003-pipecat.md) | Pipecat for the voice pipeline only | **Proposed** until P3-01 | P0-14 |
| [0004](0004-audio-transport.md) | Audio transport: WebSocket | **Accepted** | P0-14 |
| [0005](0005-database.md) | Database: PostgreSQL 16; Cloud SQL on Google Cloud | **Accepted** (PostgreSQL); **Cloud SQL if hosting is Google Cloud** | P0-14 |
| [0006](0006-code-conventions.md) | Code conventions | **Accepted** | P0-14 |

## Status values
- **Proposed:** written and reviewed, but a condition is open (named in the ADR).
- **Accepted:** in force. "Accepted, if hosting is Google Cloud" means in force for the Google Cloud design and re-opened if the client picks other hosting (DECISIONS #302, #320).
- **Superseded by NNNN:** replaced; kept for history.

## Template
```markdown
# ADR NNNN: <title>

| | |
|---|---|
| Status | Proposed / Accepted / Superseded by NNNN (date) |
| Date | YYYY-MM-DD |
| Task | <ID> (issue #N) · DECISIONS #… |
| Deciders | <roles> |

## Context
## Options considered
## Decision
## Consequences
## Review triggers
```
