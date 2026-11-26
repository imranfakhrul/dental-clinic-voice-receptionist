# P0-13 Gemini model spike

Measures each candidate model per routing tier (ADR [0001](../../../docs/adr/0001-gemini-models.md)):
- latency: time to first token (TTFT) and total;
- JSON validity and field accuracy on extraction;
- simple automatic checks on short replies.

**Synthetic data only.** Fictional names; phones `555-01xx`.

| File | What |
|---|---|
| `extraction.yaml` | 30 single turns: intents (book, reschedule, cancel, check, FAQ, emergency, callback), name, DOB in spoken forms, phone, day and time, reason; corrections, two intents, spelled names |
| `replies.yaml` | 20 situations for the next receptionist message, including requests for medical advice (must be refused, P0-03) |
| `complex.yaml` | 10 multi-part or complaint conversations, for the `pro` tier |
| `schema.json` | The spike's JSON schema: a small subset of the P0-04 slots. P2-05 owns the production schema |
| `run_spike.py` | The runner: backends `fake` (offline), `developer` (Gemini Developer API) and `vertex`. Live backends use the Google Gen AI SDK `google-genai` (ADR 0001 §5.2), which handles API keys, Vertex login, streaming and the JSON schema |
| `test_run_spike.py` | Offline tests (`pytest evals/spike/p0-13/`) |
| `requirements.txt` | Pinned packages: `google-genai` (live backends only), `pyyaml`, `pytest` |
| `results/` | `<run>.csv` and `<run>-summary.md`: IDs, timings, token counts and scores only, **never prompt or response text** |

## Two ways to call Gemini
| Backend | Key or login | Use for |
|---|---|---|
| `developer` | **Normal Gemini API key** from Google AI Studio (`GEMINI_API_KEY` in `.env`) | Local development and tests now; synthetic data only; needs `APP_ENV=local` |
| `vertex` | Google Cloud login (`gcloud auth application-default login`); no key | Production and anything with PHI; `us` endpoint; needs billing |

Both go through the same SDK (`google-genai`); only `--backend` and the `.env` settings change.

## Run
One-time setup (Python 3.12+), from the repo root:
```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r evals/spike/p0-13/requirements.txt
```

```bash
# offline check, no network, no API key
python3 evals/spike/p0-13/run_spike.py --backend fake --runs 1

# Gemini Developer API (local only; key in the git-ignored .env)
set -a; . ./.env; set +a                      # APP_ENV=local, GEMINI_API_KEY=...
python3 evals/spike/p0-13/run_spike.py --backend developer --runs 1 \
  --models gemini-3.5-flash-lite gemini-3.1-flash-lite gemini-3.8-flash

# Vertex AI (needs billing and the API enabled in the project; not available yet)
gcloud auth application-default login
python3 evals/spike/p0-13/run_spike.py --backend vertex --project dai-rcpt-dev --location us
```

The runner refuses to start in these cases:
- `developer` without `APP_ENV=local`;
- `vertex` with a location other than `us` or `us-*`;
- any model ID containing `preview`, `exp` or `latest`;
- any model outside `GEMINI_ALLOWED_MODELS`, when that variable is set.

## What the numbers mean
- **TTFT** is measured with streaming. It includes the model's thinking time, which is what a voice turn waits for.
- **Field accuracy:** only the fields listed in `expect` are scored. A `null` in `expect` means the model must not invent a value.
- **Reply proxy:**
  - checks: a word limit, forbidden phrases (e.g. drug names) and required phrases;
  - two team members also score each reply against the rubric (short, polite, no medical advice, no invented facts) in the `human_pass` column.
- **Cost per call** uses Vertex `us` (non-global) prices (sources G9), even for Developer API runs, so tiers can be compared.
- **Developer API vs Vertex:**
  - Developer API numbers come from a laptop over the public internet. They are indicative for **quality**, but not reliable for **latency**.
  - The ADR choice is for Vertex `us`, and P3-14 re-measures there.
  - `gemini-4-argon` has **no free tier** on the Developer API. On the free tier, the `pro` tier is measured with its fallback, `gemini-3.8-flash` with `thinking_level=HIGH`.
- Free-tier data can be read by Google's human reviewers (sources G11). That is fine only because every item is synthetic.

## Reuse
P5-01 can import these three sets as a starting suite, after converting them to its format.
