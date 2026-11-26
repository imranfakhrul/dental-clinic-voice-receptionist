"""Tests for check_templates.py (P0-15 spec §10). Run: pytest scripts/messaging/

The baseline is the real templates.yaml and messaging_policy.yaml; each test changes a deep copy in memory,
so the real files are never touched.
"""

import copy
import json
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent))
import check_templates as ct  # noqa: E402

BASE_T = yaml.safe_load(ct.TEMPLATES.read_text(encoding="utf-8"))
BASE_P = yaml.safe_load(ct.POLICY.read_text(encoding="utf-8"))
SCHEMA = json.loads(ct.SCHEMA.read_text(encoding="utf-8"))


@pytest.fixture
def tpl():
    return copy.deepcopy(BASE_T)


@pytest.fixture
def policy():
    return copy.deepcopy(BASE_P)


def errors(t, p):
    return [f for f in ct.check(t, p, SCHEMA) if f.level == "error"]


def by_id(t, tid):
    return next(x for x in t["templates"] if x["id"] == tid)


def test_real_files_pass(tpl, policy):
    assert ct.check(tpl, policy, SCHEMA) == []
    assert ct.main([]) == 0


def test_last_name_rejected(tpl, policy):
    t = by_id(tpl, "booking_confirmation_sms_v1")
    t["body"] = t["body"].replace("{first_name}", "{first_name} {last_name}")
    t["variables"].append("last_name")
    t["example"]["last_name"] = "Lopez"
    assert any(f.rule == "T5" for f in errors(tpl, policy))


def test_reason_rejected(tpl, policy):
    t = by_id(tpl, "booking_confirmation_sms_v1")
    t["body"] += " Reason: {reason}"
    t["variables"].append("reason")
    t["example"]["reason"] = "check-up"
    assert any(f.rule in ("T4", "T5") for f in errors(tpl, policy))


def test_field_not_in_policy_type(tpl, policy):
    t = by_id(tpl, "cancel_notice_sms_v1")
    t["body"] = t["body"].replace("on {appointment_date}", "on {appointment_date} at {appointment_time}")
    t["variables"].append("appointment_time")
    t["example"]["appointment_time"] = "9:30 AM"
    assert [f.rule for f in errors(tpl, policy)] == ["T4"]


def test_undeclared_variable(tpl, policy):
    by_id(tpl, "reminder_sms_v1")["variables"].remove("first_name")
    assert any(f.rule == "T3" and "used in body" in f.message for f in errors(tpl, policy))


def test_declared_but_unused(tpl, policy):
    by_id(tpl, "reminder_sms_v1")["variables"].append("appointment_date")
    assert any(f.rule == "T3" and "not used" in f.message for f in errors(tpl, policy))


def test_denylist_word(tpl, policy):
    t = by_id(tpl, "reminder_sms_v1")
    t["body"] = t["body"].replace("your visit", "your cleaning")
    assert any(f.rule == "T7" and "cleaning" in f.message for f in errors(tpl, policy))


def test_denylist_word_only_in_clinic_name(tpl, policy):
    for t in tpl["templates"]:
        t["example"]["clinic_name"] = "Clean Teeth Cleaning Co"
    assert errors(tpl, policy) == []


def test_denylist_whole_words_only(tpl, policy):
    t = by_id(tpl, "reminder_sms_v1")
    t["body"] = t["body"].replace("reminder:", "reminder (Spain office):")
    assert not any(f.rule == "T7" for f in errors(tpl, policy))


def test_sms_length_warning_and_error(tpl, policy):
    t = by_id(tpl, "reminder_sms_v1")
    t["body"] = t["body"].replace("reminder:", "reminder: " + "x" * 40)
    f = ct.check(tpl, policy, SCHEMA)
    assert [x.level for x in f if x.rule == "T8"] == ["warning"]
    t["body"] = t["body"].replace("reminder:", "reminder: " + "y" * 160)
    assert any(x.rule == "T8" for x in errors(tpl, policy))


def test_curly_apostrophe_is_not_gsm(tpl, policy):
    t = by_id(tpl, "booking_confirmation_sms_v1")
    t["body"] = t["body"].replace("you're", "you’re")
    assert any(f.rule == "T8" and "non-GSM" in f.message for f in errors(tpl, policy))


def test_policy_version_mismatch(tpl, policy):
    policy["decision_version"] = "1.3"
    assert [f.rule for f in errors(tpl, policy)] == ["T2"]


def test_whatsapp_ending_with_variable(tpl, policy):
    t = by_id(tpl, "cancel_notice_wa_v1")
    t["body"] = t["body"].replace(" Reply STOP to opt out.", "").replace("please call {clinic_phone}.",
                                                                          "Reply STOP to opt out or call {clinic_phone}")
    assert any(f.rule == "T10" for f in errors(tpl, policy))


def test_whatsapp_starting_with_variable(tpl, policy):
    t = by_id(tpl, "reminder_wa_v1")
    t["body"] = "{clinic_name} says: " + t["body"]
    assert any(f.rule == "T10" for f in errors(tpl, policy))


def test_channel_not_integrated(tpl, policy):
    policy["channels"]["whatsapp"]["integrated"] = False
    policy["environments"]["testing"]["active_channel"] = "sms"
    assert sum(f.rule == "T6" for f in errors(tpl, policy)) == 4


def test_missing_type_for_channel(tpl, policy):
    tpl["templates"] = [t for t in tpl["templates"] if t["id"] != "reminder_wa_v1"]
    assert [(f.rule, f.message) for f in errors(tpl, policy)] == [("T6", "channel whatsapp has no reminder template")]


def test_missing_opt_out_text(tpl, policy):
    t = by_id(tpl, "reschedule_notice_sms_v1")
    t["body"] = t["body"].replace(" Reply STOP to opt out.", "")
    assert [f.rule for f in errors(tpl, policy)] == ["T9"]


def test_system_reply_with_first_name(tpl, policy):
    tpl["system_replies"]["whatsapp"]["help"] = "Hi {first_name}, " + tpl["system_replies"]["whatsapp"]["help"]
    assert [f.rule for f in errors(tpl, policy)] == ["T11"]


def test_schema_error_stops_early(tpl, policy):
    del by_id(tpl, "reminder_sms_v1")["example"]
    f = errors(tpl, policy)
    assert f and all(x.rule == "T1" for x in f)


def test_sms_template_with_whatsapp_fields_rejected(tpl, policy):
    by_id(tpl, "reminder_sms_v1")["provider_status"] = "APPROVED"
    assert any(f.rule == "T1" for f in errors(tpl, policy))


def test_examples_are_synthetic():
    for t in BASE_T["templates"]:
        phone = t["example"].get("clinic_phone", "")
        assert "555-01" in phone
        assert t["example"]["clinic_name"] == "Example Dental"


def test_output_has_no_example_values(tpl, policy, tmp_path, capsys):
    t = by_id(tpl, "reminder_sms_v1")
    t["body"] = t["body"].replace("your visit", "your cleaning")
    p = tmp_path / "t.yaml"
    p.write_text(yaml.safe_dump(tpl), encoding="utf-8")
    assert ct.main(["--templates", str(p)]) == 1
    err = capsys.readouterr().err
    assert "T7" in err and "Maria" not in err and "555" not in err
