# Glossary

Terms a new team member needs. Add new terms when they first appear in a task.

| Term | Meaning |
|---|---|
| **Open Dental** | Practice-management software the clinic uses. Holds patients, appointments, schedules, providers. It is our source of truth. |
| **Open Dental API** | Open Dental's REST API at `https://api.opendental.com/api/v1`. Requests are relayed to the clinic's database through the clinic's **eConnector**. |
| **Developer key / Customer key** | Open Dental API credentials: ours, and one per clinic. Sent as `Authorization: ODFHIR {DeveloperKey}/{CustomerKey}`. |
| **PatNum** | Open Dental's patient ID (integer). The only patient identifier we store. |
| **AptNum** | Open Dental's appointment ID (integer). |
| **Operatory** | A treatment room/chair in Open Dental; appointments are booked into an operatory. |
| **Appointment type** | A named kind of visit defined in Open Dental (e.g. "Recall"), with a default length. Mapped from reason codes in P0-02. |
| **Provider / ProvNum** | A dentist or hygienist in Open Dental, identified by the integer ProvNum. Setup data, not PHI. |
| **Reason code** | Our fixed list of visit reasons (e.g. `toothache`, `emergency_exam`). The LLM classifies the patient's words into one; config maps it to an appointment type (P0-02). |
| **Clinic slug** | Lowercase hyphenated clinic identifier used in config paths, e.g. `smile-dental-pdx`. |
| **PHI** | Protected Health Information under HIPAA: anything that identifies a patient together with health or care data (name, DOB, phone, email, address, appointment reason…). |
| **HIPAA** | US law protecting health information. Drives our encryption, access control, logging and vendor rules. |
| **BAA** | Business Associate Agreement. A contract required before any vendor processes PHI for us. We need: Google Cloud, Google Workspace, WhatsApp BSP, each clinic. |
| **Covered products list** | Google's list of Cloud services covered by its BAA. We only use services on it. |
| **Organization / folder / project (Google Cloud)** | Google Cloud resource hierarchy: the organization (tied to the company domain) contains folders, which contain projects where resources live. Ours: folder `dental-ai` with `-dev`, `-staging`, `-prod`, `-ops` projects (P0-05). |
| **Organization policy** | A Google Cloud rule set on the org, a folder or a project that limits configuration (e.g. allowed services, allowed locations). Inherited by children. |
| **VPC Service Controls (VPC-SC) / perimeter** | A boundary around projects that blocks Google API calls moving data across it. Dry-run mode only logs would-be violations. |
| **Assured Workloads** | Google Cloud feature that applies a compliance package of controls to a folder, e.g. "US Data Boundary for Healthcare and Life Sciences". |
| **Gemini Developer API / AI Studio** | Google's API-key-based Gemini access (`generativelanguage.googleapis.com`). Never used here; we call Gemini only through Vertex AI. |
| **Break-glass account** | Emergency super-admin account with a hardware security key, used only for recovery. |
| **Essential contacts** | Email addresses Google uses for security, billing and legal notices about our organization. |
| **Vertex AI** | Google Cloud's AI platform. We call Gemini only through Vertex AI (BAA-covered), never through AI Studio / Gemini Developer API keys. |
| **GA / Pre-GA** | Generally Available vs preview/experimental. Only GA models and features may touch PHI. |
| **STT / TTS** | Speech-to-Text / Text-to-Speech (Google Cloud, streaming). |
| **VAD** | Voice Activity Detection: detects when someone is speaking. |
| **Endpointing** | Deciding that the user has finished their turn. |
| **Barge-in** | User starts talking while the AI is speaking; we stop audio and cancel generation. |
| **TTFT** | Time to first token from the LLM. |
| **Voice-to-voice latency** | Time from the end of the user's speech to the first AI audio heard. |
| **Tool / tool calling** | A backend function the LLM may request (e.g. `book_appointment`). Runs only through the **tool gateway**. |
| **Tool gateway** | Our layer that validates tool calls: allow-list per state, JSON schema, preconditions, session scoping, idempotency. |
| **Slot memory** | Structured data collected in a conversation (name, DOB, phone, preferred time…). Not to be confused with appointment **time slots**. |
| **State machine / transition / guard** | The conversation is always in one state; an event moves it to the next state via a transition, allowed only if its guards (yes/no conditions such as `verified`) hold. Defined in `docs/flows/state_machine.yaml` (P0-04). |
| **Global interrupt** | An event that can fire in any state (emergency, "talk to a person", Open Dental down, idle timeout) and overrides the normal flow. |
| **Golden conversation** | A synthetic example conversation per flow with the expected state, slots and tool calls per turn; used as an eval scenario. |
| **Mermaid** | Text-based diagram format rendered by GitHub; used for flow diagrams. |
| **Idempotency key** | A unique key per action so a retried request doesn't create a second record. |
| **BSP** | WhatsApp Business Solution Provider: a company that connects a business to the WhatsApp Business Platform. With the Cloud API, Meta hosts and processes message content, and Meta states it is not a Business Associate and the platform is not HIPAA compliant (see P0-07a, DECISIONS #35). |
| **A2P 10DLC / toll-free verification** | US carrier registration required for business (application-to-person) texting from ordinary long-code numbers, or verification for toll-free numbers. Has lead time. |
| **Messaging policy** | `docs/compliance/messaging_policy.yaml` (P0-07a): which channel may carry which message type and which fields are allowed; enforced by P4-01. |
| **TCPA** | US Telephone Consumer Protection Act: consent rules for automated texts and calls. |
| **Template (WhatsApp)** | Pre-approved message format required for business-initiated WhatsApp messages. |
| **Emergency tiers** | Tier 1 = life-threatening (call 911 + URGENT case), Tier 2 = urgent dental (urgent slot or URGENT callback), Tier 3 = routine symptoms (normal booking). Plus `crisis` (self-harm → 988) and `uncertain` (URGENT callback with 911 safety line). See P0-03. |
| **Under-triage / over-triage** | Treating an emergency as less urgent than it is (target 0) / treating a non-emergency as more urgent (tracked, acceptable). |
| **Co-occurrence group** | In emergency rules: a set of terms of which at least one must appear; a category matches when every group has a hit in the same sentence (e.g. "swelling" + "eye"). |
| **988** | US Suicide & Crisis Lifeline (call or text 988). |
| **TLS compliance (Gmail)** | Workspace setting that forces TLS for mail to listed domains; mail to a server without TLS bounces instead of going unencrypted. |
| **SPF / DKIM / DMARC** | DNS records that prove a domain may send email and how receivers should treat failures; keep callback emails out of spam. |
| **Domain-wide delegation** | Workspace setting that lets a service account act as a Workspace user for listed API scopes only (here: send mail as `callbacks@`). |
| **Email mode (`link_only` / `full_details`)** | Content of callback emails: case link only (default, no PHI) or the full §4.9 details (needs advisor approval). |
| **Callback case** | Record created when the AI can't resolve something; the clinic admin is emailed and calls the patient back. |
| **CMEK** | Customer-Managed Encryption Keys (Cloud KMS) used to encrypt our database. |
| **RBAC / MFA** | Role-based access control / multi-factor authentication for clinic staff. |
| **eConnector** | Open Dental program running at the clinic that relays Open Dental API requests to the clinic's own database. Must be running for the API to work. |
| **Pilot clinic** | The first real clinic that uses the system (Phase 6). Its answers in P0-01 set the defaults for later clinics. |
| **Clinic SME** | Subject-matter expert at the clinic (usually the office manager). Answers workflow questions and signs off decisions (P0-01, P5-15). |
| **Clinic decision log** | `docs/discovery/clinic-decision-log.md`: the clinic's signed-off answers from P0-01, cited as "P0-01 Q1"… "P0-01 B8". Contains no PHI. |
| **Agreed default** | A decision-log status: the clinic accepted our Proposed value and set a date to review it. Other statuses: Answered, Blocked. |
| **E.164** | International phone format, e.g. `+15035550123`. |
| **Covered entity** | Under HIPAA: a health plan, clearinghouse or provider that bills electronically. The clinic is the covered entity. |
| **Business associate** | A company that handles PHI on behalf of a covered entity. We are the clinic's business associate and need a BAA with it (P0-09). |
| **Subcontractor (HIPAA)** | A vendor that handles PHI on behalf of a business associate (e.g. Google Cloud, the messaging provider). Each needs a BAA with us and is listed in Annex B of the clinic BAA. |
| **Annex A / Annex B** | Attachments of the clinic BAA (P0-09): Annex A lists the PHI categories, purposes, storage and retention; Annex B lists our subcontractors and their BAAs. |
| **Commitments table** | `docs/compliance/baa/commitments.md`: maps every promise in a clinic BAA to the task that implements it. No term is signed without a row (DECISIONS #45). |
| **Breach notification** | Telling the affected party about a breach of unsecured PHI. HIPAA (45 CFR 164.410) gives a business associate at most 60 days; our proposed BAA term is 5 business days to the clinic. |
| **Vendor/BAA matrix** | `docs/compliance/vendors.yaml` and its generated `vendor-matrix.md` (P0-10): every third party, whether PHI reaches it, its BAA status and record. |
| **PHI gate** | The set of conditions before real PHI may enter production (DECISIONS #25). Shown by `check_vendors.py --gate` as OPEN or CLOSED. |
| **Compliance owner** | Named person who reviews every change to the vendor matrix and compliance files (CODEOWNERS team `compliance-owners`). |
| **CODEOWNERS** | GitHub file that makes chosen people required reviewers for changes to chosen paths. |
| **Risk analysis** | HIPAA Security Rule requirement (45 CFR 164.308(a)(1)(ii)(A)): assess risks to ePHI. Ours is P0-11 (v1), finalized in P5-14. |
| **ePHI** | Electronic protected health information: PHI that is stored or sent electronically. The Security Rule protects ePHI. |
| **Risk register** | `docs/compliance/risk/risk-register.md`: one row per risk with likelihood, impact, score, controls (task IDs), residual score and owner. |
| **Residual risk** | The risk score that remains once the planned controls are in place. |
| **Accepted risk** | A risk the sponsor decides to live with, written in `accepted-risks.md` with reason and review date. |
| **Remote API** | Open Dental's cloud-hosted API (`api.opendental.com/api/v1`) that relays requests to a clinic through its eConnector. The mode we use. Throttled to 1 request/s per customer key. |
| **Developer Portal** | Open Dental's web portal where we see our developer key and generate customer keys for each location (P0-12). |
| **Test DB (A) / (B)** | (A) Open Dental's public hosted test database, read smoke tests only; (B) our own synthetic Open Dental test install in `<prefix>-dev`, the integration DB (P0-12). |
| **Seed data** | The documented synthetic patients, providers, operatories, schedules and appointments loaded into test DB (B) (`docs/integrations/open-dental-test-data.md`). |
| **GA / Preview / short-term model** | Google model lifecycle labels. GA models with a 12-month lifecycle are the only ones we use with PHI; preview and short-term models are excluded (DECISIONS #65). |
| **Model tier** | `lite`, `flash` or `pro`: the routing level of plan §4.3; each maps to one model ID in config (P0-13, P2-06). |
| **Global vs US endpoint** | Vertex AI endpoints. `global` may process data anywhere; the `us` multi-region and `us-*` regional endpoints keep ML processing in the US. We use only US endpoints. |
| **Implicit caching** | Vertex AI's automatic prompt caching (in-memory and durable, up to 24 h). Durable caching is turned off for us because it doesn't support CMEK. |
| **ADR** | Architecture Decision Record: a short document in `docs/adr/` recording one technical decision, its options and reasons. |
| **Trust boundary** | A line in the data-flow diagram where data passes between parties with different protections (browser, our prod project, Workspace, a vendor, the clinic). |
| **PHI flow table** | `docs/architecture/phi-flows.md` (P0-14): every PHI hop with fields, vendor id, BAA and protection. The source of truth for Annex A and the risk assessment. |
| **Restricted VIP** | `restricted.googleapis.com`: the address range for Google APIs that VPC Service Controls fully enforces. |
| **Instance-based billing** | Cloud Run setting (formerly "CPU always allocated"): CPU stays allocated while an instance is up. Any open WebSocket makes the instance billed this way. |
| **Session affinity** | Cloud Run cookie-based routing of a client to the same instance. Best effort only. |
| **Pipecat** | Open-source Python framework for real-time voice agents (transports, VAD, STT/TTS). Proposed for our voice pipeline only (ADR 0003). |
| **Brand / Campaign (10DLC)** | A2P 10DLC registration parts: the brand is the business that sends (here the clinic, with its EIN); the campaign describes the messages, sample texts and opt-in flow. |
| **ISV** | Independent software vendor: a company (us) that registers and sends messages on behalf of its customers (clinics) under its own provider account. |
| **GSM-7 / segment** | SMS character set and unit. One GSM-7 segment holds 160 characters; non-GSM characters cut it to 70. Our templates target one segment. |
| **Message template** | Fixed message text with named variables (`{first_name}`), stored in `docs/messaging/templates.yaml` and checked against `messaging_policy.yaml` (P0-15). |
| **Liveness / readiness** | `/healthz` says the process is up; `/readyz` says it can serve traffic (database and Redis reachable). Cloud Run uses them as probes. |
| **Request ID** | An ID per request (`X-Request-ID`), included in every log line and error response so a problem can be traced without logging PHI. |
| **gitleaks** | A scanner that blocks commits and PRs containing secrets such as API keys. |
| **uv** | Python package and environment manager with a lockfile (`uv.lock`), used for the backend. |
| **Private Service Access (PSA)** | A reserved IP range in our VPC, peered with Google's network, where Cloud SQL and Memorystore get private IPs. |
| **Direct VPC egress** | Cloud Run setting that sends a service's outbound traffic through our VPC subnet, so firewall rules and private IPs apply. |
| **Serverless NEG** | A load-balancer backend that points at a Cloud Run service. |
| **DNS response policy** | Cloud DNS rules that override answers for names such as `*.run.app` inside the VPC, e.g. to send them to the restricted VIP. |
| **Cloud NGFW FQDN rule** | A firewall-policy rule that allows egress to named hosts (e.g. `api.opendental.com`) instead of IP ranges. |
| **Cloud Armor** | Google's edge security policy on the load balancer: WAF rules, rate limiting, path blocking. |
| **Reminder sweep** | Hourly Scheduler job that enqueues reminders due in the next 48 hours, because Cloud Tasks can't schedule more than 30 days ahead. |
| **OIDC token (service-to-service)** | A signed Google identity token that Cloud Tasks and Scheduler attach to calls; the API checks its audience and service-account email. |
| **IAM database authentication** | Logging in to Cloud SQL with a Google identity (here a service account) instead of a password. |
| **Cloud SQL Python Connector** | Google's library that opens authenticated, encrypted connections to Cloud SQL from Python (used with asyncpg). |
| **PITR (point-in-time recovery)** | Restoring the database to any moment within the log retention window (7 days here). |
| **Regional HA (Cloud SQL)** | A standby in a second zone that takes over automatically if the primary zone fails. |
| **Blind index** | An HMAC of a normalized value (e.g. a phone number) stored next to its ciphertext so rows can be found by exact match without decrypting. |
| **Append-only table** | A table whose rows can be inserted and read but never changed or deleted by the app (audit log, consents, config versions). |
| **Alembic** | The migration tool for SQLAlchemy; each schema change is a versioned migration file. |
| **Idempotency key** | A key sent with a write (e.g. a booking) so that retrying it never performs the action twice. |
| **KEK / DEK** | Key-encryption key (here the KMS key `app-fields`) wraps the data-encryption keys (the Tink keyset) that actually encrypt fields. |
| **Envelope encryption** | Encrypting data with a local data key, and encrypting that data key with a KMS key. |
| **Tink keyset** | A set of keys handled by Google's Tink library; one primary key encrypts, the others can still decrypt, which allows rotation. |
| **Associated data (AAD)** | Extra context bound into an encryption (table, column, clinic) so a ciphertext only decrypts in the place it was written. |
| **Privileged Access Manager (PAM)** | Google Cloud service for temporary, approved IAM grants instead of standing access. |
| **Break-glass access** | Emergency access path, used rarely, always audited and reviewed. |
| **Resource-level IAM binding** | Granting a role on one resource (a single secret, key or queue) instead of the whole project. |
| **Workload Identity Federation (WIF)** | Lets GitHub Actions exchange its short-lived OIDC token for Google Cloud access, so no service-account key is stored in GitHub. |
| **GitHub Environment** | A named deploy target in GitHub (dev, staging, prod) with required reviewers and branch rules; its name is part of the OIDC token. |
| **Image digest** | The immutable `sha256:` ID of a container image; deploying by digest guarantees the exact same image runs everywhere. |
| **Promotion** | Moving an already-tested image digest to the next environment without rebuilding it. |
| **Expand/contract migration** | A schema change split into a backward-compatible "expand" release and a later "contract" (cleanup) release, so old and new code can run at the same time. |
| **Smoke test** | A short post-deploy check (health, version, a few routes) that decides whether to keep or roll back a release. |
| **Vulnerability waiver** | A time-limited, approved exception for a known image vulnerability, recorded in `security/vuln-waivers.yaml`. |
| **Release PR** | A small pull request that changes a file in `releases/` (e.g. the SHA to put in prod); its required reviews are the approval for that release. |
| **Field allow-list (logging)** | The fixed set of log fields that may be written; any other field is dropped automatically. |
| **Event name** | A fixed dotted log message such as `booking.slot_taken`, used instead of free-text messages so no data ends up in the message. |
| **Scrubber** | The last logging layer that replaces anything looking like a phone, email, date or ID number with `[REDACTED:<kind>]`. |
| **Audit mirror** | A PHI-free copy of each committed audit row written to a locked log bucket, as tamper-evident backup of the database audit log. |
| **Bucket lock (Cloud Logging)** | Makes a log bucket's retention permanent: entries can't be deleted early and retention can't be reduced. |
| **Data Access audit logs** | Google Cloud logs of who read or used data and keys (e.g. KMS decrypts, secret reads); off by default for most services. |
| **OpenTelemetry (OTel)** | Open standard and SDK for traces and metrics, exported here to Cloud Trace and Cloud Monitoring. |
| **p50 / p95** | The median and 95th-percentile latency: half of requests are faster than p50, 95% are faster than p95. |
| **Identity Platform** | Google Cloud's sign-in service (same engine as Firebase Authentication); stores staff accounts and MFA, issues ID tokens. |
| **TOTP** | Time-based one-time password from an authenticator app (6 digits, changes every 30 s); our required second factor for staff. |
| **RBAC** | Role-based access control: each role (Admin, Front Desk, Dentist, Read-only) has a fixed set of permissions. |
| **CSRF** | Cross-site request forgery: another site tricking a logged-in browser into sending requests; blocked by SameSite cookies and the `X-CSRF-Token` header. |
| **IDOR** | Insecure direct object reference: reading another clinic's or patient's record by changing an ID; blocked by clinic scoping (404). |
| **Automatic logoff** | Ending a session after a period of inactivity (15 min here), a HIPAA addressable safeguard. |
| **Bearer token** | A token that grants access to whoever holds it; patient session tokens are short-lived and bound to one session. |
| **Token bucket** | Rate-limiting method: each subject has a bucket of allowed requests that refills over time. |
| **Pacer** | Shared Redis-based gate that spaces our requests to one clinic's Open Dental to stay under 1 request per second across all instances. |
| **Interactive vs background priority** | Open Dental calls made while a patient or staff member waits go first; reminder and refresh jobs use leftover capacity. |
| **Uncertain write** | A booking or change request whose result is unknown (timeout after sending); resolved by reading Open Dental, never by sending it again. |
| **od_fake** | Our fake Open Dental server with synthetic data and injectable faults, used in development and CI. |
| **Contract test** | A test that checks the shape and behaviour of an external API; run against both the fake and the real test database. |
| **Stale-on-error** | Serving the last cached copy of setup data when Open Dental is temporarily unavailable. |
| **eConnector** | Open Dental's service on the clinic's server that relays Remote API requests to the clinic database; if it is off, the API fails. |
| **Idempotency guard** | Our wrapper around every Open Dental write that records the request key in Postgres so the same request can never create two records. |
| **Reconcile** | After a write with an unknown result, read Open Dental to find out whether it actually happened, instead of sending it again. |
| **AI marker** | A short tag like `[AI-booked ref:7KQ2M9XA]` in an appointment note, showing staff the AI made it and letting us find it exactly; contains no patient data. |
| **Break (appointment)** | Open Dental's way to cancel a scheduled appointment; it can move the appointment to the Unscheduled list for staff follow-up. |
| **Unscheduled list** | Open Dental list of appointments that need to be rebooked; staff work through it to contact patients. |
| **PatStatus** | Open Dental patient status: Patient, NonPatient, Inactive, Archived, Deceased or Prospective. |
| **AptStatus** | Open Dental appointment status: Scheduled, Complete, UnschedList, Broken, Planned, PtNote, PtNoteCompleted. |
| **Clinic config version** | An immutable snapshot of all of a clinic's rules; changes always create a new version, and one version is active. |
| **Session pinning** | A conversation keeps using the config version it started with, even if the clinic changes the config meanwhile. |
| **AI booking window** | The hours in which the AI may offer appointment slots; an extra limit on top of the providers' Open Dental schedules. |
| **Blockout** | A time block in the Open Dental schedule reserved for a purpose (e.g. emergencies or new patients) or closed for booking. |
| **Edit matrix** | Which config sections clinic admins may change in the console, and which only through a reviewed file and release PR. |
| **JSON merge patch** | A standard way (RFC 7396) to send only the changed parts of a JSON document. |
| **Availability engine** | Our code that turns Open Dental's open times plus clinic rules into 2–3 real appointment options. |
| **Offer store** | Per-session record of the slots the patient was shown; booking is allowed only for one of these. |
| **Slot lock** | A short Redis lock taken while booking, so two of our bookings for the same chair or provider and day can't run at once. |
| **Lead time** | The minimum time between now and the earliest offered slot (routine and urgent values are configurable). |
| **Pattern (appointment)** | Open Dental's appointment length string: one character per 5 minutes (`X` provider time, `/` assistant time). |
| **Tool registry** | The list of backend functions the AI may ask to run, each with a fixed input and output schema. |
| **Tool context** | Server-side facts passed to every tool (clinic, session, verified PatNum, config); the AI can't change them. |
| **Handle** | A short session-only reference such as `A1` that the AI uses instead of real Open Dental IDs. |
| **Function declaration** | The tool description format Gemini receives so it can request a tool call. |
| **Event (conversation)** | Something that can move the conversation to another state, e.g. `confirmed`, `faq_asked`, `emergency_tier1`; code fires it, the AI may only propose it. |
| **Resume state** | The state a side branch (like FAQ) returns to when it is done. |
| **Masked view** | The version of collected patient details given to the AI, with most personal values hidden (e.g. "provided"). |
| **Compare-and-set (CAS)** | Saving only if nobody else changed the data since it was read, so two servers can't overwrite each other. |
| **TTFT (time to first token)** | Time from sending a request to an LLM until its first streamed text arrives. Drives how soon a patient sees or hears a reply (P2-03, P3-15). |
| **Model tier** | One of `lite`, `flash`, `pro`: a class of Gemini model chosen per request by the model router. Model IDs per tier come from config (P0-13, P2-03). |
| **Model router** | Deterministic rules in P2-03 that decide whether a turn is answered by a template, a clinic-config lookup (no LLM) or an LLM tier, with a `reason_code`. |
| **Fallback model** | A second GA model configured per tier (`GEMINI_MODEL_*_FALLBACK`), tried once when the primary fails before any output was sent (P2-03). |
| **Google Gen AI SDK (`google-genai`)** | Google's Python SDK for Gemini. With `vertexai=True` it calls Vertex AI using service-account credentials; we never use its API-key mode (P2-03). |
| **Thinking budget** | A setting on newer Gemini models that limits how many tokens the model spends reasoning before answering; more thinking is better for hard turns but slower (P2-03). |
| **ADC (Application Default Credentials)** | Google's standard way for code to find credentials automatically; on Cloud Run it is the service's own service account, so no key file or API key is needed (P2-03). |
| **Reply intent** | A short name a state handler sets to say what the AI should say next (`ask_missing`, `offer_options`, `booked`). P2-04 decides how it is worded (template or LLM) (P2-01, P2-04). |
| **Reply facts** | The non-PHI, sanitized data a reply may mention for one turn (offered slot labels, provider names, booking outcome, clinic-info answers). The output guardrail checks LLM text against them (P2-04). |
| **Prompt injection** | Text from a patient or from data that tries to make the model ignore its instructions. We treat such text as data, give the model no tools and check every reply sentence (P2-04). |
| **Output guardrail** | Deterministic checks (G1–G7) run on each sentence the model writes before the patient sees or hears it; a failing sentence is replaced by a template (P2-04). |
| **Reply template** | A fixed, versioned sentence for a reply intent, with whitelisted placeholders; used for greetings, read-backs, emergencies, static answers and as the fallback when the guardrail fails (P2-04). |
| **Intent** | What the patient wants overall: `book`, `reschedule`, `cancel`, `check_appointment`, `faq`, `talk_to_human`, `complaint` or `other` (P0-04, P2-05). |
| **Structured output** | Asking Gemini to answer with JSON that follows a given schema; used for extraction (P2-03 `structured()`, P2-05). |
| **Code-only event** | A state-machine event only code may fire (tool results, timeouts, emergency rules); never offered to the model in the extraction schema (P2-05). |
| **Unclear slot** | A slot the model marks as uncertain; it is never stored and the AI asks again (P2-05). |
| **Confirmation card** | A written summary of everything the AI is about to do (appointment, registration or callback details) shown in the chat window; the patient checks it and says yes or what to change. It carries the operation hash (P2-04, P2-08). |
| **Operation hash** | An HMAC of exactly what the patient confirmed (operation kind plus slot, appointment or details). Shown with the confirmation card and checked again by the tool gateway before the write (P2-08). |
| **Tool budget** | The maximum number of times a tool may run in one patient session (for example 5 patient searches), to stop enumeration and runaway loops (P2-08). |
| **Precondition (tool)** | A guard that must be true before a tool runs, such as `verified` or `confirmation_recorded` (P2-08). |
| **Verification oracle** | Any difference in the AI's replies, timing or attempt counting that would tell an unverified person whether a patient record exists. P2-12's flow is designed to have none. |
| **Jaro-Winkler** | A 0–1 string similarity that favours matching prefixes; used with a 0.92 threshold to tolerate typos in first names (P2-12). |
| **Nickname table** | A reviewed list of common US given-name nickname groups (Bob ~ Robert) used when matching first names (P2-12). |
| **Strong match** | Exactly one existing-status Open Dental record whose last name, DOB and first name match the patient's answers (plan §4.5, P2-12). |
| **Household (session)** | The family members verified or registered in one chat (max 4). One of them is the active patient; tools, cards and writes always apply to the active patient only (P2-12, DECISIONS #185). |
| **Active patient** | The household member the AI is currently helping; `principal.verified_patnum` holds their PatNum (P1-13, P2-12). |
| **Guarantor** | In Open Dental, the person financially responsible for a patient's account (for a child, usually a parent). The AI never sets it; staff link it after a minor is registered (P2-15). |
| **Registration card** | The confirmation card for a new patient's details (name, DOB, mobile, email, address) shown before the record is created (P2-04, P2-15). |
| **Quick reply (choice)** | A tappable button under the AI's message (for example an offered time or "Later times"); tapping sends a `choice_id` that code maps directly, without the LLM (P2-16, P2-25). |
| **Booked card** | A read-only card in the chat window shown only after Open Dental confirms an appointment, with patient, visit, date and time, dentist and location (P2-16). |
| **Notice window** | The minimum time before an appointment (default 24 hours) inside which the AI may not reschedule or cancel it; the patient is offered a staff callback instead (P1-19 `policies`, P2-18). |
| **Policy checkpoint** | One of the three places where the notice-window rule is checked in code: the flow handler, the gateway guard and the tool handler (P2-18). |
| **Rebook offer** | The question "Would you like to book a new time?" shown after a successful cancel (P2-18). |
| **Emergency stickiness** | Within one session, an emergency action runs only when a new result is more severe than the one already handled, so repeated symptoms don't restart the flow (P2-20). |
| **Safety-net line** | The fixed script sentence telling a Tier 2 patient to call 911 if specific danger signs appear; no treatment advice (P0-03, P2-20). |
| **Reason registry** | The single list of callback reasons any flow may raise, each mapped to a P1-03 category, default urgency and staff label (P2-22). |
| **Unsent alert** | A callback case whose admin email failed after all retries (`email_status = FAILED`); shown in the console and alerted to on-call (P2-22, P4-14). |
| **Outbox sweep** | A job that re-sends queue tasks for records still marked pending, so a lost enqueue never loses an email (P2-22). |
| **Case reference** | The short random code shown to the patient for a callback case, e.g. `CB-7Q2M8X` (P2-22). |
| **Embed snippet** | The one-line `<script>` tag a clinic adds to its website to show the chat launcher and widget iframe (P2-25). |
| **frame-ancestors** | A Content-Security-Policy directive listing which sites may show our page in an iframe; set per clinic from `widget.allowed_origins` (P2-25). |
| **reCAPTCHA Enterprise score** | Google's 0.0–1.0 estimate that a browser session is human, used to block or limit bots when a chat session starts (P2-25). |
| **Display history** | The encrypted list of the last 30 messages shown to the patient, used to restore the chat after a page reload in the same tab (P2-25). |
| **Stale card** | A card or set of buttons from an earlier message; it is disabled so an old choice can't be tapped (P2-27). |
| **WCAG 2.2 AA** | The W3C web accessibility standard level our widget must meet (contrast, keyboard, focus, target size, announcements) (P2-27). |
| **Live region** | A page area whose updates screen readers announce automatically; used for new chat messages and the emergency banner (P2-27). |
| **Text-only mode** | A widget setting that hides the avatar and animation and can enlarge text (P2-27). |
| **ZZTEST patient** | A synthetic patient created by tests on Open Dental test DB (B), recognised by the `ZZTEST` last-name prefix and cleaned up after runs (P0-12, P2-30). |
| **Flaky scenario** | An E2E scenario that failed once and passed on its single retry; reported separately so trends are visible (P2-30). |
| **Promotion gate** | A CI check that must pass before a build digest is promoted to the next environment (P1-06, P2-30). |
| **Voice-to-voice latency** | Time from the end of the patient's speech to the first assistant audio heard; target ≤ 1.5 s p50 / ≤ 2.5 s p95 (plan §4.4, P3-01). |
| **Endpointing** | Deciding that the patient has finished speaking so the AI can reply; target ≤ 500 ms after speech ends (P3-01, P3-02). |
| **Replay mode** | Feeding recorded WAV files instead of the live microphone so latency runs are repeatable and the end of speech is known exactly (P3-01). |
| **Voice allow-list** | The fixed set of standard female en-US Google TTS voices the product may use (`TTS_ALLOWED_VOICES`, DECISIONS #175, ADR 0007). |
| **Protocol v2** | The voice extension of the widget WebSocket protocol: binary audio frames plus voice control messages, on the same socket as text (P3-02, DECISIONS #226). |
| **Binary audio frame** | A WebSocket binary message with a 9-byte header (kind, sequence number, utterance or reply id) followed by PCM16 audio (P3-02). |
| **Pre-roll** | The last 300 ms of audio kept in a ring buffer and sent when speech starts, so the first syllable is not cut off (P3-02). |
| **Endpoint profile** | The silence rule set in force for the current state: `normal`, `data_entry` or `spelling` (P3-02, DECISIONS #227). |
| **Jitter buffer** | A small playback buffer (60–120 ms) that smooths uneven arrival of TTS audio before it is played (P3-02). |
| **Phrase hints** | Words and phrases (and class tokens like digit sequences) sent with a Speech-to-Text request to bias recognition toward expected terms; ours never contain patient data (P3-03, DECISIONS #231). |
| **Partial transcript** | An interim STT result while the patient is still speaking; it may change. The final transcript is the settled text used for the turn (P3-03). |
| **Speech normalizer** | Our code that rewrites reply text so it reads correctly aloud (phone digits one by one, times, "Doctor", clinic pronunciations) before Text-to-Speech (P3-03). |
| **Pronunciation map** | Clinic config `voice.pronunciations`: words the voice says wrongly and how to say them, e.g. "Nguyen" → "Win" (P3-03, DECISIONS #232). |
| **Data logging (Speech-to-Text)** | Google's opt-in programme that lets it keep audio to improve models; it must never be enabled for our projects (P0-06, P3-03). |
| **Backchannel** | Short listener sounds ("okay", "mm-hmm") spoken while the assistant talks; they pause playback briefly but do not count as a barge-in (P3-06). |
| **Pause-then-decide** | Our barge-in method: pause the assistant's audio at once, then use the STT words within 700 ms to either stop the reply or resume it (P3-06, DECISIONS #234). |
| **Protected audio** | Assistant audio that cannot be interrupted; only the first sentence of the 911 script (P3-06, DECISIONS #235). |
| **Filler phrase** | A short pre-recorded line such as "Let me check that for you." played while a slow lookup runs, audio only (P3-06). |
| **Speculative extraction** | Running slot extraction on the partial transcript during the endpoint wait and reusing it if the final text matches; never runs tools or saves (P3-06, DECISIONS #236). |
| **Read-back** | The assistant repeats a critical detail it heard by voice (name, DOB, phone, email, ZIP) and waits for "yes" before using it (P3-09, DECISIONS #238). |
| **Unconfirmed slot** | A voice-heard critical value not yet confirmed by read-back; no handler or tool may use it (P3-09). |
| **Spelling mode** | A voice mode where the patient spells a name letter by letter (plain letters, NATO words or "B as in boy"), with a longer endpoint wait (P3-09). |
| **NATO phonetic alphabet** | Alfa, Bravo, Charlie… words used to spell letters clearly over voice (P3-09). |
| **Failure ladder** | The fixed sequence of fallbacks after repeated read-back failures: ask again, spell, type it, callback (P3-09, DECISIONS #240). |
| **Rive** | A vector-animation tool and runtime. It was planned for the avatar (DECISIONS #242) but is no longer used: the avatar is now a code-drawn voice orb (DECISIONS #270). |
| **Avatar state** | What the avatar shows: idle, listening, thinking or speaking, driven by voice protocol events (P3-11, DECISIONS #242). |
| **Partial transcript bubble** | The grey, updating chat bubble that shows what the patient is saying before the turn ends (P3-11, DECISIONS #244). |
| **Reply follows the channel** | A reply is spoken only when the patient's turn was spoken; typed turns get text only (P3-11, DECISIONS #245). |
| **Permissions API** | A browser API that tells whether microphone access is granted, denied or not yet asked, without asking (P3-11). |
| **p50 / p95** | The median and the 95th-percentile value of a measurement; "p95 ≤ 2.5 s" means 95% of turns are faster (P3-14). |
| **Voice-to-first-sound** | Time from the end of the patient's speech to any assistant audio, filler included; voice-to-voice excludes fillers (P3-14, DECISIONS #247). |
| **Nightly latency run** | The automated staging run that replays recorded speech through the full voice pipeline every night and checks the targets (P3-14, DECISIONS #248). |
| **Decision rule (tuning)** | A condition written before tuning that says when a setting may change and when the change is kept (P3-14, DECISIONS #249). |
| **Gap report** | The document listing where voice latency misses its target and the options, used for a product-owner decision (P3-14). |
| **WhatsApp Cloud API** | Meta's HTTP API for sending and receiving WhatsApp messages from a business number (`POST /<PHONE_NUMBER_ID>/messages`); P4-01's adapter speaks this format. |
| **24-hour customer service window** | WhatsApp allows free-form (non-template) messages only within 24 hours of the user's last message; outside it, error 131047 (P4-01). |
| **X-Hub-Signature-256** | Header on Meta webhooks: `sha256=` + HMAC-SHA256 of the raw body with the App Secret. P4-01 rejects requests whose signature doesn't match. |
| **wamid** | The WhatsApp message ID returned on send and echoed in status webhooks; stored as `outbound_messages.provider_msg_id`. |
| **biz_opaque_callback_data** | A string we attach when sending; Meta echoes it in status webhooks. P4-01 puts the `outbound_messages.id` there. |
| **Content mode** | `messaging_policy.yaml` `whatsapp.mode`: `phi_free_nudge` (clinic name and phone only) or `minimal_phi` (adds first name, date, time; advisor approval required) (DECISIONS #252). |
| **Policy gate** | The checks G1–G8 that every outbound patient message passes before reaching the provider (P4-01). |
| **outbound_messages** | Table tracking each patient message's status (queued → sent → delivered/read, or failed/skipped); never stores the body (P4-01). |
| **System reply** | A fixed, PHI-free free-form WhatsApp reply (STOP/START/HELP confirmation, auto-reply) sent only inside the 24-hour window (P4-01). |
| **Consent wording version** | ID of the exact consent text shown to the patient (e.g. `wa-optin-nudge-v1`), stored in `consents.wording_version`; any text change gets a new ID (P4-02). |
| **ConsentService** | Shared backend service that reads, grants and revokes messaging consent and cancels pending reminders on revoke; used by the chat, STOP/START and the staff screen (P4-02). |
| **Consent step** | The `CONSENT` state, between choosing a slot and the confirmation card, where the AI asks about WhatsApp messages and the number (P4-02, DECISIONS #256). |
| **WhatsApp card row** | The last row of the book/reschedule/cancel confirmation card showing where the WhatsApp message will go, with a "check carefully" note (DECISIONS #254). |
| **Notification task** | The IDs-only Cloud Task on the `notifications` queue that sends a booking confirmation, reschedule or cancel notice after re-reading the appointment from Open Dental (P4-03). |
| **APPT_CHANGED (skip)** | Reason code for a notice or reminder that was not sent because the appointment in Open Dental no longer matches the event (e.g. cancelled right after booking) (P4-03). |
| **ReminderPlanner** | The P4-04 interface told about every booked, rescheduled or cancelled appointment so the 1-hour reminder is created, moved or cancelled (P4-03). |
| **Reminder sweep** | Hourly Scheduler job that enqueues reminders due in the next 48 hours (Cloud Tasks can't schedule more than 30 days ahead) and marks missed ones `TOO_LATE` (P4-04). |
| **Pre-send verification** | Re-reading the appointment from Open Dental right before a reminder is sent; it is sent only if the appointment still exists at the same time (P4-04). |
| **Send-time offset** | Minutes before the appointment that the reminder is sent (`reminders.offset_minutes`, 30–240, default 60); stored on each reminder row (P4-04). |
| **Console shell** | The admin console's login, session, layout and permission-filtered menu that every staff screen plugs into (P4-09). |
| **`<Can>`** | Frontend component that shows its children only if the signed-in staff member has a given permission (P4-09). |
| **Save and publish** | The console's single step for settings changes: preview the diff, write a change note, create and activate a new config version (P4-09, DECISIONS #262). |
| **Settings history** | Console page listing config versions with who, when and why, with a diff view and restore (P4-09). |
| **Availability preview** | Console "Check availability": counts of open slots in the next 7 days for current vs proposed settings, before publishing; counts only, nothing stored (P4-11). |
| **Config change request** | A request from clinic staff to change file-only settings such as emergency rules; stored in `config_change_requests` and applied by the project team through the reviewed file process (P4-11). |
| **Visit length source** | Where an appointment's length comes from: the Open Dental appointment type pattern when the variant has one, otherwise `duration_min` (P1-20, P4-11). |
| **Greeting override** | Clinic-edited first sentence the AI says (`conversation.greeting_override`); only `{assistant_name}` and `{clinic_name}` placeholders allowed (P4-13). |
| **Test email (callback)** | Console button that sends a PHI-free test email to a callback address to prove it receives mail (P4-13). |
| **Voice sample** | Console button that plays the greeting with the unsaved voice, rate and pronunciations (P4-13). |
| **Contact attempt** | One staff call to a callback patient, recorded with a fixed outcome code such as `NO_ANSWER` or `APPOINTMENT_MADE` (`callback_attempts`, P4-13a). |
| **AI activity log** | Console list of patient conversations with outcome codes (booked, callback, emergency…), built from audit rows; no text (P4-13a). |
| **AI-booked review** | Console list of appointments the AI created, with live Open Dental details and a "Mark reviewed" action (P4-13a). |
| **Run-now (reminder)** | Staging-only endpoint that runs the real reminder task handler immediately instead of waiting for its send time; used by E2E tests (P4-17). |
| **Lifecycle suite** | The Phase 4 E2E tests that follow one appointment from booking through confirmation, reminder, reschedule or cancel, and notices (P4-17). |
| **Live messaging check** | The one E2E scenario that sends a real WhatsApp message to the team's test phone and waits for Meta's delivered status (P4-17). |
| **Voice orb** | The widget's avatar: an abstract glowing circle drawn in code that changes with the assistant's state and moves with the sound level (P3-11, DECISIONS #270). |
| **AnalyserNode** | Web Audio node that reports an audio stream's waveform without changing it; used to measure loudness for the voice orb. |
| **Eval scenario** | A scripted multi-turn conversation with assertions on states, tool calls and slots, run against the real LLM (P5-01). |
| **LLM-as-judge** | A second model call that grades a reply against a rubric; report-only in our evals (P5-01). |
| **Flaky (eval)** | A scenario that fails, then passes on retry without a code change (P5-01). |
| **WER** | Word error rate: wrong, missing and extra words divided by the words in the reference transcript (P5-03). |
| **SNR** | Signal-to-noise ratio in dB; how much louder speech is than background noise (P5-03). |
| **Simulated caller** | Test client that plays recorded patient audio into the voice pipeline and plays a correction when the read-back is wrong (P5-03). |
| **Property-based test** | A test that generates many random inputs and checks that a rule always holds (Hypothesis; P5-04). |
| **UAT** | User acceptance testing: clinic staff try the system in realistic situations before go-live (P5-07). |
| **Persona card** | A fictional patient (name, DOB, phone, situation) that UAT testers use instead of real people (P5-07). |
| **Canary value** | A unique made-up value planted in test data so any leak can be found by searching for it (P5-08). |
| **SAST / DAST** | Static analysis of source code (Semgrep) / attacking the running app over HTTP (OWASP ZAP) (P5-08). |
| **IDOR** | Insecure direct object reference: reaching someone else's data by changing an ID in a request (P5-08). |
| **Binary Authorization** | Google Cloud control that lets only signed container images run (P5-08). |
| **Red teaming** | Deliberately attacking the AI (prompt injection, data requests, misuse) to find weaknesses (P5-08). |
| **Penetration test** | An authorized, time-boxed attack by an outside firm, ending in a findings report (P5-11). |
| **Rules of engagement** | Signed document stating what a pentest may attack, when, and what is forbidden (P5-11). |
| **Incident Commander** | The person who leads the response to an incident and owns its timeline (P5-12). |
| **RPO / RTO** | Recovery point objective (how much data may be lost) / recovery time objective (how long the service may be down) (P5-12). |
| **Tabletop exercise** | A meeting that walks through an imagined incident to test the plan (P5-12). |
| **Alert watcher** | The engineer on the daily rotation who checks the alert inbox during clinic hours (P5-12). |
| **Security Official / Privacy Official** | The people named as responsible for HIPAA security and privacy duties (P5-14). |
| **Access review** | A periodic check that every account still needs its access (P5-14). |
| **Kill switch** | Pilot flag that turns a channel off at once without a deploy (P6-01). |
| **Staff-only period** | Days in prod when only clinic staff can reach the widget through an unlisted link (P6-01). |
| **KPI** | Key performance indicator: a number with a target that shows whether the pilot is succeeding (P6-02). |
| **Failure taxonomy** | The fixed list of labels used to classify failed conversations in the weekly review (P6-04). |
| **Conditional go** | A pilot decision to expand only after listed fixes, used when quality KPIs miss by a small margin (P6-07). |
