---
id: P1-13
title: Staff auth (Identity Platform, MFA, RBAC), patient session tokens, rate limiting and internal caller auth
milestone: P1
epic: E1.2
size: L
labels: area:backend, area:security, area:infra, type:feature
depends_on: P1-01, P1-03, P1-05, P1-07
status: approved
---

# P1-13: Staff auth (Identity Platform, MFA, RBAC), patient session tokens, rate limiting and internal caller auth

## 1. Summary
This task builds every way a caller proves who it is to the `api` service, and what it may then do. It also absorbs **P1-14 (Patient session tokens, idle timeout and rate limiting)**.

1. **Staff authentication.** Clinic staff log in to the admin console through **Google Identity Platform**:
   - email and password, with **TOTP MFA required** (an authenticator app), invite-only;
   - the backend checks the second factor itself and then issues its own server-side session in Redis;
   - the session cookie is `HttpOnly`, `Secure`, `SameSite=Strict`;
   - sessions end after **15 min idle** and after **12 h** at most;
   - staff management endpoints: invite, change role, deactivate. Deactivation ends sessions at once.
2. **RBAC.** Roles Admin, Front Desk, Dentist and Read-only, with a fixed role-to-permission matrix.
   - Every console route declares its permission through `require(...)`; there is no default access.
   - Every query is scoped to the staff member's clinic.
3. **Patient sessions.** Widget users are anonymous.
   - `POST /v1/sessions` returns a **signed, short-lived token**. It is held in the widget's memory, **not a cookie**, because the widget runs in an iframe on the clinic's site.
   - The server-side idle timeout is 15 min; the maximum life is 2 h.
   - Each token is bound to one session and one clinic.
   - The same token authenticates the WebSocket (first message).
   - The session carries the verified PatNum, which tools must use (P2).
4. **Rate limiting.** Redis token buckets per IP, per session, per clinic and for identity verification attempts. Over the limit, the API returns 429 with `Retry-After`, plus a log event and an audit entry.
5. **Internal caller auth.** `/internal/*` routes accept only Google OIDC tokens from `sa-scheduler` and `sa-tasks-invoker` (P1-02), with audience, issuer and email checks.

Done means:
- staff can't get a session without MFA;
- every role/permission pair is tested;
- patient tokens expire as specified and can't reach another session's data;
- limits return 429;
- `/internal/*` rejects anything but the two service accounts.

## 2. Why this matters
- **The admin console shows PHI** (callback cases with names, phone numbers and summaries). P0-11 rates these risks:
  - **R04** broken access control (IDOR): High;
  - **R05** phished staff account: High;
  - **R32** a departed staff member keeps access: High.

  MFA, server-side sessions that can be revoked instantly, automatic logoff and a tested permission matrix are the controls.
- **The widget is public.** Anyone on the internet can open a session, so short-lived tokens, per-session scoping and rate limits stop abuse (cost, scraping, brute-forcing identity checks; plan §11 "abuse of public widget").
- **Plan §4.2:** "tools can only act on the patient verified in *this* session". The session principal defined here is how the tool gateway knows which patient that is.
- **HIPAA Security Rule:**
  - §164.312(a)(2)(i) unique user identification;
  - §164.312(a)(2)(iii) automatic logoff;
  - §164.312(d) person or entity authentication.

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P1, Core Platform & Open Dental Adapter**.
- **What already exists:**
  - **P1-01:**
    - `create_app`, `AppError` with the error shape `{"error":{code,message,request_id}}`;
    - `CORS_ALLOWED_ORIGINS` (exact origins);
    - one Next.js app with `/widget` and `/admin` (DECISIONS #85).
  - **P1-02:**
    - hosts `api.<domain>` and `app.<domain>` behind the LB;
    - Cloud Armor rate limit of 300 requests/min per IP;
    - `/internal/*` blocked at the edge;
    - Scheduler and Tasks call the `api` `run.app` URL with OIDC as `sa-scheduler` / `sa-tasks-invoker`.
  - **P1-03:** tables `staff_users` (`idp_uid`, `role`, `mfa_enrolled`, `active`, `clinic_id`) and `sessions` (`status`, `verified_patnum`, `channel`); `ClinicScopedRepository`.
  - **P1-05:**
    - secret `patient-session-signing-key` → `PATIENT_SESSION_SIGNING_KEY`;
    - `sa-api` roles (this task adds the Identity Platform role);
    - `admin-email-sender`.
  - **P1-07:**
    - `audit()` / `audit_now()` and actions `auth.login`, `auth.login_failed`, `auth.mfa_failed`, `auth.logout`, `staff.create`, `staff.role_change`, `staff.deactivate`, `security.rate_limited`;
    - `client_ip()`; `Actor`.
- **Identity Platform** (Google Cloud's customer identity service, the same engine as Firebase Authentication):
  - stores staff accounts (email, password hash, MFA enrollment) and issues **ID tokens** (JWTs, about 1 h).
  - **Facts to verify:**
    - that Identity Platform is on the Google Cloud HIPAA covered-products list (it holds staff identities, not PHI, but it is part of the access-control system);
    - TOTP MFA support and the project setting that makes MFA mandatory;
    - the ID-token claim `firebase.sign_in_second_factor` set to `"totp"` after an MFA sign-in;
    - the password policy options;
    - built-in brute-force protection on password sign-in;
    - the Admin SDK calls `create_user`, `update_user(disabled=True)`, `revoke_refresh_tokens`, `generate_password_reset_link` and `verify_id_token(check_revoked=True)`;
    - the IAM role that lets `sa-api` manage users;
    - whether `identitytoolkit.googleapis.com` and `securetoken.googleapis.com` can be inside the VPC-SC perimeter while browsers call them directly (§6 "Perimeter note").
- **Why patient tokens are not cookies:** the widget page (`app.<domain>/widget`) is embedded as an iframe on the clinic's own website. Browsers treat cookies inside a cross-site iframe as third-party cookies, and Safari and others block them. Plan §6 says "secure cookies". We keep cookies for the staff console, which is a first-party site, and use an in-memory bearer token for the widget (decision logged).

## 4. Scope
**In scope**
- **Terraform:**
  - Identity Platform config: email/password sign-in, TOTP MFA mandatory, password policy, authorized domains `app.<domain>`, no self sign-up;
  - APIs added to `allowed_services.yaml`;
  - the IAM role for `sa-api`;
  - the perimeter decision for the Identity Platform APIs.
- **Backend `app/auth/`:**
  - `staff.py`: session create, refresh, delete; the `StaffPrincipal` dependency;
  - `rbac.py`: `Role`, `Permission`, matrix, `require()`;
  - `patient.py`: token issue and verify; the `PatientPrincipal` dependency; the WebSocket auth helper;
  - `internal.py`: OIDC verification for `/internal/*`;
  - `ratelimit.py`: Redis token bucket (Lua), the limits table, the `rate_limit()` dependency;
  - `csrf.py`.
- **Endpoints:**
  - `/v1/auth/session` (POST, DELETE), `/v1/auth/me` (P4-09 addition, DECISIONS #262: the response also carries `permissions: Permission[]` and a fresh `csrf_token`, and the call refreshes the idle timer);
  - `/v1/admin/staff` (GET, POST), `/v1/admin/staff/{id}` (PATCH);
  - `/v1/sessions` (POST), `/v1/sessions/{id}` (DELETE).
- **Frontend** (minimal, in `frontend/app/admin/`):
  - login page using the Identity Platform JS SDK;
  - TOTP enrollment on first login;
  - session exchange; idle-logout timer UI; logout;
  - the `apiFetch` wrapper with credentials and the CSRF header.
- **`Settings` additions** and the CORS update (`app.<domain>` with credentials).
- **Dev seed:** one Admin user in dev Identity Platform for the test clinic, created by a script, with credentials in the dev password manager (never in the repo).
- **Tests** T1–T20 (§10).

**Out of scope** (and which task covers it)
- Console shell and screens beyond the minimal login/logout page here (cases, staff management UI, config) → P4-09, P4-11, P4-13; P4-09 restyles and wraps the login page built here
- reCAPTCHA / bot protection on session creation and staff login → P2-25 (hooks are defined here)
- Widget handshake UI, session resume across voice/text, Redis conversation state → P2-25, P2-01
- Identity verification logic (which identifiers, matching) → P2-12; this task only provides the attempt limiter
- SSO with the clinic's Microsoft 365 or Google Workspace → later (Identity Platform supports SAML/OIDC providers)
- Periodic access reviews → P5-14; authorization testing and OWASP review → P5-08

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P1-01 (approved) | App factory, errors, CORS settings | Build on the skeleton. |
| P1-03 (approved) | `staff_users`, `sessions`, repository base | Tests use the CI Postgres with P1-03 migrations. |
| P1-05 (approved) | `PATIENT_SESSION_SIGNING_KEY`, `sa-api` roles | Local: random key in `.env`; dev: the secret. |
| P1-07 (approved) | `audit()`, `client_ip()`, logging | Use the specs' signatures; tests run with the real modules once merged. |
| Identity Platform in dev | A project with Identity Platform enabled | Unit tests mock `verify_id_token`. For local manual testing use the **Firebase Auth emulator** (`firebase emulators:start --only auth`; **Verify** that it supports TOTP MFA; if not, test MFA in dev). |
| P2-22 email sender | Sending invite emails | Until it exists, `POST /v1/admin/staff` returns the invite link **only in `ENV=dev`/`local`** in the response, never logged; staging/prod require the sender. |

## 6. Interface contract

### Identity Platform configuration (Terraform; **Verify** resource and field names)
```hcl
resource "google_identity_platform_config" "default" {
  project                    = var.project_id
  autodelete_anonymous_users = true
  sign_in {
    allow_duplicate_emails = false
    email {
      enabled           = true
      password_required = true
    }
  }
  mfa {
    state             = "MANDATORY"                 # Verify; the backend also enforces it (below)
    enabled_providers = ["PHONE_SMS"]               # placeholder - see note: TOTP is configured via provider_configs
    provider_configs {
      state = "ENABLED"
      totp_provider_config { adjacent_intervals = 1 }
    }
  }
  authorized_domains = ["app.${var.domain}"]
  client {
    permissions {
      disabled_user_signup   = true                 # invite-only
      disabled_user_deletion = true
    }
  }
}
```
Note: SMS MFA must **not** be enabled (SIM-swap risk, and phone numbers would be stored). If the provider requires `enabled_providers`, set it to TOTP only. **Verify** the exact Terraform shape; it is the intent that matters: **TOTP only, mandatory**.

- **Password policy** (Proposed): at least 12 characters, with a breached-password check if available. **Verify** the policy options.
- **IAM:** `sa-api` gets the Identity Platform user-admin role on the project (**Verify** the name, e.g. `roles/identityplatform.admin` or `roles/firebaseauth.admin`). Add it to the P1-05 matrix.

**Perimeter note:** browsers call `identitytoolkit.googleapis.com` and `securetoken.googleapis.com` directly to sign in. If those services are restricted by the `dai_prod` perimeter, browser sign-in fails. Proposed: keep both **out of the perimeter's restricted services**. They hold staff credentials, not PHI, and are protected by MFA, authorized domains and invite-only sign-up. `sa-api` still calls them through the restricted VIP if supported, or else through the FQDN egress allow-list. **Verify** in dev, and record the outcome in `docs/architecture/network.md`.

### Staff login flow
```text
Browser (app.<domain>/admin/login)            Identity Platform                 api.<domain>
  email + password  ───────────────────────▶  check, MFA required
  TOTP code         ───────────────────────▶  ID token (sign_in_second_factor="totp")
  POST /v1/auth/session  Authorization: Bearer <ID token>  ───────────────────▶ verify, map, create session
                         ◀── 200 {staff, csrf_token}  Set-Cookie: __Host-dai_staff=<opaque id>
  signOut() from the Identity Platform SDK (no lingering client-side IdP session)
  later: fetch(api, {credentials:"include", headers:{"X-CSRF-Token": csrf_token}})
```
First login: the SDK shows TOTP enrollment (QR code) before the first MFA sign-in. On the first successful session, `staff_users.mfa_enrolled` is set to true.

`POST /v1/auth/session` checks, in order. Any failure returns **401** and writes `audit_now(auth.login_failed | auth.mfa_failed, reason_code=…)`:
1. Verify the ID token with `verify_id_token(token, check_revoked=True)`. It must be signed for our project, unexpired, with `auth_time` no older than 5 min. Failure → `invalid_token`.
2. `firebase.sign_in_second_factor == "totp"`. Failure → `mfa_required`, audited as `auth.mfa_failed`.
3. A `staff_users` row with this `idp_uid` exists and is `active`. Failure → `account_disabled`, audited as `auth.login_failed`.
4. Rate limit `staff_login` per IP (§ Rate limits).

On success:
- create a session and write `audit(auth.login)`;
- update `last_login_at` and `mfa_enrolled`;
- return the body `{"staff":{"id","display_name","role","clinic_id"},"csrf_token":"…","idle_timeout_s":900,"expires_at":"…"}`.

### Staff session (Redis)
```python
# key: f"staff_sess:{sha256(session_id).hexdigest()}"   (the raw ID is only in the cookie)
@dataclass(frozen=True)
class StaffSessionData:
    staff_id: uuid.UUID
    clinic_id: uuid.UUID
    role: Role
    csrf_token_hash: str        # sha256 of the CSRF token
    created_at: datetime
    expires_at: datetime        # created_at + STAFF_SESSION_MAX_S (12 h)
# Redis TTL = STAFF_SESSION_IDLE_S (900 s), reset on every authenticated request (sliding idle timeout).
# Index: set f"staff_sessions:{staff_id}" -> session key hashes, for revoke-all.
```
- **Cookie:** `__Host-dai_staff=<43-char URL-safe random>`, with `Secure`, `HttpOnly`, `SameSite=Strict`, `Path=/`, no `Domain` attribute, and no `Max-Age`. It is a browser-session cookie; the server enforces lifetimes.
- **CSRF:**
  - every state-changing staff request (`POST`, `PATCH`, `PUT`, `DELETE`) must send `X-CSRF-Token`, whose SHA-256 must match `csrf_token_hash`;
  - `SameSite=Strict` is the first layer, the token the second;
  - mismatch → 403 `csrf_failed`.
- **CORS:** `CORS_ALLOWED_ORIGINS=["https://app.<domain>"]` with `allow_credentials=True`, and allowed headers `Content-Type`, `X-CSRF-Token`, `X-Request-ID`.
- **Revocation:** `revoke_staff_sessions(staff_id)` deletes every key in the index. It is called on:
  - deactivation;
  - a role change;
  - logout-everywhere;
  - the Identity Platform `revoke_refresh_tokens(uid)` call.
- **Idle UI:** the console shows a warning at 13 minutes and logs out at 15. The server is authoritative; the UI is a convenience.

### RBAC (`app/auth/rbac.py`)
```python
class Role(StrEnum):
    ADMIN = "ADMIN"
    FRONT_DESK = "FRONT_DESK"
    DENTIST = "DENTIST"
    READ_ONLY = "READ_ONLY"

class Permission(StrEnum):
    DASHBOARD_READ = "dashboard:read"
    CALLBACK_READ = "callback:read"                  # list + detail, contact masked
    CALLBACK_READ_CONTACT = "callback:read_contact"  # full contact name/phone
    CALLBACK_UPDATE = "callback:update"              # status, assignee
    CALLBACK_REOPEN = "callback:reopen"            # Addition (P4-13a, DECISIONS #266): ADMIN only; reopen a RESOLVED case
    ACTIVITY_READ = "activity:read"                  # AI activity log (sessions, outcomes)
    CONFIG_READ = "config:read"
    CONFIG_WRITE = "config:write"                    # incl. scheduling.booking_horizon_days (DECISIONS #86)
    PILOT_KILL = "pilot:kill"                     # Addition (P6-01, DECISIONS #280): ADMIN + ops role; switch a pilot channel OFF (ON needs two people)
    KPI_READ = "kpi:read"                         # Addition (P6-02, DECISIONS #281): ADMIN; /admin/insights
    TRANSCRIPT_READ = "transcript:read"           # Addition (P6-04, DECISIONS #282): new role REVIEWER only (two named team members); audited views
    CONFIG_REQUEST = "config:request"              # Addition (P4-11, DECISIONS #264): ADMIN, DENTIST; submit config change requests (e.g. emergency rules)
    STAFF_MANAGE = "staff:manage"
    AUDIT_READ = "audit:read"
    CONSENT_READ = "consent:read"                   # consent screen (added by P4-02; ADMIN, FRONT_DESK, READ_ONLY)
    CONSENT_WRITE = "consent:write"                 # revoke / staff grant (added by P4-02; ADMIN, FRONT_DESK)
    MESSAGE_READ = "message:read"                   # failed-messages list (added by P4-01; ADMIN, FRONT_DESK)
    MESSAGE_ACK = "message:ack"                     # acknowledge a failed message (added by P4-01; ADMIN, FRONT_DESK)

ROLE_PERMISSIONS: Final[Mapping[Role, frozenset[Permission]]] = {
    Role.ADMIN: frozenset(Permission),
    Role.FRONT_DESK: frozenset({Permission.DASHBOARD_READ, Permission.CALLBACK_READ, Permission.CALLBACK_READ_CONTACT,
                                Permission.CALLBACK_UPDATE, Permission.ACTIVITY_READ, Permission.CONFIG_READ,
                                Permission.MESSAGE_READ, Permission.MESSAGE_ACK,     # MESSAGE_*: P4-01
                                Permission.CONSENT_READ, Permission.CONSENT_WRITE}), # CONSENT_*: P4-02
    Role.DENTIST: frozenset({Permission.DASHBOARD_READ, Permission.CALLBACK_READ, Permission.CALLBACK_READ_CONTACT,
                             Permission.CALLBACK_UPDATE}),
    Role.READ_ONLY: frozenset({Permission.DASHBOARD_READ, Permission.CALLBACK_READ,
                               Permission.CONSENT_READ}),   # CONSENT_READ: P4-02
}

@dataclass(frozen=True)
class StaffPrincipal:
    staff_id: uuid.UUID
    clinic_id: uuid.UUID
    role: Role
    permissions: frozenset[Permission]
    def actor(self, ip: str | None) -> Actor: ...   # P1-07 Actor(type=STAFF, id=str(staff_id), ip=ip)

def require(*perms: Permission) -> Callable[..., Awaitable[StaffPrincipal]]:
    """FastAPI dependency.

    401 if no valid session; 403 `forbidden` (and audit_now security.access_denied) if any permission is missing.
    """

# usage
@router.patch("/v1/admin/callbacks/{callback_id}")
async def update_callback(callback_id: uuid.UUID, body: CallbackUpdate,
                          staff: StaffPrincipal = Depends(require(Permission.CALLBACK_UPDATE))) -> CallbackOut: ...
```
Rules:
- **Default deny:** test T10 walks `app.routes`. Every route under `/v1/admin/` and `/v1/auth/me` must depend on `require(...)` or `current_staff`, or the test fails.
- **Object-level checks:** repositories are created with `staff.clinic_id` (`ClinicScopedRepository`, P1-03). An ID from another clinic returns **404**, never 403, so existence is not revealed.
- **Masking for READ_ONLY:** the response serializer masks contact fields when `CALLBACK_READ_CONTACT` is missing. Phone `+1 •••-•••-4567`; name: first initial only.
- **Matrix changes** are code changes reviewed by the compliance owner (CODEOWNERS on `rbac.py`). `docs/security/rbac.md` mirrors the table.
- New audit action added to P1-07's enum: `security.access_denied`.

### Staff management endpoints (ADMIN, `STAFF_MANAGE`)
| Method and path | Body | Result | Audit |
|---|---|---|---|
| `GET /v1/admin/staff` | — | `[{id, email, display_name, role, active, mfa_enrolled, last_login_at}]` (own clinic) | — |
| `POST /v1/admin/staff` | `{email, display_name, role}` | 201 `{id, invite_sent: true}` → creates the Identity Platform user (disabled until the password is set? **Verify**; otherwise enabled with no password) and the `staff_users` row; sends a password-set link via `EmailSender` (P2-22) | `staff.create` |
| `PATCH /v1/admin/staff/{id}` | `{role?}` or `{active: false}` | 200 staff → role change revokes sessions; deactivation sets `active=false`, disables the IdP user, revokes refresh tokens and sessions | `staff.role_change` / `staff.deactivate` |

Guards:
- an admin can't deactivate or demote themselves;
- the last active ADMIN of a clinic can't be demoted or deactivated (409 `last_admin`);
- emails are unique per clinic (P1-03).

### Patient session token (`app/auth/patient.py`)
`POST /v1/sessions`:
- request: `{"clinic_slug": "pilot-clinic", "channel": "TEXT" | "VOICE"}`;
- response 201: `{"session_id": "<uuid>", "token": "<jwt>", "idle_timeout_s": 900, "expires_at": "<RFC3339>"}`.

Steps:
1. Rate limit `session_create` per IP.
2. The bot-protection hook `verify_bot_token(request)` (no-op until P2-25; P2-25 adds `bot_token` and `client_reason` to the request body and returns 403 `bot_suspected` on `block`).
3. Find the clinic by slug (`ACTIVE` only; else 404).
4. Insert a `sessions` row (`ACTIVE`).
5. Create Redis `psess:{session_id}` = `{clinic_id, channel, verify_attempts: 0, verified_patnum: null}` with TTL `PATIENT_SESSION_IDLE_S`.
6. Sign the token.

Token (PyJWT, HS256, key `PATIENT_SESSION_SIGNING_KEY`):
```json
{"iss":"dai-api","aud":"dai-widget","sid":"<session uuid>","cid":"<clinic uuid>","iat":1764000000,"exp":1764007200,"kid":"k1"}
```
- `exp` = iat + `PATIENT_SESSION_MAX_S` (7200 s). There is no PHI in the token, and it never carries the PatNum.
- **Key rotation:** `kid` selects the key. `PATIENT_SESSION_SIGNING_KEY_PREVIOUS` (optional) is accepted for verification only, so rotating the key (P1-05) doesn't end live sessions abruptly.

**Use:**
- **HTTP:** `Authorization: Bearer <token>`. The token is never put in a URL, a query string or a cookie.
- **WebSocket** (P2/P3 implement; contract fixed here):
  1. connect to `wss://api.<domain>/v1/sessions/{session_id}/ws`;
  2. the **first message** within 5 s must be `{"type":"auth","token":"<token>"}`;
  3. otherwise close with code **4401** (`not_authenticated`); an expired session closes with **4408** (`session_expired`).
  4. The server re-checks the Redis idle key every 60 s, and on each client message.
- **Widget storage:** in memory plus `sessionStorage` (scoped to the iframe's origin and tab), so a page reload within the tab can resume. Never in `localStorage`.

`PatientPrincipal` dependency (and the WebSocket equivalent):
```python
@dataclass(frozen=True)
class PatientPrincipal:
    session_id: uuid.UUID
    clinic_id: uuid.UUID
    channel: Literal["TEXT", "VOICE"]
    verified_patnum: int | None       # the ACTIVE patient's PatNum; set only by P2-12 via mark_verified() / switch_active()
    household: tuple[int, ...] = ()   # every PatNum verified or registered in this session, max 4 (DECISIONS #185)
    def actor(self, ip: str | None) -> Actor: ...   # Actor(type=PATIENT_SESSION, id=str(session_id), ip=ip)

async def current_patient(request: Request, redis: Redis = Depends(get_redis)) -> PatientPrincipal:
    """Checks, in order:

    1. signature, iss, aud, exp (401 invalid_token);
    2. Redis psess key exists (401 session_expired);
    3. path {session_id}, if present, equals sid (404).

    Then resets the idle TTL.
    """

async def mark_verified(session_id: uuid.UUID, patnum: int) -> None: ...      # Redis + sessions.verified_patnum
async def record_verify_attempt(session_id: uuid.UUID) -> int: ...            # returns attempts so far (per session, all persons)
async def start_new_person(session_id: uuid.UUID) -> None: ...                # active patient becomes "none" (verified_patnum=None); household kept
async def switch_active(session_id: uuid.UUID, patnum: int) -> None: ...      # only to a PatNum already in household, else ValueError
async def end_session(session_id: uuid.UUID, reason: EndReason) -> None: ...   # deletes Redis key, updates row
```
Rules:
- **Scoping:** tools use `principal.verified_patnum` and never a PatNum from the request or from the LLM (P2-08 tool gateway). Without verification, `verified_patnum` is `None`, and tools that need a patient refuse.
- **Verification attempts:**
  - after **3 failed** attempts, `record_verify_attempt` makes the session `verification_locked`;
  - further attempts return 403 `verification_locked`, and the conversation offers a callback (P2-12 owns the wording);
  - audit `patient.verify_failed` for each failure, and `security.rate_limited` once on lock.
- **Expiry:** when the idle key is gone, the next call gets 401 `session_expired`. The widget then starts a new session, and the patient must verify again. The `sessions` row is marked `EXPIRED` by that call, or by P2-01's cleanup.
- `DELETE /v1/sessions/{id}`: the patient ends the session, the API returns 204, and the Redis key is deleted.

### Rate limits (`app/auth/ratelimit.py`; Proposed values, tuned in P5-03)
A token bucket in Redis, atomic through one Lua script. Key `rl:{name}:{subject}`, with a TTL of 2 × the window.

| Name | Subject | Limit | Over limit |
|---|---|---|---|
| `session_create` | client IP | 10 / min (burst 10) | 429 `rate_limited` |
| `patient_message` | session ID | 30 / min (burst 10) | 429, or a WebSocket error event `rate_limited` (connection kept) |
| `patient_message_strict` | session ID (sessions flagged `bot_suspect` by P2-25) | 10 / min (burst 5) | Same as `patient_message`; added by P2-25 (DECISIONS #210) |
| `voice_concurrent` | client IP | 3 open voice WebSockets (a counter with TTL, decremented on close) | WebSocket close 4429. **Added by P3-02 (DECISIONS #226):** counted at the `voice_start` message (protocol v2), decremented on `voice_stop` or close; over the limit the server sends `voice_stopped limit` and keeps the socket open for text instead of closing |
| `clinic_messages` | clinic ID | 600 / min across all sessions (cost guard) | 429; alert if sustained (P1-07 log metric) |
| `staff_login` | client IP | 20 / 15 min | 429 |
| `staff_api` | staff ID | 300 / min | 429 |
| `verify_attempts` | session ID | 3 failures per session (not time-based) | 403 `verification_locked` |

```python
def rate_limit(name: LimitName, subject: Callable[[Request], str]) -> Callable[..., Awaitable[None]]: ...
async def check_limit(redis: Redis, name: LimitName, subject: str) -> LimitResult: ...   # LimitResult(allowed, retry_after_s)
```
- **429 response:** `{"error":{"code":"rate_limited","message":"Too many requests. Please wait and try again.","request_id":…}}` with header `Retry-After: <s>`.
- **Logging:** `security.rate_limited` (with `limit` = name), plus `audit_now(security.rate_limited)` **once per subject per window**, so an attacker can't flood the audit table.
- **Redis down:** limits **fail open** for patient chat, so the clinic's patients aren't blocked by a cache outage; the outage itself alerts (A16). They **fail closed** for `staff_login` and `verify_attempts`, so brute-force protection never silently disappears.
- **Staff password brute force:** password checks happen inside Identity Platform, not in our API. We rely on its built-in protection (**Verify** what it does and whether a lockout can be configured; record it in `docs/security/auth.md`). Optional reCAPTCHA on the login page comes with P2-25. Our `staff_login` limit covers the session-exchange step.

### Internal caller auth (`app/auth/internal.py`)
```python
@dataclass(frozen=True)
class InternalCaller:
    email: str                   # sa-scheduler@… or sa-tasks-invoker@…
    queue_or_job: str | None     # from X-CloudTasks-QueueName / X-CloudScheduler-JobName headers (informational only)

async def require_internal_caller(request: Request) -> InternalCaller:
    """Validates the `Authorization: Bearer <Google ID token>`.

    Uses google.oauth2.id_token.verify_oauth2_token(token, google.auth.transport.requests.Request(),
    audience=settings.INTERNAL_AUDIENCE). Then checks:
    - iss in {"https://accounts.google.com", "accounts.google.com"};
    - email_verified is true;
    - email in settings.INTERNAL_CALLER_EMAILS.
    Any failure: 401, and log internal.auth_failed (no token content).
    """
```
Google's public certificates are cached by the library (**Verify** the caching behaviour, or wrap it with a 1 h cache). The router for `/internal/*` has this dependency at router level, so no internal route can exist without it (test T18).

### Settings additions (extends P1-01)
```python
IDP_PROJECT_ID: str | None = None                         # Identity Platform project (= the env project)
STAFF_SESSION_IDLE_S: int = Field(default=900, ge=300, le=1800)
STAFF_SESSION_MAX_S: int = Field(default=43200, ge=3600, le=86400)
PATIENT_SESSION_IDLE_S: int = Field(default=900, ge=300, le=3600)
PATIENT_SESSION_MAX_S: int = Field(default=7200, ge=900, le=14400)
PATIENT_SESSION_SIGNING_KEY_PREVIOUS: SecretStr | None = None
CONSOLE_ORIGIN: str                                       # "https://app.<domain>"; also the only CORS origin with credentials
INTERNAL_AUDIENCE: str                                    # the api run.app URL (P1-02)
INTERNAL_CALLER_EMAILS: list[str]                         # [sa-scheduler@…, sa-tasks-invoker@…]
RATE_LIMIT_OVERRIDES: dict[str, str] = {}                 # e.g. {"patient_message": "40/min"} for tuning without code changes
```

### Error codes added to the `AppError` hierarchy
| Code | HTTP | When |
|---|---|---|
| `not_authenticated` | 401 | No cookie/token |
| `invalid_token` | 401 | Bad signature, audience or expiry |
| `session_expired` | 401 | Idle or absolute timeout |
| `mfa_required` | 401 | ID token without a TOTP second factor |
| `account_disabled` | 401 | Staff not found or inactive |
| `forbidden` | 403 | Missing permission |
| `csrf_failed` | 403 | Missing or wrong `X-CSRF-Token` |
| `verification_locked` | 403 | 3 failed identity checks in this session |
| `last_admin` | 409 | Would remove the clinic's last admin |
| `rate_limited` | 429 | Any limit |

## 7. Implementation guide
1. **Read** P1-01 (errors, CORS), P1-03 (`staff_users`, `sessions`), P1-05 (secrets, SA roles), P1-07 (`audit`, `client_ip`), P1-02 (OIDC callers), P0-11 R04, R05 and R32, and plan §4.2 and §6.
2. **Verify** the Identity Platform facts in §3 (HIPAA list, TOTP, mandatory MFA, second-factor claim, brute-force protection, roles, perimeter behaviour). Record them in `docs/security/auth.md`.
3. **Terraform:**
   - Identity Platform config;
   - APIs in `allowed_services.yaml` (P0-06 PR);
   - the `sa-api` role (P1-05 module);
   - the perimeter decision.

   Apply in dev.
4. **RBAC module** first, with T8–T10, so other tasks can import `require()` early.
5. **Staff session:**
   - write `POST/DELETE /v1/auth/session`, `/v1/auth/me`, the CSRF check and revocation;
   - unit-test with a mocked `verify_id_token` (T1–T7);
   - run the manual dev test with a real TOTP app.
6. **Staff management endpoints** with the guards (T11, T12).
7. **Patient sessions:** token, `current_patient`, the WebSocket helper, attempts, expiry (T13–T16).
8. **Rate limiter:** the Lua script, the limits table, overrides, fail-open/fail-closed behaviour (T17, T19).
9. **Internal caller auth** and the router-level dependency (T18). Test it in dev with `gcloud scheduler jobs run unsent-email-check` (P1-02 N8).
10. **Frontend:** login, TOTP enrollment, session exchange, `apiFetch`, idle timer, logout. **Manual check** in Safari, Chrome and Firefox. Check the widget token flow inside an iframe on a test page served from a different origin (Safari ITP).
11. **Dev seed script** `backend/tools/create_admin.py --clinic pilot-test-db --email …` (dev and staging only; refuses `ENV=prod`).
12. **Docs:** `docs/security/auth.md` (flows, timeouts, verified facts) and `docs/security/rbac.md` (matrix).
13. **Notify:**
    - P2-01: `PatientPrincipal`, `end_session`, `psess:` key;
    - P2-12: `mark_verified`, `record_verify_attempt`, `verification_locked`;
    - P2-25: token flow, WebSocket auth message, bot hook;
    - P2-22: `EmailSender` for invites;
    - P3 tasks: WebSocket close codes;
    - P4-09, P4-11, P4-13: `require()`, permissions, masking;
    - P4-04 and P2-22: `require_internal_caller`;
    - P5-08: authorization test list;
    - P1-07: new action `security.access_denied`.

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| Staff signs in with password but skips MFA (e.g. old SDK flow) | ID token lacks `sign_in_second_factor` → 401 `mfa_required`, audited `auth.mfa_failed`. |
| Staff member deactivated while logged in | `PATCH … {active:false}` revokes sessions → their next request gets 401 `session_expired`; IdP refresh tokens revoked, user disabled. |
| Role changed from ADMIN to FRONT_DESK while logged in | Sessions revoked → re-login gives the new role. |
| Stolen session cookie used from another network | Works until idle/absolute timeout (cookie is HttpOnly, so XSS can't read it). Proposed hardening for P5: bind the session to a hash of the user agent; not IP (mobile networks change IPs). |
| CSRF: malicious site posts to `api.<domain>` | Cookie not sent (`SameSite=Strict`); even if it were, no `X-CSRF-Token` → 403. |
| Staff opens console in two tabs | Same cookie, same session; both work; logout in one ends both. |
| Clock skew on the ID token | Allow 60 s leeway on `iat`/`exp` checks (**Verify** library default). |
| Patient token copied to another browser | Works until expiry (bearer token), but only for that session, and the session's verified patient can still only be acted on after verification in that session. Short lifetimes limit this. |
| Patient tries `session_id` B with token for A | `sid` ≠ path → 404. |
| Patient reloads the page | Token from `sessionStorage` resumes if the idle key still exists; else a new session. |
| WebSocket opened without the auth message | Closed with 4401 after 5 s; counted for `voice_concurrent` only after auth. |
| Redis unavailable | Staff and patient session checks fail → 503 `dependency_unavailable` (the readiness probe also fails, P1-01); rate limits per §6 fail-open/closed rules. |
| `PATIENT_SESSION_SIGNING_KEY` rotated | New tokens use the new key and `kid`; old tokens valid until expiry via `_PREVIOUS`; remove `_PREVIOUS` after `PATIENT_SESSION_MAX_S`. |
| `/internal/jobs/...` called with a valid Google token for another SA | 401, `internal.auth_failed` logged. |
| Invite link expires before the staff member uses it | Admin re-sends via `POST /v1/admin/staff/{id}/resend-invite` (same guard and audit `staff.create` with `reason_code=resend`). |

## 9. Security, HIPAA and PHI
- **PHI handled:** none directly. Staff emails and names are workforce data, not PHI. Patient sessions carry only IDs; `verified_patnum` is stored in Redis and in the `sessions` row (P1-03). Tokens contain no PHI. Client IPs go only to `audit_log` (P1-07).
- **Never log:** ID tokens, session IDs (log only a 8-char hash prefix if needed: `sess_hash`), CSRF tokens, patient JWTs, invite or password-reset links, TOTP secrets. Add `sess_hash` to the P1-07 allow-list.
- **Controls:**
  - **staff authentication:** MFA mandatory (TOTP), invite-only, unique accounts per person (no shared logins; stated in `auth.md` and the clinic onboarding checklist, P6-01);
  - **staff sessions:** server-side and revocable, with automatic logoff after 15 min idle and a 12 h maximum; cookie protections plus CSRF tokens;
  - **authorization:** RBAC with default deny and clinic scoping (404 on foreign IDs), and masked contacts for Read-only;
  - **patient sessions:** short-lived signed tokens bound to session and clinic, an idle timeout, at most 3 verification attempts, and rate limits;
  - **internal routes:** OIDC with exact service-account emails, plus the edge block at Cloud Armor (P1-02).
- **Audit:**
  - `auth.login`, `auth.login_failed`, `auth.mfa_failed`, `auth.logout`;
  - `staff.create`, `staff.role_change`, `staff.deactivate`;
  - `security.access_denied`, `security.rate_limited`;
  - `patient.verify_failed` (from P2-12 using this limiter).
- **Risks reduced:** P0-11 R04, R05, R32 (deactivation; periodic reviews are in P5-14).
- **HIPAA:**
  - §164.312(a)(2)(i) unique user identification;
  - §164.312(a)(2)(iii) automatic logoff;
  - §164.312(d) authentication;
  - §164.308(a)(4) access authorization (roles);
  - §164.308(a)(3)(ii)(C) termination procedures (deactivation).

## 10. Testing
Unit and integration tests (`backend/tests/unit/auth/`, `backend/tests/integration/auth/`; Identity Platform mocked, Redis and Postgres real in CI):

| # | Test | Expected |
|---|---|---|
| T1 | Session create with a valid TOTP ID token for an active staff member | 200; `__Host-dai_staff` cookie with Secure, HttpOnly, SameSite=Strict, Path=/; audit `auth.login` |
| T2 | ID token without `sign_in_second_factor` | 401 `mfa_required`; audit `auth.mfa_failed`; no cookie |
| T3 | ID token for an inactive or unknown staff member | 401 `account_disabled`; audit `auth.login_failed` |
| T4 | Request after 15 min idle (time-travel Redis TTL) | 401 `session_expired` |
| T5 | Requests every 5 min for 12 h 5 min | Last one 401 `session_expired` (absolute) |
| T6 | POST without or with a wrong `X-CSRF-Token` | 403 `csrf_failed` |
| T7 | Deactivate staff with 2 live sessions | Both sessions rejected on next request; IdP `update_user(disabled=True)` and `revoke_refresh_tokens` called |
| T8 | **Matrix:** for each of the 4 roles × 9 permissions, a test route with `require(p)` | 200 exactly where `ROLE_PERMISSIONS` allows, else 403 `forbidden` (36 cases, parametrized from the matrix) |
| T9 | READ_ONLY fetches a callback | Contact fields masked; FRONT_DESK sees them |
| T10 | **Default deny:** introspect `app.routes` | Every `/v1/admin/*` route depends on `require`/`current_staff`; every `/internal/*` route on `require_internal_caller` |
| T11 | Admin demotes themself; demote the last admin | 409 / 409 `last_admin` |
| T12 | Staff of clinic A requests a callback ID of clinic B | 404 |
| T13 | `POST /v1/sessions` → use token on `GET …/sessions/{sid}/…` | 200; token claims as §6; no PHI in token |
| T14 | Token for session A used on path of session B | 404 |
| T15 | Token with bad signature / wrong `aud` / expired / signed with `_PREVIOUS` key | 401 / 401 / 401 / 200 |
| T16 | 4 failed verification attempts | 4th returns 403 `verification_locked`; one `security.rate_limited` audit row |
| T17 | 11 `POST /v1/sessions` from one IP in a minute | 11th 429 with `Retry-After`; one audit row for that window |
| T18 | `/internal/jobs/x` with: no token; Google token for another SA; token with wrong audience; correct `sa-scheduler` token (mocked verifier) | 401, 401, 401, 200 |
| T19 | Redis down: `patient_message` limit vs `staff_login` limit | Patient message allowed (fail open, `ratelimit.unavailable` logged); staff login 503 (fail closed) |
| T20 | WebSocket: no auth message in 5 s; expired session | Close 4401; close 4408 |

Manual checks in dev (recorded in `docs/security/auth.md`):
- TOTP enrollment and login with a real authenticator app;
- idle logout at 15 min in the UI;
- the widget in an iframe on a different-origin test page in Safari, Chrome and Firefox (token flow works, no cookie needed);
- `gcloud scheduler jobs run` reaches `/internal/jobs/unsent-email-check` and passes the auth check.

## 11. Acceptance criteria
- [ ] Identity Platform is configured with email/password, TOTP MFA mandatory (no SMS MFA), invite-only sign-up and authorized domain `app.<domain>`; the verified facts are recorded
- [ ] Staff get a console session only with a TOTP second factor and an active `staff_users` row (T1–T3); sessions are server-side, cookie-protected, CSRF-checked, end after 15 min idle and 12 h total, and are revoked on deactivation or role change (T4–T7)
- [ ] The RBAC matrix is enforced for all 36 role/permission pairs; every admin route requires a permission; foreign-clinic IDs return 404; READ_ONLY sees masked contacts (T8–T12)
- [ ] Admins can invite, change roles and deactivate staff, with self and last-admin guards and audit entries
- [ ] Patient sessions use signed tokens (no cookies) bound to session and clinic; idle 15 min, max 2 h; WebSocket auth by first message with close codes 4401/4408; 3 failed verifications lock the session (T13–T16, T20)
- [ ] Rate limits in §6 return 429 with `Retry-After`, log and audit once per window, and follow the fail-open/fail-closed rules (T17, T19)
- [ ] `/internal/*` accepts only Google OIDC tokens for `sa-scheduler`/`sa-tasks-invoker` with the right audience (T18)
- [ ] `auth.md` and `rbac.md` are written; the §7 step 13 issues are notified

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI (T1–T20); manual checks recorded
- [ ] PR reviewed (HIPAA review if labelled `phi`): tech lead + compliance owner (MFA, timeouts, matrix); not labelled `phi` (no PHI handled), but CODEOWNERS covers `app/auth/`
- [ ] No PHI in logs: no tokens, session IDs, links or secrets logged (checked by P1-07's leak suite extended with token-shaped samples)
- [ ] Docs / README updated: `auth.md`, `rbac.md`, `.env.example` (local signing key placeholder), README "How to log in locally"

## 13. Hand-off
| Task | Can rely on |
|---|---|
| P2-01 Session state | `PatientPrincipal`, `current_patient`, `end_session`, Redis key `psess:{sid}` (TTL = idle timeout) |
| P2-12 Identity verification | `mark_verified(session_id, patnum)`, `record_verify_attempt`, `verification_locked` (403), max 3 attempts |
| P2-08 Tool gateway | Tools take the patient only from `principal.verified_patnum` |
| P2-25 Widget + bot protection | `POST /v1/sessions` response, Bearer header, WebSocket first-message auth, `verify_bot_token` hook, `sessionStorage` rule |
| P3 voice tasks | WebSocket close codes 4401/4408/4429; `voice_concurrent` limit |
| P4-09, P4-11, P4-13 Console | `require(Permission…)`, `StaffPrincipal`, masking rule, `apiFetch` with CSRF; `CONFIG_WRITE` for booking horizon |
| P2-22 Email | `EmailSender` used for staff invites (link never logged) |
| P4-04, P2-22 internal handlers | `require_internal_caller` at router level |
| P5-08 Security tests | Matrix, default-deny test, rate limits to attack-test |
| P6-01 Onboarding | Create the clinic's first ADMIN with `create_admin.py` equivalent for prod (run by `key-admin`/ops via PAM), unique accounts per staff member |

## 14. Open questions
| Question | Owner | Needed by |
|---|---|---|
| Is the role matrix in §6 right for the pilot clinic (especially: may Dentists see the AI activity log; may Front Desk read config)? | Project sponsor with the clinic (P0-01 follow-up) | Before P4-09 |
| Does Identity Platform's built-in brute-force protection meet our need, or do we add reCAPTCHA on login now (P2-25)? | Tech lead | Step 2 |

## 15. References
- Plan §4.2, §6, §11
- Identity Platform overview: https://docs.cloud.google.com/identity-platform/docs/overview
- Identity Platform MFA (TOTP): https://docs.cloud.google.com/identity-platform/docs/web/totp-mfa
- Verifying ID tokens / Admin SDK: https://firebase.google.com/docs/auth/admin/verify-id-tokens
- Revoking sessions: https://firebase.google.com/docs/auth/admin/manage-sessions
- Google HIPAA covered products: https://cloud.google.com/security/compliance/hipaa
- Cloud Run service-to-service auth (ID tokens): https://docs.cloud.google.com/run/docs/authenticating/service-to-service
- `google.oauth2.id_token`: https://googleapis.dev/python/google-auth/latest/reference/google.oauth2.id_token.html
- OWASP Session Management Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html
- OWASP CSRF Prevention Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html
- MDN cookies (`__Host-` prefix, SameSite): https://developer.mozilla.org/docs/Web/HTTP/Cookies
- HIPAA Security Rule 45 CFR §164.308, §164.312
- Related tasks: P0-06, P0-11, P1-01, P1-02, P1-03, P1-05, P1-07, P2-01, P2-08, P2-12, P2-22, P2-25, P3-01, P4-04, P4-09, P4-11, P4-13, P5-03, P5-08, P5-14, P6-01
