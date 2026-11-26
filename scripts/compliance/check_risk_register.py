"""Check the risk register (P0-11).

  python3 scripts/compliance/check_risk_register.py [register.md]

Rules:
  K1 risk IDs are unique and look like R01
  K2 score = L x I and the band matches (inherent and residual)
  K3 every task ID in Controls exists in dental-ai-tasks/tasks/ and is a survivor
     (a merged ID may only appear as "was P1-11")
  K4 every High or Critical risk names at least one task and has a residual of 9 or less,
     or is listed in accepted-risks.md
  K5 every vendor in vendors.yaml with phi yes or conditional is named in some risk
Exit 0 when all rules hold, 1 otherwise. Standard library plus pyyaml; no network.
"""

import re
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
TASK = re.compile(r"P\d-\d{2}[a-z]?")


def band(score: int) -> str:
    return "Low" if score <= 4 else "Medium" if score <= 9 else "High" if score <= 16 else "Critical"


def task_index(tasks_dir: Path) -> dict[str, str | None]:
    """Task ID -> survivor ID it was merged into, or None for a survivor."""
    index: dict[str, str | None] = {}
    for f in tasks_dir.glob("P*.md"):
        m = re.search(r"merged_into:\s*(\S+)", f.read_text(encoding="utf-8"))
        index[f.name.split(" ")[0]] = m.group(1) if m else None
    return index


def rows(register: Path) -> list[list[str]]:
    out = []
    for line in register.read_text(encoding="utf-8").splitlines():
        if re.match(r"^\| R\d", line):
            out.append([c.strip() for c in line.strip().strip("|").split(" | ")])
    return out


def check(register: Path, root: Path = REPO) -> list[str]:
    errors: list[str] = []
    tasks = task_index(root / "dental-ai-tasks/tasks")
    accepted = (register.parent / "accepted-risks.md")
    accepted_text = accepted.read_text(encoding="utf-8") if accepted.is_file() else ""
    seen: set[str] = set()
    data = rows(register)
    if not data:
        return [f"no risk rows found in {register}"]
    for r in data:
        if len(r) != 17:
            errors.append(f"{r[0]}: expected 17 columns, found {len(r)}")
            continue
        rid, controls = r[0], r[8]
        if not re.fullmatch(r"R\d{2,}", rid) or rid in seen:
            errors.append(f"K1 {rid}: bad or duplicate ID")
        seen.add(rid)
        try:
            li, ii, sc, rl, ri, rs = (int(r[k]) for k in (4, 5, 6, 9, 10, 11))
        except ValueError:
            errors.append(f"K2 {rid}: L, I and scores must be numbers")
            continue
        if sc != li * ii or r[7] != band(sc):
            errors.append(f"K2 {rid}: inherent {li}x{ii} should be {li * ii} {band(li * ii)}, found {sc} {r[7]}")
        if rs != rl * ri or r[12] != band(rs):
            errors.append(f"K2 {rid}: residual {rl}x{ri} should be {rl * ri} {band(rl * ri)}, found {rs} {r[12]}")
        survivors = re.sub(r"was " + TASK.pattern, "", controls)
        for old in re.findall(r"was (" + TASK.pattern + ")", controls):
            if tasks.get(old, "missing") is None or old not in tasks:
                errors.append(f"K3 {rid}: 'was {old}' but {old} is not a merged task")
        for tid in TASK.findall(survivors):
            if tid not in tasks:
                errors.append(f"K3 {rid}: task {tid} does not exist")
            elif tasks[tid]:
                errors.append(f"K3 {rid}: task {tid} was merged into {tasks[tid]}; cite the survivor")
        if band(sc) in ("High", "Critical"):
            if not TASK.search(survivors):
                errors.append(f"K4 {rid}: {band(sc)} risk names no task")
            if rs > 9 and not re.search(rf"\b{rid}\b", accepted_text):
                errors.append(f"K4 {rid}: residual {rs} above Medium and no entry in accepted-risks.md")
    text = register.read_text(encoding="utf-8")
    vendors = yaml.safe_load((root / "docs/compliance/vendors.yaml").read_text(encoding="utf-8"))["vendors"]
    for v in vendors:
        if v["phi"] in ("yes", "conditional") and v["id"] not in text:
            errors.append(f"K5 vendor {v['id']} (phi={v['phi']}) is not named in any risk")
    return errors


def main() -> int:
    register = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "docs/compliance/risk/risk-register.md"
    errors = check(register)
    for e in errors:
        sys.stderr.write(f"FAIL {e}\n")
    if not errors:
        sys.stdout.write(f"OK {len(rows(register))} risks in {register.name}\n")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
