# ADR 0005: Database: PostgreSQL 16, on Cloud SQL

| | |
|---|---|
| Status | **Accepted** for PostgreSQL 16 (any hosting). **Accepted, if hosting is Google Cloud** for Cloud SQL (2026-11-26) |
| Date | 2026-11-26 |
| Task | P0-14 (issue #15) · DECISIONS #318, #320 |
| Deciders | Riley Tech (tech lead), Sam Comply (compliance owner) |

## Context
We store little: Open Dental references (`PatNum`, `AptNum`), callback cases, consents, message records, clinic config and the audit log (plan §5). PHI fields are encrypted at field level (P1-05). It must be relational (constraints, append-only tables), encrypted with our key, private, backed up in the US, and HIPAA-covered. Local development uses Postgres 16 in docker compose (DECISIONS #302).

## Options considered
| Option | For | Against |
|---|---|---|
| **Cloud SQL for PostgreSQL** | Managed, HA, CMEK, private IP (PSC, A12), IAM DB auth (A13), point-in-time recovery, HIPAA-covered | Fewer tuning knobs |
| AlloyDB for PostgreSQL | Faster at scale | More cost and features than our data needs |
| Firestore | Serverless | No relational constraints; append-only and joins harder |
| Self-managed Postgres on VMs | Control | Patching, backups, HA by us |

## Decision
- **Engine:** PostgreSQL 16 everywhere (local, dev, staging, prod).
- **On Google Cloud:** Cloud SQL for PostgreSQL, CMEK, private IP only (Private Service Connect by default), no public IP, IAM database authentication, HA in prod, 30 daily backups and point-in-time recovery in a US location.
- Every schema change is an Alembic migration; `audit_log` and `consents` are append-only (CLAUDE.md).

## Consequences
- P1-03 builds the instance and the schema (absorbs P1-09).
- VPC-SC protects only the Cloud SQL Admin API, not network access (A9): private IP, IAM auth and no public IP are the real controls.
- Cost is one small HA instance in prod.

## Review triggers
- The client chooses other hosting (Cloud SQL part re-opens; PostgreSQL 16 stays).
- Data volume or latency needs outgrow Cloud SQL.
