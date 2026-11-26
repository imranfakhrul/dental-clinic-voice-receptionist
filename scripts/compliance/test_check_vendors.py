"""Tests for check_vendors.py (P0-10 spec §10). Run: pytest scripts/compliance/

Each test builds a small repo copy in tmp_path (schema + fixture YAML + record files), so the real files are never touched.
"""

import copy
import shutil
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent))
import check_vendors as cv  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
TODAY = "2026-11-26"

BASE = {
    "schema_version": 1,
    "reviewed_on": TODAY,
    "reviewed_by": "Test Reviewer",
    "vendors": [
        {"id": "cloud", "name": "Cloud", "services": ["hosting"], "phi": "yes", "environments": ["prod"],
         "baa": {"status": "pending", "record": None}, "product_list": "products.yaml", "owner": "o", "tasks": ["P0-05"]},
        {"id": "mail", "name": "Mail", "services": ["email"], "phi": "conditional", "phi_condition": "full_details only",
         "environments": ["prod"], "baa": {"status": "pending", "record": None}, "owner": "o", "tasks": ["P0-08"]},
        {"id": "git", "name": "Git", "services": ["code"], "phi": "no", "no_phi_control": "synthetic only",
         "environments": ["team"], "baa": {"status": "not_required"}, "owner": "o", "tasks": ["P1-01"]},
    ],
    "clinics": [{"clinic_slug": "clinic-a", "baa": {"status": "pending", "record": None}}],
    "phi_gate": [
        {"id": "gcp_baa", "description": "Cloud BAA", "task": "P0-05", "status": "pending", "evidence": None},
        {"id": "matrix", "description": "Matrix", "task": "P0-10", "status": "pending", "evidence": None},
    ],
}
PRODUCTS = {"checked_on": TODAY, "services": [
    {"api": "run.googleapis.com", "purpose": "run", "hipaa_covered": True, "notes": ""},
    {"api": "servicenetworking.googleapis.com", "purpose": "net", "hipaa_covered": False,
     "notes": "control plane. Exception DECISIONS #295."},
]}


def make(tmp_path: Path, data: dict, products: dict | None = PRODUCTS, render: bool = True) -> Path:
    (tmp_path / "docs/compliance").mkdir(parents=True)
    shutil.copy(REPO / cv.SCHEMA, tmp_path / cv.SCHEMA)
    (tmp_path / cv.VENDORS).write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    (tmp_path / "record.md").write_text("record", encoding="utf-8")
    if products is not None:
        (tmp_path / "products.yaml").write_text(yaml.safe_dump(products), encoding="utf-8")
    if render:
        assert cv.main(["--render", "--root", str(tmp_path), "--today", TODAY]) == 0
    return tmp_path


def run(root: Path, *args: str, today: str = TODAY) -> int:
    return cv.main([*args, "--root", str(root), "--today", today])


def all_done() -> dict:
    d = copy.deepcopy(BASE)
    for v in d["vendors"][:2]:
        v["baa"] = {"status": "signed", "type": "click_through", "date": TODAY, "record": "record.md"}
    d["clinics"][0]["baa"] = {"status": "signed", "date": TODAY, "record": "record.md"}
    for item in d["phi_gate"]:
        item.update(status="done", evidence="record.md")
    return d


def test_valid_example_validates_and_gate_closed(tmp_path, capsys):
    root = make(tmp_path, copy.deepcopy(BASE))
    assert run(root) == 0
    assert run(root, "--gate") == 2
    out = capsys.readouterr().out
    assert "GATE CLOSED" in out
    assert "cloud phi=yes in prod, baa=pending" in out
    assert "gate item gcp_baa (P0-05) is pending" in out
    assert "no clinic has a signed BAA" in out


def test_all_done_gate_open(tmp_path, capsys):
    root = make(tmp_path, all_done())
    assert run(root, "--gate") == 0
    assert "GATE OPEN" in capsys.readouterr().out


def test_real_repo_files_validate_and_gate_closed(capsys):
    assert cv.main(["--today", TODAY]) == 0
    assert cv.main(["--gate", "--today", TODAY]) == 2
    assert "GATE CLOSED" in capsys.readouterr().out


@pytest.mark.parametrize(("change", "rule", "name"), [
    (lambda d: d["vendors"].append(copy.deepcopy(d["vendors"][0])), "C2", "cloud"),
    (lambda d: d["vendors"][0].update(baa={"status": "signed", "date": TODAY, "record": "missing.md"}), "C3", "cloud"),
    (lambda d: d["vendors"][0].update(baa={"status": "not_required"}), "C4", "cloud"),
    (lambda d: d["vendors"][2].pop("no_phi_control"), "C5", "git"),
    (lambda d: d["vendors"][1].pop("phi_condition"), "C5", "mail"),
    (lambda d: d["phi_gate"][0].update(status="done", evidence="missing.md"), "C7", "gcp_baa"),
    (lambda d: d["vendors"][0].update(phi="maybe"), "C1", "vendors/0/phi"),
])
def test_rule_errors(tmp_path, capsys, change, rule, name):
    data = copy.deepcopy(BASE)
    change(data)
    root = make(tmp_path, data, render=False)
    assert run(root) == 1
    err = capsys.readouterr().err
    assert f"ERROR {rule}" in err and name in err


def test_c6_product_list_missing_warns_and_closes(tmp_path, capsys):
    root = make(tmp_path, all_done(), products=None)
    assert run(root, "--gate") == 2
    cap = capsys.readouterr()
    assert "WARN C6 cloud" in cap.err
    assert "cloud product list not yet available" in cap.out


def test_c8_hand_edited_matrix(tmp_path, capsys):
    root = make(tmp_path, copy.deepcopy(BASE))
    with (root / cv.MATRIX).open("a", encoding="utf-8") as f:
        f.write("hand edit\n")
    assert run(root) == 1
    assert "ERROR C8" in capsys.readouterr().err


def test_c9_stale_review_warns_only(tmp_path, capsys):
    root = make(tmp_path, copy.deepcopy(BASE))
    assert run(root, today="2027-03-26") == 0  # 120 days later
    assert "WARN C9" in capsys.readouterr().err


def test_conditional_pending_does_not_close_gate(tmp_path, capsys):
    data = all_done()
    data["vendors"][1]["baa"] = {"status": "pending", "record": None}
    root = make(tmp_path, data)
    assert run(root, "--gate") == 0
    assert "PHI blocked for this vendor" in (root / cv.MATRIX).read_text(encoding="utf-8")


def test_verify_api_closes_gate(tmp_path, capsys):
    products = copy.deepcopy(PRODUCTS)
    products["services"].append({"api": "new.googleapis.com", "purpose": "x", "hipaa_covered": "verify", "notes": ""})
    root = make(tmp_path, all_done(), products=products)
    assert run(root, "--gate") == 2
    assert "cloud API new.googleapis.com hipaa_covered=verify" in capsys.readouterr().out


def test_not_covered_without_exception_closes_gate(tmp_path, capsys):
    products = copy.deepcopy(PRODUCTS)
    products["services"][1]["notes"] = "control plane"
    root = make(tmp_path, all_done(), products=products)
    assert run(root, "--gate") == 2
    assert "servicenetworking.googleapis.com hipaa_covered=no without a recorded exception" in capsys.readouterr().out


def test_not_covered_with_exception_is_accepted(tmp_path):
    root = make(tmp_path, all_done())
    assert run(root, "--gate") == 0
    assert "no (exception)" in (root / cv.MATRIX).read_text(encoding="utf-8")
