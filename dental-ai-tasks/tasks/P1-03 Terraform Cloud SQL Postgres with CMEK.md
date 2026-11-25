---
id: P1-03
title: Cloud SQL Postgres (private IP, CMEK, HA, PITR) and application database schema
milestone: P1
epic: E1.1
size: L
labels: area:infra, area:backend, type:feature, phi
depends_on: P1-02, P1-01
status: approved
---

# P1-03: Cloud SQL Postgres (private IP, CMEK, HA, PITR) and application database schema

## 1. Summary
This issue does two connected things. It also absorbs **P1-09 (Database schema and migrations, all §5 tables)**.

1. **Infrastructure (Terraform):** a Cloud SQL for PostgreSQL instance per environment:
   - private IP only, on the Private Service Access range from P1-02;
   - CMEK with the `sql` key from P1-02;
   - SSL required;
   - daily backups and point-in-time recovery (PITR);
   - regional HA in prod;
   - IAM database authentication;
   - a database `app`.
2. **Schema:** SQLAlchemy 2 models and Alembic migrations for every application table, three database roles, and the append-only audit log:
   - from plan §5: `clinics`, `sessions`, `appointment_refs`, `contact_prefs`, `consents`, `reminders`, `callback_requests`, `audit_log`, `staff_users`, `clinic_config_versions`;
   - one table added here: `idempotency_keys`;
   - roles: `app_owner`, `app_rw`, `app_ro`.

   Also included:
   - the async connection layer, using the Cloud SQL Python Connector in the cloud and a plain DSN locally;
   - a clinic-scoped repository base class;
   - migration tests in CI.

Done means:
- the instance exists in dev, staging and prod with the §6 settings;
- `alembic upgrade head` runs in CI against Postgres 16 and in dev against Cloud SQL;
- the schema stores **only references (PatNum, AptNum) and encrypted contact fields**, never copies of patient records;
- `app_rw` can't change or delete audit rows;
- every repository query is scoped by `clinic_id`.

## 2. Why this matters
Everything stateful in the product goes into this database:
- sessions, booked-appointment references, consents, reminders, callback cases, staff users, clinic configuration and the audit trail;
- in prod, it holds **PHI**: PatNums linked to phone numbers, callback contact details and summaries (flow F06 in P0-14).

The settings here carry three HIPAA safeguards from the risk register (P0-11):
- **encryption at rest** (R10, CMEK);
- **integrity of the audit trail** (R20, append-only roles);
- **availability** (R24, backups, PITR and HA).

CMEK and the network mode can only be chosen at creation.

The schema is the contract that more than 20 later tasks write against, so its names, types and constraints are fixed here once. Plan references: §5 (data model), §6 (encryption, audit, access control), §3.2 (stack).

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P1, Core Platform & Open Dental Adapter**.
- **What already exists:**
  - **P1-02:** VPC `vpc-main`, the PSA range output `psa_range_name`, `kms_key_ids.sql` (key ring `kr-<env>`, us-central1), service accounts `sa-api` and `sa-web`. Cloud Run `api` has Direct VPC egress with all traffic, and egress is allowed to the PSA ranges on 5432.
  - **P1-01:**
    - `backend/app/db/session.py` with `create_async_engine` + `async_sessionmaker`;
    - `Settings.DATABASE_URL`, `DB_POOL_SIZE`;
    - an empty Alembic async baseline;
    - `/readyz` runs `SELECT 1`;
    - local and CI Postgres is `postgres:16`.
  - **Decisions that shape the schema:**
    - #78: the messaging channel follows P0-07a (SMS by default, WhatsApp only if allowed), so columns say `messaging_address` and `channel`, not `whatsapp_number`.
    - #86: the booking horizon lives in clinic config.
    - P0-01 Q9: no transcripts are stored, so there is no transcript table.
    - #75 / F13: task payloads carry IDs only.
- **Facts to check at implementation** (Google docs, read 2026-11-24; marked **Verify** where we could not confirm the exact field):
  - Cloud SQL supports private IP through Private Service Access and CMEK chosen at creation (**Verify** that CMEK can't be added later, in the Cloud SQL CMEK page).
  - IAM database authentication needs the flag `cloudsql.iam_authentication=on`. A service-account IAM user's database username is the SA email **without** `.gserviceaccount.com`. A new IAM user has no table privileges until granted.
  - The **Cloud SQL Python Connector** (`cloud-sql-python-connector[asyncpg]`) supports asyncpg, `enable_iam_auth=True` and `ip_type="private"`, and is used with SQLAlchemy through `async_creator`. **Verify** the current API names in the connector README. It calls the Cloud SQL Admin API (`sqladmin.googleapis.com`), which must be in `allowed_services.yaml` and reachable through the restricted VIP.
  - PITR on the Enterprise edition keeps transaction logs for up to 7 days; up to 35 on Enterprise Plus. **Verify** both numbers.
  - `pgaudit` is enabled with the flag `cloudsql.enable_pgaudit=on` plus `CREATE EXTENSION pgaudit`.

## 4. Scope
**In scope**
- **Terraform** in `infra/modules/cloud_sql/` (inputs, outputs and README, same style as P1-02), called from `infra/env/{dev,staging,prod}`:
  - the instance with its flags, backups, PITR, maintenance window and Query Insights (without client addresses);
  - database `app`;
  - IAM users `sa-api` and `sa-migrate`;
  - a new service account `sa-migrate`, used by the migration job in P1-06;
  - `roles/cloudsql.client` and `roles/cloudsql.instanceUser` for both SAs.
- **Database roles and grants** created by the first migration: `app_owner`, `app_rw`, `app_ro`.
- **Alembic migrations** for all tables in §6, with indexes, constraints, the append-only triggers and the `current_consents` view.
- **SQLAlchemy models** in `backend/app/db/models/` (one module per area) and shared enums in `backend/app/db/enums.py`.
- **Connection layer:** `db/session.py` gains the Cloud SQL connector path, plus new `Settings` fields (§6, extending P1-01).
- **`ClinicScopedRepository` base class** and the rule that every query filters on `clinic_id`.
- **Dev seed:** one clinic row for the Open Dental test DB (P0-12) with config version 1.
- **Tests:** migrations up and down, drift check, role and grant tests, append-only triggers, the "no plaintext PHI columns" test, and clinic scoping.
- **`docs/architecture/data-model.md`:** an ER diagram (Mermaid) and the column-level PHI classification.

**Out of scope** (and which task covers it)
- Encrypting and decrypting the `*_enc` columns and computing the `*_bidx` blind indexes → P1-05 (absorbs P1-10). This task only defines the columns and their format contract.
- The audit writing API (`audit()` helper) → P1-07 (absorbs P1-12). This task creates the table and its protections.
- Staff authentication, MFA, Identity Platform → P1-13 (this task creates `staff_users`).
- The clinic config JSON schema and its validation → P1-19 (this task stores it as versioned JSONB).
- Session state in Redis → P2-01.
- Retention and deletion jobs, and the restore drill → P5-12.
- Postgres row-level security → later, when a second clinic is onboarded (P5-14).
- Running migrations in the deploy pipeline (Cloud Run job) → P1-06 (uses `sa-migrate` and the commands here).

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P1-02 Terraform base (approved spec) | `network_id`, `psa_range_name`, `kms_key_ids.sql`, `sa-api` | Write the module and run `terraform validate`; apply after P1-02 is applied in dev. |
| P1-01 Repo skeleton (approved spec) | `db/session.py`, `Base`, Alembic baseline, CI Postgres service | All schema work runs locally against `docker compose up postgres` (`postgres:16`); no cloud needed. |
| P1-05 Field encryption | Real `encrypt()` / `blind_index()` | Not needed: the schema stores `bytea`. Tests insert fake bytes (`b"\x01fake"`). |
| P1-06 CI/CD | Migration job in the pipeline | Run `alembic upgrade head` by hand in dev through the Cloud SQL Auth Proxy (§7). |

## 6. Interface contract

### Terraform module `cloud_sql`
| Input | Example (prod) | Notes |
|---|---|---|
| `project_id`, `region` | `acme-dai-prod`, `us-central1` | |
| `network_id`, `psa_range_name` | from P1-02 | private IP only |
| `kms_key_id` | `kms_key_ids["sql"]` | creation-time only |
| `tier` | `db-custom-2-7680` (dev/staging `db-custom-1-3840`) | **Verify** tier names and sizing; P5-03 tunes |
| `availability_type` | `REGIONAL` (dev/staging `ZONAL`) | |
| `iam_users` | `["sa-api", "sa-migrate"]` | SA account IDs |
| `deletion_protection` | `true` (dev `false`) | |

Outputs: `instance_connection_name` (`project:region:instance`), `private_ip`, `database_name`, `iam_db_users` (map SA → database username).

```hcl
resource "google_sql_database_instance" "main" {
  name                = "pg-main"
  region              = var.region
  database_version    = "POSTGRES_16"                 # same as local/CI; Verify 17 later
  encryption_key_name = var.kms_key_id                # CMEK, creation-time only
  deletion_protection = var.deletion_protection

  settings {
    edition           = "ENTERPRISE"
    tier              = var.tier
    availability_type = var.availability_type
    disk_type         = "PD_SSD"
    disk_size         = 20
    disk_autoresize   = true

    ip_configuration {
      ipv4_enabled       = false                      # no public IP (also enforced by P0-06 org policy)
      private_network    = var.network_id
      allocated_ip_range = var.psa_range_name
      ssl_mode           = "ENCRYPTED_ONLY"           # Verify; TRUSTED_CLIENT_CERTIFICATE_REQUIRED is not needed with the connector
    }

    backup_configuration {
      enabled                        = true
      start_time                     = "08:00"        # UTC, about 3-4 am US Eastern
      location                       = "us"           # backups stay in the US
      point_in_time_recovery_enabled = true
      transaction_log_retention_days = 7
      backup_retention_settings {
        retained_backups = 30
        retention_unit   = "COUNT"
      }
    }

    maintenance_window {
      day          = 7                               # Sunday
      hour         = 9                               # UTC
      update_track = "stable"
    }

    insights_config {
      query_insights_enabled  = true
      record_application_tags = false
      record_client_address   = false
      query_string_length     = 1024
    }

    database_flags {
      name  = "cloudsql.iam_authentication"
      value = "on"
    }
    database_flags {
      name  = "cloudsql.enable_pgaudit"
      value = "on"
    }
    database_flags {
      name  = "pgaudit.log"
      value = "ddl,role"                             # schema and permission changes only; no read/write (would log statements)
    }
    database_flags {
      name  = "log_connections"
      value = "on"
    }
    database_flags {
      name  = "log_disconnections"
      value = "on"
    }
    database_flags {
      name  = "log_min_error_statement"
      value = "panic"                                # failing statements could contain values; never log them
    }
  }
}

resource "google_sql_database" "app" {
  name     = "app"
  instance = google_sql_database_instance.main.name
}

resource "google_sql_user" "iam" {
  for_each = toset(var.iam_users)                    # "sa-api", "sa-migrate"
  name     = trimsuffix("${each.key}@${var.project_id}.iam.gserviceaccount.com", ".gserviceaccount.com")
  instance = google_sql_database_instance.main.name
  type     = "CLOUD_IAM_SERVICE_ACCOUNT"
}
```
The flag names and values must be verified against the Cloud SQL supported-flags page before apply.

No built-in password users are created except the default `postgres` user. Its password is set to a random value, stored only in Secret Manager secret `sql-postgres-break-glass` (accessible to `gcp-org-admins` only), and used only for break-glass access (P5-12 runbook).

### Database roles (first migration, run as `sa-migrate`)
| Role | Login | Members | Privileges |
|---|---|---|---|
| `app_owner` | no | `sa-migrate` IAM user | Owns schema `app` and all objects; DDL. Migrations run `SET ROLE app_owner` so objects are owned by the role, not the user. |
| `app_rw` | no | `sa-api` IAM user | `USAGE` on schema; `SELECT, INSERT, UPDATE, DELETE` on all tables **except** `audit_log`, `consents` and `clinic_config_versions` (`SELECT, INSERT` only); `USAGE` on sequences. |
| `app_ro` | no | none yet (support access via P5) | `SELECT` on all tables. |

```sql
-- migration 0001_roles_and_schema (excerpt)
CREATE ROLE app_owner NOLOGIN;
CREATE ROLE app_rw NOLOGIN;
CREATE ROLE app_ro NOLOGIN;
CREATE SCHEMA app AUTHORIZATION app_owner;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA app TO app_rw, app_ro;
ALTER DEFAULT PRIVILEGES FOR ROLE app_owner IN SCHEMA app GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_rw;
ALTER DEFAULT PRIVILEGES FOR ROLE app_owner IN SCHEMA app GRANT USAGE ON SEQUENCES TO app_rw;
ALTER DEFAULT PRIVILEGES FOR ROLE app_owner IN SCHEMA app GRANT SELECT ON TABLES TO app_ro;
-- IAM user grants: the usernames come from Alembic -x args (env-specific), e.g.
--   alembic -x api_user=sa-api@acme-dai-dev.iam -x migrate_user=sa-migrate@acme-dai-dev.iam upgrade head
GRANT app_rw TO "sa-api@acme-dai-dev.iam";
GRANT app_owner TO "sa-migrate@acme-dai-dev.iam";
CREATE EXTENSION IF NOT EXISTS pgaudit;
```
Locally and in CI, the users are plain roles `app_api` and `app_migrate` with passwords (created by `docker/postgres/init.sql`), so the same grants are tested.

### Schema conventions
- **Schema:** everything lives in schema `app`; `search_path = app` is set on the connection.
- **IDs:** `uuid` primary keys with `DEFAULT gen_random_uuid()`, except `audit_log` (`bigint` identity) and natural composite keys where noted.
- **Time:** every timestamp is `timestamptz` in UTC. Columns are named `*_at`, plus `scheduled_for`.
- **Enums:** `text` columns with `CHECK (col IN (...))` constraints instead of Postgres enum types, which are easier to migrate. The same values live as Python `StrEnum`s in `db/enums.py`.
- **Tenancy:** every table has `clinic_id uuid NOT NULL REFERENCES clinics(id)`, except `clinics` itself. Every unique constraint and index starts with `clinic_id`.
- **Open Dental IDs:** `patnum bigint`, `aptnum bigint`. **Verify** the Open Dental type width; they are 64-bit integers in the Open Dental schema.
- **Encrypted PHI:** `<field>_enc bytea` holds ciphertext produced by P1-05. The format is P1-05's envelope: `version byte ‖ key id ‖ nonce ‖ ciphertext ‖ tag`. The schema treats it as opaque bytes. **Never a plaintext PHI column.**
- **Blind index:** `<field>_bidx bytea` holds 32 bytes of HMAC-SHA256 over the normalized value (E.164 phone, lowercase email), with a key from P1-05. It is used only for equality lookups, such as finding consents when an SMS STOP arrives from a number.
- **No free text from patients or the LLM** is stored outside `*_enc` columns. Reasons, errors and outcomes are stored as codes.
- **Timestamps:** `created_at timestamptz NOT NULL DEFAULT now()` on every table; `updated_at` where rows change, set by the app.

### Tables
PHI legend: **P** = PHI (encrypted or a link to a patient), **R** = reference (an Open Dental ID that is PHI only when combined with clinic data), **-** = not PHI.

**`clinics`**
| Column | Type | Constraints | PHI |
|---|---|---|---|
| `id` | uuid | PK | - |
| `slug` | text | UNIQUE, `CHECK (slug ~ '^[a-z0-9-]{3,40}$')` | - |
| `name` | text | NOT NULL | - |
| `timezone` | text | NOT NULL; IANA name, validated in the app with `zoneinfo` | - |
| `od_customer_key_secret` | text | NOT NULL; the Secret Manager secret name, e.g. `od-customer-key-<slug>` (never the key) | - |
| `active_config_version` | int | NULL until the first config; FK (`id`, version) → `clinic_config_versions`, deferrable | - |
| `status` | text | `ACTIVE`, `PAUSED`, `OFFBOARDED` | - |
| `created_at`, `updated_at` | timestamptz | | - |

**`clinic_config_versions`** (immutable rows; replaces plan §5 `clinic_config`)
| Column | Type | Constraints | PHI |
|---|---|---|---|
| `clinic_id` | uuid | PK part, FK | - |
| `version` | int | PK part, `> 0` | - |
| `config` | jsonb | NOT NULL; validated by P1-19's Pydantic model before insert. Holds hours, holidays, appointment types, emergency rules, policies (incl. `scheduling.booking_horizon_days`, DECISIONS #86), voice | - |
| `schema_version` | int | NOT NULL | - |
| `created_by_staff_id` | uuid | NULL (system), FK `staff_users` | - |
| `change_note` | text | NULL, ≤ 500 chars, staff-written (no PHI by policy) | - |
| `created_at` | timestamptz | | - |

**`staff_users`**
| Column | Type | Constraints | PHI |
|---|---|---|---|
| `id` | uuid | PK | - |
| `clinic_id` | uuid | FK | - |
| `idp_uid` | text | UNIQUE; Identity Platform user ID (P1-13) | - |
| `email` | text | NOT NULL; UNIQUE (`clinic_id`, lower(`email`)) | - (workforce) |
| `display_name` | text | NOT NULL | - |
| `role` | text | `ADMIN`, `FRONT_DESK`, `DENTIST`, `READ_ONLY` | - |
| `mfa_enrolled` | bool | NOT NULL DEFAULT false | - |
| `active` | bool | NOT NULL DEFAULT true | - |
| `last_login_at`, `created_at`, `updated_at` | timestamptz | | - |

**`sessions`** (one patient conversation; live state is in Redis, P2-01)
| Column | Type | Constraints | PHI |
|---|---|---|---|
| `id` | uuid | PK | - |
| `clinic_id` | uuid | FK | - |
| `channel` | text | `TEXT`, `VOICE` (the starting channel) | - |
| `status` | text | `ACTIVE`, `ENDED`, `EXPIRED`, `ESCALATED` | - |
| `end_reason` | text | NULL; codes: `COMPLETED`, `IDLE_TIMEOUT`, `USER_LEFT`, `EMERGENCY_911`, `CALLBACK_CREATED`, `ERROR` | - |
| `verified_patnum` | bigint | NULL until identity is verified | R |
| `channel_switches` | int | NOT NULL DEFAULT 0 | - |
| `started_at`, `last_activity_at`, `ended_at` | timestamptz | | - |

**`appointment_refs`** (appointments this system created or changed)
| Column | Type | Constraints | PHI |
|---|---|---|---|
| `id` | uuid | PK | - |
| `clinic_id` | uuid | FK; UNIQUE (`clinic_id`, `aptnum`) | - |
| `aptnum`, `patnum` | bigint | NOT NULL | R |
| `created_by_session_id` | uuid | NULL, FK `sessions` | - |
| `status_cache` | text | `SCHEDULED`, `CANCELLED`, `BROKEN`, `COMPLETE`, `UNKNOWN`; a cache only, Open Dental is the truth | - |
| `status_checked_at` | timestamptz | | - |
| `created_at`, `updated_at` | timestamptz | | - |

No appointment date or time, procedure or provider is stored (they are fetched from Open Dental when needed).

**`contact_prefs`**
| Column | Type | Constraints | PHI |
|---|---|---|---|
| `clinic_id` | uuid | PK part | - |
| `patnum` | bigint | PK part | R |
| `channel` | text | `SMS`, `WHATSAPP` | - |
| `messaging_address_enc` | bytea | NOT NULL | P |
| `messaging_address_bidx` | bytea | NOT NULL, length 32; index (`clinic_id`, `messaging_address_bidx`) | P (hash) |
| `created_at`, `updated_at` | timestamptz | | - |

**`consents`** (append-only history; current state = latest row)
| Column | Type | Constraints | PHI |
|---|---|---|---|
| `id` | uuid | PK | - |
| `clinic_id` | uuid | FK | - |
| `patnum` | bigint | NULL when the event arrived by address only (e.g. STOP from an unknown number) | R |
| `messaging_address_bidx` | bytea | NOT NULL | P (hash) |
| `channel` | text | `SMS`, `WHATSAPP` | - |
| `purpose` | text | `APPOINTMENT_MESSAGES` | - |
| `action` | text | `GRANTED`, `REVOKED` | - |
| `source` | text | `CHAT`, `VOICE`, `SMS_STOP`, `SMS_START`, `STAFF` (plus `WHATSAPP_STOP`, `WHATSAPP_START` from P4-01) | - |
| `staff_reason` | text | NULL; added by P4-02: `PATIENT_REQUEST_PHONE`, `PATIENT_REQUEST_IN_PERSON`, `SIGNED_FORM`, `WRONG_NUMBER`, `OTHER_REVOKE`; NOT NULL when `source='STAFF'` | - |
| `wording_version` | text | NOT NULL for `GRANTED` (template ID from P0-15, e.g. `optin-v1`) | - |
| `session_id` | uuid | NULL, FK | - |
| `staff_user_id` | uuid | NULL, FK | - |
| `occurred_at` | timestamptz | NOT NULL | - |

View `current_consents`: `DISTINCT ON (clinic_id, messaging_address_bidx, channel, purpose) … ORDER BY …, occurred_at DESC`. A reminder may be sent only if the current row is `GRANTED` (P4-04).

> **Addition (P4-01, DECISIONS #253):** `consents.source` also allows `WHATSAPP_STOP` and `WHATSAPP_START` (WhatsApp has no carrier-level STOP; P4-01 handles the keywords). P4-01's migration also adds the table **`outbound_messages`** (one row per patient message: type, template ID, policy version, PatNum, AptNum, optional `reminder_id`, address blind index, `dedupe_key` unique per clinic, status `QUEUED`/`SENDING`/`SENT`/`DELIVERED`/`READ`/`FAILED`/`SKIPPED`, reason and provider error code, `provider_msg_id`, timestamps, acknowledgement). It never stores the message body or the number in clear text; full definition in P4-01 §6.7.

> **Addition (P4-11, DECISIONS #264):** table **`config_change_requests`** (`id`, `clinic_id`, `section`, `kind`, `description_enc` field-level encrypted, `dentist_agrees`, `status` `OPEN`/`IN_REVIEW`/`DONE`/`REJECTED`, `created_by`, `resolution_note`, `created_at`, `resolved_at`). Requests to change file-only config such as emergency rules; full definition in P4-11 §6.8.

> **Addition (P5-12, DECISIONS #278):** `callback_requests.phi_purged_at timestamptz NULL` (also on `config_change_requests`); each NOT NULL PHI column gets the check `(<col> IS NOT NULL) OR (phi_purged_at IS NOT NULL) OR <existing URGENT rule>`, so the retention job can blank PHI and keep the row.

> **Addition (P6-02, DECISIONS #281):** table **`kpi_daily`** (`clinic_id`, `day`, `kpi` as PK; `numerator`, `denominator`, `value`, `details` jsonb with counters only, `computed_at`). No PHI, no IDs.

> **Addition (P6-04, DECISIONS #282):** table **`conversation_transcripts`** (`id`, `clinic_id`, `session_id`, `turn_index`, `speaker`, `channel`, `text_enc` field-encrypted, `created_at`, `expires_at` indexed). Written only when `privacy.transcript_retention_days` > 0 (pilot, clinic consent); purged by the P5-12 retention job.

> **Addition (P4-13a, DECISIONS #266):** table **`callback_attempts`** (`id`, `clinic_id`, `callback_id`, `attempt_no` UNIQUE per case, `outcome` ∈ `NO_ANSWER`/`LEFT_VOICEMAIL`/`WRONG_NUMBER`/`SPOKE_WITH_PATIENT`/`APPOINTMENT_MADE`/`OTHER`, `staff_id`, `occurred_at`), append-only for `app_rw` like `audit_log`; `appointment_refs.reviewed_at` / `reviewed_by`; index `ix_audit_session_actor` on `audit_log` (`clinic_id`, `actor_id`, `occurred_at`) WHERE `actor_type = 'PATIENT_SESSION'`. No free-text columns. Full definition in P4-13a §6.4.

**`reminders`**
| Column | Type | Constraints | PHI |
|---|---|---|---|
| `id` | uuid | PK | - |
| `clinic_id` | uuid | FK | - |
| `aptnum`, `patnum` | bigint | NOT NULL | R |
| `kind` | text | `BEFORE_1H` (more kinds later) | - |
| `scheduled_for` | timestamptz | NOT NULL (UTC send time) | P (linked to a patient, it reveals an appointment time) |
| `status` | text | `PENDING`, `ENQUEUED`, `SENT`, `SKIPPED`, `FAILED`, `CANCELLED` | - |
| `skip_reason` | text | NULL; codes: `NO_CONSENT`, `APPT_CANCELLED`, `APPT_MOVED`, `TOO_LATE` (P4-04 adds `VERIFY_FAILED`, `REMINDERS_DISABLED`) | - |
| `offset_minutes` | int | NOT NULL DEFAULT 60, CHECK 30–240; added by P4-04: the clinic offset in force when the row was created, so the expected appointment start is `scheduled_for + offset_minutes` (DECISIONS #260) | - |
| `task_name` | text | NULL; the Cloud Tasks task ID (P1-02 `enqueue()`) | - |
| `attempts` | int | NOT NULL DEFAULT 0 | - |
| `provider_msg_id` | text | NULL | - |
| `last_error_code` | text | NULL; provider error code only, never the provider's message text | - |
| `created_at`, `updated_at` | timestamptz | | - |

Constraints and indexes: UNIQUE (`clinic_id`, `aptnum`, `kind`, `scheduled_for`); index (`status`, `scheduled_for`), used by the reminder sweep (DECISIONS #92).

**`callback_requests`**
| Column | Type | Constraints | PHI |
|---|---|---|---|
| `id` | uuid | PK | - |
| `clinic_id` | uuid | FK | - |
| `session_id` | uuid | NULL, FK | - |
| `patient_type` | text | `NEW`, `EXISTING`, `UNKNOWN` | - |
| `patnum` | bigint | NULL | R |
| `contact_name_enc` | bytea | NOT NULL | P |
| `contact_phone_enc` | bytea | NOT NULL | P |
| `contact_phone_bidx` | bytea | NOT NULL | P (hash) |
| `reason_code` | text | `BOOKING_FAILED`, `NO_SLOTS`, `IDENTITY_UNVERIFIED`, `INSURANCE_BILLING`, `CLINICAL_QUESTION`, `URGENT_DENTAL`, `PATIENT_REQUEST`, `SYSTEM_ERROR`, `OTHER` | - |
| `urgency` | text | `ROUTINE`, `URGENT` | - |
| `summary_enc` | bytea | NOT NULL (LLM- or template-generated summary) | P |
| `status` | text | `OPEN`, `CONTACTED`, `RESOLVED` | - |
| `email_status` | text | `PENDING`, `SENT`, `FAILED` | - |
| `email_attempts` | int | NOT NULL DEFAULT 0 | - |
| `assigned_to_staff_id` | uuid | NULL, FK | - |
| `created_at`, `updated_at`, `contacted_at`, `resolved_at` | timestamptz | | - |

Additive (P2-20, DECISIONS #203): `contact_name_enc`, `contact_phone_enc` and `contact_phone_bidx` are NULLable, with a check constraint allowing NULL only when `urgency = 'URGENT'` and `reason_code = 'URGENT_DENTAL'` (emergency case created before contact details are known; filled later by `update_contact`).

Additive (P2-22, DECISIONS #207): `case_ref` (UNIQUE per clinic), `reason_detail`, `extra_reasons text[]`, `contact_dob_enc`, `contact_email_enc`, `preferred_time_enc` (P), `email_seq`, `email_sent_seq`, `email_last_error`, `email_sent_at`, `upgraded_at`; partial unique index `ux_callback_open_session` on `session_id` WHERE `status = 'OPEN'` (one open case per session).

Indexes: (`clinic_id`, `status`, `urgency`, `created_at` DESC) for the console list (P4-09); (`email_status`, `created_at`) for the unsent-email check (P2-22).

**`audit_log`** (append-only)
| Column | Type | Constraints | PHI |
|---|---|---|---|
| `id` | bigint | identity PK | - |
| `clinic_id` | uuid | NULL (system-wide events) | - |
| `occurred_at` | timestamptz | NOT NULL DEFAULT now() | - |
| `actor_type` | text | `SYSTEM`, `STAFF`, `PATIENT_SESSION` | - |
| `actor_id` | text | staff ID, session ID or service name | - |
| `action` | text | NOT NULL; dotted code, e.g. `patient.search`, `appointment.book`, `auth.login_failed`, `config.update` (P1-07 owns the list) | - |
| `object_type` | text | NULL; e.g. `patient`, `appointment`, `callback`, `config` | - |
| `object_ref` | text | NULL; IDs only (PatNum, AptNum, UUID) | R |
| `result` | text | `SUCCESS`, `FAILURE`, `DENIED` | - |
| `ip` | inet | NULL | - |
| `request_id` | text | NULL | - |
| `details` | jsonb | NULL; codes and IDs only, keys allow-listed by P1-07 | - |

**`idempotency_keys`** (makes book, reschedule, cancel and create-patient safe to retry)
| Column | Type | Constraints | PHI |
|---|---|---|---|
| `clinic_id` | uuid | PK part | - |
| `key` | text | PK part; built by the caller, e.g. `book:<session_id>:<slot_hash>` | - |
| `operation` | text | `BOOK`, `RESCHEDULE`, `CANCEL`, `CREATE_PATIENT` | - |
| `request_hash` | bytea | NOT NULL; SHA-256 of the canonical request, to detect key reuse with different input | - |
| `status` | text | `IN_PROGRESS`, `SUCCEEDED`, `FAILED` | - |
| `result_ref` | text | NULL; AptNum or PatNum | R |
| `created_at`, `expires_at` | timestamptz | `expires_at` = created + 24 h | - |

### Append-only triggers
```sql
CREATE FUNCTION app.reject_change() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'table % is append-only', TG_TABLE_NAME USING ERRCODE = 'insufficient_privilege';
END $$;

CREATE TRIGGER audit_log_no_update BEFORE UPDATE OR DELETE OR TRUNCATE ON app.audit_log
  FOR EACH STATEMENT EXECUTE FUNCTION app.reject_change();
-- same for app.consents and app.clinic_config_versions
REVOKE UPDATE, DELETE, TRUNCATE ON app.audit_log, app.consents, app.clinic_config_versions FROM app_rw;
```
The retention job (P5-12) deletes old rows as `app_owner` and disables the trigger only inside its own transaction (`ALTER TABLE … DISABLE TRIGGER` needs ownership). Each such run is itself audited.

### Settings and connection (extends P1-01)
```python
# backend/app/core/config.py (additions)
class Settings(BaseSettings):
    DATABASE_URL: PostgresDsn | None = None          # local/CI: postgresql+asyncpg://app_api:app@localhost:5432/app
    CLOUDSQL_INSTANCE: str | None = None             # cloud: "acme-dai-dev:us-central1:pg-main"
    DB_IAM_USER: str | None = None                   # cloud: "sa-api@acme-dai-dev.iam"
    DB_NAME: str = "app"
    DB_SCHEMA: str = "app"

    @model_validator(mode="after")
    def _one_db_mode(self) -> "Settings":
        if (self.DATABASE_URL is None) == (self.CLOUDSQL_INSTANCE is None):
            raise ValueError("set exactly one of DATABASE_URL or CLOUDSQL_INSTANCE")
        if self.CLOUDSQL_INSTANCE and not self.DB_IAM_USER:
            raise ValueError("DB_IAM_USER is required with CLOUDSQL_INSTANCE")
        if self.ENV in (Env.DEV, Env.STAGING, Env.PROD) and self.DATABASE_URL is not None:
            raise ValueError("cloud environments must use CLOUDSQL_INSTANCE (IAM auth)")
        return self
```
```python
# backend/app/db/session.py
from google.cloud.sql.connector import IPTypes, create_async_connector
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

async def create_engine(settings: Settings) -> tuple[AsyncEngine, Connector | None]:
    connect_args = {"server_settings": {"search_path": settings.DB_SCHEMA, "application_name": settings.SERVICE_NAME}}
    common = {"pool_size": settings.DB_POOL_SIZE, "pool_pre_ping": True, "pool_recycle": 1800}
    if settings.DATABASE_URL is not None:
        return create_async_engine(str(settings.DATABASE_URL), connect_args=connect_args, **common), None

    connector = await create_async_connector()       # closed in the app lifespan shutdown

    async def getconn() -> asyncpg.Connection:
        return await connector.connect_async(
            settings.CLOUDSQL_INSTANCE, "asyncpg",
            user=settings.DB_IAM_USER, db=settings.DB_NAME,
            enable_iam_auth=True, ip_type=IPTypes.PRIVATE,
            server_settings=connect_args["server_settings"],
        )

    return create_async_engine("postgresql+asyncpg://", async_creator=getconn, **common), connector
```
The lifespan from P1-01 stores the connector and calls `await connector.close_async()` on shutdown. Cloud Run env (set in P1-02's module): `CLOUDSQL_INSTANCE`, `DB_IAM_USER`. No database password exists in the cloud.

### Model example and repository base
```python
# backend/app/db/models/reminders.py
class Reminder(Base):
    __tablename__ = "reminders"
    __table_args__ = (
        UniqueConstraint("clinic_id", "aptnum", "kind", "scheduled_for", name="uq_reminders_apt_kind_time"),
        Index("ix_reminders_status_due", "status", "scheduled_for"),
        CheckConstraint(f"status IN ({sql_in(ReminderStatus)})", name="ck_reminders_status"),
        {"schema": "app"},
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    clinic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app.clinics.id"), nullable=False)
    aptnum: Mapped[int] = mapped_column(BigInteger, nullable=False)
    patnum: Mapped[int] = mapped_column(BigInteger, nullable=False)
    kind: Mapped[ReminderKind] = mapped_column(Text, nullable=False)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[ReminderStatus] = mapped_column(Text, nullable=False, default=ReminderStatus.PENDING)
    ...
```
```python
# backend/app/db/repository.py
class ClinicScopedRepository[M: ClinicScoped]:
    """Every read and write is filtered by clinic_id; there is no unscoped method."""
    model: type[M]

    def __init__(self, session: AsyncSession, clinic_id: uuid.UUID) -> None: ...
    def select(self) -> Select[tuple[M]]:            # select(self.model).where(self.model.clinic_id == self.clinic_id)
    async def get(self, id_: uuid.UUID) -> M | None: ...
    async def add(self, obj: M) -> M: ...            # sets obj.clinic_id; raises ClinicMismatchError if set to another clinic
```
`ClinicScoped` is a mixin that declares `clinic_id`. Raw `session.execute(select(Model))` on a clinic-scoped model outside a repository is flagged by a test (§10, T6).

### Migration commands
```bash
cd backend
uv run alembic revision --autogenerate -m "describe change"   # review the file by hand, always
uv run alembic upgrade head
uv run alembic downgrade -1
uv run alembic check                                         # fails if models and migrations differ (CI)
# dev via Cloud SQL Auth Proxy (IAM, private IP; run from a host inside the VPC or perimeter, Verify access path):
cloud-sql-proxy --auto-iam-authn --private-ip acme-dai-dev:us-central1:pg-main &
DATABASE_URL=postgresql+asyncpg://sa-migrate%40acme-dai-dev.iam@127.0.0.1:5432/app \
  uv run alembic -x api_user=sa-api@acme-dai-dev.iam -x migrate_user=sa-migrate@acme-dai-dev.iam upgrade head
```
Migration file names: `NNNN_<slug>.py` (`0001_roles_and_schema`, `0002_core_tables`, …). Every migration has a working `downgrade()`, except where it would drop PHI-bearing data in prod; there the migration refuses with a clear error and the runbook explains the manual step.

## 7. Implementation guide
1. **Read** plan §5 and §6; P0-14 flows F06 and F14; P1-01 `session.py` and `Settings`; P1-02 outputs; DECISIONS #75, #78, #86, #92.
2. **Terraform module** `cloud_sql` (§6):
   1. add `sqladmin.googleapis.com` and `sql-component.googleapis.com` to `allowed_services.yaml` if they are missing (P0-06 PR);
   2. create `sa-migrate` and grant `roles/cloudsql.client` + `roles/cloudsql.instanceUser` to `sa-api` and `sa-migrate`;
   3. apply in dev, then check the settings with `gcloud sql instances describe` (§10 N-tests).
3. **Local roles:** add `docker/postgres/init.sql` creating login roles `app_api` and `app_migrate`; update `docker-compose.yml` and the CI service so `DATABASE_URL` uses `app_api` and migrations use `app_migrate`.
4. **Enums and models:** write `db/enums.py` (one `StrEnum` per CHECK list), the `ClinicScoped` mixin, and the models for every table in §6.
5. **Migrations:**
   1. `0001_roles_and_schema`: roles, schema, default privileges, IAM grants from `-x` args, `pgaudit`;
   2. `0002_core_tables`: all tables, constraints and indexes;
   3. `0003_append_only_and_views`: triggers, revokes, `current_consents`;
   4. `0004_dev_seed`: only when `-x seed=dev`; one clinic `pilot-test-db` with `od_customer_key_secret=od-customer-key-testdb` and config version 1 = `{}` placeholder until P1-19.
6. **Connection layer:** the `Settings` additions and `create_engine` (§6). Add the `cloud-sql-python-connector[asyncpg]` dependency, pinned (**Verify** the current version).
7. **Repository base** and the clinic-scoping lint test.
8. **Tests** (§10) and CI: add `alembic upgrade head`, `alembic check`, `alembic downgrade base` and `upgrade head` again to the `backend` job.
9. **Docs:** `docs/architecture/data-model.md` with a Mermaid ER diagram and the PHI column table (copy the §6 PHI legend).
10. **Dev:** run the migrations through the proxy, deploy `api` with `CLOUDSQL_INSTANCE`, and check that `/readyz` returns 200.
11. **Notify:**
    - P1-05: the `*_enc` and `*_bidx` columns and their format contract;
    - P1-06: `sa-migrate`, the migration commands, `-x` args;
    - P1-07: `audit_log` columns, the append-only rules;
    - P1-13: `staff_users`;
    - P1-19: `clinic_config_versions`, `active_config_version`;
    - P2-01 and P2-16: `sessions`, `idempotency_keys`;
    - P4-02 and P4-04: `consents`, `current_consents`, `reminders`;
    - P2-22: `callback_requests`;
    - P5-12: retention, break-glass and backups.

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| Instance created without CMEK or with a public IP | Can't be fixed in place. In dev, recreate it. In staging or prod, create a new instance and migrate data (export/import), with a runbook entry. The org policy (P0-06) blocks public IP. |
| `app_rw` tries `UPDATE`/`DELETE` on `audit_log`, `consents` or `clinic_config_versions` | Permission denied (revoked), plus the trigger as a second layer. The app maps it to `AppError` 500 and alerts (P1-07): this is a bug or an attack. |
| A migration fails halfway | Postgres runs DDL in a transaction, so it rolls back; the deploy stops (P1-06). Migrations must not mix DDL with long data backfills; backfills go in separate migrations. |
| `alembic check` finds drift between models and migrations | CI fails; generate and review a migration. |
| Connector can't reach the Cloud SQL Admin API (VPC-SC or DNS) | `/readyz` returns 503 and the revision never becomes ready; check `sqladmin` in the allow-list and perimeter. |
| IAM user exists but has no grants | Queries fail with "permission denied for schema app"; re-run migration `0001` with the right `-x api_user`. |
| Two concurrent bookings with the same idempotency key | The `INSERT … ON CONFLICT DO NOTHING` on `idempotency_keys` lets exactly one proceed; the other reads the row and returns its result or "in progress" (P2-16 owns the flow). |
| Same key reused with a different request (`request_hash` differs) | Raise `IdempotencyConflictError` (409); never return the old result. |
| STOP arrives from a number that has no `contact_prefs` row | Insert a `consents` row with `patnum = NULL` and the `messaging_address_bidx`; any future reminder lookup by address sees `REVOKED`. |
| HA failover in prod | A short outage (Cloud SQL docs describe about a minute, **Verify**). `pool_pre_ping` drops dead connections; requests in flight fail with 503 and the client retries. |
| PITR restore needed | Restore to a new instance at a timestamp (P5-12 runbook); point `CLOUDSQL_INSTANCE` to it. |
| Repository receives an object with another clinic's `clinic_id` | `ClinicMismatchError`, and the event is audited as `security.clinic_mismatch`. |

## 9. Security, HIPAA and PHI
- **PHI in this task's tables:**
  - **encrypted:** messaging address, callback contact name and phone, callback summary;
  - **references** (PHI in context): PatNum, AptNum, `verified_patnum`, reminder `scheduled_for`;
  - **hashes:** blind indexes.
- **Not stored at all:** names, DOB, addresses, insurance, clinical notes, appointment details, transcripts, audio. Those stay in Open Dental, or are never kept (P0-01 Q9).
- **Protection:**
  - private IP only, reached through Direct VPC egress inside the VPC-SC perimeter;
  - CMEK on the instance and its backups (key in us-central1, 90-day rotation);
  - SSL enforced;
  - IAM authentication for the app, so there are no passwords;
  - field encryption on PHI columns (P1-05);
  - least-privilege roles;
  - append-only audit and consent history;
  - backups kept in the US.
- **Logging:**
  - `pgaudit` logs DDL and role changes only;
  - `log_min_error_statement=panic` keeps failing SQL text, which may contain values, out of the logs;
  - Query Insights has client addresses off. Queries are parameterized, so the stored query text holds placeholders, not values. **Verify** in Insights after the first load test.
  - The app never logs row contents (P1-07 redaction).
- **Access:**
  - only `sa-api` (runtime) and `sa-migrate` (deploy) can connect;
  - human access is break-glass only (`postgres` password in Secret Manager, `gcp-org-admins`), with every use audited by Cloud Audit Logs and P5-12.
- **HIPAA safeguards covered:**
  - §164.312(a)(2)(iv) encryption;
  - §164.312(b) audit controls;
  - §164.312(c)(1) integrity;
  - §164.308(a)(7) contingency (backup and PITR).

## 10. Testing
Unit and integration tests (`backend/tests/integration/db/`, against the CI Postgres 16 service):

| # | Test | Expected |
|---|---|---|
| T1 | `alembic upgrade head` on an empty database, then `alembic check` | Succeeds; no drift |
| T2 | `downgrade base` then `upgrade head` | Succeeds both ways |
| T3 | As `app_api`: `UPDATE app.audit_log …`, `DELETE FROM app.consents …`, `UPDATE app.clinic_config_versions …` | Each raises `InsufficientPrivilegeError` |
| T4 | As `app_migrate` with `SET ROLE app_owner`: `UPDATE app.audit_log …` | Raises from the trigger (`append-only`) |
| T5 | **No plaintext PHI columns:** inspect `Base.metadata`; any column whose name matches `phone|email|name|address|dob|birth|summary|note|reason_text` must be `bytea` and end in `_enc` or `_bidx`, unless it is in the allow-list (`staff_users.email`, `staff_users.display_name`, `clinics.name`) | Pass; adding a plaintext PHI column fails CI |
| T6 | **Clinic scoping:** AST scan of `backend/app/` for `select(<ClinicScoped model>)` outside `db/repository.py` | None found |
| T7 | `ClinicScopedRepository(clinic A).get(id of a clinic B row)` | Returns `None` |
| T8 | Insert two `reminders` with the same (`clinic_id`, `aptnum`, `kind`, `scheduled_for`) | Second raises `UniqueViolationError` |
| T9 | `current_consents` after GRANTED then REVOKED for one address | One row, `REVOKED` |
| T10 | Insert an invalid enum value (e.g. `status='DONE'`) | `CheckViolationError` |
| T11 | `Settings` with both or neither of `DATABASE_URL`/`CLOUDSQL_INSTANCE`; `ENV=prod` with `DATABASE_URL` | `ValidationError` |
| T12 | `create_engine` in connector mode with a mocked `create_async_connector` | Calls `connect_async(..., enable_iam_auth=True, ip_type=PRIVATE)` |

Cloud checks in dev, recorded in `docs/runbooks/terraform.md`:
```bash
gcloud sql instances describe pg-main --format="yaml(settings.ipConfiguration,settings.backupConfiguration,diskEncryptionConfiguration,settings.availabilityType,settings.databaseFlags)"
# expect: ipv4Enabled false, privateNetwork set, sslMode ENCRYPTED_ONLY,
#         backups enabled + pointInTimeRecoveryEnabled true + 7-day logs + 30 retained,
#         kmsKeyName .../cryptoKeys/sql, flags as in §6
curl https://api.<domain>/readyz          # 200 with the connector path
```
N-tests:
- an attempt to connect from outside the VPC to the private IP fails;
- an attempt to log in as `sa-web` fails (not a database user).

## 11. Acceptance criteria
- [ ] Cloud SQL `pg-main` exists in dev, staging and prod: Postgres 16, private IP only, CMEK with the `sql` key, `ENCRYPTED_ONLY` SSL, daily backups kept 30, PITR with 7 days of logs, backups in the US, `REGIONAL` HA in prod, deletion protection in staging and prod
- [ ] IAM database auth is on; `sa-api` and `sa-migrate` are IAM database users; no other login users except the break-glass `postgres`, whose password is only in Secret Manager
- [ ] Migrations create schema `app`, roles `app_owner`/`app_rw`/`app_ro`, and all 11 tables of §6 with their constraints and indexes; `alembic check` reports no drift (T1, T2)
- [ ] `audit_log`, `consents` and `clinic_config_versions` are append-only for the app (T3, T4)
- [ ] No plaintext PHI column exists; PHI fields are `bytea` `_enc`/`_bidx` (T5); only Open Dental IDs are stored, no patient record copies
- [ ] Every clinic-scoped query goes through `ClinicScopedRepository` (T6, T7)
- [ ] The app connects in dev with the connector (IAM, private IP) and `/readyz` returns 200; locally and in CI it connects with `DATABASE_URL`
- [ ] CI runs T1–T12 on every PR
- [ ] `docs/architecture/data-model.md` (ER diagram + PHI classification) is written; the §7 step 11 issues are notified

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI (T1–T12)
- [ ] PR reviewed (HIPAA review if labelled `phi`): labelled `phi`; reviewed by the tech lead and the compliance owner (PHI columns, roles, logging flags)
- [ ] No PHI in logs: database flags as in §6; tests use fake bytes; no row contents logged
- [ ] Docs / README updated: module README, `data-model.md`, `terraform.md`, migration commands in `backend/README.md`

## 13. Hand-off
| Task | Can rely on |
|---|---|
| P1-05 Field encryption | Columns `*_enc` (opaque `bytea`) and `*_bidx` (32-byte HMAC); it provides `encrypt`, `decrypt`, `blind_index` and the envelope format |
| P1-06 CI/CD | `sa-migrate`; run `alembic … upgrade head` as a Cloud Run job before each deploy; `alembic check` in CI |
| P1-07 Audit/logging | `audit_log` table and columns, append-only enforcement, `details` keys must be allow-listed |
| P1-13 Staff auth | `staff_users` (`idp_uid`, `role`, `mfa_enrolled`, `active`) |
| P1-19 Clinic config | `clinic_config_versions` (immutable versions), `clinics.active_config_version`, `clinics.timezone` |
| P1-15 Open Dental client | `clinics.od_customer_key_secret` (secret name per clinic) |
| P2-01, P2-16, P2-18 | `sessions`, `appointment_refs`, `idempotency_keys` with conflict semantics |
| P2-22 / P4-09 | `callback_requests` and its indexes |
| P4-02, P4-04 | `contact_prefs`, `consents`, `current_consents`, `reminders` (unique key, sweep index, skip codes) |
| P5-12 | Retention runs as `app_owner`; break-glass access; backups and PITR for the restore drill |

## 14. Open questions
| Question | Owner | Needed by |
|---|---|---|
| Is the prod tier `db-custom-2-7680` enough for the pilot, or should P5-03 load tests decide before go-live? | Tech lead | Prod apply (can be resized later with a short restart) |
| Is 30 days of backups enough, or does the clinic's retention policy (P0-09) require longer? | Compliance owner | Prod apply |
| Who may use break-glass database access, and how is it approved? | Compliance owner (with P5-12) | Before PHI (gate) |

## 15. References
- Plan §3.2, §5, §6
- Cloud SQL private IP: https://docs.cloud.google.com/sql/docs/postgres/private-ip
- Cloud SQL CMEK: https://docs.cloud.google.com/sql/docs/postgres/cmek
- IAM database authentication: https://docs.cloud.google.com/sql/docs/postgres/iam-authentication
- Backups and PITR: https://docs.cloud.google.com/sql/docs/postgres/backup-recovery/backups, https://docs.cloud.google.com/sql/docs/postgres/backup-recovery/pitr
- Database flags: https://docs.cloud.google.com/sql/docs/postgres/flags
- pgAudit on Cloud SQL: https://docs.cloud.google.com/sql/docs/postgres/pg-audit
- Connect from Cloud Run: https://docs.cloud.google.com/sql/docs/postgres/connect-run
- Cloud SQL Python Connector: https://github.com/GoogleCloudPlatform/cloud-sql-python-connector
- Terraform `google_sql_database_instance`: https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/sql_database_instance
- Alembic: https://alembic.sqlalchemy.org/
- HIPAA Security Rule 45 CFR §164.308, §164.312
- Related tasks: P0-01, P0-06, P0-09, P0-11, P0-14, P1-01, P1-02, P1-05, P1-06, P1-07, P1-13, P1-15, P1-19, P2-01, P2-16, P2-18, P2-22, P4-02, P4-04, P4-09, P5-03, P5-12, P5-14
