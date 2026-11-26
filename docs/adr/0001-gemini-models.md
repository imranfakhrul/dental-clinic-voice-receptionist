# ADR 0001: Gemini models per routing tier

| | |
|---|---|
| Status | **Proposed** (2026-11-26). Becomes Accepted after the conditions in §9 |
| Task | P0-13 (issue #14) · DECISIONS #65–#69, #315–#317 |
| Deciders | Riley Tech (tech lead), Sam Comply (compliance advisor) |
| Facts | Google pages read on 2026-11-26, sources [G1–G12](../compliance/sources/README.md#p0-13-gemini-models-checked-2026-11-26) |
| Spike | [`evals/spike/p0-13/`](../../evals/spike/p0-13/README.md) |

## 1. Context
The plan routes each turn to one of three Gemini tiers (plan §4.3). P2-03 implements the provider and the routing (it absorbed P2-06).

| Tier | Used for |
|---|---|
| `lite` | Greetings, acknowledgements, short confirmations |
| `flash` | Intent and slot extraction in JSON, normal replies |
| `pro` | Ambiguous, multi-part and complaint conversations |

**Rules for PHI (CLAUDE.md 5–6, plan §3.3):**
- Gemini only through Vertex AI in a project covered by the BAA;
- GA models only;
- US processing only;
- no feature that logs or stores prompts.

**Constraints today:**
- No Google Cloud project has billing (DECISIONS #293).
- The trial credit can't pay for Vertex AI.
- Hosting stays local-first (DECISIONS #302).

So Vertex AI can't be called yet. The user chose to keep **two backends**: Vertex AI for production and any PHI, and the Gemini Developer API locally with synthetic data (§5).

## 2. Selection rules (DECISIONS #65)
A model may serve a tier only if **all** of these hold:
1. **GA with a 12-month lifecycle** (G1). Not short-term, preview or experimental. Its retirement date is at least **6 months after the pilot start**.
2. **Available and processed on the US multi-region `us`** (G2–G6). Shown "Supported" for the US multi-region in the data-residency table.
3. **Served under the HIPAA covered entries** "Gemini Enterprise Agent Platform" / "Generative AI on Agent Platform" (G8). P0-05 records the covered-products snapshot.
4. **Doesn't need a forbidden feature** (§6).
5. **Passes the spike thresholds** for its tier (§4).

If a retirement date has passed, the model counts as retired even if a page still lists it as GA.

## 3. Candidates (pages of 2026-11-26)
| Model | Lifecycle | Released | Retirement (minimum) | US multi-region | US regional endpoint | Thinking levels | Implicit caching | Vertex `us` price per 1M in / out | Developer API free tier |
|---|---|---|---|---|---|---|---|---|---|
| `gemini-3.5-flash-lite` | GA, 12 months | 2026-07-21 | 2027-07-21 or later | Yes | **No** | MINIMAL–HIGH | In-memory only | $0.33 / $2.75 | Yes |
| `gemini-3.1-flash-lite` | GA, 12 months | 2026-05-07 | 2027-05-07 or later | Yes | No | (Verify) | (Verify) | $0.275 / $1.65 | Yes |
| `gemini-3.8-flash` | GA, 12 months | 2026-09-02 | 2027-09-02 or later | Yes | **No** | LOW–HIGH (no MINIMAL) | In-memory **and durable** | $0.825 / $4.125 to 2026-12-31, then $1.65 / $8.25 | Yes |
| `gemini-3.5-flash` | GA, 12 months | 2026-05-19 | 2027-05-19 or later | Yes | No | (Verify) | (Verify) | $1.65 / $9.90 | (not listed) |
| `gemini-4-argon` | GA, 12 months ("frontier model") | 2026-10-13 | 2027-10-13 or later | Yes | **No** | LOW, MEDIUM (default), HIGH | In-memory and **durable on by default** | $2.20 / $11.00 to 2026-11-30, then $4.40 / $22.00 | **No** (paid only) |

**Rejected:**

| Option | Why |
|---|---|
| `gemini-2.5-pro`, `-flash`, `-flash-lite` | Retirement 2026-10-20 has passed (G1); treated as retired |
| `gemini-3.1-pro-preview`, `gemini-3-flash-preview`, any `-preview`/`-exp`/`-latest` ID | Pre-GA: no PHI (G8) |
| `gemini-4-neon`, `-hydrogen`, `-carbon`, `gemini-3.6-flash`, `gemini-3.7-flash`, the `-cyber` variants | Short-term availability (45 days' notice), or allowlist only |
| The **global** endpoint | "May be processed in any Google Cloud location around the world" (G5) |
| US **regional** endpoints (`us-central1` and others) for these models | The model pages list only the `us` multi-region for the US (G2–G4). `VERTEX_LOCATION` is therefore **`us`**. A `us-*` region is allowed by config only for a future model that is offered there |
| `gemini-3.8-live` (Live API) | Speech-to-speech; the voice architecture is P3-01's decision (DECISIONS #69) |

## 4. Spike
- **Set:** 30 extraction, 20 reply and 10 complex items. Synthetic; built on the P0-04 slots.
- **Thresholds** (task spec §6):

  | Tier | TTFT p50 / p95 | JSON valid | Field accuracy | Reply pass |
  |---|---|---|---|---|
  | `lite` | ≤ 300 / 600 ms | - | - | ≥ 90% |
  | `flash` | ≤ 450 / 900 ms | 100% | ≥ 95% | ≥ 95% |
  | `pro` | ≤ 1,000 / 2,000 ms | 100% | ≥ 95% | ≥ 95% |
- **Results:**
  - **Vertex `us`:** pending (no billing).
  - **Developer API:** results go in `evals/spike/p0-13/results/` and §8. These are indicative: latency from a laptop isn't Vertex latency.

## 5. Decision
### 5.1 Models (Vertex, `VERTEX_LOCATION=us`)
| Tier | Primary | Thinking level | Fallback | Retirement rule (6 months before) holds if the pilot starts by |
|---|---|---|---|---|
| `lite` | `gemini-3.5-flash-lite` | `MINIMAL` | `gemini-3.1-flash-lite` | 2027-01-21 (fallback: 2026-11-07, already passed) |
| `flash` | `gemini-3.8-flash` | `LOW` | `gemini-3.5-flash` | 2027-03-02 (fallback: 2026-11-19, already passed) |
| `pro` | `gemini-4-argon` | `MEDIUM` | `gemini-3.8-flash` with `thinking_level=HIGH` | 2027-04-13 |

- This **confirms** DECISIONS #66. The `pro` tier's open question ("is argon verified?") is answered:
  - GA;
  - `us` multi-region;
  - in the data-residency table;
  - described as Google's frontier model.
- The "thinking budget" parameter is **`thinking_level`**:
  - `MINIMAL` isn't accepted by 3.8 Flash or 4 Argon (G2, G3);
  - `thinking_budget` returns 400 on 4 Argon.
- **Pilot date condition:** the pilot start isn't set yet.
  - The retirement dates are **minimums** ("or later").
  - The lifecycle runbook re-checks them monthly.
  - If the pilot is later than the dates in the table, the then-current GA replacement is chosen through a new ADR revision, and the spike is re-run.
  - The fallbacks already fail the 6-month rule for any future pilot. They stay listed only as emergency stand-ins until a newer GA model replaces them.

### 5.2 Two backends, one config
| Env var | Value | Rule |
|---|---|---|
| `APP_ENV` | `local` / `dev` / `staging` / `prod` | - |
| `GEMINI_BACKEND` | `vertex` or `developer` | `developer` only when `APP_ENV=local` |
| `VERTEX_PROJECT` | `dai-rcpt-<env>` | - |
| `VERTEX_LOCATION` | `us` | `us` or `us-*` only; **`global` rejected** |
| `GEMINI_API_KEY` | Google AI Studio key | Only in the git-ignored local `.env`; never in a cloud environment |
| `GEMINI_MODEL_LITE` / `_FLASH` / `_PRO` | §5.1 | Each must be in `GEMINI_ALLOWED_MODELS` |
| `GEMINI_ALLOWED_MODELS` | `gemini-3.5-flash-lite,gemini-3.1-flash-lite,gemini-3.8-flash,gemini-3.5-flash,gemini-4-argon` | The approved list (this ADR) |

**Startup checks** (P2-03 implements them; the spike runner already enforces them, `run_spike.py check_config`). Refuse to start when:
- `GEMINI_BACKEND=developer` and `APP_ENV` isn't `local`;
- `VERTEX_LOCATION` is `global` or not `us`/`us-*`;
- a model ID contains `preview`, `exp` or `latest`;
- a model isn't in `GEMINI_ALLOWED_MODELS`.

**Request rules (P2-03):**
- Use the **GenerateContent** API.
- If the Interactions API is ever used, always send `store=false`: it stores conversation state by default (G7).
- Never send grounding tools (`google_search`, `google_maps`, other web grounding). The provider rejects them before sending.
- Set `thinking_level` per tier from config.

**The Developer API is never a fallback for Vertex in production.** No BAA, no US-processing statement, and free-tier data may be reviewed by humans (G10, G11).

## 6. Data settings (all Vertex projects: dev, staging, prod)
| Setting | Value | Status |
|---|---|---|
| `cacheConfig` | `{"disableCache": false, "retentionConfig": {"retentionType": "EPHEMERAL"}}`: durable caching off, in-memory on. All caching off (`disableCache: true`) if the advisor requires | **Pending:** Vertex not enabled in any project. Needed because 3.8 Flash and 4 Argon use durable caching, and 4 Argon has it **on by default** (G2, G3). Durable caching doesn't support CMEK (G7) |
| Request-response logging (BigQuery) | Never enabled | Pending check per model and project |
| Grounding with Google Search / Maps | Never used | Rule in P2-03 (§5.2) |
| Interactions API `store` | `false`, or don't use the Interactions API | Rule in P2-03 |
| Abuse-monitoring prompt logging | Google may log prompts under Cloud Terms §4.3; "Advanced AI" models or features may add logging (G7) | **Open:** advisor and Google account team (R13). Ask whether 4 Argon is covered by the Advanced AI Safety Addendum |

**Commands, per project** (run by the tech lead when Vertex is enabled). `cacheConfig` is project-wide; Google's examples use the `us-central1` host (G7):

```bash
P=dai-rcpt-dev   # then staging, prod
curl -X PATCH -H "Authorization: Bearer $(gcloud auth application-default print-access-token)" \
  -H "Content-Type: application/json" \
  https://us-central1-aiplatform.googleapis.com/v1/projects/$P/cacheConfig \
  -d '{"name": "projects/'$P'/cacheConfig", "disableCache": false, "retentionConfig": {"retentionType": "EPHEMERAL"}}'
curl -H "Authorization: Bearer $(gcloud auth application-default print-access-token)" \
  https://us-central1-aiplatform.googleapis.com/v1/projects/$P/cacheConfig
# expect: "retentionConfig": {"retentionType": "EPHEMERAL"}
```

Record the GET output, with project ID and no token, in this ADR when run.

## 7. Consequences
- **Endpoint:** everything uses the `us` multi-region endpoint (`aiplatform.us.rep.googleapis.com`, G6). There is no single-region option, so latency is measured from `us` (P3-14).
- **Cost per turn**, rough, from the Vertex `us` prices after promotions end, with thinking tokens billed as output:

  | Tier | Assumed tokens per turn | Cost per turn |
  |---|---|---|
  | lite | 200 in / 30 out | about $0.0002 |
  | flash | 300 in / 100–300 out | about $0.001–0.003 |
  | pro | 600 in / 200–500 out | about $0.005–0.014 |

  The spike's token counts replace these estimates.
- **Model changes are config changes**, under the lifecycle runbook. Code never names a model.
- **Developer API use leaves no PHI risk** only if the startup check and the "synthetic only" rule hold. The vendor matrix lists it as `phi: no`.
- **R13** (vendor keeps or uses data) depends on the `cacheConfig` and on the advisor's abuse-monitoring answer. It stays a planned control until both are done.

## 8. Developer API measurements
**Pending: deferred by the user** (2026-11-26). The runner is ready and tested offline (17 tests). To run it later:
1. Create a key in Google AI Studio and put it in `GEMINI_API_KEY` in the git-ignored `.env` (`APP_ENV=local`, `GEMINI_BACKEND=developer` are already set).
2. Install the pinned packages in a virtualenv: `pip install -r evals/spike/p0-13/requirements.txt`.
3. Run the command in [the spike README](../../evals/spike/p0-13/README.md#run) with `--runs 1` and the three free-tier models.
4. Paste the summary table from `results/<run>-summary.md` here, labelled "Developer API, indicative only".

## 9. Review triggers and what is needed for Accepted
**Accepted when:**
- the Vertex `us` spike is run and each primary meets its thresholds, or the exception is written here;
- `cacheConfig` is set and verified in dev, staging and prod;
- the advisor has answered on in-memory caching and abuse monitoring;
- the tech lead and the compliance owner approve.

**Review when:**
- a chosen model gets an earlier retirement date, or a newer GA replacement appears;
- the pilot date is set or moves (§5.1);
- Google changes caching, logging or residency terms;
- the HIPAA covered-products list changes;
- the hosting decision moves us off Google Cloud (DECISIONS #302): the provider choice re-opens;
- P3-14 latency misses its targets.
