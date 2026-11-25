---
id: P1-06
title: CI/CD pipeline - build once, migrate, deploy to dev, promote to staging and prod
milestone: P1
epic: E1.1
size: L
labels: area:infra, type:chore
depends_on: P1-01, P1-02, P1-03, P1-05
status: approved
---

# P1-06: CI/CD pipeline - build once, migrate, deploy to dev, promote to staging and prod

## 1. Summary
Build the delivery pipeline on **GitHub Actions** with **Workload Identity Federation (WIF)**, so GitHub never holds a Google Cloud key. The pipeline:
- **Builds** the `api` and `web` images **once** per merge to `main`, tagged with the git SHA, and pushes them to the dev Artifact Registry.
- **Deploys to dev automatically:**
  1. run the `migrate` Cloud Run job;
  2. update `api` and `web` to the new image digest;
  3. smoke test through the load balancer;
  4. roll back traffic automatically if the smoke test fails.
- **Promotes the same digest** to staging (one approval) and prod (two approvals from `prod-approvers`, never the requester) through **release PRs** (`releases/staging.yaml`, `releases/prod.yaml`). Promotion copies the image; it never rebuilds.
- **Blocks prod** when:
  - the image has an unwaived CRITICAL vulnerability;
  - or, once PHI is enabled, the PHI gate (`check_vendors.py --gate`, P0-10) is closed.
- **Runs Terraform:**
  - `plan` on PRs that touch `infra/`, posted as a PR comment;
  - `apply` for staging and prod only through an approved release PR (`releases/tf-<env>.yaml`); dev by manual run.
- **Runs nightly jobs:**
  - `iam_audit.py` (P1-05);
  - the Open Dental smoke and integration tests against test DB (B) (P0-12);
  - dependency audits;
  - the image vulnerability report.

Done means:
- a merge to `main` reaches dev without manual steps;
- staging and prod can be reached only through the promote workflow with the §6 approvals;
- there are no service-account keys or long-lived GCP credentials in GitHub;
- a failed smoke test leaves the previous revision serving.

## 2. Why this matters
Every later task ships through this pipeline. For a HIPAA system the pipeline is also a security boundary:
- the identity that deploys to prod can change code that handles PHI;
- P0-11 **R06** (a compromised or over-privileged identity) is mitigated by WIF and short-lived tokens, plus approvals.

"Build once, promote the digest" guarantees that prod runs exactly what was tested in dev and staging. Automatic migration and rollback keep deploys safe during the pilot, when the clinic depends on the system.

The pipeline also enforces the gates that earlier tasks defined but couldn't run by themselves:
- the vendor matrix and PHI gate (P0-10);
- message templates (P0-15);
- Terraform static checks (P1-02);
- the IAM audit (P1-05);
- the Open Dental smoke test (P0-12).

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P1, Core Platform & Open Dental Adapter**.
- **What already exists:**
  - **P0-05:** project `<prefix>-ops` (outside the perimeters) with the state bucket `gs://<prefix>-ops-tfstate`.
  - **P0-06:**
    - perimeters `dai_dev`, `dai_staging` and `dai_prod` around the environment projects;
    - an admin ingress rule;
    - SA keys blocked;
    - the CI ingress rule is left to this task.
  - **P1-01:**
    - `pr.yml` with required checks `backend`, `frontend` and `compliance`;
    - the backend `Dockerfile` (port 8080);
    - `/healthz` and `/readyz`;
    - branch protection and CODEOWNERS.
  - **P1-02:**
    - an Artifact Registry repo `app` per environment (CMEK, immutable tags, scanning on push);
    - Cloud Run `api` and `web` with `ignore_changes` on the image;
    - load balancer hosts `api.<domain>` and `app.<domain>`;
    - the static checks to run (`fmt`, `validate`, `tflint`, `checkov`).
  - **P1-03:** SA `sa-migrate`; Alembic commands with `-x api_user` and `-x migrate_user`; `alembic check`.
  - **P1-05:**
    - the `iam_workloads` module pattern;
    - `iam_audit.py --json`;
    - pinned secret versions in staging and prod tfvars.
- **Facts to verify at implementation:**
  - **GitHub OIDC:**
    - GitHub issues an OIDC token to a job with `permissions: id-token: write`;
    - the token's claims include `repository`, `repository_id`, `repository_owner_id`, `ref`, `environment` (when the job uses an environment), `event_name` and `workflow_ref`;
    - pull requests from forks get no token by default.
    - **Verify** the claim list at https://docs.github.com/actions/security-for-github-actions/security-hardening-your-deployments/about-security-hardening-with-openid-connect.
  - **Google WIF:**
    - a workload identity pool and an OIDC provider map claims to attributes;
    - an `attribute_condition` limits which tokens are accepted;
    - a principal set (`principalSet://…/attribute.environment/prod`) gets `roles/iam.workloadIdentityUser` on a service account.
    - **Verify** the docs and the `google-github-actions/auth` action's current major version.
  - **VPC-SC ingress rules:**
    - an ingress rule can allow a specific service-account identity from **any source** (`sources { access_level = "*" }`) to specific services;
    - **Verify** this, and whether `run.googleapis.com` and `artifactregistry.googleapis.com` support method-level restrictions.
    - P0-14 noted a restriction on identity types for some Cloud Run ingress cases, so **Verify** with a dry-run first (§7 step 2).
  - **GitHub plans** (docs read 2026-11-24; our repo is private):
    - GitHub Free can configure environments only for public repos, and Free organizations get no protected branches or code owners for private repos;
    - GitHub Team (and Pro) can configure environments and deployment branch rules for private repos, and have protected branches and code owners;
    - **required reviewers** (and "prevent self-review") on environments are available for private repos **only on GitHub Enterprise**. The docs say: "If you are on a GitHub Free, GitHub Pro, or GitHub Team plan, required reviewers are only available for public repositories."
    - **Decision (DECISIONS #110):** we use **GitHub Team** and enforce approvals with **release PRs** (branch protection + CODEOWNERS + an approval check in the workflow) instead of environment reviewers, so no Enterprise plan is needed.
  - **Image copy:** `crane copy` (go-containerregistry) copies an image by digest between registries without changing the digest. **Verify** whether `gcloud artifacts docker images copy` (or an equivalent) exists and is simpler.

## 4. Scope
**In scope**
- **Terraform** `infra/ci/` (state `gs://<prefix>-ops-tfstate/ci/`), applied by `gcp-org-admins`:
  - the WIF pool and GitHub provider in `ops`;
  - CI service accounts in `ops` and their roles in each environment project;
  - the `principalSet` bindings;
  - the perimeter ingress rules (PR to `infra/org/`).
- **Terraform in the environment roots:**
  - the Cloud Run job `migrate` (image ignored like the services);
  - `traffic` added to `ignore_changes` in P1-02's `cloud_run_service` module (rollbacks change traffic outside Terraform).
- **`frontend/Dockerfile`** (Next.js standalone output, port 8080, non-root) and the `APP_VERSION` build argument in both Dockerfiles.
- **`GET /healthz` returns the version:** `{"status":"ok","version":"<git sha>"}` from the `APP_VERSION` env baked into the image (a small extension of P1-01).
- **Workflows** in `.github/workflows/`:
  - `pr.yml`, extended with the `terraform` and `image-build` jobs and the plan comment;
  - `deploy-dev.yml`;
  - `promote.yml`;
  - `rollback.yml`;
  - `terraform-apply.yml`;
  - `nightly.yml` (P2-30 adds job `e2e-staging`; `promote.yml` gains a gate requiring a green `e2e-staging` run for the digest before the prod step, DECISIONS #218).
  - Addition (P5 / P6, DECISIONS #272–#276, #280): `pr.yml` gains `evals-fast` (path filter, required), `evals-schema`, `sched-edge`, `secrets-scan`, `semgrep`, `authz-matrix`; `nightly.yml` gains `evals-full`, `evals-staging-smoke`, `sched-props`, `secrets-weekly`, `zap-weekly`; `promote.yml`'s prod step also requires a green `evals-full` ≤ 72 h for the release commit, green staging race + reminder runs (P5-04), a clean canary PHI scan (P5-08) and, if voice code changed, a green `voice-quality.yml` (P5-03); CI signs image digests for Binary Authorization if it is adopted (P5-08). CODEOWNERS adds `evals/overrides/**` (ai-leads + tech-leads).
  - Addition (P4-17, DECISIONS #268): job `e2e-phase4` runs on `workflow_run` after `promote.yml` deploys a digest to staging, and on `workflow_dispatch` (no schedule; single developer). `promote.yml`'s prod step also requires a green `e2e-phase4` run (L1–L9) for the digest; a LIVE-only failure does not block.
- **Scripts** in `scripts/ci/`: `smoke.sh`, `vuln_gate.py`, `deploy_service.sh`, `run_migrations.sh`.
- **GitHub settings:**
  - environments `dev`, `staging`, `prod`, `tf-dev`, `tf-staging`, `tf-prod`, `nightly` with deployment branch rule `main` only (no environment reviewers; see §6);
  - team `prod-approvers`, CODEOWNERS for `releases/` and `.github/`, and the `releases/` files;
  - branch protection updated (new required checks);
  - Dependabot for GitHub Actions, uv and pnpm.
- **Security waiver file** `security/vuln-waivers.yaml` (schema in §6).
- **`docs/runbooks/deploy.md`:** how to deploy, promote, roll back and handle a failed migration.

**Out of scope** (and which task covers it)
- Alerting on deploy failures beyond GitHub notifications → P1-07 (it can alert on a revision failing to become ready)
- Binary Authorization (only signed images run in prod) → P5-08 (Proposed; **Verify** HIPAA coverage first)
- Load and performance tests in the pipeline → P5-03
- Eval suites (conversation scenarios) as a gate → P5-01 adds them to `pr.yml` / nightly using the patterns here
- Penetration testing → P5-11; OWASP review and SAST beyond ruff `S` → P5-08
- Clinic onboarding steps (prod secrets, clinic row) → P6-01

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P1-01 Repo (approved spec) | `pr.yml`, Dockerfile, health endpoints | Extend the files from the spec; open the PR against the skeleton branch. |
| P1-02 Terraform base (approved spec) | AR repos, Cloud Run services, LB hosts, perimeters enforced | Write the workflows now. Test the WIF login and the build against dev as soon as P1-02 dev is applied. Use `--dry-run` style steps (`echo` the gcloud commands) until then. |
| P1-03 Cloud SQL (approved spec) | `sa-migrate`, Alembic commands | Before P1-03 is applied, the `migrate` step is skipped behind the repo variable `MIGRATIONS_ENABLED=false`. |
| P1-05 IAM/secrets (approved spec) | `iam_workloads` module, `iam_audit.py`, secret-version tfvars | Write the CI SAs with the same module; the nightly IAM job starts once `iam_audit.py` exists. |
| GitHub admin (external) | The org on the **GitHub Team** plan (needed for protected branches, code owners and private-repo environments); an admin to create environments, the team and branch protection | Ask the repo owner on day 1; the list of settings is in §6. |

## 6. Interface contract

### Identities (all in `<prefix>-ops`, no keys)
| SA | Used by (GitHub environment / event) | Roles |
|---|---|---|
| `sa-ci-build` | `deploy-dev.yml` build job (`environment: dev`, ref `main`) | `artifactregistry.writer` on the dev `app` repo |
| `sa-deploy-dev` | dev deploy job (`environment: dev`) | In dev: `run.developer` (project); `iam.serviceAccountUser` on `sa-api`, `sa-web`, `sa-migrate`; `artifactregistry.reader` on `app` |
| `sa-deploy-staging` | `promote.yml` (`environment: staging`) | In staging: same as dev + `artifactregistry.writer` on staging `app`. In dev: `artifactregistry.reader` on `app` (copy source) |
| `sa-deploy-prod` | `promote.yml` (`environment: prod`) | In prod: same as staging. In staging: `artifactregistry.reader` (copy source) |
| `sa-tf-plan` | `pr.yml` terraform job (event `pull_request`, same repo only) | `viewer`, `iam.securityReviewer` and `storage.objectViewer` on the state bucket, in each env project. **No secret access.** |
| `sa-tf-apply-<env>` | `terraform-apply.yml` (`environment: tf-<env>`) | `owner` on that env project, `storage.objectAdmin` on the state bucket prefix `env/<env>/`. Exempt from `iam_audit.py` A1 by name; usable only after approval. |
| `sa-ci-tests` | `nightly.yml` (`environment: nightly`, schedule) | In dev: `secretmanager.secretAccessor` on `od-customer-key-testdb` and `od-developer-key`; `iam.securityReviewer` in all envs (for `iam_audit.py`) |

```hcl
# infra/ci/wif.tf
resource "google_iam_workload_identity_pool" "github" {
  project                   = var.ops_project_id
  workload_identity_pool_id = "github"
  display_name              = "GitHub Actions"
}

resource "google_iam_workload_identity_pool_provider" "github" {
  project                            = var.ops_project_id
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-oidc"
  attribute_mapping = {
    "google.subject"         = "assertion.sub"
    "attribute.repository"   = "assertion.repository"
    "attribute.repo_id"      = "assertion.repository_id"
    "attribute.ref"          = "assertion.ref"
    "attribute.environment"  = "assertion.environment"
    "attribute.event"        = "assertion.event_name"
  }
  # Only our repository (by immutable numeric IDs, so a renamed or recreated repo can't match)
  attribute_condition = "assertion.repository_owner_id == '${var.github_owner_id}' && assertion.repository_id == '${var.github_repo_id}'"
  oidc { issuer_uri = "https://token.actions.githubusercontent.com" }
}

# Prod deployer: only jobs running in the GitHub environment "prod"
resource "google_service_account_iam_member" "prod_deployer_wif" {
  service_account_id = google_service_account.deploy["prod"].name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.environment/prod"
}
# sa-tf-plan: member = ".../attribute.event/pull_request"; sa-ci-build: ".../attribute.ref/refs/heads/main" (and environment dev)
```
A job can only become `sa-deploy-prod` if it runs in the `prod` environment, which is allowed only on `main`. The only workflow on `main` that uses `prod` is `promote.yml`, which runs after a release PR is merged and first checks the PR's approvals (§6). Changes to `.github/` and `releases/` need `prod-approvers` review (CODEOWNERS), so nobody can add another path to `prod` alone.

### Perimeter ingress rules (PR to `infra/org/`, P0-06 owns the code)
| Perimeter | Identity | Sources | Services |
|---|---|---|---|
| `dai_dev` | `sa-ci-build`, `sa-deploy-dev`, `sa-deploy-staging` (copy source), `sa-tf-plan`, `sa-tf-apply-dev`, `sa-ci-tests` | any (`*`) | `artifactregistry`, `run`; Terraform SAs: all restricted services; `sa-ci-tests`: `secretmanager` |
| `dai_staging` | `sa-deploy-staging`, `sa-deploy-prod` (copy source), `sa-tf-plan`, `sa-tf-apply-staging` | any | same pattern |
| `dai_prod` | `sa-deploy-prod`, `sa-tf-plan`, `sa-tf-apply-prod` | any | same pattern |

**Verify** that identity-scoped ingress from any source works for these services. If it doesn't:
- **Fallback:** run builds and deploys in a **Cloud Build private pool** inside each environment project. GitHub only starts the build (`gcloud builds submit` / triggers), which needs an ingress rule only for `cloudbuild.googleapis.com`.
- Record the outcome in `docs/runbooks/deploy.md` and DECISIONS.

### GitHub environments, approvals and release PRs
We use **GitHub Team**. Environment reviewers are not available for private repos on Team, so approvals are enforced by **release PRs** (decided, DECISIONS #110).

| Environment | Used by | Branch rule | Approval enforced by |
|---|---|---|---|
| `dev` | `deploy-dev.yml` | `main` only | PR review on the code change (P1-01 branch protection) |
| `staging` | `promote.yml` (target staging) | `main` only | Release PR on `releases/staging.yaml`: 1 approval from someone other than the author |
| `prod` | `promote.yml` (target prod) | `main` only | Release PR on `releases/prod.yaml`: 2 approvals from `prod-approvers`, not the author, at least one A or B |
| `tf-dev` | `terraform-apply.yml` (manual run) | `main` only | PR review on the Terraform change |
| `tf-staging` | `terraform-apply.yml` | `main` only | Release PR on `releases/tf-staging.yaml`: 1 approval |
| `tf-prod` | `terraform-apply.yml` | `main` only | Release PR on `releases/tf-prod.yaml`: same rule as `prod` |
| `nightly` | `nightly.yml` | `main` only | none (read-only jobs) |

**`prod-approvers` team** (names are placeholders until set by the sponsor):
| Member | Role |
|---|---|
| **A** | Tech lead |
| **B** | Compliance owner |
| **C** | Senior engineer |

Each prod or `tf-prod` release needs two of them, never the PR author, and at least one of A or B. A fourth member can be added later with a PR that updates this table in `docs/runbooks/deploy.md` and the team.

**Release files** (one small YAML per target; the PR that changes it is the request):
```yaml
# releases/prod.yaml
sha: 3f9c2e1d7b...            # full git SHA already serving in staging
type: normal                  # normal | hotfix
reason: ""                    # required for hotfix: what is broken in prod
requested_by: "@github-user"  # informational; the PR author is what counts
```
```yaml
# releases/tf-prod.yaml
root: env/prod                # env/prod | ci
sha: 3f9c2e1d7b...            # the commit whose Terraform is applied (already merged to main)
```

**How approval is enforced (all of these, together):**
1. **CODEOWNERS:** `/releases/ @org/prod-approvers` and `/.github/ @org/prod-approvers`. Branch protection on `main` has "Require review from Code Owners", "Dismiss stale approvals" and at least 1 approval (P1-01). So no release file or workflow change merges without a `prod-approvers` review.
2. **Approval check step:** the first step of `promote.yml` and `terraform-apply.yml` runs `scripts/ci/check_release_approvals.py`. It reads the merged PR for the push (`GET /repos/{owner}/{repo}/commits/{sha}/pulls`, then `/pulls/{n}/reviews`) and fails unless:
   - the PR changed only the one release file;
   - for staging: at least 1 `APPROVED` review by someone other than the author;
   - for prod and `tf-prod`: at least 2 `APPROVED` reviews, from distinct `prod-approvers` members, none of them the author, at least one of A or B;
   - each review is on the final commit of the PR.
   Team membership is read with the workflow's `GITHUB_TOKEN` (**Verify** that `members: read` is enough, or use a fine-grained read-only token stored as a GitHub secret, which is not a GCP credential).
3. **Environment branch rule:** `prod` and `tf-prod` jobs run only from `main`, so a branch can't impersonate `sa-deploy-prod` (WIF binds the `prod` environment claim).

If the org ever moves to GitHub Enterprise, environment reviewers can be added on top. The release PRs stay as the request record.

Branch protection on `main` (adds to P1-01):
- required checks `backend`, `frontend`, `compliance`, `image-build`, plus `terraform` when `infra/` changed;
- linear history;
- no force pushes;
- dismiss stale approvals.

### Image naming and tags
```text
us-central1-docker.pkg.dev/<project>/app/api:<git-sha>      # immutable tag (P1-02 immutable_tags = true)
us-central1-docker.pkg.dev/<project>/app/web:<git-sha>
```
Deploys always use the **digest** (`…/api@sha256:…`), resolved once after the build and passed between jobs as an output. No `latest` tag exists.

Build arguments: `APP_VERSION=<git-sha>`, `BUILD_TIME=<RFC3339 UTC>`; both images set `ENV APP_VERSION=$APP_VERSION`.

### `deploy-dev.yml` (excerpt; pin actions by commit SHA in the real file)
```yaml
name: deploy-dev
on:
  push:
    branches: [main]
concurrency: {group: deploy-dev, cancel-in-progress: false}
permissions: {contents: read, id-token: write}
jobs:
  build:
    runs-on: ubuntu-latest
    environment: dev
    outputs:
      api_digest: ${{ steps.push.outputs.api_digest }}
      web_digest: ${{ steps.push.outputs.web_digest }}
    steps:
      - uses: actions/checkout@v4
      - uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ vars.WIF_PROVIDER }}   # projects/<num>/locations/global/workloadIdentityPools/github/providers/github-oidc
          service_account: ${{ vars.SA_CI_BUILD }}
      - uses: google-github-actions/setup-gcloud@v2
      - run: gcloud auth configure-docker us-central1-docker.pkg.dev --quiet
      - id: push
        run: |
          REPO=us-central1-docker.pkg.dev/${{ vars.DEV_PROJECT }}/app
          for svc in api web; do
            ctx=$([ "$svc" = api ] && echo backend || echo frontend)
            docker build --build-arg APP_VERSION=${GITHUB_SHA} -t $REPO/$svc:${GITHUB_SHA} $ctx
            docker push $REPO/$svc:${GITHUB_SHA}
            digest=$(gcloud artifacts docker images describe $REPO/$svc:${GITHUB_SHA} --format='value(image_summary.digest)')
            echo "${svc}_digest=$REPO/$svc@$digest" >> "$GITHUB_OUTPUT"
          done
  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment: dev
    steps:
      - uses: actions/checkout@v4
      - uses: google-github-actions/auth@v2
        with: {workload_identity_provider: "${{ vars.WIF_PROVIDER }}", service_account: "${{ vars.SA_DEPLOY_DEV }}"}
      - uses: google-github-actions/setup-gcloud@v2
      - run: scripts/ci/run_migrations.sh dev "${{ needs.build.outputs.api_digest }}"
      - run: scripts/ci/deploy_service.sh dev api "${{ needs.build.outputs.api_digest }}"
      - run: scripts/ci/deploy_service.sh dev web "${{ needs.build.outputs.web_digest }}"
      - run: scripts/ci/smoke.sh "https://api.${{ vars.DEV_DOMAIN }}" "https://app.${{ vars.DEV_DOMAIN }}" "${GITHUB_SHA}"
      - if: failure()
        run: scripts/ci/deploy_service.sh dev --rollback-all
```

### Scripts
```bash
# scripts/ci/run_migrations.sh <env> <api_digest>
# Updates the job image, runs it, waits; fails the workflow on a non-zero exit.
gcloud run jobs update migrate --region us-central1 --project "$PROJECT" --image "$DIGEST"
gcloud run jobs execute migrate --region us-central1 --project "$PROJECT" --wait
```
```bash
# scripts/ci/deploy_service.sh <env> <service> <digest> | <env> --rollback-all
# 1. remember the revision currently serving 100% (written to $RUNNER_TEMP/prev_<service>)
# 2. gcloud run services update <service> --image <digest> --region us-central1 --project <project>
#    (only the image changes; Terraform owns everything else; traffic goes to the new revision once ready)
# 3. --rollback-all: gcloud run services update-traffic <service> --to-revisions <prev>=100 for each remembered service
```
```bash
# scripts/ci/smoke.sh <api_url> <web_url> <expected_sha>
# - GET <api_url>/healthz -> 200 and .version == expected_sha (retries for up to 120 s, every 5 s)
# - GET <api_url>/readyz  -> 200
# - GET <web_url>/        -> 200
# - GET <api_url>/internal/jobs/reminder-sweep -> 404 (Cloud Armor still blocks internal paths)
# exits 1 with a short reason; prints no response bodies
```

The `migrate` Cloud Run job (Terraform, env roots):
```hcl
resource "google_cloud_run_v2_job" "migrate" {
  name     = "migrate"
  location = var.region
  template {
    task_count = 1
    template {
      service_account = var.sa_emails.migrate
      timeout         = "600s"
      max_retries     = 0                          # a failed migration is never retried blindly
      vpc_access {
        egress = "ALL_TRAFFIC"
        network_interfaces {
          network    = var.network_id
          subnetwork = var.subnet_id
        }
      }
      containers {
        image   = var.bootstrap_image
        command = ["uv", "run", "alembic"]
        args    = ["-x", "api_user=${var.db_iam_users.api}", "-x", "migrate_user=${var.db_iam_users.migrate}", "upgrade", "head"]
        env {
          name  = "CLOUDSQL_INSTANCE"
          value = var.instance_connection_name
        }
        env {
          name  = "DB_IAM_USER"
          value = var.db_iam_users.migrate
        }
        env {
          name  = "ENV"
          value = var.env
        }
      }
    }
  }
  lifecycle { ignore_changes = [template[0].template[0].containers[0].image, client, client_version] }
}
```
Alembic's `env.py` builds its engine with P1-03's `create_engine(settings)`, so the job uses the connector and IAM auth like the app. **Verify** that `uv` is available in the runtime image. If it isn't, use `python -m alembic`.

### `promote.yml` (behaviour)
```yaml
on:
  push:
    branches: [main]
    paths: ["releases/staging.yaml", "releases/prod.yaml"]
concurrency: {group: "promote-${{ github.sha }}", cancel-in-progress: false}
permissions: {contents: write, id-token: write, pull-requests: read}
# a first job detects which file changed and sets target=staging|prod; the deploy job uses
# environment: ${{ needs.detect.outputs.target }} and reads sha/type/reason from the file
```
Steps, in order:
0. **Approval check:** `check_release_approvals.py --target <target>` (§6). Nothing else runs if it fails.
1. **Check the source stage.**
   - Resolve the digests for `api:<sha>` and `web:<sha>` in the source repo (dev for staging, staging for prod).
   - Check that the source service is currently serving that digest; for prod, check that staging has served it for at least **24 h** (`type: normal`) or **1 h** (`type: hotfix`, which also needs a non-empty `reason`, shown to the approvers in the run summary). The serving time comes from the staging revision's creation time.
   - If either check fails, stop.
2. **Vulnerability gate:** `scripts/ci/vuln_gate.py --image <digest> --waivers security/vuln-waivers.yaml`. It fails on any CRITICAL finding without a valid waiver (and on HIGH as well for prod, Proposed).
3. **PHI gate** (prod only, when the repo variable `PHI_ENABLED=true`): `check_vendors.py --gate` must print `GATE OPEN`. Its output is saved as a workflow artifact for the audit trail.
4. **Copy** both images by digest: `crane copy <src>@<digest> <dst>/<svc>:<sha>`. The digest stays the same.
5. **Migrate**, **deploy**, **smoke test**, and **roll back on failure**, exactly as in dev.
6. **Record** the release:
   - create a GitHub Deployment (automatic with environments);
   - create a git tag `release-<target>-<YYYYMMDD>-<shortsha>`;
   - write the step summary with the digests, approvers, gate result and migration revision.

### `vuln-waivers.yaml`
```yaml
schema_version: 1
waivers:
  - id: CVE-2026-12345            # the scanner's finding ID
    package: openssl
    images: [api]
    severity: HIGH
    reason: "Not reachable: TLS terminates at the load balancer; fix pending in base image"
    approved_by: tech-lead
    expires: 2027-01-31            # vuln_gate.py fails once expired
```

### `terraform-apply.yml` and the PR plan
- **On PRs:** `pr.yml` gains a `terraform` job (paths filter `infra/**`):
  - `fmt -check`, `validate`, `tflint`, `checkov`;
  - `terraform plan -lock=false` for each changed root as `sa-tf-plan`;
  - the plan is posted as a PR comment (sensitive values are redacted by Terraform; the comment is truncated to 60 KB).
  - PRs from forks get no OIDC token, so they skip the plan.
- **Apply:** `terraform-apply.yml` (`org` stays manual by `gcp-org-admins`):
  - **dev:** `workflow_dispatch` with input `root` (`env/dev`), environment `tf-dev`;
  - **staging and prod:** triggered by a merged release PR on `releases/tf-staging.yaml` or `releases/tf-prod.yaml`, environment `tf-<env>`; step 0 is `check_release_approvals.py` (§6);
  - then: `plan -out=tfplan`, upload the plan summary, and apply **that** plan file. If the new plan differs from the plan posted on the original infra PR in resources to change, the job stops and asks for a new release PR (Proposed: compare the resource-change summary).

### `nightly.yml` (schedule `0 7 * * *` UTC)
| Job | Command | Fails when |
|---|---|---|
| `iam-audit` | `tools/iam_audit.py --project <each env> --json` | Any finding A1–A6 |
| `od-smoke` | `scripts/opendental/smoke_test.py` (P0-12) against test DB (B), serially | Any check fails or 429s persist |
| `od-integration` | `pytest -m opendental --maxfail=1 -p no:xdist` (serial; 1 request/second per key) | Any failure |
| `deps-audit` | `uv run pip-audit` (backend), `pnpm audit --prod --audit-level high` (frontend) | HIGH/CRITICAL without a waiver |
| `image-vulns` | `vuln_gate.py --report` for the digests serving in each env | New CRITICAL in a running image (opens an issue) |

Failures notify through GitHub (watchers of the repo) and open or update an issue labelled `nightly-failure`. P1-07 adds paging for prod-impacting jobs.

## 7. Implementation guide
1. **Read** P0-05, P0-06 (perimeters), P0-10 (`--gate`), P0-12 (`smoke_test.py`), P0-15 (`check_templates.py`), and P1-01 to P1-05 (outputs, SAs, Dockerfile, commands).
2. **WIF and ingress first, in dev:**
   1. apply `infra/ci/` for the pool, provider, `sa-ci-build` and `sa-deploy-dev`;
   2. add the `dai_dev` ingress rule in **dry-run** (P0-06 supports per-perimeter dry-run config);
   3. run a test workflow that logs in and runs `gcloud artifacts repositories list` and `gcloud run services list`;
   4. read the dry-run logs;
   5. enforce the rule.

   If identity-from-any-source ingress is not supported, switch to the Cloud Build private-pool fallback (§6) now, before writing the rest.
3. **Dockerfiles:**
   - add `APP_VERSION`;
   - write `frontend/Dockerfile`: multi-stage, `node:22-slim`, `next build` with `output: "standalone"`, run as a non-root user on port 8080;
   - make `/healthz` return the version.
4. **GitHub settings** (org on GitHub Team): create the environments with the `main` branch rule, the `prod-approvers` team (A, B, C), CODEOWNERS for `/releases/` and `/.github/`, "Require review from Code Owners" on `main`, the `releases/*.yaml` files, `check_release_approvals.py` with tests, and the repo variables. The variables are `WIF_PROVIDER`, `SA_*`, `DEV_PROJECT`, `STAGING_PROJECT`, `PROD_PROJECT`, `*_DOMAIN`, `MIGRATIONS_ENABLED` and `PHI_ENABLED`. They are not secrets, so there are no GitHub secrets for GCP.
5. **Scripts:** `run_migrations.sh`, `deploy_service.sh`, `smoke.sh`, `vuln_gate.py` (with tests for waiver expiry and severity rules).
6. **Workflows:** `deploy-dev.yml`, then `promote.yml`, `rollback.yml` (`workflow_dispatch`, input: env, and optional revision; default = previous revision; it can only move traffic back to a revision that already served in that environment, never deploy a new image, so it needs no release PR and can be run quickly in an incident; every run is announced in the step summary and reviewed afterwards), `terraform-apply.yml`, `nightly.yml`; extend `pr.yml`. Pin every third-party action by commit SHA, and let Dependabot propose updates.
7. **Terraform changes:**
   - add `traffic` to `ignore_changes` in `cloud_run_service`;
   - add the `migrate` job to each env root;
   - add the remaining CI SAs and their ingress rules for staging and prod.
8. **Rehearse:**
   - a normal merge reaches dev;
   - a deliberately broken `/readyz` image triggers the automatic rollback;
   - a failing migration stops the deploy with the old revision still serving;
   - promote to staging, then to prod with two approvals;
   - `rollback.yml` in staging.

   Record the results in `deploy.md`.
9. **Docs:** `docs/runbooks/deploy.md`: normal flow, promote, rollback, failed migration (expand/contract rules, below), waivers, rotating a pinned secret version (P1-05), and what to do if WIF breaks (`gcp-org-admins` deploy manually, audited).
10. **Notify:**
    - P1-07: revision-not-ready alert and nightly failures;
    - P5-01: how to add eval jobs;
    - P5-03: load-test hook;
    - P5-08: Binary Authorization later;
    - P6-01: `PHI_ENABLED` and the gate;
    - all developers: the expand/contract migration rule and "deploys use digests".

**Migration rule (expand/contract):** during a deploy, the old revision keeps serving until the new one is ready, and WebSocket sessions can last up to 60 minutes (ADR 0002). So every migration must work with **both** the old and new code:
- add columns as nullable or with defaults;
- add tables freely;
- never rename or drop in the same release as the code change. Drop in a later release, after no revision uses the column.

Reviewers check this, and the PR template gains a checkbox "Migration is backward compatible (expand/contract)".

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| Migration job fails | Workflow stops before the service update; the old revision keeps serving. Fix forward with a new migration (Alembic's transactional DDL rolled back the failed one). Never edit an applied migration. |
| New revision never becomes ready (startup probe fails) | Cloud Run keeps traffic on the old revision; `gcloud run services update` returns an error; the workflow fails. No manual rollback needed. |
| New revision is ready but the smoke test fails | `deploy_service.sh --rollback-all` moves 100% of traffic back to the remembered previous revisions; the workflow fails with the smoke reason. |
| Two merges land quickly | `concurrency: deploy-dev` queues them; each deploys in order. Promote uses one concurrency group per target. |
| Someone pushes an image tag by hand | Tags are immutable, and only CI SAs have `artifactregistry.writer`. Humans would need PAM `ops-write` (P1-05), which is audited. |
| A fork PR | No OIDC token; Terraform plan and image push are skipped; the other checks run. |
| WIF provider misconfigured or GitHub OIDC outage | Deploys fail at login. Emergency path: a `gcp-org-admins` member deploys the same digest with the same scripts from Cloud Shell, logged in the runbook and reviewed afterwards. |
| CRITICAL vulnerability found in a running prod image (nightly) | Issue opened; fix by rebuilding on a patched base and promoting; or add a waiver with a reason and expiry (tech lead approves). |
| PHI gate closed while `PHI_ENABLED=true` | Prod promotion fails at step 3; nothing is copied or deployed. |
| Terraform apply and a deploy run at the same time | Terraform ignores image and traffic, so they don't fight; state locking prevents two applies. |
| A deploy changes env vars or secrets | Not possible through deploy scripts (image only). Env and secret changes go through Terraform (P1-02/P1-05), then a deploy creates a new revision. |
| Open Dental test DB (B) is down at night | `od-smoke` fails and opens an issue; the deploy workflows don't depend on it. |

## 9. Security, HIPAA and PHI
- **No PHI flows through CI:**
  - tests use synthetic data;
  - the Open Dental test DB (B) holds fake patients only (P0-12);
  - logs from the smoke test print status codes only;
  - CI never reads prod data or prod secrets (`sa-deploy-prod` has no secret access and no database access).
- **Identity:**
  - no service-account keys anywhere (P0-06 blocks them);
  - GitHub gets short-lived tokens through WIF, bound to our repository's numeric IDs and to the GitHub environment;
  - prod deploy and Terraform apply need two human approvals, never self-approved.
- **Supply chain:**
  - third-party actions are pinned by SHA;
  - Dependabot is on;
  - images are immutable, deployed by digest, scanned, and gated on CRITICAL (and HIGH for prod) findings with expiring waivers;
  - "build once, promote" means prod runs exactly what staging ran.
- **Audit trail:**
  - the release PRs and their reviews record who requested and who approved each release; GitHub Deployments record what ran where;
  - Cloud Audit Logs record every `run.services.update` and `run.jobs.run` by `sa-deploy-*`;
  - release tags and step summaries hold the digests and the gate output;
  - P1-07 retains the Cloud side.
- **Perimeter:** CI enters each perimeter only through identity-scoped ingress rules for named SAs and services (or through the private-pool fallback).
- **Risks reduced:** P0-11 R06 (identity), R12 (no keys in GitHub). Supply-chain risk is partly reduced; Binary Authorization is in P5-08.

## 10. Testing
Unit tests (`scripts/ci/tests/`, run in `pr.yml`):
| # | Test | Expected |
|---|---|---|
| T1 | `vuln_gate.py` with a CRITICAL finding and no waiver | exit 1, names the finding ID |
| T2 | Same finding with a valid waiver; with an expired waiver | exit 0; exit 1 ("waiver expired") |
| T3 | HIGH finding: target staging vs prod | staging exit 0, prod exit 1 |
| T4 | `smoke.sh` against a local mock server: wrong version; `/readyz` 503; correct | exit 1; exit 1; exit 0 |
| T5 | `deploy_service.sh --rollback-all` with a mocked `gcloud` (PATH shim) | Calls `update-traffic … --to-revisions <prev>=100` for each service |

Rehearsals in dev and staging (§7 step 8), recorded in `deploy.md`:
| # | Scenario | Expected |
|---|---|---|
| R1 | Merge a trivial change to `main` | Dev serves the new SHA (`/healthz` version) within the workflow; no manual step |
| R2 | Image whose `/readyz` always fails | Workflow fails; old revision still serves 100% |
| R3 | Image that is ready but returns the wrong version (smoke fail) | Traffic rolled back automatically |
| R4 | Migration that raises | Workflow stops before service update; old revision serves |
| R5 | Release PR on `releases/staging.yaml`, approved by one other person, merged | Staging serves the dev digest |
| R6 | Prod release PR authored by A | A's own approval doesn't count; approvals by B and C pass and prod serves the staging digest; a run where the approvals come from C and a non-member fails at step 0 |
| R10 | Prod release PR for a SHA that has been in staging for 2 h, `type: normal`; then `type: hotfix` with a reason | Normal is refused (needs 24 h); hotfix proceeds after approvals |
| R11 | A PR that edits `promote.yml` or a release file without a `prod-approvers` review | Can't be merged (CODEOWNERS) |
| R12 | A workflow on a feature branch that uses `environment: prod` | Blocked by the environment branch rule; WIF never issues a `sa-deploy-prod` token |
| R7 | `PHI_ENABLED=true` with a closed gate (test in staging with a copy of the variable) | Promotion fails at the gate step |
| R8 | Login attempt from another repository's workflow using our provider path | Rejected by `attribute_condition` |
| R9 | `rollback.yml` in staging | Previous revision serves 100% |

## 11. Acceptance criteria
- [ ] WIF pool and provider exist in `ops`, restricted by repository owner and repository numeric IDs; CI SAs exist with exactly the §6 roles; GitHub holds no GCP keys or credentials (only non-secret variables)
- [ ] A merge to `main` builds `api` and `web` once, runs migrations and deploys both to dev by digest, and passes the smoke test with no manual step (R1)
- [ ] A failed readiness, failed smoke test or failed migration leaves the previous revision serving (R2–R4)
- [ ] Staging and prod are reachable only through release PRs and `promote.yml`; staging needs 1 approval, prod needs 2 from `prod-approvers` (A, B, C; at least one of A or B; never the author), enforced by CODEOWNERS and `check_release_approvals.py` (R11, R12); prod requires 24 h in staging, or 1 h for a hotfix with a reason; the promoted digest equals the tested one (R5, R6, R10)
- [ ] Prod promotion is blocked by unwaived CRITICAL/HIGH vulnerabilities and, when `PHI_ENABLED=true`, by a closed PHI gate (T1–T3, R7)
- [ ] `pr.yml` runs Terraform static checks and posts plans for changed roots; `terraform-apply.yml` applies staging and prod only from approved `releases/tf-<env>.yaml` PRs (2 `prod-approvers` for prod)
- [ ] `nightly.yml` runs the IAM audit, Open Dental smoke and integration tests (serial), dependency audits and the image report, and opens an issue on failure
- [ ] Third-party actions are pinned by SHA and Dependabot is enabled
- [ ] `docs/runbooks/deploy.md` documents deploy, promote, rollback, failed migration, waivers and the emergency path; the §7 step 10 issues are notified

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI (T1–T5); rehearsals R1–R12 recorded
- [ ] PR reviewed (HIPAA review if labelled `phi`): tech lead + compliance owner (identities, approvals, gates); no `phi` label (no PHI in CI)
- [ ] No PHI in logs: workflow logs contain no response bodies or data; test data is synthetic
- [ ] Docs / README updated: `deploy.md`, README "How we deploy", PR template checkbox for expand/contract migrations

## 13. Hand-off
| Task | Can rely on |
|---|---|
| All feature tasks | Merge to `main` deploys to dev; migrations run automatically; follow expand/contract; `/healthz` shows the running SHA |
| P1-07 Logging/monitoring | Deploy identities (`sa-deploy-*`) in audit logs; revision readiness failures to alert on; `nightly-failure` issues |
| P5-01 Evals | Add eval jobs to `pr.yml` (fast set) and `nightly.yml` (full set) following the job patterns here |
| P5-03 Load tests | A manual workflow on staging can reuse the auth and smoke steps |
| P5-08 Security | Pinned actions, waivers file, vuln gate; Binary Authorization to add later |
| P6-01 Pilot onboarding | `PHI_ENABLED` variable and the PHI gate step in prod promotion |
| P1-02 owners | `traffic` added to the module's `ignore_changes`; `migrate` job in each env root |

## 14. Open questions
| Question | Owner | Needed by |
|---|---|---|
| Does VPC-SC accept identity-scoped ingress from any source for Artifact Registry and Cloud Run? Decided approach: try it first in dev (dry-run, §7 step 2); if it fails, use the Cloud Build private-pool fallback. Only the outcome is open. | Tech lead | Step 2 |

## 15. References
- GitHub Actions OIDC: https://docs.github.com/actions/security-for-github-actions/security-hardening-your-deployments/about-security-hardening-with-openid-connect
- GitHub environments: https://docs.github.com/actions/managing-workflow-runs-and-deployments/managing-deployments/managing-environments-for-deployment
- Google WIF with deployment pipelines: https://docs.cloud.google.com/iam/docs/workload-identity-federation-with-deployment-pipelines
- `google-github-actions/auth`: https://github.com/google-github-actions/auth
- VPC-SC ingress and egress rules: https://docs.cloud.google.com/vpc-service-controls/docs/ingress-egress-rules
- Cloud Build private pools: https://docs.cloud.google.com/build/docs/private-pools/private-pools-overview
- Cloud Run rollbacks and traffic: https://docs.cloud.google.com/run/docs/rollouts-rollbacks-traffic-migration
- Cloud Run jobs: https://docs.cloud.google.com/run/docs/create-jobs
- Artifact Analysis (vulnerability scanning): https://docs.cloud.google.com/artifact-analysis/docs/container-scanning-overview
- crane: https://github.com/google/go-containerregistry/tree/main/cmd/crane
- Next.js standalone output: https://nextjs.org/docs/app/api-reference/config/next-config-js/output
- Related tasks: P0-05, P0-06, P0-10, P0-11, P0-12, P0-14, P0-15, P1-01, P1-02, P1-03, P1-05, P1-07, P5-01, P5-03, P5-08, P5-11, P6-01
