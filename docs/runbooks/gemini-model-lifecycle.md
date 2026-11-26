# Runbook: Gemini model lifecycle

Owner: **Riley Tech** (tech lead). Decision record: [ADR 0001](../adr/0001-gemini-models.md). Spec: `openspec/specs/gemini-models/spec.md`.

## 1. Retirement reminders
Each reminder fires **90 days before** the earliest listed retirement date. The dates are minimums ("or later", sources G1).

There is no shared team calendar yet. Until one exists, the tech lead keeps these in their own calendar and this table is the record. Add a row whenever a model is approved.

| Model | Tier | Retirement (minimum) | Reminder | Set in calendar |
|---|---|---|---|---|
| `gemini-3.1-flash-lite` | `lite` fallback | 2027-05-07 | 2027-02-06 | Pending (tech lead) |
| `gemini-3.5-flash` | `flash` fallback | 2027-05-19 | 2027-02-18 | Pending (tech lead) |
| `gemini-3.5-flash-lite` | `lite` | 2027-07-21 | 2027-04-22 | Pending (tech lead) |
| `gemini-3.8-flash` | `flash`, `pro` fallback | 2027-09-02 | 2027-06-04 | Pending (tech lead) |
| `gemini-4-argon` | `pro` | 2027-10-13 | 2027-07-15 | Pending (tech lead) |

## 2. Monthly check (first working day of each month)
1. Open the HTML model-versions page (not the `.md.txt` copy, which was stale on 2026-11-26): https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/model-versions
2. For each model in `GEMINI_ALLOWED_MODELS`:
   - Has the retirement date changed?
   - Has it moved to short-term?
   - Is there a newer GA replacement?
3. Check that each chosen model's page still lists the `us` multi-region and "Supported" in the data-residency table.
4. Check the HIPAA covered-products page for changes to "Gemini Enterprise Agent Platform" / "Generative AI on Agent Platform".
5. Record the date and the result (no change, or what changed) at the bottom of this file. If something changed, start §3.

**A model whose retirement date has passed is treated as retired, even if a page still lists it as GA.** Remove it from `GEMINI_ALLOWED_MODELS`.

## 3. Changing a model
A model is **never** changed by editing code.
1. **ADR:** write a new revision of ADR 0001. Include the candidate's lifecycle, `us` availability, residency, the covered entry and the 6-month rule against the pilot date.
2. **Spike:** run `evals/spike/p0-13/run_spike.py --backend vertex --location us` for the candidate. From P5-01 onwards, run the full eval suites instead. They must pass the tier thresholds.
3. **Config:** add the model to `GEMINI_ALLOWED_MODELS`, then set `GEMINI_MODEL_<TIER>`.
4. **Deploy:** staging first, run the regression there, then prod. Keep the old model in the allowed list until prod is confirmed, then remove it.
5. **Records:** add a DECISIONS row, and update the reminder table in §1.

## 4. Developer API rules
- Allowed only with `APP_ENV=local` and synthetic data. The startup check enforces this.
- The API key lives only in the git-ignored `.env`.
  - If it leaks, delete it in Google AI Studio, create a new one, and record a security event.
- The free tier may be read by human reviewers (sources G11).
  - Never paste anything real into it: not even "test" data copied from somewhere real.
- Developer API latency numbers are never used to accept a model for production.

## 5. Check log
| Date | By | Result |
|---|---|---|
| 2026-11-26 | Riley Tech (P0-13) | Pages read for ADR 0001; `gemini-4-neon` newly listed as short-term (not allowed) |
