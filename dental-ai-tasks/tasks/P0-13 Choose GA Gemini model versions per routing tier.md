---
id: P0-13
title: Choose GA Gemini model versions per routing tier
milestone: P0
epic: E0.3
size: S
labels: area:ai, type:spike
depends_on: P0-06
status: approved
---

# P0-13: Choose GA Gemini model versions per routing tier

## 1. Summary
Choose one Gemini model for each routing tier in plan §4.3:
- **Lite:** greetings, acknowledgements, short confirmations;
- **Flash:** intent and slot extraction with JSON output;
- **Pro:** ambiguous, multi-part or complaint conversations.

Then:
- confirm by a short spike that each model is GA, on a 12-month lifecycle, available on a **US** Vertex AI endpoint and covered by the HIPAA BAA;
- set the project's Gemini data settings: durable caching off, no grounding with Google Search, request-response logging off;
- measure latency, JSON quality and cost on a small synthetic eval;
- record everything in an ADR, with model IDs as **config, not code**.

Done means:
- `docs/adr/0001-gemini-models.md` is merged;
- the config keys and their values are defined;
- the cache setting is applied and verified in dev, staging and prod;
- the spike results are recorded;
- P2-03, P2-06 and P0-14 are notified.

## 2. Why this matters
Three rules from plan §3.3 meet here:
- Gemini only through Vertex AI in the BAA-covered project;
- **no Pre-GA models or features with PHI**;
- avoid data-logging options.

Picking a preview model, the global endpoint or a feature that stores prompts would send PHI outside what the BAA and the US-only guardrails (P0-06) cover. Picking a short-lived model forces a rushed migration in the middle of the pilot.

Model choice also drives the two pilot targets most exposed to the LLM:
- voice latency (≤ 1.5 s p50 voice-to-voice);
- extraction accuracy, which feeds booking without callback (≥ 70%).

A small measured spike now is cheaper than discovering in P3-15 that the Flash tier is too slow.

Plan references: §4.3 (model routing), §3.3 (BAA rules: Vertex AI only, GA only, no data logging), §3.2 (stack), §1 principle 5 (swappable providers), §4.4 (latency targets).

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P0, Discovery & Compliance Foundation**.
- **Naming:** Google's docs now present Vertex AI generative features under the name **"Gemini Enterprise Agent Platform"**. The old `vertex-ai/generative-ai/docs/...` URLs still serve the same pages, and the API is still `aiplatform.googleapis.com`. The HIPAA covered-products list (updated 2026-11-11) names the entries **"Generative AI on Agent Platform"** and **"Gemini Enterprise Agent Platform"**. There is no entry called "Vertex AI". P0-05 records which entry covers us.
- **The model landscape, as read on 2026-11-24** (https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/model-versions, https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models). **Verify** again on the day of the spike, since this changes monthly.
  - GA models with a 12-month lifecycle ("available for at least 12 months after release"):

    | Model | Released | Retirement |
    |---|---|---|
    | `gemini-3.5-flash-lite` | 2026-07-21 | 2027-07-21 or later |
    | `gemini-3.1-flash-lite` | 2026-05-07 | 2027-05-07 or later |
    | `gemini-3.8-flash` | 2026-09-02 | 2027-09-02 or later |
    | `gemini-3.5-flash` | 2026-05-19 | 2027-05-19 or later |
    | `gemini-4-argon` | 2026-10-13 | 2027-10-13 or later |

    `gemini-4-argon` is listed as GA, but its tier class (Pro or otherwise) is not labelled.
  - **Short-term** models (kept only until a replacement exists; at least 45 days' notice): `gemini-3.6-flash`, `gemini-3.7-flash`, `gemini-4-carbon`, `gemini-4-hydrogen`. **Not allowed** (§6 rules).
  - **Preview** models, which must not receive PHI: `gemini-3.1-pro-preview`, `gemini-3-flash-preview`. There is **no GA Gemini 3.x Pro** model.
  - `gemini-2.5-pro`, `gemini-2.5-flash` and `gemini-2.5-flash-lite` show a retirement date of **2026-10-20**, which has passed, yet the pages still list them as GA. **Not allowed:** treat them as retired.
- **Endpoints and data residency** (https://docs.cloud.google.com/gemini-enterprise-agent-platform/resources/data-residency.md.txt, https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/locations):
  - **Global endpoint:** "may be processed in any Google Cloud location around the world, and therefore don't provide any data residency guarantees." Google's advice: don't use it if you have ML processing requirements. **We never use it.**
  - **US multi-region endpoint** `us`, host `aiplatform.us.rep.googleapis.com`: "machine learning processing of Customer Data by the service stays within a specific jurisdictional boundary." The data-residency table marks the models above (except `gemini-4-argon`, which was not found in it) as "Yes" for the US multi-region.
  - **US regional endpoints** (e.g. `us-central1`, `us-east4`): processed within the US.
  - **Verify:** per-model availability for each endpoint, because the locations table could not be read in text form (check it in a browser).
- **Data governance** (https://docs.cloud.google.com/vertex-ai/generative-ai/docs/data-governance):
  - **Training:** "Google won't use your data to train or fine-tune any AI/ML models without your prior permission or instruction." This covers GA and pre-GA models.
  - **Implicit caching:** in-memory and **durable**, both on by default for supported models, deleted within 24 hours. **Durable caching does not support CMEK.** It is controlled per project through `projects/PROJECT_ID/cacheConfig`, which applies to all regions and needs `roles/aiplatform.admin`:
    - all caching off: `{"disableCache": true}`;
    - in-memory only: `{"retentionConfig": {"retentionType": "EPHEMERAL"}, "disableCache": false}`.
  - **Request-response logging** (to BigQuery): off by default; "to achieve zero data retention, do not enable this feature."
  - **Grounding with Google Search:** logs stored up to 3 days, and this "can't be disabled". Grounding with Google Maps: 30 days.
  - **Abuse monitoring:** Google may log prompts to detect abuse (Cloud Terms §4.3). Some "Advanced AI" features add logging. **Verify with the compliance advisor** what applies to our account under the BAA.
- **HIPAA best practice** (https://docs.cloud.google.com/docs/security/compliance/hipaa): "Don't use pre-GA offerings… with PHI, unless expressly noted otherwise."
- **Voice alternative:** the Live API (`gemini-3.8-live`, GA) does speech-to-speech in one model. Our plan uses the cascade STT → LLM → TTS (plan §4.4), so the Live API is out of scope here. It is noted for the P3-01 latency spike to consider.
- **Where routing lives:** P2-06 routes requests; P2-03 implements the provider. Both read the model IDs from config defined here.

## 4. Scope
**In scope**
- Selection rules and candidate list (§6).
- A spike in `<prefix>-dev`, with **synthetic data only**:
  - latency (time to first token, total) per candidate and endpoint;
  - JSON-schema validity and field accuracy on an extraction set;
  - quality of short replies;
  - cost per typical turn.
- Confirming each chosen model is GA, has a 12-month lifecycle, is available on the US endpoint and is covered under the HIPAA entry.
- Setting and verifying `cacheConfig` in dev, staging and prod; confirming request-response logging is off; recording the "no Google Search/Maps grounding" rule.
- The ADR, the config keys, and the model lifecycle runbook.

**Out of scope** (and which task covers it)
- The provider interface, streaming and cancel → P2-03
- The routing rules and their tests → P2-06
- The extraction prompt and JSON schema in production → P2-05
- The full eval harness and regression on every model change → P5-01 (this spike's set becomes one of its suites)
- Voice architecture (cascade vs Live API) → P3-01
- Quotas and Provisioned Throughput → P5-06 / P3-15 (note the spike's findings)

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P0-06 Guardrails (approved spec) | `aiplatform.googleapis.com` allowed; Gemini Developer API denied; US-only locations | Run the spike in `<prefix>-dev` as soon as the API is allowed there. It uses only synthetic data, so the PHI gate doesn't apply. If P0-06 isn't applied yet, still use only the `us` or a `us-*` endpoint and record it. |
| P0-05 Foundation (approved spec) | Projects; the covered-products entry name | Use the entry names in §3; P0-05 confirms them. |
| P0-04 Flow designs (approved spec, soft) | Slots and intents to extract | Use the P0-04 slot list for the extraction set (§6). |
| Compliance advisor (external) | Abuse monitoring and caching setting confirmation | Apply the Proposed setting now; record the advisor's answer when it comes. |

## 6. Interface contract

### Selection rules (Proposed)
A model may be used for any tier only if **all** of the following hold:
1. It is listed as **GA** with a **12-month** lifecycle (not "short-term availability", not preview or experimental), and its retirement date is at least 6 months after the planned pilot start.
2. It is available on the **US multi-region `us` endpoint** (preferred) or a **US regional** endpoint, and appears with "Yes" for the US in the data-residency table.
3. It is served under the HIPAA covered entry recorded by P0-05.
4. It doesn't require a feature we forbid (grounding with Google Search/Maps, request-response logging, durable caching).
5. It passes the spike thresholds below for its tier.

### Candidates and proposed choice
| Tier (`model_tier`) | Used for (plan §4.3) | Proposed primary | Fallback |
|---|---|---|---|
| `lite` | Greetings, acknowledgements, confirmations that aren't templates | `gemini-3.5-flash-lite` | `gemini-3.1-flash-lite` |
| `flash` | Intent and slot extraction (JSON), normal replies | `gemini-3.8-flash` | `gemini-3.5-flash` |
| `pro` | Ambiguous, multi-part, complaint conversations | `gemini-4-argon` **if** rules 1–3 are verified for it | `gemini-3.8-flash` with a higher thinking budget (**Verify** parameter name in the SDK) |

If `gemini-4-argon` fails any rule or threshold, the `pro` tier uses the fallback, and the ADR says so.

### Spike thresholds (Proposed; per tier)
| Metric | `lite` | `flash` | `pro` |
|---|---|---|---|
| Time to first token p50 / p95 from Cloud Run-equivalent client in `us-central1` (Cloud Shell or a dev Cloud Run job) | ≤ 300 / 600 ms | ≤ 450 / 900 ms | ≤ 1,000 / 2,000 ms |
| JSON output valid against the schema (with `response_schema`) | n/a | 100% | 100% |
| Field accuracy on the extraction set | n/a | ≥ 95% | ≥ 95% |
| Reply rubric pass (short, polite, no medical advice, no invented facts) | ≥ 90% | ≥ 95% | ≥ 95% |

These come from the voice budget in plan §4.4 (LLM first token within the ~1.5 s voice-to-voice target). P3-15 tunes them later.

### Spike eval set (`evals/spike/p0-13/`)
- `extraction.yaml`: 30 synthetic utterances with expected JSON. They cover:
  - intents: book, reschedule, cancel, check, FAQ, emergency, callback;
  - slots: name, DOB in several spoken forms, phone, preferred day and time, reason;
  - hard cases: corrections ("no, Tuesday"), two intents in one turn, spelled names.
- `replies.yaml`: 20 situations with a rubric. Some include a demand for medical advice, which must be refused, per P0-03.
- `complex.yaml`: 10 multi-part or complaint conversations, for `pro`.
- All names, DOBs and phone numbers are fictional (`555-01xx`).
- The schema used is the P0-04 slot set. P2-05 owns the production schema later.

### Config keys (P1-08 config; P2-03 reads them)
| Env var | Example value | Meaning |
|---|---|---|
| `VERTEX_PROJECT` | `<prefix>-prod` | Project ID |
| `VERTEX_LOCATION` | `us` | Endpoint location: `us` or a `us-*` region; **`global` is rejected at startup** |
| `GEMINI_MODEL_LITE` | `gemini-3.5-flash-lite` | `lite` tier |
| `GEMINI_MODEL_FLASH` | `gemini-3.8-flash` | `flash` tier |
| `GEMINI_MODEL_PRO` | `gemini-4-argon` | `pro` tier |
| `GEMINI_ALLOWED_MODELS` | comma list | Startup check: every `GEMINI_MODEL_*` must be in this list, which is the ADR's approved list |

Startup validation (P2-03 implements; Proposed): refuse to start if:
- `VERTEX_LOCATION` is `global` or not `us`/`us-*`;
- a model ID contains `preview`, `exp` or `latest`;
- a model ID is not in `GEMINI_ALLOWED_MODELS`.

Never pass grounding tools (`google_search`, `google_maps`) in requests; P2-03 asserts this.

### Project data settings (applied in dev, staging, prod)
| Setting | Value | How to check |
|---|---|---|
| `cacheConfig` | `retentionType: EPHEMERAL`, `disableCache: false` (in-memory only; durable cache off). If the advisor prefers, `disableCache: true`. | `GET https://us-central1-aiplatform.googleapis.com/v1/projects/PROJECT_ID/cacheConfig` (**Verify** the host for the `us` multi-region) |
| Request-response logging | Off for every model | Console / API per model: not enabled |
| Grounding with Google Search / Maps | Not used | Code rule + review (P2-03) |
| Abuse-monitoring logging | Record what applies (advisor) | ADR note |

### ADR (`docs/adr/0001-gemini-models.md`)
The ADR contains:
- context;
- the selection rules;
- the candidates table with the spike results;
- the decision per tier, with the exact model ID, endpoint, release and retirement dates, and the covered entry;
- the data settings;
- the rejected options and why (2.5 models retired, 3.1 Pro preview, short-term models, global endpoint);
- consequences;
- review triggers.

The ADR status is "Accepted" after the tech lead and compliance owner approve it.

### Lifecycle runbook (`docs/runbooks/gemini-model-lifecycle.md`)
- A calendar reminder 90 days before each chosen model's retirement date, owned by the tech lead.
- Every month: check the model-versions page for new retirement dates or new GA replacements.
- **Changing a model:**
  1. new ADR revision;
  2. run the P5-01 eval suites, which must pass;
  3. update `GEMINI_ALLOWED_MODELS` and `GEMINI_MODEL_*`;
  4. deploy to staging, run the regression, then prod.

  A model is never changed by editing code.
- If Google's pages show an inconsistency (a retired model still listed as GA), treat the model as retired.

## 7. Implementation guide
1. **Re-read the model-versions, models, data-residency and locations pages** on the day. Update the §3 table in the ADR draft, and open the locations table in a browser to confirm `us` availability per candidate.
2. **Confirm coverage:** with P0-05's covered-products snapshot, write down which HIPAA entry covers Gemini calls on `aiplatform.googleapis.com`, and that no footnote excludes our features.
3. **Apply the data settings** in `<prefix>-dev` first, then staging and prod:
   - PATCH `cacheConfig`, then GET it to check;
   - confirm request-response logging is not enabled.

   Save the command output, with project IDs and no secrets, in the PR.
4. **Write the spike sets** (§6) with synthetic data only.
5. **Write the spike script** `evals/spike/p0-13/run_spike.py`:
   - Google Gen AI SDK `google-genai` with `vertexai=True`, `location` from the CLI (**Verify** the current SDK and parameters);
   - streaming, measuring time to first token and total time;
   - `response_schema` for extraction.

   Per candidate × endpoint (`us`, `us-central1`), run each set 3 times. Output a CSV of IDs, timings, scores and token counts, with no prompt text, in `evals/spike/p0-13/results/`.
6. **Score:**
   - extraction is scored automatically (exact field match after normalization);
   - replies are scored by two team members against the rubric.

   Compute the cost per typical turn from token counts and the current price list (**Verify**).
7. **Decide** per tier using the rules and thresholds. Write the ADR, then get approval from the tech lead and the compliance owner.
8. **Write the lifecycle runbook** and set the calendar reminders.
9. **Notify:**
   - P2-03: config keys, startup checks, no grounding, the SDK used;
   - P2-06: tiers and measured latencies;
   - P2-05: extraction results and failure patterns;
   - P3-01 and P3-15: latency numbers, the Live API note;
   - P5-01: the spike sets, to reuse as a suite;
   - P0-10: the Google Cloud row (no new vendor) and the `allowed_services.yaml` note;
   - P0-11: R13 (training, caching) answered;
   - P0-14: the endpoint and data settings for the data-flow diagram.

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| No candidate for `pro` meets the rules | `pro` uses the `flash` model with a higher thinking budget; the ADR says so. Never a preview model. |
| A candidate isn't available on `us` but is on `us-central1` | Use the regional endpoint for that tier; `VERTEX_LOCATION` may then be set per tier (`VERTEX_LOCATION_PRO`). Record it in the ADR. |
| A candidate is only on the global endpoint | Rejected. |
| A model passes all rules but misses a latency threshold | Prefer the fallback if it passes. If none passes, record it as a risk for P3-15 and choose the best measured model. |
| Google announces a retirement date earlier than 6 months after the pilot start | Choose the newer GA replacement now and record the reason. |
| 429 (resource exhausted) during the spike | Record it. Note for P5-06 that quota or Provisioned Throughput may be needed. Don't switch to the global endpoint to avoid 429s. |
| The advisor says in-memory caching is also not acceptable | Set `disableCache: true`, re-measure latency, and update the ADR. |
| Someone wants to use Google Search grounding for FAQs | Not allowed. FAQs come from clinic config (plan §4.3). |
| A developer uses an AI Studio API key "just for the spike" | Not allowed (plan §3.3). The Gemini Developer API is denied by P0-06, so the request fails; use Vertex AI in `<prefix>-dev`. |

## 9. Security, HIPAA and PHI
- **No PHI is handled in this task.** The spike uses fictional data only, in `<prefix>-dev`.
- **This task sets the rules that make Gemini safe for PHI later:**
  - GA models only, under the BAA-covered entry;
  - US endpoint only;
  - no grounding with Search or Maps;
  - no request-response logging;
  - durable cache off (it doesn't support CMEK).
- The results CSV has no prompt or response text, only IDs, timings and scores.
- **Audit:** the ADR and PR hold the evidence: config GET outputs, page snapshots with dates, and approvals. Changes to `cacheConfig` appear in Cloud Audit Logs (admin activity).

## 10. Testing
- The spike script runs against each candidate and produces the results CSV. A reviewer re-runs one set for one model and gets similar numbers (±20% latency).
- `GET cacheConfig` in each project shows the chosen setting.
- Request-response logging shows not enabled for each chosen model in each project.
- A config-check unit test (delivered to P2-03 as a spec, implemented there): `VERTEX_LOCATION=global` → startup error; a model with `preview` → startup error; a model not in `GEMINI_ALLOWED_MODELS` → startup error.

## 11. Acceptance criteria
- [ ] `docs/adr/0001-gemini-models.md` is accepted, with a model ID, endpoint, release/retirement dates and HIPAA entry for each tier
- [ ] Every chosen model is GA with a 12-month lifecycle, is available on a US endpoint, and is covered; none is preview, short-term or a 2.5 model
- [ ] Spike results (CSV + summary) are committed, and each chosen model meets its tier thresholds, or the exception is written in the ADR
- [ ] `cacheConfig` is set and verified in dev, staging and prod; request-response logging is off; the no-grounding rule is documented
- [ ] Config keys and startup checks are specified and handed to P2-03
- [ ] `docs/runbooks/gemini-model-lifecycle.md` exists, and retirement reminders are set
- [ ] The P2-03, P2-05, P2-06, P3-01, P3-15, P5-01, P0-10, P0-11 and P0-14 issues are notified

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI: not applicable (spike); the spike script and sets are committed for P5-01 to reuse
- [ ] PR reviewed (HIPAA review if labelled `phi`): reviewed by the tech lead and compliance owner; no `phi` label (synthetic data only)
- [ ] No PHI in logs: results contain no prompt text
- [ ] Docs / README updated: ADR, runbook, `evals/spike/p0-13/README.md`

## 13. Hand-off
| Task | Can rely on |
|---|---|
| P2-03 LLM provider | Config keys, approved model list, US endpoint, startup checks, no grounding, SDK choice |
| P2-05 Extraction | Measured accuracy and failure patterns per model |
| P2-06 Model router | Tier → model mapping and measured latencies |
| P3-01 / P3-15 Voice latency | First-token latencies; note on the Live API alternative |
| P5-01 Eval harness | The spike sets as a starting suite; model-change procedure |
| P0-10 / P0-11 / P0-14 | Data settings and endpoint for the vendor row, risk R13 and the data-flow diagram |

## 14. Open questions
| Question | Owner | Needed by |
|---|---|---|
| Is `gemini-4-argon` a Pro-class model, available on `us`, and in the data-residency table? | Tech lead (spike step 1) | Step 7 |
| Is in-memory implicit caching acceptable for PHI, or should all caching be off? | Compliance advisor | Step 3 |
| What abuse-monitoring logging applies to our account under the BAA, and can it be turned off? | Compliance advisor / Google account team | Before real PHI |
| When is the pilot planned to start (for the 6-month retirement rule)? | Project sponsor | Step 7 |

## 15. References
- Plan §4.3, §3.3, §3.2, §4.4, §1 principle 5
- Model versions and lifecycle: https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/model-versions
- Models: https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models
- Locations: https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/locations
- Data residency: https://docs.cloud.google.com/gemini-enterprise-agent-platform/resources/data-residency.md.txt
- Data governance and caching: https://docs.cloud.google.com/vertex-ai/generative-ai/docs/data-governance
- HIPAA covered products: https://docs.cloud.google.com/docs/security/compliance/hipaa
- Migrate to the latest models: https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/migrate.md.txt (not yet read; Verify)
- Related tasks: P0-03, P0-04, P0-05, P0-06, P0-10, P0-11, P0-14, P1-08, P2-03, P2-05, P2-06, P3-01, P3-15, P5-01, P5-06
