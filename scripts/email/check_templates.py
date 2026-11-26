"""Check the callback email templates (P0-08).

Rules:
- link_only (subject and body) may use only the allow-listed fields: no patient data at all.
- No template's subject may use a patient field (only urgency and case ID).
- Every template starts with a "Subject:" line.

Usage: python3 scripts/email/check_templates.py [templates_dir]
Exits 0 when all rules hold, 1 with the problems otherwise. P2-23 turns this into pytest tests.
"""

import re
import sys
from pathlib import Path

LINK_ONLY_ALLOWED = {"urgency", "received_at", "case_id", "admin_console_base_url"}
SUBJECT_ALLOWED = {"urgency", "case_id"}
PATIENT_FIELDS = {
    "patient_name", "first_name", "last_name", "phone", "whatsapp_number", "dob", "email",
    "pat_num", "apt_num", "patient_type", "reason", "reason_category", "situation", "preferred_time",
    "insurance", "provider_name", "symptoms", "procedure",
}
FIELD = re.compile(r"\{([a-z_]+)\}")


def check(directory: Path) -> list[str]:
    problems: list[str] = []
    for name in ("link_only.txt", "full_details.txt"):
        path = directory / name
        if not path.exists():
            problems.append(f"{name}: missing")
            continue
        text = path.read_text(encoding="utf-8")
        first, _, body = text.partition("\n")
        if not first.startswith("Subject: "):
            problems.append(f"{name}: first line must start with 'Subject: '")
        subject_fields = set(FIELD.findall(first))
        if subject_fields - SUBJECT_ALLOWED:
            problems.append(f"{name}: subject uses fields beyond urgency/case_id: {sorted(subject_fields - SUBJECT_ALLOWED)}")
        if name == "link_only.txt":
            fields = set(FIELD.findall(text))
            if fields - LINK_ONLY_ALLOWED:
                problems.append(f"link_only.txt: fields outside the allow-list: {sorted(fields - LINK_ONLY_ALLOWED)}")
            lowered = body.lower()
            for word in ("patient name", "date of birth", "phone:", "patnum"):
                if word in lowered:
                    problems.append(f"link_only.txt: body mentions '{word}'")
    return problems


def main() -> int:
    directory = Path(sys.argv[1] if len(sys.argv) > 1 else "docs/integrations/admin-email/templates")
    problems = check(directory)
    for p in problems:
        sys.stderr.write(f"FAIL {p}\n")
    if not problems:
        sys.stdout.write(f"OK {directory}\n")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
