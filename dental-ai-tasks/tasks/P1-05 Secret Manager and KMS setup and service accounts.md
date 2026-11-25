---
id: P1-05
title: Service accounts and IAM, Secret Manager, KMS and field-level encryption
milestone: P1
epic: E1.1
size: L
labels: area:infra, area:security, area:backend, type:feature, phi
depends_on: P1-02, P1-03
status: approved
---

# P1-05: Service accounts and IAM, Secret Manager, KMS and field-level encryption

## 1. Summary
This issue sets up who can access what, where secrets live, and how PHI columns are encrypted. It also absorbs **P1-10 (Field-level encryption helper, KMS envelope encryption)**.

1. **Service accounts and IAM (Terraform):**
   - one service account per workload, with only the roles it needs, granted on single resources (one secret, one key, one queue) wherever possible;
   - the human access model: standing access in dev only; staging and prod through time-limited, approved elevation;
   - an IAM audit script that fails on over-broad bindings.
2. **Secret Manager:**
   - the complete secret inventory, with names, accessors and owning tasks;
   - the secrets are created empty by Terraform; values are added by a person or a script, never by Terraform and never committed;
   - the mapping from secret to Cloud Run env var.
3. **KMS key `app-fields`** (the key-encryption key, KEK) and two **Tink keysets** stored KMS-encrypted in Secret Manager:
   - `field-keyset`: AES-256-GCM, used to encrypt the `*_enc` columns;
   - `bidx-keyset`: HMAC-SHA256 PRF, used to compute the `*_bidx` blind indexes.
4. **`FieldCipher`** in `backend/app/core/crypto.py`: `encrypt`, `decrypt`, `blind_index`, `needs_reencrypt`, with context binding through associated data.
5. **Key tools:**
   - create, rotate and re-wrap keysets;
   - a re-encryption backfill job;
   - a blind-index rebuild job.

Done means:
- every workload runs as its own SA with the §6 roles and nothing else;
- `iam_audit.py` passes in all three projects;
- the secrets exist with per-secret access;
- the app loads both keysets at startup (one KMS decrypt each) and round-trips PHI fields;
- a raw database dump shows no plaintext;
- the rotation tests pass.

## 2. Why this matters
Plan §6 requires three things:
- field-level encryption for phone numbers and summaries, with KMS-managed keys;
- least privilege for every identity;
- secrets kept out of code.

The risk register (P0-11) rates these risks as High, and this task is the main control for them:
- **R06:** an over-privileged identity reads prod data;
- **R10:** database or backup data is exfiltrated;
- **R12:** Open Dental keys leak, which would expose the whole clinic database.

The **PHI gate** (DECISIONS #25) requires these controls before any real patient data exists.

Field encryption means a stolen database dump, backup or export still doesn't reveal phone numbers, contact details or summaries without the KMS key, which has its own IAM and audit trail. Context binding means a ciphertext copied into another row, column or clinic doesn't decrypt.

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P1, Core Platform & Open Dental Adapter**.
- **What already exists:**
  - **P0-05:** groups `gcp-org-admins`, `gcp-security-admins`, `gcp-billing-admins`, `gcp-developers`; developers have `roles/viewer` in dev only.
  - **P0-06:** service-account keys are blocked by org policy; US-only resource locations.
  - **P0-08:** design for the `admin-email-sender` SA. It uses keyless domain-wide delegation through the IAM Credentials API (`signJwt`), with the single scope `gmail.send`, sending as `callbacks@`.
  - **P0-12:** the Open Dental secret names.
  - **P0-15:** the `messaging-api-key` secret.
  - **P1-01:** `Settings` with `SecretStr` fields. Secrets reach the app as env vars that Cloud Run maps from Secret Manager (DECISIONS #84).
  - **P1-02:**
    - SAs `sa-api`, `sa-web`, `sa-tasks-invoker`, `sa-scheduler`;
    - key ring `kr-<env>` (us-central1) with storage keys;
    - `redis-auth` and `redis-ca` secrets;
    - the `cloud_run_service` module's `secret_env` input (empty until now).
  - **P1-03:**
    - SA `sa-migrate`;
    - columns `<field>_enc bytea` (opaque ciphertext) and `<field>_bidx bytea` (32 bytes);
    - the `sql-postgres-break-glass` secret;
    - the envelope format: version byte ‖ key ID ‖ nonce ‖ ciphertext ‖ tag.
- **Tink** (https://developers.google.com/tink) is Google's open-source cryptography library. A **keyset** holds one or more keys; one is the *primary*, used for new encryptions, while the others can still decrypt.
  - AEAD output with the TINK prefix is: 1 byte `0x01`, a 4-byte key ID, then the AES-GCM output (12-byte IV, ciphertext, 16-byte tag). This matches the P1-03 format, and it is how rotation works: the key ID tells Tink which key to use.
  - Keysets can be stored encrypted by a KMS key; Tink calls KMS once to decrypt the keyset.
  - **Verify** in the Tink Python docs: the current package name (`tink`), the GCP KMS integration (`tink.integration.gcpkms`), the encrypted-keyset JSON functions, and the PRF key templates.
- **Facts to verify at implementation:**
  - IAM role names for each product (§6 table);
  - Secret Manager user-managed replication and resource-level IAM;
  - Cloud Run secret env vars resolve the version **when an instance starts**, so a new version reaches running services only after a new revision or new instances;
  - **Privileged Access Manager (PAM)** for time-limited, approved IAM grants: whether it is GA, whether it is in the HIPAA covered list, and its approval flow.

## 4. Scope
**In scope**
- **Terraform:**
  - module `infra/modules/iam_workloads/` for the SAs and their resource-level bindings;
  - module `infra/modules/secrets/` for the secret shells and their accessors;
  - KMS key `app-fields` added to `kr-<env>` (module `kms` from P1-02 gains the key);
  - PAM entitlements, or the fallback (§6), for staging and prod;
  - developer roles in dev;
  - `secret_env` filled for the `api` service.
- **New SA `admin-email-sender`** (prod and dev), with token-creator rights for `sa-api` only. The Workspace delegation itself is done in P2-22.
- **`backend/app/core/crypto.py`:**
  - `FieldCipher`, `EncContext`, `BidxKind`, the normalizers, the error types;
  - startup loading in the lifespan;
  - a local cleartext-keyset mode for local and test only.
- **`Settings` additions** (§6).
- **Key tools** in `backend/tools/keys/`:
  - `create_keyset.py`, `rotate_keyset.py`, `rewrap_keyset.py`;
  - `reencrypt.py` (backfill);
  - `rebuild_bidx.py`.
- **`tools/iam_audit.py`**, which fails on:
  - basic roles (`owner`, `editor`, `viewer`) held by service accounts;
  - project-level `secretmanager.secretAccessor`;
  - any `allUsers` or `allAuthenticatedUsers` binding;
  - user (non-group) principals in staging or prod.
- **Docs:**
  - `docs/security/iam.md` (the SA and human access matrix);
  - `docs/security/secrets.md` (inventory and rotation);
  - `docs/runbooks/key-rotation.md`.

**Out of scope** (and which task covers it)
- CI deploy identity and Workload Identity Federation → P1-06 (adds `sa-ci-deployer` using the same module)
- Gmail domain-wide delegation in the Workspace admin console and sending code → P2-22
- Using `FieldCipher` in each feature (callbacks, contact prefs, consents) → the feature tasks (P2-22, P4-02, …)
- Patient session token design (uses `PATIENT_SESSION_SIGNING_KEY`) → P1-13
- Log redaction → P1-07
- Fetching per-clinic Open Dental keys at runtime → P1-15 (this task creates the secrets and grants access)
- Periodic access reviews → P5-14
- Re-encrypting backups → not needed (backups contain the same ciphertext; old KEK versions are kept)

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P1-02 Terraform base (approved spec) | SAs, key ring, `secret_env` input, project roots | Write the modules and `validate`; apply after P1-02 in dev. |
| P1-03 Cloud SQL + schema (approved spec) | `*_enc`/`*_bidx` columns, `sa-migrate` | `FieldCipher` needs no database; unit tests use a cleartext keyset. The dump test (T8) runs against the CI Postgres. |
| P0-08 Admin email (approved spec) | SA name, scope | Create the SA now; P2-22 does the delegation. |
| PAM availability (external) | Time-limited prod access | Use the fallback (§6) until PAM is verified. |

## 6. Interface contract

### Workload service accounts (resource-level bindings; Proposed, **Verify** role names)
| SA | Runs | Roles (and on what) |
|---|---|---|
| `sa-api` | Cloud Run `api` | `secretmanager.secretAccessor` on each secret marked `api` below; `cloudkms.cryptoKeyDecrypter` on key `app-fields` only (to open keysets); `cloudsql.client` + `cloudsql.instanceUser` (project; P1-03); `aiplatform.user` (project; Vertex AI); Speech-to-Text role, **Verify** (`roles/speech.client`?); Text-to-Speech needs no extra role if only `serviceusage` is required, **Verify**; `cloudtasks.enqueuer` on the three queues; `iam.serviceAccountUser` on `sa-tasks-invoker` (to create tasks with its OIDC identity); `iam.serviceAccountTokenCreator` on `admin-email-sender` only; `logging.logWriter`, `monitoring.metricWriter`, `cloudtrace.agent` (project) |
| `sa-web` | Cloud Run `web` | `logging.logWriter`, `monitoring.metricWriter` only. No secrets, no data. |
| `sa-tasks-invoker` | OIDC identity on Cloud Tasks | `run.invoker` on `api` (P1-02) |
| `sa-scheduler` | OIDC identity on Scheduler jobs | `run.invoker` on `api` (P1-02) |
| `sa-migrate` | Migration job (P1-06) | `cloudsql.client`, `cloudsql.instanceUser` (P1-03), `logging.logWriter` |
| `admin-email-sender` | Impersonated by `sa-api` for Gmail delegation | **No Google Cloud roles.** Domain-wide delegation, scope `gmail.send` only (P2-22) |

The Cloud Tasks service agent also needs to act as `sa-tasks-invoker` when it mints OIDC tokens. **Verify** in the Cloud Tasks auth docs whether this is needed, and grant `iam.serviceAccountUser` (or `iam.serviceAccountTokenCreator`) on that SA to `service-<num>@gcp-sa-cloudtasks.iam.gserviceaccount.com` if so. Do the same check for Cloud Scheduler and `sa-scheduler`.

```hcl
# infra/modules/iam_workloads (excerpt)
resource "google_secret_manager_secret_iam_member" "api" {
  for_each  = toset(var.api_secret_ids)
  secret_id = each.value
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${var.sa_emails.api}"
}
resource "google_kms_crypto_key_iam_member" "api_fields" {
  crypto_key_id = var.kms_key_ids["app-fields"]
  role          = "roles/cloudkms.cryptoKeyDecrypter"     # decrypt only; encrypting keysets is done by people via PAM
  member        = "serviceAccount:${var.sa_emails.api}"
}
resource "google_service_account_iam_member" "api_impersonates_mailer" {
  service_account_id = google_service_account.admin_email_sender.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:${var.sa_emails.api}"
}
resource "google_cloud_tasks_queue_iam_member" "api_enqueue" {
  for_each = var.queue_ids
  name     = each.value
  location = var.region
  role     = "roles/cloudtasks.enqueuer"
  member   = "serviceAccount:${var.sa_emails.api}"
}
```

### Human access
| Group | dev | staging | prod |
|---|---|---|---|
| `gcp-developers` | `run.developer`, `logging.viewer`, `cloudsql.client`, `secretmanager.secretAccessor` on dev test secrets only, `cloudtasks.viewer`, `monitoring.viewer` | `monitoring.viewer`, `run.viewer` | `monitoring.viewer` (metrics only, no logs, no data) |
| `gcp-security-admins` | `secretmanager.admin`, `cloudkms.admin` | via PAM | via PAM |
| `gcp-org-admins` | as P0-05 | as P0-05 | as P0-05, use is audited |

**Proposed PAM entitlements** (staging and prod; max 4 h; requester justification; approver = compliance owner or tech lead, never the requester):
| Entitlement | Grants | Use |
|---|---|---|
| `ops-read` | `logging.viewer`, `run.viewer`, `cloudsql.viewer`, `cloudtasks.viewer` | Investigating incidents (logs are PHI-free by P1-07, but may contain IDs) |
| `ops-write` | `run.developer`, `cloudtasks.queueAdmin` | Emergency rollback or queue purge |
| `key-admin` | `cloudkms.cryptoKeyEncrypterDecrypter` on `app-fields`, `secretmanager.secretVersionAdder` | Keyset rotation and secret value changes |
| `db-breakglass` | `secretmanager.secretAccessor` on `sql-postgres-break-glass`, `cloudsql.client` | Direct database access (P5-12 runbook) |

**Fallback if PAM isn't verified:** the same role sets bound to Google Groups (`gcp-prod-ops-read`, …) whose membership is added with an expiry date in Cloud Identity (**Verify** membership expiry). Approval is recorded in the ticket. `iam_audit.py` reports any membership older than 24 h.

### Secret inventory
All secrets use user-managed replication in `us-central1` only. Terraform creates the shells; values come from people (`gcloud secrets versions add`, via `key-admin`) or the key tools.

| Secret | Projects | Content | Accessors | Env var in `api` | Owner task |
|---|---|---|---|---|---|
| `od-developer-key` | dev, staging, prod | Our Open Dental developer key | `sa-api` | `OD_DEVELOPER_KEY` | P0-12 |
| `od-customer-key-testdb` | dev, staging | Test DB (B) customer key | `sa-api`, CI (P1-06) | not mapped (read by name at runtime, P1-15) | P0-12 |
| `od-customer-key-<clinic_slug>` | prod | Clinic customer key; **first version only after the BAA** (P0-09) | `sa-api` | not mapped (runtime, P1-15) | P0-12, P6-01 |
| `messaging-api-key` | dev, staging, prod | Messaging provider credentials (JSON: account ID + key/secret) | `sa-api` | `MESSAGING_API_KEY` | P0-15, P4-01 |
| `messaging-webhook-secret` | dev, staging, prod | Inbound webhook signature secret, if the provider uses one (**Verify** in P4-01) | `sa-api` | `MESSAGING_WEBHOOK_SECRET` | P4-01 |
| `messaging-webhook-verify-token` | dev, staging, prod | Random token Meta echoes when verifying the webhook URL (added by P4-01, DECISIONS #253; the webhook secret above is the Meta App Secret) | `sa-api` | `MESSAGING_WEBHOOK_VERIFY_TOKEN` | P4-01 |
| `redis-auth` | all | Redis AUTH string | `sa-api` | `REDIS_PASSWORD` | P1-02 |
| `redis-ca` | all | Redis server CA (PEM) | `sa-api` | `REDIS_CA_CERT` | P1-02 |
| `field-keyset` | all | Tink AEAD keyset, **encrypted with `app-fields`** (JSON) | `sa-api`, `sa-migrate` (backfill jobs) | `FIELD_KEYSET` | this task |
| `bidx-keyset` | all | Tink PRF keyset, encrypted with `app-fields` | `sa-api`, `sa-migrate` | `BIDX_KEYSET` | this task |
| `patient-session-signing-key` | all | 32+ random bytes, base64 | `sa-api` | `PATIENT_SESSION_SIGNING_KEY` | P1-13 |
| `sql-postgres-break-glass` | all | Postgres `postgres` user password | `db-breakglass` only | not mapped | P1-03 |

Proposed version pinning: **dev** maps `latest`. **Staging and prod** map a numbered version, recorded in tfvars. Rotating a value then means adding a version, updating tfvars and deploying, so every revision knows exactly which value it runs with.

Secret env mapping in the `api` root (input to P1-02's `cloud_run_service`):
```hcl
module "api" {
  source = "../../modules/cloud_run_service"
  # ...
  secret_env = {
    OD_DEVELOPER_KEY            = { secret = "od-developer-key",            version = var.secret_versions["od-developer-key"] }
    MESSAGING_API_KEY           = { secret = "messaging-api-key",           version = var.secret_versions["messaging-api-key"] }
    REDIS_PASSWORD              = { secret = "redis-auth",                  version = "latest" }
    REDIS_CA_CERT               = { secret = "redis-ca",                    version = "latest" }
    FIELD_KEYSET                = { secret = "field-keyset",                version = var.secret_versions["field-keyset"] }
    BIDX_KEYSET                 = { secret = "bidx-keyset",                 version = var.secret_versions["bidx-keyset"] }
    PATIENT_SESSION_SIGNING_KEY = { secret = "patient-session-signing-key", version = var.secret_versions["patient-session-signing-key"] }
  }
}
```
Inside the module:
```hcl
dynamic "env" {
  for_each = var.secret_env
  content {
    name = env.key
    value_source {
      secret_key_ref {
        secret  = env.value.secret
        version = env.value.version
      }
    }
  }
}
```

### KMS key for field encryption
```hcl
resource "google_kms_crypto_key" "app_fields" {
  name            = "app-fields"
  key_ring        = var.key_ring_id               # kr-<env> from P1-02
  purpose         = "ENCRYPT_DECRYPT"
  rotation_period = "7776000s"                    # 90 days; old versions stay enabled for decrypt
  version_template {
    algorithm        = "GOOGLE_SYMMETRIC_ENCRYPTION"
    protection_level = "SOFTWARE"                 # Proposed; HSM optional for prod (§14)
  }
  lifecycle { prevent_destroy = true }
}
```
**Never destroy or disable a key version that still wraps a keyset version in use.** Destroying the KEK makes every encrypted field permanently unreadable, backups included. `prevent_destroy` stays on, and key-version destruction needs `key-admin` plus a second approver (runbook).

### `Settings` additions (extends P1-01)
```python
FIELD_KEK_URI: str | None = None                 # "gcp-kms://projects/<p>/locations/us-central1/keyRings/kr-dev/cryptoKeys/app-fields"
FIELD_KEYSET: SecretStr | None = None            # encrypted keyset JSON (cloud) or cleartext keyset JSON (local/test only)
BIDX_KEYSET: SecretStr | None = None
CRYPTO_MODE: Literal["kms", "cleartext"] = "kms"
REDIS_PASSWORD: SecretStr | None = None
REDIS_CA_CERT: SecretStr | None = None
MESSAGING_API_KEY: SecretStr | None = None
MESSAGING_WEBHOOK_SECRET: SecretStr | None = None
PATIENT_SESSION_SIGNING_KEY: SecretStr | None = None

@model_validator(mode="after")
def _crypto_mode(self) -> "Settings":
    if self.CRYPTO_MODE == "cleartext" and self.ENV not in (Env.LOCAL,):
        raise ValueError("cleartext keysets are allowed only with ENV=local")
    if self.CRYPTO_MODE == "kms" and not (self.FIELD_KEK_URI and self.FIELD_KEYSET and self.BIDX_KEYSET):
        raise ValueError("FIELD_KEK_URI, FIELD_KEYSET and BIDX_KEYSET are required in kms mode")
    return self
```
P1-01's `create_redis` uses `REDIS_PASSWORD` and `REDIS_CA_CERT` (TLS with `ssl_ca_data`) when they are set. Tests run with `ENV=local` and a cleartext test keyset fixture.

### `FieldCipher` API (`backend/app/core/crypto.py`)
```python
class BidxKind(StrEnum):
    PHONE = "phone"            # normalized to E.164 (phonenumbers, default region "US")
    EMAIL = "email"            # strip + lowercase
    MESSAGING_ADDRESS = "msg"  # E.164 for SMS/WhatsApp

@dataclass(frozen=True, slots=True)
class EncContext:
    table: str                 # "callback_requests"
    column: str                # "contact_phone_enc"
    clinic_id: uuid.UUID

    def aad(self) -> bytes:
        return f"dai.v1|{self.table}|{self.column}|{self.clinic_id}".encode()

class CryptoError(AppError):
    code = "crypto_error"
    status = 500

class KeysetLoadError(CryptoError):        # startup: keyset missing, KMS unreachable or denied
    code = "crypto_keyset_load_failed"

class DecryptionError(CryptoError):        # wrong context, corrupted data, unknown key ID
    code = "crypto_decrypt_failed"

class NormalizationError(AppError):        # invalid phone/email for a blind index
    code = "invalid_identifier"
    status = 422

class FieldCipher:
    @classmethod
    async def load(cls, settings: Settings) -> "FieldCipher": ...   # one KMS decrypt per keyset; run in lifespan via asyncio.to_thread
    def encrypt(self, plaintext: str, *, ctx: EncContext) -> bytes: ...
    def decrypt(self, ciphertext: bytes, *, ctx: EncContext) -> str: ...
    def blind_index(self, value: str, *, kind: BidxKind, clinic_id: uuid.UUID) -> bytes: ...  # 32 bytes
    def needs_reencrypt(self, ciphertext: bytes) -> bool: ...       # key ID != current primary
    @property
    def primary_key_id(self) -> int: ...
```
Rules:
- **Associated data** binds the ciphertext to table, column and clinic. A ciphertext moved to another place fails with `DecryptionError`.
- **Blind index input:** `HMAC-PRF(bidx_primary, f"{kind}|{clinic_id}|{normalized}")`, first 32 bytes. Including `clinic_id` means the same phone number in two clinics gives unrelated hashes.
- **The PRF keyset has one key in normal use.** Rotating it changes every blind index, so it happens only on compromise, with `rebuild_bidx.py`.
- **Encryption is explicit** in the repository or service layer, not a SQLAlchemy `TypeDecorator`, because the context needs the row's `clinic_id`. `FieldCipher` is created once in the lifespan, stored on `app.state` and provided by a dependency `get_cipher()`.
- **Never log** plaintext, ciphertext, keysets or blind indexes. Exceptions carry no values.

Example:
```python
ctx = EncContext("callback_requests", "contact_phone_enc", clinic_id)
row.contact_phone_enc = cipher.encrypt("+15551234567", ctx=ctx)
row.contact_phone_bidx = cipher.blind_index("(555) 123-4567", kind=BidxKind.PHONE, clinic_id=clinic_id)
assert cipher.decrypt(row.contact_phone_enc, ctx=ctx) == "+15551234567"
```

Loading (sketch; **Verify** the Tink Python API names):
```python
import tink
from tink import aead, prf, secret_key_access
from tink.integration import gcpkms

aead.register()
prf.register()
kek = gcpkms.GcpKmsClient(settings.FIELD_KEK_URI, None).get_aead(settings.FIELD_KEK_URI)   # ADC = sa-api
field = tink.json_proto_keyset_format.parse_encrypted(settings.FIELD_KEYSET.get_secret_value(), kek, b"dai-field-keyset")
self._aead = field.primitive(aead.Aead)
```

### Key tools (`backend/tools/keys/`, run by a `key-admin` holder)
```bash
# create (once per environment)
uv run python -m tools.keys.create_keyset --kind field --kek-uri "$KEK" --secret field-keyset --project acme-dai-dev
uv run python -m tools.keys.create_keyset --kind bidx  --kek-uri "$KEK" --secret bidx-keyset  --project acme-dai-dev
# rotate the field keyset: add a new AES256_GCM key, make it primary, keep old keys; writes a new secret version
uv run python -m tools.keys.rotate_keyset --secret field-keyset --project acme-dai-prod
# re-wrap the keyset with the current KEK version (after KMS rotation, optional, yearly)
uv run python -m tools.keys.rewrap_keyset --secret field-keyset --project acme-dai-prod
# backfill: re-encrypt rows whose key ID is not primary (batches of 500, resumable, dry-run first)
uv run python -m tools.keys.reencrypt --dry-run
uv run python -m tools.keys.reencrypt --batch-size 500
# after a bidx key compromise: new bidx keyset, then recompute every *_bidx from decrypted values
uv run python -m tools.keys.rebuild_bidx --batch-size 500
```
Rotation policy (Proposed):
- **KEK (`app-fields`):** automatic every 90 days.
- **Field keyset:** rotated yearly or on suspicion of compromise. New writes use the new key at once (after deploy). Old rows are re-encrypted lazily on update, and by `reencrypt.py` within 30 days. An old key is removed from the keyset only after `reencrypt.py --dry-run` reports 0 rows using it, and never while backups still hold it (backups are kept 30 days, P1-03).
- **Bidx keyset:** rotated only on compromise.

Every tool run writes an `audit_log` row (`action = key.rotate | key.reencrypt | key.rebuild_bidx`) once P1-07 exists.

### IAM audit (`tools/iam_audit.py`)
```bash
uv run python tools/iam_audit.py --project acme-dai-prod --env prod
# exit 1 with a list of findings; JSON output with --json for CI (P1-06 runs it nightly)
```
| Check | Fails when |
|---|---|
| A1 | A service account holds `roles/owner`, `roles/editor` or `roles/viewer` |
| A2 | `secretmanager.secretAccessor` or `cloudkms.cryptoKeyDecrypter` granted at project level |
| A3 | Any binding to `allUsers` or `allAuthenticatedUsers` |
| A4 | A `user:` principal (not a group) in staging or prod |
| A5 | A service account has a user-managed key (should be impossible under P0-06) |
| A6 | A PAM fallback group membership is older than 24 h (fallback mode only) |

## 7. Implementation guide
1. **Read** P0-05 (groups), P0-06 (org policies), P0-08 (§6 auth design), P0-12 (secrets), P0-15 (messaging secret), P1-02 and P1-03 outputs, DECISIONS #25 and #84.
2. **Verify** the role names in §6, the PAM availability and HIPAA status, Cloud Tasks and Scheduler service-agent needs, and the Tink Python API. Record the results in `docs/security/iam.md`.
3. **Terraform:**
   1. add `app-fields` to the `kms` module;
   2. write `iam_workloads` and `secrets`;
   3. add the PAM entitlements or the fallback groups;
   4. add developer roles in dev;
   5. fill `secret_env` for `api`;
   6. apply in dev.
4. **Crypto module:** write `crypto.py` with unit tests first (T1–T7) using a cleartext keyset fixture.
5. **Key tools:**
   1. `create_keyset.py`;
   2. create both keysets in dev and staging (and prod later, after the PHI gate review);
   3. redeploy `api` and check that the lifespan loads them and `/readyz` is 200.
6. **Settings and lifespan:**
   - add the fields;
   - load `FieldCipher` in the lifespan;
   - if the keysets fail to load, `/readyz` returns 503 and logs `crypto.keyset_load_failed` (no values).
7. **Rotation tools** (`rotate`, `rewrap`, `reencrypt`, `rebuild_bidx`): test them against the CI database with fake rows (T9, T10).
8. **IAM audit:** write `iam_audit.py` and run it in all three projects; fix the findings.
9. **Docs:** `iam.md`, `secrets.md`, `key-rotation.md` (with the "never destroy a KEK version in use" rule).
10. **Notify:**
    - P1-06: `sa-ci-deployer` pattern, `iam_audit.py` nightly, the secret-version tfvars;
    - P1-07: no crypto values in logs, `key.*` audit actions;
    - P1-13: `PATIENT_SESSION_SIGNING_KEY`;
    - P1-15: per-clinic secret naming and `sa-api` access;
    - P2-22, P4-02, P4-01: `FieldCipher` usage and the `EncContext` names;
    - P2-22: `admin-email-sender` and the impersonation grant;
    - P4-01: `MESSAGING_API_KEY`;
    - P5-12, P5-14: break-glass, access reviews, PAM logs.

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| KMS is unreachable or denies decrypt at startup | `KeysetLoadError`; the instance stays unready (`/readyz` 503), so traffic goes to healthy instances; alert (P1-07). No fallback to cleartext. |
| Ciphertext from another row, column or clinic | `DecryptionError` (associated data mismatch); audit `security.decrypt_failed` with table, column and row ID only; return 500 to the caller. |
| Ciphertext with a key ID not in the keyset (key removed too early) | `DecryptionError`; this is a data-loss incident. Restore the previous keyset version from Secret Manager (versions are kept) and redeploy. |
| `blind_index` on an invalid phone (e.g. "123") | `NormalizationError` → 422 to the tool or flow; nothing is stored. |
| A new secret version is added but not yet deployed | Running instances keep the old value (versions are resolved at start). Staging and prod use pinned versions, so a deploy is required, which is the intended behaviour. |
| A secret version is disabled while a revision still uses it | New instances fail to start. Never disable a version that a live revision maps; the runbook checks `gcloud run revisions describe` first. |
| Someone grants `secretAccessor` at project level | `iam_audit.py` A2 fails; the nightly CI run alerts. |
| PAM approval is unavailable during an incident | `gcp-org-admins` break-glass (P0-05), audited, with a post-incident review. |
| Prod keysets are needed before the PHI gate | Not allowed: prod keysets and `od-customer-key-<clinic>` are created only after `check_vendors.py --gate` passes (DECISIONS #25). |
| `reencrypt.py` interrupted | Resumable: it selects rows where `needs_reencrypt` is true; each batch is one transaction. |

## 9. Security, HIPAA and PHI
- **PHI handled:** the plaintext values of the `*_enc` fields pass through `FieldCipher` in memory only:
  - callback contact name and phone, and summary;
  - messaging address.
- **What is stored:** ciphertext and 32-byte blind indexes (P1-03).
- **What is never logged:** plaintext, ciphertext, blind indexes, keysets or secret values. Exceptions and audit rows carry only table, column, row ID and error code.
- **Encryption:**
  - AES-256-GCM per field with associated data;
  - keysets wrapped by a KMS key that rotates every 90 days;
  - only `sa-api` and `sa-migrate` can open the keysets (decrypt only);
  - only `key-admin` can create or rotate them.
- **Least privilege:**
  - one SA per workload, with resource-level bindings;
  - no SA keys (P0-06);
  - no standing human access to staging or prod;
  - `iam_audit.py` checks this nightly.
- **Audit:**
  - KMS decrypt calls and Secret Manager access are recorded in Cloud Audit Logs. Data Access logs must be on for `cloudkms` and `secretmanager`; P1-07 enables and retains them (**Verify** the default).
  - PAM grants are logged.
  - Key-tool runs are written to `audit_log`.
- **HIPAA safeguards:**
  - §164.312(a)(1) access control (unique identities, least privilege, emergency access);
  - §164.312(a)(2)(iv) encryption;
  - §164.308(a)(4) access management;
  - §164.312(b) audit controls.
- **Risks reduced:** P0-11 R06, R10, R12.

## 10. Testing
Unit tests (`backend/tests/unit/test_crypto.py`, cleartext keyset fixture):
| # | Test | Expected |
|---|---|---|
| T1 | `encrypt` then `decrypt` with the same context, for ASCII, Unicode and 2 KB text | Round trip equal |
| T2 | Same plaintext encrypted twice | Different ciphertexts (random nonce) |
| T3 | Decrypt with a different `table`, `column` or `clinic_id` | `DecryptionError` |
| T4 | Ciphertext starts with `0x01` + 4-byte primary key ID | Format matches P1-03 |
| T5 | Rotation: encrypt with keyset v1; add a key and make it primary (v2); decrypt old ciphertext with v2; `needs_reencrypt(old)` is true and `needs_reencrypt(new)` is false | Pass |
| T6 | `blind_index` of "(555) 123-4567", "+1 555-123-4567" and "5551234567" | Identical 32 bytes; different for another `clinic_id`; different for another kind |
| T7 | `Settings(ENV=prod, CRYPTO_MODE="cleartext")`; `CRYPTO_MODE="kms"` without keysets | `ValidationError` |

Integration tests (CI Postgres):
| # | Test | Expected |
|---|---|---|
| T8 | **Raw dump:** insert a `callback_requests` row through the repository with phone "+15551234567" and summary "toothache since Monday"; run `pg_dump --data-only` | Neither string, nor the digits `5551234567`, appears in the dump |
| T9 | `reencrypt.py` on 1,200 rows with an old key | All rows on the new primary; values unchanged after decrypt; second run updates 0 rows |
| T10 | `rebuild_bidx.py` after a bidx keyset change | Lookups by phone work again; all `*_bidx` changed |
| T11 | Lifespan with a broken keyset | App starts, `/readyz` returns 503, the log has `crypto.keyset_load_failed` and no keyset content |

Cloud checks (dev, then staging and prod), recorded in `docs/security/iam.md`:
- `iam_audit.py` exits 0 in all three projects.
- `gcloud secrets get-iam-policy od-developer-key` lists only `sa-api`.
- From a dev Cloud Run job running as `sa-web`, `gcloud secrets versions access latest --secret field-keyset` is **denied**.
- `gcloud kms keys describe app-fields …` shows the 90-day rotation and the SOFTWARE level.
- A KMS Data Access log entry appears for the `api` startup decrypt.

## 11. Acceptance criteria
- [ ] SAs `sa-api`, `sa-web`, `sa-tasks-invoker`, `sa-scheduler`, `sa-migrate` and `admin-email-sender` have exactly the §6 roles, granted on single resources where the table says so
- [ ] `iam_audit.py` passes (A1–A5, and A6 in fallback mode) in dev, staging and prod
- [ ] Developers have standing access only in dev; staging and prod access is via PAM entitlements (or the documented fallback) with approval and a 4 h maximum
- [ ] Every secret in the inventory exists in its projects with per-secret accessors; no secret value is in the repo, Terraform files or tfvars
- [ ] `api` gets its secrets as env vars from Secret Manager (pinned versions in staging and prod)
- [ ] KMS key `app-fields` exists (90-day rotation); `field-keyset` and `bidx-keyset` are stored encrypted with it; only `sa-api` and `sa-migrate` can decrypt
- [ ] `FieldCipher` passes T1–T7; the raw dump test T8 shows no plaintext; rotation and rebuild tools pass T9–T10; a broken keyset makes `/readyz` fail (T11)
- [ ] `iam.md`, `secrets.md` and `key-rotation.md` are written; the §7 step 10 issues are notified

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI (T1–T11)
- [ ] PR reviewed (HIPAA review if labelled `phi`): labelled `phi`; reviewed by the tech lead and the compliance owner (IAM matrix, crypto design)
- [ ] No PHI in logs: crypto errors carry no values (T11); test data is fake
- [ ] Docs / README updated: module READMEs, `iam.md`, `secrets.md`, `key-rotation.md`

## 13. Hand-off
| Task | Can rely on |
|---|---|
| P1-06 CI/CD | The `iam_workloads` module pattern for `sa-ci-deployer`; `iam_audit.py --json` to run nightly; `secret_versions` tfvars to bump on rotation |
| P1-07 Logging/audit | Never log crypto values; audit actions `key.rotate`, `key.reencrypt`, `key.rebuild_bidx`, `security.decrypt_failed`; enable Data Access logs for KMS and Secret Manager |
| P1-13 Auth | `PATIENT_SESSION_SIGNING_KEY` (SecretStr) |
| P1-15 Open Dental client | Secret name pattern `od-customer-key-<clinic_slug>` (from `clinics.od_customer_key_secret`), `sa-api` has access |
| P2-01 Slot memory | `FieldCipher` for any PHI kept in Redis (`EncContext(table="redis_session", column=<field>, clinic_id)`) |
| P2-22, P4-02, P4-01 | `get_cipher()` dependency, `EncContext` naming = real table/column names, `blind_index` kinds |
| P2-22 Admin email | `admin-email-sender` SA; `sa-api` can impersonate it; no Cloud roles on it |
| P4-01 Messaging | `MESSAGING_API_KEY`, `MESSAGING_WEBHOOK_SECRET` |
| P5-12 / P5-14 | Break-glass entitlement, PAM logs, key rotation runbook, access review input |

## 14. Open questions
| Question | Owner | Needed by |
|---|---|---|
| Is PAM available and in the HIPAA covered list for our org, or do we use the expiring-group fallback? | Tech lead + compliance owner | Step 3 |
| HSM protection for `app-fields` in prod (small monthly cost), or SOFTWARE everywhere? | Compliance owner | Before prod keyset creation |
| Who approves PAM requests, and who are the `key-admin` holders (at least two people)? | Project sponsor | Before PHI (gate) |

## 15. References
- Plan §6
- Tink: https://developers.google.com/tink (Python, AEAD, PRF, key management with Cloud KMS)
- Cloud KMS rotation: https://docs.cloud.google.com/kms/docs/key-rotation
- Envelope encryption: https://docs.cloud.google.com/kms/docs/envelope-encryption
- Secret Manager access control: https://docs.cloud.google.com/secret-manager/docs/access-control
- Cloud Run secrets: https://docs.cloud.google.com/run/docs/configuring/services/secrets
- Privileged Access Manager: https://docs.cloud.google.com/iam/docs/pam-overview
- Cloud Tasks OIDC auth: https://docs.cloud.google.com/tasks/docs/creating-http-target-tasks
- IAM roles reference: https://docs.cloud.google.com/iam/docs/understanding-roles
- HIPAA Security Rule 45 CFR §164.308, §164.312
- Related tasks: P0-05, P0-06, P0-08, P0-09, P0-11, P0-12, P0-15, P1-01, P1-02, P1-03, P1-06, P1-07, P1-13, P1-15, P2-01, P2-22, P4-01, P4-02, P5-12, P5-14
