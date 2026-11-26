"""Offline tests for run_spike.py (fake backend only). Run: pytest evals/spike/p0-13/"""

import csv
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import run_spike as rs  # noqa: E402

SCHEMA = json.loads((rs.HERE / "schema.json").read_text(encoding="utf-8"))


def fake(wrong: set[str] | None = None) -> rs.FakeBackend:
    return rs.FakeBackend({i["id"]: i for s in rs.load_sets().values() for i in s["items"]}, wrong)


def test_sets_have_expected_sizes_and_synthetic_phones():
    sets = rs.load_sets()
    assert [len(sets[n]["items"]) for n in ("extraction", "replies", "complex")] == [30, 20, 10]
    text = "".join((rs.HERE / f"{n}.yaml").read_text(encoding="utf-8") for n in sets)
    digits = {d for d in __import__("re").findall(r"\d[\d\s().-]{8,}\d", text)}
    assert all("55501" in "".join(c for c in d if c.isdigit()) for d in digits if len([c for c in d if c.isdigit()]) >= 10)


@pytest.mark.parametrize(("backend", "location", "models", "allowed", "env", "msg"), [
    ("developer", None, ["gemini-3.8-flash"], None, None, "APP_ENV=local"),
    ("developer", None, ["gemini-3.8-flash"], None, "dev", "APP_ENV=local"),
    ("vertex", "global", ["gemini-3.8-flash"], None, None, "'us'"),
    ("vertex", "europe-west4", ["gemini-3.8-flash"], None, None, "'us'"),
    ("vertex", "us", ["gemini-3.1-pro-preview"], None, None, "not a GA"),
    ("vertex", "us", ["gemini-flash-latest"], None, None, "not a GA"),
    ("vertex", "us", ["gemini-3.8-flash"], ["gemini-3.5-flash"], None, "GEMINI_ALLOWED_MODELS"),
])
def test_config_rules_refuse(backend, location, models, allowed, env, msg):
    with pytest.raises(rs.ConfigError, match=msg):
        rs.check_config(backend, location, models, allowed, env)


@pytest.mark.parametrize(("backend", "location", "env"), [("vertex", "us", None), ("vertex", "us-central1", None),
                                                          ("developer", None, "local"), ("fake", None, None)])
def test_config_rules_allow(backend, location, env):
    rs.check_config(backend, location, ["gemini-3.8-flash"], ["gemini-3.8-flash"], env)


def test_main_refuses_developer_without_local(monkeypatch, capsys, tmp_path):
    monkeypatch.delenv("APP_ENV", raising=False)
    assert rs.main(["--backend", "developer", "--out", str(tmp_path)]) == 2
    assert "REFUSED" in capsys.readouterr().err and not list(tmp_path.iterdir())


def test_scoring():
    exp = {"intent": "book", "phone": "5035550142", "first_name": None}
    good = json.dumps({k: None for k in SCHEMA["properties"]} | {"intent": "book", "phone": "(503) 555-0142"})
    assert rs.score_extraction(good, exp, SCHEMA) == (True, 3, [])
    invented = json.dumps({k: None for k in SCHEMA["properties"]} | {"intent": "book", "phone": "5035550142",
                                                                     "first_name": "Sam"})
    assert rs.score_extraction(invented, exp, SCHEMA)[2] == ["first_name"]
    assert rs.score_extraction("not json", exp, SCHEMA) == (False, 0, list(exp))
    bad_enum = json.dumps({k: None for k in SCHEMA["properties"]} | {"intent": "purchase"})
    assert rs.score_extraction(bad_enum, {"intent": "book"}, SCHEMA)[0] is False


def test_reply_proxy():
    item = {"must_not": ["ibuprofen"], "must_any": ["call"]}
    assert rs.score_reply("Our team will call you today.", item, 45)
    assert not rs.score_reply("Take ibuprofen and call us.", item, 45)
    assert not rs.score_reply("Please come in.", item, 45)
    assert not rs.score_reply("word " * 50 + "call", item, 45)


def test_fake_run_writes_no_text(tmp_path):
    rows = rs.run("fake", fake({"X01"}), "-", 1, 0, None, list(rs.PLAN), "t1")
    assert len(rows) == 2 * 20 + 2 * (30 + 20) + 2 * 10
    csv_path, md = rs.write(rows, "t1", "Backend: fake.", tmp_path)
    data = csv_path.read_text(encoding="utf-8") + md.read_text(encoding="utf-8")
    for text in ("book a cleaning", "Maria", "Lopez", "Example Dental", "503", "Patient:", "FACTS"):
        assert text not in data
    rows_read = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    x01 = [r for r in rows_read if r["item"] == "X01"]
    assert x01 and all(r["failed_fields"] == "intent" for r in x01)
    assert "| flash | `gemini-3.8-flash` | LOW |" in md.read_text(encoding="utf-8")


def test_models_filter_skips_argon():
    rows = rs.run("fake", fake(), "-", 1, 0, ["gemini-3.8-flash"], ["pro"], "t2")
    assert {r.model for r in rows} == {"gemini-3.8-flash"} and {r.thinking for r in rows} == {"HIGH"}
