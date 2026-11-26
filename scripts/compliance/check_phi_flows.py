"""Check the PHI flow table against the flow designs, the vendor matrix and the allowed Google services (P0-14).

  python3 scripts/compliance/check_phi_flows.py            exit 0 ok, 1 gaps found
  python3 scripts/compliance/check_phi_flows.py --root DIR  check another repo copy (tests)

Rules:
  F1  every PHI slot in docs/flows/overview.md appears in the Fields of at least one PHI flow row
  F2  every vendors.yaml vendor with phi yes/conditional appears in at least one PHI flow row
  F3  every vendor id in a flow row exists in vendors.yaml
  F4  every PHI flow row with a vendor names a BAA, and that vendor has phi yes/conditional
  F5  every `cloud` API in the containers.md services table is in allowed_services.yaml (services or always_on)
  F6  flow IDs are unique
Prints IDs, slot names and file paths only. No network calls.
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).resolve().parents[2]
OVERVIEW = "docs/flows/overview.md"
FLOWS = "docs/architecture/phi-flows.md"
CONTAINERS = "docs/architecture/containers.md"
VENDORS = "docs/compliance/vendors.yaml"
ALLOWED = "infra/org/allowed_services.yaml"
TICK = re.compile(r"`([^`]+)`")


def cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def table_after(text: str, header_start: str) -> list[dict[str, str]]:
    """Rows of the first Markdown table whose header row starts with header_start."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith(header_start):
            head = cells(line)
            rows = []
            for row in lines[i + 2:]:
                if not row.startswith("|"):
                    break
                rows.append(dict(zip(head, cells(row), strict=False)))
            return rows
    return []


def check(root: Path) -> list[str]:
    errors: list[str] = []
    slots = [TICK.findall(r["PHI slot"])[0] for r in table_after((root / OVERVIEW).read_text(encoding="utf-8"),
                                                                    "| PHI slot |") if TICK.findall(r["PHI slot"])]
    if not slots:
        errors.append(f"F1 no PHI slot table found in {OVERVIEW}")
    flows = table_after((root / FLOWS).read_text(encoding="utf-8"), "| ID | From")
    if not flows:
        errors.append(f"F1 no flow table found in {FLOWS}")
    vendors: dict[str, Any] = {v["id"]: v for v in
                               yaml.safe_load((root / VENDORS).read_text(encoding="utf-8"))["vendors"]}
    phi_vendors = {i for i, v in vendors.items() if v.get("phi") in ("yes", "conditional")}

    seen: set[str] = set()
    covered_slots: set[str] = set()
    used_phi_vendors: set[str] = set()
    for f in flows:
        fid = f.get("ID", "")
        if fid in seen:
            errors.append(f"F6 duplicate flow ID {fid}")
        seen.add(fid)
        is_phi = not f.get("PHI", "").lower().startswith("no")
        ids = [] if f.get("Vendor id", "-").strip() in ("-", "") else TICK.findall(f["Vendor id"])
        for vid in ids:
            if vid not in vendors:
                errors.append(f"F3 {fid}: vendor id {vid} not in {VENDORS}")
            elif is_phi and vid not in phi_vendors:
                errors.append(f"F4 {fid}: PHI flow to {vid}, whose vendors.yaml row says phi: no")
        if is_phi:
            covered_slots.update(TICK.findall(f.get("Fields", "")))
            used_phi_vendors.update(ids)
            if ids and f.get("BAA (status)", "-").strip() in ("", "-"):
                errors.append(f"F4 {fid}: PHI flow to a vendor without a BAA named")
    for s in slots:
        if s not in covered_slots:
            errors.append(f"F1 PHI slot {s} is in no PHI flow row")
    for v in sorted(phi_vendors - used_phi_vendors):
        errors.append(f"F2 PHI vendor {v} is in no PHI flow row")

    allowed_doc = yaml.safe_load((root / ALLOWED).read_text(encoding="utf-8"))
    allowed = {s["api"] for s in allowed_doc.get("services", [])} | set(allowed_doc.get("always_on", []))
    services = table_after((root / CONTAINERS).read_text(encoding="utf-8"), "| API | Kind |")
    if not services:
        errors.append(f"F5 no services table found in {CONTAINERS}")
    for s in services:
        api = TICK.findall(s.get("API", ""))
        if s.get("Kind") == "cloud" and api and api[0] not in allowed:
            errors.append(f"F5 service {api[0]} is not in {ALLOWED}")
    return errors


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", type=Path, default=REPO)
    args = ap.parse_args(argv)
    errors = check(args.root)
    for e in errors:
        sys.stderr.write(f"ERROR {e}\n")
    if not errors:
        sys.stdout.write(f"OK {FLOWS}\n")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
