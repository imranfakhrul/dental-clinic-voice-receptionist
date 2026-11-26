"""Offline tests for submit_whatsapp_templates.py and send_test_message.py --template (P0-15).

A fake opener stands in for the network: no test makes a real HTTP call. Values are fake.
"""

import copy
import io
import json
import sys
import urllib.error
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent))
import send_test_message as stm  # noqa: E402
import submit_whatsapp_templates as swt  # noqa: E402

FAKE_TOKEN = "T" * 60
ENV = {"WA_TOKEN": FAKE_TOKEN, "WA_WABA_ID": "1234567890", "WA_GRAPH_VERSION": "v27.0"}
BASE = yaml.safe_load(swt.check_templates.TEMPLATES.read_text(encoding="utf-8"))


class FakeResponse(io.BytesIO):
    status = 200


class Recorder:
    def __init__(self, reply=None, error=None):
        self.requests, self.reply, self.error = [], reply or {"id": "111", "status": "PENDING"}, error

    def __call__(self, request, timeout):
        self.requests.append(request)
        if self.error:
            raise self.error
        return FakeResponse(json.dumps(self.reply).encode())


def write(tmp_path, data):
    p = tmp_path / "templates.yaml"
    p.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return p


def test_named_parameters_and_examples():
    t = next(x for x in BASE["templates"] if x["id"] == "booking_confirmation_wa_v1")
    p = swt.payload(t)
    assert p["category"] == "utility" and p["parameter_format"] == "named" and p["language"] == "en_US"
    assert "{{first_name}}" in p["components"][0]["text"] and "{first_name}" not in p["components"][0]["text"].replace(
        "{{first_name}}", "")
    names = [x["param_name"] for x in p["components"][0]["example"]["body_text_named_params"]]
    assert names == ["first_name", "clinic_name", "appointment_date", "appointment_time", "clinic_phone"]


def test_dry_run_by_default_makes_no_call(capsys):
    rec = Recorder()
    assert swt.main([], opener=rec, env=ENV) == 0
    out = capsys.readouterr().out
    assert rec.requests == [] and "dry run" in out and out.count("utility") == 4
    assert FAKE_TOKEN not in out and "1234567890" not in out and "Maria" not in out


def test_submit_without_credentials_is_dry_run():
    rec = Recorder()
    assert swt.main(["--submit"], opener=rec, env={}) == 2
    assert rec.requests == []


def test_submit_posts_each_draft(capsys):
    rec = Recorder()
    assert swt.main(["--submit"], opener=rec, env=ENV) == 0
    assert len(rec.requests) == 4
    r = rec.requests[0]
    assert r.full_url == "https://graph.facebook.com/v27.0/1234567890/message_templates"
    assert json.loads(r.data)["name"] == "booking_confirmation_wa_v1"
    out = capsys.readouterr().out
    assert "status PENDING" in out and FAKE_TOKEN not in out and "1234567890" not in out


def test_submit_skips_approved(tmp_path):
    data = copy.deepcopy(BASE)
    for t in data["templates"]:
        if t["channel"] == "whatsapp":
            t["provider_status"] = "APPROVED"
    rec = Recorder()
    assert swt.main(["--submit", "--templates", str(write(tmp_path, data))], opener=rec, env=ENV) == 0
    assert rec.requests == []


def test_submit_refuses_invalid_templates(tmp_path):
    data = copy.deepcopy(BASE)
    data["templates"][4]["body"] += " {reason}"
    rec = Recorder()
    assert swt.main(["--submit", "--templates", str(write(tmp_path, data))], opener=rec, env=ENV) == 2
    assert rec.requests == []


def test_submit_http_error_is_redacted(capsys):
    body = json.dumps({"error": {"code": 100, "message": f"bad token {FAKE_TOKEN} for +1 503 555 0100"}}).encode()
    err = urllib.error.HTTPError("u", 400, "Bad", {}, io.BytesIO(body))
    assert swt.main(["--submit"], opener=Recorder(error=err), env=ENV) == 1
    e = capsys.readouterr().err
    assert "code 100" in e and FAKE_TOKEN not in e and "555" not in e


@pytest.fixture
def send_env(monkeypatch):
    monkeypatch.setenv("WA_TOKEN", FAKE_TOKEN)
    monkeypatch.setenv("WA_PHONE_NUMBER_ID", "1098765432")
    monkeypatch.setenv("WA_TEST_TO", "15035550100")
    monkeypatch.setenv("WA_GRAPH_VERSION", "v27.0")


def test_send_refuses_draft_template(send_env, capsys):
    rec = Recorder()
    assert stm.main(["--template", "reminder_wa_v1"], opener=rec) == 2
    assert rec.requests == [] and "not APPROVED" in capsys.readouterr().err


def test_send_refuses_sms_or_unknown_template(send_env):
    rec = Recorder()
    assert stm.main(["--template", "reminder_sms_v1"], opener=rec) == 2
    assert stm.main(["--template", "nope_v1"], opener=rec) == 2
    assert rec.requests == []


def test_send_refuses_extra_values(send_env):
    rec = Recorder()
    assert stm.main(["--template", "reminder_wa_v1", "first_name=Real"], opener=rec) == 2
    assert rec.requests == []


def test_send_approved_uses_examples_only(send_env, tmp_path, monkeypatch, capsys):
    data = copy.deepcopy(BASE)
    for t in data["templates"]:
        if t["id"] == "reminder_wa_v1":
            t["provider_status"] = "APPROVED"
    monkeypatch.setattr(stm, "TEMPLATES", write(tmp_path, data))
    rec = Recorder(reply={"messages": [{"id": "wamid.TEST"}]})
    assert stm.main(["--template", "reminder_wa_v1"], opener=rec) == 0
    sent = json.loads(rec.requests[0].data)
    assert sent["to"] == "15035550100" and sent["template"]["name"] == "reminder_wa_v1"
    params = {p["parameter_name"]: p["text"] for p in sent["template"]["components"][0]["parameters"]}
    ex = next(t for t in BASE["templates"] if t["id"] == "reminder_wa_v1")["example"]
    assert params == ex
    out = capsys.readouterr().out
    assert "wamid.TEST" in out and FAKE_TOKEN not in out and "15035550100" not in out
