"""Check docs/messaging/templates.yaml against its schema and docs/compliance/messaging_policy.yaml (P0-15).

  python3 scripts/messaging/check_templates.py [--templates PATH] [--policy PATH] [--schema PATH]
  exit 0 ok (warnings allowed), 1 any error

Rules (P0-15 design, adapted to messaging policy v1.2):
  T1  valid against templates.schema.json
  T2  policy_version equals the policy's decision_version
  T3  every {var} in the body is declared in variables, and every declared variable is used
  T4  every variable is in the policy's message_types[<type>].fields
  T5  no variable is in never_allowed_fields
  T6  the channel is integrated in the policy; every integrated channel and the testing channel have all four types
  T7  the rendered example has no denylisted word (whole word, case-insensitive), except inside the clinic name
  T8  SMS: rendered example is GSM-7 only; <= 160 ok, 161-306 warning, > 306 error
  T9  when the policy requires opt-out text, every body contains "Reply STOP"
  T10 WhatsApp: category UTILITY; the body doesn't start or end with a variable
  T11 system replies use only {clinic_name} and {clinic_phone}
Prints rule, template ID and a short message only; never example values. No network calls.
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

REPO = Path(__file__).resolve().parents[2]
TEMPLATES = REPO / "docs/messaging/templates.yaml"
SCHEMA = REPO / "docs/messaging/templates.schema.json"
POLICY = REPO / "docs/compliance/messaging_policy.yaml"
TYPES = ("booking_confirmation", "reminder", "reschedule_notice", "cancel_notice")
VAR = re.compile(r"\{([a-z_]+)\}")
REPLY_VARS = {"clinic_name", "clinic_phone"}
OPT_OUT = "reply stop"
DENYLIST = [
    "appointment type", "cleaning", "exam", "x-ray", "filling", "crown", "root canal", "extraction", "implant",
    "whitening", "ortho", "braces", "emergency", "pain", "toothache", "swelling", "bleeding", "infection",
    "insurance", "balance", "payment", "dr.", "doctor", "hygienist", "dentist", "dental",
]
# GSM 03.38 basic set and extension table (extension characters count as two).
GSM_BASIC = set(
    "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§"
    "¿abcdefghijklmnopqrstuvwxyzäöñüà"
)
GSM_EXT = set("^{}\\[~]|€\f")


@dataclass(frozen=True)
class Finding:
    rule: str
    template_id: str
    message: str
    level: str = "error"


def render(body: str, values: dict[str, str]) -> str:
    return VAR.sub(lambda m: values[m.group(1)], body)


def is_gsm7(text: str) -> bool:
    return all(c in GSM_BASIC or c in GSM_EXT for c in text)


def gsm_length(text: str) -> int:
    return sum(2 if c in GSM_EXT else 1 for c in text)


def denylisted(text: str, clinic_name: str) -> list[str]:
    t = text.replace(clinic_name, " ") if clinic_name else text
    hits = []
    for word in DENYLIST:
        pattern = rf"(?<![a-z]){re.escape(word)}" + ("" if word.endswith(".") else r"(?![a-z])")
        if re.search(pattern, t, re.IGNORECASE):
            hits.append(word)
    return hits


def check(templates: dict[str, Any], policy: dict[str, Any], schema: dict[str, Any]) -> list[Finding]:
    out: list[Finding] = []
    for err in sorted(Draft202012Validator(schema).iter_errors(templates), key=str):
        where = "/".join(str(p) for p in err.absolute_path) or "-"
        out.append(Finding("T1", where, err.message[:160]))
    if out:
        return out  # later rules assume the schema holds

    if str(templates["policy_version"]) != str(policy.get("decision_version")):
        out.append(Finding("T2", "-", "policy_version differs from messaging_policy.yaml decision_version"))

    types = policy.get("message_types") or {}
    never = set(policy.get("never_allowed_fields") or [])
    channels = policy.get("channels") or {}
    opt_out_required = bool(policy.get("opt_out_text_required"))
    seen: dict[str, set[str]] = {}

    for t in templates["templates"]:
        tid, body, ch, mt = t["id"], t["body"], t["channel"], t["message_type"]
        declared, used = set(t["variables"]), set(VAR.findall(body))
        for v in sorted(used - declared):
            out.append(Finding("T3", tid, f"{{{v}}} used in body but not declared"))
        for v in sorted(declared - used):
            out.append(Finding("T3", tid, f"{v} declared but not used in body"))
        for v in sorted(used - set(t["example"])):
            out.append(Finding("T3", tid, f"no example value for {v}"))
        allowed = set((types.get(mt) or {}).get("fields") or [])
        for v in sorted(used | declared):
            if v in never:
                out.append(Finding("T5", tid, f"{v} is in never_allowed_fields"))
            elif v not in allowed:
                out.append(Finding("T4", tid, f"{v} is not a policy field for {mt}"))
        if not (channels.get(ch) or {}).get("integrated"):
            out.append(Finding("T6", tid, f"channel {ch} is not integrated in the policy"))
        seen.setdefault(ch, set()).add(mt)

        if used - set(t["example"]):
            continue
        text = render(body, t["example"])
        for word in denylisted(text, t["example"].get("clinic_name", "")):
            out.append(Finding("T7", tid, f"denylisted word: {word}"))
        if ch == "sms":
            if not is_gsm7(text):
                out.append(Finding("T8", tid, "rendered example has non-GSM-7 characters"))
            else:
                n = gsm_length(text)
                if n > 306:
                    out.append(Finding("T8", tid, f"rendered example is {n} characters (over 2 segments)"))
                elif n > 160:
                    out.append(Finding("T8", tid, f"rendered example is {n} characters (2 segments)", "warning"))
        if opt_out_required and OPT_OUT not in body.lower():
            out.append(Finding("T9", tid, "body has no opt-out text (Reply STOP)"))
        if ch == "whatsapp":
            if t.get("whatsapp_category") != "UTILITY":
                out.append(Finding("T10", tid, "WhatsApp template must be UTILITY"))
            if re.match(r"\s*\{[a-z_]+\}", body) or re.search(r"\{[a-z_]+\}[\s.!?]*$", body):
                out.append(Finding("T10", tid, "WhatsApp body starts or ends with a variable"))

    test_ch = ((policy.get("environments") or {}).get("testing") or {}).get("active_channel")
    required_channels = {c for c, v in channels.items() if (v or {}).get("integrated")} & {"sms", "whatsapp"}
    if test_ch:
        required_channels.add(test_ch)
    for ch in sorted(required_channels):
        for mt in TYPES:
            if mt not in seen.get(ch, set()):
                out.append(Finding("T6", "-", f"channel {ch} has no {mt} template"))

    for ch, replies in (templates.get("system_replies") or {}).items():
        for key, text in replies.items():
            for v in sorted(set(VAR.findall(text)) - REPLY_VARS):
                out.append(Finding("T11", f"system_replies.{ch}.{key}", f"{{{v}}} not allowed in a system reply"))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--templates", type=Path, default=TEMPLATES)
    ap.add_argument("--policy", type=Path, default=POLICY)
    ap.add_argument("--schema", type=Path, default=SCHEMA)
    a = ap.parse_args(argv)
    findings = check(yaml.safe_load(a.templates.read_text(encoding="utf-8")),
                     yaml.safe_load(a.policy.read_text(encoding="utf-8")),
                     json.loads(a.schema.read_text(encoding="utf-8")))
    for f in findings:
        sys.stderr.write(f"{f.level.upper()} {f.rule} {f.template_id}: {f.message}\n")
    errors = [f for f in findings if f.level == "error"]
    if not errors:
        sys.stdout.write(f"OK {a.templates.name}" + (f" ({len(findings)} warnings)" if findings else "") + "\n")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
