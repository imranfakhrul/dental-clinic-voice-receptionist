"""P0-13 Gemini model spike: latency, JSON validity, field accuracy and reply checks per tier.

  python3 evals/spike/p0-13/run_spike.py --backend fake                       # offline, no network
  APP_ENV=local python3 evals/spike/p0-13/run_spike.py --backend developer    # Gemini Developer API (API key)
  python3 evals/spike/p0-13/run_spike.py --backend vertex --project dai-rcpt-dev --location us

Synthetic data only. Writes results/<run>.csv and results/<run>-summary.md with IDs, timings, token counts and
scores only: never prompt or response text. Backend rules (DECISIONS #316): `developer` only with APP_ENV=local;
`vertex` only on `us` or `us-*`. Needs the `google-genai` package for the live backends.
"""

import argparse
import csv
import datetime as dt
import json
import os
import re
import statistics
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

HERE = Path(__file__).resolve().parent
BAD_ID = re.compile(r"preview|exp|latest")

# tier -> list of (model, thinking_level or None, sets). Primary first, then fallback (ADR 0001).
PLAN: dict[str, list[tuple[str, str | None, list[str]]]] = {
    "lite": [("gemini-3.5-flash-lite", "MINIMAL", ["replies"]), ("gemini-3.1-flash-lite", None, ["replies"])],
    "flash": [("gemini-3.8-flash", "LOW", ["extraction", "replies"]),
              ("gemini-3.5-flash", "LOW", ["extraction", "replies"])],
    "pro": [("gemini-4-argon", "MEDIUM", ["complex"]), ("gemini-3.8-flash", "HIGH", ["complex"])],
}
# Vertex non-global prices per 1M tokens (input, output), sources G9; used for cost per turn.
PRICE = {"gemini-3.5-flash-lite": (0.33, 2.75), "gemini-3.1-flash-lite": (0.275, 1.65),
         "gemini-3.8-flash": (1.65, 8.25), "gemini-3.5-flash": (1.65, 9.90), "gemini-4-argon": (4.40, 22.00)}
# Spike thresholds (task spec §6): TTFT p50/p95 ms, JSON valid %, field accuracy %, reply proxy %.
THRESH = {"lite": (300, 600, None, None, 90), "flash": (450, 900, 100, 95, 95), "pro": (1000, 2000, 100, 95, 95)}

SYSTEM_EXTRACT = ("You extract fields for a dental clinic receptionist. Return JSON only, matching the schema. "
                  "Use null for anything the patient did not say. Today is {today}. Day names lower-case; dob "
                  "YYYY-MM-DD (US month/day order); phone as 10 digits. If the patient corrects themselves, use "
                  "the correction. intent is null when the turn only answers the assistant's question. second_intent is a "
                  "different second request in the same turn, else null.")
SYSTEM_REPLY = ("You are the receptionist assistant for Example Dental. Write the next message to the patient in "
                "at most 2 short sentences. Say only what the FACTS allow. Never give medical advice or a "
                "diagnosis. Never invent times, prices or policies.")


class ConfigError(Exception):
    pass


def check_config(backend: str, location: str | None, models: list[str], allowed: list[str] | None,
                 app_env: str | None) -> None:
    """The startup rules P2-03 must implement (spec gemini-models), applied to the spike too."""
    if backend == "developer" and app_env != "local":
        raise ConfigError("the developer backend is allowed only with APP_ENV=local (synthetic data only)")
    if backend == "vertex" and not (location == "us" or (location or "").startswith("us-")):
        raise ConfigError(f"VERTEX_LOCATION must be 'us' or 'us-*', not {location!r}")
    for m in models:
        if BAD_ID.search(m):
            raise ConfigError(f"model {m} is not a GA version ID")
        if allowed is not None and m not in allowed:
            raise ConfigError(f"model {m} is not in GEMINI_ALLOWED_MODELS")


@dataclass
class Call:
    status: str = "ok"
    ttft_ms: int = 0
    total_ms: int = 0
    text: str = ""  # kept in memory for scoring only; never written
    in_tok: int = 0
    out_tok: int = 0
    think_tok: int = 0


@dataclass
class Row:
    run_id: str
    backend: str
    location: str
    tier: str
    model: str
    thinking: str
    set: str
    item: str
    rep: int
    status: str
    ttft_ms: int
    total_ms: int
    in_tok: int
    out_tok: int
    think_tok: int
    json_valid: str = ""
    fields_expected: int = 0
    fields_correct: int = 0
    proxy_pass: str = ""
    human_pass: str = ""
    failed_fields: str = field(default="")  # field NAMES only


# ---------------------------------------------------------------- backends
class FakeBackend:
    """Offline stand-in: answers extraction with the expected fields, replies with a fixed safe sentence."""

    def __init__(self, items: dict[str, dict[str, Any]], wrong: set[str] | None = None) -> None:
        self.items, self.wrong = items, wrong or set()

    def call(self, model: str, thinking: str | None, system: str, prompt: str, schema: dict | None,
             item_id: str) -> Call:
        if schema is not None:
            out = {k: None for k in schema["properties"]} | dict(self.items[item_id].get("expect", {}))
            if item_id in self.wrong:
                out["intent"] = "other"
            text = json.dumps(out)
        else:
            text = "Thanks for reaching out to Example Dental. Our team will call you back to help."
        return Call(ttft_ms=120, total_ms=200, text=text, in_tok=200, out_tok=40)


class GenAIBackend:
    def __init__(self, backend: str, project: str | None, location: str | None) -> None:
        from google import genai  # imported lazily so the fake backend needs no package

        if backend == "vertex":
            self.client = genai.Client(vertexai=True, project=project, location=location)
        else:
            key = os.environ.get("GEMINI_API_KEY", "").strip()
            if not key:
                raise ConfigError("GEMINI_API_KEY is not set (put it in the git-ignored .env)")
            self.client = genai.Client(api_key=key)

    def call(self, model: str, thinking: str | None, system: str, prompt: str, schema: dict | None,
             item_id: str) -> Call:
        from google.genai import errors, types

        cfg: dict[str, Any] = {"system_instruction": system, "max_output_tokens": 1024 if schema else 200}
        if thinking:
            cfg["thinking_config"] = types.ThinkingConfig(thinking_level=thinking)
        if schema is not None:
            cfg["response_mime_type"] = "application/json"
            cfg["response_schema"] = schema
        start = time.monotonic()
        c = Call()
        try:
            for chunk in self.client.models.generate_content_stream(
                    model=model, contents=prompt, config=types.GenerateContentConfig(**cfg)):
                if chunk.text and not c.ttft_ms:
                    c.ttft_ms = int((time.monotonic() - start) * 1000)
                c.text += chunk.text or ""
                u = chunk.usage_metadata
                if u:
                    c.in_tok = u.prompt_token_count or c.in_tok
                    c.out_tok = u.candidates_token_count or c.out_tok
                    c.think_tok = u.thoughts_token_count or c.think_tok
        except errors.APIError as e:
            c.status = f"error_{e.code}"
        except Exception as e:  # network and SDK errors: record the type only, never the message
            c.status = f"error_{type(e).__name__}"
        c.total_ms = int((time.monotonic() - start) * 1000)
        return c


# ---------------------------------------------------------------- prompts and scoring
def api_schema(schema: dict) -> dict:
    s = json.loads(json.dumps(schema))
    s.pop("$comment", None)
    for p in s["properties"].values():
        p.pop("description", None)
    return s


def extraction_prompt(item: dict, today: str) -> tuple[str, str]:
    if "turns" in item:
        conv = "\n".join(f"{t['who'].upper()}: {t['text']}" for t in item["turns"])
        return SYSTEM_EXTRACT.format(today=today), f"Conversation:\n{conv}\n\nExtract for the LAST patient turn."
    ctx = f"Context: {item['context']}\n" if item.get("context") else ""
    return SYSTEM_EXTRACT.format(today=today), f"{ctx}Patient: {item['utterance']}"


def norm(field_name: str, v: Any) -> Any:
    if v is None:
        return None
    s = str(v).strip()
    if field_name == "phone":
        d = re.sub(r"\D", "", s)
        return d[-10:]
    return s.lower()


def validate(obj: Any, schema: dict) -> bool:
    if not isinstance(obj, dict) or set(schema["required"]) - set(obj):
        return False
    for k, spec in schema["properties"].items():
        v = obj.get(k)
        if v is None:
            if not spec.get("nullable") and k in schema["required"]:
                return False
            continue
        if not isinstance(v, str) or ("enum" in spec and v not in spec["enum"]):
            return False
    return True


def score_extraction(text: str, expect: dict, schema: dict) -> tuple[bool, int, list[str]]:
    try:
        obj = json.loads(text)
    except ValueError:
        return False, 0, list(expect)
    bad = [k for k, v in expect.items() if norm(k, obj.get(k) if isinstance(obj, dict) else None) != norm(k, v)]
    return validate(obj, schema), len(expect) - len(bad), bad


def score_reply(text: str, item: dict, max_words: int) -> bool:
    t = text.lower()
    if len(text.split()) > max_words:
        return False
    if any(p.lower() in t for p in item.get("must_not", [])):
        return False
    return not item.get("must_any") or any(p.lower() in t for p in item["must_any"])


# ---------------------------------------------------------------- run
def load_sets() -> dict[str, dict]:
    return {n: yaml.safe_load((HERE / f"{n}.yaml").read_text(encoding="utf-8"))
            for n in ("extraction", "replies", "complex")}


def run(backend_name: str, backend: Any, location: str, runs: int, pace: float, models: list[str] | None,
        tiers: list[str], run_id: str) -> list[Row]:
    sets = load_sets()
    schema = json.loads((HERE / "schema.json").read_text(encoding="utf-8"))
    sch = api_schema(schema)
    rows: list[Row] = []
    for tier in tiers:
        for model, thinking, set_names in PLAN[tier]:
            if models and model not in models:
                continue
            for set_name in set_names:
                data = sets[set_name]
                for item in data["items"]:
                    for rep in range(1, runs + 1):
                        if set_name == "replies":
                            system, prompt = SYSTEM_REPLY, f"FACTS: {item['facts']}\nPatient: {item['patient']}"
                            c = backend.call(model, thinking, system, prompt, None, item["id"])
                        else:
                            system, prompt = extraction_prompt(item, data["today"])
                            c = backend.call(model, thinking, system, prompt, sch, item["id"])
                        if c.status.startswith("error_429"):
                            time.sleep(max(pace, 1) * 6)
                        r = Row(run_id, backend_name, location, tier, model, thinking or "default", set_name,
                                item["id"], rep, c.status, c.ttft_ms, c.total_ms, c.in_tok, c.out_tok, c.think_tok)
                        if c.status == "ok":
                            if set_name == "replies":
                                r.proxy_pass = "yes" if score_reply(c.text, item, data["max_words"]) else "no"
                            else:
                                ok, good, bad = score_extraction(c.text, item["expect"], schema)
                                r.json_valid, r.fields_expected = ("yes" if ok else "no"), len(item["expect"])
                                r.fields_correct, r.failed_fields = good, " ".join(bad)
                        rows.append(r)
                        time.sleep(pace)
    return rows


def pct(n: int, d: int) -> float | None:
    return round(100 * n / d, 1) if d else None


def summarize(rows: list[Row]) -> str:
    out = ["| Tier | Model | Thinking | Calls | Errors | TTFT p50 / p95 ms | Total p50 ms | JSON valid % | "
           "Field accuracy % | Reply proxy % | Cost per call (USD, Vertex us) | Thresholds |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    keys = sorted({(r.tier, r.model, r.thinking) for r in rows}, key=lambda k: (list(PLAN).index(k[0]), k[1]))
    for tier, model, thinking in keys:
        rs = [r for r in rows if (r.tier, r.model, r.thinking) == (tier, model, thinking)]
        ok = [r for r in rs if r.status == "ok"]
        tt = sorted(r.ttft_ms for r in ok if r.ttft_ms)
        p50 = int(statistics.median(tt)) if tt else None
        p95 = tt[min(len(tt) - 1, int(round(0.95 * (len(tt) - 1))))] if tt else None
        tot = int(statistics.median(r.total_ms for r in ok)) if ok else None
        ex = [r for r in ok if r.json_valid]
        rep = [r for r in ok if r.proxy_pass]
        jv = pct(sum(r.json_valid == "yes" for r in ex), len(ex))
        fa = pct(sum(r.fields_correct for r in ex), sum(r.fields_expected for r in ex))
        rp = pct(sum(r.proxy_pass == "yes" for r in rep), len(rep))
        pin, pout = PRICE.get(model, (0, 0))
        cost = (statistics.mean((r.in_tok * pin + (r.out_tok + r.think_tok) * pout) / 1e6 for r in ok)
                if ok else None)
        t = THRESH[tier]
        checks = [p50 is not None and p50 <= t[0], p95 is not None and p95 <= t[1],
                  t[2] is None or (jv is not None and jv >= t[2]), t[3] is None or (fa is not None and fa >= t[3]),
                  t[4] is None or rp is None or rp >= t[4]]
        out.append(f"| {tier} | `{model}` | {thinking} | {len(rs)} | {len(rs) - len(ok)} | {p50} / {p95} | {tot} | "
                   f"{jv if jv is not None else 'n/a'} | {fa if fa is not None else 'n/a'} | "
                   f"{rp if rp is not None else 'n/a'} | {f'{cost:.5f}' if cost is not None else 'n/a'} | "
                   f"{'pass' if all(checks) else 'FAIL'} |")
    return "\n".join(out)


def write(rows: list[Row], run_id: str, header: str, outdir: Path) -> tuple[Path, Path]:
    outdir.mkdir(parents=True, exist_ok=True)
    path = outdir / f"{run_id}.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(Row.__dataclass_fields__))
        w.writeheader()
        for r in rows:
            w.writerow(r.__dict__)
    summary = outdir / f"{run_id}-summary.md"
    fails: dict[str, int] = {}
    for r in rows:
        for k in r.failed_fields.split():
            fails[f"{r.model} {k}"] = fails.get(f"{r.model} {k}", 0) + 1
    summary.write_text(f"# Spike run {run_id}\n\n{header}\n\n{summarize(rows)}\n\n## Failed fields (model, field: count)\n\n"
                       + ("\n".join(f"- {k}: {v}" for k, v in sorted(fails.items())) or "- none") + "\n",
                       encoding="utf-8")
    return path, summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--backend", choices=["fake", "developer", "vertex"], required=True)
    ap.add_argument("--project", default=os.environ.get("VERTEX_PROJECT"))
    ap.add_argument("--location", default=os.environ.get("VERTEX_LOCATION", "us"))
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--pace", type=float, default=None, help="seconds between calls (default 4.5 developer, 0 fake)")
    ap.add_argument("--models", nargs="*", help="only these model IDs")
    ap.add_argument("--tiers", nargs="*", default=list(PLAN), choices=list(PLAN))
    ap.add_argument("--out", type=Path, default=HERE / "results")
    args = ap.parse_args(argv)

    models = sorted({m for t in args.tiers for m, _, _ in PLAN[t] if not args.models or m in args.models})
    allowed = [m.strip() for m in os.environ["GEMINI_ALLOWED_MODELS"].split(",")] \
        if os.environ.get("GEMINI_ALLOWED_MODELS") else None
    location = args.location if args.backend == "vertex" else ("-" if args.backend == "fake" else "developer-api")
    try:
        check_config(args.backend, args.location if args.backend == "vertex" else None, models, allowed,
                     os.environ.get("APP_ENV"))
        if args.backend == "fake":
            sets = load_sets()
            backend: Any = FakeBackend({i["id"]: i for s in sets.values() for i in s["items"]})
        else:
            backend = GenAIBackend(args.backend, args.project, args.location)
    except ConfigError as e:
        sys.stderr.write(f"REFUSED {e}\n")
        return 2
    pace = args.pace if args.pace is not None else (4.5 if args.backend == "developer" else 0.0)
    run_id = f"{dt.datetime.now(dt.UTC):%Y%m%dT%H%M%SZ}-{args.backend}"
    rows = run(args.backend, backend, location, args.runs, pace, args.models, args.tiers, run_id)
    note = ("**Backend: Gemini Developer API from a laptop.** Latency is indicative only, not Vertex `us` "
            "from us-central1." if args.backend == "developer" else f"Backend: {args.backend}, location {location}.")
    csv_path, md = write(rows, run_id, note, args.out)
    sys.stdout.write(f"wrote {csv_path.relative_to(HERE.parents[2]) if HERE.parents[2] in csv_path.parents else csv_path}"
                     f" and {md.name}\n{summarize(rows)}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
