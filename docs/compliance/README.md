# Compliance records

| File | What |
|---|---|
| [../adr/0001-gemini-models.md](../adr/0001-gemini-models.md) | **Gemini models ADR** (P0-13): tiers, two backends, data settings. Proposed |
| [../architecture/](../architecture/README.md) | **Architecture and PHI flow table** (P0-14): [phi-flows.md](../architecture/phi-flows.md) is the source of truth for PHI hops, check `scripts/compliance/check_phi_flows.py`; ADRs 0002–0006 in [../adr/](../adr/README.md) |
| [risk/](risk/) | **HIPAA risk assessment v1.1** (P0-11, flows updated by P0-14): [assessment](risk/risk-assessment-v1.md), [register](risk/risk-register.md) (42 risks, check `scripts/compliance/check_risk_register.py`), [safeguard coverage](risk/safeguard-coverage.md), [accepted risks](risk/accepted-risks.md) (none). Draft v1; final at P5-14 |
| [vendor-matrix.md](vendor-matrix.md) | **Vendor/BAA matrix and PHI gate** (P0-10), generated from [vendors.yaml](vendors.yaml) (schema [vendors.schema.json](vendors.schema.json)). Gate today: **CLOSED** |
| [pr-vendor-check.md](pr-vendor-check.md) | PR checklist text for P1-01, and the proposed CODEOWNERS entries (not active) |
| [baa-google-cloud.md](baa-google-cloud.md) | Google Cloud HIPAA BAA record. Status **NOT ACCEPTED**. Includes the covered-products snapshot (2026-11-26). P0-10 imports it into the vendor matrix. |
| [bootstrap-checks-2026-11-26.md](bootstrap-checks-2026-11-26.md) | Output of the Google Cloud setup checks (P0-05) |
| [baa-google-workspace.md](baa-google-workspace.md) | Google Workspace BAA record (P0-08): **NOT ACCEPTED**; no domain or Workspace until production |
| [email-readiness-example-dental.md](email-readiness-example-dental.md) | Callback email readiness for our clinic (P0-08): **not ready**, placeholder address |
| [baa/](baa/) | Clinic ↔ company BAA (P0-09): [requirements checklist](baa/requirements-checklist.md), [Annex A](baa/annex-a-data-and-purposes.md) (data and purposes), [Annex B](baa/annex-b-subcontractors.md) (subcontractors), [commitments](baa/commitments.md), [template v1 draft](baa/clinic-baa-template-v1.md) |
| [baa-clinic-example-dental.md](baa-clinic-example-dental.md) | Clinic BAA record (P0-09): **NOT SIGNED**; no counsel engaged; reviews and clinic comments |
| [baa-meta-whatsapp.md](baa-meta-whatsapp.md) | Meta (WhatsApp Cloud API) BAA record (P0-07): **NOT ACCEPTED**; Meta's terms say it isn't a business associate; written request drafted |
| [baa-twilio.md](baa-twilio.md) | Twilio (Programmable SMS) BAA record (P0-07): **NOT ACCEPTED**; needs Security/Enterprise Edition; written request drafted |
| [patient-messaging-decision.md](patient-messaging-decision.md) | Patient messaging decision (P0-07a): **WhatsApp now** (testing, synthetic data); **at go-live each clinic chooses SMS or WhatsApp**, WhatsApp with real details only after a signed Meta BAA (else SMS); sources, advisor answers, signatures |
| [messaging_policy.yaml](messaging_policy.yaml) | Machine-readable content policy: allowed channel and fields per message type (check: `scripts/compliance/check_messaging_policy.py`) |
| [sources/README.md](sources/README.md) | Dated, fingerprinted sources for the messaging decision |
| [hipaa-controls.md](hipaa-controls.md) | HIPAA guardrails (P0-06): Assured Workloads decision, allowed services, status of every control (enforced / substitute / pending), dated evidence |

Runbooks: [gcp-bootstrap.md](../runbooks/gcp-bootstrap.md), [org-guardrails-tests.md](../runbooks/org-guardrails-tests.md) · IDs: [infra/bootstrap/foundation.yaml](../../infra/bootstrap/foundation.yaml) · Allow-list: [infra/org/allowed_services.yaml](../../infra/org/allowed_services.yaml)

## Current state (2026-11-26)
- **Google Cloud:** projects `dai-rcpt-dev`, `dai-rcpt-staging`, `dai-rcpt-prod` and `dai-rcpt-ops` exist in a personal Google account, with no organization (DECISIONS #293).
- **Data:** synthetic only. **No PHI may enter any project.**

## Vendor matrix and PHI gate (P0-10)
Commands (run from the repo root):
```bash
python3 scripts/compliance/check_vendors.py            # validate rules C1-C9; exit 0 ok, 1 errors
python3 scripts/compliance/check_vendors.py --render   # write vendor-matrix.md (never edit it by hand)
python3 scripts/compliance/check_vendors.py --gate     # GATE OPEN (exit 0) or GATE CLOSED with reasons (exit 2)
pytest scripts/compliance/                             # tests (needs pytest, pyyaml, jsonschema)
```

### How to add a vendor
1. Add a row to `vendors.yaml` with `baa.status: pending` (or `phi: "no"` with a real `no_phi_control`) in the same change that introduces the vendor.
2. Get the BAA through the vendor's task, and write its record `baa-<vendor>.md` in the P0-05 format.
3. When the record says accepted or signed: set `baa.status: signed`, `date` and `record`.
4. If it will receive the clinic's PHI: update Annex B of the clinic BAA and notify each clinic at least 30 days before PHI flows (P0-09 C8).
5. Run `--render`, commit the YAML and `vendor-matrix.md` together.

A vendor that won't sign a BAA stays `phi: "no"` with a real control, or is dropped. A dropped vendor keeps its row with "dropped on YYYY-MM-DD" in `notes` until its data is deleted.

### Review routine
- **Quarterly:** the compliance owner re-reads every row against its record, re-checks Google's covered-products list against `infra/org/allowed_services.yaml` (P0-06 owns it), updates `reviewed_on`, and re-renders. The checker warns (C9) after 100 days.
- **On any change** (new vendor, new Google API, BAA signed or renewed, vendor dropped): update `vendors.yaml` in the same change.
- Until CI exists (P1-06), run the checker locally before each commit that touches these files.

## Pending before real PHI
Every item must be done before any real PHI enters `dai-rcpt-prod` (dev, staging and ops never get real PHI):

| Item | Why it's pending | Task |
|---|---|---|
| Accept the Google Cloud HIPAA BAA, save the copy, legal review | Paper-only for now (user decision 2026-11-26) | P0-05 / P0-11 |
| Billing account linked to the four projects | No billing account yet | P0-05, deferred (runbook Part B); needed before P1-02 |
| Terraform state bucket `gs://dai-rcpt-ops-tfstate` and its synthetic test | Needs billing | P0-05, deferred (Part B); needed before P1-02 |
| Budget USD 50 with 50/90/100% alerts | Needs a billing account | P0-05, deferred (Part B) |
| Company domain with Workspace or Cloud Identity, and so an organization | Personal account has no organization | P0-05 (runbook Part C) |
| Folder `dental-ai`, with the projects moved into it | Needs an organization | P0-05 (Part C) |
| IAM through groups only; default domain-wide creator grants removed | Needs an organization and groups | P0-05 (Part C) |
| Two break-glass super-admins with hardware keys; 2-step verification enforced for admins | Needs Workspace or Cloud Identity | P0-05 (Part C) |
| Org-level essential contacts | Needs an organization (project-level contacts are set) | P0-05 (Part C) |
| Org policies (service allow-list, Gemini Developer API deny, US-only locations, no SA keys, domain-restricted IAM, no public buckets or SQL public IP, no VM external IPs): apply `infra/org/` Terraform and run the negative tests | Org policies can't be set without an organization (DECISIONS #296) | P0-06 (guardrails runbook) |
| VPC-SC perimeters `dai_prod` (enforced), `dai_dev` and `dai_staging` (dry-run) | Need an organization | P0-06 / P1-02 |
| Speech-to-Text data logging confirmed off with a screenshot | API not enabled yet (so it can't be on) | P3-03 |
| Clinic ↔ company BAA ([baa-clinic-example-dental.md](baa-clinic-example-dental.md)): counsel finalizes template v1, sponsor decides outside-US access and names our signatory, both parties sign | Paper record, NOT SIGNED; no counsel engaged | P0-09 (DECISIONS #305, #306) |
| Messaging BAA for the clinic's chosen channel: Twilio for SMS ([baa-twilio.md](baa-twilio.md)), Meta for WhatsApp ([baa-meta-whatsapp.md](baa-meta-whatsapp.md)) | Both NOT ACCEPTED; requests drafted, not sent; Meta's terms currently say it isn't a business associate | P0-07 (DECISIONS #299–#301) |
| Callback email: company domain, Google Workspace and its BAA ([baa-google-workspace.md](baa-google-workspace.md)), `callbacks@` lock-down, SPF/DKIM/DMARC, TLS rule per clinic, readiness with the clinic's real domain | Bought for production; Workspace BAA NOT ACCEPTED | P0-08 (DECISIONS #303, #304) |
| Vendor matrix shows every PHI vendor signed and `check_vendors.py --gate` prints **GATE OPEN** | Matrix built; gate CLOSED (all BAAs pending) | P0-10 |

## Pending notifications
These GitHub issues aren't closed yet or don't have this information. When each task starts, comment on its issue with the paths above.

| Task | What it relies on | Posted on issue (date) |
|---|---|---|
| P0-07 Messaging provider (from P0-07a) | Done in P0-07: Meta Cloud API direct for WhatsApp, Twilio for SMS (DECISIONS #300) | ✅ |
| P0-15 Sender registration (from P0-07a) ✅ templates v1 done in P0-15 | WhatsApp test number and templates now; SMS sender (10DLC or toll-free verification) before go-live; templates may use only the fields in `messaging_policy.yaml` | - |
| P0-15 Sender registration (from P0-07) | Meta Cloud API test number now; production WhatsApp and Twilio SMS registration steps in `docs/integrations/messaging-provider.md` §8 | - |
| P0-10 Vendor matrix (from P0-07) | Rows for Meta and Twilio from `baa-meta-whatsapp.md` and `baa-twilio.md` (both NOT ACCEPTED); the test tunnel noted as test-only, no PHI | ✅ done in P0-10 (`vendors.yaml`) |
| P0-10 Vendor matrix (from P0-08) | Row for Google Workspace (Gmail) from `baa-google-workspace.md` (NOT ACCEPTED); Mailpit is a local dev tool, not a vendor | ✅ done in P0-10 (`vendors.yaml`) |
| P2-23 Admin email sender (from P0-08) | Templates in `docs/integrations/admin-email/templates/`, config keys and load-time rules, keyless DWD design (`gmail.send`, `signJwt`), limits, logging rules, Mailpit for local dev (`docs/integrations/admin-email.md`) | - |
| P2-22 Callback cases (from P0-08) | `case_id` must be a random opaque ID (it appears in emails and links) | - |
| P4-13 / P4-14 (from P0-08) | Config keys `callback.*` and their rules; link format `/cases/{case_id}`; unsent-email alerts | - |
| P0-06 / P1-05 (from P0-08) | APIs `gmail.googleapis.com`, `iamcredentials.googleapis.com`; service account `admin-email-sender` in a dedicated project, key creation blocked | - |
| P4-01 / P4-06 / P4-07 (from P0-07) | Integration facts in `messaging-provider.md` §7: Graph API v27.0, `X-Hub-Signature-256`, status values, no WhatsApp STOP keyword handling (P4-07 must detect it), Twilio `X-Twilio-Signature` via SDK validator; **P4-06 runs the deferred live webhook test** | - |
| P1-05 Secrets (from P0-07) | Create `whatsapp-access-token`, `whatsapp-app-secret`, `whatsapp-webhook-verify-token`; later `twilio-account-sid`, `twilio-auth-token`, `twilio-messaging-service-sid` | - |
| P0-09 Clinic ↔ company BAA (from P0-07a) | Must mention subcontractors under their own BAAs, including the messaging vendors of the clinic's chosen channel: the SMS provider, or Meta and the WhatsApp provider (advisor answer 5, DECISIONS #299) | - |
| P0-10 Vendor matrix (from P0-09) | Import Annex B (`baa/annex-b-subcontractors.md`) and the clinic BAA record (NOT SIGNED); the 30-day subcontractor notice (C8) is part of the matrix change process | ✅ done in P0-10 (`vendors.yaml`) |
| P0-11 Risk assessment (from P0-09) | Annex A as the data inventory; commitments C1–C22 as controls; open questions: outside-US access, Open Dental relay | ✅ used in P0-11 (`risk/`) |
| P0-12 Open Dental keys (from P0-09) | **The clinic's production key may not be requested until the clinic BAA record says SIGNED**; test database only | ✅ recorded in P0-12 (`docs/integrations/open-dental-access.md` §5) |
| P1-07 Audit log (from P0-09, spec named P1-12) | Audit retention 6 years (C20); audit entries must support the accounting-of-disclosures information (C10) | - |
| P5-12 Incident response and retention (from P0-09) | Breach notice ≤ 5 business days (C4); check a same-day heads-up for v2; access/amendment requests forwarded in 5 business days, accounting info in 10 (C9, C10); return/destroy in 30 days with certificate (C13) | - |
| P5-14 HIPAA readiness (from P0-09) | Checklist, commitments and the signed record as evidence | - |
| P4-01 / P4-03 / P4-04 / P4-07 / P4-08 (from P0-07a) | Enforce `messaging_policy.yaml` (refuse disallowed channel, unknown or never-allowed fields); opt-out text in every message; both adapters, WhatsApp active for testing, SMS switched off until go-live | - |
| P4-02 Consent (from P0-07a) | Consent names the channel and message types, carries the SMS risk notice, rates notice, STOP/HELP, "not required to book"; dated record; wording approved by the advisor | - |
| P0-13 Gemini model choice (from P0-06) | Gemini only via `aiplatform.googleapis.com` (Developer API never enabled); US regional endpoint only, since the location policy doesn't cover global endpoints | ✅ used in P0-13 (ADR 0001) |
| P1-02 Terraform base (from P0-06) | `allowed_apis` from `infra/org/`; no `vpcaccess` (use Cloud Run Direct VPC egress); `servicenetworking` allowed by exception #295; perimeters to enforce after dry-run review; Cloud Run needs VPC-SC setup; Cloud SQL must use private IP | - |
| P1-03 / P1-05 (from P0-06) | Not Assured Workloads (#295), so CMEK only where the plan requires it | - |
| P1-06 CI/CD (from P0-06) | `ops` is outside every perimeter; CI needs an ingress rule; `iamcredentials` and `sts` are on the ops list; no SA keys (use Workload Identity Federation) | - |
| P1-07 Monitoring (from P0-06) | Alert on VPC-SC dry-run violations and org-policy changes once they exist | - |
| P3-03 Speech-to-Text (from P0-06) | Re-check data logging (screenshot) when the API is enabled; code must never enable it | - |
| P0-10 Vendor/BAA matrix | `baa-google-cloud.md` as the Google Cloud row: **NOT ACCEPTED**; `hipaa-controls.md` as guardrail evidence; the SMS provider from P0-07a/P0-07 | ✅ done in P0-10 (`vendors.yaml`) |
| P0-11 Risk assessment (from P0-10) | `vendors.yaml` / `vendor-matrix.md`: vendor list with PHI flags and environments as the third-party input; gate CLOSED today | ✅ used in P0-11 (`risk/`) |
| P5-12 Incident response (from P0-11) | Scenarios R01–R38 from `risk/risk-register.md`, especially R31 (late breach), R21–R24 (outages, data loss) and the C risks; gap G4 contingency plan is yours (DECISIONS #310) | - |
| P5-14 HIPAA readiness (from P0-11) | Finalize the register and sign-off; gaps G1–G3 (policies, training, sanctions, access reviews, device policy) are yours; confirm G4 with the advisor; R29 legal review still pending; re-check the Security Rule NPRM status | - |
| P0-14 Architecture (from P0-11) | Replace the flow table F1–F9 and asset inventory A01–A18 (`risk/risk-assessment-v1.md` §3–§4) with the data-flow diagram, then trigger a review | - |
| High-risk control owners (from P0-11) | Reference your risk IDs in your spec and tests: P1-07 (R01, R20, R31), P2-12 (R02, R16), P2-04 and P2-08 (R03, R18, R27), P1-13 and P4-09 (R04, R05), P1-05 (R06, R10, R12), P0-13 (R07, R13), P2-22 (R08, R23), P2-25 (R15, R25), P2-20 (R26, R28), P1-02 (R34, R37), P0-12 (R12, R36) | - |
| P1-01 Monorepo (from P0-10) | Copy the checklist in `pr-vendor-check.md` into `.github/pull_request_template.md`; CODEOWNERS entries there are proposed, add the file only when the user decides (DECISIONS #308). No GitHub issue yet | - |
| P1-06 CI/CD (from P0-10) | Run `check_vendors.py` and `pytest scripts/compliance/` on every PR; `check_vendors.py --gate` must print GATE OPEN before the first prod deploy with real PHI. No GitHub issue yet | - |
| P1-15 Open Dental client (from P0-12) | Base URL, `ODFHIR {DeveloperKey}/{CustomerKey}` header, env/secret names, 1 request per second per customer key processed sequentially, 429 + `Retry-After`, 504 after 60 s, lists of 100 with Limit/Offset, 400 for version too low (`docs/integrations/open-dental-access.md` §1–§4, DECISIONS #312). Wrong-key status and measured rate pending the deferred smoke test | - |
| P1-16 Adapters (from P0-12; spec also named P1-17) | Seed cases with refs (`open-dental-test-data.md`), phone formats, Open Dental's duplicate check on `POST /patients`, cancel via `PUT /appointments/{AptNum}/Break`, list GETs only on 24.3; test database (B) pending, so build against `respx` mocks | - |
| P1-20 Availability (from P0-12) | The 1-request-per-second throttle: cache providers, operatories, appointment types and schedules; minimize calls per availability query | - |
| P3-14 Latency (from P0-12; spec named P3-15) | Open Dental latency numbers come from the deferred smoke test; until then assume up to ~1 s per request plus queueing | - |
| P1-06 CI/CD (from P0-12) | `pytest scripts/open_dental/`; nightly `smoke_test.py --target testdb` once (B) exists; integration tests serial per customer key; never against the hosted database | - |
| P0-10 / P0-11 (from P0-12) | Open Dental row: $30 per location per month, permissions per DECISIONS #312 (updated in `vendors.yaml`). R12: least-privilege permissions requested but not granted yet (no developer key) | - |
| P2-03 LLM provider and routing (from P0-13) | ADR 0001 §5: config keys, approved list, `VERTEX_LOCATION=us`, `thinking_level` per tier; startup checks (developer only with `APP_ENV=local`, no `global`, no `preview`/`exp`/`latest`, allowed list) as in `evals/spike/p0-13/run_spike.py check_config`; GenerateContent API (or Interactions with `store=false`); no grounding tools; SDK `google-genai` | - |
| P2-05 Extraction (from P0-13) | Spike schema and 30 extraction items in `evals/spike/p0-13/`; `intent` is null when a turn only answers a question; failure patterns in the results summary once runs exist | - |
| P3-01 / P3-14 Voice latency (from P0-13) | Vertex `us` TTFT not measured yet (no billing); Developer API numbers are indicative only; `gemini-3.8-live` noted as the Live API option (DECISIONS #69) | - |
| P5-01 Eval harness (from P0-13) | Reuse the three spike sets as a starting suite; model-change procedure in `docs/runbooks/gemini-model-lifecycle.md` | - |
| P0-10 / P0-11 / P0-14 (from P0-13) | Vendor row `google-ai-studio` (`phi: no`, local only, DECISIONS #316). R13: `cacheConfig` EPHEMERAL pending and abuse-monitoring question open, so R13 stays a planned control. Data-flow F2: `us` multi-region endpoint, no grounding, no request-response logging | - |
| P1-01 Monorepo (from P0-14) | ADR 0006 conventions; module responsibilities in `docs/architecture/containers.md` §3; add `check_phi_flows.py` to CI with the other compliance checks; app-level outbound host allow-list (R42) | - |
| P1-02 Terraform base (from P0-14) | `docs/architecture/network.md`: LB + Cloud Armor, ingress "Internal and Cloud Load Balancing", Direct VPC egress + Cloud NAT static IPs, restricted VIP DNS, **PSC endpoint for `aiplatform.us.rep.googleapis.com`**, Gmail via NAT, `dns.googleapis.com` now allowed (DECISIONS #319); open questions Q1–Q5; Cloud Run settings in ADR 0002; Memorystore TLS + AUTH, CMEK only at creation | - |
| P1-03 Cloud SQL (from P0-14) | ADR 0005: Postgres 16, CMEK, private IP via PSC, no public IP, IAM DB auth, HA in prod, 30 backups + PITR in the US | - |
| P1-06 CI/CD (from P0-14) | Two Cloud Run services (`web`, `api`); deploy from `ops` with a perimeter ingress rule; Cloud Run continuous deployment isn't available inside a perimeter (sources A9) | - |
| P2-01 State machine and slot memory (from P0-14) | Save state after every turn so a reconnect (60-minute WebSocket limit, instance loss) loses nothing (sequences S1b, R39) | - |
| P2-03 LLM provider (from P0-14) | Flow F02 rules; the only Gemini path; fail startup if `GOOGLE_API_KEY` is set outside `APP_ENV=local`; never Pipecat's LLM services (ADR 0003, R40) | - |
| P3-01 / P3-02 Voice (from P0-14) | Confirm ADR 0003 (Pipecat only for transport/VAD/STT/TTS, explicit US `location`) and ADR 0004 (WebSocket, 16 kHz PCM, 20 ms); implement reconnect with session token | - |
| P4-01 / P4-04 Messaging and reminders (from P0-14) | F10a/F10b content limits; webhook signature checks, no payload in logs (F15a/F15b, R41); task payloads carry IDs only and handlers re-fetch (F13) | - |
| P0-09 Clinic BAA (from P0-14) | Annex A must match `phi-flows.md`: add inbound status and replies to A4; clarify Annex B B1 "logging" (F11 allows no PHI) | - |
| P0-10 Vendor matrix (from P0-14) | Flow rows use vendor ids `google-cloud`, `google-workspace`, `meta-whatsapp`, `twilio`, `open-dental`, `google-ai-studio`; rule R-F blocks any flow to an unlisted vendor | - |
| P5-14 HIPAA readiness (from P0-10) | `vendor-matrix.md` and the `--gate` output as evidence | - |
| P0-05, P0-07, P0-08, P0-09 (from P0-10) | When a record turns ACCEPTED/SIGNED, set that row (or clinic) to `signed` with date and record, and re-render | - |
| P0-13 Gemini model choice | Covered entries "Generative AI on Agent Platform" and "Gemini Enterprise Agent Platform" (Vertex AI renamed); GA models only | ✅ used in P0-13 (ADR 0001) |
| P1-02 Terraform base | `foundation.yaml`: **import** the four projects, never recreate them; the state bucket once Part B is done | - |
| P4-01 Messaging adapter (from P0-15) | Load `docs/messaging/templates.yaml` at startup and fail if `check_templates.py` rules fail; render `{var}` for SMS and send WhatsApp as named parameters; WhatsApp STOP/START/HELP and auto-reply from `system_replies` (Twilio handles SMS keywords by default, error 21610 = opted out); template IDs and statuses from the registration record | - |
| P4-02 Consent (from P0-15) | Consent checkbox text in `docs/messaging/opt-in-and-help-texts.md` §1, verbatim, unchecked by default, plus the policy's risk-notice sentence | - |
| P4-03 Booking messages (from P0-15) | Formats `ddd, MMM D` and `h:mm A` in the clinic time zone; only the template fields | - |
| P4-04 Reminders (from P0-15) | Reminder templates `reminder_sms_v1` / `reminder_wa_v1` ("today at" a time) | - |
| P0-10 / P0-14 (from P0-15) | No new vendor or flow: templates stay within F10a/F10b fields; Twilio stays SMS-only and off until its BAA | - |
