"""Check docs/compliance/messaging_policy.yaml (P0-07a, spec §10).

Usage: python3 scripts/compliance/check_messaging_policy.py [path]
Exits 0 when the policy is consistent, 1 with a list of problems otherwise.
P4-01 turns these checks into pytest tests.
"""

import sys
from pathlib import Path

import yaml

REQUIRED_NEVER = {
    "last_name", "dob", "reason", "reason_code", "procedure",
    "symptoms", "provider_name", "insurance", "pat_num", "apt_num",
}


def check(policy: dict) -> list[str]:
    problems: list[str] = []
    channels = policy.get("channels") or {}
    envs = policy.get("environments") or {}
    types = policy.get("message_types") or {}
    never = set(policy.get("never_allowed_fields") or [])

    # Testing: one enabled channel, synthetic data only
    testing = envs.get("testing") or {}
    test_ch = testing.get("active_channel")
    if test_ch not in channels:
        problems.append(f"testing: active channel {test_ch!r} is not defined")
    elif not (channels[test_ch].get("integrated") is True and channels[test_ch].get("enabled") is True):
        problems.append(f"testing: channel {test_ch!r} must be integrated and enabled")
    if testing.get("data") != "synthetic_only":
        problems.append("testing: data must be synthetic_only")

    # Production: every clinic option is allowed with PHI, or has a gate and a fallback that is
    prod = envs.get("production") or {}
    options = prod.get("clinic_options") or []
    if not options:
        problems.append("production: clinic_options is empty")
    for ch in options:
        c = channels.get(ch)
        if c is None:
            problems.append(f"production: option {ch!r} is not defined")
            continue
        if c.get("allowed_with_phi") is True:
            continue
        fb = c.get("fallback_until_gate")
        if not c.get("phi_gate"):
            problems.append(f"production: option {ch!r} is not allowed with PHI and names no phi_gate")
        if fb not in channels or channels[fb].get("allowed_with_phi") is not True:
            problems.append(f"production: option {ch!r} needs a fallback allowed with PHI, got {fb!r}")

    # Field rules
    if not types:
        problems.append("message_types is empty")
    missing = REQUIRED_NEVER - never
    if missing:
        problems.append(f"never_allowed_fields lacks: {sorted(missing)}")
    for name, spec in types.items():
        fields = (spec or {}).get("fields") or []
        if not fields:
            problems.append(f"{name}: no fields")
        bad = sorted(set(fields) & never)
        if bad:
            problems.append(f"{name}: never-allowed fields used: {bad}")

    if (policy.get("consent") or {}).get("required") is not True:
        problems.append("consent.required must be true")
    return problems


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "docs/compliance/messaging_policy.yaml")
    problems = check(yaml.safe_load(path.read_text(encoding="utf-8")))
    for p in problems:
        sys.stderr.write(f"FAIL {p}\n")
    if not problems:
        sys.stdout.write(f"OK {path}\n")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
