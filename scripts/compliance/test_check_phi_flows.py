"""Tests for check_phi_flows.py (P0-14). Run: pytest scripts/compliance/

Each test writes a small repo copy in tmp_path, so the real files are never touched.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import check_phi_flows as cf  # noqa: E402

OVERVIEW = """# Flows
| PHI slot | Collected in | Sent to tools |
|---|---|---|
| `first_name` | `IDENTIFY` | `search_patient` |
| `dob` | `IDENTIFY` | `search_patient` |
"""
FLOWS_HEAD = ("| ID | From → To | Fields | PHI | Purpose | Vendor id | BAA (status) | Annex A | Protection |"
              " Environments | Owner tasks |\n|---|---|---|---|---|---|---|---|---|---|---|\n")
ROW_OK_1 = "| F01 | Widget → api | `first_name`, `dob` | yes | Talk | - | - | A1 | TLS | all | P2-25 |\n"
ROW_OK_2 = "| F02 | api → Cloud | `first_name` | yes | Extract | `cloud` | Cloud BAA (pending) | A1 | x | all | P2-03 |\n"
ROW_DEV = "| F17 | laptop → dev api | synthetic | no | Dev | `devapi` | None | - | x | local | P0-13 |\n"
VENDORS = """vendors:
  - {id: cloud, phi: "yes"}
  - {id: devapi, phi: "no"}
"""
ALLOWED = """services:
  - {api: run.googleapis.com}
always_on: [logging.googleapis.com]
"""
CONTAINERS = """| API | Kind | Used for |
|---|---|---|
| `run.googleapis.com` | cloud | Run |
| `logging.googleapis.com` | cloud | Logs |
| `gmail.googleapis.com` | workspace | Email |
"""


def repo(tmp_path: Path, rows: str = ROW_OK_1 + ROW_OK_2 + ROW_DEV, vendors: str = VENDORS,
         containers: str = CONTAINERS, overview: str = OVERVIEW) -> Path:
    files = {cf.OVERVIEW: overview, cf.FLOWS: "# Flows\n\n" + FLOWS_HEAD + rows + "\n## Rules\n",
             cf.VENDORS: vendors, cf.ALLOWED: ALLOWED, cf.CONTAINERS: containers}
    for rel, text in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return tmp_path


def test_clean_fixture_passes(tmp_path):
    assert cf.check(repo(tmp_path)) == []


def test_real_repo_passes():
    assert cf.check(cf.REPO) == []


def test_slot_without_flow(tmp_path):
    rows = "| F01 | Widget → api | `first_name` | yes | Talk | - | - | A1 | TLS | all | P2-25 |\n" + ROW_OK_2
    errs = cf.check(repo(tmp_path, rows=rows))
    assert errs == ["F1 PHI slot dob is in no PHI flow row"]


def test_slot_only_in_non_phi_row_does_not_count(tmp_path):
    rows = ROW_OK_2 + "| F16 | api → test | `dob` | no | Test | - | - | - | x | dev | P0-12 |\n"
    assert "F1 PHI slot dob is in no PHI flow row" in cf.check(repo(tmp_path, rows=rows))


def test_unknown_vendor(tmp_path):
    rows = ROW_OK_1 + ROW_OK_2 + "| F09 | api → X | `first_name` | yes | x | `nobody` | X BAA | A1 | x | all | P1 |\n"
    assert "F3 F09: vendor id nobody not in docs/compliance/vendors.yaml" in cf.check(repo(tmp_path, rows=rows))


def test_phi_vendor_without_flow(tmp_path):
    vendors = VENDORS + '  - {id: sms, phi: "yes"}\n'
    assert cf.check(repo(tmp_path, vendors=vendors)) == ["F2 PHI vendor sms is in no PHI flow row"]


def test_phi_flow_to_no_phi_vendor(tmp_path):
    rows = ROW_OK_1 + ROW_OK_2 + "| F18 | api → dev | `dob` | yes | x | `devapi` | None | A1 | x | all | P1 |\n"
    assert any(e.startswith("F4 F18") for e in cf.check(repo(tmp_path, rows=rows)))


def test_phi_flow_without_baa(tmp_path):
    rows = ROW_OK_1 + "| F02 | api → Cloud | `first_name` | yes | x | `cloud` | - | A1 | x | all | P2 |\n"
    assert cf.check(repo(tmp_path, rows=rows)) == ["F4 F02: PHI flow to a vendor without a BAA named"]


def test_duplicate_flow_id(tmp_path):
    assert "F6 duplicate flow ID F01" in cf.check(repo(tmp_path, rows=ROW_OK_1 + ROW_OK_1 + ROW_OK_2))


def test_service_not_allowed(tmp_path):
    containers = CONTAINERS + "| `bigquery.googleapis.com` | cloud | Analytics |\n"
    assert cf.check(repo(tmp_path, containers=containers)) == [
        "F5 service bigquery.googleapis.com is not in infra/org/allowed_services.yaml"]


@pytest.mark.parametrize("missing", ["overview", "containers"])
def test_missing_tables_reported(tmp_path, missing):
    kwargs = {missing: "# nothing here\n"}
    errs = cf.check(repo(tmp_path, **kwargs))
    assert errs and errs[0].startswith("F1" if missing == "overview" else "F5")


def test_main_exit_codes(tmp_path, capsys):
    assert cf.main(["--root", str(repo(tmp_path))]) == 0
    assert cf.main(["--root", str(repo(tmp_path, rows=ROW_OK_2))]) == 1
    assert "dob" in capsys.readouterr().err
