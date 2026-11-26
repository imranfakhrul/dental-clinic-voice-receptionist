"""Check the vendor/BAA matrix, compute the PHI gate and render vendor-matrix.md (P0-10).

  python3 scripts/compliance/check_vendors.py            validate only; exit 0 ok, 1 errors
  python3 scripts/compliance/check_vendors.py --render   validate, then write docs/compliance/vendor-matrix.md
  python3 scripts/compliance/check_vendors.py --gate     print GATE OPEN / GATE CLOSED with reasons; exit 0 open, 2 closed

Rules C1-C9 are in the P0-10 task spec §6. Prints vendor IDs and file paths only. No network calls.
Options --root, --today (YYYY-MM-DD) and --vendors exist for tests.
"""

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

REPO = Path(__file__).resolve().parents[2]
VENDORS = "docs/compliance/vendors.yaml"
SCHEMA = "docs/compliance/vendors.schema.json"
MATRIX = "docs/compliance/vendor-matrix.md"
EXCEPTION = re.compile(r"Exception DECISIONS #\d+")
STALE_DAYS = 100


def yn(value: Any) -> str:
    """allowed_services.yaml uses bare yes/no, which YAML 1.1 reads as booleans."""
    return {True: "yes", False: "no"}.get(value, str(value))


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.reasons: list[str] = []  # why the gate is closed


def check(data: dict[str, Any], root: Path, today: dt.date, rendering: bool) -> Report:
    r = Report()
    schema = json.loads((root / SCHEMA).read_text(encoding="utf-8"))
    for err in sorted(Draft202012Validator(schema).iter_errors(data), key=str):
        where = "/".join(str(p) for p in err.absolute_path) or "(top)"
        r.errors.append(f"C1 schema: {where}: {err.message}")
    if r.errors:
        return r  # later rules assume a valid shape

    def exists(path: str | None) -> bool:
        if rendering and path == MATRIX:
            return True  # being written now
        return bool(path) and (root / path).is_file()

    for key, rows in (("id", data["vendors"]), ("clinic_slug", data["clinics"])):
        seen: set[str] = set()
        for row in rows:
            if row[key] in seen:
                r.errors.append(f"C2 duplicate {key}: {row[key]}")
            seen.add(row[key])

    for v in data["vendors"]:
        baa, vid = v["baa"], v["id"]
        if baa["status"] == "signed" and not (baa.get("date") and exists(baa.get("record"))):
            r.errors.append(f"C3 {vid}: baa signed needs a date and an existing record file")
        if v["phi"] in ("yes", "conditional") and baa["status"] == "not_required":
            r.errors.append(f"C4 {vid}: phi={v['phi']} can't have baa not_required")
        if v["phi"] == "no" and not v.get("no_phi_control"):
            r.errors.append(f"C5 {vid}: phi=no needs no_phi_control")
        if v["phi"] == "conditional" and not v.get("phi_condition"):
            r.errors.append(f"C5 {vid}: phi=conditional needs phi_condition")
        if v.get("product_list"):
            check_products(v, root, r)
        if v["phi"] == "yes" and "prod" in v["environments"] and baa["status"] != "signed":
            r.reasons.append(f"{vid} phi=yes in prod, baa={baa['status']}")

    for c in data["clinics"]:
        if c["baa"]["status"] == "signed" and not (c["baa"].get("date") and exists(c["baa"].get("record"))):
            r.errors.append(f"C3 clinic {c['clinic_slug']}: baa signed needs a date and an existing record file")
    if not any(c["baa"]["status"] == "signed" for c in data["clinics"]):
        r.reasons.append("no clinic has a signed BAA")

    for item in data["phi_gate"]:
        if item["status"] == "done" and not exists(item.get("evidence")):
            r.errors.append(f"C7 gate item {item['id']}: done needs an existing evidence file")
        if item["status"] != "done":
            r.reasons.append(f"gate item {item['id']} ({item['task']}) is {item['status']}")

    age = (today - dt.date.fromisoformat(data["reviewed_on"])).days
    if age > STALE_DAYS:
        r.warnings.append(f"C9 reviewed_on is {age} days old (limit {STALE_DAYS}); run the quarterly review")
    return r


def check_products(v: dict[str, Any], root: Path, r: Report) -> None:
    path = root / v["product_list"]
    if not path.is_file():
        r.warnings.append(f"C6 {v['id']}: product_list {v['product_list']} not found")
        r.reasons.append(f"{v['id']} product list not yet available")
        return
    for svc in load_products(path).get("services", []):  # dev/staging/prod list; ops never holds PHI
        covered = yn(svc.get("hipaa_covered"))
        if covered == "yes" or (covered == "no" and EXCEPTION.search(svc.get("notes", ""))):
            continue
        r.reasons.append(f"{v['id']} API {svc.get('api')} hipaa_covered={covered} without a recorded exception")


def load_products(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def cell(text: Any) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def render(data: dict[str, Any], root: Path, r: Report) -> str:
    out = [
        "# Vendor/BAA matrix",
        "",
        f"> Generated from `{VENDORS}` (reviewed on {data['reviewed_on']}). **Do not edit.** "
        "Change the YAML and run `python3 scripts/compliance/check_vendors.py --render`.",
        "",
        f"## PHI gate: {'OPEN' if not r.reasons else 'CLOSED'}",
        "",
        "| Item | Task | Status | Evidence |",
        "|---|---|---|---|",
    ]
    out += [f"| {cell(i['description'])} | {i['task']} | {i['status']} | {i.get('evidence') or '-'} |"
            for i in data["phi_gate"]]
    if r.reasons:
        out += ["", "Why it's closed:", ""] + [f"- {cell(x)}" for x in r.reasons]
    out += ["", "## Vendors", "",
            "| Vendor | Services | PHI | Environments | BAA status | BAA date | Record | Owner | Tasks |",
            "|---|---|---|---|---|---|---|---|---|"]
    for v in data["vendors"]:
        baa = v["baa"]
        phi = v["phi"]
        if phi == "conditional":
            phi += f": {v['phi_condition']}"
            if baa["status"] != "signed":
                phi += " **PHI blocked for this vendor**"
        elif phi == "no":
            phi += f" (control: {v['no_phi_control']})"
        out.append(f"| {cell(v['name'])} | {cell(', '.join(v['services']))} | {cell(phi)} | "
                   f"{', '.join(v['environments'])} | {baa['status']} | {baa.get('date') or '-'} | "
                   f"{baa.get('record') or '-'} | {cell(v['owner'])} | {', '.join(v['tasks'])} |")
    notes = [v for v in data["vendors"] if v.get("notes")]
    if notes:
        out += ["", "Notes:", ""] + [f"- **{v['id']}:** {cell(v['notes'])}" for v in notes]
    out += ["", "## Clinics", "", "| Clinic | BAA status | Date | Record |", "|---|---|---|---|"]
    out += [f"| {c['clinic_slug']} | {c['baa']['status']} | {c['baa'].get('date') or '-'} | "
            f"{c['baa'].get('record') or '-'} |" for c in data["clinics"]]
    for v in data["vendors"]:
        path = root / v.get("product_list", "")
        if v.get("product_list") and path.is_file():
            products = load_products(path)
            out += ["", f"## Google Cloud products (from `{v['product_list']}`, dev/staging/prod)", "",
                    "| API | Purpose | HIPAA covered | Checked on |", "|---|---|---|---|"]
            out += [f"| `{s.get('api')}` | {cell(s.get('purpose', ''))} | {yn(s.get('hipaa_covered'))}"
                    f"{' (exception)' if yn(s.get('hipaa_covered')) == 'no' and EXCEPTION.search(s.get('notes', '')) else ''}"
                    f" | {products.get('checked_on', '-')} |" for s in products.get("services", [])]
    out += ["", "## Last review", "", f"{data['reviewed_on']} by {cell(data['reviewed_by'])}", ""]
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--render", action="store_true")
    mode.add_argument("--gate", action="store_true")
    ap.add_argument("--root", type=Path, default=REPO)
    ap.add_argument("--today", type=dt.date.fromisoformat, default=dt.datetime.now(dt.UTC).date())
    args = ap.parse_args(argv)

    root: Path = args.root
    data = yaml.safe_load((root / VENDORS).read_text(encoding="utf-8"))
    r = check(data, root, args.today, rendering=args.render)
    if not r.errors:
        text = render(data, root, r)
        matrix = root / MATRIX
        if args.render:
            matrix.write_text(text, encoding="utf-8")
            sys.stdout.write(f"wrote {MATRIX}\n")
        elif not matrix.is_file() or matrix.read_text(encoding="utf-8") != text:
            r.errors.append(f"C8 {MATRIX} differs from the YAML; run --render (don't edit it by hand)")

    for w in r.warnings:
        sys.stderr.write(f"WARN {w}\n")
    for e in r.errors:
        sys.stderr.write(f"ERROR {e}\n")
    if r.errors:
        return 1
    if args.gate:
        if r.reasons:
            sys.stdout.write("GATE CLOSED\n" + "".join(f"CLOSED: {x}\n" for x in r.reasons))
            return 2
        sys.stdout.write("GATE OPEN\n")
        return 0
    sys.stdout.write(f"OK {VENDORS}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
