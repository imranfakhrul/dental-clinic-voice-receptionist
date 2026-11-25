---
id: P1-02
title: Terraform base - network, ingress, Cloud Run, Artifact Registry, Redis, Cloud Tasks and Scheduler
milestone: P1
epic: E1.1
size: L
labels: area:infra, type:chore
depends_on: P0-06, P1-01
status: approved
---

# P1-02: Terraform base - network, ingress, Cloud Run, Artifact Registry, Redis, Cloud Tasks and Scheduler

## 1. Summary
Build the runtime infrastructure for `dev`, `staging` and `prod` as Terraform, following the P0-14 network map. This issue also absorbs **P1-04 (Memorystore Redis, Cloud Tasks, Cloud Scheduler)**.

The deliverables:
- **Modules** in `infra/modules/`:
  - `network`: VPC, subnet, Private Service Access, Cloud NAT, restricted-VIP DNS, egress firewall policy;
  - `kms`: storage CMEK keys;
  - `artifact_registry`;
  - `cloud_run_service`, used for `api` and `web`;
  - `lb`: external HTTPS load balancer, serverless NEGs and Cloud Armor;
  - `redis`: TLS, AUTH, CMEK, Private Service Access;
  - `tasks`: queues with retry policies;
  - `scheduler`: OIDC jobs.
- **Root configurations** in `infra/env/{dev,staging,prod}/`, with state in `gs://<prefix>-ops-tfstate/env/<env>/`.
- **The `dai_dev` and `dai_staging` perimeters switched from dry-run to enforced**, via a PR to `infra/org/` (P0-06).

Done means:
- `terraform plan` and `apply` work for all three environments;
- the §10 negative tests pass:
  - Cloud Run can't be reached on its `run.app` URL;
  - no public IP on any data store;
  - Redis refuses non-TLS and unauthenticated clients;
  - egress to anything other than the allowed hosts fails;
  - all storage uses CMEK;
- the outputs are published for P1-03, P1-05, P1-06 and P1-07.

## 2. Why this matters
This is where the HIPAA design (P0-06, P0-14) becomes real. Several settings **can only be set at creation**:
- Memorystore in-transit encryption: "You can only enable in-transit encryptions when you initially create your Redis instance";
- Memorystore CMEK: "You can enable CMEK only on new instances";
- the Memorystore connection mode;
- Artifact Registry CMEK: "You cannot change the encryption mechanism of an existing repository".

Getting them wrong means rebuilding later, with data.

Ingress and egress decide whether the Cloud Armor and VPC-SC controls can be bypassed. Google warns that without the right ingress setting "users can use your serverless application's default URL to bypass the load balancer, Cloud Armor security policies". The queues decide how reminders and callback emails survive failures.

Plan references: §3.2 (stack, US region), §6 (encryption, access control), §4.7 (reminder jobs), §4.9 (callback emails).

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P1, Core Platform & Open Dental Adapter**.
- **What already exists:**
  - **P0-05:** projects `<prefix>-dev`, `-staging`, `-prod`, `-ops`; the state bucket `gs://<prefix>-ops-tfstate`; IDs in `infra/bootstrap/foundation.yaml`; groups `gcp-org-admins`, `gcp-security-admins`, `gcp-developers`.
  - **P0-06** (`infra/org/`):
    - org policies: allow-list from `allowed_services.yaml`, US locations, no SA keys, no public Cloud SQL IP;
    - perimeters: `dai_prod` enforced, `dai_dev` and `dai_staging` in dry-run;
    - the Gemini Developer API is denied.
  - **P0-14:** network map, ADR 0002 (Cloud Run settings), flows F01–F14 (F13: no PHI in task payloads).
  - **P1-01:** Dockerfile on port 8080, `/healthz` and `/readyz`, `Settings`.
- **Facts verified on 2026-11-24** (Google docs; **Verify** again at implementation):
  - **Cloud Run and VPC-SC** (https://docs.cloud.google.com/run/docs/securing/using-vpc-service-controls):
    - org policy `run.allowedIngress` set to `internal` or `internal-and-cloud-load-balancing`;
    - `run.allowedVPCEgress` set to `all-traffic`, so every revision must use Direct VPC egress or a connector with all traffic;
    - "Setting ingress to 'all' disables VPC Service Controls enforcement";
    - a DNS response policy maps `*.googleapis.com` and `*.run.app` to `restricted.googleapis.com` (199.36.153.4–.7);
    - firewall: a deny-all egress rule at a priority after 1000, with an allow for TCP 443 to 199.36.153.4/30 at a higher priority.
  - **Restricted VIP** (https://docs.cloud.google.com/vpc-service-controls/docs/set-up-private-connectivity): a private zone `googleapis.com`, `*.googleapis.com` CNAME `restricted.googleapis.com.`, A records 199.36.153.4/.5/.6/.7, and a route for 199.36.153.4/30 to the default internet gateway.
  - **Multi-region Vertex AI endpoint:** `*.rep.googleapis.com` hosts are reached through a **Private Service Connect endpoint**, not documented for the restricted VIP. `aiplatform.googleapis.com` is GA on the restricted VIP.
  - **Cloud SQL private IP** from Cloud Run through Direct VPC egress is supported (https://docs.cloud.google.com/sql/docs/postgres/connect-run). **Memorystore** is reachable from Direct VPC egress ("access to… Memorystore instances").
  - **Memorystore for Redis** (https://docs.cloud.google.com/memorystore/docs/redis/):
    - TLS 1.2+, created with `SERVER_AUTHENTICATION`, on port **6378**; clients must trust the instance CA;
    - AUTH is optional and can be toggled;
    - CMEK only at creation, with the key in the same region;
    - connection mode `DIRECT_PEERING` (default) or `PRIVATE_SERVICE_ACCESS` (recommended), and it can't be switched later.
  - **Cloud Tasks** (https://docs.cloud.google.com/tasks/docs/quotas, https://docs.cloud.google.com/tasks/docs/configuring-queues):
    - maximum schedule time is **30 days ahead**;
    - maximum task size 1 MiB;
    - HTTP dispatch deadline 15 s to 30 min, default 10 min;
    - retry fields `max_attempts` (includes the first attempt), `min_backoff`, `max_backoff`, `max_doublings`, `max_retry_duration`;
    - queue-level routing is not compatible with CMEK;
    - OIDC tokens are recommended for Cloud Run targets; the token's service account needs `roles/run.invoker`.
  - **Cloud Scheduler:** OIDC to Cloud Run with a dedicated service account (not the service agent). To invoke a target internally, it must be in the same project or perimeter. It is GA on the restricted VIP.
  - **Artifact Registry:** CMEK only at creation; automatic vulnerability scanning on push (Container Scanning API); cleanup policies with dry-run.
  - **HIPAA covered list** (2026-11-11) includes Cloud Run, Cloud Scheduler, Cloud SQL, Cloud Tasks, Artifact Registry, Artifact Analysis, Cloud KMS, VPC Service Controls and Memorystore.
- **Booking horizon** (DECISIONS #86) is configurable up to 365 days, and staff can create appointments in Open Dental far ahead. Since Cloud Tasks can't schedule more than 30 days out, reminders are **not** enqueued at booking time. An hourly Scheduler job ("reminder sweep", P4-04) enqueues reminders that fall within the next 48 hours.

## 4. Scope
**In scope**
- **Modules**, each with `variables.tf`, `main.tf`, `outputs.tf`, `versions.tf` and a `README.md` (inputs and outputs table): `network`, `kms`, `artifact_registry`, `cloud_run_service`, `lb`, `redis`, `tasks`, `scheduler`.
- **Roots** `infra/env/dev|staging|prod` with `backend.tf`, `main.tf`, `variables.tf`, `terraform.tfvars`, `outputs.tf`.
- **Service account identities** used by the infrastructure: `sa-api`, `sa-web`, `sa-tasks-invoker`, `sa-scheduler`. This task creates only the identities and the `run.invoker` bindings; data-access roles are granted by P1-05.
- **Storage CMEK keys:** key ring `kr-<env>` in `us-central1` with keys `sql`, `redis`, `artifact-registry`, `tasks`, a 90-day rotation, and grants to the service agents.
- **Redis:** the AUTH string and server CA written to Secret Manager secrets `redis-auth` and `redis-ca`, with values from Terraform outputs.
- **Org changes** via a PR to `infra/org/` (P0-06 owns the code):
  - set the org policies `run.allowedIngress` and `run.allowedVPCEgress` on the `dental-ai` folder;
  - switch `dai_dev` and `dai_staging` to enforced after reviewing the dry-run logs;
  - add the ingress rule for CI deploys from `ops` (P1-06 fills in the identity).
- A **bootstrap image:** build P1-01's Dockerfile once and push it to each environment's repository so that Cloud Run has an image. P1-06 takes over deploys; Terraform ignores image changes.
- DNS records for the load balancer, managed TLS certificates, and the Cloud Armor baseline.
- `docs/runbooks/terraform.md`: how to plan and apply, who may apply, and the order of applies.

**Out of scope** (and which task covers it)
- Cloud SQL instance, databases, users → P1-03 (uses the Private Service Access range and the `sql` key from here)
- Application secrets, field-encryption key, data-access IAM, secret env mapping → P1-05
- Deploy pipeline, Workload Identity Federation, image promotion → P1-06
- Log sinks, metrics, uptime checks, alerting → P1-07
- Bot protection rules beyond the Cloud Armor baseline (reCAPTCHA etc.) → P2-25
- The handlers behind `/internal/jobs/*` → P4-04 (reminder sweep), P2-22 (unsent-email check); token verification → P1-13
- Private Service Connect for the Vertex AI `us` multi-region endpoint → later, if P0-13 requires `us` (§14)
- Retention and deletion jobs → P5-12

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P0-06 Guardrails (approved spec) | Allowed APIs, perimeters, org policy code in `infra/org/` | Write the modules now and run `terraform validate` and `plan` in dev. Apply in dev once `dai_dev` exists (dry-run is enough to start). |
| P1-01 Repo (approved spec) | `infra/` folder, Dockerfile, health endpoints | Use the Dockerfile from the P1-01 spec; a placeholder image built from it is enough. |
| P0-05 Foundation (approved spec) | Project IDs, state bucket | Read the IDs from `infra/bootstrap/foundation.yaml`. |
| Company DNS (external) | A domain or subdomain for the load balancer hostnames | Use the LB IP with a self-managed test certificate in dev until DNS is delegated (§14). |
| Messaging provider (P0-07) | The provider's API hostname for the egress allow-list | Use a variable; leave the list empty until P0-07 decides. Egress to it fails safely until it is added. |

## 6. Interface contract

### Layout
```text
infra/
├── org/                      # P0-06 (perimeters, org policies) - changed here only by PR
├── modules/
│   ├── network/  kms/  artifact_registry/  cloud_run_service/  lb/  redis/  tasks/  scheduler/
└── env/
    ├── dev/      backend.tf main.tf variables.tf terraform.tfvars outputs.tf
    ├── staging/
    └── prod/
```
Provider pins (`versions.tf` in every root; **Verify** the current major versions):
```hcl
terraform {
  required_version = ">= 1.8"
  required_providers {
    google      = { source = "hashicorp/google", version = "~> 6.0" }
    google-beta = { source = "hashicorp/google-beta", version = "~> 6.0" }
  }
}
```
Backend:
```hcl
terraform {
  backend "gcs" {
    bucket = "<prefix>-ops-tfstate"
    prefix = "env/dev"            # env/staging, env/prod
  }
}
```

### Root variables (`terraform.tfvars`, dev example; IDs are not secrets)
```hcl
project_id          = "acme-dai-dev"
env                 = "dev"
region              = "us-central1"
domain              = "dev.assistant.example.com"     # LB hostnames: api.<domain>, app.<domain>
subnet_cidr_run     = "10.10.0.0/24"                   # Direct VPC egress for Cloud Run
psa_range_prefix    = 20                               # Private Service Access range for Cloud SQL + Redis
egress_allow_fqdns  = ["api.opendental.com"]           # + messaging provider API host after P0-07
redis_tier          = "BASIC"                          # STANDARD_HA in staging and prod
redis_memory_gb     = 1
api_min_instances   = 0                                # prod: 1
api_max_instances   = 5                                # prod: 20 (P5-03 tunes)
web_min_instances   = 0
cloud_armor_rate_limit_per_min = 300
```
Environment differences:

| Setting | dev | staging | prod |
|---|---|---|---|
| Redis tier | BASIC | STANDARD_HA | STANDARD_HA |
| `api` min instances | 0 | 0 | 1 |
| Perimeter | enforced (after review) | enforced | enforced |
| Deletion protection (Redis, AR) | off | on | on |

### Module interfaces (inputs → outputs)
| Module | Key inputs | Outputs |
|---|---|---|
| `network` | `project_id`, `region`, `subnet_cidr_run`, `psa_range_prefix`, `egress_allow_fqdns` | `network_id`, `network_name`, `subnet_run_id`, `psa_range_name`, `nat_ips` |
| `kms` | `project_id`, `region`, `env`, `service_agents` (map key → SA email) | `key_ids` (map: `sql`, `redis`, `artifact-registry`, `tasks`) |
| `artifact_registry` | `project_id`, `region`, `kms_key_id` | `repo_url` (`us-central1-docker.pkg.dev/<project>/app`) |
| `cloud_run_service` | `name`, `image`, `service_account`, `subnet_id`, `min/max_instances`, `timeout_s`, `concurrency`, `env_vars` (map), `secret_env` (map, empty here; P1-05 fills), `session_affinity`, `probes` | `service_name`, `service_uri` (internal only) |
| `lb` | `project_id`, `domain`, `services` (map host → Cloud Run name), `rate_limit_per_min` | `lb_ip`, `cert_ids`, `security_policy_id` |
| `redis` | `project_id`, `region`, `network_id`, `psa_range_name`, `tier`, `memory_gb`, `kms_key_id` | `host`, `port` (6378), `secret_ids` (`redis-auth`, `redis-ca`) |
| `tasks` | `project_id`, `region`, `queues` (map), `kms_key_id` | `queue_ids` |
| `scheduler` | `project_id`, `region`, `jobs` (map), `invoker_sa` | `job_ids` |

### Network (`modules/network`, excerpt)
```hcl
resource "google_compute_network" "main" {
  name                    = "vpc-main"
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"
}

resource "google_compute_subnetwork" "run" {
  name                     = "snet-run-${var.region}"
  network                  = google_compute_network.main.id
  region                   = var.region
  ip_cidr_range            = var.subnet_cidr_run
  private_ip_google_access = true
}

# Private Service Access (Cloud SQL in P1-03, Redis here)
resource "google_compute_global_address" "psa" {
  name          = "psa-range"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = var.psa_range_prefix
  network       = google_compute_network.main.id
}
resource "google_service_networking_connection" "psa" {
  network                 = google_compute_network.main.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.psa.name]
}

# Internet egress only through NAT (static IPs, logged)
resource "google_compute_router" "r" {
  name    = "rtr-${var.region}"
  network = google_compute_network.main.id
  region  = var.region
}
resource "google_compute_address" "nat" {
  count  = 2
  name   = "nat-ip-${count.index}"
  region = var.region
}
resource "google_compute_router_nat" "nat" {
  name                               = "nat-${var.region}"
  router                             = google_compute_router.r.name
  region                             = var.region
  nat_ip_allocate_option             = "MANUAL_ONLY"
  nat_ips                            = google_compute_address.nat[*].self_link
  source_subnetwork_ip_ranges_to_nat = "LIST_OF_SUBNETWORKS"
  subnetwork {
    name                    = google_compute_subnetwork.run.id
    source_ip_ranges_to_nat = ["ALL_IP_RANGES"]
  }
  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}

# Restricted VIP: private zone + route
resource "google_dns_managed_zone" "googleapis" {
  name       = "googleapis-restricted"
  dns_name   = "googleapis.com."
  visibility = "private"
  private_visibility_config { networks { network_url = google_compute_network.main.id } }
}
resource "google_dns_record_set" "restricted_a" {
  managed_zone = google_dns_managed_zone.googleapis.name
  name         = "restricted.googleapis.com."
  type         = "A"
  ttl          = 300
  rrdatas      = ["199.36.153.4", "199.36.153.5", "199.36.153.6", "199.36.153.7"]
}
resource "google_dns_record_set" "wildcard_cname" {
  managed_zone = google_dns_managed_zone.googleapis.name
  name         = "*.googleapis.com."
  type         = "CNAME"
  ttl          = 300
  rrdatas      = ["restricted.googleapis.com."]
}
resource "google_compute_route" "restricted_vip" {
  name             = "route-restricted-vip"
  network          = google_compute_network.main.name
  dest_range       = "199.36.153.4/30"
  next_hop_gateway = "default-internet-gateway"
}
```
Also, a Cloud DNS **response policy** maps `*.run.app` to the restricted VIP, as required by the Cloud Run VPC-SC guide. Use `google_dns_response_policy` + `google_dns_response_policy_rule`.

**Exception for Google Workspace APIs:** `gmail.googleapis.com` (P0-08) and `oauth2.googleapis.com` (token exchange for domain-wide delegation) are not Cloud APIs protected by VPC-SC. They may not be served on the restricted VIP. Proposed: a response-policy rule that maps those two names to `private.googleapis.com` (199.36.153.8/30), plus a route and a firewall allow for that range. **Verify** both hosts with a live call from dev (§10 test N7) before prod. Record the outcome in `docs/architecture/network.md`.

### Egress firewall (`modules/network`, network firewall policy)
| Priority | Direction | Match | Action |
|---|---|---|---|
| 100 | Egress | Destination: subnet and PSA ranges (Cloud SQL 5432, Redis 6378) | allow |
| 200 | Egress | Destination 199.36.153.4/30, TCP 443 (restricted VIP) | allow |
| 210 | Egress | Destination 199.36.153.8/30, TCP 443 (private VIP, Workspace exception only) | allow |
| 300 | Egress | `dest_fqdns = var.egress_allow_fqdns`, TCP 443 | allow |
| 65000 | Egress | 0.0.0.0/0, all | deny (logged) |

```hcl
resource "google_compute_network_firewall_policy_rule" "allow_fqdns" {
  firewall_policy = google_compute_network_firewall_policy.egress.name
  priority        = 300
  direction       = "EGRESS"
  action          = "allow"
  match {
    dest_fqdns = var.egress_allow_fqdns
    layer4_configs {
      ip_protocol = "tcp"
      ports       = ["443"]
    }
  }
  enable_logging = true
}
```
FQDN objects in firewall policies need **Cloud NGFW** (**Verify** the tier and price). If it isn't approved, the fallback is to allow TCP 443 to 0.0.0.0/0 at priority 300. That is then an accepted risk in `docs/compliance/risk/accepted-risks.md` (P0-11) with the sponsor's signature.

### KMS (`modules/kms`)
```hcl
resource "google_kms_key_ring" "kr" {
  name     = "kr-${var.env}"
  location = var.region
}
resource "google_kms_crypto_key" "k" {
  for_each        = toset(["sql", "redis", "artifact-registry", "tasks"])
  name            = each.key
  key_ring        = google_kms_key_ring.kr.id
  rotation_period = "7776000s"                    # 90 days
  lifecycle { prevent_destroy = true }
}
resource "google_kms_crypto_key_iam_member" "agent" {
  for_each      = var.service_agents             # e.g. redis -> service-<num>@cloud-redis.iam.gserviceaccount.com
  crypto_key_id = google_kms_crypto_key.k[each.key].id
  role          = "roles/cloudkms.cryptoKeyEncrypterDecrypter"
  member        = "serviceAccount:${each.value}"
}
```
Service-agent emails per product (Cloud SQL, Memorystore, Artifact Registry, Cloud Tasks): **Verify** each format in the product's CMEK page. Use `google_project_service_identity` (google-beta) where available to create them.

### Cloud Run (`modules/cloud_run_service`, `api` example)
```hcl
resource "google_cloud_run_v2_service" "svc" {
  name                = var.name                                   # "api" | "web"
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"
  deletion_protection = var.env != "dev"
  template {
    service_account                  = var.service_account
    timeout                          = "${var.timeout_s}s"         # api: 3600 (ADR 0002), web: 60
    session_affinity                 = var.session_affinity        # api: true
    max_instance_request_concurrency = var.concurrency             # api: 80 (P5-03 tunes)
    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }
    vpc_access {
      egress = "ALL_TRAFFIC"
      network_interfaces {
        network    = var.network_id
        subnetwork = var.subnet_id
      }
    }
    containers {
      image = var.image
      ports { container_port = 8080 }
      resources {
        limits   = { cpu = "1", memory = "1Gi" }
        cpu_idle = false                                            # instance-based billing (WebSockets)
      }
      dynamic "env" {
        for_each = var.env_vars
        content {
          name  = env.key
          value = env.value
        }
      }
      startup_probe {
        http_get { path = "/readyz" }
        period_seconds    = 3
        failure_threshold = 20
      }
      liveness_probe {
        http_get { path = "/healthz" }
        period_seconds = 15
      }
    }
  }
  lifecycle { ignore_changes = [template[0].containers[0].image, client, client_version] }  # P1-06 deploys images
}
```
Non-secret env set here: `ENV`, `SERVICE_NAME`, `VERTEX_PROJECT`, `VERTEX_LOCATION=us-central1` (§14), the Redis host and port, and the queue names. Secret env is added by P1-05. `web` uses the same module with `timeout_s = 60`, no affinity, and no Redis env.

### Load balancer and Cloud Armor (`modules/lb`, key resources)
- `google_compute_region_network_endpoint_group` (type `SERVERLESS`, `cloud_run { service = ... }`), one per service.
- `google_compute_backend_service` per NEG, `protocol = "HTTPS"`, `security_policy = google_compute_security_policy.edge.id`, a `log_config` block with `enable = true` and `sample_rate = 1.0`.
- `google_compute_url_map`: host `api.<domain>` → `api` backend; host `app.<domain>` → `web` backend; default → `web`.
- `google_compute_managed_ssl_certificate` for both hosts, `google_compute_target_https_proxy`, and `google_compute_global_forwarding_rule` on 443 with a reserved global IP. An HTTP (80) forwarding rule only redirects to HTTPS.
- An `ssl_policy` with `min_tls_version = "TLS_1_2"` and profile `MODERN`.

Cloud Armor baseline (`google_compute_security_policy.edge`):

| Priority | Rule | Action |
|---|---|---|
| 1000 | `evaluatePreconfiguredWaf('sqli-v33-stable')` (**Verify** rule-set names) | deny(403) |
| 1010 | `evaluatePreconfiguredWaf('xss-v33-stable')` | deny(403) |
| 2000 | `request.path.matches('/internal/.*')` | deny(404): internal routes are never reachable from the internet |
| 2100 | `request.path == '/v1/webhooks/messaging/whatsapp'` | allow, with a per-IP rate limit (Proposed 600/min); WAF rules for this path run in preview first. Added by P4-01: the Meta webhook is public and authenticated by its HMAC signature (DECISIONS #253) |
| 3000 | Rate limit per client IP: `cloud_armor_rate_limit_per_min` per minute, ban 10 min | rate_based_ban |
| 2147483647 | Default | allow |

WAF rules start in **preview mode** in dev for one week; enforce them after reviewing the logs for false positives.

### Artifact Registry
```hcl
resource "google_artifact_registry_repository" "app" {
  location      = var.region
  repository_id = "app"
  format        = "DOCKER"
  kms_key_name  = var.kms_key_id
  docker_config { immutable_tags = true }
  cleanup_policy_dry_run = false
  cleanup_policies {
    id     = "keep-last-20"
    action = "KEEP"
    most_recent_versions { keep_count = 20 }
  }
  cleanup_policies {
    id     = "delete-untagged-30d"
    action = "DELETE"
    condition {
      tag_state  = "UNTAGGED"
      older_than = "2592000s"
    }
  }
}
```
Enable `containerscanning.googleapis.com` for automatic vulnerability scanning on push, if it is in `allowed_services.yaml` (add it via P0-06 if not).

### Redis (`modules/redis`)
```hcl
resource "google_redis_instance" "main" {
  name                    = "redis-main"
  region                  = var.region
  tier                    = var.tier                       # BASIC | STANDARD_HA
  memory_size_gb          = var.memory_gb
  redis_version           = "REDIS_7_2"                    # Verify latest supported
  authorized_network      = var.network_id
  connect_mode            = "PRIVATE_SERVICE_ACCESS"       # can't be changed later
  reserved_ip_range       = var.psa_range_name
  transit_encryption_mode = "SERVER_AUTHENTICATION"        # creation-time only; TLS on 6378
  auth_enabled            = true
  customer_managed_key    = var.kms_key_id                 # creation-time only
  redis_configs           = { maxmemory-policy = "volatile-lru" }  # sessions/locks always have TTLs
  lifecycle { prevent_destroy = true }
}

resource "google_secret_manager_secret" "redis" {
  for_each  = toset(["redis-auth", "redis-ca"])
  secret_id = each.key
  replication { user_managed { replicas { location = var.region } } }
}
resource "google_secret_manager_secret_version" "auth" {
  secret      = google_secret_manager_secret.redis["redis-auth"].id
  secret_data = google_redis_instance.main.auth_string
}
resource "google_secret_manager_secret_version" "ca" {
  secret      = google_secret_manager_secret.redis["redis-ca"].id
  secret_data = google_redis_instance.main.server_ca_certs[0].cert
}
```
The AUTH string is in Terraform state. The state bucket is in `ops` and accessible only to `gcp-org-admins` and the CI deployer (P1-06). **Verify** the bucket IAM before the first apply.

**App connection** (handed to P1-05 and P2-01): `REDIS_URL=rediss://:<redis-auth>@<host>:6378/0`, with the CA from `redis-ca` written to a file at startup or passed as `ssl_ca_data`. P1-01's `create_redis` gains an optional `REDIS_CA_CERT` setting (P1-05 adds the field).

### Cloud Tasks queues (`modules/tasks`)
Payloads contain IDs only (F13, DECISIONS #75). Targets are `<api run.app URL>/internal/tasks/<queue>` (see the next paragraph).

Because `/internal/*` is blocked at Cloud Armor, the queue and Scheduler targets use the **Cloud Run service URL** (`*.run.app`), which is reachable only from inside the project or perimeter (internal ingress). **Verify** in dev (§10 test N8) that Cloud Tasks and Scheduler reach an `INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER` service via its `run.app` URL. If they don't, set the `api` ingress to `INGRESS_TRAFFIC_INTERNAL_ONLY` plus LB, per the Cloud Run docs.

| Queue | Used by | Max dispatches/s | Max concurrent | `max_attempts` | `min_backoff` | `max_backoff` | `max_doublings` | `max_retry_duration` | Why |
|---|---|---|---|---|---|---|---|---|---|
| `reminders` | P4-04 | 2 | 5 | 5 | 30s | 600s | 4 | 3600s | Pre-send re-fetch hits Open Dental (1 req/s per clinic); a reminder is useless after the visit |
| `notifications` | P4-03 (confirm, reschedule, cancel) | 5 | 10 | 8 | 10s | 300s | 4 | 7200s | Should arrive soon; give up after 2 h and alert |
| `callback-emails` | P2-22 | 5 | 10 | 10 | 10s | 300s | 5 | 21600s | Must not be lost; unsent alert after failures (P2-22) |

```hcl
resource "google_cloud_tasks_queue" "q" {
  for_each = var.queues
  name     = each.key
  location = var.region
  rate_limits {
    max_dispatches_per_second = each.value.rate
    max_concurrent_dispatches = each.value.concurrent
  }
  retry_config {
    max_attempts       = each.value.max_attempts
    min_backoff        = each.value.min_backoff
    max_backoff        = each.value.max_backoff
    max_doublings      = each.value.max_doublings
    max_retry_duration = each.value.max_retry_duration
  }
  stackdriver_logging_config { sampling_ratio = 1.0 }
}
```
CMEK for Cloud Tasks is configured per project and location, not per queue. **Verify** the Terraform resource name and the "no queue-level routing with CMEK" constraint. We use task-level HTTP targets only.

Task creation contract (for P2-22, P4-03, P4-04):
```python
# app/integrations/gcp/tasks.py (implemented by the first consumer; signature fixed here)
async def enqueue(queue: Literal["reminders", "notifications", "callback-emails"],
                  path: str,                     # e.g. "/internal/tasks/reminders"
                  payload: dict[str, str | int], # IDs only; validated: no key outside an allow-list (P4-03 adds `kind`: booked|rescheduled|cancelled)
                  task_id: str,                  # deterministic, e.g. f"rem-{apt_num}-{scheduled_for:%Y%m%d%H%M}" (dedup)
                  schedule_time: datetime | None = None) -> str: ...
# Raises ScheduleTooFarError if schedule_time > now + 29 days (stay under the 30-day limit).
```

### Cloud Scheduler jobs (`modules/scheduler`)
| Job | Schedule (UTC) | Target | Purpose |
|---|---|---|---|
| `callback-email-sweep` | `*/2 * * * *` | `POST <api run.app URL>/internal/jobs/callback-email-sweep` | Re-enqueue callback emails still `PENDING` after 2 minutes (P2-22, DECISIONS #207) |
| `reminder-sweep` | `0 * * * *` (hourly) | `POST <api run.app URL>/internal/jobs/reminder-sweep` | Enqueue reminders whose send time is in the next 48 h and not yet enqueued (P4-04); covers the 30-day Cloud Tasks limit and any booking horizon (DECISIONS #86) |
| `unsent-email-check` | `*/10 * * * *` | `POST …/internal/jobs/unsent-email-check` | Alert on callback emails not sent after retries (P2-22) |

```hcl
resource "google_cloud_scheduler_job" "job" {
  for_each         = var.jobs
  name             = each.key
  region           = var.region
  schedule         = each.value.schedule
  time_zone        = "Etc/UTC"
  attempt_deadline = "300s"
  retry_config { retry_count = 3 }
  http_target {
    http_method = "POST"
    uri         = each.value.uri
    oidc_token {
      service_account_email = var.invoker_sa          # sa-scheduler, has run.invoker on api only
      audience              = each.value.audience     # the api run.app URL
    }
  }
}
```
Handlers verify the OIDC token: audience, issuer and the exact service-account email (P1-13 implements; contract in §13).

### Outputs (per environment root)
```hcl
output "network_id"      { value = module.network.network_id }
output "psa_range_name"  { value = module.network.psa_range_name }      # P1-03
output "kms_key_ids"     { value = module.kms.key_ids }                 # P1-03 (sql), P1-05
output "repo_url"        { value = module.artifact_registry.repo_url }  # P1-06
output "api_service"     { value = module.api.service_name }            # P1-06, P1-07
output "web_service"     { value = module.web.service_name }
output "lb_ip"           { value = module.lb.lb_ip }
output "redis_host"      { value = module.redis.host }                  # P1-05, P2-01
output "redis_secret_ids"{ value = module.redis.secret_ids }
output "queue_ids"       { value = module.tasks.queue_ids }
output "sa_emails" {
  value = {
    api           = google_service_account.api.email
    web           = google_service_account.web.email
    tasks_invoker = google_service_account.tasks.email
    scheduler     = google_service_account.scheduler.email
  }
}
```

### Apply order and permissions
```bash
# One person plans, a second reviews the plan output (no secrets in it: sensitive values are redacted).
cd infra/env/dev
terraform init
terraform fmt -check -recursive ../../
terraform validate
terraform plan -out=tfplan
terraform apply tfplan
```
1. Apply `infra/org/` (PR adding the Cloud Run org policies) first.
2. Apply `env/dev`, then run §10.
3. Apply `env/staging`, then `env/prod`.

Only `gcp-org-admins` apply until P1-06 provides a CI deployer. No service-account keys are used (blocked by P0-06).

## 7. Implementation guide
1. **Read** the P0-14 `network.md`, P0-06 `infra/org/` and `allowed_services.yaml`, and `foundation.yaml`. Check that every API used here is in the allow-list: `run`, `compute`, `dns`, `servicenetworking`, `redis`, `cloudtasks`, `cloudscheduler`, `artifactregistry`, `containerscanning`, `cloudkms`, `secretmanager`, `networksecurity` (for NGFW, **Verify**). Add any that are missing through a P0-06 PR.
2. **Write the modules** in the order `kms` → `network` → `artifact_registry` → `redis` → `cloud_run_service` → `lb` → `tasks` → `scheduler`, each with a README table of inputs and outputs.
3. **Org PR** (`infra/org/`): add `run.allowedIngress` (`internal-and-cloud-load-balancing`) and `run.allowedVPCEgress` (`all-traffic`) on the folder. Review the `dai_dev` and `dai_staging` dry-run violation logs (Logs Explorer, `protoPayload.metadata.dryRun=true`), add the needed ingress and egress rules, then switch both to enforced.
4. **Dev apply** and the bootstrap image:
   1. apply `kms`, `network` and `artifact_registry` first;
   2. build and push the P1-01 image (`docker build` + `docker push` to `repo_url`, from a machine inside the allowed path, **Verify** the perimeter ingress for the push, or use Cloud Build in the project);
   3. apply the rest.
5. **DNS and certificates:** create A records `api.<domain>` and `app.<domain>` pointing to `lb_ip`. Managed certificates become ACTIVE only after DNS resolves (can take up to about an hour, **Verify**).
6. **Run the §10 tests** in dev, and record the outputs in `docs/runbooks/terraform.md` (no secrets).
7. **Staging and prod:** same steps with their `tfvars`; Redis `STANDARD_HA`, `api` min instances 1 in prod; deletion protection on.
8. **Update `docs/architecture/network.md`** (P0-14) with the real ranges, IPs, the NGFW-or-fallback decision and the Workspace-API outcome.
9. **Notify:**
   - P1-03: `psa_range_name`, `kms_key_ids.sql`, `network_id`;
   - P1-05: SA emails, `redis-auth`/`redis-ca` secrets, the `secret_env` input of the Cloud Run module, the `REDIS_CA_CERT` field;
   - P1-06: `repo_url`, service names, `ignore_changes` on the image, the perimeter ingress rule for CI;
   - P1-07: LB and NAT logs, firewall deny logs, queue names;
   - P1-13: OIDC verification contract;
   - P2-01: Redis TLS URL;
   - P2-22, P4-03, P4-04: queues, `enqueue()` contract, the 30-day limit, the sweep job;
   - P0-13: `VERTEX_LOCATION=us-central1` (§14).

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| Redis was created without TLS or CMEK by mistake | It can't be fixed in place. Destroy and recreate it (dev/staging); in prod, create a new instance and switch over (sessions are short-lived). `prevent_destroy` makes this a deliberate act. |
| A Cloud Run revision is deployed with ingress `all` | Blocked by the `run.allowedIngress` org policy. |
| A Cloud Run revision without VPC egress | Blocked by `run.allowedVPCEgress`. |
| Egress to a host not in the allow-list (e.g. a new SaaS) | The connection times out; the firewall deny log shows it. Adding a host needs a `vendors.yaml` row (P0-10) and a PR to `egress_allow_fqdns`. |
| Gmail or OAuth2 calls fail via the restricted VIP | Expected risk; apply the private-VIP response-policy exception (§6) and re-test (N7). Never remove the restricted VIP mapping for other APIs. |
| The managed certificate is stuck in PROVISIONING | DNS isn't pointing to `lb_ip`, or CAA records block Google CAs. Check `dig`, fix DNS, wait. |
| Cloud Tasks returns an error for `schedule_time` > 30 days | `enqueue()` raises `ScheduleTooFarError` before calling the API; callers rely on the sweep instead. |
| The same reminder is enqueued twice (sweep and booking) | Deterministic `task_id` makes the second create fail with ALREADY_EXISTS, which `enqueue()` treats as success. **Verify** task-name dedup window (~1 h after deletion/execution). |
| A queue handler returns 5xx repeatedly | Retries per policy; after `max_retry_duration` the task is dropped. Handlers must record failure state in the DB before returning 5xx on the last attempt (P2-22/P4-04 own this). |
| The dry-run logs show a needed Google API outside the perimeter (e.g. Workspace) | Handle it with the documented exception, not by weakening the perimeter. Record it in `network.md`. |
| `terraform destroy` run against prod by mistake | `prevent_destroy` on keys and Redis, deletion protection on Cloud Run, and the projects are not managed here (DECISIONS #87). |
| Cloud NGFW not approved (cost) | Use the 0.0.0.0/0:443 fallback with an accepted-risk entry; revisit in P5-14. |

## 9. Security, HIPAA and PHI
- **No PHI is handled by this task**, but it builds where PHI will live (prod Redis, queues).
- **Controls implemented here:**
  - CMEK on Redis, Artifact Registry and Cloud Tasks (and the key for Cloud SQL), with 90-day rotation;
  - TLS 1.2+ at the load balancer and on Redis;
  - Redis AUTH;
  - no public IPs on data stores;
  - load-balancer-only ingress with Cloud Armor (WAF, rate limiting, `/internal/*` blocked);
  - all egress through the VPC, with a deny-by-default firewall and an FQDN allow-list;
  - Google APIs through the restricted VIP inside enforced perimeters;
  - OIDC-authenticated internal jobs;
  - IDs-only task payloads.
- **Secrets:** the Redis AUTH string lives in Secret Manager and in the Terraform state. The state bucket access is limited (verify before the first apply). No service-account keys.
- **Audit:**
  - admin activity on all resources is in Cloud Audit Logs;
  - LB request logs, firewall deny logs and NAT logs are enabled;
  - P1-07 routes and retains them;
  - LB logs contain URLs, so **no PHI in URLs** (F01) is critical.

## 10. Testing
Static checks (CI via P1-06; run locally now):
```bash
terraform fmt -check -recursive infra/
terraform validate                       # each root
tflint --recursive infra/                # Proposed; Verify ruleset for google provider
checkov -d infra/ --framework terraform  # Proposed: fails on public IPs, missing CMEK, open firewall
```

Negative and positive tests in dev, recorded in `docs/runbooks/terraform.md`:
| # | Test | Command (example) | Expected |
|---|---|---|---|
| N1 | `run.app` URL is not reachable from the internet | `curl -s -o /dev/null -w "%{http_code}" https://api-xxxx-uc.a.run.app/healthz` | 403 or 404 (not 200) |
| N2 | LB path works | `curl https://api.<domain>/healthz` | 200 |
| N3 | `/internal/*` is blocked at the edge | `curl -X POST https://api.<domain>/internal/jobs/reminder-sweep` | 404 from Cloud Armor |
| N4 | Redis has no public endpoint; TLS + AUTH + CMEK | `gcloud redis instances describe redis-main --region us-central1 --format="value(transitEncryptionMode,authEnabled,customerManagedKey,connectMode)"` | `SERVER_AUTHENTICATION True projects/…/redis PRIVATE_SERVICE_ACCESS` |
| N5 | Redis refuses plain TCP | from a dev Cloud Run job: `redis-cli -h <host> -p 6378 PING` without TLS | connection error |
| N6 | Egress allow-list | from a dev Cloud Run job: `curl -m 5 https://example.com` and `curl -m 5 https://api.opendental.com/api/v1/` | first times out; second returns an HTTP status (401 is fine) |
| N7 | Workspace APIs reachable | from the dev job: `curl -m 5 https://gmail.googleapis.com/` and `https://oauth2.googleapis.com/` | an HTTP status (not timeout); record which VIP served it |
| N8 | Tasks and Scheduler reach internal Cloud Run | `gcloud scheduler jobs run unsent-email-check --location us-central1`, then check the `api` request log | request logged with the `sa-scheduler` identity, 2xx/404 from the app |
| N9 | CMEK on Artifact Registry | `gcloud artifacts repositories describe app --location us-central1 --format="value(kmsKeyName)"` | the `artifact-registry` key |
| N10 | Vulnerability scan runs | push an image; `gcloud artifacts docker images list … --show-occurrences` | scan results present |
| N11 | Cloud Run revision with ingress `all` is refused | `gcloud run services update api --ingress all` | org policy violation |
| N12 | Vertex AI via restricted VIP | from the dev job: call `us-central1-aiplatform.googleapis.com` with a trivial request | success; the DNS lookup returns 199.36.153.x |

## 11. Acceptance criteria
- [ ] The modules and the dev, staging and prod roots exist; `fmt`, `validate` and a reviewed `plan` pass; `apply` succeeded in all three environments
- [ ] No data store has a public IP. Redis is `PRIVATE_SERVICE_ACCESS` with TLS (6378), AUTH and CMEK, and Artifact Registry and Cloud Tasks use CMEK (N4, N9)
- [ ] Cloud Run `api` and `web` run with LB-only ingress, Direct VPC egress (all traffic), the ADR 0002 settings and probes on `/readyz` and `/healthz`; the `run.app` URL is not reachable from the internet (N1, N2, N11)
- [ ] The LB has managed TLS (min TLS 1.2) and the Cloud Armor baseline (WAF, rate limit, `/internal/*` denied) (N3)
- [ ] Egress is deny-by-default, with only the restricted VIP, the Workspace exception and the FQDN allow-list open (N6, N7, N12)
- [ ] Queues `reminders`, `notifications` and `callback-emails` exist with the §6 retry policies; Scheduler jobs `reminder-sweep` and `unsent-email-check` call `api` with OIDC (N8)
- [ ] `run.allowedIngress` and `run.allowedVPCEgress` are set; `dai_dev` and `dai_staging` are enforced
- [ ] `redis-auth` and `redis-ca` secrets exist; the outputs listed in §6 are available
- [ ] `docs/runbooks/terraform.md` and `docs/architecture/network.md` are updated; the §7 step 9 issues are notified

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI: `fmt`/`validate`/`tflint`/`checkov` run in CI once P1-06 adds them; N1–N12 results are recorded
- [ ] PR reviewed (HIPAA review if labelled `phi`): tech lead + compliance owner (network and egress); no `phi` label
- [ ] No PHI in logs: no PHI exists yet; LB logging is on and URLs must stay PHI-free (F01)
- [ ] Docs / README updated: module READMEs, `terraform.md`, `network.md`

## 13. Hand-off
| Task | Can rely on |
|---|---|
| P1-03 Cloud SQL | `network_id`, `psa_range_name`, the `sql` CMEK key, Direct VPC egress from `api` |
| P1-05 Secrets/IAM | SA identities, `secret_env` input, `redis-auth`/`redis-ca`, KMS key ring for app keys |
| P1-06 CI/CD | `repo_url`, service names, image managed outside Terraform, perimeter ingress rule for CI, the static checks to run |
| P1-07 Logging | LB, NAT, firewall and queue logs; service names for uptime checks (via LB host) |
| P1-13 Auth | OIDC verification for `/internal/*`: audience = api `run.app` URL, issuer `https://accounts.google.com`, email ∈ {`sa-scheduler`, `sa-tasks-invoker`} |
| P2-01 Slot memory | `rediss://` on 6378 with AUTH and CA; `volatile-lru` (every key must have a TTL) |
| P2-22, P4-03, P4-04 | Queue names and policies, `enqueue()` contract, `ScheduleTooFarError`, `reminder-sweep` and `unsent-email-check` jobs |
| P2-25 | Cloud Armor policy to extend with bot protection |
| P0-13 / P2-03 | `VERTEX_LOCATION=us-central1` through the restricted VIP |

## 14. Open questions
| Question | Owner | Needed by |
|---|---|---|
| Which domain hosts the app (`api.<domain>`, `app.<domain>`), and who manages its DNS? | Project sponsor | Step 5 |
| Is Cloud NGFW (FQDN egress rules) approved for cost, or do we accept the 0.0.0.0/0:443 fallback? | Sponsor + compliance owner | Step 2 |
| Confirm `VERTEX_LOCATION=us-central1` instead of `us` for the MVP (the `us` multi-region needs a PSC endpoint). | Tech lead (with the P0-13 ADR) | Step 4 |
| Do Gmail and OAuth2 work through the private-VIP exception inside an enforced perimeter (N7)? | Tech lead | Before prod apply |

## 15. References
- Plan §3.2, §4.7, §4.9, §6
- Cloud Run + VPC-SC: https://docs.cloud.google.com/run/docs/securing/using-vpc-service-controls
- Restricted VIP setup: https://docs.cloud.google.com/vpc-service-controls/docs/set-up-private-connectivity
- Regional/multi-regional Google API endpoints: https://docs.cloud.google.com/vpc/docs/about-accessing-regional-google-apis-endpoints
- Cloud Run ingress: https://docs.cloud.google.com/run/docs/securing/ingress
- Serverless NEG + LB: https://docs.cloud.google.com/load-balancing/docs/https/setting-up-https-serverless
- Cloud SQL from Cloud Run: https://docs.cloud.google.com/sql/docs/postgres/connect-run
- Memorystore TLS / AUTH / CMEK / networking: https://docs.cloud.google.com/memorystore/docs/redis/about-in-transit-encryption, …/about-redis-auth, …/cmek, …/networking
- Cloud Tasks quotas and queues: https://docs.cloud.google.com/tasks/docs/quotas, https://docs.cloud.google.com/tasks/docs/configuring-queues, https://docs.cloud.google.com/tasks/docs/creating-http-target-tasks
- Cloud Scheduler auth: https://docs.cloud.google.com/scheduler/docs/http-target-auth
- Artifact Registry CMEK and cleanup: https://docs.cloud.google.com/artifact-registry/docs/cmek, https://docs.cloud.google.com/artifact-registry/docs/repositories/cleanup-policy
- Terraform Google provider: https://registry.terraform.io/providers/hashicorp/google/latest/docs
- Related tasks: P0-05, P0-06, P0-07, P0-08, P0-10, P0-11, P0-13, P0-14, P1-01, P1-03, P1-05, P1-06, P1-07, P1-13, P2-01, P2-22, P2-25, P4-03, P4-04, P5-03, P5-12, P5-14
